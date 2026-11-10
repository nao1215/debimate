"""Generate the cover diagram of the Bitcoin Script note as a hand-written SVG.

The stack of P2PKH, one column per step: the x axis is the step, the blocks
in a column are the stack after that step (top of the stack is the highest
block). The unlocking script pushes the signature and the public key (blue),
then the locking script duplicates, hashes and compares (ochre), and only
`true` (gray-green, success) is left. The steps are the table in the note body.

Run: python3 content/notes/blockchain-systems/bitcoin-script/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED_PALE = "#fbe3e3"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
            '<marker id="arrowred" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def circle(self, cx, cy, r, fill, stroke, sw=3, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def box(self, x, y, w, h, fill, stroke, sw=3, rx=14):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def arrow(self, x1, y1, x2, y2, color=SUB, sw=4):
        m = "arrowred" if color == RED else "arrow"
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" marker-end="url(#{m})"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


# (instruction label lines, stack after the step from bottom to top)
STEPS = [
    (["<sig>"], ["sig"]),
    (["<pub>"], ["sig", "pub"]),
    (["DUP"], ["sig", "pub", "pub"]),
    (["HASH160"], ["sig", "pub", "h"]),
    (["<H>"], ["sig", "pub", "h", "H"]),
    (["EQUAL", "VERIFY"], ["sig", "pub"]),
    (["CHECK", "SIG"], ["true"]),
]
UNLOCK = 2  # the first two steps are the unlocking script


def style(value):
    if value in ("sig", "pub"):
        return ACCENT, ACCENT, INK
    if value == "true":
        return GREEN, GREEN, INK
    return OCHRE_PALE, OCHRE, INK


def concept_figure():
    f = Svg(960, 540, "P2PKH の実行で、スタックに値が積まれて消えていく様子")
    x0, col, bw, bh, gap = 30, 128, 108, 54, 6
    base = 405

    # Bands: who supplied the instructions of each step.
    split = x0 + col * UNLOCK
    f.box(x0, 34, col * UNLOCK - 6, 74, PALE, ACCENT, sw=2.5, rx=10)
    f.text(x0 + (col * UNLOCK - 6) / 2, 82, "アンロック", 26, weight="normal")
    f.box(split + 6, 34, col * (len(STEPS) - UNLOCK) - 6, 74, OCHRE_PALE, OCHRE, sw=2.5, rx=10)
    f.text(split + 6 + (col * (len(STEPS) - UNLOCK) - 6) / 2, 82,
           "ロック（出力に書かれた条件）", 26, weight="normal")

    for i, (label, stack) in enumerate(STEPS):
        cx = x0 + col * i + col / 2
        for depth, value in enumerate(stack):
            fill, stroke, color = style(value)
            y = base - (depth + 1) * (bh + gap)
            f.box(cx - bw / 2, y, bw, bh, fill, stroke, sw=2.5, rx=8)
            f.text(cx, y + bh / 2 + 9, value, 26, color)
        for k, line in enumerate(label):
            f.text(cx, base + 38 + k * 30, line, 24, SUB)

    f.parts.append(
        f'<line x1="{x0}" y1="{base + 4}" x2="{x0 + col * len(STEPS)}" '
        f'y2="{base + 4}" stroke="{SUB}" stroke-width="2.5"/>')
    f.text(480, 525, "左から右へ 1 命令ずつ実行し、最後に true だけが残る", 24, SUB)

    f.save(HERE / "images" / "bitcoin-script_concept.svg")


def token_row(f, x, y, tokens, h=76):
    """Draw instruction tokens left to right; return the x after the last one."""
    for label, w, fill, stroke, dash in tokens:
        d = ' stroke-dasharray="8 6"' if dash else ""
        f.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="2.5"{d}/>')
        lines = label.split("\n")
        for k, line in enumerate(lines):
            ty = y + h / 2 + 9 - (len(lines) - 1) * 14 + k * 28
            f.text(x + w / 2, ty, line, 24, INK if not dash else SUB)
        x += w + 8
    return x


def split_figure():
    f = Svg(960, 540, "scriptSig と scriptPubKey を連結して実行する作りと、分けて実行する作り")
    lock = [("DUP", 84), ("HASH\n160", 84), ("<H>", 70), ("EQUAL\nVERIFY", 104), ("CHECK\nSIG", 90)]

    # Early implementation: one concatenated script.
    f.text(30, 44, "v0.3.4 まで: 連結して 1 回だけ実行", 26, anchor="start")
    y = 64
    x = token_row(f, 30, y, [("<1>", 64, PALE, ACCENT, False),
                             ("OP_\nRETURN", 104, PALE, ACCENT, False)])
    stop = x - 4
    f.parts.append(f'<line x1="{stop}" y1="{y - 10}" x2="{stop}" y2="{y + 86}" '
                   f'stroke="{RED}" stroke-width="4"/>')
    token_row(f, x + 4, y, [(n, w, "#ffffff", OCHRE, True) for n, w in lock])
    f.text(30 + (stop - 30) / 2, y + 110, "使う側の命令", 24, SUB)
    f.text(x + 4 + 240, y + 110, "条件の命令は実行されない", 24, SUB)
    f.box(30, 206, 900, 52, OCHRE_PALE, OCHRE, sw=2, rx=10)
    f.text(480, 241, "1（真）が残って合格、条件を満たさずに出力を使える", 24)

    # Current implementation: two runs, only the stack is handed over.
    f.text(30, 326, "現在: 2 回に分けて実行し、スタックだけ渡す", 26, anchor="start")
    y = 346
    x = token_row(f, 30, y, [("<sig>", 74, PALE, ACCENT, False),
                             ("<pub>", 74, PALE, ACCENT, False)])
    f.arrow(x + 4, y + 38, x + 62, y + 38)
    token_row(f, x + 72, y, [(n, w, OCHRE_PALE, OCHRE, False) for n, w in lock])
    f.text(30 + (x - 38) / 2, y + 112, "1 回目", 24, SUB)
    f.text(x + 72 + 240, y + 112, "2 回目は必ず最後まで実行", 24, SUB)
    f.box(30, 476, 900, 52, GREEN_PALE, GREEN, sw=2, rx=10)
    f.text(480, 511, "条件を満たさなければ、1 回目が何をしても不合格", 24)

    f.save(HERE / "images" / "bitcoin-script_split.svg")


if __name__ == "__main__":
    concept_figure()
    split_figure()
