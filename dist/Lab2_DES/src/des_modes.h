/*
 * des_modes.h - encrypting whole messages (any length) with the DES block
 * cipher: PKCS#7 padding + ECB or CBC mode of operation.
 */
#ifndef DES_MODES_H
#define DES_MODES_H

#include <stddef.h>
#include <stdint.h>

#include "des.h"

typedef enum {
    DES_MODE_ECB = 1,   /* every block encrypted independently             */
    DES_MODE_CBC = 2    /* C_i = E_K(P_i XOR C_{i-1}), C_0 = IV  (default)  */
} des_mode;

enum {
    DES_OK = 0,
    DES_ERR_LENGTH = -1,    /* ciphertext length not a positive multiple of 8 */
    DES_ERR_PADDING = -2,   /* padding check failed (usually: wrong key)      */
    DES_ERR_MODE = -3
};

const char *des_mode_name(des_mode mode);
int des_mode_parse(const char *text, des_mode *mode);

/* Size after PKCS#7 padding: always 1..8 bytes added (a full block when len
 * is already a multiple of 8, so the padding can always be removed). */
size_t des_padded_size(size_t len);

/* Pads `in` and encrypts it into `out` (needs des_padded_size(len) bytes).
 * Returns the ciphertext length.  `iv` is ignored in ECB mode. */
size_t des_encrypt_message(des_mode mode, const des_key_schedule *ks, uint64_t iv,
                           const uint8_t *in, size_t len, uint8_t *out);

/* Decrypts `len` bytes into `out` (needs `len` bytes, padding included),
 * checks and strips the padding.  *plain_len receives the message length. */
int des_decrypt_message(des_mode mode, const des_key_schedule *ks, uint64_t iv,
                        const uint8_t *in, size_t len, uint8_t *out,
                        size_t *plain_len);

#endif /* DES_MODES_H */
