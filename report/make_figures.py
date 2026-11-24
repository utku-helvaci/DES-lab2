#!/usr/bin/env python3
"""
report/make_figures.py - diagrams and charts for the report.

  des_structure.png   DES block + key schedule, every box = one C function
  des_round.png       one round, every box = one C function
  network.png         the two Docker machines on the virtual LAN
  network_arial.png   the same drawing with Arial as its only font (reduced report)
  avalanche.png       differing bits per round (handout Tables 4.3 / 4.4)
  build/fig/*.png     screenshots with the empty terminal area trimmed
  net_settings_both.png   the two network-settings screenshots stacked (reduced report)

How every image in build/fig was made: build/fig/SCREENSHOTS.md.

Needs graphviz (dot), matplotlib, ImageMagick.
"""
import contextlib
import csv
import glob
import html
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG = os.path.join(HERE, "figures")
OUT = os.path.join(HERE, "build", "fig")

BLUE, BLUE_FILL = "#2a78d6", "#eaf2fc"
ORANGE, ORANGE_FILL = "#c4501f", "#fdeee7"
GRAY = "#6b6a64"
INK = "#1a1a19"
# no time stamps in the PNG files, so an unchanged figure gives an identical file
DETERMINISTIC = ["-define", "png:exclude-chunks=date,time", "+set", "date:create",
                 "+set", "date:modify"]


# Arial is not a free font: Linux systems usually have a look-alike instead (Liberation
# Sans, Arimo). These are the places where a mounted Windows partition has the real one.
ARIAL_FILES = ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf")
ARIAL_DIRS = ("/mnt/*/Windows/Fonts", "/media/*/*/Windows/Fonts",
              "/run/media/*/*/Windows/Fonts")


@contextlib.contextmanager
def arial_fonts():
    """Environment variables with which LibreOffice and Graphviz find the real Arial.

    If Arial is not installed, the font files in $ARIAL_DIR or on a mounted Windows
    partition are read through a temporary fontconfig file; nothing is installed or copied.
    """
    env = dict(os.environ)
    match = subprocess.run(["fc-match", "-f", "%{family}", "Arial"], capture_output=True,
                           text=True).stdout
    if "Arial" in match.split(","):
        yield env
        return
    folders = [env["ARIAL_DIR"]] if env.get("ARIAL_DIR") else \
        sorted(d for pattern in ARIAL_DIRS for d in glob.glob(pattern))
    folder = next((d for d in folders
                   if all(os.path.exists(os.path.join(d, f)) for f in ARIAL_FILES)), None)
    if folder is None:
        print(f"warning: Arial not found, {match or 'another font'} is used instead (install "
              "Arial or set ARIAL_DIR to a folder with arial.ttf, arialbd.ttf, ariali.ttf "
              "and arialbi.ttf)", file=sys.stderr)
        yield env
        return
    with tempfile.TemporaryDirectory(prefix="des-report-arial-") as tmp:
        os.mkdir(os.path.join(tmp, "fonts"))
        for f in ARIAL_FILES:
            os.symlink(os.path.join(folder, f), os.path.join(tmp, "fonts", f))
        conf = os.path.join(tmp, "fonts.conf")
        with open(conf, "w") as f:
            f.write('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
                    f"<fontconfig>\n  <cachedir>{html.escape(tmp)}/cache</cachedir>\n"
                    f"  <dir>{html.escape(tmp)}/fonts</dir>\n"
                    '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
                    "</fontconfig>\n")
        yield dict(env, FONTCONFIG_FILE=conf)


def fn(name, size=9, face="Courier New"):
    return f'<font face="{face}" point-size="{size}">{name}</font>'


def node(title, item, function, extra=""):
    lines = f"<b>{title}</b>" + (f"  [{item}]" if item else "")
    if extra:
        lines += f'<br/><font point-size="9" color="{GRAY}">{html.escape(extra)}</font>'
    return f"<{lines}<br/>{fn(function)}>"


def render(name, dot_source, env=None):
    path = os.path.join(OUT, name + ".dot")
    with open(path, "w") as f:
        f.write(dot_source)
    subprocess.run(["dot", "-Tpng", "-Gdpi=220", "-o", os.path.join(OUT, name + ".png"), path],
                   check=True, env=env)


COMMON = f"""
  graph [fontname="Arial", fontsize=11, bgcolor="white", pad=0.15, newrank=true];
  node  [shape=box, style="rounded,filled", fontname="Arial", fontsize=10.5, fontcolor="{INK}",
         fillcolor="{BLUE_FILL}", color="{BLUE}", penwidth=1.3, margin="0.14,0.06"];
  edge  [color="#4a4a48", arrowsize=0.7, penwidth=1.1, fontname="Arial", fontsize=9.5,
         fontcolor="#3a3a38"];
"""


