"""Generate the figures of the Ethereum transaction note.

python3 figures.py
  -> images/ethereum-transaction_concept.webp  （手書きの SVG。最大手数料の枠と、実際に払う手数料）
  -> images/ethereum-transaction_nested.webp   （手書きの SVG。中の呼び出しの失敗と status）
SVG は標準ライブラリだけで組み立て、Chrome の headless で 2 倍の解像度の PNG に描いてから、
Pillow で WebP にする。比率は模式的で、実際の値とは対応しない。
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE = "#d4a24c"
RED_PALE, GREEN, GREEN_PALE = "#fbe3e3", "#8fae86", "#e9f1e6"


def to_webp(png, name):
    (HERE / "images").mkdir(exist_ok=True)
    Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


class Svg:
    def __init__(self, width, height, title):
        self.w, self.h = width, height
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

    def text(self, x, y, s, size=24, color=INK, anchor="middle", rotate=None):
        r = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" '
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

    def save(self, name):
        svg_text = "\n".join(self.parts + ["</svg>"]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text(svg_text, encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            to_webp(png, name)


def concept_figure():
    """The fee of a type 2 transaction as areas: width is gas, height is the price per gas."""
    f = Svg(960, 540, "取引の手数料を gas の量と 1 gas あたりの額の面積で表した図")
    x0, x_used, x_lim = 200, 560, 760   # gas axis
    y0, y_base, y_prio, y_max = 430, 270, 205, 100   # price axis (top is larger)

    # Outer frame: gasLimit x maxFeePerGas, the maximum fee.
    f.box(x0, y_max, x_lim - x0, y0 - y_max, FILL, SUB, sw=2.5, dash="10 7", rx=0)
    # Painted part: used gas x (base fee + priority fee), the actual fee.
    f.box(x0, y_base, x_used - x0, y0 - y_base, OCHRE, "none", rx=0)
    f.box(x0, y_prio, x_used - x0, y_base - y_prio, ACCENT, "none", rx=0)
    cx = (x0 + x_used) / 2
    f.text(cx, (y0 + y_base) / 2 + 9, "base fee の分 → 焼却", 26)
    f.text(cx, (y_base + y_prio) / 2 + 9, "priority fee の分 → 参加者", 24)
    f.text(cx, (y_prio + y_max) / 2 + 9, "単価の上限までの余り", 24, SUB)
    rx = (x_used + x_lim) / 2
    f.text(rx, 250, "使わずに", 24, SUB)
    f.text(rx, 284, "済んだ gas", 24, SUB)

    # Axes.
    f.line(x0, y0, x0, y_max - 30, INK, sw=3, arrow="ink")
    f.line(x0, y0, x_lim + 50, y0, INK, sw=3, arrow="ink")
    f.text(70, 265, "1 gas あたりの額", 24, INK, rotate=-90)
    f.text(x_lim + 60, y0 + 8, "gas の量", 24, INK, anchor="start")
    for y, label in ((y_max, "maxFeePerGas"), (y_base, "base fee")):
        f.line(x0 - 10, y, x0, y, INK, sw=2)
        f.text(x0 - 16, y + 8, label, 24, INK, anchor="end")
    for x, label in ((x_used, "使った gas"), (x_lim, "gasLimit")):
        f.line(x, y0, x, y0 + 10, INK, sw=2)
        f.text(x, y0 + 40, label, 24, INK)
    f.text(480, 60, "外枠：最大手数料（gasLimit × maxFeePerGas）", 24, SUB)
    f.text(480, 515, "塗った面積が実際に払う手数料", 26, INK)
    f.save("ethereum-transaction_concept.webp")


def nested_figure():
    """A failed inner call: the caller ignores it (status 1) or checks it and reverts (status 0)."""
    f = Svg(960, 540, "中の呼び出しが失敗しても、呼び出し元が受け流せば status は 1 になる")
    rows = (
        (20, "トップレベルの実行：中の失敗を受け流す",
         ("③ 結果を確かめず", "最後まで進む"), PALE, ACCENT,
         ("status 1", "成功として残る"), GREEN_PALE, GREEN),
        (290, "トップレベルの実行：中の失敗を確かめる",
         ("③ 失敗を見て", "REVERT で中止"), PALE, ACCENT,
         ("status 0", "状態の変更を", "取り消す"), RED_PALE, RED),
    )
    for top, title, step3, fill3, stroke3, result, rfill, rstroke in rows:
        f.box(30, top, 700, 210, FILL, SUB, sw=2, rx=12)
        f.text(52, top + 38, title, 22, INK, anchor="start")
        by, bh = top + 66, 124
        mid = by + bh / 2
        # ① and ② and ③ inside the top-level execution.
        f.box(50, by, 170, bh, PALE, ACCENT, sw=2)
        f.text(135, mid - 6, "① 処理を", 22)
        f.text(135, mid + 24, "始める", 22)
        f.box(255, by, 230, bh, RED_PALE, RED, sw=2, dash="8 6")
        f.text(370, mid - 22, "② 別のコントラクト", 21)
        f.text(370, mid + 6, "を呼ぶ", 21)
        f.text(370, mid + 38, "× 中で失敗", 21, RED)
        f.box(520, by, 190, bh, fill3, stroke3, sw=2)
        f.text(615, mid - 6, step3[0], 21)
        f.text(615, mid + 24, step3[1], 21)
        f.line(222, mid, 250, mid, INK, sw=3, arrow="ink")
        f.line(487, mid, 515, mid, INK, sw=3, arrow="ink")
        f.line(712, mid, 768, mid, INK, sw=3, arrow="ink")
        # Result in the receipt.
        f.box(775, by, 160, bh, rfill, rstroke, sw=2.5)
        n = len(result)
        for i, s in enumerate(result):
            f.text(855, mid + 8 + (i - (n - 1) / 2) * 30, s, 22 if i else 24)
    f.save("ethereum-transaction_nested.webp")


if __name__ == "__main__":
    concept_figure()
    nested_figure()
