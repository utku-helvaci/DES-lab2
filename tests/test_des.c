/*
 * test_des.c - unit tests for every DES step (lab items 2.1 - 2.9), the key
 * schedule, whole blocks, the message modes and the avalanche effect.
 *
 * Expected values are taken from sources that are independent of this code:
 *   [T] lab handout DES_LAB_example (= Stallings, Cryptography and Network
 *       Security, 8th ed., Tables 4.2 and 4.3): key 0f1571c947d9e859,
 *       plaintext 02468aceeca86420
 *   [G] J. Orlin Grabbe, "The DES Algorithm Illustrated": key 133457799bbcdff1,
 *       M = 0123456789abcdef; lists the result of every step of round 1
 *   [S] Stallings: S-box example S1(011001) = 1001
 *   [F] FIPS PUB 81 (DES modes of operation), "Now is the time for all "
 *   [N] variable-plaintext known-answer vectors, key 0101010101010101
 *       (NIST SP 800-17, Appendix A; originally NBS SP 500-20)
 * Properties (inverse, permutation, weak keys, complementation) need no data.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "des.h"
#include "des_modes.h"
#include "des_trace.h"
#include "des_util.h"

typedef unsigned long long ull;

static int g_checks, g_failures;

static void check_eq(int line, const char *what, uint64_t actual, uint64_t expected)
{
    g_checks++;
    if (actual != expected) {
        g_failures++;
        printf("    FAIL line %d: %s = %llx, expected %llx\n", line, what, (ull)actual,
               (ull)expected);
    }
}
#define CHECK_EQ(what, actual, expected) \
    check_eq(__LINE__, what, (uint64_t)(actual), (uint64_t)(expected))
#define CHECK(what, condition) CHECK_EQ(what, !!(condition), 1)

static void run(const char *name, void (*test)(void))
{
    int checks = g_checks, failures = g_failures;
    test();
    printf("[%s] %-62s %5d checks\n", g_failures == failures ? "PASS" : "FAIL", name,
           g_checks - checks);
}

/* Reproducible pseudo-random numbers (xorshift64*) for property tests. */
static uint64_t g_rng = 0x9E3779B97F4A7C15ull;
static uint64_t rnd(void)
{
    g_rng ^= g_rng >> 12;
    g_rng ^= g_rng << 25;
    g_rng ^= g_rng >> 27;
    return g_rng * 0x2545F4914F6CDD1Dull;
}

static uint64_t subkey(const char *six_bit_groups)
{
    uint64_t k = 0;
    if (des_parse_subkey(six_bit_groups, &k) != 0) {
        printf("bad subkey literal %s\n", six_bit_groups);
        exit(2);
    }
    return k;
}

/* ---------------- reference data ---------------- */

#define TB_KEY    0x0f1571c947d9e859ull
#define TB_PLAIN  0x02468aceeca86420ull
#define TB_CIPHER 0xda02ce3a89ecac3bull

/* [T] Table 4.2.  K6 and K7 are printed with a letter 'l' instead of the
 * digit '1' in the handout ("...2alc", "...0blc..."); corrected here. */
static const char *TB_SUBKEYS[16] = {
    "1e030f03080d2930", "0a31293432242318", "23072318201d0c1d", "05261d3824311a20",
    "3325340136002c25", "123a2d0d04262a1c", "021f120b1c130611", "1c10372a2832002b",
    "04292a380c341f03", "2703212607280403", "2826390c31261504", "12071c241a0a0f08",
    "300935393c0d100b", "311e09231321182a", "283d3e0227072528", "2921080b13143025"};

/* [T] L_i, R_i for i = 0 (after IP) .. 16 */
static const uint32_t TB_L[17] = {
    0x5a005a00, 0x3cf03c0f, 0xbad22845, 0x99e9b723, 0x0bae3b9e, 0x42415649,
    0x18b3fa41, 0x9616fe23, 0x67117cf2, 0xc11bfc09, 0x887fbc6c, 0x600f7e8b,
    0xf596506e, 0x738538b8, 0xc6a62c4e, 0x56b0bd75, 0x75e8fd8f};
