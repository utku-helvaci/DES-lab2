/*
 * lab2.c - CMPE455/CMSE456 Lab 2: DES on two computers, in one C file
 *
 *   gcc -o lab2 lab2.c
 *   ./lab2 steps             prints every DES step of the handout example
 *   ./lab2 server            Machine B: waits for Machine A on port 9000
 *   ./lab2 client ADDRESS    Machine A: connects to Machine B and sends first
 */
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

#define PORT 9000
#define MAX 1024                       /* longest message, in bytes */

typedef unsigned long long u64;        /* a number of up to 64 bits */

u64 key = 0x0f1571c947d9e859;          /* both machines know the key */
int show = 0;                          /* 1: every step prints its input and output */

/* ==================== tables of DES (bit 1 is the leftmost bit) ==================== */

/* 2.1 initial permutation */
int IP[64] = {
    58, 50, 42, 34, 26, 18, 10, 2,
    60, 52, 44, 36, 28, 20, 12, 4,
    62, 54, 46, 38, 30, 22, 14, 6,
    64, 56, 48, 40, 32, 24, 16, 8,
    57, 49, 41, 33, 25, 17,  9, 1,
    59, 51, 43, 35, 27, 19, 11, 3,
    61, 53, 45, 37, 29, 21, 13, 5,
    63, 55, 47, 39, 31, 23, 15, 7
};

/* 2.2 inverse initial permutation */
int IP_INV[64] = {
    40, 8, 48, 16, 56, 24, 64, 32,
    39, 7, 47, 15, 55, 23, 63, 31,
    38, 6, 46, 14, 54, 22, 62, 30,
    37, 5, 45, 13, 53, 21, 61, 29,
    36, 4, 44, 12, 52, 20, 60, 28,
    35, 3, 43, 11, 51, 19, 59, 27,
    34, 2, 42, 10, 50, 18, 58, 26,
    33, 1, 41,  9, 49, 17, 57, 25
};

/* 2.3 expansion/permutation */
int E[48] = {
    32,  1,  2,  3,  4,  5,
     4,  5,  6,  7,  8,  9,
     8,  9, 10, 11, 12, 13,
    12, 13, 14, 15, 16, 17,
    16, 17, 18, 19, 20, 21,
    20, 21, 22, 23, 24, 25,
    24, 25, 26, 27, 28, 29,
    28, 29, 30, 31, 32,  1
};

/* 2.4.1 permuted choice 1 */
int PC1[56] = {
    57, 49, 41, 33, 25, 17,  9,
     1, 58, 50, 42, 34, 26, 18,
    10,  2, 59, 51, 43, 35, 27,
    19, 11,  3, 60, 52, 44, 36,
    63, 55, 47, 39, 31, 23, 15,
     7, 62, 54, 46, 38, 30, 22,
    14,  6, 61, 53, 45, 37, 29,
    21, 13,  5, 28, 20, 12,  4
};

/* 2.4.2 number of left shifts in round 1 ... 16 (index 0 is not used) */
int SHIFTS[17] = { 0, 1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1 };

/* 2.4.3 permuted choice 2 */
int PC2[48] = {
    14, 17, 11, 24,  1,  5,
     3, 28, 15,  6, 21, 10,
    23, 19, 12,  4, 26,  8,
    16,  7, 27, 20, 13,  2,
    41, 52, 31, 37, 47, 55,
    30, 40, 51, 45, 33, 48,
    44, 49, 39, 56, 34, 53,
    46, 42, 50, 36, 29, 32
};

/* 2.7 permutation P */
int P[32] = {
    16,  7, 20, 21, 29, 12, 28, 17,
     1, 15, 23, 26,  5, 18, 31, 10,
     2,  8, 24, 14, 32, 27,  3,  9,
    19, 13, 30,  6, 22, 11,  4, 25
};

