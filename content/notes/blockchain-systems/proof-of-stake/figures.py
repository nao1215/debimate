"""Generate the cover diagram of the Proof of Stake note (Python stdlib only).

concept_figure() draws validators as circles whose area stands for the
effective balance (the weight in consensus). Validators that follow the rules
stay in the set; the one that signed two contradicting votes loses part of its
stake (smaller red circle) and leaves the set.

Run: python3 content/notes/blockchain-systems/proof-of-stake/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE = "#d4a24c"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    """A tiny hand-written SVG builder (960x540, white background)."""

    def __init__(self, title, width=960, height=540):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
                for name, color in (("sub", SUB), ("accent", ACCENT), ("red", RED)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10, opacity=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' fill-opacity="{opacity}"' if opacity != 1 else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}"{o} stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, r, fill, stroke="none", sw=2.5, dash="", opacity=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' fill-opacity="{opacity}"' if opacity != 1 else ""
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{o} '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def path(self, d, stroke, sw=4, fill="none"):
        self.parts.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            'stroke-linecap="round" stroke-linejoin="round"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def check(f, cx, cy, r):
    s = r * 0.42
    f.path(f"M{cx - s:.1f},{cy:.1f} L{cx - s * 0.25:.1f},{cy + s * 0.7:.1f} "
           f"L{cx + s:.1f},{cy - s * 0.65:.1f}", ACCENT, sw=5)


def concept_figure():
    f = Svg("預け入れ額を重みにした投票と、矛盾する署名への罰則")
    f.text(337, 62, "バリデータ（円の面積 = 有効残高）", 28, weight="normal")
    f.box(40, 120, 594, 280, "none", ACCENT, sw=3, dash="10 7", rx=16)
    for cx, r in ((100, 46), (228, 72), (344, 36), (448, 56)):
        f.circle(cx, 262, r, PALE, ACCENT, sw=3)
        check(f, cx, 262, r)
    # The slot the slashed validator used to occupy.
    f.circle(566, 262, 56, "none", SUB, sw=3, dash="8 6")
    f.text(337, 470, "規則どおりの提案・投票 → 報酬", 26, SUB)

    f.text(806, 62, "矛盾する署名", 28, weight="normal")
    f.line(630, 262, 728, 262, SUB, sw=5, arrow="sub")
    f.circle(806, 262, 56, "none", SUB, sw=3, dash="8 6")
    f.circle(806, 262, 38, RED)
    for x in (742, 872):
        f.box(x - 48, 118, 96, 46, "#ffffff", OCHRE, sw=3)
        f.line(x, 164, 806 + (x - 806) * 0.35, 222, OCHRE, sw=3)
    f.text(742, 150, "投票 1", 24)
    f.text(872, 150, "投票 2", 24)
    f.text(807, 152, "≠", 30, RED, weight="normal")
    f.text(806, 470, "担保の減額・強制退出", 26, SUB)
    f.save(HERE / "images" / "proof-of-stake_concept.svg")


def surround_figure():
    """The intervals of the table in the note: A (2->5) against B, C and D."""
    f = Svg("epoch の区間で比べる包囲投票")
    x0, step = 190, 80          # epoch 1 at x0, one epoch = step px

    def ex(e):
        return x0 + (e - 1) * step

    f.text(40, 52, "source.epoch → target.epoch の区間", 26, SUB, anchor="start")
    for e in (2, 5):            # A's endpoints, to judge "strictly inside"
        f.line(ex(e), 92, ex(e), 452, SUB, sw=1.5, dash="6 6")
    rows = (
        ("A", 2, 5, ACCENT, "基準の投票", SUB),
        ("B", 3, 4, OCHRE, "包囲する", INK),
        ("C", 2, 4, OCHRE, "包囲しない（起点が同じ）", SUB),
        ("D", 3, 6, OCHRE, "包囲しない（交差のみ）", SUB),
    )
    for i, (name, src, dst, color, verdict, vcolor) in enumerate(rows):
        y = 130 + i * 90
        f.text(60, y + 9, f"{name}  {src}→{dst}", 26, anchor="start")
        f.line(ex(src), y, ex(dst) - 6, y, color, sw=7)
        f.circle(ex(src), y, 9, "#ffffff", color, sw=4)
        f.circle(ex(dst), y, 9, color, color, sw=4)
        vx = 650
        if name == "B":
            f.path(f"M{vx - 2},{y - 12} L{vx + 22},{y + 12} M{vx + 22},{y - 12} L{vx - 2},{y + 12}", RED, sw=4)
            vx += 36
        f.text(vx, y + 9, verdict, 24, vcolor, anchor="start")
    f.line(ex(1) - 20, 480, ex(6) + 20, 480, SUB, sw=2)
    for e in range(1, 7):
        f.line(ex(e), 474, ex(e), 486, SUB, sw=2)
        f.text(ex(e), 518, str(e), 24, SUB)
    f.text(ex(6) + 40, 518, "epoch", 24, SUB, anchor="start")
    f.save(HERE / "images" / "proof-of-stake_surround.svg")


if __name__ == "__main__":
    concept_figure()
    surround_figure()
