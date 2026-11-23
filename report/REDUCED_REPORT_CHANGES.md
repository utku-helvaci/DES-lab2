# Reduced Report: what was removed or simplified

The **Reduced Report** (`report/Reduced_Report.docx` / `.pdf`) is a shorter
version of the full lab report (`report/DES_Lab2_Report.docx` / `.pdf`). It
follows the style of the sample report *"CMPE455 - LAB2 Report - a simpler and
more preffered report.docx"*, but still contains everything the lab sheet asks
for.

|  | Full report | Reduced Report |
|---|---|---|
| Pages | 86 (41 body + 45 appendices) | 42 (16 body + 26 appendix) |
| Words of running text | about 5 200 | about 2 000 |
| Figures | 28, with captions | 16, without captions |
| Code boxes in the body | one or more for every step | none (the code is in the appendix) |
| Tables | 23 | 4 |
| Appendices | A source code (24 files), B full step table (148 rows), C archive layout | source code (15 C files) |

`make report` builds both reports at once (`make reduced-report` builds only
this one). Both are generated from the same code, test results and
screenshots, so they never disagree.

## The sample report in short

13 pages: a cover with the university logo, a one-paragraph problem definition,
then *Work done* as a numbered list, one item per DES step (initial
permutation, inverse, expansion, round keys, XOR, S-boxes, P, final
permutation, encryption, decryption, output). Each item has one to three
sentences and screenshots of the code and the output. It has no tables, no
figure captions, no network or two-machine part, and no conclusion, references
or appendix.

## What the Reduced Report takes from the sample

- **Numbering by step.** Sections 2.1 - 2.11 have the same numbers as the lab
  sheet's tasks (2.1 initial permutation ... 2.9 swap, 2.10 create/encrypt/send,
  2.11 receive/decrypt/display), like the sample's numbered list.
- **Short sections.** Each step has one to three plain sentences: what the step
  does, then the values of the example. After that comes the screenshot.
- **No figure captions.** Like the sample, no image has a "Figure N." line. The
  sentence before a screenshot says what it shows, and the few facts that were
  only in a caption (for example C1 = `d1f8894` in 2.4, or which machine is at
  the top of the settings screenshot) moved into the text. Tables keep their
  captions.
- **No code boxes in Sections 2 - 2.11.** As in the sample, the code is seen in
  the screenshots: the source pane of every debugger screenshot shows the step
  function. The complete code is in the appendix.
- **Plain language.** The sentences are shorter, there is less formal wording,
  and there are few "see Table 17"-style cross-references.
- **Cover.** The university logo and centred lines replace the field table. The
  logo comes from the sample report and is stored as `report/assets/emu_logo.png`.

## What it keeps although the sample report does not have it

These are lab-sheet requirements, or things the lecturer asked for:

- all 13 cover-page fields (lab sheet 3.1) and the outline (3.2);
- for every lab item 2.1 - 2.9, a screenshot of the debugger in step mode with
  the tested variables watched (3.4.1);
- the table with *input to method, method name, method output, current DES step*
  that the lecturer asked for, now as one table (Section 3.1);
- screenshots of create -> encrypt -> send -> receive -> decrypt -> display on
  **both** machines (2.10, 2.11);
- the settings of the distributed system, including how to run the programs on
  real computers or virtual machines (3.4.2). The sample report has no
  networking part;
- a short comparison of the choices made and an opinion (the lecturer's general
  instructions);
- conclusion, references and an appendix with the source code (3.5 - 3.7).

## Section by section

