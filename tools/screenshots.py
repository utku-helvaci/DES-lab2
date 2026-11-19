#!/usr/bin/env python3
"""
tools/screenshots.py - takes the screenshots used in the report.

Everything runs on a private virtual X display (Xvfb), so nothing appears on
(or is captured from) the real desktop.  Real programs run in real xterm
windows; keystrokes are sent with xdotool and the windows are captured with
ImageMagick's `import`.

  python3 tools/screenshots.py debugger   gdb TUI, step by step through DES
  python3 tools/screenshots.py network    machine-a / machine-b / packet capture
  python3 tools/screenshots.py all

Needs: Xvfb, xterm, xdotool, ImageMagick, gdb, docker (for "network"),
the containers from docker-compose.yml, and `make all` done.
Output: report/figures/*.png
"""
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "report", "figures")
DISPLAY = ":91"
ENV = dict(os.environ, DISPLAY=DISPLAY, LANG="C.UTF-8", LC_ALL="C.UTF-8")
ENV.pop("WAYLAND_DISPLAY", None)

PALETTE = ["#2e3436", "#ef5350", "#8ae234", "#fce94f", "#729fcf", "#d18ad0", "#34e2e2", "#d3d7cf",
           "#686a66", "#ff6b6b", "#9ef05a", "#fff27a", "#8cb4ff", "#e3a6e0", "#5ff5f5", "#ffffff"]


def sh(*args, **kw):
    return subprocess.run(args, env=ENV, check=True, capture_output=True, text=True, **kw).stdout


