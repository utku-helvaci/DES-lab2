#!/usr/bin/env bash
# test_loopback.sh - runs tcpServer and tcpClient on THIS computer (127.0.0.1)
# with the scripted messages in test_examples/ and checks that
#   1. every message created on one side is displayed unchanged on the other;
#   2. a client with a WRONG key is rejected (padding check fails);
#   3. ECB leaks the repeated "AAAA..." blocks while CBC does not.
# The two-machine version of this test is docker/demo.sh.
set -euo pipefail
cd "$(dirname "$0")/.."

BIN=./bin
PORT=${PORT:-9555}
A=test_examples/messages_machine_a.txt
B=test_examples/messages_machine_b.txt
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
fail() { echo "FAIL: $*"; exit 1; }

run_pair() {   # $1 = name, rest = extra client options
    local name=$1; shift
    "$BIN/tcpServer" -1 -n -p "$PORT" < "$B" > "$OUT/$name-server.log" 2>&1 &
    local server=$!
    "$BIN/tcpClient" -n -p "$PORT" -r 20 "$@" < "$A" > "$OUT/$name-client.log" 2>&1 || true
    wait "$server" || true
}

expect_displayed() {   # $1 = file with the sent lines, $2 = receiver log, $3 = label
    while IFS= read -r line; do
        grep -qF "[DISPLAY] Message from the $3: \"$line\"" "$2" ||
            fail "'$line' was not displayed by the receiver ($2)"
    done < "$1"
}

# 1. normal conversation (CBC)
run_pair cbc
expect_displayed "$A" "$OUT/cbc-server.log" client
expect_displayed "$B" "$OUT/cbc-client.log" Server
grep -q "The client ended the conversation" "$OUT/cbc-server.log" || fail "no clean end"
echo "PASS  CBC conversation: $(wc -l < "$A") + $(wc -l < "$B") messages arrived unchanged"

# 2. wrong key on the client side
"$BIN/tcpServer" -1 -n -p "$PORT" < "$B" > "$OUT/wrong-server.log" 2>&1 &
server=$!
"$BIN/tcpClient" -n -p "$PORT" -r 20 -m ecb -k 1f1571c947d9e859 < "$A" \
    > "$OUT/wrong-client.log" 2>&1 || true
wait "$server" || true
grep -q "padding check failed" "$OUT/wrong-server.log" || fail "wrong key not detected"
grep -q "\[DISPLAY\]" "$OUT/wrong-server.log" && fail "wrong key: something was displayed"
echo "PASS  wrong key: receiver refuses to display the message"

# 3. ECB vs CBC on the 32 x 'A' message (4 equal plaintext blocks)
run_pair ecb -m ecb
blocks() {   # distinct ciphertext blocks of the 32 x 'A' message in a sender log
    awk '/"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"/{f=1} f&&/ciphertext/{print; exit}' "$1" |
        grep -oE '[0-9a-f]{16}' | head -4 | sort -u | wc -l
}
ecb_unique=$(blocks "$OUT/ecb-client.log")
cbc_unique=$(blocks "$OUT/cbc-client.log")
[ "$ecb_unique" -eq 1 ] || fail "ECB should repeat the ciphertext block ($ecb_unique unique)"
[ "$cbc_unique" -eq 4 ] || fail "CBC should give 4 different blocks ($cbc_unique unique)"
echo "PASS  ECB: 4 equal plaintext blocks -> $ecb_unique distinct ciphertext block;" \
     "CBC -> $cbc_unique distinct blocks"

if [ -n "${KEEP_LOGS:-}" ]; then
    mkdir -p "$KEEP_LOGS"
    cp "$OUT"/*.log "$KEEP_LOGS"/
fi
echo "loopback tests passed"
