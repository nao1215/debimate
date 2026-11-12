"""Generate the figures of the Rollup note (hand-written SVG -> WebP).

concept_figure()   L2 executes many transactions; only a state root and the
                   transaction data reach the rollup contract on L1.
bisection_figure() A dispute is narrowed down to the one step where the two
                   claims first differ, and only that step is executed on L1.
withdraw_figure()  The steps of a withdrawal to L1, Optimistic vs ZK.
retention_figure() Blob retention (4096 epochs) against the challenge periods.

Run: python3 content/notes/blockchain-systems/rollup/figures.py
Needs google-chrome (headless, to render the SVG) and Pillow.
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED_PALE = "#fbe3e3"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    """A tiny hand-written SVG builder (white background)."""

    def __init__(self, title, width=960, height=540):
        self.w, self.h = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
                for name, color in (("sub", SUB), ("accent", ACCENT), ("ochre", OCHRE)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="normal" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, r, fill):
        self.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def save(self, name):
        """Render the SVG with headless Chrome at 2x and store it as WebP."""
        IMAGES.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(
                ["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                 "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                 f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)


def concept_figure():
    f = Svg("L2 で実行した多数のトランザクションのうち、L1 に届くのは state root とトランザクションデータだけ")
    # L2: many transactions are executed off L1.
    f.box(24, 24, 912, 266, PALE, rx=16)
    f.text(56, 68, "L2（Ethereum の外のチェーン）", 28, anchor="start")
    for row in range(5):
        for col in range(9):
            f.circle(118 + col * 34, 112 + row * 30, 9, ACCENT)
    f.text(254, 278, "利用者のトランザクション", 24, SUB)
    f.line(416, 172, 456, 172, SUB, sw=4, arrow="sub")
    f.box(466, 112, 196, 120, "#ffffff", ACCENT, sw=3)
    f.text(564, 164, "シーケンサー", 26)
    f.text(564, 200, "順に実行", 24, SUB)
    f.line(668, 172, 708, 172, SUB, sw=4, arrow="sub")
    for i in range(3):
        f.box(722 + i * 8, 104 + i * 8, 150, 112, PALE if i < 2 else "#ffffff",
              ACCENT, sw=3, rx=8)
    # The same transactions, packed tightly into one batch.
    for row in range(5):
        for col in range(9):
            f.circle(769 + col * 11, 154 + row * 11, 3.6, ACCENT)
    f.text(813, 254, "batch（まとめ）", 24)

    # L1: the state root goes to the contract, the data goes into the block.
    f.box(24, 316, 912, 200, FILL, rx=16)
    f.text(56, 360, "L1（Ethereum）", 28, anchor="start")
    f.line(790, 264, 790, 350, SUB, sw=4)
    f.line(790, 350, 480, 350, SUB, sw=4)
    f.line(480, 350, 480, 384, SUB, sw=4, arrow="sub")
    f.line(840, 264, 840, 384, SUB, sw=4, arrow="sub")
    f.box(330, 392, 300, 104, "#ffffff", SUB, sw=3)
    f.text(480, 428, "rollup のコントラクト", 24, SUB)
    f.box(352, 448, 28, 28, ACCENT, rx=4)
    f.text(392, 472, "state root", 24, anchor="start")
    f.box(650, 392, 270, 104, "#ffffff", SUB, sw=3)
    f.text(785, 428, "L1 のブロック", 24, SUB)
    f.box(672, 452, 28, 20, ACCENT, rx=3)
    f.text(712, 472, "トランザクションデータ", 18, anchor="start")
    # The checker is a second actor on L1 (ochre), not a failure.
    f.box(40, 396, 248, 96, OCHRE_PALE, OCHRE, sw=3)
    f.text(164, 434, "異議 または", 24)
    f.text(164, 468, "validity proof", 24)
    f.line(292, 444, 322, 444, OCHRE, sw=4, arrow="ochre")
    f.save("rollup_concept.webp")


def bisection_figure():
    f = Svg("2 人の主張が最初に食い違う 1 ステップまで絞り、L1 はその 1 ステップだけを実行する",
            height=590)
    x0, cw, n = 260, 40, 16

    def x(i):
        return x0 + i * cw

    f.text(x0 - 20, 40, "ステップ", 22, SUB, anchor="end")
    for i in (0, 4, 8, 12, 16):
        f.text(x(i), 40, str(i), 22, SUB)
    rows = (("提出者の主張", 60, OCHRE_PALE, OCHRE), ("異議を出した人", 124, PALE, ACCENT))
    for label, y, fill, stroke in rows:
        f.text(x0 - 20, y + 34, label, 24, anchor="end")
        for i in range(n):
            differ = i >= 10
            f.box(x(i) + 2, y, cw - 4, 48, fill if differ else PALE,
                  stroke if differ else ACCENT, sw=2, rx=4)
    f.text(x(5), 214, "10 ステップ目までは同じ状態", 22, SUB)
    f.text(x(13), 214, "11 ステップ目から食い違う", 22, SUB)
    f.text(x0 - 20, 262, "途中の状態を比べて、範囲を半分ずつ絞る", 22, SUB, anchor="start")

    # Each question halves the range that still contains the first difference.
    ranges = (("最初の範囲", 0, 16), ("8 で一致", 8, 16), ("12 で不一致", 8, 12),
              ("10 で一致", 10, 12), ("11 で不一致", 10, 11))
    for k, (label, lo, hi) in enumerate(ranges):
        y = 282 + k * 46
        f.text(x0 - 20, y + 26, label, 24, anchor="end")
        last = k == len(ranges) - 1
        f.box(x(lo) + 2, y, (hi - lo) * cw - 4, 34, RED_PALE if last else FILL,
              RED if last else SUB, sw=2, rx=4)
    f.line(x(10) + 20, 282 + 4 * 46 + 40, x(10) + 20, 530, RED, sw=3, arrow=None)
    f.text(x(10) + 20, 562, "L1 は 11 ステップ目だけを実行して判定する", 24)
    f.save("rollup_bisection.webp")


def _steps(f, y, steps):
    """A row of step boxes joined by arrows. steps: (lines, width, fill, stroke)."""
    x = 40
    for i, (lines, w, fill, stroke) in enumerate(steps):
        f.box(x, y, w, 96, fill, stroke, sw=2.5, rx=8)
        for j, s in enumerate(lines):
            f.text(x + w / 2, y + 40 + j * 32 - (len(lines) - 1) * 6, s, 24)
        if i < len(steps) - 1:
            f.line(x + w + 4, y + 48, x + w + 26, y + 48, SUB, sw=3, arrow="sub")
        x += w + 34


def withdraw_figure():
    f = Svg("L1 に戻す出金の手順。Optimistic Rollup は challenge 期間を待ち、"
            "ZK Rollup は証明の検証を待つ", height=420)
    f.text(40, 44, "Optimistic Rollup（OP Mainnet の例）", 24, anchor="start")
    _steps(f, 64, [(["L2 で", "出金を送る"], 140, "#ffffff", SUB),
                   (["batch を", "L1 に提出"], 140, "#ffffff", SUB),
                   (["L1 で出金", "を証明"], 140, "#ffffff", SUB),
                   (["challenge 期間", "（7 日）"], 210, OCHRE_PALE, OCHRE),
                   (["L1 で", "受け取る"], 140, "#ffffff", SUB)])
    f.text(40, 236, "ZK Rollup", 24, anchor="start")
    _steps(f, 256, [(["L2 で", "出金を送る"], 140, "#ffffff", SUB),
                    (["batch を", "L1 に提出"], 140, "#ffffff", SUB),
                    (["validity proof を", "作り、L1 が検証"], 210, PALE, ACCENT),
                    (["L1 で", "受け取る"], 140, "#ffffff", SUB)])
    f.text(480, 400, "箱の幅は時間の長さを表していない", 22, SUB)
    f.save("rollup_withdraw.webp")


def retention_figure():
    """Blob retention (4096 epochs) against the withdrawal challenge periods."""
    blob_days = 4096 * 32 * 12 / 86400
    arbitrum_days = 45818 * 12 / 86400
    rows = [("blob の保持", blob_days, PALE, ACCENT, f"約 {blob_days:.0f} 日以上（4096 epoch）"),
            ("OP Mainnet", 7, OCHRE_PALE, OCHRE, "7 日"),
            ("Arbitrum One", arbitrum_days, OCHRE_PALE, OCHRE, f"約 {arbitrum_days:.1f} 日")]
    f = Svg("blob の保持期間約 18 日の内側に、約 1 週間の challenge 期間が収まる", height=500)
    x0, per_day, top = 250, 30, 70
    for d in range(0, 21, 5):
        x = x0 + d * per_day
        f.line(x, top - 10, x, 400, "#dddddd", sw=2)
        f.text(x, 435, f"{d}", 24, SUB)
    f.text(x0 + 10 * per_day, 478, "日", 24, SUB)
    for i, (label, days, fill, stroke, value) in enumerate(rows):
        y = top + i * 105
        f.text(x0 - 20, y + 45, label, 24, anchor="end")
        f.box(x0, y + 10, days * per_day, 56, fill, stroke, sw=2.5, rx=4)
        end = x0 + days * per_day
        if end + 14 + 20 * len(value) > 940:  # no room on the right: write inside
            f.text(end - 16, y + 47, value, 24, anchor="end")
        else:
            f.text(end + 14, y + 47, value, 24, anchor="start")
    f.save("rollup_retention.webp")


if __name__ == "__main__":
    concept_figure()
    bisection_figure()
    withdraw_figure()
    retention_figure()
