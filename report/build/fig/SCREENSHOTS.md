# How the images in `report/build/fig` were made

Every screenshot in this folder is a real run of our programs: real `gdb`, real
`tcpServer`/`tcpClient` inside the two Docker machines, real `tcpdump`. Only the
typing and the window capture were automated, by `tools/screenshots.py`. It
runs everything on a separate virtual screen (Xvfb), so nothing appears on the
desktop and the desktop is never captured.

There are two stages:

```
tools/screenshots.py    ->  report/figures/*.png     raw window captures
report/make_figures.py  ->  report/build/fig/*.png   trimmed copies, diagrams, chart
```

To make all of them again:

```sh
make all                                    # gdb needs bin/des_trace built with -g
docker compose up -d machine-a machine-b    # only needed for the net_*.png screenshots
python3 tools/screenshots.py debugger       # dbg_*.png  (about 1 minute)
python3 tools/screenshots.py network        # net_*.png  (about 30 seconds)
python3 report/make_figures.py              # trim + diagrams + chart into report/build/fig
```

Tools used: `Xvfb`, `xterm`, `xdotool`, ImageMagick (`import`, `convert`), `gdb`,
Docker, Graphviz (`dot`) and Python with matplotlib.

---

## 1. The building blocks

`tools/screenshots.py` does the same five things for every screenshot.

**1. Start a private virtual screen** (display `:91`, 2600 x 1700 pixels):

```sh
Xvfb :91 -screen 0 2600x1700x24 -nolisten tcp &
export DISPLAY=:91 LANG=C.UTF-8 LC_ALL=C.UTF-8
```

**2. Open a terminal window** with a title, a size in characters and a position
in pixels, running one command. The `-xrm` options set the 16 terminal colours
(listed as `PALETTE` in the script).

```sh
xterm -T "<title>" -geometry <cols>x<rows>+<x>+<y> \
      -fa "DejaVu Sans Mono" -fs 10 -bg "#1b1d1e" -fg "#e6e6e6" -cr "#e6e6e6" \
      -b 6 -u8 +sb -xrm "XTerm*color0: #2e3436" ... -e <command>
```

**3. Type into the window**, line by line, as a person would:

```sh
WIN=$(xdotool search --sync --name '^<title>$')     # window id
xdotool windowfocus --sync "$WIN"
xdotool type --delay 8 -- '<text>'
xdotool key Return
sleep 0.4                                          # 0.4 - 2.6 s: let the program answer
```

**4. Capture the window**:

```sh
import -window "$WIN" report/figures/<name>.png
```

**5. Trim the empty terminal area** (done later by `report/make_figures.py`;
the result is the file in this folder):

```sh
convert report/figures/<name>.png -trim +repage \
        -bordercolor "#1b1d1e" -border 10 report/build/fig/<name>.png
```

---

## 2. Debugger screenshots: `dbg_*.png`

One window, opened once for all 15 screenshots:

```sh
xterm -T "gdb - DES step by step" -geometry 128x46+0+0 ... \
      -e gdb -q -tui --args bin/des_trace -q -k 0f1571c947d9e859 -i 02468aceeca86420
```

`gdb -tui` is GDB's text interface: source code on top, with the current line
highlighted, and the command window below it. `bin/des_trace -q` encrypts the
handout's example once and prints only the ciphertext.

These five settings are typed first:

```gdb
set debuginfod enabled off     # no "download debug info?" question
set confirm off
set pagination off
set output-radix 16            # print function arguments in hexadecimal
tui window height src 22       # source window: 22 lines
```

Each screenshot then follows the same recipe:

1. `tbreak des.c:<line>` sets a one-time breakpoint on the `return` line of the
   step function. At that line both the input (the parameter) and the output
   (the local variable) exist.
2. `run` (first time) or `continue` runs until the breakpoint.
3. `display/z <variable>` adds a watch. `/z` means hexadecimal with leading
   zeros, so a 48-bit value appears as `0x0000...` in a 64-bit variable.
4. The window is captured.
5. `undisplay` removes the watches before the next step.

The line numbers are not typed by hand. The script finds them in the source
(`ret()` and `line_of()` in `tools/screenshots.py`), so they follow the code if
it changes. For the current `src/des.c` they are:

| File | Lab item | Typed (after the previous screenshot) | Stops at |
|---|---|---|---|
| `dbg_01_pc1.png` | 2.4.1 | `tbreak des.c:194`, `run`, `display/z key`, `display/z cd` | `return cd;` in `des_permuted_choice_1` |
| `dbg_02_shift.png` | 2.4.2 | `tbreak des.c:210`, `continue`, `display/z half`, `display amount`, `display/z rotated` | `return rotated;` in `des_left_circular_shift` (first call: C0 -> C1) |
| `dbg_03_pc2.png` | 2.4.3 | `tbreak des.c:217`, `continue`, `display/z cd`, `display/z subkey` | `return subkey;` in `des_permuted_choice_2` (K1) |
| `dbg_04_all_round_keys.png` | 2.4 | `tbreak des_trace_main.c:129`, `continue`, `print/x ks.subkey` | `main()`, just before `des_process_block()`: all 16 round keys |
| `dbg_05_ip.png` | 2.1 | `tbreak des.c:171`, `continue`, `display/z block`, `display/z permuted` | `return permuted;` in `des_initial_permutation` |
| `dbg_06_expansion.png` | 2.3 | `tbreak des.c:185`, `continue`, `display/z right`, `display/z expanded` | `return expanded;` in `des_expansion_permutation` (round 1) |
| `dbg_07_xor_round_key.png` | 2.5 | `tbreak des.c:254`, `continue`, `display/z expanded`, `display/z subkey`, `display/z mixed` | `return mixed;` in `des_xor_round_key` |
| `dbg_08_sbox_loop.png` | 2.6 | `break des.c:277`, `continue`, `display box + 1`, `display/t six_bits`, `display four_bits`, `display/z output`, `continue`, `continue` | the line `output = (output << 4) \| four_bits;` inside the S-box loop: it stops for S1, S2 and S3. Afterwards `delete` removes this normal breakpoint. |
| `dbg_09_sbox_result.png` | 2.6 | `tbreak des.c:279`, `continue`, `display/z input48`, `display/z output` | `return output;` in `des_sbox_substitution` |
| `dbg_10_permutation_p.png` | 2.7 | `tbreak des.c:286`, `continue`, `display/z input`, `display/z permuted` | `return permuted;` in `des_permutation_p` |
| `dbg_11_xor_left_half.png` | 2.8 | `tbreak des.c:311`, `continue`, `display/z left`, `display/z f_output`, `display/z new_right` | `return new_right;` in `des_xor_left_half` |
| `dbg_12_swap.png` | 2.9 | `tbreak des.c:318`, `continue`, `display/z block`, `display/z swapped` | `return swapped;` in `des_swap_halves` (end of round 1) |
| `dbg_13_round_step_mode.png` | 2.9 | `finish`, `display/z left`, `display/z right`, `display/z f_output`, `display/z new_right`, `display/z before_swap`, `display/z after_swap`, `next` | step mode in `des_round()`: `finish` returns from `des_swap_halves`, then one `next` fills `after_swap` |
| `dbg_14_inverse_ip.png` | 2.2 | `tbreak des.c:177`, `continue`, `display/z block`, `display/z restored` | `return restored;` in `des_inverse_initial_permutation` |
| `dbg_15_result.png` | - | `tbreak des_trace_main.c:131`, `continue`, `display/z input`, `display/z key`, `display/z output` | `main()` after the encryption: plaintext, key and ciphertext |

At the end the script types `continue` and `quit`.

Notes:

- `display/t` (binary) drops leading zeros, so `10001` in `dbg_08` is the
  6-bit value `010001`.
- In `dbg_13`, `after_swap` shows leftover stack content (`0x0000000100000001`)
  until `next` executes its line. This is normal debugger behaviour for a
  variable that has not been assigned yet.

---

## 3. Network screenshots: `net_*.png`

The two Docker machines must be running (`docker compose up -d machine-a
machine-b`). Three windows are opened:

| Window title | Geometry | Command |
|---|---|---|
| `machine-a` | `100x52+0+0` | `docker exec -it machine-a bash` |
| `machine-b` | `100x52+830+0` | `docker exec -it machine-b bash` |
| `sniffer` | `160x44+0+900` | `docker compose --profile capture run --rm sniffer tcpdump -i des-lan0 -nn -X 'tcp port 9000 and (tcp[tcpflags] & tcp-push != 0)'` |

