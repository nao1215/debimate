"""Rate Limiting のノートの図を作る。

  python3 lab/simulate.py && python3 lab/split.py   # 数値を作る（race は lab/run.sh で Redis を起動して実行）
  python3 figures.py                               # images/ の WebP を作り直す

数値は lab/results.json・lab/split_results.json・lab/race_results.json から読む。
"""
import json
import math
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
LAB, OUT = HERE / "lab", HERE / "images"
sys.path.insert(0, str(LAB))
from limiters import TokenBucket  # noqa: E402

INK, SUB, LINE = "#1f1f1f", "#666666", "#999999"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN = "#8fae86"
RED = "#e15759"

plt.rcParams.update({
    "font.family": "Noto Sans CJK JP",
    "svg.fonttype": "path",
    "font.size": 11,
    "axes.edgecolor": LINE,
    "axes.labelcolor": INK,
    "xtick.color": SUB,
    "ytick.color": SUB,
    "text.color": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def save(fig, name):
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff", bbox_inches="tight", pad_inches=0.15)
        Image.open(png).convert("RGB").save(OUT / name, "WEBP", quality=90, method=6)
    plt.close(fig)


def per_bin(times, start, stop, width):
    n = int(round((stop - start) / width))
    counts = [0] * n
    for t in times:
        k = math.floor((t - start) / width + 1e-9)
        if 0 <= k < n:
            counts[k] += 1
    return [start + i * width for i in range(n)], counts


def fig_boundary(res):
    """表紙: ウィンドウの境目の前後 1 秒に 60 件ずつ送った時、1 秒ごとに通した件数。"""
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.4), sharey=True)
    for ax, key, title in [(axes[0], "fixed", "固定ウィンドウ"), (axes[1], "log", "スライディングログ")]:
        xs, ys = per_bin(res[key]["times"], 56, 64, 1.0)
        colors = []
        for x, y in zip(xs, ys):
            colors.append(RED if (key == "fixed" and x == 60) else BLUE)
        ax.bar([x + 0.5 for x in xs], ys, width=0.8, color=colors, edgecolor="none")
        ax.axvline(60, color=SUB, lw=1, ls=(0, (4, 3)))
        ax.text(59.9, 78, "ウィンドウの境目", color=SUB, fontsize=9, ha="right", va="top")
        ax.set_title(title, fontsize=13, loc="left", color=INK)
        ax.set_xlim(56, 64)
        ax.set_ylim(0, 80)
        ax.set_xticks(range(56, 65, 2))
        ax.set_xlabel("時刻（秒）")
        total = sum(ys)
        ax.text(63.8, 45, f"2 秒で {total} 件", ha="right", fontsize=12,
                color=RED if key == "fixed" else INK)
    axes[0].set_ylabel("1 秒に通した件数")
    fig.suptitle("上限は 60 秒あたり 60 件。59〜60 秒と 60〜61 秒に 60 件ずつ届いた時",
                 fontsize=10, color=SUB, x=0.02, ha="left", y=1.02)
    save(fig, "ratelimit_boundary.webp")


