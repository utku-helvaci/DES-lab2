/*
 * des.c - DES block cipher (FIPS PUB 46-3) written so that EVERY step of the
 * algorithm is its own small function.  Each step function
 *   - takes its input as a parameter and returns its output (no side effects),
 *   - keeps the result in a named local variable before returning it, so the
 *     input and the output are both visible in the debugger's watch window
 *     when you stop on the return line,
 *   - is unit-tested in tests/test_des.c.
 *
 * The orchestrating functions (des_generate_round_keys, des_feistel, des_round,
 * des_process_block) call des_trace() after every step.  When a trace sink is
 * installed (bin/des_trace, tcpServer/tcpClient -t) this produces the table
 *     input -> method (function) -> output -> DES step
 * requested for the lab report.  Without a sink des_trace() returns at once.
 */
#include "des.h"
#include "des_trace.h"

/* ------------------------------------------------------------------------- */
/*  Tables from FIPS 46-3. Entries are 1-based bit positions (1 = MSB).      */
/* ------------------------------------------------------------------------- */

/* 2.1 Initial permutation IP (64 -> 64) */
static const uint8_t IP_TABLE[64] = {
    58, 50, 42, 34, 26, 18, 10, 2,
    60, 52, 44, 36, 28, 20, 12, 4,
    62, 54, 46, 38, 30, 22, 14, 6,
    64, 56, 48, 40, 32, 24, 16, 8,
    57, 49, 41, 33, 25, 17,  9, 1,
    59, 51, 43, 35, 27, 19, 11, 3,
    61, 53, 45, 37, 29, 21, 13, 5,
    63, 55, 47, 39, 31, 23, 15, 7
};

/* 2.2 Inverse initial permutation IP^-1 (64 -> 64) */
static const uint8_t IP_INV_TABLE[64] = {
    40, 8, 48, 16, 56, 24, 64, 32,
    39, 7, 47, 15, 55, 23, 63, 31,
    38, 6, 46, 14, 54, 22, 62, 30,
    37, 5, 45, 13, 53, 21, 61, 29,
    36, 4, 44, 12, 52, 20, 60, 28,
    35, 3, 43, 11, 51, 19, 59, 27,
    34, 2, 42, 10, 50, 18, 58, 26,
    33, 1, 41,  9, 49, 17, 57, 25
};

/* 2.3 Expansion/permutation E (32 -> 48): every 4-bit group gets its two
 *     neighbouring bits added at the edges. */
static const uint8_t E_TABLE[48] = {
    32,  1,  2,  3,  4,  5,
     4,  5,  6,  7,  8,  9,
     8,  9, 10, 11, 12, 13,
    12, 13, 14, 15, 16, 17,
    16, 17, 18, 19, 20, 21,
    20, 21, 22, 23, 24, 25,
    24, 25, 26, 27, 28, 29,
    28, 29, 30, 31, 32,  1
};

/* 2.7 Permutation P (32 -> 32) applied to the S-box output */
static const uint8_t P_TABLE[32] = {
    16,  7, 20, 21, 29, 12, 28, 17,
     1, 15, 23, 26,  5, 18, 31, 10,
     2,  8, 24, 14, 32, 27,  3,  9,
    19, 13, 30,  6, 22, 11,  4, 25
};

/* 2.4.1 Permuted choice 1 (64 -> 56): drops parity bits 8,16,...,64 */
static const uint8_t PC1_TABLE[56] = {
    57, 49, 41, 33, 25, 17,  9,
     1, 58, 50, 42, 34, 26, 18,
    10,  2, 59, 51, 43, 35, 27,
    19, 11,  3, 60, 52, 44, 36,
    63, 55, 47, 39, 31, 23, 15,
     7, 62, 54, 46, 38, 30, 22,
    14,  6, 61, 53, 45, 37, 29,
    21, 13,  5, 28, 20, 12,  4
};

