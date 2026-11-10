"""Side-Channel Attack のノートの図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/security/side-channel-attack/figures.py

図 1 は lab/output.txt（lab/compare_timing.c の実測）を読む。
図 2 は lab/simulate_remote.py のシミュレーションをその場で実行する。
図 3 は lab/output.txt の 2 段目（復元できた秘密の数）を読む。
"""

import pathlib
import sys

import matplotlib

matplotlib.use("Agg")  # 表示せずファイルへ書く
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE / "lab"))
import simulate_remote  # noqa: E402

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GRAY = "#666666"

plt.rcParams.update({
    "figure.figsize": (6.5, 4),
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "-",
    "grid.linewidth": 0.5,
    "savefig.bbox": "tight",
    "savefig.dpi": 144,
    "svg.hashsalt": "side-channel-attack",  # 要素の id を固定する
})

OUT = HERE / "images"
OUT.mkdir(exist_ok=True)


def save(name: str) -> None:
    path = OUT / name
    plt.savefig(path)
    plt.close()
    print(f"wrote {path}")


# --- 図 1: 一致する接頭辞の長さと 1 回の比較の時間（実測） ---
profile = {"early_exit": [], "constant_time": []}
for line in (HERE / "lab" / "output.txt").read_text().splitlines():
    parts = line.split(",")
    if len(parts) == 3 and parts[0] in profile and "/" not in parts[2]:
        profile[parts[0]].append((int(parts[1]), float(parts[2])))

plt.figure()
for name, color, style, marker, label in [
    ("early_exit", COLOR_RED, "-", "o", "Early-exit compare (returns at first mismatch)"),
    ("constant_time", COLOR_BLUE, "--", "s", "Constant-time compare (XOR all bytes)"),
]:
    xs, ys = zip(*profile[name])
    plt.plot(xs, ys, linestyle=style, marker=marker, color=color, label=label)
plt.xlabel("Matching prefix length (bytes of 32)")
plt.ylabel("Time per call (ns, trimmed mean)")
plt.xticks(range(0, 33, 4))
plt.ylim(bottom=0)
plt.legend(loc="upper left", fontsize=9, framealpha=1.0)
save("side_channel_prefix_timing.svg")


# --- 図 2: 試行回数と、1 us の差を当てられる割合（シミュレーション） ---
rows = simulate_remote.run()
counts = [n for n, _ in rows]

plt.figure()
for key, color, style, marker, label in [
    ("mean", COLOR_GRAY, ":", "^", "Mean"),
    ("median", COLOR_GRAY, "-.", "v", "Median"),
    ("p10", COLOR_BLUE, "-", "o", "10th percentile"),
    ("p10+delay", COLOR_RED, "--", "s", "10th percentile, server adds 0-100 us random delay"),
]:
    plt.plot(counts, [row[key] for _, row in rows], linestyle=style, marker=marker,
             color=color, label=label)
plt.axhline(0.5, color=COLOR_GRAY, linewidth=0.8, label="Coin flip (0.5)")
plt.xscale("log")
plt.xlabel("Requests per candidate (log scale)")
plt.ylabel("Rate of picking the slower candidate")
plt.ylim(0.45, 1.25)
plt.yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
plt.legend(loc="upper left", fontsize=9, framealpha=1.0)
save("side_channel_remote_simulation.svg")


# --- 図 3: 1 候補あたりのサンプル数と、20 個の秘密のうち復元できた数（実測） ---
recovered = {"early_exit": [], "constant_time": []}
for line in (HERE / "lab" / "output.txt").read_text().splitlines():
    parts = line.split(",")
    if len(parts) == 3 and parts[0] in recovered and "/" in parts[2]:
        ok, total = parts[2].split("/")
        recovered[parts[0]].append((int(parts[1]), int(ok), int(total)))

samples = [n for n, _, _ in recovered["early_exit"]]
total = recovered["early_exit"][0][2]
pos = range(len(samples))
width = 0.38

