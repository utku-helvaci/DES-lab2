/*
 * des_avalanche.c - bin/des_avalanche
 *
 * Reproduces the avalanche tables of the lab handout: two encryptions that
 * differ in ONE bit (of the plaintext or of the key) are run side by side and
 * the number of differing bits of Li|Ri is printed after every round.
 *
 *   des_avalanche -P 4      Table 4.3: plaintext 02468ace... vs 12468ace...
 *   des_avalanche -K 4      Table 4.4: key 0f1571c9... vs 1f1571c9...
 *   des_avalanche -K 8      key parity bit: PC-1 drops it, nothing changes
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "des.h"
#include "des_util.h"

#define DEFAULT_KEY   "0f1571c947d9e859"
#define DEFAULT_BLOCK "02468aceeca86420"

static void usage(const char *prog)
{
    fprintf(stderr,
            "usage: %s [-k KEY] [-i BLOCK] (-P BIT | -K BIT) [-f table|csv]\n"
            "  -P BIT  flip plaintext bit BIT (1 = left-most bit)\n"
            "  -K BIT  flip key bit BIT       (1 = left-most bit)\n",
            prog);
}

static void bar(int n)
{
    for (int i = 0; i < n; i++)
        putchar('#');
}

int main(int argc, char *argv[])
{
    const char *key_text = DEFAULT_KEY, *block_text = DEFAULT_BLOCK;
    const char *format = "table";
    int plain_bit = 0, key_bit = 0, opt;

    while ((opt = getopt(argc, argv, "k:i:P:K:f:h")) != -1) {
        switch (opt) {
        case 'k': key_text = optarg; break;
        case 'i': block_text = optarg; break;
        case 'P': plain_bit = atoi(optarg); break;
        case 'K': key_bit = atoi(optarg); break;
        case 'f': format = optarg; break;
        default: usage(argv[0]); return opt == 'h' ? 0 : 2;
        }
    }

    uint64_t key1, block1;
    if (des_parse_hex64(key_text, &key1) || des_parse_hex64(block_text, &block1)) {
        fprintf(stderr, "error: key and block must be 16 hex digits\n");
        return 2;
    }
    if ((plain_bit == 0) == (key_bit == 0) || plain_bit < 0 || plain_bit > 64 ||
        key_bit < 0 || key_bit > 64) {
        usage(argv[0]);
        return 2;
    }

    uint64_t key2 = key_bit ? des_flip_bit(key1, key_bit) : key1;
    uint64_t block2 = plain_bit ? des_flip_bit(block1, plain_bit) : block1;

    des_key_schedule ks1, ks2;
    uint64_t s1[DES_ROUNDS], s2[DES_ROUNDS];
    des_generate_round_keys(key1, &ks1);
    des_generate_round_keys(key2, &ks2);
    uint64_t c1 = des_process_block(block1, &ks1, DES_ENCRYPT, s1);
    uint64_t c2 = des_process_block(block2, &ks2, DES_ENCRYPT, s2);

    int csv = strcmp(format, "csv") == 0;
    if (csv) {
        printf("round,first,second,differing_bits\n");
        printf("0,%016llx,%016llx,%d\n", (unsigned long long)block1,
               (unsigned long long)block2, des_bit_difference(block1, block2));
        for (int r = 0; r < DES_ROUNDS; r++)
            printf("%d,%016llx,%016llx,%d\n", r + 1, (unsigned long long)s1[r],
                   (unsigned long long)s2[r], des_bit_difference(s1[r], s2[r]));
        printf("IP-1,%016llx,%016llx,%d\n", (unsigned long long)c1,
               (unsigned long long)c2, des_bit_difference(c1, c2));
        return 0;
    }

    printf("Avalanche effect in DES: %s bit %d flipped\n",
           plain_bit ? "plaintext" : "key", plain_bit ? plain_bit : key_bit);
    printf("  key       %016llx   %016llx\n", (unsigned long long)key1,
           (unsigned long long)key2);
    printf("  plaintext %016llx   %016llx\n\n", (unsigned long long)block1,
           (unsigned long long)block2);
    printf("Round  first Li|Ri        second Li|Ri       diff  \n");
    printf("-----  ----------------   ----------------   ----\n");

    int d = des_bit_difference(block1, block2);
    printf("    0  %016llx   %016llx   %4d  ", (unsigned long long)block1,
           (unsigned long long)block2, d);
    bar(d);
    putchar('\n');
    for (int r = 0; r < DES_ROUNDS; r++) {
        d = des_bit_difference(s1[r], s2[r]);
        printf("%5d  %016llx   %016llx   %4d  ", r + 1, (unsigned long long)s1[r],
               (unsigned long long)s2[r], d);
        bar(d);
        putchar('\n');
    }
    d = des_bit_difference(c1, c2);
    printf(" IP-1  %016llx   %016llx   %4d  ", (unsigned long long)c1,
           (unsigned long long)c2, d);
    bar(d);
    printf("\n\nCiphertexts differ in %d of 64 bits.\n", d);
    return 0;
}