class Screen:
    def __init__(self, width=2600, height=1700):
        self.proc = subprocess.Popen(["Xvfb", DISPLAY, "-screen", "0", f"{width}x{height}x24",
                                      "-nolisten", "tcp"], env=ENV,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)
        self.terms = []

    def xterm(self, title, command, cols, rows, x, y, font_size=10):
        resources = [f"XTerm*color{i}: {c}" for i, c in enumerate(PALETTE)]
        args = ["xterm", "-T", title, "-n", title, "-geometry", f"{cols}x{rows}+{x}+{y}",
                "-fa", "DejaVu Sans Mono", "-fs", str(font_size), "-bg", "#1b1d1e",
                "-fg", "#e6e6e6", "-cr", "#e6e6e6", "-b", "6", "-u8", "+sb"]
        for r in resources:
            args += ["-xrm", r]
        args += ["-e"] + command
        proc = subprocess.Popen(args, env=ENV, cwd=ROOT, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        window = sh("xdotool", "search", "--sync", "--name", f"^{re.escape(title)}$").split()[0]
        self.terms.append(proc)
        time.sleep(0.8)
        return window

    def close(self):
        for t in self.terms:
            t.terminate()
        self.proc.terminate()


def type_line(window, text, wait=0.8):
    sh("xdotool", "windowfocus", "--sync", window)
    if text:
        sh("xdotool", "type", "--delay", "8", "--", text)
    sh("xdotool", "key", "Return")
    time.sleep(wait)


def shot(window, name):
    path = os.path.join(FIG, name + ".png")
    sh("import", "-window", window, path)
    print("  saved", os.path.relpath(path, ROOT))
    return path


def line_of(path, function, pattern):
    """Line number of the first line matching `pattern` after `function(` begins."""
    lines = open(os.path.join(ROOT, path)).read().splitlines()
    start = next(i for i, l in enumerate(lines) if re.match(rf"^\w.*\b{function}\(", l))
    for j in range(start + 1, len(lines)):
        if re.search(pattern, lines[j]):
            return j + 1
    raise ValueError(f"{pattern} not found in {function}")


def ret(function):
    return line_of("src/des.c", function, r"^\s+return\b")


# --------------------------------------------------------------------------- #
#  Debugger: GDB in TUI mode, stopping at every DES step                       #
# --------------------------------------------------------------------------- #

def debugger():
    screen = Screen()
    try:
        win = screen.xterm("gdb - DES step by step", ["gdb", "-q", "-tui", "--args",
                           "bin/des_trace", "-q", "-k", "0f1571c947d9e859",
                           "-i", "02468aceeca86420"], 128, 46, 0, 0, font_size=10)
        gdb = lambda cmd, wait=0.7: type_line(win, cmd, wait)
        for cmd in ["set debuginfod enabled off", "set confirm off", "set pagination off",
                    "set output-radix 16", "tui window height src 22"]:
            gdb(cmd, 0.4)

        def step(name, location, displays, first=False, extra=()):
            gdb(f"tbreak {location}", 0.4)
            gdb("run" if first else "continue", 1.2 if first else 0.8)
            for d in displays:
                gdb(f"display{d}", 0.5)
            for e in extra:
                gdb(e, 0.6)
            shot(win, name)
            gdb("undisplay", 0.4)

        sbox_line = line_of("src/des.c", "des_sbox_substitution", r"output = \(output << 4\)")
        call_line = line_of("src/des_trace_main.c", "main", r"= des_process_block\(input")
        main_line = line_of("src/des_trace_main.c", "main", r"^\s+if \(quiet\)")

        step("dbg_01_pc1", f"des.c:{ret('des_permuted_choice_1')}", ["/z key", "/z cd"], first=True)
        step("dbg_02_shift", f"des.c:{ret('des_left_circular_shift')}",
             ["/z half", " amount", "/z rotated"])
        step("dbg_03_pc2", f"des.c:{ret('des_permuted_choice_2')}", ["/z cd", "/z subkey"])
        step("dbg_04_all_round_keys", f"des_trace_main.c:{call_line}", [],
             extra=["print/x ks.subkey"])
        step("dbg_05_ip", f"des.c:{ret('des_initial_permutation')}", ["/z block", "/z permuted"])
        step("dbg_06_expansion", f"des.c:{ret('des_expansion_permutation')}",
             ["/z right", "/z expanded"])
        step("dbg_07_xor_round_key", f"des.c:{ret('des_xor_round_key')}",
             ["/z expanded", "/z subkey", "/z mixed"])

        # S-boxes in step mode: stop in the loop for S1, S2, S3, then at return
        gdb(f"break des.c:{sbox_line}", 0.4)
        gdb("continue", 0.8)
        for d in [" box + 1", "/t six_bits", " four_bits", "/z output"]:
            gdb(f"display{d}", 0.5)
        gdb("continue", 0.8)
        gdb("continue", 0.8)
        shot(win, "dbg_08_sbox_loop")
        gdb("delete", 0.4)
        gdb("undisplay", 0.4)
        step("dbg_09_sbox_result", f"des.c:{ret('des_sbox_substitution')}",
             ["/z input48", "/z output"])
        step("dbg_10_permutation_p", f"des.c:{ret('des_permutation_p')}",
             ["/z input", "/z permuted"])
        step("dbg_11_xor_left_half", f"des.c:{ret('des_xor_left_half')}",
             ["/z left", "/z f_output", "/z new_right"])
        step("dbg_12_swap", f"des.c:{ret('des_swap_halves')}", ["/z block", "/z swapped"])

        # step mode in des_round: finish the swap, then watch the round's locals
        gdb("finish", 0.8)
        for d in ["/z left", "/z right", "/z f_output", "/z new_right", "/z before_swap",
                  "/z after_swap"]:
            gdb(f"display{d}", 0.4)
        gdb("next", 0.8)
        shot(win, "dbg_13_round_step_mode")
        gdb("undisplay", 0.4)

        step("dbg_14_inverse_ip", f"des.c:{ret('des_inverse_initial_permutation')}",
             ["/z block", "/z restored"])
        step("dbg_15_result", f"des_trace_main.c:{main_line}", ["/z input", "/z key", "/z output"])
        gdb("continue", 0.8)
        gdb("quit", 0.5)
    finally:
        screen.close()


# --------------------------------------------------------------------------- #
#  Network: two machines side by side + a packet capture                       #
# --------------------------------------------------------------------------- #

def network():
    subprocess.run(["docker", "compose", "up", "-d", "machine-a", "machine-b"], cwd=ROOT,
                   check=True, capture_output=True)
    screen = Screen()
    try:
        cols, rows = 100, 52
        a = screen.xterm("machine-a", ["docker", "exec", "-it", "machine-a", "bash"],
                         cols, rows, 0, 0)
        b = screen.xterm("machine-b", ["docker", "exec", "-it", "machine-b", "bash"],
                         cols, rows, 830, 0)
        sniff = screen.xterm("sniffer", ["docker", "compose", "--profile", "capture", "run",
                             "--rm", "sniffer", "tcpdump", "-i", "des-lan0", "-nn", "-X",
                             "tcp port 9000 and (tcp[tcpflags] & tcp-push != 0)"],
                             160, 44, 0, 900)
        time.sleep(2.5)

        # 1. network settings of the two machines
        for w, peer in ((a, "172.28.10.20"), (b, "172.28.10.10")):
            type_line(w, "hostname; ip -4 -br addr show eth0; ip route | head -2", 0.6)
            type_line(w, f"ping -c 2 {peer}", 2.6)
        shot(a, "net_01_settings_machine-a")
        shot(b, "net_02_settings_machine-b")
        for w in (a, b):
            type_line(w, "clear", 0.4)

        # 2. start the server on B and the client on A
        type_line(b, "tcpServer", 1.0)
        type_line(a, "tcpClient -s 172.28.10.20", 1.5)
        shot(b, "net_03_server_listening")

        # 3. A creates, encrypts and sends; B receives, decrypts and displays
        type_line(a, "Hello Machine B, this is Machine A.", 1.5)
        shot(a, "net_04_machine-a_create_encrypt_send")
        shot(b, "net_05_machine-b_receive_decrypt_display")

        # 4. B answers; A receives
        type_line(b, "Hi Machine A! Teşekkürler, your message arrived intact.", 1.5)
        shot(b, "net_06_machine-b_create_encrypt_send")
        shot(a, "net_07_machine-a_receive_decrypt_display")
        shot(sniff, "net_08_packet_capture")

        # 5. end of the conversation
        type_line(a, ":exit", 1.5)
        shot(a, "net_09_machine-a_exit")
        shot(b, "net_10_machine-b_exit")
    finally:
        screen.close()
        leftovers = subprocess.run(["docker", "ps", "-aq", "--filter", "name=des-lab2-sniffer-run"],
                                   capture_output=True, text=True).stdout.split()
        if leftovers:
            subprocess.run(["docker", "rm", "-f"] + leftovers, capture_output=True)


def main():
    for tool in ("Xvfb", "xterm", "xdotool", "import", "gdb"):
        if shutil.which(tool) is None:
            sys.exit(f"missing tool: {tool}")
    os.makedirs(FIG, exist_ok=True)
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("debugger", "all"):
        print("debugger screenshots")
        debugger()
    if what in ("network", "all"):
        print("network screenshots")
        network()


if __name__ == "__main__":
    main()