| Full report | Reduced Report |
|---|---|
| Cover with a 13-row field table | Logo and centred lines, same 13 fields |
| Outline: paragraph and 3-level contents (63 entries) | One paragraph and 2-level contents (21 entries) |
| 1 Problem definition: 3 paragraphs, requirement list R1 - R6, note on Docker | 2 short paragraphs |
| 2.1 DES in brief, with 2 diagrams | **Removed.** Each step section explains its own step |
| 2.2 Environment table and project-file table (17 rows) | **Removed** (see README.md) |
| 2.3 Design: 3 paragraphs, `des_permute` code, 17-row function table, paragraph on tracing | 1 paragraph and a 13-row function table; no code |
| 2.4.1 - 2.4.9: text, constant tables (IP, E, S1), code, step table for rounds 1, 2 and 16, and 1 - 4 screenshots for each step (15 debugger screenshots) | 2.1 - 2.9: 1 - 3 sentences and 1 screenshot (3 for round keys): 11 debugger screenshots, no code |
| Round-key comparison table (16 rows) | Merged into the result table of 3.2 |
| 9 separate step tables (rounds 1, 2, 16, S-box look-ups) | **One** step table: the first call of every step (13 rows), Section 3.1 |
| 2.5 Table 4.2 comparison and a 16-row decryption table | 3.2: the comparison table; decryption in one sentence |
| 2.6 Values observed by the debugger (GDB breakpoint table) | **Removed** (the screenshots show the same values; the table is in `test_examples/gdb_watch_steps.txt`) |
| 2.7 Padding and modes: code of 2 functions, ECB/CBC table | **Removed**; one sentence in 2.10 and one bullet in Section 5 |
| 2.8 Distributed application: starter-code problem table (9 rows), frame table, code of 5 functions, 6 screenshots, packet-capture paragraph | 2.10 / 2.11: 3 bullets, 4 sentences about the starter code, 2 screenshots that each show all six stages on one machine, the packet capture |
| 2.9 Settings: text, diagram, 8-row table, `docker-compose.yml` excerpt, 2 screenshots, commands, 9-row options table, 4 numbered steps for real computers and VMs, Wi-Fi note | Section 4: 1 paragraph, diagram, 4-row table, commands, 1 combined screenshot, 1 paragraph for real computers and VMs |
| 2.10 Testing: 4 subsections with full output listings, avalanche table (18 rows), chart, note on the handout | Section 5: 4 bullets with the results |
| 2.11 Comparison of choices: 6-row table and 5 paragraphs | Section 5: 3 bullets and a 2-sentence opinion |
| 3 Conclusion: paragraph, 4 bullets, paragraph | 1 paragraph |
| 4 References: 14 | 6 |
| Appendix A: 24 files (sources, tests, Python and shell scripts, Makefile, Docker files) | 15 C files of `src/`, the only code in the report (the Makefile, the Docker files and `des_avalanche.c` are in its zip; the tests and scripts only in the full zip) |
| A "Figure N." caption under every figure | **No captions**; tables keep theirs |
| Appendix B: 148-row step table | **Removed** (`test_examples/trace_textbook_encrypt.csv`) |
| Appendix C: archive layout | **Removed** (see README.md) |

## Screenshots and drawings that were dropped

| Image | Why it could go |
|---|---|
| `des_structure.png`, `des_round.png` | the step sections and the function table describe the same thing |
| `dbg_04_all_round_keys.png` | the round keys are in the table of Section 3.2 |
| `dbg_09_sbox_result.png` | `dbg_08` already shows the S-box loop and its result growing |
| `dbg_12_swap.png` | `dbg_13` shows the swap in step mode |
| `dbg_15_result.png` | the final ciphertext is in `dbg_14` and in Section 3.2 |
| `net_03`, `net_04`, `net_05` | `net_06` and `net_07` already show all six stages on each machine |
| `net_09`, `net_10` (`:exit`) | described in one sentence |
| `net_01` + `net_02` | combined into one figure, `net_settings_both.png` |
| `avalanche.png` | the numbers are given in one bullet |

## What did not change

The programs, the tests, the executables and the test examples are the same,
and the full report is still built next to the reduced one.

## The two submission zips

Each report has its own zip; both unpack into a folder `Lab2_DES/`:

```sh
make dist                  # both zips
make dist REPORT=full      # only dist/Lab2_DES_Full_Report.zip
make dist REPORT=reduced   # only dist/Lab2_DES_Reduced_Report.zip
```

|  | Full report zip | Reduced report zip |
|---|---|---|
| Report (pdf + docx) | `DES_Lab2_Report` | `Reduced_Report` |
| `src/`, `docker/`, `docker-compose.yml`, `Makefile`, `README.md`, `.vscode/`, report scripts and screenshots | yes | yes |
| `bin/` | 5 executables | 4 (no `des_test`) |
| `tests/`, `debug/`, `tools/`, `test_examples/`, `starter_original/` | yes | **no** |

Without `tests/`, `make` skips `bin/des_test` and the Docker build skips the
unit tests, so the programs and both machines still build from the reduced zip.
`make test`, `make check`, `make demo`, `make examples`, `make screenshots`,
`make report` and `make dist` need the full zip. The README of each zip names
only its own report; the reduced one also says what it leaves out.
