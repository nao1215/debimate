"""CQRS - コマンドとクエリの分離 の図を生成する。

再生成（標準ライブラリだけで動く）:
    python3 content/notes/software-architecture/cqrs/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent

INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=3, arrow=False):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{m}/>')

    def save(self, path):
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    """左に明細まで持つ集約（木）、右に必要な列だけの平らな一覧を置く。

    集約 1 つが一覧の 1 行に対応し、明細は一覧に現れない。赤い破線の枠は
    業務規則を検査する単位（集約）を表す。
    """
    f = Svg(960, 540, "CQRS の更新モデルと読み取りモデルの形")

    f.text(230, 46, "更新モデル（集約）", 28, weight="normal")
    f.text(230, 80, "業務規則を守る", 24, SUB)
    f.text(760, 46, "読み取りモデル（一覧）", 28, weight="normal")
    f.text(760, 80, "表示の形と速さを守る", 24, SUB)

    # Left: three Order aggregates, each a small tree inside its rule boundary.
    band_h, child_h, gap = 116, 34, 4
    tops = (100, 226, 352)
    for i, top in enumerate(tops):
        f.box(40, top, 380, band_h, "none", ACCENT, sw=3, dash="10 7", rx=12)
        cy = top + band_h / 2
        f.box(62, cy - 26, 120, 52, PALE, ACCENT, sw=3)
        f.text(122, cy + 9, "Order", 26)
        c0 = cy - (3 * child_h + 2 * gap) / 2
        for j in range(3):
            y = c0 + j * (child_h + gap)
            f.line(182, cy, 250, y + child_h / 2, ACCENT, sw=3)
            f.box(250, y, 150, child_h, PALE, ACCENT, sw=2.5, rx=6)
            if i == 0:
                f.text(325, y + child_h - 8, ("明細", "明細", "状態")[j], 24)

    # Right: one flat table, one row per aggregate, only the columns it needs.
    cols = (("番号", 100), ("合計", 120), ("状態", 100))
    tx, ty, rh = 600, 190, 52
    rows = (("o-1", "3,000", "確定"), ("o-2", "1,200", "確定"),
            ("o-3", "800", "取消"))
    x = tx
    for name, w in cols:
        f.box(x, ty, w, rh, OCHRE_PALE, OCHRE, sw=2.5, rx=0)
        f.text(x + w / 2, ty + rh / 2 + 9, name, 24, weight="normal")
        x += w
    for r, row in enumerate(rows):
        x, y = tx, ty + rh * (r + 1)
        for (name, w), v in zip(cols, row):
            f.box(x, y, w, rh, "#ffffff", OCHRE, sw=2.5, rx=0)
            f.text(x + w / 2, y + rh / 2 + 9, v, 24)
            x += w

    # Each aggregate becomes one row; the detail lines are left behind.
    for i, top in enumerate(tops):
        cy = top + band_h / 2
        ry = ty + rh * (i + 1) + rh / 2
        f.line(424, cy, tx - 10, ry, SUB, sw=3, arrow=True)
    f.text(512, 150, "必要な列だけ", 24, SUB)

    # Which request goes where.
    f.text(230, 516, "コマンドはここを通る", 24, SUB)
    f.text(760, 430, "クエリはここを読む", 24, SUB)

    (HERE / "images").mkdir(exist_ok=True)
    f.save(HERE / "images" / "cqrs_concept.svg")


def chronology_figure():
    """MediaWiki の ChronologyProtector の待ち方を時間軸で描く。

    編集を保存した要求の終わりに primary の書き込み位置 P を記録し、
    約 10 秒以内に同じユーザーから来た要求は、複製が P に追い付くまで待つ。
    黄土色は遅れと待ちを表す。
    """
    f = Svg(960, 540, "ChronologyProtector が複製の追い付きを待つ様子")
    lanes = {"primary": 170, "複製": 300, "ユーザー": 430}
    for name, y in lanes.items():
        f.text(24, y + 9, name, 24, SUB, anchor="start")
        f.line(170, y, 930, y, "#cccccc", sw=2)

    # ① 保存: ユーザーから primary へ書き、位置 P を記録する。
    f.line(240, lanes["ユーザー"] - 12, 240, lanes["primary"] + 14, SUB, sw=3, arrow=True)
    f.parts.append(f'<circle cx="240" cy="{lanes["primary"]}" r="11" fill="{ACCENT}"/>')
    f.text(220, lanes["primary"] - 30, "書いた位置 P を記録", 24, anchor="start")
    f.text(240, 480, "① 編集を保存", 24)

    # 複製は P まで遅れている。
    y = lanes["複製"]
    f.box(240, y - 12, 330, 24, OCHRE_PALE, OCHRE, sw=2, rx=4)
    f.text(405, y - 26, "複製の遅れ", 24, SUB)
    f.parts.append(f'<circle cx="570" cy="{y}" r="11" fill="{ACCENT}"/>')
    f.text(590, y + 9, "P に追い付く", 24, anchor="start")

    # ② 約 10 秒以内の要求は追い付くまで待ってから複製を読む。
    y = lanes["ユーザー"]
    f.parts.append(
        f'<line x1="430" y1="{y}" x2="560" y2="{y}" stroke="{OCHRE}" '
        'stroke-width="6" stroke-dasharray="10 8"/>')
    f.text(495, y - 18, "待つ", 24, SUB)
    f.line(570, y - 12, 570, lanes["複製"] + 16, SUB, sw=3, arrow=True)
    f.text(430, 480, "② 履歴を開く", 24)
    f.text(592, y - 18, "新しい編集が出る", 24, anchor="start")
    for cx in (240, 430):
        f.parts.append(f'<circle cx="{cx}" cy="{y}" r="8" fill="{SUB}"/>')

    f.text(480, 50, "同じユーザーの約 10 秒以内の要求だけが待つ", 26)
    f.text(480, 528, "数秒で追い付かなければ打ち切り、古い値を返す", 24, SUB)

    f.save(HERE / "images" / "cqrs_chronology.svg")


if __name__ == "__main__":
    concept_figure()
    chronology_figure()
