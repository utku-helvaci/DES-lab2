#!/usr/bin/env python3
"""
report/build_reduced_report.py - builds the "Reduced Report".

A shorter version of the Lab 2 report, written in the plainer style of a sample
report the team preferred: one short numbered section per lab item with a few
sentences, the code and one screenshot. Everything the lab sheet asks for is
still there; report/REDUCED_REPORT_CHANGES.md lists what was removed or
shortened compared with the full report (report/build_report.py).

    make report            (both reports)   or   make reduced-report   (only this one)

Output: report/Reduced_Report.docx and report/Reduced_Report.pdf
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True       # no __pycache__ folder next to the report

import build_report as full  # noqa: E402  shared data helpers, layout and two-pass build
from build_report import (ACCENT, GRAY, NOTE_FILL, STEP_HEADER, STEP_WIDTHS,  # noqa: E402
                          Cm, Pt, WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX)

DOCX = os.path.join(HERE, "Reduced_Report.docx")
PDF = os.path.join(HERE, "Reduced_Report.pdf")
LOGO = os.path.join(HERE, "assets", "emu_logo.png")
SHOT = 13.5          # width of a debugger screenshot, cm


def code(R, *functions, path="src/des.c"):
    R.code("\n\n".join(full.c_function(path, f) for f in functions))


def cover_page(R):
    c = R.cover

    def line(parts, size, after=3, before=0, color=None):
        p = R.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(after)
        p.paragraph_format.space_before = Pt(before)
        for text, bold in parts:
            r = p.add_run(text)
            r.font.size = Pt(size)
            r.bold = bold
            if color is not None:
                r.font.color.rgb = color
            if text.startswith("["):
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW

    if os.path.exists(LOGO):
        p = R.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(24)
        p.paragraph_format.space_after = Pt(18)
        p.add_run().add_picture(LOGO, width=Cm(4.6))
    line([(c["university"], True)], 16, after=4)
    line([(c["department"], False)], 13)
    line([(c["program"], False)], 13, after=22)
    line([(c["course"], True)], 12.5, after=22, color=ACCENT)
    line([(f'{c["lab"]} Report', False)], 13, after=2)
    line([(c["subject"], True)], 24, after=30, color=ACCENT)
    line([("Team members", True)], 11, after=1)
    for member in c["team_members"]:
        line([(member, False)], 11, after=1)
    line([("Lecturer: ", True), (c["lecturer"], False)], 11, before=10)
    line([("Lab Assistant: ", True), (c["lab_assistant"], False)], 11)
    line([("Year: ", True), (c["year"], False), ("     Semester: ", True),
          (c["semester"], False)], 11, before=10)
    line([("City: ", True), (c["city"], False), ("     Country: ", True),
          (c["country"], False)], 11)


def build(R):
    tr = full.trace()

    cover_page(R)

    # ------------------------------------------------------------------ outline
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
           "reverse order [1, 2].")
    R.para("In this lab we implement DES in C and use it in a distributed application. Two "
           "processes run on two computers, and each one can create a message, encrypt it, "
           "send it, receive a message, decrypt it and display it. The displayed text must be "
           "the same as the text typed on the other computer. Every DES step has to be checked "
           "in the debugger. As the lecturer asked, every step is its own function, and a table "
           "shows the input, the method, the output and the DES step of each one. We started "
           "from the course's `tcpServer.c` and `tcpClient.c` [5]. The two computers are two "
           "Docker containers on one virtual network (Section 4).")

    # ------------------------------------------------------------------ 2
    R.heading("2  Work done", 1, new_page=True)
    R.para("Every DES step is a small function in `src/des.c` ({tab:functions}). It takes its "
           "input as parameters and returns its output, so both can be watched in the debugger. "
           "All six permutations (IP, IP^{-1}, E, P, PC-1, PC-2) use the same helper, "
           "`des_permute()`, each with its own table from the DES standard [1].")
    code(R, "des_permute")
    R.table(["Lab item", "DES step", "C function", "Bits in -> out"], [
        ["2.1", "Initial permutation", "`des_initial_permutation(block)`", "64 -> 64"],
        ["2.2", "Inverse initial permutation", "`des_inverse_initial_permutation(block)`", "64 -> 64"],
        ["2.3", "Expansion/permutation", "`des_expansion_permutation(right)`", "32 -> 48"],
        ["2.4.1", "Permuted choice 1", "`des_permuted_choice_1(key)`", "64 -> 56"],
        ["2.4.2", "Left circular shift", "`des_left_circular_shift(half, amount)`", "28 -> 28"],
        ["2.4.3", "Permuted choice 2", "`des_permuted_choice_2(cd)`", "56 -> 48"],
        ["2.5", "XOR with round key", "`des_xor_round_key(expanded, subkey)`", "48 -> 48"],
        ["2.6", "S-boxes", "`des_sbox_substitution(input48)`", "48 -> 32"],
        ["2.7", "Permutation P", "`des_permutation_p(input)`", "32 -> 32"],
        ["2.8", "XOR with left half", "`des_xor_left_half(left, f_output)`", "32 -> 32"],
        ["2.9", "Swap of the halves", "`des_swap_halves(block)`", "64 -> 64"],
        ["2.10", "Create, encrypt, send", "`create_message`, `encrypt_message`, `send_message`", "text -> frame"],
        ["2.11", "Receive, decrypt, display", "`receive_message`, `decrypt_message`, `display_message`", "frame -> text"],
    ], [1.5, 4.0, 8.6, 2.9], caption="The lab items and the functions that implement them.",
        label="tab:functions", size=8.5, center=(0,))
    R.para("The examples use the key and the plaintext of the handout: K = `0f1571c947d9e859` "
           "and P = `02468aceeca86420`. Each screenshot shows GDB stopped at the end of the "
           "step function, with its input and output variables watched (`display/z` prints "
           "them in hexadecimal).")

    R.heading("2.1  Initial permutation", 2)
    R.para("The initial permutation is done once, before the first round. It moves every bit "
           "of the 64-bit block to a new position given by a fixed table: output bit 1 is "
           "input bit 58, output bit 2 is input bit 50, and so on. The result is split into "
           "the left half L0 = `5a005a00` and the right half R0 = `3cf03c0f`, the first row "
           "of the handout's Table 4.2.")
    code(R, "des_initial_permutation")
    R.figure("dbg_05_ip.png", SHOT, "`des_initial_permutation()`: block 02468aceeca86420 "
             "becomes 5a005a003cf03c0f.")

    R.heading("2.2  Inverse initial permutation", 2)
    R.para("The inverse initial permutation is the last step and undoes the initial "
           "permutation. Its input is R16 | L16 = `25896490 75e8fd8f`, its output the "
           "ciphertext `da02ce3a89ecac3b`.")
    code(R, "des_inverse_initial_permutation")
    R.figure("dbg_14_inverse_ip.png", SHOT, "`des_inverse_initial_permutation()`: "
             "2589649075e8fd8f becomes the ciphertext da02ce3a89ecac3b.")

    R.heading("2.3  Expansion/permutation", 2)
    R.para("The right half has 32 bits but the round key has 48, so E expands the half to 48 "
           "bits: the two edge bits of every 4-bit group are copied into the neighbouring "
           "groups. In round 1, R0 = `3cf03c0f` becomes `9f97a01f805e`.")
    code(R, "des_expansion_permutation")
    R.figure("dbg_06_expansion.png", SHOT, "`des_expansion_permutation()` in round 1.")

    R.heading("2.4  Round key generation", 2)
    R.para("The 16 round keys are made from the key in three steps. **Permuted choice 1** "
           "removes the 8 parity bits and splits the other 56 bits into two 28-bit halves, "
           "C0 = `68fc44a` and D0 = `1113e96`. Before every round both halves are **rotated "
           "left** by one position (rounds 1, 2, 9 and 16) or by two positions (all other "
           "rounds). **Permuted choice 2** then picks 48 of the 56 bits as the round key: "
           "K1 = `7833c320da70`, which is `1e030f03080d2930` when written in 6-bit groups as in "
           "the handout.")
    code(R, "des_left_circular_shift", "des_generate_round_keys")
    R.figure("dbg_01_pc1.png", 12.5, "Permuted choice 1: the key becomes C0 | D0.")
    R.figure("dbg_02_shift.png", 12.5, "Left circular shift in round 1: C0 = 68fc44a, rotated "
             "by 1, gives C1 = d1f8894.")
    R.figure("dbg_03_pc2.png", 12.5, "Permuted choice 2 in round 1: C1 | D1 becomes "
             "K1 = 7833c320da70.")

    R.heading("2.5  XOR with round key", 2)
    R.para("The expanded right half is XORed with the round key of the round. In round 1: "
           "`9f97a01f805e` XOR `7833c320da70` = `e7a4633f5a2e`.")
    code(R, "des_xor_round_key")
    R.figure("dbg_07_xor_round_key.png", SHOT, "`des_xor_round_key()` in round 1.")

    R.heading("2.6  S-boxes", 2)
    R.para("The S-boxes turn the 48 bits back into 32. The 48 bits are cut into eight 6-bit "
           "groups, one for each S-box. The two outer bits of a group select the row and the "
           "four inner bits the column of the S-box table; the number found there is the 4-bit "
           "output. In round 1, S1 receives `111001`: row 3, column 12, output 10 (`1010`). The "
           "screenshot shows the loop stopping for S1, S2 and S3.")
    code(R, "des_sbox_lookup", "des_sbox_substitution")
    R.figure("dbg_08_sbox_loop.png", SHOT, "The S-box loop in step mode: box number, 6-bit "
             "input, 4-bit output and the 32-bit result so far.")

    R.heading("2.7  Permutation P after the S-boxes", 2)
    R.para("P reorders the 32 output bits of the S-boxes. Its result is the round function f: "
           "in round 1, `a32f11c2` becomes f = `e0d27245`.")
    code(R, "des_permutation_p", "des_feistel")
    R.figure("dbg_10_permutation_p.png", SHOT, "`des_permutation_p()` in round 1.")

    R.heading("2.8  XOR with the left half", 2)
    R.para("The output of f is XORed with the left half, and the result becomes the new right "
           "half. In round 1: `5a005a00` XOR `e0d27245` = `bad22845`, which is R1 in Table 4.2.")
    code(R, "des_xor_left_half")
    R.figure("dbg_11_xor_left_half.png", SHOT, "`des_xor_left_half()` in round 1.")

    R.heading("2.9  Swap of the halves", 2)
    R.para("At the end of every round the two halves change places, so L1 = R0 = `3cf03c0f` "
           "and R1 = `bad22845`. After round 16 the halves are swapped once more, before "
           "IP^{-1}. The screenshot shows the round function in step mode: after one `next` "
           "the watched variable `after_swap` holds `3cf03c0fbad22845`.")
    code(R, "des_swap_halves", "des_round")
    R.figure("dbg_13_round_step_mode.png", SHOT, "`des_round()` in step mode, round 1.")

    R.heading("2.10  Create, encrypt and send a message", 2)
    R.para("`tcpServer` (Machine B) and `tcpClient` (Machine A) are the starter programs with "
           "DES added. After connecting, the two machines take turns, and the client starts. "
           "On its turn a machine:")
    R.bullets([
        "**creates** the message: `create_message()` reads a line from the keyboard;",
        "**encrypts** it: `encrypt_message()` pads it to a multiple of 8 bytes and encrypts it "
        "with DES in CBC mode, with a new random IV for every message;",
        "**sends** it: `send_message()` sends one frame over TCP that holds the length, the "
        "mode, the IV and the ciphertext. The key is never sent; both machines know it.",
    ])
    R.para("We changed four things in the starter code. The server listens on all network "
           "interfaces (0.0.0.0) instead of 127.0.0.1, so that another computer can connect. "
           "The client takes the server's address as an argument (`-s`). Messages are sent "
           "together with their length, because ciphertext can contain zero bytes and TCP can "
           "split a message. Whole lines are read with `fgets()` instead of single words with "
           "`scanf`.")
    code(R, "chat_send_turn", path="src/des_chat.c")
    R.figure("net_07_machine-a_receive_decrypt_display.png", 13.0, "Machine A creates, "
             "encrypts and sends its message, then receives, decrypts and displays the answer "
             "of Machine B.")

    R.heading("2.11  Receive, decrypt and display a message", 2)
    R.para("On the other turn a machine **receives** the frame (`receive_message()`), "
           "**decrypts** it and removes the padding (`decrypt_message()`), and **displays** the "
           "text (`display_message()`). Typing `:exit` ends the conversation on both machines. "
           "If the two machines use different keys, the padding check fails and nothing is "
           "displayed.")
    code(R, "chat_receive_turn", path="src/des_chat.c")
    R.figure("net_06_machine-b_create_encrypt_send.png", 13.0, "Machine B receives, decrypts "
             "and displays the message of Machine A, then creates, encrypts and sends its "
             "answer. The Turkish letters arrive unchanged.")
    R.para("The capture below was taken on the virtual network between the machines while "
           "these two messages were sent. It contains only the frame header, the IV and the "
           "ciphertext; the text of the messages does not appear anywhere.")
    R.figure("net_08_packet_capture.png", 16.5, "The two messages as captured by tcpdump on "
             "the network between the machines.")

    # ------------------------------------------------------------------ 3
    R.heading("3  Results", 1, new_page=True)
    R.heading("3.1  Input, method, output and DES step", 2)
    R.para("{tab:steps} is the table the lecturer asked for. It shows the first call of every "
           "step: the input to the method, the method name, the method output and the DES step. "
           "`bin/des_trace` prints the same table for all 148 calls of one encryption "
           "(`test_examples/trace_textbook_encrypt.csv`). In the table, `^` means XOR and `|` "
           "joins the two halves.")
    first = lambda **kw: full.pick(tr, **kw)[0]
    rows = [first(method="des_permuted_choice_1"),
            first(method="des_left_circular_shift", step="of C", rounds=(1,)),
            first(method="des_left_circular_shift", step="of D", rounds=(1,)),
            first(method="des_permuted_choice_2", rounds=(1,)),
            first(method="des_initial_permutation"),
            first(method="des_expansion_permutation", rounds=(1,)),
            first(method="des_xor_round_key", rounds=(1,)),
            first(method="des_sbox_substitution", rounds=(1,)),
            first(method="des_permutation_p", rounds=(1,)),
            first(method="des_xor_left_half", rounds=(1,)),
            first(method="des_swap_halves", step="Swap of", rounds=(1,)),
            first(method="des_swap_halves", step="32-bit"),
            first(method="des_inverse_initial_permutation")]
    R.table(STEP_HEADER, full.step_table_rows(rows), STEP_WIDTHS, caption="Every DES step "
            "of the handout example (first call; round 1 where the step belongs to a round).",
            label="tab:steps", mono=(1, 2, 3), size=7.5, center=(0,), keep_together=True)

    R.heading("3.2  Encryption and decryption of the handout example", 2)
    R.para("{tab:t42} compares our round keys and halves with Table 4.2 of the handout. All "
           "values are the same. Three entries of the handout contain typing errors: K6 and K7 "
           "are printed with the letter l instead of the digit 1, and the last row shows "
           "`25896490` (which is R16) instead of `da02ce3a` as the left half of the ciphertext. "
           "Decryption runs the same function with the round keys from K16 down to K1 and gives "
           "back the plaintext `02468aceeca86420`.")
    printed = {r[0]: r for r in full.HANDOUT_42}
    rows, fills = [], {}
    for n, (rnd, kname, k, left, right) in enumerate(
            full.parse_summary("summary_textbook_table_4_2.txt")):
        h = printed[rnd]
        if k != h[1]:
            remark = "yes (handout typo: l instead of 1)"
        elif left != h[2]:
            remark = f"yes (handout typo: {h[2]})"
        else:
            remark = "yes"
        if remark != "yes":
            fills[(n, 4)] = NOTE_FILL
        rows.append([rnd, k, left, right, remark])
    R.table(["Round", "Ki (6-bit groups)", "Li", "Ri", "Same as the handout?"], rows,
            [1.4, 4.2, 2.6, 2.6, 6.2], caption="Our results for the handout example "
            "(`bin/des_trace -f summary`).", label="tab:t42", mono=(1, 2, 3), size=8,
            center=(0,), fills=fills, keep_together=True)

    # ------------------------------------------------------------------ 4
    R.heading("4  Settings of the distributed system", 1, new_page=True)
    R.para("The two computers are two Docker containers. Each one has its own host name, "
           "network interface, IP address and processes, and both are connected to the same "
           "virtual Ethernet network `des_lan` [6]. The settings are in `docker-compose.yml`; "
           "the DES key is given to both machines as the environment variable `DES_KEY`.")
    R.figure("network.png", 15.5, "The two machines on the virtual network.")
    R.table(["", "machine-a", "machine-b"], [
        ["Role", "Machine A, sends first", "Machine B, receives first"],
        ["Host name", "machine-a", "machine-b"],
        ["IP address", "172.28.10.10/24", "172.28.10.20/24"],
        ["Program and port", "`tcpClient -s 172.28.10.20`", "`tcpServer`, port 9000"],
    ], [3.6, 6.7, 6.7], caption="Settings of the two machines.", label="tab:net",
        size=9, bold_col0=True)
    R.code("docker compose up -d --build                          # start both machines\n"
           "docker exec -it machine-b tcpServer                   # terminal 1: Machine B\n"
           "docker exec -it machine-a tcpClient -s 172.28.10.20   # terminal 2: Machine A\n"
           "docker compose down                                   # stop both machines",
           size=8)
    R.figure("net_settings_both.png", 12.5, "machine-a (top) and machine-b (bottom): host "
             "name, IP address, route and a ping to the other machine.")
    R.para("**Real computers or virtual machines.** The programs do not depend on Docker. On "
           "two computers in the same network - or two virtual machines with a bridged network "
           "adapter - start `./bin/tcpServer -k KEY` on Machine B, allow TCP port 9000 in its "
           "firewall, and start `./bin/tcpClient -s <IP address of B> -k KEY` on Machine A. "
           "`tcpServer` prints its IP addresses when it starts. Campus Wi-Fi often blocks "
           "connections between devices; a cable or a phone hotspot avoids this.")

    # ------------------------------------------------------------------ 5
    R.heading("5  Testing and the choices we made", 1)
    R.para("**Tests.**", after=2, keep=True)
    R.bullets([
        "Unit tests (`make test`): every step function and the whole cipher are compared with "
        "values from the handout, from Grabbe's worked example [3] and from FIPS 81; all "
        "25 080 checks pass.",
        "Cross-check (`make crosscheck`): 300 random keys and blocks give the same results as "
        "pycryptodome and OpenSSL (700 comparisons, no difference).",
        "Network tests (`make loopback`, `make demo`): every message arrives unchanged on the "
        "other machine, a wrong key is rejected, and the packet capture contains no plaintext.",
        "Avalanche effect: changing bit 4 of the plaintext changes 32 of the 64 ciphertext "
        "bits, exactly as in Table 4.3 of the handout; changing bit 4 of the key changes 30.",
    ])
    R.para("**Choices.**", after=2, keep=True)
    R.bullets([
        "Docker containers instead of two laptops or virtual machines: one command starts both "
        "machines, and the network traffic can be recorded. The programs also run unchanged "
        "on real computers.",
        "CBC instead of ECB: with ECB, equal 8-byte blocks of a message give equal ciphertext "
        "blocks; CBC hides this.",
        "64-bit integers instead of arrays of bits: the debugger shows every value as one "
        "hexadecimal number that can be compared with the handout directly.",
    ])
    R.para("**Our opinion.** Writing each step as its own function made the debugging easy, "
           "because every value could be compared with the handout one step at a time. The "
           "harder part was the networking rather than DES: the starter code had to be changed "
           "before encrypted data could travel between two computers.")

    # ------------------------------------------------------------------ 6, 7
    R.heading("6  Conclusion", 1)
    R.para("We implemented DES in C with one function per step and checked every step in the "
           "debugger and against the handout's example: all values agree, and the program even "
           "shows three typing errors in the handout. Two machines exchange messages that are "
           "created, encrypted, sent, received, decrypted and displayed unchanged, while only "
           "ciphertext travels over the network. DES itself is no longer secure, because its "
           "56-bit key can be found by trying all keys [4]; today AES would be used. For "
           "learning how a block cipher works, however, DES is a good example.")

    R.heading("7  References", 1)
    full.references(R, [
        "National Institute of Standards and Technology, *FIPS PUB 46-3: Data Encryption "
        "Standard (DES)*, 1999.",
        "W. Stallings, *Cryptography and Network Security: Principles and Practice*, 8th ed., "
        "Pearson, 2020, Chapter 4.",
        "J. Orlin Grabbe, *The DES Algorithm Illustrated*, online article.",
        "Electronic Frontier Foundation, *Cracking DES*, O'Reilly, 1998.",
        "CMPE455/CMSE456 lab handouts *Lab 2 Task. DES on Two Computers* and *A DES Example*, "
        "and the starter code tcpServer.c and tcpClient.c, 2026.",
        "Docker Inc., *Bridge network driver*, Docker documentation (docs.docker.com).",
    ])

    # ------------------------------------------------------------------ appendix
    R.heading("Appendix  Source code", 1, new_page=True)
    R.para("The C source code of the DES functions and the two programs. The tests, the Docker "
           "files and the helper tools are in the submitted archive.")
    sources = ["src/des.h", "src/des.c", "src/des_trace.h", "src/des_trace.c",
               "src/des_modes.h", "src/des_modes.c", "src/des_util.h", "src/des_util.c",
               "src/net.h", "src/net.c", "src/des_chat.h", "src/des_chat.c",
               "src/tcpServer.c", "src/tcpClient.c", "src/des_trace_main.c"]
    for path in sources:
        R.heading(path, 2, toc=False)
        R.code(full.read(path), size=7)


if __name__ == "__main__":
    full.build_document(build, DOCX, PDF)