def des_structure():
    key = f'fillcolor="{ORANGE_FILL}", color="{ORANGE}"'
    io = 'fillcolor="white", color="#8a8984", style="rounded"'
    src = f"""digraph DES {{
  {COMMON}
  ranksep=0.30; nodesep=0.55;
  P   [label="Plaintext block P (64 bits)", {io}];
  IP  [label={node("Initial permutation IP", "2.1", "des_initial_permutation()")}];
  R1  [label={node("Round 1", "2.3, 2.5-2.9", "des_round(state, K1)")}];
  R2  [label={node("Round 2", "", "des_round(state, K2)")}];
  RD  [label="...", shape=plaintext, style=""];
  R16 [label={node("Round 16", "", "des_round(state, K16)")}];
  SW  [label={node("32-bit swap", "2.9", "des_swap_halves()")}];
  IPI [label={node("Inverse initial permutation IP<sup>-1</sup>", "2.2",
                   "des_inverse_initial_permutation()")}];
  C   [label="Ciphertext block C (64 bits)", {io}];

  K    [label="Key K (64 bits, 8 of them parity)", {io}];
  PC1  [label={node("Permuted choice 1", "2.4.1", "des_permuted_choice_1()", "64 -> 56 bits: C0 | D0")}, {key}];
  LS1  [label={node("Left circular shift", "2.4.2", "des_left_circular_shift()", "C, D rotated by des_shift_amount(1)")}, {key}];
  PC21 [label={node("Permuted choice 2", "2.4.3", "des_permuted_choice_2()", "56 -> 48 bits")}, {key}];
  LS2  [label={node("Left circular shift", "2.4.2", "des_left_circular_shift()")}, {key}];
  PC22 [label={node("Permuted choice 2", "2.4.3", "des_permuted_choice_2()")}, {key}];
  KD   [label="...", shape=plaintext, style=""];
  LS16 [label={node("Left circular shift", "2.4.2", "des_left_circular_shift()")}, {key}];
  PC216[label={node("Permuted choice 2", "2.4.3", "des_permuted_choice_2()")}, {key}];

  P -> IP;
  IP -> R1 [label="  L0 | R0"];
  R1 -> R2 [label="  L1 | R1"];
  R2 -> RD; RD -> R16;
  R16 -> SW [label="  L16 | R16"];
  SW -> IPI [label="  R16 | L16"];
  IPI -> C;

  K -> PC1 -> LS1 -> LS2 -> KD -> LS16;
  LS1 -> PC21; LS2 -> PC22; LS16 -> PC216;
  PC21 -> R1 [label="K1 (48)", color="{ORANGE}", fontcolor="{ORANGE}", constraint=false];
  PC22 -> R2 [label="K2", color="{ORANGE}", fontcolor="{ORANGE}", constraint=false];
  PC216 -> R16 [label="K16", color="{ORANGE}", fontcolor="{ORANGE}", constraint=false];

  {{ rank=same; P; K; }}
  {{ rank=same; R1; PC21; }}
  {{ rank=same; R2; PC22; }}
  {{ rank=same; R16; PC216; }}
}}"""
    render("des_structure", src)


def des_round():
    key = f'fillcolor="{ORANGE_FILL}", color="{ORANGE}"'
    io = 'fillcolor="white", color="#8a8984", style="rounded"'
    src = f"""digraph ROUND {{
  {COMMON}
  ranksep=0.32; nodesep=0.6;
  L  [label="L(i-1)  (32 bits)", {io}];
  R  [label="R(i-1)  (32 bits)", {io}];
  E  [label={node("Expansion/permutation E", "2.3", "des_expansion_permutation()", "32 -> 48 bits")}];
  X  [label={node("XOR with round key", "2.5", "des_xor_round_key()", "48 XOR 48 bits")}];
  K  [label="Ki (48 bits)", {key}];
  S  [label={node("S-boxes S1 ... S8", "2.6", "des_sbox_substitution()",
                  "48 -> 32 bits, 8 x des_sbox_lookup(): 6 -> 4")}];
  PP [label={node("Permutation P", "2.7", "des_permutation_p()", "32 -> 32 bits = f(R(i-1), Ki)")}];
  XL [label={node("XOR with left half", "2.8", "des_xor_left_half()", "L(i-1) XOR f")}];
  SW [label={node("Swap of the halves", "2.9", "des_swap_halves()", "(L XOR f) | R  ->  R | (L XOR f)")}];
  LO [label="Li = R(i-1)", {io}];
  RO [label="Ri = L(i-1) XOR f(R(i-1), Ki)", {io}];
  subgraph cluster_f {{
    label="Feistel function f(R, K) - des_feistel()"; labeljust=l; style="rounded,dashed";
    color="#9a9993"; fontcolor="{GRAY}"; fontsize=10;
    E; X; S; PP;
  }}
  R -> E -> X -> S -> PP;
  K -> X;
  PP -> XL [label="  f (32)"];
  L -> XL;
  XL -> SW [label="  L XOR f"];
  R -> SW [label="R(i-1)", style=dashed];
  SW -> LO; SW -> RO;
  {{ rank=same; L; R; }}
  {{ rank=same; X; K; }}
  {{ rank=same; LO; RO; }}
}}"""
    render("des_round", src)


