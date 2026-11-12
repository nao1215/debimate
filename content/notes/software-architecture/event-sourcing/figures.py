"""Event Sourcing - 出来事の並びを一次記録にする の図を生成する。

復元時間の図は lab/replay_time_output.txt（lab/replay_time.py の実測）から作る。
読み飛ばしの図（event-sourcing_gap.svg）は、本文の連番 10 と 11 の例を描いた概念図。

再生成:
    uv run --with matplotlib python content/notes/software-architecture/event-sourcing/figures.py
"""

import pathlib
from html import escape

import matplotlib
matplotlib.use("Agg")  # 表示せずファイルへ書く
import matplotlib.pyplot as plt

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GRAY = "#666666"
COLOR_INK = "#1f1f1f"

plt.rcParams.update({
    "figure.figsize": (6, 4),
    "font.size": 11,
    "axes.edgecolor": COLOR_GRAY,
    "text.color": COLOR_INK,
    "axes.labelcolor": COLOR_INK,
    "figure.facecolor": "#ffffff",
    "axes.facecolor": "#ffffff",
    "svg.fonttype": "path",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "-",
    "grid.linewidth": 0.5,
    "savefig.bbox": "tight",
    "savefig.dpi": 144,
    "svg.hashsalt": "event-sourcing",
})

OUT = pathlib.Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)


def save(name: str) -> None:
    path = OUT / name
    plt.savefig(path, metadata={"Date": None})
    plt.close()
    print(f"wrote {path}")


# --- 図1: 現在の状態の復元にかかった時間（lab/replay_time.py の実測） ---
#
# lab/replay_time_output.txt を読む。列は stream の長さと、スナップショット
# 無し・500 件ごと・100 件ごとの (ms, 再生した件数)。
rows = []
for line in (pathlib.Path(__file__).parent / "lab" / "replay_time_output.txt").read_text().splitlines():
    parts = line.replace("|", " ").split()
    if len(parts) == 7 and parts[0].isdigit():
        rows.append([float(v) for v in parts])
n = [r[0] for r in rows]
fig, ax = plt.subplots(figsize=(7.2, 4.0))
ax.plot(n, [r[1] for r in rows], color=COLOR_RED, linewidth=2.0, label="No snapshot")
ax.plot(n, [r[3] for r in rows], color=COLOR_GRAY, linewidth=1.6,
        label="Snapshot every 500 events")
ax.plot(n, [r[5] for r in rows], color=COLOR_BLUE, linewidth=2.0,
        label="Snapshot every 100 events")
ax.set_xlim(0, 5000)
ax.set_ylim(0, None)
ax.set_xlabel("Events in the stream")
ax.set_ylabel("Time to restore the\ncurrent state (ms, measured)")
ax.legend(loc="upper left", frameon=False, fontsize=10)
save("event-sourcing_replay_time.svg")


# --- 図0: 冒頭の概念図（標準ライブラリだけで SVG を書く） ---
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
FILL, PALE = "#f2f2f2", "#eaf1f5"


class Svg:
    def __init__(self, width, height, title):
        marks = "".join(
            f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="8" refY="5" '
            f'markerUnits="userSpaceOnUse" markerWidth="20" markerHeight="20" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
            for n, c in (("gray", COLOR_GRAY), ("blue", COLOR_BLUE)))
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{COLOR_INK}}}</style>',
            f'<defs>{marks}</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=COLOR_INK, weight="normal",
             anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=3, dash="", arrow=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}"{d}{m}/>')

    def save(self, path):
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def table(f, x, y, w, title):
    """読み取りモデルを、見出し付きの平らな表で描く。"""
    f.box(x, y, w, 44, FILL, COLOR_GRAY, rx=0)
    f.text(x + w / 2, y + 31, title, 24, weight="normal")
    for r in range(3):
        f.box(x, y + 44 + r * 26, w, 26, "#ffffff", COLOR_GRAY, rx=0)
    f.line(x + w * 0.45, y + 44, x + w * 0.45, y + 122, COLOR_GRAY, sw=2)


