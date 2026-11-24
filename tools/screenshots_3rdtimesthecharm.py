#!/usr/bin/env python3
"""
tools/screenshots_3rdtimesthecharm.py - screenshots of 3rdtimesthecharm/lab2.c for the
report of the same name: the code of every DES step with the line it prints, and the two
machines. No debugger. Real programs in real terminals on a private virtual display, as in
tools/screenshots.py.

Needs: Xvfb, xterm, xdotool, ImageMagick, bat, gcc, Docker (the machines are started if
they are not running). Output: 3rdtimesthecharm/screenshots/*.png
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
import screenshots as base  # noqa: E402  the virtual display and the terminals
from screenshots import ROOT, Screen, sh, type_line  # noqa: E402

FOLDER = os.path.join(ROOT, "3rdtimesthecharm")
OUT = os.path.join(FOLDER, "screenshots")
COMPOSE = ["docker", "compose", "-f", os.path.join(FOLDER, "docker-compose.yml")]
BACKGROUND = "#1b1d1e"

# picture, functions whose code is shown, how the program's output is filtered
STEPS = [
    ("2_1_initial_permutation", ["initial_permutation"], "grep -m 1 initial_permutation"),
    ("2_2_inverse_initial_permutation", ["inverse_initial_permutation"],
     "grep inverse_initial_permutation"),
    ("2_3_expansion_permutation", ["expansion_permutation"], "grep -m 1 expansion_permutation"),
    ("2_4_1_permuted_choice_1", ["permuted_choice_1"], "grep permuted_choice_1"),
    ("2_4_2_left_circular_shift", ["left_circular_shift"], "grep -m 2 left_circular_shift"),
    ("2_4_3_permuted_choice_2", ["permuted_choice_2"], "grep permuted_choice_2"),
    ("2_5_xor_round_key", ["xor_round_key"], "grep -m 1 xor_round_key"),
    ("2_6_sbox_substitution", ["sbox_substitution"], "grep -m 1 -B 8 sbox_substitution"),
    ("2_7_permutation_p", ["permutation_p"], "grep -m 1 permutation_p"),
    ("2_8_xor_left_half", ["xor_left_half"], "grep -m 1 xor_left_half"),
    ("2_9_swap_halves", ["swap_halves"], "grep -m 1 swap_halves"),
    ("3_2_des", ["des"], "tail -1"),
]


def save(window, name):
    """The window without the empty lines at its end; every picture keeps its full width."""
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".png")
    sh("import", "-window", window, path)
    subprocess.run(["magick", path, "-define", "trim:edges=south", "-trim", "+repage",
                    "-background", BACKGROUND, "-gravity", "south", "-splice", "0x10",
                    "-define", "png:exclude-chunks=date,time", "+set", "date:create",
                    "+set", "date:modify", path], check=True)
    print("  saved", os.path.relpath(path, ROOT))


def lines_of(function):
    """first:last line of a function in lab2.c, with the comment above it"""
    lines = open(os.path.join(FOLDER, "lab2.c")).read().split("\n")
    start = next(i for i, l in enumerate(lines) if re.match(rf"\w+ {function}\(", l))
    end = next(i for i in range(start, len(lines)) if lines[i] == "}")
    if lines[start - 1].startswith("/*"):
        start -= 1
    return f"{start + 1}:{end + 1}"


def steps():
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(os.path.join(FOLDER, "lab2.c"), tmp)
        subprocess.run(["gcc", "-o", "lab2", "lab2.c"], cwd=tmp, check=True)
        rc = os.path.join(tmp, "bashrc")
        with open(rc, "w") as f:
            f.write(f"unset PROMPT_COMMAND; PS1='$ '; cd {tmp}; TERM=xterm-256color\n"
                    "alias bat='bat --style=numbers --paging=never --color=always "
                    "--theme=\"Visual Studio Dark+\"'\n")
        screen = Screen()
        try:
            win = screen.xterm("lab2 steps", ["bash", "--rcfile", rc], 112, 46, 0, 0)
            for name, functions, output in STEPS:
                type_line(win, "clear", 0.5)
                for function in functions:
                    type_line(win, f"bat -r {lines_of(function)} lab2.c", 0.7)
                type_line(win, f"./lab2 steps | {output}", 0.7)
                save(win, name)
        finally:
            screen.close()


def network():
    subprocess.run(COMPOSE + ["up", "-d", "--build"], check=True, capture_output=True)
    screen = Screen()
    try:
        a = screen.xterm("machine-a", COMPOSE + ["exec", "machine-a", "bash"], 100, 34, 0, 0)
        b = screen.xterm("machine-b", COMPOSE + ["exec", "machine-b", "bash"], 100, 34, 830, 0)
        sniff = screen.xterm("capture", COMPOSE + [
            "exec", "machine-b", "tcpdump", "-i", "eth0", "-nn", "-q", "-t", "-X",
            "tcp port 9000 and (tcp[tcpflags] & tcp-push != 0)"], 100, 50, 0, 800)
        time.sleep(2.5)
        for w, peer in ((a, "172.28.20.20"), (b, "172.28.20.10")):
            type_line(w, "hostname; ip -4 -br addr show eth0; ip route | head -2", 0.6)
            type_line(w, f"ping -c 2 {peer}", 2.6)
        save(a, "4_settings_machine-a")
        save(b, "4_settings_machine-b")
        for w in (a, b):
            type_line(w, "clear", 0.4)

        type_line(b, "./lab2 server", 1.0)
        type_line(a, "./lab2 client 172.28.20.20", 1.2)
        type_line(a, "Hello Machine B, this is Machine A.", 1.2)
        type_line(b, "Hi Machine A, teşekkürler!", 1.2)
        save(a, "2_10_machine-a")
        save(b, "2_11_machine-b")
        save(sniff, "2_11_packet_capture")
        type_line(a, ":exit", 1.2)
    finally:
        screen.close()


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("steps", "all"):
        steps()
    if what in ("network", "all"):
        network()
