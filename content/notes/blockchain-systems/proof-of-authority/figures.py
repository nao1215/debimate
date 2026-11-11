"""Generate the figures of the Proof of Authority note.

concept_figure()      -> images/proof-of-authority_concept.webp
families_figure()     -> images/proof-of-authority_families.webp
signer_limit_figure() -> images/proof-of-authority_signer_limit.webp
round_wait_figure()   -> images/proof-of-authority_round_wait.webp
limits_figure()       -> images/proof-of-authority_limits.webp (from lab/limits_output.txt)

Run: python3 content/notes/blockchain-systems/proof-of-authority/figures.py
Needs google-chrome (headless, to render the SVG) and Pillow (to write WebP).
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED, NEUTRAL = "#e15759", "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
            '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="7" markerHeight="7" orient="auto">'
            f'<path d="M0 0 L10 5 L0 10 z" fill="{SUB}"/></marker></defs>',
        ]

    def raw(self, s):
        self.p.append(s)

    def text(self, x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" '
                      f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=3, rx=10, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                      f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, label, stroke=BLUE, fill=BLUE_PALE, r=38, size=32, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="3"{d}/>')
        self.text(cx, cy + size * 0.35, label, size)

    def arrow(self, x1, y1, x2, y2, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{SUB}" '
                      f'stroke-width="2.5"{d} marker-end="url(#a)"/>')

    def cross(self, x, y, s=30):
        self.p.append(f'<path d="M{x} {y} l{s} {s} M{x + s} {y} l-{s} {s}" '
                      f'stroke="{RED}" stroke-width="6" stroke-linecap="round"/>')

    def save(self, name):
        """Render the SVG with headless Chrome at 2x and store it as WebP."""
        (HERE / "images").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.p + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(
                ["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                 "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                 f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(
                HERE / "images" / name, "WEBP", quality=90, method=6)


def concept_figure():
    """Only listed keys may sign; they take turns, and a stopped one is skipped."""
    f = Svg(960, 540, "許可された署名者だけが順番にブロックへ署名し、止まった署名者の番は別の署名者が埋める")
    f.box(40, 70, 300, 320, NEUTRAL, SUB, sw=2, rx=14)
    f.text(190, 112, "許可された署名者", 26)
    pos = {"A": (120, 185), "B": (260, 185), "C": (120, 295), "D": (260, 295)}
    for k, (x, y) in pos.items():
        f.circle(x, y, k)
    x, y = pos["D"]
    f.cross(x + 18, y - 52)
    f.text(x, y + 72, "停止", 24, cls="sub")
    # An outsider needs votes to get in.
    f.circle(190, 482, "E", SUB, "#ffffff", dash="7 6")
    f.arrow(190, 442, 190, 400, dash="7 6")
    f.text(248, 476, "一覧に加えられる", 24, "start", "sub")
    f.text(248, 508, "まで署名できない", 24, "start", "sub")

    f.text(655, 112, "順番に作られたブロック", 26)
    blocks = [("A", True), ("B", True), ("C", True), ("A", False)]
    bx, by, bw, bh, gap = 395, 230, 104, 104, 34
    for i, (k, in_turn) in enumerate(blocks):
        x = bx + i * (bw + gap)
        stroke, fill = (BLUE, BLUE_PALE) if in_turn else (OCHRE, OCHRE_PALE)
        f.box(x, by, bw, bh, fill, stroke)
        f.text(x + bw / 2, by + bh / 2 + 12, k, 34)
        if i:
            f.arrow(x - gap + 4, by + bh / 2, x - 4, by + bh / 2)
    x4 = bx + 3 * (bw + gap)
    f.box(x4, by - 96, bw, 70, "#ffffff", SUB, sw=2, dash="7 6")
    f.text(x4 + bw / 2, by - 50, "D の番", 24, cls="sub")
    f.text(bx + (3 * bw + 2 * gap) / 2, by + bh + 46, "順番どおり", 24, cls="sub")
    f.text(x4 + bw / 2, by + bh + 46, "D の代わり", 24, cls="sub")
    f.text(700, 470, "止まった署名者の番は、", 24, cls="sub")
    f.text(700, 502, "動いている別の署名者が埋める", 24, cls="sub")
    f.save("proof-of-authority_concept.webp")


def families_figure():
    """One seal per block (Clique) versus a proposal plus votes (QBFT)."""
    f = Svg(1000, 470, "1 人の署名でブロックになる系統と、提案に投票を集めてブロックになる系統")
    for x0, title in ((20, "1 人が署名する系統（Clique）"), (510, "投票する系統（QBFT）")):
        f.box(x0, 20, 470, 430, "#ffffff", "#cccccc", sw=2, rx=14)
        f.text(x0 + 235, 64, title, 26)

    # Left: block with one seal; a fork may appear and the heavier side wins.
    f.box(70, 110, 170, 120, BLUE_PALE, BLUE)
    f.text(155, 160, "ブロック", 24)
    f.circle(155, 200, "A", BLUE, "#ffffff", r=20, size=22)
    f.text(330, 166, "作った 1 人", 24, cls="sub")
    f.text(330, 198, "の署名だけ", 24, cls="sub")
    # tiny fork
    f.box(70, 290, 70, 50, BLUE_PALE, BLUE, sw=2, rx=6)
    f.box(200, 262, 70, 50, BLUE_PALE, BLUE, sw=2, rx=6)
    f.box(200, 322, 70, 50, OCHRE_PALE, OCHRE, sw=2, rx=6)
    f.arrow(142, 308, 196, 290)
    f.arrow(142, 322, 196, 344)
    f.text(290, 296, "分岐し得る", 22, "start", "sub")
    f.text(290, 352, "重い方を選ぶ", 22, "start", "sub")
    f.text(255, 420, "確定の定義は無い", 24)

    # Right: proposer's block collects commit seals from the voters.
    f.box(560, 110, 170, 120, BLUE_PALE, BLUE)
    f.text(645, 178, "ブロック", 24)
    f.text(645, 256, "提案者 B", 22, cls="sub")
    for i, k in enumerate("BCD"):
        cx = 800 + i * 58
        f.circle(cx, 170, k, OCHRE, OCHRE_PALE, r=24, size=24)
    f.arrow(780, 200, 736, 200)
    f.text(858, 230, "提案者を含む 3 人の投票", 22, cls="sub")
    f.text(858, 258, "（commit seal）", 22, cls="sub")
    f.box(560, 296, 400, 76, NEUTRAL, "#cccccc", sw=2, rx=10)
    f.text(760, 328, "3 人に届かなければ", 22)
    f.text(760, 358, "ブロックを作らずに止まる", 22)
    f.text(745, 420, "ブロックを入れた時点で確定", 24)
    f.save("proof-of-authority_families.webp")


def signer_limit_figure():
    """N=4: a signer may sign one of any 3 consecutive blocks."""
    f = Svg(1000, 450, "署名者 4 人の Clique で、直近 2 ブロックに署名した署名者は次のブロックに署名できない")
    f.text(20, 44, "4 人が動いている場合", 24, "start")
    bw, bh, gap, by = 120, 90, 30, 70
    xs = [60 + i * (bw + gap) for i in range(4)]
    for i, (n, k) in enumerate(((5, "B"), (6, "C"), (7, "D"), (8, "?"))):
        x = xs[i]
        last = k == "?"
        f.box(x, by, bw, bh, "#ffffff" if last else BLUE_PALE, SUB if last else BLUE,
              sw=2 if last else 3, dash="7 6" if last else "")
        f.text(x + bw / 2, by + 34, f"ブロック {n}", 20, cls="sub")
        f.text(x + bw / 2, by + 72, k, 30)
        if i:
            f.arrow(x - gap + 4, by + bh / 2, x - 4, by + bh / 2)
    # bracket over the last three blocks
    bx1, bx2 = xs[1], xs[3] + bw
    f.raw(f'<path d="M{bx1} {by + bh + 14} v14 H{bx2} v-14" fill="none" stroke="{OCHRE}" stroke-width="3"/>')
    f.text((bx1 + bx2) / 2, by + bh + 58, "連続する 3 個（⌊4/2⌋+1）に 1 人 1 回まで", 22)
    # who may sign block 7
    f.text(808, 52, "ブロック 8 に署名できるか", 22, cls="sub")
    for i, (k, ok) in enumerate((("A", True), ("B", True), ("C", False), ("D", False))):
        cx, cy = 700 + i * 72, 120
        f.circle(cx, cy, k, BLUE if ok else SUB, BLUE_PALE if ok else NEUTRAL, r=28, size=26)
        if not ok:
            f.cross(cx + 14, cy - 44, 20)
    f.text(736, 186, "署名できる", 22, cls="sub")
    f.text(880, 186, "直近に署名済み", 22, cls="sub")

    # lower row: only C and D are online
    f.raw(f'<line x1="20" y1="262" x2="980" y2="262" stroke="#dddddd" stroke-width="2"/>')
    f.text(20, 304, "C と D の 2 人だけが動いている場合", 24, "start")
    by2 = 330
    for i, (n, k) in enumerate(((6, "C"), (7, "D"), (8, ""))):
        x = xs[i]
        last = not k
        f.box(x, by2, bw, bh, "#ffffff" if last else BLUE_PALE, SUB if last else BLUE,
              sw=2 if last else 3, dash="7 6" if last else "")
        f.text(x + bw / 2, by2 + 34, f"ブロック {n}", 20, cls="sub")
        if last:
            f.cross(x + bw / 2 - 15, by2 + 46, 30)
        else:
            f.text(x + bw / 2, by2 + 72, k, 30)
        if i:
            f.arrow(x - gap + 4, by2 + bh / 2, x - 4, by2 + bh / 2)
    f.text(xs[3] - 10, by2 + 40, "C も D も直近 2 個に署名済みで、", 22, "start", "sub")
    f.text(xs[3] - 10, by2 + 72, "次のブロックを誰も作れない", 22, "start", "sub")
    f.save("proof-of-authority_signer_limit.webp")


def round_wait_figure():
    """When QBFT on Besu enters round r (4 × 2^r s per round) and the measured recoveries."""
    f = Svg(960, 540, "Besu の QBFT が round r に入るまでの待ち時間の合計と、node3 を再起動してから次のブロックまでの実測")
    left, right, top, bottom, ymax = 130, 900, 70, 440, 140
    rounds = [1, 2, 3, 4, 5]
    starts = [sum(4 * 2 ** k for k in range(r)) for r in rounds]  # 4, 12, 28, 60, 124
    measured = {4: [64.7, 65.1], 5: [128.8, 130.0]}  # lab/output/qbft_trial*.txt

    def y(v):
        return bottom - (bottom - top) * v / ymax

    for v in range(0, ymax + 1, 20):
        f.raw(f'<line x1="{left}" y1="{y(v):.1f}" x2="{right}" y2="{y(v):.1f}" stroke="#e4e4e4" stroke-width="1"/>')
        f.text(left - 14, y(v) + 8, str(v), 24, anchor="end", cls="sub")
    slot = (right - left) / len(rounds)
    for i, (r, v) in enumerate(zip(rounds, starts)):
        cx = left + slot * (i + 0.5)
        f.raw(f'<rect x="{cx - 50:.1f}" y="{y(v):.1f}" width="100" height="{bottom - y(v):.1f}" '
              f'fill="{BLUE_PALE}" stroke="{BLUE}" stroke-width="2"/>')
        f.text(cx, y(v) - 12, f"{v} 秒", 24)
        f.text(cx, bottom + 34, f"round {r}", 24, cls="sub")
        for k, m in enumerate(measured.get(r, [])):
            f.raw(f'<circle cx="{cx + 72 + 22 * k:.1f}" cy="{y(m):.1f}" r="8" fill="{OCHRE}" stroke="{INK}" stroke-width="1"/>')
    f.raw(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{SUB}" stroke-width="2"/>')
    f.text(left - 14, top - 30, "次のブロックまでの秒数", 24, anchor="start", cls="sub")
    f.raw(f'<rect x="170" y="112" width="26" height="26" fill="{BLUE_PALE}" stroke="{BLUE}" stroke-width="2"/>')
    f.text(208, 133, "計算値: round r に入るまでの待ち時間の合計（4+8+…）", 22, anchor="start")
    f.raw(f'<circle cx="183" cy="168" r="8" fill="{OCHRE}" stroke="{INK}" stroke-width="1"/>')
    f.text(208, 176, "実測: 再起動から次のブロックまで（4 回）", 22, anchor="start")
    f.text(515, 522, "次のブロックを作った round（最初の試みは round 0）", 24, cls="sub")
    f.save("proof-of-authority_round_wait.webp")


def limits_figure():
    """Minimum online signers for Clique and QBFT, read from lab/limits_output.txt."""
    rows = []
    for line in (HERE / "lab" / "limits_output.txt").read_text().splitlines():
        cols = [c.strip() for c in line.split("|")]
        if len(cols) == 4 and cols[0].isdigit():
            rows.append((int(cols[0]), int(cols[2]), int(cols[3])))
    f = Svg(960, 540, "署名者・検証者の数 N ごとに、Clique と QBFT が進み続けるのに必要な台数")
    left, right, top, bottom, ymax = 110, 930, 110, 440, 8

    def y(v):
        return bottom - (bottom - top) * v / ymax

    for v in range(0, ymax + 1, 2):
        f.raw(f'<line x1="{left}" y1="{y(v):.1f}" x2="{right}" y2="{y(v):.1f}" stroke="#e4e4e4" stroke-width="1"/>')
        f.text(left - 14, y(v) + 8, str(v), 24, anchor="end", cls="sub")
    slot = (right - left) / len(rows)
    for i, (n, clique, qbft) in enumerate(rows):
        cx = left + slot * (i + 0.5)
        for dx, v, st, fi in ((-17, clique, BLUE, BLUE_PALE), (17, qbft, OCHRE, OCHRE_PALE)):
            f.raw(f'<rect x="{cx + dx - 15:.1f}" y="{y(v):.1f}" width="30" height="{bottom - y(v):.1f}" '
                  f'fill="{fi}" stroke="{st}" stroke-width="2"/>')
        f.text(cx, bottom + 34, str(n), 24, cls="sub")
    f.raw(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{SUB}" stroke-width="2"/>')
    f.text(left - 14, 50, "進み続けるのに必要な台数", 24, anchor="start", cls="sub")
    f.raw(f'<rect x="130" y="72" width="26" height="26" fill="{BLUE_PALE}" stroke="{BLUE}" stroke-width="2"/>')
    f.text(166, 93, "Clique  ⌊N/2⌋ + 1", 24, anchor="start")
    f.raw(f'<rect x="420" y="72" width="26" height="26" fill="{OCHRE_PALE}" stroke="{OCHRE}" stroke-width="2"/>')
    f.text(456, 93, "QBFT  ⌈2N/3⌉", 24, anchor="start")
    f.text(520, 522, "N（署名者・検証者の数）", 24, cls="sub")
    f.save("proof-of-authority_limits.webp")


if __name__ == "__main__":
    concept_figure()
    families_figure()
    signer_limit_figure()
    round_wait_figure()
    limits_figure()