def fig_windows():
    """各方式が「今の数」として何を数えるかの概念図（時刻 75 秒で判定する時）。"""
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    rows = [("固定ウィンドウ", 2), ("スライディングログ", 1), ("スライディングウィンドウカウンター", 0)]
    now = 75
    for label, y in rows:
        ax.text(-3, y, label, ha="right", va="center", fontsize=13)
        ax.plot([0, 120], [y, y], color=LINE, lw=0.8, zorder=1)
    # 固定ウィンドウ: 60〜75 を数える
    ax.add_patch(plt.Rectangle((60, 2 - 0.28), now - 60, 0.56, fc=BLUE_PALE, ec=BLUE, zorder=2))
    ax.text(67.5, 2, "今の枠", ha="center", va="center", fontsize=12, zorder=3)
    # スライディングログ: 15〜75 を数える
    ax.add_patch(plt.Rectangle((now - 60, 1 - 0.28), 60, 0.56, fc=BLUE_PALE, ec=BLUE, zorder=2))
    ax.text(45, 1, "直近 60 秒の記録をすべて", ha="center", va="center", fontsize=12, zorder=3)
    # カウンター: 前の枠 × 45/60 + 今の枠
    ax.add_patch(plt.Rectangle((0, 0 - 0.28), 60, 0.56, fc="#ffffff", ec=OCHRE, zorder=2))
    ax.add_patch(plt.Rectangle((now - 60, 0 - 0.28), 60 - (now - 60), 0.56, fc=OCHRE_PALE, ec=OCHRE, zorder=2))
    ax.add_patch(plt.Rectangle((60, 0 - 0.28), now - 60, 0.56, fc=BLUE_PALE, ec=BLUE, zorder=2))
    ax.text(37.5, 0, "前の枠の数 × 45/60", ha="center", va="center", fontsize=12, zorder=3)
    ax.text(67.5, -0.5, "＋ 今の枠", ha="center", va="center", fontsize=12, color=SUB)
    ax.plot([now, now], [-0.8, 2.45], color=INK, lw=1.2, zorder=4)
    ax.text(now, 2.55, "今（75 秒）", ha="center", va="bottom", fontsize=12)
    for b in (0, 60, 120):
        ax.plot([b, b], [-0.8, 2.45], color=LINE, lw=0.8, ls=(0, (2, 3)), zorder=1)
    ax.set_xlim(-1, 121)
    ax.set_ylim(-0.8, 2.95)
    ax.set_yticks([])
    ax.set_xticks([0, 15, 60, 75, 120])
    ax.tick_params(axis="x", labelsize=12)
    ax.set_xlabel("時刻（秒）、点線は 60 秒ごとの枠の境目", fontsize=12)
    ax.spines["left"].set_visible(False)
    save(fig, "ratelimit_windows.webp")


def fig_counter_example():
    """Cloudflare のブログの例: 上限 50、前の 1 分に 42 件、今の 1 分の 15 秒目までに 18 件。"""
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(8.8, 2.9), gridspec_kw={"width_ratios": [2.3, 1]})
    # 左: 時間軸。前の枠は 42 件が均等に届いたとみなし、直近 60 秒に重なる 45/60 だけを数える
    ax.add_patch(plt.Rectangle((0, 0.2), 60, 0.6, fc="#ffffff", ec=OCHRE, lw=1.2))
    ax.add_patch(plt.Rectangle((15, 0.2), 45, 0.6, fc=OCHRE_PALE, ec=OCHRE, lw=1.2))
    ax.add_patch(plt.Rectangle((60, 0.2), 15, 0.6, fc=BLUE_PALE, ec=BLUE, lw=1.2))
    for k in range(42):
        x = (k + 0.5) * 60 / 42
        ax.plot([x, x], [0.3, 0.42], color=OCHRE, lw=0.9)
    ax.text(7.5, 0.62, "数えない", ha="center", va="center", fontsize=9.5, color=SUB)
    ax.text(37.5, 0.62, "42 × 45/60 = 31.5", ha="center", va="center", fontsize=10.5)
    ax.text(67.5, 0.62, "18", ha="center", va="center", fontsize=10.5)
    ax.annotate("", (75, 1.12), (15, 1.12), arrowprops=dict(arrowstyle="<->", color=SUB, lw=1))
    ax.text(45, 1.2, "直近 60 秒", ha="center", va="bottom", fontsize=10, color=SUB)
    ax.text(30, -0.12, "前の 1 分（42 件を均等とみなす）", ha="center", va="top", fontsize=9.5, color=SUB)
    ax.text(67.5, -0.12, "今の 1 分", ha="center", va="top", fontsize=9.5, color=SUB)
    ax.plot([75, 75], [0.05, 1.05], color=INK, lw=1.2)
    ax.set_xlim(-1, 90)
    ax.set_ylim(-0.45, 1.5)
    ax.set_yticks([])
    ax.set_xticks([0, 15, 60, 75])
    ax.set_xticklabels(["0", "15", "60", "75（今）"])
    ax.set_xlabel("時刻（秒）")
    ax.spines["left"].set_visible(False)
    # 右: 推定値と上限
    bx.barh([0], [31.5], color=OCHRE_PALE, edgecolor=OCHRE, height=0.5)
    bx.barh([0], [18], left=[31.5], color=BLUE_PALE, edgecolor=BLUE, height=0.5)
    bx.axvline(50, color=SUB, lw=1, ls=(0, (4, 3)))
    bx.text(48.5, 0.42, "上限 50", ha="right", va="bottom", fontsize=9.5, color=SUB)
    bx.text(15.75, 0, "31.5", ha="center", va="center", fontsize=10.5)
    bx.text(40.5, 0, "18", ha="center", va="center", fontsize=10.5)
    bx.text(24.75, -0.48, "推定 49.5 件。次の 1 件は断る", ha="center", va="top", fontsize=9.5)
    bx.set_xlim(0, 60)
    bx.set_ylim(-0.9, 0.9)
    bx.set_yticks([])
    bx.set_xlabel("件数")
    bx.spines["left"].set_visible(False)
    fig.tight_layout()
    save(fig, "ratelimit_counter.webp")


