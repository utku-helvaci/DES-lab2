/*
 * des_util.c - small helpers shared by the tools, the tests and the chat.
 */
#include "des_util.h"

#include <ctype.h>
#include <string.h>

int des_parse_hex64(const char *text, uint64_t *value)
{
    uint64_t result = 0;
    int digits = 0;

    if (text == NULL)
        return -1;
    if (text[0] == '0' && (text[1] == 'x' || text[1] == 'X'))
        text += 2;

    for (const char *c = text; *c; c++) {
        int nibble;
        if (*c == ' ' || *c == ':' || *c == '_')
            continue;
        if (*c >= '0' && *c <= '9')
            nibble = *c - '0';
        else if (*c >= 'a' && *c <= 'f')
            nibble = *c - 'a' + 10;
        else if (*c >= 'A' && *c <= 'F')
            nibble = *c - 'A' + 10;
        else
            return -1;
        if (++digits > 16)
            return -1;
        result = (result << 4) | (uint64_t)nibble;
    }
    if (digits != 16)
        return -1;
    *value = result;
    return 0;
}

char *des_format_bits(char *buf, size_t cap, uint64_t value, int bits, int group)
{
    size_t pos = 0;
    for (int i = bits - 1; i >= 0 && pos + 1 < cap; i--) {
        buf[pos++] = ((value >> i) & 1u) ? '1' : '0';
        if (group > 0 && i > 0 && i % group == 0 && pos + 1 < cap)
            buf[pos++] = ' ';
    }
    buf[pos] = '\0';
    return buf;
}

char *des_format_subkey(char *buf, size_t cap, uint64_t subkey48)
{
    size_t pos = 0;
    buf[0] = '\0';
    for (int g = 0; g < 8 && pos + 3 <= cap; g++) {
        unsigned six = (unsigned)(subkey48 >> (42 - 6 * g)) & 0x3Fu;
        snprintf(buf + pos, cap - pos, "%02x", six);
        pos += 2;
    }
    return buf;
}

int des_parse_subkey(const char *text, uint64_t *subkey48)
{
    uint64_t result = 0;
    if (text == NULL || strlen(text) != 16)
        return -1;
    for (int g = 0; g < 8; g++) {
        unsigned value = 0;
        for (int j = 0; j < 2; j++) {
            int c = tolower((unsigned char)text[2 * g + j]);
            if (!isxdigit(c))
                return -1;
            value = value * 16 + (unsigned)(isdigit(c) ? c - '0' : c - 'a' + 10);
        }
        if (value > 0x3F)
            return -1;
        result = (result << 6) | value;
    }
    *subkey48 = result;
    return 0;
}

void des_print_hex_blocks(FILE *f, const uint8_t *data, size_t len,
                          const char *indent, int blocks_per_line)
{
    if (blocks_per_line <= 0)
        blocks_per_line = 4;
    for (size_t i = 0; i < len; i++) {
        size_t block = i / 8;
        if (i % 8 == 0 && i > 0) {
            if (block % (size_t)blocks_per_line == 0)
                fprintf(f, "\n%s", indent);
            else
                fputc(' ', f);
        }
        fprintf(f, "%02x", data[i]);
    }
    fputc('\n', f);
}

int des_random_bytes(void *buf, size_t len)
{
    FILE *urandom = fopen("/dev/urandom", "rb");
    if (urandom == NULL)
        return -1;
    size_t got = fread(buf, 1, len, urandom);
    fclose(urandom);
    return got == len ? 0 : -1;
}

int des_bit_difference(uint64_t a, uint64_t b)
{
    uint64_t diff = a ^ b;
    int count = 0;
    while (diff) {
        diff &= diff - 1;   /* clear the lowest set bit */
        count++;
    }
    return count;
}

uint64_t des_flip_bit(uint64_t value, int bit)
{
    if (bit < 1 || bit > 64)
        return value;
    return value ^ (1ull << (64 - bit));
}