static const uint32_t TB_R[17] = {
    0x3cf03c0f, 0xbad22845, 0x99e9b723, 0x0bae3b9e, 0x42415649, 0x18b3fa41,
    0x9616fe23, 0x67117cf2, 0xc11bfc09, 0x887fbc6c, 0x600f7e8b, 0xf596506e,
    0x738538b8, 0xc6a62c4e, 0x56b0bd75, 0x75e8fd8f, 0x25896490};

#define GR_KEY    0x133457799bbcdff1ull
#define GR_PLAIN  0x0123456789abcdefull
#define GR_CIPHER 0x85e813540f0ab405ull
#define GR_K1     0x1b02effc7072ull   /* 000110 110000 001011 101111 111111 000111 000001 110010 */
#define GR_K2     0x79aed9dbc9e5ull
#define GR_K16    0xcb3d8b0e17f5ull

/* ---------------- 2.1 / 2.2 ---------------- */

static void test_initial_permutation(void)
{
    CHECK_EQ("[T] IP(02468aceeca86420)", des_initial_permutation(TB_PLAIN), 0x5a005a003cf03c0full);
    CHECK_EQ("[G] IP(0123456789abcdef)", des_initial_permutation(GR_PLAIN), 0xcc00ccfff0aaf0aaull);
    /* first table entry: input bit 58 becomes output bit 1 */
    CHECK_EQ("IP moves bit 58 to bit 1", des_initial_permutation(1ull << (64 - 58)), 1ull << 63);
    /* a permutation keeps the number of 1-bits */
    for (int i = 0; i < 1000; i++) {
        uint64_t x = rnd();
        CHECK_EQ("popcount preserved", des_bit_difference(des_initial_permutation(x), 0),
                 des_bit_difference(x, 0));
    }
}

static void test_inverse_initial_permutation(void)
{
    CHECK_EQ("[T] IP^-1(R16|L16)", des_inverse_initial_permutation(0x2589649075e8fd8full), TB_CIPHER);
    CHECK_EQ("[G] IP^-1(R16|L16)", des_inverse_initial_permutation(0x0a4cd99543423234ull), GR_CIPHER);
    for (int bit = 1; bit <= 64; bit++) {
        uint64_t x = 1ull << (64 - bit);
        CHECK_EQ("IP^-1(IP(single bit))", des_inverse_initial_permutation(des_initial_permutation(x)), x);
    }
    for (int i = 0; i < 10000; i++) {
        uint64_t x = rnd();
        CHECK_EQ("IP^-1(IP(x)) = x", des_inverse_initial_permutation(des_initial_permutation(x)), x);
        CHECK_EQ("IP(IP^-1(x)) = x", des_initial_permutation(des_inverse_initial_permutation(x)), x);
    }
}

/* ---------------- 2.3 ---------------- */

static void test_expansion(void)
{
    CHECK_EQ("[G] E(f0aaf0aa)", des_expansion_permutation(0xf0aaf0aa), 0x7a15557a1555ull);
    CHECK_EQ("E(ffffffff) = 48 ones", des_expansion_permutation(0xffffffffu), 0xffffffffffffull);
    CHECK_EQ("E(0) = 0", des_expansion_permutation(0), 0);
    /* 16 of the 32 input bits are used twice (the edges of every 4-bit group) */
    int doubled = 0;
    for (int bit = 1; bit <= 32; bit++) {
        int copies = des_bit_difference(des_expansion_permutation(1u << (32 - bit)), 0);
        CHECK("each input bit appears once or twice", copies == 1 || copies == 2);
        doubled += (copies == 2);
    }
    CHECK_EQ("bits that appear twice", doubled, 16);
}