def fig_steady(res):
    """100 秒から 1 秒に 2 件を送り続けた時、5 秒ごとに通した件数。"""
    keys = [("fixed", "固定ウィンドウ"), ("log", "スライディングログ"),
            ("counter", "スライディングウィンドウカウンター"), ("bucket10", "トークンバケット（容量 10）")]
    fig, axes = plt.subplots(len(keys), 1, figsize=(8.4, 6.4), sharex=True, sharey=True)
    for ax, (key, title) in zip(axes, keys):
        xs, ys = per_bin(res[key]["times"], 90, 235, 5.0)
        ax.bar([x + 2.5 for x in xs], ys, width=4.2, color=BLUE, edgecolor="none")
        ax.axhline(5, color=SUB, lw=1, ls=(0, (4, 3)))
        for b in (120, 180):
            ax.axvline(b, color=LINE, lw=0.8, ls=(0, (2, 3)))
        ax.set_ylim(0, 12)
        ax.set_yticks([0, 5, 10])
        r = res[key]
        ax.text(0.0, 1.02, title, transform=ax.transAxes, fontsize=11, ha="left", va="bottom")
        ax.text(1.0, 1.02, f"計 {r['passed']} 件、どの 60 秒でも最大 {r['max_60s']} 件",
                transform=ax.transAxes, fontsize=10, ha="right", va="bottom",
                color=OCHRE if r["max_60s"] > 60 else SUB)
    axes[-1].set_xlabel("時刻（秒）、点線は 60 秒ごとの枠の境目、横の破線は 1 秒に 1 件の速さ")
    axes[-1].set_xlim(90, 235)
    fig.text(0.07, 0.5, "5 秒に通した件数", rotation=90, va="center", ha="right")
    fig.subplots_adjust(hspace=0.55)
    save(fig, "ratelimit_steady.webp")