/* 2.4.3 Permuted choice 2 (56 -> 48) */
static const uint8_t PC2_TABLE[48] = {
    14, 17, 11, 24,  1,  5,
     3, 28, 15,  6, 21, 10,
    23, 19, 12,  4, 26,  8,
    16,  7, 27, 20, 13,  2,
    41, 52, 31, 37, 47, 55,
    30, 40, 51, 45, 33, 48,
    44, 49, 39, 56, 34, 53,
    46, 42, 50, 36, 29, 32
};

/* 2.4.2 Number of left circular shifts per round (sums to 28) */
static const uint8_t SHIFT_SCHEDULE[DES_ROUNDS] = {
    1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1
};

/* 2.6 The eight S-boxes: SBOX[box][row][column] */
static const uint8_t SBOX[8][4][16] = {
    { /* S1 */
        {14,  4, 13,  1,  2, 15, 11,  8,  3, 10,  6, 12,  5,  9,  0,  7},
        { 0, 15,  7,  4, 14,  2, 13,  1, 10,  6, 12, 11,  9,  5,  3,  8},
        { 4,  1, 14,  8, 13,  6,  2, 11, 15, 12,  9,  7,  3, 10,  5,  0},
        {15, 12,  8,  2,  4,  9,  1,  7,  5, 11,  3, 14, 10,  0,  6, 13}
    },
    { /* S2 */
        {15,  1,  8, 14,  6, 11,  3,  4,  9,  7,  2, 13, 12,  0,  5, 10},
        { 3, 13,  4,  7, 15,  2,  8, 14, 12,  0,  1, 10,  6,  9, 11,  5},
        { 0, 14,  7, 11, 10,  4, 13,  1,  5,  8, 12,  6,  9,  3,  2, 15},
        {13,  8, 10,  1,  3, 15,  4,  2, 11,  6,  7, 12,  0,  5, 14,  9}
    },
    { /* S3 */
        {10,  0,  9, 14,  6,  3, 15,  5,  1, 13, 12,  7, 11,  4,  2,  8},
        {13,  7,  0,  9,  3,  4,  6, 10,  2,  8,  5, 14, 12, 11, 15,  1},
        {13,  6,  4,  9,  8, 15,  3,  0, 11,  1,  2, 12,  5, 10, 14,  7},
        { 1, 10, 13,  0,  6,  9,  8,  7,  4, 15, 14,  3, 11,  5,  2, 12}
    },
    { /* S4 */
        { 7, 13, 14,  3,  0,  6,  9, 10,  1,  2,  8,  5, 11, 12,  4, 15},
        {13,  8, 11,  5,  6, 15,  0,  3,  4,  7,  2, 12,  1, 10, 14,  9},
        {10,  6,  9,  0, 12, 11,  7, 13, 15,  1,  3, 14,  5,  2,  8,  4},
        { 3, 15,  0,  6, 10,  1, 13,  8,  9,  4,  5, 11, 12,  7,  2, 14}
    },
    { /* S5 */
        { 2, 12,  4,  1,  7, 10, 11,  6,  8,  5,  3, 15, 13,  0, 14,  9},
        {14, 11,  2, 12,  4,  7, 13,  1,  5,  0, 15, 10,  3,  9,  8,  6},
        { 4,  2,  1, 11, 10, 13,  7,  8, 15,  9, 12,  5,  6,  3,  0, 14},
        {11,  8, 12,  7,  1, 14,  2, 13,  6, 15,  0,  9, 10,  4,  5,  3}
    },
    { /* S6 */
        {12,  1, 10, 15,  9,  2,  6,  8,  0, 13,  3,  4, 14,  7,  5, 11},
        {10, 15,  4,  2,  7, 12,  9,  5,  6,  1, 13, 14,  0, 11,  3,  8},
        { 9, 14, 15,  5,  2,  8, 12,  3,  7,  0,  4, 10,  1, 13, 11,  6},
        { 4,  3,  2, 12,  9,  5, 15, 10, 11, 14,  1,  7,  6,  0,  8, 13}
    },
    { /* S7 */
        { 4, 11,  2, 14, 15,  0,  8, 13,  3, 12,  9,  7,  5, 10,  6,  1},
        {13,  0, 11,  7,  4,  9,  1, 10, 14,  3,  5, 12,  2, 15,  8,  6},
        { 1,  4, 11, 13, 12,  3,  7, 14, 10, 15,  6,  8,  0,  5,  9,  2},
        { 6, 11, 13,  8,  1,  4, 10,  7,  9,  5,  0, 15, 14,  2,  3, 12}
    },
    { /* S8 */
        {13,  2,  8,  4,  6, 15, 11,  1, 10,  9,  3, 14,  5,  0, 12,  7},
        { 1, 15, 13,  8, 10,  3,  7,  4, 12,  5,  6, 11,  0, 14,  9,  2},
        { 7, 11,  4,  1,  9, 12, 14,  2,  0,  6, 10, 13, 15,  3,  5,  8},
        { 2,  1, 14,  7,  4, 10,  8, 13, 15, 12,  9,  0,  3,  5,  6, 11}
    }
};