/* ---------------- 2.4 ---------------- */

static void test_permuted_choice_1(void)
{
    CHECK_EQ("[G] PC-1(133457799bbcdff1) = C0|D0", des_permuted_choice_1(GR_KEY), 0xf0ccaaf556678full);
    /* parity bits 8, 16, ..., 64 are dropped */
    for (int i = 0; i < 1000; i++) {
        uint64_t k = rnd();
        CHECK_EQ("parity bits ignored", des_permuted_choice_1(k ^ 0x0101010101010101ull),
                 des_permuted_choice_1(k));
    }
    CHECK_EQ("PC-1 output is 56 bits", des_permuted_choice_1(~0ull), 0xffffffffffffffull);
}

static void test_left_shifts(void)
{
    static const int expected[16] = {1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1};
    int total = 0;
    for (int round = 1; round <= 16; round++) {
        CHECK_EQ("shift schedule", des_shift_amount(round), expected[round - 1]);
        total += des_shift_amount(round);
    }
    CHECK_EQ("shifts add up to 28 (C16 = C0)", total, 28);
    CHECK_EQ("[G] C1 = C0 <<< 1", des_left_circular_shift(0xf0ccaaf, 1), 0xe19955f);
    CHECK_EQ("[G] D1 = D0 <<< 1", des_left_circular_shift(0x556678f, 1), 0xaaccf1e);
    CHECK_EQ("bit 1 wraps around to bit 28", des_left_circular_shift(0x8000000, 1), 0x0000001);
    CHECK_EQ("two positions", des_left_circular_shift(0xc000000, 2), 0x0000003);
    for (int i = 0; i < 1000; i++) {
        uint32_t half = (uint32_t)rnd() & 0x0FFFFFFF, x = half;
        for (int round = 1; round <= 16; round++)
            x = des_left_circular_shift(x, des_shift_amount(round));
        CHECK_EQ("16 rounds of shifts give back C0", x, half);
    }
}

static void test_permuted_choice_2_and_schedule(void)
{
    des_key_schedule ks;
    des_generate_round_keys(GR_KEY, &ks);
    CHECK_EQ("[G] K1", ks.subkey[0], GR_K1);
    CHECK_EQ("[G] K2", ks.subkey[1], GR_K2);
    CHECK_EQ("[G] K16", ks.subkey[15], GR_K16);
    CHECK_EQ("[G] PC-2(C1|D1) = K1", des_permuted_choice_2(0xe19955faaccf1eull), GR_K1);

    des_generate_round_keys(TB_KEY, &ks);
    for (int i = 0; i < 16; i++)
        CHECK_EQ("[T] Table 4.2 subkey Ki", ks.subkey[i], subkey(TB_SUBKEYS[i]));

    /* PC-2 drops 8 of the 56 bits -> 48 ones out of 56 ones */
    CHECK_EQ("PC-2(all ones) = 48 ones", des_permuted_choice_2(0xffffffffffffffull), 0xffffffffffffull);
}

/* ---------------- 2.5 - 2.9 ---------------- */

static void test_xor_round_key(void)
{
    CHECK_EQ("[G] E(R0) xor K1", des_xor_round_key(0x7a15557a1555ull, GR_K1), 0x6117ba866527ull);
    CHECK_EQ("x xor x = 0", des_xor_round_key(0x123456789abcull, 0x123456789abcull), 0);
    CHECK_EQ("result stays 48 bits", des_xor_round_key(~0ull, 0), 0xffffffffffffull);
}

