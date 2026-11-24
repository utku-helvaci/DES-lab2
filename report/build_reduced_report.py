#!/usr/bin/env python3
"""
report/build_reduced_report.py - builds the "Reduced Report".

A shorter version of the Lab 2 report, written in the plainer style of a sample
report the team preferred: one short numbered section per lab item with a few
sentences and a screenshot. Like the sample, the figures have no captions, and
the code is only in the appendix, not in the sections of the steps. Everything
the lab sheet asks for is still there; report/REDUCED_REPORT_CHANGES.md lists
what was removed or shortened compared with the full report (report/build_report.py).
Arial is the only font of the document, also for code, bullets and the network drawing.

    make report            (both reports)   or   make reduced-report   (only this one)

Output: report/Reduced_Report.docx and report/Reduced_Report.pdf
"""
import os
import re
import subprocess
import sys
import zipfile

from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True       # no __pycache__ folder next to the report

import build_report as full  # noqa: E402  shared data helpers, layout and two-pass build
from build_report import (ACCENT, GRAY, NOTE_FILL, STEP_HEADER, STEP_WIDTHS,  # noqa: E402
                          Cm, OxmlElement, Pt, WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, qn)
from make_figures import arial_fonts  # noqa: E402

full.MONO = full.FONT       # code in Arial too

DOCX = os.path.join(HERE, "Reduced_Report.docx")
PDF = os.path.join(HERE, "Reduced_Report.pdf")
LOGO = os.path.join(HERE, "assets", "emu_logo.png")
SHOT = 13.5          # width of a debugger screenshot, cm

# --------------------------------------------------------------------------- #
#  Arial as the only font                                                      #
# --------------------------------------------------------------------------- #

# advance widths of the Arial glyphs " " ... "~" in 1/1000 of the font size
ARIAL_WIDTHS = dict(zip(map(chr, range(32, 127)), map(int, """
    278 278 355 556 556 889 667 191 333 333 389 584 278 333 278 278 556 556 556 556 556 556
    556 556 556 556 278 278 584 584 584 556 1015 667 667 722 722 667 611 778 722 278 500 667
    556 833 722 778 667 778 722 667 611 722 667 944 667 667 611 278 278 278 469 556 333 556
    556 500 556 556 278 556 556 222 222 500 222 833 556 556 556 556 333 500 278 556 500 722
    500 500 500 334 260 334 584""".split())))
COLUMN = 0.5         # width of one column of source code, in font sizes
DIGIT = 0.556        # width of an Arial digit = of two Arial spaces
CODE_TOKEN = re.compile(r"[-=]{4,}|(?:(?![-=]{4,})\S)+")     # a rule (----, ====) or a word


def text_width(text):
    return sum(ARIAL_WIDTHS[ch] for ch in text) / 1000


def rule_spacing(x, rule, end):
    """Extra width per character with which a rule from x ends at `end` (0: leave it alone)."""
    extra = 0 if end is None else (end - x - text_width(rule)) / len(rule)
    return extra if -0.1 < extra < 0.25 else 0


def end_of(pieces):
    """Where the pieces of a line end, in font sizes."""
    x = 0.0
    for stop, text, end in pieces:
        x = x if stop is None else stop
        x += text_width(text) + rule_spacing(x, text, end) * len(text)
    return x