/* 2.6 the eight S-boxes: S[box][row][column] */
int S[8][4][16] = {
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

/* ==================== the DES steps ==================== */

/* Output bit i is input bit table[i]. All six permutations use this function. */
u64 permute(u64 input, int input_bits, int *table, int output_bits)
{
    u64 output = 0;
    for (int i = 0; i < output_bits; i++)
        output = (output << 1) | ((input >> (input_bits - table[i])) & 1);
    return output;
}

/* 2.1 Initial permutation (64 -> 64 bits) */
u64 initial_permutation(u64 block)
{
    u64 out = permute(block, 64, IP, 64);
    if (show) printf("2.1 initial_permutation: %016llx -> %016llx\n", block, out);
    return out;
}

/* 2.2 Inverse initial permutation (64 -> 64 bits) */
u64 inverse_initial_permutation(u64 block)
{
    u64 out = permute(block, 64, IP_INV, 64);
    if (show) printf("2.2 inverse_initial_permutation: %016llx -> %016llx\n", block, out);
    return out;
}

/* 2.3 Expansion/permutation (32 -> 48 bits) */
u64 expansion_permutation(u64 right)
{
    u64 out = permute(right, 32, E, 48);
    if (show) printf("2.3 expansion_permutation: %08llx -> %012llx\n", right, out);
    return out;
}

/* 2.4.1 Permuted choice 1 (64 -> 56 bits) */
u64 permuted_choice_1(u64 key64)
{
    u64 out = permute(key64, 64, PC1, 56);
    if (show) printf("2.4.1 permuted_choice_1: %016llx -> %014llx\n", key64, out);
    return out;
}

/* 2.4.2 Left circular shift of a 28-bit half by n positions */
u64 left_circular_shift(u64 half, int n)
{
    u64 out = ((half << n) | (half >> (28 - n))) & 0xfffffff;
    if (show) printf("2.4.2 left_circular_shift: %07llx << %d -> %07llx\n", half, n, out);
    return out;
}

/* 2.4.3 Permuted choice 2 (56 -> 48 bits) */
u64 permuted_choice_2(u64 cd)
{
    u64 out = permute(cd, 56, PC2, 48);
    if (show) printf("2.4.3 permuted_choice_2: %014llx -> %012llx\n", cd, out);
    return out;
}

/* 2.4 Round key generation: k[1] ... k[16] */
void generate_round_keys(u64 k[17])
{
    u64 cd = permuted_choice_1(key);
    u64 c = cd >> 28, d = cd & 0xfffffff;
    for (int i = 1; i <= 16; i++) {
        c = left_circular_shift(c, SHIFTS[i]);
        d = left_circular_shift(d, SHIFTS[i]);
        k[i] = permuted_choice_2((c << 28) | d);
    }
}

/* 2.5 XOR with round key (48 bits) */
u64 xor_round_key(u64 expanded, u64 round_key)
{
    u64 out = expanded ^ round_key;
    if (show) printf("2.5 xor_round_key: %012llx ^ %012llx -> %012llx\n", expanded, round_key, out);
    return out;
}

/* 2.6 S-boxes (48 -> 32 bits) */
u64 sbox_substitution(u64 input)
{
    u64 out = 0;
    for (int i = 0; i < 8; i++) {
        int six = (input >> (42 - 6 * i)) & 63;       /* the 6 bits of this S-box */
        int row = ((six >> 4) & 2) | (six & 1);       /* the two outer bits */
        int col = (six >> 1) & 15;                    /* the four inner bits */
        out = (out << 4) | S[i][row][col];
        if (show) printf("  S%d: row %d, column %d -> %d\n", i + 1, row, col, S[i][row][col]);
    }
    if (show) printf("2.6 sbox_substitution: %012llx -> %08llx\n", input, out);
    return out;
}

/* 2.7 Permutation P after the S-boxes (32 -> 32 bits) */
u64 permutation_p(u64 input)
{
    u64 out = permute(input, 32, P, 32);
    if (show) printf("2.7 permutation_p: %08llx -> %08llx\n", input, out);
    return out;
}

/* 2.8 XOR with the left half (32 bits) */
u64 xor_left_half(u64 left, u64 f)
{
    u64 out = left ^ f;
    if (show) printf("2.8 xor_left_half: %08llx ^ %08llx -> %08llx\n", left, f, out);
    return out;
}

/* 2.9 Swap of the halves of a 64-bit block */
u64 swap_halves(u64 block)
{
    u64 out = (block << 32) | (block >> 32);
    if (show) printf("2.9 swap_halves: %016llx -> %016llx\n", block, out);
    return out;
}

/* DES for one block. Decryption uses the round keys in reverse order. */
u64 des(u64 block, int decrypt)
{
    u64 k[17];
    generate_round_keys(k);

    block = initial_permutation(block);
    for (int i = 1; i <= 16; i++) {
        u64 left = block >> 32, right = block & 0xffffffff;
        if (show) printf("--- round %d ---\n", i);
        u64 x = expansion_permutation(right);
        x = xor_round_key(x, decrypt ? k[17 - i] : k[i]);
        x = sbox_substitution(x);
        x = permutation_p(x);
        left = xor_left_half(left, x);
        block = swap_halves((left << 32) | right);
    }
    block = swap_halves(block);                       /* the last swap, after round 16 */
    return inverse_initial_permutation(block);
}

/* ==================== messages ==================== */

/* 8 bytes -> one 64-bit block */
u64 get_block(char *bytes)
{
    u64 block = 0;
    for (int i = 0; i < 8; i++)
        block = (block << 8) | (bytes[i] & 255);
    return block;
}

/* one 64-bit block -> 8 bytes */
void put_block(u64 block, char *bytes)
{
    for (int i = 7; i >= 0; i--) {
        bytes[i] = block & 255;
        block >>= 8;
    }
}

void print_blocks(char *title, char *data, int length)
{
    printf("%s", title);
    for (int i = 0; i < length; i += 8)
        printf(" %016llx", get_block(data + i));
    printf("\n");
}

/* 2.10 Create: reads one line from the keyboard; returns 0 for :exit */
int create_message(char *text)
{
    memset(text, 0, MAX);                             /* zeros fill the last block */
    printf("[CREATE]  Enter your message: ");
    fflush(stdout);
    if (fgets(text, MAX, stdin) == NULL)
        return 0;
    text[strcspn(text, "\n")] = 0;
    return strcmp(text, ":exit") != 0;
}

/* 2.10 Encrypt: block by block; returns the length of the ciphertext */
int encrypt_message(char *text, char *cipher)
{
    int length = (strlen(text) / 8 + 1) * 8;
    for (int i = 0; i < length; i += 8)
        put_block(des(get_block(text + i), 0), cipher + i);
    print_blocks("[ENCRYPT]", cipher, length);
    return length;
}

/* 2.10 Send: the length, then the ciphertext */
void send_message(int sock, char *cipher, int length)
{
    int n = htonl(length);
    send(sock, &n, 4, 0);
    send(sock, cipher, length, 0);
    printf("[SEND] %d bytes sent\n\n", length);
}

/* 2.11 Receive: returns the length, or 0 when the other machine has left */
int receive_message(int sock, char *cipher)
{
    int n;
    printf("Waiting for a message...\n");
    if (recv(sock, &n, 4, MSG_WAITALL) != 4)
        return 0;
    n = ntohl(n);
    if (n <= 0 || n > MAX)
        return 0;
    if (recv(sock, cipher, n, MSG_WAITALL) != n)
        return 0;
    print_blocks("[RECEIVE]", cipher, n);
    return n;
}

/* 2.11 Decrypt: block by block */
void decrypt_message(char *cipher, int length, char *text)
{
    for (int i = 0; i < length; i += 8)
        put_block(des(get_block(cipher + i), 1), text + i);
    text[length] = 0;
    print_blocks("[DECRYPT]", text, length);
}

/* 2.11 Display */
void display_message(char *text)
{
    printf("[DISPLAY] %s\n\n", text);
}

/* The two machines take turns until one of them types :exit. */
void chat(int sock, int my_turn)
{
    char text[MAX + 1], cipher[MAX];
    int length;

    while (1) {
        if (my_turn) {
            if (!create_message(text))
                break;
            length = encrypt_message(text, cipher);
            send_message(sock, cipher, length);
        } else {
            length = receive_message(sock, cipher);
            if (length == 0)
                break;
            decrypt_message(cipher, length, text);
            display_message(text);
        }
        my_turn = !my_turn;
    }
    printf("The conversation is over.\n");
    close(sock);
}

/* ==================== main ==================== */

/* The example of the handout: every step of the encryption, then the decryption */
void steps(void)
{
    u64 plain = 0x02468aceeca86420;
    show = 1;
    u64 cipher = des(plain, 0);
    show = 0;
    printf("plaintext %016llx, ciphertext %016llx, decrypted %016llx\n",
           plain, cipher, des(cipher, 1));
}

int main(int argc, char *argv[])
{
    int sock = socket(AF_INET, SOCK_STREAM, 0), yes = 1;
    struct sockaddr_in address = { .sin_family = AF_INET, .sin_port = htons(PORT) };
    struct sockaddr *addr = (struct sockaddr *)&address;

    if (argc == 2 && strcmp(argv[1], "steps") == 0) {
        steps();
    } else if (argc == 2 && strcmp(argv[1], "server") == 0) {           /* Machine B */
        address.sin_addr.s_addr = INADDR_ANY;                           /* every interface */
        setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
        if (bind(sock, addr, sizeof address) < 0 || listen(sock, 1) < 0) {
            perror("server");
            return 1;
        }
        printf("Machine B: waiting for Machine A on port %d\n", PORT);
        sock = accept(sock, NULL, NULL);
        printf("Machine A is connected.\n\n");
        chat(sock, 0);
    } else if (argc == 3 && strcmp(argv[1], "client") == 0) {           /* Machine A */
        address.sin_addr.s_addr = inet_addr(argv[2]);
        if (connect(sock, addr, sizeof address) < 0) {
            perror("client");
            return 1;
        }
        printf("Machine A: connected to Machine B (%s)\n\n", argv[2]);
        chat(sock, 1);
    } else {
        printf("usage: ./lab2 steps | ./lab2 server | ./lab2 client ADDRESS\n");
    }
    return 0;
}