static void test_sboxes(void)
{
    CHECK_EQ("[S] S1(011001) = 1001", des_sbox_lookup(0, 0x19), 0x9);
    CHECK_EQ("[G] S1(011000) = 0101", des_sbox_lookup(0, 0x18), 0x5);
    CHECK_EQ("[G] S(E(R0) xor K1)", des_sbox_substitution(0x6117ba866527ull), 0x5c82b597);
    /* every row of every S-box is a permutation of 0..15 */
    for (int box = 0; box < 8; box++)
        for (int row = 0; row < 4; row++) {
            unsigned seen = 0;
            for (int col = 0; col < 16; col++) {
                unsigned six = ((unsigned)(row & 2) << 4) | ((unsigned)col << 1) | (unsigned)(row & 1);
                seen |= 1u << des_sbox_lookup(box, six);
            }
            CHECK_EQ("S-box row is a permutation of 0..15", seen, 0xFFFFu);
        }
}

static void test_permutation_p(void)
{
    CHECK_EQ("[G] P(5c82b597)", des_permutation_p(0x5c82b597), 0x234aa9bb);
    uint32_t all = 0;
    for (int bit = 1; bit <= 32; bit++) {
        uint32_t out = des_permutation_p(1u << (32 - bit));
        CHECK_EQ("one bit in, one bit out", des_bit_difference(out, 0), 1);
        all |= out;
    }
    CHECK_EQ("P reaches every output bit", all, 0xffffffffu);
    /* f(R0,K1) of the textbook example follows from Table 4.2: f = L0 xor R1 */
    CHECK_EQ("[T] f(R0,K1) = L0 xor R1", des_feistel(TB_R[0], subkey(TB_SUBKEYS[0])),
             TB_L[0] ^ TB_R[1]);
    CHECK_EQ("[G] f(R0,K1)", des_feistel(0xf0aaf0aa, GR_K1), 0x234aa9bb);
}

static void test_xor_left_half(void)
{
    CHECK_EQ("[G] L0 xor f = R1", des_xor_left_half(0xcc00ccff, 0x234aa9bb), 0xef4a6544);
    CHECK_EQ("[T] L0 xor f = R1",
             des_xor_left_half(TB_L[0], des_feistel(TB_R[0], subkey(TB_SUBKEYS[0]))), TB_R[1]);
}

static void test_swap(void)
{
    CHECK_EQ("swap(01234567|89abcdef)", des_swap_halves(0x0123456789abcdefull), 0x89abcdef01234567ull);
    for (int i = 0; i < 1000; i++) {
        uint64_t x = rnd();
        CHECK_EQ("swap(swap(x)) = x", des_swap_halves(des_swap_halves(x)), x);
    }
    CHECK_EQ("[T] round 1: L1|R1", des_round(0x5a005a003cf03c0full, subkey(TB_SUBKEYS[0])),
             0x3cf03c0fbad22845ull);
    CHECK_EQ("[G] round 1: L1|R1", des_round(0xcc00ccfff0aaf0aaull, GR_K1), 0xf0aaf0aaef4a6544ull);
}

/* ---------------- whole blocks ---------------- */

static void test_textbook_example(void)
{
    des_key_schedule ks;
    uint64_t state[DES_ROUNDS];
    des_generate_round_keys(TB_KEY, &ks);
    uint64_t c = des_process_block(TB_PLAIN, &ks, DES_ENCRYPT, state);
    for (int r = 1; r <= 16; r++) {
        CHECK_EQ("[T] Li", des_left_half(state[r - 1]), TB_L[r]);
        CHECK_EQ("[T] Ri", des_right_half(state[r - 1]), TB_R[r]);
    }
    CHECK_EQ("[T] ciphertext", c, TB_CIPHER);
    CHECK_EQ("[T] decryption", des_decrypt_block(TB_CIPHER, &ks), TB_PLAIN);
}

static void test_grabbe_example(void)
{
    des_key_schedule ks;
    uint64_t state[DES_ROUNDS];
    des_generate_round_keys(GR_KEY, &ks);
    uint64_t c = des_process_block(GR_PLAIN, &ks, DES_ENCRYPT, state);
    CHECK_EQ("[G] L1|R1", state[0], 0xf0aaf0aaef4a6544ull);
    CHECK_EQ("[G] L16|R16", state[15], 0x434232340a4cd995ull);
    CHECK_EQ("[G] ciphertext", c, GR_CIPHER);
    CHECK_EQ("[G] decryption", des_decrypt_block(GR_CIPHER, &ks), GR_PLAIN);
}

