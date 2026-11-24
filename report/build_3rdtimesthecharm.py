#!/usr/bin/env python3
"""
report/build_3rdtimesthecharm.py - builds the document "3rdtimesthecharm".

The reduced report (report/build_reduced_report.py) with a simpler program: one C file,
3rdtimesthecharm/lab2.c, and no debugger. Each step shows its code and the line it prints.
Like the edited Reduced_Report.docx it has no "Same as the handout?" column in Table 3 and
no paragraph about real computers in Section 4.

    python3 tools/screenshots_3rdtimesthecharm.py     the screenshots (only if lab2.c changed)
    python3 report/build_3rdtimesthecharm.py          the document

Output: report/3rdtimesthecharm.docx and report/3rdtimesthecharm.pdf
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import build_reduced_report as reduced  # noqa: E402  Arial-only layout and the cover page
import make_figures  # noqa: E402
from build_reduced_report import full  # noqa: E402  shared helpers and two-pass build

FOLDER = os.path.join(full.ROOT, "3rdtimesthecharm")
DOCX = os.path.join(HERE, "3rdtimesthecharm.docx")
PDF = os.path.join(HERE, "3rdtimesthecharm.pdf")
STEP_WIDTH, MACHINE_WIDTH = 15.5, 13.9      # cm; the same size of letters in both

STEP_NAMES = {"2.1": "Initial permutation", "2.2": "Inverse initial permutation",
              "2.3": "Expansion/permutation", "2.4.1": "Permuted choice 1",
              "2.4.2": "Left circular shift", "2.4.3": "Permuted choice 2",
              "2.5": "XOR with round key", "2.6": "S-boxes", "2.7": "Permutation P",
              "2.8": "XOR with left half", "2.9": "Swap of the halves"}


def source(name):
    with open(os.path.join(FOLDER, name), encoding="utf-8") as f:
        return f.read()


def picture(name):
    return os.path.join(FOLDER, "screenshots", name + ".png")


def run_steps():
    """Compiles lab2.c, runs `./lab2 steps`; returns [(item, method, input, output)]."""
    with tempfile.TemporaryDirectory() as tmp:
        exe = os.path.join(tmp, "lab2")
        subprocess.run(["gcc", "-o", exe, os.path.join(FOLDER, "lab2.c")], check=True)
        text = subprocess.run([exe, "steps"], check=True, capture_output=True, text=True).stdout
    return re.findall(r"^(2[\d.]+) (\w+): (.+) -> ([0-9a-f]+)$", text, re.M)


def table_4_2(rows):
    """Round, Ki in 6-bit groups, Li, Ri - checked against the handout's Table 4.2."""
    out = lambda item: [r[3] for r in rows if r[0] == item]
    halves = lambda block: (block[:8], block[8:])
    groups = lambda k: "".join(f"{int(k, 16) >> s & 63:02x}" for s in range(42, -1, -6))
    table = [("IP", "", *halves(out("2.1")[0]))]
    for i, (k, block) in enumerate(zip(out("2.4.3"), out("2.9")), 1):
        table.append((str(i), groups(k), *halves(block)))
    table.append(("IP-1", "", *halves(out("2.2")[0])))
    typos = {("6", 1), ("7", 1), ("IP-1", 2)}          # the three typing errors of the handout
    for row, h in zip(table, full.HANDOUT_42):
        printed = (h[0], *h[1:])
        for i, (ours, theirs) in enumerate(zip(row, printed)):
            assert (ours == theirs) != ((row[0], i) in typos), (row, printed)
    assert len(table) == len(full.HANDOUT_42) == 18
    return table


def network_drawing(env):
    blue, fill, gray = make_figures.BLUE, make_figures.BLUE_FILL, make_figures.GRAY
    small = lambda text: f'<font point-size="9" color="{gray}">{text}</font>'
    make_figures.render("network_3rdtimesthecharm", f"""graph NET {{
  graph [fontname="Arial", fontsize=11, bgcolor="white", pad=0.1, nodesep=1.9, ranksep=0.4];
  node  [shape=box, style="rounded,filled", fontname="Arial", fontsize=10.5,
         fontcolor="{make_figures.INK}", fillcolor="{fill}", color="{blue}", penwidth=1.3,
         margin="0.16,0.08"];
  edge  [color="#4a4a48", penwidth=1.3, fontname="Arial", fontsize=9.5, fontcolor="#3a3a38"];
  subgraph cluster_host {{
    label="Host computer (Linux, Docker Engine) - docker-compose.yml"; labeljust=l;
    style="rounded"; color="#9a9993"; fontcolor="{gray}";
    A [label=<<b>machine-a</b>  (container = computer A)<br/>hostname machine-a<br/>eth0  172.28.20.10/24<br/>./lab2 client 172.28.20.20<br/>{small("Machine A: sends first")}>];
    BR [label=<<b>des_lan</b> (virtual Ethernet switch)<br/>subnet 172.28.20.0/24<br/>gateway 172.28.20.1>, fillcolor="#f3f3f1", color="#8a8984"];
    B [label=<<b>machine-b</b>  (container = computer B)<br/>hostname machine-b<br/>eth0  172.28.20.20/24<br/>./lab2 server   (port 9000)<br/>{small("Machine B: receives first")}>];
    {{ rank=same; A; B; }}
  }}
  A -- B [style=bold, color="{blue}", fontcolor="{blue}",
          label=<TCP, port 9000<br/>length | DES ciphertext>];
  A -- BR [label="  veth pair"];
  B -- BR [label="  veth pair"];
}}""", env)


