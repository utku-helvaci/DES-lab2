#!/usr/bin/env bash
# docker/demo.sh - automated run of the distributed application on two
# Docker "computers" (see docker-compose.yml):
#
#   1. builds the image, starts machine-a (172.28.10.10) and machine-b (172.28.10.20)
#   2. records the network settings of both machines and pings B from A
#   3. starts tcpdump on the LAN bridge des-lan0 (the "cable" between them)
#   4. machine-b runs tcpServer, machine-a runs tcpClient -s 172.28.10.20; their
#      messages come from test_examples/messages_machine_{a,b}.txt
#   5. checks that every message was displayed unchanged on the OTHER machine,
#      that no plaintext was seen on the wire and that the captured payload is
#      exactly the ciphertext printed by the sender
#
# Output: test_examples/docker_run/   (logs, network settings, capture)
# Usage:  docker/demo.sh [--down]      --down stops the machines afterwards
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=test_examples/docker_run
A_MSG=test_examples/messages_machine_a.txt
B_MSG=test_examples/messages_machine_b.txt
mkdir -p "$OUT"
exec > >(tee "$OUT/demo_output.txt") 2>&1     # keep a copy of this console output
fail() { echo "FAIL: $*"; exit 1; }
step() { printf '\n==> %s\n' "$*"; }

step "Building the image and starting the two machines"
docker compose build -q
docker compose up -d machine-a machine-b
docker rm -f des-sniffer > /dev/null 2>&1 || true

step "Network settings of the two machines"
for m in machine-a machine-b; do
    docker exec "$m" sh -c 'echo "hostname: $(hostname)"; ip -4 -br addr show eth0;
                            ip -br link show eth0; ip route' | tee "$OUT/${m}_network.txt"
done
docker network inspect des_lan > "$OUT/docker_network_inspect.json"
docker exec machine-a ping -c 3 172.28.10.20 | tee "$OUT/ping_machine-a_to_machine-b.txt"

step "Starting the packet capture on the LAN bridge des-lan0"
docker run -d --name des-sniffer --network host --cap-add NET_RAW --cap-add NET_ADMIN \
    des-lab2:latest tcpdump -i des-lan0 -nn -U -w /tmp/des_lan.pcap 'tcp port 9000' > /dev/null
sleep 1

step "machine-b: tcpServer   |   machine-a: tcpClient -s 172.28.10.20"
docker exec -i machine-b tcpServer -1 -n < "$B_MSG" > "$OUT/machine-b_tcpServer.log" 2>&1 &
server=$!
sleep 1
docker exec -i machine-a tcpClient -n -s 172.28.10.20 < "$A_MSG" \
    > "$OUT/machine-a_tcpClient.log" 2>&1
wait "$server"
sleep 1

step "Stopping the capture"
docker stop des-sniffer > /dev/null
docker cp des-sniffer:/tmp/des_lan.pcap "$OUT/des_lan.pcap" > /dev/null
docker rm des-sniffer > /dev/null
docker run --rm -v "$PWD/$OUT:/cap:ro" des-lab2:latest \
    tcpdump -r /cap/des_lan.pcap -nn -X 2> /dev/null > "$OUT/des_lan_capture.txt"
echo "$(grep -c ' IP ' "$OUT/des_lan_capture.txt") packets captured -> $OUT/des_lan_capture.txt"

step "Checks"
expect_displayed() {   # $1 sent lines, $2 receiver log, $3 label used by the receiver
    while IFS= read -r line; do
        grep -qF "[DISPLAY] Message from the $3: \"$line\"" "$2" ||
            fail "'$line' was not displayed by the receiver"
    done < "$1"
}
expect_displayed "$A_MSG" "$OUT/machine-b_tcpServer.log" client
expect_displayed "$B_MSG" "$OUT/machine-a_tcpClient.log" Server
echo "PASS  all $(wc -l < "$A_MSG") messages of machine-a were displayed unchanged on machine-b"
echo "PASS  all $(wc -l < "$B_MSG") messages of machine-b were displayed unchanged on machine-a"

python3 - "$OUT" "$A_MSG" "$B_MSG" <<'PY'
import re, sys
out, *scripts = sys.argv[1:]
wire = open(f"{out}/des_lan.pcap", "rb").read()
# 1. no plaintext message may appear in the captured packets
for script in scripts:
    for line in open(script, encoding="utf-8").read().splitlines():
        if line.encode() in wire:
            sys.exit(f"FAIL: plaintext seen on the wire: {line!r}")
print("PASS  no plaintext message appears in the captured packets")
# 2. every ciphertext printed in the logs is found byte-for-byte on the wire
found = set()
for log in ("machine-a_tcpClient.log", "machine-b_tcpServer.log"):
    text = open(f"{out}/{log}", encoding="utf-8").read()
    for block in re.finditer(r"ciphertext\s+\d+ B  ([0-9a-f ]+(?:\n {29}[0-9a-f ]+)*)", text):
        cipher = bytes.fromhex(re.sub(r"\s", "", block.group(1)))
        if cipher not in wire:
            sys.exit(f"FAIL: ciphertext from {log} not found on the wire")
        found.add(cipher)
print(f"PASS  all {len(found)} ciphertexts printed in the logs were found "
      "byte-for-byte in the capture")
PY

echo
echo "Logs and capture: $OUT/"
if [ "${1:-}" = "--down" ]; then
    docker compose down
else
    echo "The machines are still running (docker compose down stops them)."
fi