static void test_known_answers(void)
{
    static const struct { uint64_t plain, cipher; } nbs[] = {
        {0x8000000000000000ull, 0x95f8a5e5dd31d900ull},
        {0x4000000000000000ull, 0xdd7f121ca5015619ull},
        {0x2000000000000000ull, 0x2e8653104f3834eaull},
        {0x0000000000000001ull, 0x166b40b44aba4bd6ull}};
    des_key_schedule ks;
    des_generate_round_keys(0x0101010101010101ull, &ks);
    for (size_t i = 0; i < sizeof nbs / sizeof nbs[0]; i++) {
        CHECK_EQ("[N] encrypt", des_encrypt_block(nbs[i].plain, &ks), nbs[i].cipher);
        CHECK_EQ("[N] decrypt", des_decrypt_block(nbs[i].cipher, &ks), nbs[i].plain);
    }
}

static void test_properties(void)
{
    des_key_schedule ks, ks_complement;
    /* Weak keys: all 16 subkeys equal, so encryption is its own inverse. */
    static const uint64_t weak[] = {0x0101010101010101ull, 0xfefefefefefefefeull,
                                    0xe0e0e0e0f1f1f1f1ull, 0x1f1f1f1f0e0e0e0eull};
    for (size_t i = 0; i < 4; i++) {
        des_generate_round_keys(weak[i], &ks);
        uint64_t x = rnd();
        CHECK_EQ("weak key: E(E(x)) = x", des_encrypt_block(des_encrypt_block(x, &ks), &ks), x);
    }
    for (int i = 0; i < 300; i++) {
        uint64_t key = rnd(), x = rnd();
        des_generate_round_keys(key, &ks);
        des_generate_round_keys(~key, &ks_complement);
        uint64_t c = des_encrypt_block(x, &ks);
        CHECK_EQ("D(E(x)) = x", des_decrypt_block(c, &ks), x);
        CHECK_EQ("complementation: E_~K(~x) = ~E_K(x)", des_encrypt_block(~x, &ks_complement), ~c);
    }
}

/* ---------------- messages (padding, ECB, CBC) ---------------- */

