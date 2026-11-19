/*
 * des.h - Data Encryption Standard (FIPS PUB 46-3), one C function per DES step.
 *
 * CMPE455/CMSE456 Lab 2 - DES on two computers.
 *
 * Conventions
 *   - Bit numbering follows FIPS 46-3 and the textbook: bit 1 is the LEFT-MOST
 *     (most significant) bit of a value.
 *   - A value narrower than its C type is stored RIGHT-aligned:
 *       64-bit block   -> uint64_t
 *       56-bit C|D     -> low 56 bits of a uint64_t (C = upper 28, D = lower 28)
 *       48-bit subkey  -> low 48 bits of a uint64_t
 *       32-bit half    -> uint32_t
 *       28-bit C or D  -> low 28 bits of a uint32_t
 *
 * Mapping of the lab-sheet items to functions
 *   2.1   des_initial_permutation()          64 -> 64 bits
 *   2.2   des_inverse_initial_permutation()  64 -> 64 bits
 *   2.3   des_expansion_permutation()        32 -> 48 bits
 *   2.4   des_generate_round_keys()          64-bit key -> K1..K16
 *   2.4.1   des_permuted_choice_1()          64 -> 56 bits (parity bits dropped)
 *   2.4.2   des_left_circular_shift()        28 -> 28 bits, amount = des_shift_amount(i)
 *   2.4.3   des_permuted_choice_2()          56 -> 48 bits
 *   2.5   des_xor_round_key()                48 XOR 48 -> 48 bits
 *   2.6   des_sbox_substitution()            48 -> 32 bits (8 x des_sbox_lookup(): 6 -> 4)
 *   2.7   des_permutation_p()                32 -> 32 bits
 *   2.8   des_xor_left_half()                32 XOR 32 -> 32 bits
 *   2.9   des_swap_halves()                  L|R -> R|L
 *         des_feistel()                      f(R, K) = P(S(E(R) XOR K))
 *         des_round()                        one complete round (2.3 .. 2.9)
 *         des_process_block()                IP, 16 rounds, 32-bit swap, IP^-1
 */
#ifndef DES_H
#define DES_H

#include <stddef.h>
#include <stdint.h>

#define DES_ROUNDS     16
#define DES_BLOCK_SIZE 8   /* bytes */

typedef enum { DES_ENCRYPT = 0, DES_DECRYPT = 1 } des_direction;

/* The 16 round keys K1..K16 (48 bits each) are kept in subkey[0..15]. */
typedef struct {
    uint64_t subkey[DES_ROUNDS];
} des_key_schedule;

/* ---- 2.1 / 2.2  Initial permutation and its inverse ---------------------- */
uint64_t des_initial_permutation(uint64_t block);
uint64_t des_inverse_initial_permutation(uint64_t block);

/* ---- 2.3  Expansion/permutation E ---------------------------------------- */
uint64_t des_expansion_permutation(uint32_t right);

/* ---- 2.4  Round-key generation ------------------------------------------- */
uint64_t des_permuted_choice_1(uint64_t key);
int      des_shift_amount(int round);
uint32_t des_left_circular_shift(uint32_t half, int amount);
uint64_t des_permuted_choice_2(uint64_t cd);
void     des_generate_round_keys(uint64_t key, des_key_schedule *ks);

/* ---- 2.5 .. 2.9  Inside one round ----------------------------------------- */
uint64_t des_xor_round_key(uint64_t expanded, uint64_t subkey);
unsigned des_sbox_lookup(int box, unsigned six_bits);
uint32_t des_sbox_substitution(uint64_t input48);
uint32_t des_permutation_p(uint32_t input);
uint32_t des_feistel(uint32_t right, uint64_t subkey);
uint32_t des_xor_left_half(uint32_t left, uint32_t f_output);
uint64_t des_swap_halves(uint64_t block);

/* ---- Helpers for the 64-bit state L|R -------------------------------------- */
uint32_t des_left_half(uint64_t block);
uint32_t des_right_half(uint64_t block);
uint64_t des_join_halves(uint32_t left, uint32_t right);

/* ---- Whole cipher ---------------------------------------------------------- */
uint64_t des_round(uint64_t state, uint64_t subkey);

/* round_state may be NULL; otherwise it receives Li|Ri after every round. */
uint64_t des_process_block(uint64_t block, const des_key_schedule *ks,
                           des_direction dir, uint64_t round_state[DES_ROUNDS]);
uint64_t des_encrypt_block(uint64_t plaintext, const des_key_schedule *ks);
uint64_t des_decrypt_block(uint64_t ciphertext, const des_key_schedule *ks);

/* ---- 8 bytes <-> 64-bit block (big-endian: byte 0 holds bits 1..8) -------- */
uint64_t des_load_block(const uint8_t bytes[DES_BLOCK_SIZE]);
void     des_store_block(uint64_t block, uint8_t bytes[DES_BLOCK_SIZE]);

#endif /* DES_H */