def fig_tokens():
    """トークンバケット（1 秒に 1 個、容量 10）の残りのトークン。100 秒から 1 秒に 2 件。"""
    tb = TokenBucket(rate=1.0, capacity=10)
    xs, ys, passed = [], [], []
    t = 90.0
    arrivals = [100 + i / 2 for i in range(240)]
    i = 0
    while t <= 140:
        while i < len(arrivals) and arrivals[i] <= t + 1e-9:
            ok = tb.allow(arrivals[i])
            passed.append((arrivals[i], ok))
            i += 1
        # 時刻 t での残量（判定はせずに計算だけする）
        tokens = min(tb.capacity, tb.tokens + (t - tb.last) * tb.rate) if tb.last is not None else tb.capacity
        xs.append(t)
        ys.append(tokens)
        t += 0.05
    fig, ax = plt.subplots(figsize=(8.4, 2.9))
    ax.plot(xs, ys, color=BLUE, lw=1.6)
    ax.fill_between(xs, ys, color=BLUE_PALE)
    ax.axhline(10, color=SUB, lw=1, ls=(0, (4, 3)))
    ax.text(90.5, 10.3, "容量 10", color=SUB, fontsize=9.5)
    rej = [a for a, ok in passed if not ok]
    ax.plot(rej, [-0.6] * len(rej), "|", color=OCHRE, ms=8)
    ax.text(108.8, -0.6, "断った要求", color=OCHRE, fontsize=9.5, ha="right", va="center")
    ax.set_ylim(-1.2, 11.5)
    ax.set_xlim(90, 140)
    ax.set_ylabel("残りのトークン")
    ax.set_xlabel("時刻（秒）、100 秒から 1 秒に 2 件が届き、トークンは 1 秒に 1 個溜まる")
    save(fig, "ratelimit_tokens.webp")


def fig_split(rows):
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ps = [r["p"] for r in rows]
    ax.plot(ps, [r["central"] for r in rows], color=BLUE, lw=2, marker="o", ms=4, label="中央で 60 件を数える")
    ax.plot(ps, [r["split"] for r in rows], color=OCHRE, lw=2, marker="o", ms=4, label="2 台で 30 件ずつ分け合う")
    ax.set_ylim(0, 70)
    ax.set_xlim(0.48, 1.02)
    ax.text(0.5, 63, "60 秒に 60 件を送る（上限ちょうど）", color=SUB, fontsize=9.5)
    ax.set_xticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_xticklabels(["50%", "60%", "70%", "80%", "90%", "100%"])
    ax.set_xlabel("同じ利用者の要求のうち、サーバー 1 に届いた割合")
    ax.set_ylabel("60 秒に通した件数")
    ax.legend(frameon=False, loc="lower left", fontsize=10)
    save(fig, "ratelimit_split.webp")


def fig_race(race):
    modes = [("check_then_incr", "GET してから INCR"),
             ("check_then_incr_1ms", "GET と INCR の間に 1 ms"),
             ("incr", "INCR の戻り値で判定"),
             ("token_bucket", "Lua のトークンバケット")]
    fig, ax = plt.subplots(figsize=(8.0, 3.4))
    for i, (key, label) in enumerate(modes):
        vals = race["trials"][key]
        counts = {}
        for v in vals:
            counts[v] = counts.get(v, 0) + 1
        for v, c in counts.items():
            step = min(0.05, 0.6 / c)
            offs = [(k - (c - 1) / 2) * step for k in range(c)]
            color = OCHRE if v > race["limit"] else BLUE
            ax.scatter([i + o for o in offs], [v] * c, s=18, color=color, zorder=3)
    ax.axhline(race["limit"], color=SUB, lw=1, ls=(0, (4, 3)))
    ax.text(-0.45, race["limit"] + 0.25, "上限 100", color=SUB, fontsize=9.5, ha="left")
    ax.set_xticks(range(len(modes)))
    ax.set_xticklabels([m[1] for m in modes], fontsize=10)
    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(98.5, 108.5)
    ax.set_ylabel("通した件数（20 回分）")
    save(fig, "ratelimit_race.webp")


def main():
    OUT.mkdir(exist_ok=True)
    res = json.loads((LAB / "results.json").read_text())
    fig_boundary(res["boundary_burst"])
    fig_windows()
    fig_counter_example()
    fig_steady(res["idle_then_steady"])
    fig_tokens()
    fig_split(json.loads((LAB / "split_results.json").read_text()))
    fig_race(json.loads((LAB / "race_results.json").read_text()))


if __name__ == "__main__":
    main()