static void test_modes(void)
{
    static const uint8_t fips_ecb[24] = {
        0x3f, 0xa4, 0x0e, 0x8a, 0x98, 0x4d, 0x48, 0x15, 0x6a, 0x27, 0x17, 0x87,
        0xab, 0x88, 0x83, 0xf9, 0x89, 0x3d, 0x51, 0xec, 0x4b, 0x56, 0x3b, 0x53};
    static const uint8_t fips_cbc[24] = {
        0xe5, 0xc7, 0xcd, 0xde, 0x87, 0x2b, 0xf2, 0x7c, 0x43, 0xe9, 0x34, 0x00,
        0x8c, 0x38, 0x9c, 0x0f, 0x68, 0x37, 0x88, 0x49, 0x9a, 0x7c, 0x05, 0xf6};
    const char *msg = "Now is the time for all ";
    uint8_t out[64], back[64];
    size_t n = 0;
    des_key_schedule ks;
    des_generate_round_keys(0x0123456789abcdefull, &ks);

    /* the FIPS example is 3 whole blocks; PKCS#7 then adds a 4th block */
    CHECK_EQ("padded length of 24 bytes", des_encrypt_message(DES_MODE_ECB, &ks, 0, (const uint8_t *)msg, 24, out), 32);
    CHECK("[F] ECB ciphertext", memcmp(out, fips_ecb, 24) == 0);
    des_encrypt_message(DES_MODE_CBC, &ks, 0x1234567890abcdefull, (const uint8_t *)msg, 24, out);
    CHECK("[F] CBC ciphertext", memcmp(out, fips_cbc, 24) == 0);

    CHECK_EQ("pad 0 -> 8", des_padded_size(0), 8);
    CHECK_EQ("pad 7 -> 8", des_padded_size(7), 8);
    CHECK_EQ("pad 8 -> 16", des_padded_size(8), 16);
    CHECK_EQ("pad 13 -> 16", des_padded_size(13), 16);

    for (int mode = DES_MODE_ECB; mode <= DES_MODE_CBC; mode++)
        for (size_t len = 0; len <= 40; len++) {
            uint8_t text[40];
            for (size_t i = 0; i < len; i++)
                text[i] = (uint8_t)rnd();
            uint64_t iv = rnd();
            size_t clen = des_encrypt_message((des_mode)mode, &ks, iv, text, len, out);
            int rc = des_decrypt_message((des_mode)mode, &ks, iv, out, clen, back, &n);
            CHECK_EQ("round trip status", rc, DES_OK);
            CHECK("round trip text", n == len && memcmp(back, text, len) == 0);
        }

    /* ECB leaks repeated blocks, CBC hides them */
    uint8_t same[16];
    memset(same, 'A', sizeof same);
    des_encrypt_message(DES_MODE_ECB, &ks, 0, same, 16, out);
    CHECK("ECB: equal blocks -> equal ciphertext", memcmp(out, out + 8, 8) == 0);
    des_encrypt_message(DES_MODE_CBC, &ks, 0x0f0e0d0c0b0a0908ull, same, 16, out);
    CHECK("CBC: equal blocks -> different ciphertext", memcmp(out, out + 8, 8) != 0);

    /* wrong key: the padding check fails (deterministic in ECB) */
    des_key_schedule wrong;
    des_generate_round_keys(0x1f1571c947d9e859ull, &wrong);
    size_t clen = des_encrypt_message(DES_MODE_ECB, &ks, 0, (const uint8_t *)"secret", 6, out);
    CHECK_EQ("wrong key -> padding error",
             des_decrypt_message(DES_MODE_ECB, &wrong, 0, out, clen, back, &n), DES_ERR_PADDING);
    CHECK_EQ("bad length rejected", des_decrypt_message(DES_MODE_CBC, &ks, 0, out, 7, back, &n),
             DES_ERR_LENGTH);
}

/* ---------------- avalanche (Table 4.3) ---------------- */

static void test_avalanche(void)
{
    static const int table_4_3[18] = {1, 1, 5, 18, 34, 37, 33, 32, 33,
                                      32, 34, 37, 31, 29, 33, 31, 32, 32};
    des_key_schedule ks, ks2;
    uint64_t s1[DES_ROUNDS], s2[DES_ROUNDS];
    uint64_t p2 = des_flip_bit(TB_PLAIN, 4);
    CHECK_EQ("[T] flipped plaintext", p2, 0x12468aceeca86420ull);

    des_generate_round_keys(TB_KEY, &ks);
    uint64_t c1 = des_process_block(TB_PLAIN, &ks, DES_ENCRYPT, s1);
    uint64_t c2 = des_process_block(p2, &ks, DES_ENCRYPT, s2);
    CHECK_EQ("[T] round 0 difference", des_bit_difference(TB_PLAIN, p2), table_4_3[0]);
    for (int r = 0; r < 16; r++)
        CHECK_EQ("[T] Table 4.3 differing bits", des_bit_difference(s1[r], s2[r]), table_4_3[r + 1]);
    CHECK_EQ("[T] Table 4.3 final difference", des_bit_difference(c1, c2), table_4_3[17]);
    CHECK_EQ("[T] second ciphertext", c2, 0x057cde97d7683f2aull);

    /* key bit 4: 0f1571c9... -> 1f1571c9... */
    des_generate_round_keys(des_flip_bit(TB_KEY, 4), &ks2);
    CHECK_EQ("key bit 4 flipped: ciphertext", des_encrypt_block(TB_PLAIN, &ks2), 0xee92b50606b62b0bull);
    /* key bit 8 is a parity bit: dropped by PC-1, ciphertext unchanged */
    des_generate_round_keys(des_flip_bit(TB_KEY, 8), &ks2);
    CHECK_EQ("parity bit flipped: same ciphertext", des_encrypt_block(TB_PLAIN, &ks2), TB_CIPHER);
}