def code_layout(lines):
    """Keeps the columns of source code in a proportional font.

    Returns for every line its pieces [tab stop or None, text, end of a rule or None], all
    in font sizes. A piece gets a tab stop at the indentation and where its line is aligned
    with a neighbouring line (trailing comments, declarations, drawn tables); consecutive
    lines share the stop. Other spaces stay spaces."""
    tokens = []                                              # [(column, spaces before, text)]
    for line in lines:
        found, end = [], 0
        for m in CODE_TOKEN.finditer(line):
            found.append((m.start(), m.start() - end, m.group()))
            end = m.end()
        tokens.append(found)
    is_number = lambda before, word: before[-1:] in (",", "{") and word[0].isdigit()
    gaps = [{c: g for (c, g, word), before in zip(row[1:], row) if not is_number(before[2], word)}
            for row in tokens]                                   # column -> spaces before it
    is_rule = lambda word: len(word) >= 4 and set(word) <= set("-=")
    is_comment = [line.lstrip().startswith(("/*", "*")) for line in lines]

    layout, aligned = [], {}
    for n, row in enumerate(tokens):
        near = [gaps[i] for i in (n - 1, n + 1)
                if 0 <= i < len(lines) and is_comment[i] == is_comment[n]]
        rules = [k for k, t in enumerate(row) if is_rule(t[2])]
        border = any(g == 0 for _, g, t in row[1:] if is_rule(t))          # +----+----+
        drawn_table = lines[n].count("|") >= 3
        pieces = []
        for k, (column, gap, word) in enumerate(row):
            shared = any(other.get(column, 0) >= 2 for other in near)
            last = pieces[-1][1] if pieces else ""
            number = is_number(last, word)
            end = (column + len(word)) * COLUMN if is_rule(word) and \
                (border or k == rules[-1]) else None             # this rule keeps its right end
            if k == 0:                                           # the indentation
                pad = column % 4 if word[0].isdigit() else 0
                stop = (column - pad) * COLUMN + pad * DIGIT
                pieces.append([stop if column else None, word, end])
            elif number:                                         # padding = half digits
                pieces[-1][1] += " " * (2 * gap - (last[-1] == ",")) + word
            elif gap and (gap >= 3 or (gap == 2 and shared)
                          or (shared and k <= 2 and not is_comment[n])     # declarations
                          or (drawn_table and word[0] == "|")
                          or (rules and k == rules[-1] + 1)):              # the */ after a rule
                aligned.setdefault(column, []).append((n, len(pieces)))
                pieces.append([0.0, word, end])
            elif is_rule(word) or is_rule(last.strip()):
                pieces[-1][1] += " " * gap
                pieces.append([None, word, end])
            else:
                pieces[-1][1] += " " * gap + word
        layout.append(pieces)

    for column in sorted(aligned):
        runs = []
        for n, k in aligned[column]:                             # groups of consecutive lines
            if runs and runs[-1][-1][0] == n - 1:
                runs[-1].append((n, k))
            else:
                runs.append([(n, k)])
        for run in runs:
            stop = max([column * COLUMN] + [end_of(layout[n][:k]) + 0.4 for n, k in run])
            for n, k in run:
                layout[n][k][0] = stop
    return layout


class ArialReport(full.Report):
    """The report with Arial instead of Courier New, Symbol and the theme fonts."""

    def runs(self, p, text, **kw):
        return super().runs(p, text.replace("`", ""), **kw)      # no special font for code

    def table(self, header, rows, widths, mono=(), **kw):
        return super().table(header, rows, widths, **kw)

    def code(self, text, size=7.5):
        """Source code in a proportional font: the columns are kept with tab stops."""
        lines = text.expandtabs(4).rstrip("\n").split("\n")
        short = len(lines) <= 20
        left = self.doc.styles["Code"].paragraph_format.left_indent
        for i, (line, pieces) in enumerate(zip(lines, code_layout(lines))):
            p = self.doc.add_paragraph(style="Code")
            for k, (stop, piece, end) in enumerate(pieces):
                x = end_of(pieces[:k]) if stop is None else stop
                if stop is not None:
                    p.paragraph_format.tab_stops.add_tab_stop(left + Pt(stop * size))
                    p.add_run("\t").font.size = Pt(size)
                r = p.add_run(piece)
                r.font.size = Pt(size)
                if rule_spacing(x, piece, end):
                    spacing = OxmlElement("w:spacing")           # in 1/20 pt
                    spacing.set(qn("w:val"), str(round(rule_spacing(x, piece, end) * size * 20)))
                    r._r.get_or_add_rPr().insert_element_before(
                        spacing, "w:w", "w:kern", "w:position", "w:sz", "w:szCs")
            if not line.strip():
                p.add_run(" ").font.size = Pt(size)
            if i < (len(lines) - 1 if short else 6):     # no heading with a line or two
                p.paragraph_format.keep_with_next = True
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(4)
        spacer.paragraph_format.line_spacing = 1.0

    def save(self, path):
        super().save(path)
        arial_only(path)


def arial_only(path):
    """Replaces every other font name inside the .docx: styles, bullets, theme, font table."""
    with zipfile.ZipFile(path) as z:
        parts = [(info, z.read(info)) for info in z.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in parts:
            if info.filename.startswith("word/") and info.filename.endswith(".xml"):
                root = etree.fromstring(data)
                for el in root.iter(qn("w:rFonts")):
                    el.attrib.clear()
                    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                        el.set(qn(attr), full.FONT)
                for el in root.iter(qn("w:lvlText")):            # Symbol bullets
                    el.set(qn("w:val"), re.sub("[\ue000-\uf8ff]", "\u2022", el.get(qn("w:val"))))
                for el in list(root.iter("{*}mathFont")):        # equations (there are none)
                    el.getparent().remove(el)
                for el in list(root.iter(qn("w:font"))):         # font table
                    if el.get(qn("w:name")) != full.FONT:
                        el.getparent().remove(el)
                for group in list(root.iter(qn("a:majorFont"), qn("a:minorFont"))):
                    for el in list(group):
                        if el.tag == qn("a:latin"):
                            el.attrib.clear()
                            el.set("typeface", full.FONT)
                        elif el.tag in (qn("a:ea"), qn("a:cs")):
                            el.attrib.clear()
                            el.set("typeface", "")
                        else:
                            group.remove(el)
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                                      standalone=True)
            z.writestr(info, data)


