"""Generate the cover diagram of the smart contract note.

concept_figure() draws, as a hand-written SVG (stdlib only), one lane for an
ordinary web service (only the operator's server runs the code) and three
lanes for verifying nodes that each apply the same transactions in the same
order to the same state, and reach the same state.

Run: python3 content/notes/blockchain-systems/smart-contract/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                for n, c in (("ink", INK), ("sub", SUB), ("accent", ACCENT), ("red", RED)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle",
             rotate=None):
        r = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}"{r}>{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def lane(f, y, name, block_fill, block_stroke, block_text, end_fill, end_stroke):
    """One row: start state -> transactions 1, 2, 3 -> end state."""
    h = 62
    f.text(200, y + 9, name, 24, INK, anchor="end")
    f.line(330, y, 590, y, SUB, sw=2.5, arrow="sub")
    f.box(220, y - h / 2, 110, h, "#ffffff", SUB, sw=2.5, rx=8)
    f.text(275, y + 9, "前の状態", 24, INK)
    for i, x in enumerate((358, 428, 498)):
        f.box(x, y - 26, 52, 52, block_fill, block_stroke, sw=2.5, rx=6)
        f.text(x + 26, y + 9, str(i + 1), 24, block_text, "normal")
    f.box(595, y - h / 2, 110, h, end_fill, end_stroke, sw=2.5, rx=8)
    f.text(650, y + 9, "後の状態", 24, INK)


def concept_figure():
    f = Svg(960, 540, "運営者のサーバーだけが実行する構成と、各ノードが同じ取引を独立に実行する構成")

    f.text(30, 52, "通常の Web サービス", 26, weight="normal", anchor="start")
    lane(f, 108, "運営者のサーバー", FILL, SUB, SUB, FILL, SUB)
    f.text(730, 117, "運営者だけが計算", 24, SUB, anchor="start")

    f.line(30, 170, 930, 170, "#dddddd", sw=2)

    f.text(30, 218, "スマートコントラクト", 26, weight="normal", anchor="start")
    f.text(453, 218, "同じ取引の並び", 24, SUB)
    for y, name in ((282, "ノード A"), (372, "ノード B"), (462, "ノード C")):
        lane(f, y, name, ACCENT, ACCENT, INK, GREEN_PALE, GREEN)
    f.box(583, 236, 134, 272, "none", GREEN, sw=3, dash="10 7", rx=12)
    f.text(735, 362, "全員が同じ", 24, INK, anchor="start")
    f.text(735, 396, "状態に至る", 24, INK, anchor="start")
    f.save(HERE / "images" / "smart-contract_concept.svg")


OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"


def order_figure():
    """Two transfers of 8 tokens from a balance of 10: the order decides the winner."""
    f = Svg(960, 540, "残高 10 から 8 枚ずつ送る 2 件の取引で、順序が結果を決める様子")
    lanes = [(120, "X が先", "X", "Y"), (330, "Y が先", "Y", "X")]
    for y, head, first, second in lanes:
        f.text(30, y + 10, head, 26, anchor="start")
        x = 150
        items = [
            (120, ["残高 10"], "#ffffff", SUB),
            (176, [f"{first} が 8 枚送る", "成功"], GREEN_PALE, GREEN),
            (120, ["残高 2"], "#ffffff", SUB),
            (176, [f"{second} が 8 枚送る", "残高不足"], OCHRE_PALE, OCHRE),
        ]
        for k, (w, lines, fill, stroke) in enumerate(items):
            f.box(x, y - 50, w, 100, fill, stroke)
            for j, line in enumerate(lines):
                ty = y + 9 - (len(lines) - 1) * 16 + j * 32
                f.text(x + w / 2, ty, line, 24, INK if j == 0 else SUB)
            x += w
            if k < len(items) - 1:
                f.line(x + 8, y, x + 46, y, SUB, sw=3, arrow="sub")
                x += 56
    f.text(480, 480, "同じ 2 件でも、先に実行された方だけが成功する", 24, SUB)
    f.save(HERE / "images" / "smart-contract_order.svg")


if __name__ == "__main__":
    concept_figure()
    order_figure()