`tcpdump` runs on `des-lan0`, the bridge that connects the two machines. The
filter keeps only TCP packets of port 9000 that carry data. `-X` prints every
byte in hex and ASCII.

Then, in this order:

| # | Typed in | Text typed | Screenshots taken afterwards |
|---|---|---|---|
| 1 | machine-a | `hostname; ip -4 -br addr show eth0; ip route \| head -2` | |
| 2 | machine-a | `ping -c 2 172.28.10.20` | |
| 3 | machine-b | `hostname; ip -4 -br addr show eth0; ip route \| head -2` | |
| 4 | machine-b | `ping -c 2 172.28.10.10` | `net_01_settings_machine-a.png`, `net_02_settings_machine-b.png` |
| 5 | both | `clear` | |
| 6 | machine-b | `tcpServer` | |
| 7 | machine-a | `tcpClient -s 172.28.10.20` | `net_03_server_listening.png` (machine-b) |
| 8 | machine-a | `Hello Machine B, this is Machine A.` | `net_04_machine-a_create_encrypt_send.png`, `net_05_machine-b_receive_decrypt_display.png` |
| 9 | machine-b | `Hi Machine A! Teşekkürler, your message arrived intact.` | `net_06_machine-b_create_encrypt_send.png`, `net_07_machine-a_receive_decrypt_display.png`, `net_08_packet_capture.png` (sniffer) |
| 10 | machine-a | `:exit` | `net_09_machine-a_exit.png`, `net_10_machine-b_exit.png` |

Lines 8 and 9 are the chat messages: they are typed at the programs'
`Enter your message:` prompt, not into the shell. Afterwards the script closes
the windows and removes the sniffer container that `docker compose run` leaves
behind:

```sh
docker rm -f $(docker ps -aq --filter name=des-lab2-sniffer-run)
```

The IV is random, so a new run shows different IV and ciphertext bytes.
Decryption gives the same text every time.

---

## 4. Images that are not screenshots

| File | How it was made |
|---|---|
| `des_structure.png`, `des_round.png`, `network.png` | Graphviz drawings. Their sources are the `.dot` files in this folder, written by `report/make_figures.py`: `dot -Tpng -Gdpi=220 -o des_structure.png des_structure.dot` (the same for the other two). |
| `avalanche.png` | matplotlib chart drawn by `avalanche()` in `report/make_figures.py` from `test_examples/avalanche_plaintext_bit4.csv` and `test_examples/avalanche_key_bit4.csv` (made by `bin/des_avalanche -P 4 -f csv` and `bin/des_avalanche -K 4 -f csv`). |
| `net_settings_both.png` | The two settings screenshots stacked, for the reduced report: `convert net_01_settings_machine-a.png -size 10x16 xc:white net_02_settings_machine-b.png -background white -append net_settings_both.png` |

---

## 5. Which report uses which image

| Image | Full report | Reduced report |
|---|---|---|
| `dbg_01` - `dbg_03`, `dbg_05` - `dbg_08`, `dbg_10`, `dbg_11`, `dbg_13`, `dbg_14` | yes | yes |
| `dbg_04`, `dbg_09`, `dbg_12`, `dbg_15` | yes | - |
| `net_06`, `net_07`, `net_08`, `network.png` | yes | yes |
| `net_01`, `net_02` | yes | as `net_settings_both.png` |
| `net_03`, `net_04`, `net_05`, `net_09`, `des_structure.png`, `des_round.png`, `avalanche.png` | yes | - |
| `net_10` | - | - |

---

## 6. Taking the screenshots by hand instead

The same commands work in an ordinary terminal on your own desktop, with your
usual screenshot tool (for example Spectacle or Flameshot on Linux, or
Win+Shift+S on Windows):

1. `make all`, then `gdb -tui --args bin/des_trace -q`, and type the commands
   from section 2.
2. `docker compose up -d`, then two terminals with
   `docker exec -it machine-b tcpServer` and
   `docker exec -it machine-a tcpClient -s 172.28.10.20`, and type the
   messages.

For screenshots of a graphical IDE, use Visual Studio Code with the launch
configuration "DES steps: textbook example" (`.vscode/launch.json`). Put
breakpoints on the same `return` lines and add the same variables to the WATCH
panel.
