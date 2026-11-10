"""Generate the figures of the Proof of Authority note.

python3 figures.py  -> images/proof-of-authority_concept.svg
                       images/proof-of-authority_round_wait.svg
                       images/proof-of-authority_limits.svg (from lab/limits_output.txt)
"""

import json
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED, NEUTRAL = "#e15759", "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def concept_figure():
    """Only listed keys may sign; they take turns, and a stopped one is skipped."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("許可された署名者だけが順番にブロックへ署名し、止まった署名者の番は別の署名者が埋める")}'
        f'</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=26, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def signer(cx, cy, label, stroke=BLUE, fill=BLUE_PALE, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p.append(f'<circle cx="{cx}" cy="{cy}" r="38" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="3"{d}/>')
        text(cx, cy + 11, label, 32)

    # Left: the fenced list of authorized signers.
    p.append(f'<rect x="40" y="70" width="300" height="320" rx="14" fill="{NEUTRAL}" '
             f'stroke="{SUB}" stroke-width="2"/>')
    text(190, 112, "authorized signers", 26)
    pos = {"A": (120, 185), "B": (260, 185), "C": (120, 295), "D": (260, 295)}
    for k, (x, y) in pos.items():
        signer(x, y, k)
    # D stopped: one red cross.
    x, y = pos["D"]
    p.append(f'<path d="M{x+18} {y-52} l30 30 M{x+48} {y-52} l-30 30" '
             f'stroke="{RED}" stroke-width="6" stroke-linecap="round"/>')
    text(x, y + 72, "stopped", 24, cls="sub")
    # An outsider needs votes to get in.
    signer(190, 482, "E", SUB, "#ffffff", "7 6")
    p.append(f'<path d="M190 442 L190 400" stroke="{SUB}" stroke-width="2.5" '
             f'stroke-dasharray="7 6" marker-end="url(#a)"/>')
    text(248, 476, "joins only by", 24, "start", "sub")
    text(248, 508, "majority vote", 24, "start", "sub")
    p.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" '
             'markerWidth="7" markerHeight="7" orient="auto">'
             f'<path d="M0 0 L10 5 L0 10 z" fill="{SUB}"/></marker></defs>')

    # Right: the chain. Each block carries the signer's seal.
    text(655, 112, "blocks signed in turn", 26)
    blocks = [("A", True), ("B", True), ("C", True), ("A", False)]
    bx, by, bw, bh, gap = 395, 230, 104, 104, 34
    for i, (k, in_turn) in enumerate(blocks):
        x = bx + i * (bw + gap)
        stroke, fill = (BLUE, BLUE_PALE) if in_turn else (OCHRE, OCHRE_PALE)
        p.append(f'<rect x="{x}" y="{by}" width="{bw}" height="{bh}" rx="10" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="3"/>')
        text(x + bw / 2, by + bh / 2 + 12, k, 34)
        if i:
            p.append(f'<path d="M{x - gap + 4} {by + bh / 2} L{x - 4} {by + bh / 2}" '
                     f'stroke="{SUB}" stroke-width="2.5" marker-end="url(#a)"/>')
    # The slot D should have filled, left empty above block 4.
    x4 = bx + 3 * (bw + gap)
    p.append(f'<rect x="{x4}" y="{by - 96}" width="{bw}" height="70" rx="10" '
             f'fill="#ffffff" stroke="{SUB}" stroke-width="2" stroke-dasharray="7 6"/>')
    text(x4 + bw / 2, by - 50, "D's turn", 24, cls="sub")
    text(bx + 1.5 * (bw + gap) - gap / 2 + bw / 2 - 52, by + bh + 46, "in turn", 24, cls="sub")
    text(x4 + bw / 2, by + bh + 46, "out of turn", 24, cls="sub")
    # Limit on consecutive signing.
    text(655, 470, "a signer may sign only 1 of any", 24, cls="sub")
    text(655, 502, "⌊N/2⌋ + 1 consecutive blocks", 24, cls="sub")
    p.append("</svg>")
    (HERE / "images" / "proof-of-authority_concept.svg").write_text("\n".join(p) + "\n")


def _chart(title):
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    return p, text


def round_wait_figure():
    """When QBFT on Besu enters round r (4 × 2^r s per round) and the measured recoveries."""
    p, text = _chart("Besu の QBFT が round r に入るまでの待ち時間の合計と、node3 を再起動してから次のブロックまでの実測")
    left, right, top, bottom, ymax = 130, 900, 70, 440, 140
    rounds = [1, 2, 3, 4, 5]
    starts = [sum(4 * 2 ** k for k in range(r)) for r in rounds]  # 4, 12, 28, 60, 124
    measured = {4: [64.7, 65.1], 5: [128.8, 130.0]}  # lab/output/qbft_trial*.txt

    def y(v):
        return bottom - (bottom - top) * v / ymax

    for v in range(0, ymax + 1, 20):
        p.append(f'<line x1="{left}" y1="{y(v):.1f}" x2="{right}" y2="{y(v):.1f}" stroke="#e4e4e4" stroke-width="1"/>')
        text(left - 14, y(v) + 8, str(v), 24, anchor="end", cls="sub")
    slot = (right - left) / len(rounds)
    for i, (r, v) in enumerate(zip(rounds, starts)):
        cx = left + slot * (i + 0.5)
        p.append(f'<rect x="{cx - 50:.1f}" y="{y(v):.1f}" width="100" height="{bottom - y(v):.1f}" '
                 f'fill="{BLUE_PALE}" stroke="{BLUE}" stroke-width="2"/>')
        text(cx, y(v) - 12, f"{v} s", 24)
        text(cx, bottom + 34, f"round {r}", 24, cls="sub")
        for k, m in enumerate(measured.get(r, [])):
            p.append(f'<circle cx="{cx + 72 + 22 * k:.1f}" cy="{y(m):.1f}" r="8" fill="{OCHRE}" stroke="{INK}" stroke-width="1"/>')
    p.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{SUB}" stroke-width="2"/>')
    text(left - 14, top - 30, "seconds until the next block", 24, anchor="start", cls="sub")
    # Legend.
    p.append(f'<rect x="170" y="112" width="26" height="26" fill="{BLUE_PALE}" stroke="{BLUE}" stroke-width="2"/>')
    text(208, 133, "computed: 4 + 8 + … until round r", 24, anchor="start")
    p.append(f'<circle cx="183" cy="168" r="8" fill="{OCHRE}" stroke="{INK}" stroke-width="1"/>')
    text(208, 176, "measured recovery (4 runs)", 24, anchor="start")
    text(480, 522, "the round that made the recovered block", 24, cls="sub")
    p.append("</svg>")
    (HERE / "images" / "proof-of-authority_round_wait.svg").write_text("\n".join(p) + "\n")


def limits_figure():
    """Minimum online signers for Clique and QBFT, read from lab/limits_output.txt."""
    rows = []
    for line in (HERE / "lab" / "limits_output.txt").read_text().splitlines():
        cols = [c.strip() for c in line.split("|")]
        if len(cols) == 4 and cols[0].isdigit():
            rows.append((int(cols[0]), int(cols[2]), int(cols[3])))
    p, text = _chart("署名者・検証者の数 N ごとに、Clique と QBFT が進み続けるのに必要な台数")
    left, right, top, bottom, ymax = 110, 930, 110, 440, 8

    def y(v):
        return bottom - (bottom - top) * v / ymax

    for v in range(0, ymax + 1, 2):
        p.append(f'<line x1="{left}" y1="{y(v):.1f}" x2="{right}" y2="{y(v):.1f}" stroke="#e4e4e4" stroke-width="1"/>')
        text(left - 14, y(v) + 8, str(v), 24, anchor="end", cls="sub")
    slot = (right - left) / len(rows)
    for i, (n, clique, qbft) in enumerate(rows):
        cx = left + slot * (i + 0.5)
        for dx, v, st, fi in ((-17, clique, BLUE, BLUE_PALE), (17, qbft, OCHRE, OCHRE_PALE)):
            p.append(f'<rect x="{cx + dx - 15:.1f}" y="{y(v):.1f}" width="30" height="{bottom - y(v):.1f}" '
                     f'fill="{fi}" stroke="{st}" stroke-width="2"/>')
        text(cx, bottom + 34, str(n), 24, cls="sub")
    p.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{SUB}" stroke-width="2"/>')
    text(left - 14, 50, "online signers needed", 24, anchor="start", cls="sub")
    p.append(f'<rect x="130" y="72" width="26" height="26" fill="{BLUE_PALE}" stroke="{BLUE}" stroke-width="2"/>')
    text(166, 93, "Clique  ⌊N/2⌋ + 1", 24, anchor="start")
    p.append(f'<rect x="420" y="72" width="26" height="26" fill="{OCHRE_PALE}" stroke="{OCHRE}" stroke-width="2"/>')
    text(456, 93, "QBFT  ⌈2N/3⌉", 24, anchor="start")
    text(520, 522, "N (signers / validators)", 24, cls="sub")
    p.append("</svg>")
    (HERE / "images" / "proof-of-authority_limits.svg").write_text("\n".join(p) + "\n")


if __name__ == "__main__":
    concept_figure()
    round_wait_figure()
    limits_figure()
