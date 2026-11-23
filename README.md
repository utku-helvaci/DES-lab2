# Lab 2 - DES on Two Computers (CMPE455/CMSE456)

DES (FIPS 46-3) in C, one function per DES step, used by a two-machine chat:
each side **creates** a message, **encrypts** it (DES-CBC), **sends** it, **receives**
the answer, **decrypts** it and **displays** it. The two "computers" are two Docker
containers on a virtual LAN; the same programs also run on two real machines.

The report is `report/DES_Lab2_Report.pdf` (editable: `.docx`). A shorter version in a
plainer style is `report/Reduced_Report.pdf`; `report/REDUCED_REPORT_CHANGES.md` lists
what it leaves out.

## Layout

| Path | Contents |
|---|---|
| `src/des.c`, `des.h` | the cipher: one function per step (IP, IP^-1, E, PC-1, shifts, PC-2, XOR, S-boxes, P, XOR-left, swap) |
| `src/des_trace.c` | the *input -> method -> output -> DES step* table |
| `src/des_modes.c` | PKCS#7 padding, ECB and CBC for messages of any length |
| `src/des_chat.c`, `net.c` | create/encrypt/send and receive/decrypt/display, TCP framing |
| `src/tcpServer.c`, `tcpClient.c` | Machine B and Machine A (the starter code extended with DES) |
| `src/des_trace_main.c`, `des_avalanche.c` | tools for the step table and the avalanche tables |
| `tests/` | unit tests (`test_des.c`), cross-check with pycryptodome/OpenSSL, loopback network test |
| `docker/`, `docker-compose.yml` | the two machines (`machine-a` 172.28.10.10, `machine-b` 172.28.10.20) |
| `debug/des_watch.py` | GDB script that reads every step's input/output with breakpoints |
| `test_examples/` | all test inputs and outputs, Docker run logs and packet capture |
| `tools/`, `report/` | scripts that regenerate the screenshots, test examples, report and zip |
| `Lab2_DES/` | the course starter code (unchanged) |

## Build and test (Linux)

```sh
make            # bin/tcpServer bin/tcpClient bin/des_trace bin/des_avalanche bin/des_test
make test       # unit tests of every DES step (25 080 checks)
make check      # + cross-check (python3 + pycryptodome, openssl) + loopback network test
```

## Run on two machines (Docker)

```sh
docker compose up -d --build                          # start machine-a and machine-b
docker exec -it machine-b tcpServer                   # terminal 1: Machine B (server)
docker exec -it machine-a tcpClient -s 172.28.10.20   # terminal 2: Machine A (client)
docker compose --profile capture up sniffer           # optional: watch the packets on the LAN
docker compose down
make demo       # scripted conversation + packet capture + automatic checks
```

The client sends first; then the two sides take turns. `:exit` (or Ctrl-D) ends the
conversation. Both sides need the same key: `-k <16 hex digits>` or `$DES_KEY`
(default: the textbook key `0f1571c947d9e859`). `-t` prints the full DES step table
for the first block of every message; `-m ecb` switches from CBC to ECB.

## Run on two real computers

1. Same network; find Machine B's IPv4 address (`ip -4 addr`, or `ipconfig` on Windows).
   `tcpServer` prints its addresses at start-up.
2. Open TCP port 9000 on Machine B (`sudo ufw allow 9000/tcp`).
3. Machine B: `./bin/tcpServer -k KEY`  -  Machine A: `./bin/tcpClient -s <IP of B> -k KEY`.

Campus Wi-Fi often isolates clients from each other; use a cable or a hotspot then.

## DES step tables

```sh
bin/des_trace                         # textbook example: key 0f1571c947d9e859, P = 02468aceeca86420
bin/des_trace -s                      # + the 8 S-box look-ups of every round
bin/des_trace -f summary              # handout Table 4.2 layout (round, Ki, Li, Ri)
bin/des_trace -d -i da02ce3a89ecac3b  # decryption
bin/des_trace -f csv > trace.csv      # formats: table, csv, md, summary
bin/des_avalanche -P 4                # handout Table 4.3 (plaintext bit 4 flipped)
bin/des_avalanche -K 4                # Table 4.4 (key bit 4 flipped)
```

## Debugging

* **VS Code**: open this folder, choose *DES steps: textbook example* in *Run and Debug*
  (needs the C/C++ extension). Put breakpoints on the `return ...;` line of the step
  functions in `src/des.c` and add the parameter and the returned variable to *Watch*.
* **GDB**: `gdb -tui --args bin/des_trace -q`, then e.g. `break des_initial_permutation`,
  `run`, `next`, `display/z block`, `display/z permuted`.
* `gdb -q -batch -x debug/des_watch.py --args bin/des_trace -q` prints every step's
  input and output as seen by the debugger.

## Regenerating the evidence

```sh
make examples      # test_examples/ (traces, avalanche, test logs, gdb output)
make demo          # test_examples/docker_run/ (needs Docker)
make screenshots   # report/figures/ (needs Xvfb, xterm, xdotool, ImageMagick; runs on a virtual display)
make report        # both reports at once: report/DES_Lab2_Report.* and report/Reduced_Report.*
                   # (python-docx, graphviz, matplotlib, LibreOffice)
make full-report   # only the full report;  make reduced-report: only the reduced one
make dist          # dist/Lab2_DES_Full_Report.zip and dist/Lab2_DES_Reduced_Report.zip
                   # (REPORT=full or REPORT=reduced: only one of them)
```

The reduced zip has only the reduced report, `src/`, `bin/` (without `des_test`),
`docker/` and the project files: no `debug/`, `starter_original/`, `test_examples/`,
`tests/` or `tools/`. Without `tests/`, `make` skips `bin/des_test` and the Docker build
skips the unit tests.

How every screenshot and figure was made (all commands): `report/build/fig/SCREENSHOTS.md`.
Cover-page fields are in `report/cover.json`. The report script starts LibreOffice
with OpenCL disabled (`SAL_DISABLE_OPENCL=1`): its OpenCL probe crashes with some
GPU drivers.