def check_fonts(pdf):
    """Says so if the PDF contains another font than Arial (Arial not installed)."""
    table = subprocess.run(["pdffonts", pdf], capture_output=True, text=True).stdout
    names = {line.split()[0].split("+")[-1] for line in table.splitlines()[2:]}
    other = sorted(n for n in names if not re.match(r"Arial(MT|-\w+MT)?$", n))
    if other:
        print("warning: the PDF contains other fonts than Arial:", ", ".join(other),
              file=sys.stderr)


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
           "reverse order [1].")
    R.para("In this lab we implement DES in C and use it in a distributed application. Two "
           "processes run on two computers, and each one can create a message, encrypt it, "
           "send it, receive a message, decrypt it and display it. The displayed text must be "
           "the same as the text typed on the other computer. Every DES step has to be checked "
           "in the debugger. As the lecturer asked, every step is its own function, and a table "
           "shows the input, the method, the output and the DES step of each one. We started "
           "from the course's `tcpServer.c` and `tcpClient.c` [2]. The two computers are two "
           "Docker containers on one virtual network (Section 4).")

    # ------------------------------------------------------------------ 2
    R.heading("2  Work done", 1, new_page=True)
    R.para("Every DES step is a small function in `src/des.c` ({tab:functions}). It takes its "
           "input as parameters and returns its output, so both can be watched in the debugger. "
           "All six permutations (IP, IP^{-1}, E, P, PC-1, PC-2) use the same helper, "
           "`des_permute()`, each with its own table from the DES standard [1]. The source "
           "code of all the functions is in the appendix.")
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
    R.figure("dbg_05_ip.png", SHOT)

    R.heading("2.2  Inverse initial permutation", 2)
    R.para("The inverse initial permutation is the last step and undoes the initial "
           "permutation. Its input is R16 | L16 = `25896490 75e8fd8f`, its output the "
           "ciphertext `da02ce3a89ecac3b`.")
    R.figure("dbg_14_inverse_ip.png", SHOT)

    R.heading("2.3  Expansion/permutation", 2)
    R.para("The right half has 32 bits but the round key has 48, so E expands the half to 48 "
           "bits: the two edge bits of every 4-bit group are copied into the neighbouring "
           "groups. In round 1, R0 = `3cf03c0f` becomes `9f97a01f805e`.")
    R.figure("dbg_06_expansion.png", SHOT)

    R.heading("2.4  Round key generation", 2)
    R.para("The 16 round keys are made from the key in three steps. **Permuted choice 1** "
           "removes the 8 parity bits and splits the other 56 bits into two 28-bit halves, "
           "C0 = `68fc44a` and D0 = `1113e96`. Before every round both halves are **rotated "
           "left** by one position (rounds 1, 2, 9 and 16) or by two positions (all other "
           "rounds); in round 1, C0 becomes C1 = `d1f8894`. **Permuted choice 2** then picks "
           "48 of the 56 bits as the round key: K1 = `7833c320da70`, which is "
           "`1e030f03080d2930` when written in 6-bit groups as in the handout. The three "
           "screenshots show these three steps in this order.")
    R.figure("dbg_01_pc1.png", 12.5)
    R.figure("dbg_02_shift.png", 12.5)
    R.figure("dbg_03_pc2.png", 12.5)

    R.heading("2.5  XOR with round key", 2)
    R.para("The expanded right half is XORed with the round key of the round. In round 1: "
           "`9f97a01f805e` XOR `7833c320da70` = `e7a4633f5a2e`.")
    R.figure("dbg_07_xor_round_key.png", SHOT)

    R.heading("2.6  S-boxes", 2)
    R.para("The S-boxes turn the 48 bits back into 32. The 48 bits are cut into eight 6-bit "
           "groups, one for each S-box. The two outer bits of a group select the row and the "
           "four inner bits the column of the S-box table; the number found there is the 4-bit "
           "output. In round 1, S1 receives `111001`: row 3, column 12, output 10 (`1010`). The "
           "screenshot shows the loop in step mode stopping for S1, S2 and S3, with the box "
           "number, the 6-bit input, the 4-bit output and the 32-bit result so far.")
    R.figure("dbg_08_sbox_loop.png", SHOT)

    R.heading("2.7  Permutation P after the S-boxes", 2)
    R.para("P reorders the 32 output bits of the S-boxes. Its result is the round function f: "
           "in round 1, `a32f11c2` becomes f = `e0d27245`.")
    R.figure("dbg_10_permutation_p.png", SHOT)

    R.heading("2.8  XOR with the left half", 2)
    R.para("The output of f is XORed with the left half, and the result becomes the new right "
           "half. In round 1: `5a005a00` XOR `e0d27245` = `bad22845`, which is R1 in Table 4.2.")
    R.figure("dbg_11_xor_left_half.png", SHOT)

    R.heading("2.9  Swap of the halves", 2)
    R.para("At the end of every round the two halves change places, so L1 = R0 = `3cf03c0f` "
           "and R1 = `bad22845`. After round 16 the halves are swapped once more, before "
           "IP^{-1}. The screenshot shows the round function in step mode: after one `next` "
           "the watched variable `after_swap` holds `3cf03c0fbad22845`.")
    R.figure("dbg_13_round_step_mode.png", SHOT)

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
    R.para("The screenshot shows Machine A: it creates, encrypts and sends its message, then "
           "receives, decrypts and displays the answer of Machine B.")
    R.figure("net_07_machine-a_receive_decrypt_display.png", 13.0)

    R.heading("2.11  Receive, decrypt and display a message", 2)
    R.para("On the other turn a machine **receives** the frame (`receive_message()`), "
           "**decrypts** it and removes the padding (`decrypt_message()`), and **displays** the "
           "text (`display_message()`). Typing `:exit` ends the conversation on both machines. "
           "If the two machines use different keys, the padding check fails and nothing is "
           "displayed.")
    R.para("The screenshot shows Machine B: it receives, decrypts and displays the message of "
           "Machine A, then creates, encrypts and sends its answer. The Turkish letters arrive "
           "unchanged.")
    R.figure("net_06_machine-b_create_encrypt_send.png", 13.0)
    R.para("The tcpdump capture below was taken on the virtual network between the machines "
           "while these two messages were sent. It contains only the frame header, the IV and "
           "the ciphertext; the text of the messages does not appear anywhere.")
    R.figure("net_08_packet_capture.png", 16.5)

    # ------------------------------------------------------------------ 3
    R.heading("3  Results", 1, new_page=True)
    R.heading("3.1  Input, method, output and DES step", 2)
    R.para("{tab:steps} is the table the lecturer asked for. It shows the first call of every "
           "step: the input to the method, the method name, the method output and the DES step. "
           "`bin/des_trace` prints the same table for all 148 calls of one encryption. In the "
           "table, `^` means XOR and `|` joins the two halves.")
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
           "virtual Ethernet network `des_lan` [3]. The settings are in `docker-compose.yml`; "
           "the DES key is given to both machines as the environment variable `DES_KEY`.")
    R.figure("network_arial.png", 15.5)
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
    R.para("The screenshot shows the host name, IP address and route of machine-a (top) and "
           "machine-b (bottom), and a ping from each machine to the other.")
    R.figure("net_settings_both.png", 12.5)
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
        "Network tests, on one computer and on the two Docker machines: every message arrives "
        "unchanged on the other machine, a wrong key is rejected, and the packet capture "
        "contains no plaintext.",
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
           "ciphertext travels over the network. DES itself is no longer secure: in January 1999 "
           "a DES key was broken publicly in 22 hours and 15 minutes, and AES has replaced DES "
           "[1]. For learning how a block cipher works, however, DES is a good example.")

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
    R.para("The C source code of the DES functions, the two programs and the step-table tool "
           "`des_trace`. The Makefile, the Docker files and `src/des_avalanche.c` are in the "
           "submitted archive.")
    sources = ["src/des.h", "src/des.c", "src/des_trace.h", "src/des_trace.c",
               "src/des_modes.h", "src/des_modes.c", "src/des_util.h", "src/des_util.c",
               "src/net.h", "src/net.c", "src/des_chat.h", "src/des_chat.c",
               "src/tcpServer.c", "src/tcpClient.c", "src/des_trace_main.c"]
    for path in sources:
        R.heading(path, 2, toc=False)
        R.code(full.read(path), size=7)


if __name__ == "__main__":
    with arial_fonts() as env:
        full.build_document(build, DOCX, PDF, report=ArialReport, env=env)
    check_fonts(PDF)