/*
 * Generic table-driven permutation.  Output bit i (counted from the left)
 * is input bit table[i].  Used by IP, IP^-1, E, P, PC-1 and PC-2; only the
 * table and the widths differ between those steps.
 */
static uint64_t des_permute(uint64_t input, int input_bits,
                            const uint8_t *table, int output_bits)
{
    uint64_t output = 0;
    for (int i = 0; i < output_bits; i++) {
        int from = table[i];                              /* 1-based, 1 = MSB */
        uint64_t bit = (input >> (input_bits - from)) & 1u;
        output = (output << 1) | bit;
    }
    return output;
}

/* ===================== 2.1 / 2.2  IP and IP^-1 =========================== */

uint64_t des_initial_permutation(uint64_t block)
{
    uint64_t permuted = des_permute(block, 64, IP_TABLE, 64);
    return permuted;
}

uint64_t des_inverse_initial_permutation(uint64_t block)
{
    uint64_t restored = des_permute(block, 64, IP_INV_TABLE, 64);
    return restored;
}

/* ===================== 2.3  Expansion/permutation E ====================== */

uint64_t des_expansion_permutation(uint32_t right)
{
    uint64_t expanded = des_permute(right, 32, E_TABLE, 48);
    return expanded;
}

/* ===================== 2.4  Round-key generation ========================= */

/* 2.4.1  64-bit key -> 56 bits C0|D0 (the 8 parity bits are discarded). */
uint64_t des_permuted_choice_1(uint64_t key)
{
    uint64_t cd = des_permute(key, 64, PC1_TABLE, 56);
    return cd;
}

/* 2.4.2  How many positions C and D are rotated in round 1..16. */
int des_shift_amount(int round)
{
    int amount = 0;
    if (round >= 1 && round <= DES_ROUNDS)
        amount = SHIFT_SCHEDULE[round - 1];
    return amount;
}

/* 2.4.2  Rotate a 28-bit half to the left by 1 or 2 positions. */
uint32_t des_left_circular_shift(uint32_t half, int amount)
{
    uint32_t rotated = ((half << amount) | (half >> (28 - amount))) & 0x0FFFFFFFu;
    return rotated;
}

/* 2.4.3  56 bits Ci|Di -> 48-bit round key Ki. */
uint64_t des_permuted_choice_2(uint64_t cd)
{
    uint64_t subkey = des_permute(cd, 56, PC2_TABLE, 48);
    return subkey;
}