/* ---------------- the trace table itself ---------------- */

static int g_rows, g_last_step;
static char g_first_function[64];
static void count_rows(const des_trace_row *row, void *user)
{
    (void)user;
    if (g_rows++ == 0)
        snprintf(g_first_function, sizeof g_first_function, "%s", row->function);
    g_last_step = (int)row->step;
}

static void test_trace(void)
{
    des_key_schedule ks;
    g_rows = 0;
    des_trace_start(count_rows, NULL, 0, 0);
    des_generate_round_keys(TB_KEY, &ks);
    des_encrypt_block(TB_PLAIN, &ks);
    des_trace_stop();
    /* 1 PC-1 + 16 x (2 shifts + PC-2) + IP + 16 x 6 + final swap + IP^-1 */
    CHECK_EQ("rows in the trace table", g_rows, 1 + 16 * 3 + 1 + 16 * 6 + 2);
    CHECK("first row is PC-1", strcmp(g_first_function, "des_permuted_choice_1") == 0);
    CHECK_EQ("last row is IP^-1", g_last_step, DES_STEP_IP_INV);

    g_rows = 0;
    des_trace_start(count_rows, NULL, 1, 0);
    des_encrypt_block(TB_PLAIN, &ks);
    des_trace_stop();
    CHECK_EQ("rows with S-box detail", g_rows, 1 + 16 * (6 + 8) + 2);

    g_rows = 0;
    des_trace_start(count_rows, NULL, 0, 1);
    des_encrypt_block(TB_PLAIN, &ks);
    des_encrypt_block(TB_PLAIN, &ks);
    des_trace_stop();
    CHECK_EQ("max_blocks = 1 stops after one block", g_rows, 1 + 16 * 6 + 2);
}

int main(void)
{
    printf("DES unit tests  ([T] textbook/handout, [G] Grabbe, [S] Stallings, "
           "[F] FIPS 81, [N] NBS)\n\n");
    run("2.1   initial permutation IP", test_initial_permutation);
    run("2.2   inverse initial permutation IP^-1", test_inverse_initial_permutation);
    run("2.3   expansion/permutation E", test_expansion);
    run("2.4.1 permuted choice 1 (PC-1)", test_permuted_choice_1);
    run("2.4.2 left circular shift schedule", test_left_shifts);
    run("2.4.3 permuted choice 2 (PC-2) + all 16 round keys", test_permuted_choice_2_and_schedule);
    run("2.5   XOR with round key", test_xor_round_key);
    run("2.6   S-boxes", test_sboxes);
    run("2.7   permutation P (and f = P(S(E(R) xor K)))", test_permutation_p);
    run("2.8   XOR with left half", test_xor_left_half);
    run("2.9   swap of the halves (and one full round)", test_swap);
    run("Table 4.2: all 16 rounds of the textbook example", test_textbook_example);
    run("Grabbe example 0123456789abcdef / 133457799bbcdff1", test_grabbe_example);
    run("NBS known-answer vectors", test_known_answers);
    run("weak keys, D(E(x)) = x, complementation property", test_properties);
    run("messages: PKCS#7, ECB, CBC (FIPS 81), wrong key", test_modes);
    run("avalanche effect (Table 4.3), key bit / parity bit", test_avalanche);
    run("trace table rows (input -> method -> output -> step)", test_trace);

    printf("\n%d checks, %d failed\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
