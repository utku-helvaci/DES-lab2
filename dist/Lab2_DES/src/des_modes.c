/*
 * des_modes.c - PKCS#7 padding and the ECB / CBC modes of operation
 * (NIST SP 800-38A) on top of the single-block DES functions in des.c.
 */
#include "des_modes.h"

#include <string.h>

const char *des_mode_name(des_mode mode)
{
    switch (mode) {
    case DES_MODE_ECB: return "ECB";
    case DES_MODE_CBC: return "CBC";
    }
    return "?";
}

int des_mode_parse(const char *text, des_mode *mode)
{
    if (text == NULL)
        return -1;
    if (strcmp(text, "cbc") == 0 || strcmp(text, "CBC") == 0) {
        *mode = DES_MODE_CBC;
        return 0;
    }
    if (strcmp(text, "ecb") == 0 || strcmp(text, "ECB") == 0) {
        *mode = DES_MODE_ECB;
        return 0;
    }
    return -1;
}

size_t des_padded_size(size_t len)
{
    return (len / DES_BLOCK_SIZE + 1) * DES_BLOCK_SIZE;
}

size_t des_encrypt_message(des_mode mode, const des_key_schedule *ks, uint64_t iv,
                           const uint8_t *in, size_t len, uint8_t *out)
{
    size_t padded = des_padded_size(len);
    uint8_t pad = (uint8_t)(padded - len);           /* 1..8, PKCS#7 */
    uint64_t previous = iv;                          /* C_0 = IV     */

    for (size_t offset = 0; offset < padded; offset += DES_BLOCK_SIZE) {
        uint8_t bytes[DES_BLOCK_SIZE];
        for (size_t i = 0; i < DES_BLOCK_SIZE; i++)
            bytes[i] = (offset + i < len) ? in[offset + i] : pad;

        uint64_t plain = des_load_block(bytes);
        if (mode == DES_MODE_CBC)
            plain ^= previous;                       /* chain with C_{i-1} */
        uint64_t cipher = des_encrypt_block(plain, ks);
        des_store_block(cipher, out + offset);
        previous = cipher;
    }
    return padded;
}

int des_decrypt_message(des_mode mode, const des_key_schedule *ks, uint64_t iv,
                        const uint8_t *in, size_t len, uint8_t *out,
                        size_t *plain_len)
{
    if (mode != DES_MODE_ECB && mode != DES_MODE_CBC)
        return DES_ERR_MODE;
    if (len == 0 || len % DES_BLOCK_SIZE != 0)
        return DES_ERR_LENGTH;

    uint64_t previous = iv;
    for (size_t offset = 0; offset < len; offset += DES_BLOCK_SIZE) {
        uint64_t cipher = des_load_block(in + offset);
        uint64_t plain = des_decrypt_block(cipher, ks);
        if (mode == DES_MODE_CBC)
            plain ^= previous;
        des_store_block(plain, out + offset);
        previous = cipher;
    }

    /* PKCS#7: the last byte says how many padding bytes there are, and all
     * of them must have that value. */
    uint8_t pad = out[len - 1];
    if (pad < 1 || pad > DES_BLOCK_SIZE)
        return DES_ERR_PADDING;
    for (size_t i = 1; i <= pad; i++)
        if (out[len - i] != pad)
            return DES_ERR_PADDING;

    *plain_len = len - pad;
    return DES_OK;
}
