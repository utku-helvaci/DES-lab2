/*
 * des_trace_main.c - bin/des_trace
 *
 * Runs DES on ONE 64-bit block and prints every step of the algorithm as
 *     input -> method (C function) -> output -> DES step (lab item)
 * i.e. the table requested for the lab report.
 *
 *   des_trace                               textbook example (Table 4.2)
 *   des_trace -f summary                    Table 4.2 layout: round, Ki, Li, Ri
 *   des_trace -k 133457799bbcdff1 -i 0123456789abcdef
 *   des_trace -d -i da02ce3a89ecac3b        decryption (keys used K16..K1)
 *   des_trace -s                            + the 8 S-box look-ups of every round
 *   des_trace -f csv > trace.csv            formats: table, csv, md, summary
 *   des_trace -q                            print only the output block
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "des.h"
#include "des_trace.h"
#include "des_util.h"

#define DEFAULT_KEY   "0f1571c947d9e859"   /* textbook example */
#define DEFAULT_BLOCK "02468aceeca86420"

static void usage(const char *prog)
{
    fprintf(stderr,
            "usage: %s [-k KEY] [-i BLOCK] [-d] [-s] [-f table|csv|md|summary] [-q]\n"
            "  -k KEY    64-bit key, 16 hex digits      (default %s)\n"
            "  -i BLOCK  64-bit input, 16 hex digits    (default %s)\n"
            "  -d        decrypt instead of encrypt\n"
            "  -s        also list the 8 S-box look-ups of every round\n"
            "  -f FMT    table (default), csv, md, or summary (Table 4.2 layout)\n"
            "  -q        quiet: print only the resulting block\n",
            prog, DEFAULT_KEY, DEFAULT_BLOCK);
}

static void print_summary(uint64_t key, uint64_t input, des_direction dir)
{
    des_key_schedule ks;
    uint64_t states[DES_ROUNDS];
    char subkey[24];

    des_generate_round_keys(key, &ks);
    uint64_t ip = des_initial_permutation(input);
    uint64_t output = des_process_block(input, &ks, dir, states);

    printf("DES %s, key %016llx, input %016llx\n",
           dir == DES_ENCRYPT ? "encryption" : "decryption",
           (unsigned long long)key, (unsigned long long)input);
    printf("(subkeys shown as eight 6-bit values in hex, as in the textbook)\n\n");
    printf("Round  Key  Ki                Li        Ri\n");
    printf("IP                            %08x  %08x\n",
           des_left_half(ip), des_right_half(ip));
    for (int round = 1; round <= DES_ROUNDS; round++) {
        int k = (dir == DES_ENCRYPT) ? round : DES_ROUNDS + 1 - round;
        des_format_subkey(subkey, sizeof subkey, ks.subkey[k - 1]);
        printf("%5d  K%-3d %s  %08x  %08x\n", round, k, subkey,
               des_left_half(states[round - 1]), des_right_half(states[round - 1]));
    }
    printf("IP-1                          %08x  %08x\n",
           des_left_half(output), des_right_half(output));
    printf("\n%s = %016llx\n", dir == DES_ENCRYPT ? "Ciphertext" : "Plaintext",
           (unsigned long long)output);
}

int main(int argc, char *argv[])
{
    const char *key_text = DEFAULT_KEY;
    const char *block_text = DEFAULT_BLOCK;
    const char *format = "table";
    int decrypt = 0, sbox_detail = 0, quiet = 0, opt;

    while ((opt = getopt(argc, argv, "k:i:dsf:qh")) != -1) {
        switch (opt) {
        case 'k': key_text = optarg; break;
        case 'i': block_text = optarg; break;
        case 'd': decrypt = 1; break;
        case 's': sbox_detail = 1; break;
        case 'f': format = optarg; break;
        case 'q': quiet = 1; break;
        default: usage(argv[0]); return opt == 'h' ? 0 : 2;
        }
    }

    uint64_t key, input;
    if (des_parse_hex64(key_text, &key) != 0) {
        fprintf(stderr, "error: key must be 16 hex digits: %s\n", key_text);
        return 2;
    }
    if (des_parse_hex64(block_text, &input) != 0) {
        fprintf(stderr, "error: block must be 16 hex digits: %s\n", block_text);
        return 2;
    }
    des_direction dir = decrypt ? DES_DECRYPT : DES_ENCRYPT;

    if (strcmp(format, "summary") == 0 && !quiet) {
        print_summary(key, input, dir);
        return 0;
    }

    des_trace_printer printer;
    if (strcmp(format, "table") == 0)
        des_trace_printer_init(&printer, stdout, DES_TRACE_TABLE);
    else if (strcmp(format, "csv") == 0)
        des_trace_printer_init(&printer, stdout, DES_TRACE_CSV);
    else if (strcmp(format, "md") == 0)
        des_trace_printer_init(&printer, stdout, DES_TRACE_MARKDOWN);
    else {
        usage(argv[0]);
        return 2;
    }

    if (!quiet) {
        if (printer.format == DES_TRACE_TABLE)
            printf("DES %s of %016llx with key %016llx: key schedule, IP, 16 rounds, IP^-1\n",
                   decrypt ? "decryption" : "encryption",
                   (unsigned long long)input, (unsigned long long)key);
        des_trace_printer_header(&printer);
        des_trace_start(des_trace_printer_row, &printer, sbox_detail, 0);
    }

    /* The whole cipher in two calls - good places for debugger breakpoints. */
    des_key_schedule ks;
    des_generate_round_keys(key, &ks);                            /* 2.4       */
    uint64_t output = des_process_block(input, &ks, dir, NULL);   /* 2.1 - 2.9 */

    if (quiet) {
        printf("%016llx\n", (unsigned long long)output);
        return 0;
    }
    des_trace_stop();
    des_trace_printer_footer(&printer);
    if (printer.format == DES_TRACE_TABLE)
        printf("Result: %s = %016llx\n", decrypt ? "plaintext" : "ciphertext",
               (unsigned long long)output);
    return 0;
}