/* 2.4  Complete key schedule: PC-1 once, then shift + PC-2 for every round. */
void des_generate_round_keys(uint64_t key, des_key_schedule *ks)
{
    uint64_t cd = des_permuted_choice_1(key);                     /* 2.4.1 */
    des_trace(DES_STEP_PC1, key, 0, cd);

    uint32_t c = (uint32_t)(cd >> 28) & 0x0FFFFFFFu;              /* C0 */
    uint32_t d = (uint32_t)(cd & 0x0FFFFFFFu);                    /* D0 */

    for (int round = 1; round <= DES_ROUNDS; round++) {
        des_trace_round(round, round);

        int amount = des_shift_amount(round);                     /* 2.4.2 */
        uint32_t c_next = des_left_circular_shift(c, amount);
        des_trace(DES_STEP_SHIFT_C, c, (uint64_t)amount, c_next);
        uint32_t d_next = des_left_circular_shift(d, amount);
        des_trace(DES_STEP_SHIFT_D, d, (uint64_t)amount, d_next);
        c = c_next;
        d = d_next;

        uint64_t cd_round = ((uint64_t)c << 28) | d;              /* Ci|Di */
        uint64_t subkey = des_permuted_choice_2(cd_round);        /* 2.4.3 */
        des_trace(DES_STEP_PC2, cd_round, 0, subkey);
        ks->subkey[round - 1] = subkey;                           /* Ki */
    }
    des_trace_round(0, 0);
}

/* ===================== 2.5 .. 2.9  The round function ===================== */

/* 2.5  E(R) XOR Ki  (48 bits). */
uint64_t des_xor_round_key(uint64_t expanded, uint64_t subkey)
{
    uint64_t mixed = (expanded ^ subkey) & 0xFFFFFFFFFFFFull;
    return mixed;
}

/* 2.6  One S-box: 6 input bits b1..b6 -> 4 output bits.
 *      row    = b1 b6       (outer bits, 0..3)
 *      column = b2 b3 b4 b5 (inner bits, 0..15)                           */
unsigned des_sbox_lookup(int box, unsigned six_bits)
{
    unsigned row = ((six_bits >> 4) & 0x2u) | (six_bits & 0x1u);
    unsigned column = (six_bits >> 1) & 0xFu;
    unsigned four_bits = SBOX[box][row][column];
    return four_bits;
}

/* 2.6  All eight S-boxes: 48 bits -> 32 bits.  This is the step where the
 *      expanded 48-bit value is reduced back to 32 bits (8 x 6 -> 8 x 4).  */
uint32_t des_sbox_substitution(uint64_t input48)
{
    uint32_t output = 0;
    for (int box = 0; box < 8; box++) {
        unsigned six_bits = (unsigned)(input48 >> (42 - 6 * box)) & 0x3Fu;
        unsigned four_bits = des_sbox_lookup(box, six_bits);
        des_trace(DES_STEP_SBOX_LOOKUP, (uint64_t)(box + 1), six_bits, four_bits);
        output = (output << 4) | four_bits;
    }
    return output;
}

/* 2.7  Permutation P on the S-box output. */
uint32_t des_permutation_p(uint32_t input)
{
    uint32_t permuted = (uint32_t)des_permute(input, 32, P_TABLE, 32);
    return permuted;
}

/* The Feistel function f(R, K) = P( S( E(R) XOR K ) ). */
uint32_t des_feistel(uint32_t right, uint64_t subkey)
{
    uint64_t expanded = des_expansion_permutation(right);         /* 2.3 */
    des_trace(DES_STEP_EXPANSION, right, 0, expanded);

    uint64_t mixed = des_xor_round_key(expanded, subkey);         /* 2.5 */
    des_trace(DES_STEP_XOR_KEY, expanded, subkey, mixed);

    uint32_t substituted = des_sbox_substitution(mixed);          /* 2.6 */
    des_trace(DES_STEP_SBOX, mixed, 0, substituted);

    uint32_t f_output = des_permutation_p(substituted);           /* 2.7 */
    des_trace(DES_STEP_P, substituted, 0, f_output);

    return f_output;
}

/* 2.8  L(i-1) XOR f(R(i-1), Ki) - becomes the new right half. */
uint32_t des_xor_left_half(uint32_t left, uint32_t f_output)
{
    uint32_t new_right = left ^ f_output;
    return new_right;
}