def concept_figure():
    """追記だけのイベントの帯と、そこから導く状態・スナップショット・プロジェクション。

    青はイベント（一次記録）、青の破線は新しく追記するイベント、灰色はイベントから
    作り直せる導出物（今の状態・スナップショット・読み取りモデル）を表す。
    """
    f = Svg(960, 540, "Event Sourcing のイベントの帯と導出物")
    cell, step, x0, band = 90, 96, 60, 162

    f.text(x0, 50, "イベントストア（追記だけ）", 28, weight="normal", anchor="start")
    for i in range(7):
        x = x0 + i * step
        f.box(x, band, cell, 60, PALE, COLOR_BLUE, sw=3)
        f.text(x + cell / 2, band + 39, f"v{i + 1}", 24)
    xn = x0 + 7 * step
    f.box(xn, band, cell, 60, "#ffffff", COLOR_BLUE, sw=3, dash="9 6")
    f.text(xn + cell / 2, band + 39, "v8", 24)
    f.text(xn + cell / 2, band + 100, "追記", 24)
    f.line(xn + cell / 2, band + 76, xn + cell / 2, band + 66, COLOR_BLUE, sw=3,
           arrow="blue")

    # Replay: fold the events from the left into the current state. A
    # snapshot lets the fold start part-way instead of from v1.
    ry, xs = 106, x0 + 5 * step - 3
    f.box(770, ry - 32, 170, 64, FILL, COLOR_GRAY, sw=2.5)
    f.text(855, ry + 9, "今の状態", 26)
    f.line(x0, ry, xs, ry, COLOR_GRAY, sw=3, dash="8 7")
    f.line(xs, ry, 766, ry, COLOR_GRAY, sw=6, arrow="gray")
    f.box(xs - 12, ry - 12, 24, 24, FILL, COLOR_GRAY, sw=2.5, rx=3)
    f.text(xs, ry - 26, "スナップショット", 24, COLOR_GRAY)
    f.line(xs, ry + 14, xs, band - 4, COLOR_GRAY, sw=2.5, dash="5 5")
    f.text(706, ry - 14, "再生", 24, COLOR_GRAY)

    # Projection: the same band feeds read models built later.
    by = band + 86
    for i in range(7):
        cx = x0 + i * step + cell / 2
        f.line(cx, band + 62, cx, by, COLOR_GRAY, sw=2.5)
    f.line(x0 + cell / 2, by, x0 + 6 * step + cell / 2, by, COLOR_GRAY, sw=4)
    for x in (210, 530):
        f.line(x, by, x, 362, COLOR_GRAY, sw=4, arrow="gray")
    f.text(370, 320, "プロジェクション", 24, COLOR_GRAY)
    table(f, 100, 372, 220, "一覧")
    table(f, 420, 372, 220, "集計")
    f.text(370, 528, "読み取りモデル", 24, COLOR_GRAY)

    f.save(OUT / "event-sourcing_concept.svg")


def gap_figure():
    """連番 10 より先に 11 が commit され、projector が 10 を読み飛ばす流れ。"""
    OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
    f = Svg(960, 540, "連番の順と commit の順が入れ替わり、projector が 10 を読み飛ばす")
    x0, w = 250, 120

    def slots(y, states):
        for i, (num, st) in enumerate(zip((8, 9, 10, 11), states)):
            x = x0 + i * (w + 16)
            fill, stroke, dash = {
                "done": (FILL, COLOR_GRAY, ""),
                "read": (PALE, COLOR_BLUE, ""),
                "wait": ("#ffffff", COLOR_GRAY, "8 6"),
                "late": (OCHRE_PALE, OCHRE, ""),
            }[st]
            f.box(x, y, w, 64, fill, stroke, dash=dash)
            f.text(x + w / 2, y + 42, str(num), 26)
        return [x0 + i * (w + 16) + w / 2 for i in range(4)]

    # 1 段目: 11 が先に commit され、projector は 11 まで読む
    f.text(40, 112, "11 が先に", 24, anchor="start")
    f.text(40, 144, "commit", 24, anchor="start")
    cx = slots(84, ["read", "read", "wait", "read"])
    f.text(cx[2], 186, "まだ読めない", 24, COLOR_GRAY)
    f.line(cx[3], 44, cx[3], 78, COLOR_BLUE, arrow="blue")
    f.text(cx[3], 34, "読んだ位置 = 11", 24)

    # 2 段目: 遅れて 10 が commit されるが、位置は 11 のまま
    f.text(40, 332, "10 が遅れて", 24, anchor="start")
    f.text(40, 364, "commit", 24, anchor="start")
    cx = slots(304, ["read", "read", "late", "read"])
    f.line(cx[3], 264, cx[3], 298, COLOR_BLUE, arrow="blue")
    f.text(cx[3], 254, "読んだ位置 = 11", 24)
    r, y = 14, 400
    f.parts.append(
        f'<path d="M{cx[2] - r} {y - r} L{cx[2] + r} {y + r} M{cx[2] + r} {y - r} '
        f'L{cx[2] - r} {y + r}" stroke="{COLOR_RED}" stroke-width="4"/>')
    f.text(cx[2], 446, "位置より前なので読まれない", 24)

    f.box(250, 484, 24, 24, PALE, COLOR_BLUE, rx=4)
    f.text(284, 504, "読み取りモデルに反映済み", 24, anchor="start")
    f.box(560, 484, 24, 24, OCHRE_PALE, OCHRE, rx=4)
    f.text(594, 504, "遅れて commit", 24, anchor="start")
    f.save(OUT / "event-sourcing_gap.svg")


concept_figure()
print(f"wrote {OUT / 'event-sourcing_concept.svg'}")
gap_figure()
print(f"wrote {OUT / 'event-sourcing_gap.svg'}")
