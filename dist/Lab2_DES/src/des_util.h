/*
 * des_util.h - small helpers: hex parsing/printing, bit strings, randomness.
 */
#ifndef DES_UTIL_H
#define DES_UTIL_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

/* Parse exactly 16 hex digits ("0x" prefix, spaces, ':' and '_' allowed).
 * Returns 0 on success, -1 on error. */
int des_parse_hex64(const char *text, uint64_t *value);

/* Binary string of the low `bits` bits, optionally grouped ("0101 1100"). */
char *des_format_bits(char *buf, size_t cap, uint64_t value, int bits, int group);

/* 48-bit subkey in the textbook notation "eight 6-bit values in hex",
 * e.g. 0x7833c320da70 -> "1e030f03080d2930" (buffer >= 17 bytes). */
char *des_format_subkey(char *buf, size_t cap, uint64_t subkey48);

/* Inverse of des_format_subkey(); returns -1 on malformed input. */
int des_parse_subkey(const char *text, uint64_t *subkey48);

/* Hex dump in 8-byte (one DES block) groups: "0123456789abcdef fedc...". */
void des_print_hex_blocks(FILE *f, const uint8_t *data, size_t len,
                          const char *indent, int blocks_per_line);

/* Fill buf with cryptographically secure random bytes (/dev/urandom). */
int des_random_bytes(void *buf, size_t len);

/* Number of differing bits between a and b (Hamming distance). */
int des_bit_difference(uint64_t a, uint64_t b);

/* Flip bit `bit` (1 = left-most) of a 64-bit value. */
uint64_t des_flip_bit(uint64_t value, int bit);

#endif /* DES_UTIL_H */
