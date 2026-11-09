"""Side-Channel Attack のノートの図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/security/side-channel-attack/figures.py

図 1 は lab/output.txt（lab/compare_timing.c の実測）を読む。
図 2 は lab/simulate_remote.py のシミュレーションをその場で実行する。
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