/* 2.9  Exchange the two 32-bit halves: L|R -> R|L. */
uint64_t des_swap_halves(uint64_t block)
{
    uint64_t swapped = (block << 32) | (block >> 32);
    return swapped;
}

uint32_t des_left_half(uint64_t block)
{
    return (uint32_t)(block >> 32);
}

uint32_t des_right_half(uint64_t block)
{
    return (uint32_t)(block & 0xFFFFFFFFu);
}

uint64_t des_join_halves(uint32_t left, uint32_t right)
{
    return ((uint64_t)left << 32) | right;
}

/*
 * One round:   Li = R(i-1)
 *              Ri = L(i-1) XOR f(R(i-1), Ki)
 * implemented literally as "XOR into the left half, then swap the halves".
 */
uint64_t des_round(uint64_t state, uint64_t subkey)
{
    uint32_t left = des_left_half(state);                         /* L(i-1) */
    uint32_t right = des_right_half(state);                       /* R(i-1) */

    uint32_t f_output = des_feistel(right, subkey);               /* 2.3-2.7 */

    uint32_t new_right = des_xor_left_half(left, f_output);       /* 2.8 */
    des_trace(DES_STEP_XOR_LEFT, left, f_output, new_right);

    uint64_t before_swap = des_join_halves(new_right, right);     /* (L^f) | R */
    uint64_t after_swap = des_swap_halves(before_swap);           /* 2.9: Li|Ri */
    des_trace(DES_STEP_SWAP, before_swap, 0, after_swap);

    return after_swap;
}

/*
 * Encrypt or decrypt one 64-bit block.  Decryption is the same algorithm
 * with the round keys used in reverse order (K16 first).
 */
uint64_t des_process_block(uint64_t block, const des_key_schedule *ks,
                           des_direction dir, uint64_t round_state[DES_ROUNDS])
{
    des_trace_block_begin(dir);

    uint64_t state = des_initial_permutation(block);              /* 2.1 */
    des_trace(DES_STEP_IP, block, 0, state);

    for (int round = 1; round <= DES_ROUNDS; round++) {
        int key_number = (dir == DES_ENCRYPT) ? round : DES_ROUNDS + 1 - round;
        des_trace_round(round, key_number);
        state = des_round(state, ks->subkey[key_number - 1]);
        if (round_state != NULL)
            round_state[round - 1] = state;
    }
    des_trace_round(0, 0);

    /* The last round must not leave the halves swapped, so they are swapped
     * once more (the "32-bit swap" box in the textbook figure): R16|L16.   */
    uint64_t preoutput = des_swap_halves(state);                  /* 2.9 */
    des_trace(DES_STEP_FINAL_SWAP, state, 0, preoutput);

    uint64_t output = des_inverse_initial_permutation(preoutput); /* 2.2 */
    des_trace(DES_STEP_IP_INV, preoutput, 0, output);

    des_trace_block_end();
    return output;
}

uint64_t des_encrypt_block(uint64_t plaintext, const des_key_schedule *ks)
{
    return des_process_block(plaintext, ks, DES_ENCRYPT, NULL);
}

uint64_t des_decrypt_block(uint64_t ciphertext, const des_key_schedule *ks)
{
    return des_process_block(ciphertext, ks, DES_DECRYPT, NULL);
}

/* ===================== bytes <-> 64-bit block ============================= */

uint64_t des_load_block(const uint8_t bytes[DES_BLOCK_SIZE])
{
    uint64_t block = 0;
    for (int i = 0; i < DES_BLOCK_SIZE; i++)
        block = (block << 8) | bytes[i];
    return block;
}

void des_store_block(uint64_t block, uint8_t bytes[DES_BLOCK_SIZE])
{
    for (int i = DES_BLOCK_SIZE - 1; i >= 0; i--) {
        bytes[i] = (uint8_t)(block & 0xFFu);
        block >>= 8;
    }
}