plt.figure(figsize=(7.2, 4.0))
for offset, name, color, label in [
    (-width / 2, "early_exit", COLOR_RED, "Early-exit compare"),
    (width / 2, "constant_time", COLOR_BLUE, "Constant-time compare"),
]:
    xs = [p + offset for p in pos]
    ys = [ok for _, ok, _ in recovered[name]]
    plt.bar(xs, ys, width=width, color=color, label=label)
    for x, y in zip(xs, ys):
        plt.text(x, y + 0.4, str(y), ha="center", fontsize=11, color=color)
plt.axhline(total, color=COLOR_GRAY, linestyle="--", linewidth=1)
plt.xticks(list(pos), [str(n) for n in samples])
plt.xlabel("Samples per candidate byte")
plt.ylabel(f"Secrets fully recovered (out of {total})")
plt.ylim(0, total * 1.3)
plt.yticks(range(0, total + 1, 5))
plt.grid(axis="x", visible=False)
plt.legend(loc="upper left", fontsize=10, framealpha=1.0)
path = OUT / "side_channel_recovery.svg"
plt.savefig(path, metadata={"Date": None})  # 日付を入れず、再生成で差分を出さない
plt.close()
print(f"wrote {path}")

# ---------------------------------------------------------------------------
# 図 4: T-table を 64 バイトの行に分けた図（標準ライブラリで SVG を手書き）
# 256 項目 x 4 バイトの表は 16 行のキャッシュラインに分かれる。被害者が読んだ
# 1 行だけが速く読め（青）、行の番号から添字の上位 4 ビットだけが分かる。
# 下位 4 ビット（黄土）は行の中の位置なので、この観測では分からない。
# ---------------------------------------------------------------------------
from html import escape  # noqa: E402

INK, SUB, OCHRE = "#1f1f1f", "#666666", "#d4a24c"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
svg = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" '
    'viewBox="0 0 960 540" role="img">'
    f'<title>{escape("T-table のキャッシュラインと、行の番号から分かる添字のビット")}</title>',
    f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
    '<rect width="960" height="540" fill="#ffffff"/>',
]


def text(x, y, s, size=24, color=INK, anchor="middle"):
    svg.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
               f'style="fill:{color}">{escape(s)}</text>')


def rect(x, y, w, h, fill, stroke, sw=1.5, rx=0):
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
               f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


HIT = 5  # 被害者が読んだ行（例）
x0, y0, cw, pitch = 130, 76, 20, 26
text(x0 + 160, 50, "T-table（4 バイト × 256 項目）", 24)
for r in range(16):
    y = y0 + r * pitch
    hit = r == HIT
    for c in range(16):
        rect(x0 + c * cw, y, cw, 20, "#eaf1f5" if hit else "#f2f2f2",
             COLOR_BLUE if hit else "#bbbbbb", 2 if hit else 1)
    if r in (0, HIT, 15):
        text(x0 - 14, y + 19, f"行 {r}", 24, INK if hit else SUB, "end")
rect(x0 - 3, y0 + HIT * pitch - 3, 16 * cw + 6, 26, "none", COLOR_BLUE, 3, 4)
text(x0 + 160, 516, "1 行 = 64 バイト = 16 項目", 24, SUB)

ax = x0 + 16 * cw + 20
svg.append(f'<line x1="{ax}" y1="{y0 + HIT * pitch + 10}" x2="{ax + 70}" '
           f'y2="{y0 + HIT * pitch + 10}" stroke="{COLOR_BLUE}" stroke-width="4"/>')
text(ax + 84, y0 + HIT * pitch + 19, "速く読めた行 = 5", 24, INK, "start")

bx, by, bw = 560, 340, 44
text(bx + 4 * bw, by - 30, "添字 p XOR k（8 ビット）", 24)
for i, b in enumerate("0101????"):
    upper = i < 4
    rect(bx + i * bw, by, bw, 56, "#eaf1f5" if upper else "#f8eed8",
         COLOR_BLUE if upper else OCHRE, 2)
    text(bx + i * bw + bw / 2, by + 38, b, 28)
text(bx + 2 * bw, by + 96, "行の番号で分かる", 24)
text(bx + 6 * bw + 10, by + 96, "分からない", 24, SUB)
svg.append("</svg>")
path = OUT / "side_channel_cache_lines.svg"
path.write_text("\n".join(svg) + "\n", encoding="utf-8")
print(f"wrote {path}")