def build(R):
    rows = run_steps()
    reduced.cover_page(R)

    R.heading("Outline", 1, new_page=True, toc=False)
    R.para("Section 1 states the problem. Section 2 shows the work done and is numbered like "
           "the tasks of the lab sheet: 2.1 - 2.9 are the DES steps, 2.10 and 2.11 the sending "
           "and receiving of messages between the two machines. Section 3 compares the results "
           "with the handout, Section 4 describes the network settings and Section 5 the tests. "
           "The appendix contains the source code.")
    R.toc()

    # ------------------------------------------------------------------ 1
    R.heading("1  Problem definition", 1, new_page=True)
    R.para("DES (Data Encryption Standard) is a block cipher. It encrypts data in 64-bit blocks "
           "with a 64-bit key, of which 56 bits are used, in 16 rounds. Encryption and "
           "decryption use the same algorithm; decryption only applies the round keys in "
           "reverse order [1].")
    R.para("In this lab we implement DES in C and use it in a distributed application. Two "
           "processes run on two computers, and each one can create a message, encrypt it, "
           "send it, receive a message, decrypt it and display it. The displayed text must be "
           "the same as the text typed on the other computer. Every DES step has to be checked. "
           "As the lecturer asked, every step is its own function, and a table shows the input, "
           "the method, the output and the DES step of each one. We started from the course's "
           "`tcpServer.c` and `tcpClient.c` [2] and put everything into one C file, `lab2.c`. "
           "The two computers are two Docker containers on one virtual network (Section 4).")

    # ------------------------------------------------------------------ 2
    R.heading("2  Work done", 1, new_page=True)
    R.para("The whole program is one C file, `lab2.c`, which is printed in the appendix. Every "
           "DES step is a small function ({tab:functions}) that takes its input as parameters "
           "and returns its output. All six permutations (IP, IP^{-1}, E, P, PC-1, PC-2) use "
           "the same function, `permute()`, each with its own table from the DES standard [1].")
    R.table(["Lab item", "DES step", "C function", "Bits in -> out"], [
        ["2.1", "Initial permutation", "`initial_permutation(block)`", "64 -> 64"],
        ["2.2", "Inverse initial permutation", "`inverse_initial_permutation(block)`", "64 -> 64"],
        ["2.3", "Expansion/permutation", "`expansion_permutation(right)`", "32 -> 48"],
        ["2.4.1", "Permuted choice 1", "`permuted_choice_1(key64)`", "64 -> 56"],
        ["2.4.2", "Left circular shift", "`left_circular_shift(half, n)`", "28 -> 28"],
        ["2.4.3", "Permuted choice 2", "`permuted_choice_2(cd)`", "56 -> 48"],
        ["2.5", "XOR with round key", "`xor_round_key(expanded, round_key)`", "48 -> 48"],
        ["2.6", "S-boxes", "`sbox_substitution(input)`", "48 -> 32"],
        ["2.7", "Permutation P", "`permutation_p(input)`", "32 -> 32"],
        ["2.8", "XOR with left half", "`xor_left_half(left, f)`", "32 -> 32"],
        ["2.9", "Swap of the halves", "`swap_halves(block)`", "64 -> 64"],
        ["2.10", "Create, encrypt, send", "`create_message`, `encrypt_message`, `send_message`", "text -> ciphertext"],
        ["2.11", "Receive, decrypt, display", "`receive_message`, `decrypt_message`, `display_message`", "ciphertext -> text"],
    ], [1.5, 4.0, 8.4, 3.1], caption="The lab items and the functions that implement them.",
        label="tab:functions", size=8.5, center=(0,))
    R.para("The examples use the key and the plaintext of the handout: K = `0f1571c947d9e859` "
           "and P = `02468aceeca86420`. When the program is started with `./lab2 steps`, every "
           "function prints its input and its output. Each screenshot shows the code of a step "
           "and the line that it prints.")

    R.heading("2.1  Initial permutation", 2)
    R.para("The initial permutation is done once, before the first round. It moves every bit "
           "of the 64-bit block to a new position given by a fixed table: output bit 1 is "
           "input bit 58, output bit 2 is input bit 50, and so on. The result is split into "
           "the left half L0 = `5a005a00` and the right half R0 = `3cf03c0f`, the first row "
           "of the handout's Table 4.2.")
    R.figure(picture("2_1_initial_permutation"), STEP_WIDTH)

    R.heading("2.2  Inverse initial permutation", 2)
    R.para("The inverse initial permutation is the last step and undoes the initial "
           "permutation. Its input is R16 | L16 = `25896490 75e8fd8f`, its output the "
           "ciphertext `da02ce3a89ecac3b`.")
    R.figure(picture("2_2_inverse_initial_permutation"), STEP_WIDTH)

    R.heading("2.3  Expansion/permutation", 2)
    R.para("The right half has 32 bits but the round key has 48, so E expands the half to 48 "
           "bits: the two edge bits of every 4-bit group are copied into the neighbouring "
           "groups. In round 1, R0 = `3cf03c0f` becomes `9f97a01f805e`.")
    R.figure(picture("2_3_expansion_permutation"), STEP_WIDTH)

    R.heading("2.4  Round key generation", 2)
    R.para("The 16 round keys are made from the key in three steps. **Permuted choice 1** "
           "removes the 8 parity bits and splits the other 56 bits into two 28-bit halves, "
           "C0 = `68fc44a` and D0 = `1113e96`. Before every round both halves are **rotated "
           "left** by one position (rounds 1, 2, 9 and 16) or by two positions (all other "
           "rounds); in round 1, C0 becomes C1 = `d1f8894`. **Permuted choice 2** then picks "
           "48 of the 56 bits as the round key: K1 = `7833c320da70`, which is "
           "`1e030f03080d2930` when written in 6-bit groups as in the handout. The three "
           "screenshots show these three steps in this order; the last one lists all 16 round "
           "keys.")
    R.figure(picture("2_4_1_permuted_choice_1"), STEP_WIDTH)
    R.figure(picture("2_4_2_left_circular_shift"), STEP_WIDTH)
    R.figure(picture("2_4_3_permuted_choice_2"), STEP_WIDTH)

    R.heading("2.5  XOR with round key", 2)
    R.para("The expanded right half is XORed with the round key of the round. In round 1: "
           "`9f97a01f805e` XOR `7833c320da70` = `e7a4633f5a2e`.")
    R.figure(picture("2_5_xor_round_key"), STEP_WIDTH)

    R.heading("2.6  S-boxes", 2)
    R.para("The S-boxes turn the 48 bits back into 32. The 48 bits are cut into eight 6-bit "
           "groups, one for each S-box. The two outer bits of a group select the row and the "
           "four inner bits the column of the S-box table; the number found there is the 4-bit "
           "output. In round 1, S1 receives `111001`: row 3, column 12, output 10 (`1010`). The "
           "screenshot shows the row, the column and the output of all eight S-boxes in "
           "round 1.")
    R.figure(picture("2_6_sbox_substitution"), STEP_WIDTH)

    R.heading("2.7  Permutation P after the S-boxes", 2)
    R.para("P reorders the 32 output bits of the S-boxes. Its result is the round function f: "
           "in round 1, `a32f11c2` becomes f = `e0d27245`.")
    R.figure(picture("2_7_permutation_p"), STEP_WIDTH)

    R.heading("2.8  XOR with the left half", 2)
    R.para("The output of f is XORed with the left half, and the result becomes the new right "
           "half. In round 1: `5a005a00` XOR `e0d27245` = `bad22845`, which is R1 in Table 4.2.")
    R.figure(picture("2_8_xor_left_half"), STEP_WIDTH)

    R.heading("2.9  Swap of the halves", 2)
    R.para("At the end of every round the two halves change places, so L1 = R0 = `3cf03c0f` "
           "and R1 = `bad22845`. After round 16 the halves are swapped once more, before "
           "IP^{-1}.")
    R.figure(picture("2_9_swap_halves"), STEP_WIDTH)

    R.heading("2.10  Create, encrypt and send a message", 2)
    R.para("The same program runs on both machines: `./lab2 server` on Machine B and "
           "`./lab2 client` with the address of Machine B on Machine A. After connecting, the "
           "two machines take turns, and the client starts. On its turn a machine:")
    R.bullets([
        "**creates** the message: `create_message()` reads a line from the keyboard;",
        "**encrypts** it: `encrypt_message()` cuts the text into blocks of 8 bytes, fills the "
        "last block with zeros and encrypts every block with DES;",
        "**sends** it: `send_message()` sends the length and the ciphertext over TCP. The key "
        "is never sent; both machines know it.",
    ])
    R.para("We changed four things in the starter code. Server and client are one program, and "
           "the first argument selects the role. The server listens on all network interfaces "
           "(0.0.0.0) instead of 127.0.0.1, so that another computer can connect. Messages are "
           "sent together with their length, because ciphertext can contain zero bytes and TCP "
           "can split a message. Whole lines are read with `fgets()` instead of single words "
           "with `scanf`.")
    R.para("The screenshot shows Machine A: it creates, encrypts and sends its message, then "
           "receives, decrypts and displays the answer of Machine B.")
    R.figure(picture("2_10_machine-a"), MACHINE_WIDTH)

    R.heading("2.11  Receive, decrypt and display a message", 2)
    R.para("On the other turn a machine **receives** the ciphertext (`receive_message()`), "
           "**decrypts** it block by block (`decrypt_message()`) and **displays** the text "
           "(`display_message()`). Typing `:exit` ends the conversation on both machines.")
    R.para("The screenshot shows Machine B: it receives, decrypts and displays the message of "
           "Machine A, then creates, encrypts and sends its answer. The Turkish letters arrive "
           "unchanged.")
    R.figure(picture("2_11_machine-b"), MACHINE_WIDTH)
    R.para("The tcpdump capture below was taken on Machine B while these two messages were "
           "sent. It contains only the length (4 bytes) and the ciphertext of each message; the "
           "text of the messages does not appear anywhere.")
    R.figure(picture("2_11_packet_capture"), MACHINE_WIDTH)

    # ------------------------------------------------------------------ 3
    R.heading("3  Results", 1, new_page=True)
    R.heading("3.1  Input, method, output and DES step", 2)
    R.para("{tab:steps} is the table the lecturer asked for. It shows the first call of every "
           "step: the input to the method, the method name, the method output and the DES step. "
           f"`./lab2 steps` prints the same for all {len(rows)} calls of one encryption. In the "
           "table, `^` means XOR and `<<` a circular shift to the left.")
    called = lambda item: [r for r in rows if r[0] == item]
    first = [called("2.4.1")[0], *called("2.4.2")[:2], called("2.4.3")[0], called("2.1")[0],
             *(called(f"2.{i}")[0] for i in (3, 5, 6, 7, 8, 9)), called("2.9")[-1],
             called("2.2")[0]]
    notes = {1: " of C", 2: " of D", 11: " (after round 16)"}
    in_round_1 = {1, 2, 3, 5, 6, 7, 8, 9, 10}
    R.table(full.STEP_HEADER, [["1" if n in in_round_1 else "-", given, method, output,
                                full.breakable(f"{item} {STEP_NAMES[item]}{notes.get(n, '')}")]
                               for n, (item, method, given, output) in enumerate(first)],
            [1.1, 4.4, 4.3, 2.9, 4.3], caption="Every DES step of the handout example (first call; round "
            "1 where the step belongs to a round).", label="tab:steps", mono=(1, 2, 3),
            size=7.5, center=(0,), keep_together=True)

    R.heading("3.2  Encryption and decryption of the handout example", 2)
    R.para("{tab:t42} compares our round keys and halves with Table 4.2 of the handout. All "
           "values are the same. Three entries of the handout contain typing errors: K6 and K7 "
           "are printed with the letter l instead of the digit 1, and the last row shows "
           "`25896490` (which is R16) instead of `da02ce3a` as the left half of the ciphertext.")
    R.table(["Round", "Ki (6-bit groups)", "Li", "Ri"],
            [[cell or "-" for cell in row] for row in table_4_2(rows)], [1.8, 5.2, 3.4, 3.4],
            caption="Our results for the handout example.", label="tab:t42", mono=(1, 2, 3),
            size=8, center=(0,), keep_together=True)
    R.para("Decryption runs the same function, `des()`, with the round keys from K16 down to K1 "
           "and gives back the plaintext `02468aceeca86420`. The screenshot shows the function "
           "and the result.")
    R.figure(picture("3_2_des"), STEP_WIDTH)

    # ------------------------------------------------------------------ 4
    R.heading("4  Settings of the distributed system", 1)
    R.para("The two computers are two Docker containers. Each one has its own host name, "
           "network interface, IP address and processes, and both are connected to the same "
           "virtual Ethernet network `des_lan` [3]. The settings are in `docker-compose.yml`. "
           "Both machines run the same program, and the DES key is a constant in it.")
    R.figure("network_3rdtimesthecharm.png", 15.0)
    R.table(["", "machine-a", "machine-b"], [
        ["Role", "Machine A, sends first", "Machine B, receives first"],
        ["Host name", "machine-a", "machine-b"],
        ["IP address", "172.28.20.10/24", "172.28.20.20/24"],
        ["Program and port", "`./lab2 client 172.28.20.20`", "`./lab2 server`, port 9000"],
    ], [3.6, 6.7, 6.7], caption="Settings of the two machines.", label="tab:net",
        size=9, bold_col0=True)
    R.code("docker compose up -d --build                                # start both machines\n"
           "docker compose exec machine-b ./lab2 server                 # terminal 1: Machine B\n"
           "docker compose exec machine-a ./lab2 client 172.28.20.20    # terminal 2: Machine A\n"
           "docker compose down                                         # stop both machines",
           size=8)
    R.para("The screenshots show the host name, IP address and route of machine-a and "
           "machine-b, and a ping from each machine to the other.")
    R.figure(picture("4_settings_machine-a"), 11.0)
    R.figure(picture("4_settings_machine-b"), 11.0)

    # ------------------------------------------------------------------ 5
    R.heading("5  Testing and the choices we made", 1)
    R.para("**Tests.**", after=2, keep=True)
    R.bullets([
        "DES: all round keys and halves of the handout's example are the same as in the "
        "handout, and decrypting the ciphertext gives the plaintext again.",
        "Network: on the two Docker machines every message arrives unchanged on the other "
        "machine, and the packet capture contains no plaintext.",
    ])
    R.para("**Choices.**", after=2, keep=True)
    R.bullets([
        "One C file instead of several: the program is short, is compiled with one command "
        "(`gcc -o lab2 lab2.c`) and is the same on both machines.",
        "Docker containers instead of two laptops or virtual machines: one command starts both "
        "machines, and the network traffic can be recorded. The program itself does not depend "
        "on Docker.",
        "Every 8-byte block is encrypted on its own (ECB). This is the simplest way; its "
        "weakness is that equal blocks of a message give equal blocks of ciphertext.",
        "64-bit integers instead of arrays of bits: every value is printed as one hexadecimal "
        "number that can be compared with the handout directly.",
    ])
    R.para("**Our opinion.** Writing each step as its own function made the testing easy, "
           "because every value could be compared with the handout one step at a time. The "
           "harder part was the networking rather than DES: the starter code had to be changed "
           "before encrypted data could travel between two computers.")

    # ------------------------------------------------------------------ 6, 7
    R.heading("6  Conclusion", 1)
    R.para("We implemented DES in one C file with one function per step and compared the steps "
           "with the handout's example: all values agree, and the program even shows three "
           "typing errors in the handout. Two machines exchange messages that are created, "
           "encrypted, sent, received, decrypted and displayed unchanged, while only ciphertext "
           "travels over the network. DES itself is no longer secure: in January 1999 a DES key "
           "was broken publicly in 22 hours and 15 minutes, and AES has replaced DES [1]. For "
           "learning how a block cipher works, however, DES is a good example.")

    R.heading("7  References", 1)
    full.references(R, [
        "*Data Encryption Standard (DES)*, CMPE455 lecture notes, "
        "https://staff.emu.edu.tr/gurcuoz/Documents/CMPE455 Ch08_2_DES",
        "CMPE455/CMSE456 lab handouts *Lab 2 Task. DES on Two Computers* and *A DES Example*, "
        "and the starter code tcpServer.c and tcpClient.c, 2026.",
        "Docker Inc., *Bridge network driver*, Docker documentation (docs.docker.com).",
    ])

    # ------------------------------------------------------------------ appendix
    R.heading("Appendix  Source code", 1, new_page=True)
    R.para("The program, `lab2.c`, and the two files that describe the Docker machines.")
    for name in ("lab2.c", "Dockerfile", "docker-compose.yml"):
        R.heading(name, 2, toc=False)
        R.code(source(name), size=7)


if __name__ == "__main__":
    with make_figures.arial_fonts() as env:
        network_drawing(env)
        full.build_document(build, DOCX, PDF, report=reduced.ArialReport, env=env)
    reduced.check_fonts(PDF)