def network(name="network", face="Courier New", size=9.5, env=None):
    """face, size: the font of the program names"""
    src = f"""graph NET {{
  graph [fontname="Arial", fontsize=11, bgcolor="white", pad=0.15, rankdir=LR, nodesep=0.5,
         ranksep=0.7];
  node  [shape=box, style="rounded,filled", fontname="Arial", fontsize=10.5, fontcolor="{INK}",
         fillcolor="{BLUE_FILL}", color="{BLUE}", penwidth=1.3, margin="0.16,0.08"];
  edge  [color="#4a4a48", penwidth=1.3, fontname="Arial", fontsize=9.5, fontcolor="#3a3a38"];
  subgraph cluster_host {{
    label="Host computer (Linux, Docker Engine) - docker-compose.yml"; labeljust=l;
    style="rounded"; color="#9a9993"; fontcolor="{GRAY}";
    A [label=<<b>machine-a</b>  (container = computer A)<br/>hostname machine-a<br/>eth0  172.28.10.10/24<br/>{fn("tcpClient -s 172.28.10.20", size, face)}<br/><font point-size="9" color="{GRAY}">Machine A: sends first</font>>];
    BR [label=<<b>des_lan</b> (virtual Ethernet switch)<br/>Linux bridge  des-lan0<br/>subnet 172.28.10.0/24<br/>gateway 172.28.10.1>, fillcolor="#f3f3f1", color="#8a8984"];
    B [label=<<b>machine-b</b>  (container = computer B)<br/>hostname machine-b<br/>eth0  172.28.10.20/24<br/>{fn("tcpServer   (0.0.0.0:9000)", size, face)}<br/><font point-size="9" color="{GRAY}">Machine B: receives first</font>>];
    S [label=<<b>sniffer</b> (optional)<br/>{fn("tcpdump -i des-lan0", size, face)}<br/><font point-size="9" color="{GRAY}">sees only IV + ciphertext</font>>, fillcolor="{ORANGE_FILL}", color="{ORANGE}"];
  }}
  A -- BR [label="veth pair"];
  BR -- B [label="veth pair"];
  BR -- S [style=dashed, label="capture"];
  A -- B [style=bold, color="{BLUE}", fontcolor="{BLUE}", constraint=false,
          label=<TCP 172.28.10.10:&lt;ephemeral&gt;  &lt;-&gt;  172.28.10.20:9000<br/>frame = length | mode | IV | DES ciphertext>];
}}"""
    render(name, src, env)


def avalanche():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def load(name):
        with open(os.path.join(ROOT, "test_examples", name)) as f:
            return [int(r["differing_bits"]) for r in csv.DictReader(f)]

    plain = load("avalanche_plaintext_bit4.csv")
    key = load("avalanche_key_bit4.csv")
    xs = list(range(len(plain)))
    labels = ["0"] + [str(i) for i in range(1, 17)] + ["IP⁻¹"]

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5})
    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=220)
    surface = "#fcfcfb"
    fig.patch.set_facecolor(surface)
    ax.set_facecolor(surface)
    ax.axhline(32, color="#a3a29b", lw=1.2, ls=(0, (4, 3)), zorder=1)
    ax.text(0.1, 33.4, "half of the 64 bits", color=GRAY, fontsize=8.5)
    for data, color, name, nudge in ((plain, BLUE, "plaintext bit 4", 1.7),
                                     (key, "#eb6834", "key bit 4", -1.7)):
        ax.plot(xs, data, color=color, lw=2, marker="o", ms=4.5, mfc=color,
                mec=surface, mew=1.2, zorder=3, label=name + " flipped")
        ax.text(xs[-1] + 0.45, data[-1] + nudge, f"{name}: {data[-1]}", color=INK,
                fontsize=8.5, va="center")
    ax.set_xticks(xs, labels)
    ax.set_xlim(-0.4, xs[-1] + 3.3)
    ax.set_ylim(0, 48)
    ax.set_yticks(range(0, 49, 8))
    ax.set_xlabel("round", color=GRAY)
    ax.set_ylabel("bits that differ (of 64)", color=GRAY)
    ax.grid(axis="y", color="#e6e5e0", lw=0.8, zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#b9b8b2")
    ax.tick_params(colors=GRAY, labelcolor=INK)
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "avalanche.png"), facecolor=surface)
    plt.close(fig)


def trim_screenshots():
    for path in sorted(glob.glob(os.path.join(FIG, "*.png"))):
        out = os.path.join(OUT, os.path.basename(path))
        subprocess.run(["convert", path, "-trim", "+repage", "-bordercolor", "#1b1d1e",
                        "-border", "10", *DETERMINISTIC, out], check=True)


def stack_settings():
    """machine-a above machine-b, with a white gap: one figure instead of two."""
    a = os.path.join(OUT, "net_01_settings_machine-a.png")
    b = os.path.join(OUT, "net_02_settings_machine-b.png")
    if os.path.exists(a) and os.path.exists(b):
        subprocess.run(["convert", a, "-size", "10x16", "xc:white", b, "-background", "white",
                        "-append", *DETERMINISTIC, os.path.join(OUT, "net_settings_both.png")],
                       check=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    des_structure()
    des_round()
    network()
    with arial_fonts() as env:
        network("network_arial", "Arial", 10.5, env)
    avalanche()
    trim_screenshots()
    stack_settings()
    print("figures written to", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
