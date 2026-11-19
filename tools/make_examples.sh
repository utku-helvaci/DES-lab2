#!/usr/bin/env bash
# tools/make_examples.sh - regenerates every file in test_examples/ from the
# current executables (traces, avalanche tables, test logs, debugger output).
#   make examples         (docker/demo.sh adds test_examples/docker_run/)
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=test_examples
mkdir -p "$OUT"
TB_KEY=0f1571c947d9e859; TB_P=02468aceeca86420; TB_C=da02ce3a89ecac3b

# textbook example (handout Table 4.2): full step tables, CSV for the report
bin/des_trace -k $TB_KEY -i $TB_P            > "$OUT/trace_textbook_encrypt.txt"
bin/des_trace -k $TB_KEY -i $TB_P -f csv     > "$OUT/trace_textbook_encrypt.csv"
bin/des_trace -k $TB_KEY -i $TB_P -f md      > "$OUT/trace_textbook_encrypt.md"
bin/des_trace -k $TB_KEY -i $TB_P -s         > "$OUT/trace_textbook_encrypt_with_sboxes.txt"
bin/des_trace -k $TB_KEY -i $TB_P -s -f csv  > "$OUT/trace_textbook_encrypt_with_sboxes.csv"
bin/des_trace -k $TB_KEY -i $TB_C -d         > "$OUT/trace_textbook_decrypt.txt"
bin/des_trace -k $TB_KEY -i $TB_C -d -f csv  > "$OUT/trace_textbook_decrypt.csv"
bin/des_trace -k $TB_KEY -i $TB_P -f summary > "$OUT/summary_textbook_table_4_2.txt"
bin/des_trace -k $TB_KEY -i $TB_C -d -f summary > "$OUT/summary_textbook_decrypt.txt"

# Grabbe's "DES Algorithm Illustrated" example
bin/des_trace -k 133457799bbcdff1 -i 0123456789abcdef -s > "$OUT/trace_grabbe_encrypt.txt"
bin/des_trace -k 133457799bbcdff1 -i 0123456789abcdef -f summary > "$OUT/summary_grabbe.txt"

# avalanche effect (handout Tables 4.3 / 4.4)
bin/des_avalanche -k $TB_KEY -i $TB_P -P 4 > "$OUT/avalanche_plaintext_bit4_table_4_3.txt"
bin/des_avalanche -k $TB_KEY -i $TB_P -K 4 > "$OUT/avalanche_key_bit4_table_4_4.txt"
bin/des_avalanche -k $TB_KEY -i $TB_P -K 8 > "$OUT/avalanche_key_parity_bit8.txt"
bin/des_avalanche -k $TB_KEY -i $TB_P -P 4 -f csv > "$OUT/avalanche_plaintext_bit4.csv"
bin/des_avalanche -k $TB_KEY -i $TB_P -K 4 -f csv > "$OUT/avalanche_key_bit4.csv"

# tests
bin/des_test > "$OUT/unit_tests.txt"
python3 tests/crosscheck.py 300 > "$OUT/crosscheck.txt"
rm -rf "$OUT/loopback"
KEEP_LOGS="$OUT/loopback" tests/test_loopback.sh > "$OUT/loopback_test.txt"

# what the debugger sees at every step function (breakpoints, no trace code)
gdb -q -batch -x debug/des_watch.py --args bin/des_trace -q 2>/dev/null |
    grep -v '^\[' > "$OUT/gdb_watch_steps.txt"

echo "test examples written to $OUT/"
ls "$OUT"
