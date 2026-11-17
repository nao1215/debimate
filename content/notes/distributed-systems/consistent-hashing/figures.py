"""Consistent Hashing のノートの図を作る（WebP）。

lab/results.json（lab/experiment.py の出力）を読んで描く。リングの図の点の位置は、
experiment.py と同じ MD5 の計算で求めた実際の位置。

    python3 lab/experiment.py > lab/output.txt   # lab の中で実行
    python3 figures.py
"""
import json
import math
from hashlib import md5
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Wedge  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "lab" / "results.json").read_text())
plt.rcParams["font.family"] = ["Noto Sans CJK JP", "DejaVu Sans"]
plt.rcParams["font.size"] = 12
INK, SUB, GRID = "#1f1f1f", "#666666", "#dddddd"
COLOR = {"cache-1": "#7aa6c2", "cache-2": "#d4a24c", "cache-3": "#b5b5b5", "cache-4": "#e15759"}
NODE_COLOR = {"node-1": "#7aa6c2", "node-2": "#d4a24c", "node-3": "#b5b5b5", "node-4": "#e15759"}
SPACE = 2**64


def h(text):
    return int.from_bytes(md5(text.encode()).digest()[:8], "big")


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def clean(ax):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(SUB)
    ax.spines["bottom"].set_color(SUB)
    ax.tick_params(colors=INK)


def stacked(ax, y, shares, height=0.36, labels=True):
    left = 0.0
    for s, v in shares.items():
        ax.barh(y, v, left=left, height=height, color=COLOR[s], edgecolor="#ffffff", linewidth=1.5)
        if labels and v >= 0.07:
            ax.text(left + v / 2, y, f"{s[-1]}: {v * 100:.0f}%", ha="center", va="center", fontsize=10.5, color=INK)
        left += v


def cover():
    rows = [("mod", "台数で割る"), ("ring1", "リング（1 台に 1 点）"), ("ring100", "リング（1 台に 100 点）")]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    yt, yl = [], []
    for i, (key, title) in enumerate(rows):
        base = (len(rows) - 1 - i) * 1.25
        d = R["add"][key]
        stacked(ax, base + 0.22, d["before"])
        stacked(ax, base - 0.22, d["after"])
        yt += [base + 0.22, base - 0.22]
        yl += ["3 台", "4 台"]
        ax.text(-0.13, base, title, ha="right", va="center", fontsize=12.5, color=INK)
        ax.text(1.02, base, f"動いたキー\n{d['moved'] * 100:.1f}%", ha="left", va="center", fontsize=12, color=INK)
    ax.set_yticks(yt, yl)
    ax.set_xlim(0, 1)
    ax.set_xticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("キー 100,000 個のうち、各サーバーが持つ割合（数字はサーバーの番号）")
    clean(ax)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    save(fig, "consistent-hashing_cover.webp")


def ring_points(servers, v=1):
    return sorted((h(f"{s}#{i}"), s) for s in servers for i in range(v))


def draw_ring(ax, servers, title, counted, highlight=None):
    pts = ring_points(servers)
    for i, (p, s) in enumerate(pts):
        prev = pts[i - 1][0] - (SPACE if i == 0 else 0)
        # 角度は 12 時から時計回り。matplotlib の Wedge は 3 時から反時計回りなので変換する。
        a1 = 90 - p / SPACE * 360
        a0 = 90 - prev / SPACE * 360
        ax.add_patch(Wedge((0, 0), 1.0, a1, a0, width=0.22, color=COLOR[s], ec="#ffffff", lw=2))
        share = counted[s]  # 弧の長さではなく、実際に数えたキーの割合を書く
        mid = math.radians((a0 + a1) / 2)
        ax.text(0.6 * math.cos(mid), 0.6 * math.sin(mid), f"{share * 100:.0f}%", ha="center", va="center", fontsize=12)
    for p, s in pts:
        a = math.radians(90 - p / SPACE * 360)
        x, y = math.cos(a), math.sin(a)
        ax.plot([0.78 * x, 1.04 * x], [0.78 * y, 1.04 * y], color=INK, lw=2)
        ax.plot(1.04 * x, 1.04 * y, "o", color=COLOR[s], mec=INK, ms=11)
        ax.text(1.12 * x + (0.08 if x > 0 else -0.08), 1.12 * y, s, ha="left" if x > 0 else "right", va="center", fontsize=12,
                color="#b03030" if s == highlight else INK)
    ax.annotate("", xy=(0.38, 1.12), xytext=(-0.38, 1.12),
                arrowprops=dict(arrowstyle="->", color=SUB, lw=1.5, connectionstyle="arc3,rad=-0.25"))
    ax.text(0, 1.5, title, ha="center", va="center", fontsize=13)
    ax.set_xlim(-1.75, 1.75)
    ax.set_ylim(-1.45, 1.65)
    ax.set_aspect("equal")
    ax.axis("off")


def ring():
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    draw_ring(axes[0], ["cache-1", "cache-2", "cache-3"], "3 台", R["add"]["ring1"]["before"])
    draw_ring(axes[1], ["cache-1", "cache-2", "cache-3", "cache-4"], "cache-4 を足した後", R["add"]["ring1"]["after"], highlight="cache-4")
    fig.text(0.5, 0.04, "弧の色は、その範囲に落ちたキーを担当するサーバー。キーは時計回りで最初に出会う点のサーバーへ行く",
             ha="center", fontsize=11, color=SUB)
    save(fig, "consistent-hashing_ring.webp")


def trials():
    m = [x * 100 for x in R["trials"]["moves"]]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.hist(m, bins=[i * 2.5 for i in range(37)], color="#b5b5b5", edgecolor="#ffffff")
    ax.axvline(25, color=INK, ls="--", lw=1.5)
    ax.text(25.8, ax.get_ylim()[1] * 0.92, "1/4（25%）", fontsize=11, va="top")
    ax.axvline(R["add"]["ring1"]["moved"] * 100, color="#e15759", lw=2)
    ax.text(R["add"]["ring1"]["moved"] * 100 + 0.8, ax.get_ylim()[1] * 0.70,
            f"冒頭の図の 1 回\n（{R['add']['ring1']['moved'] * 100:.1f}%）", fontsize=11, va="top", color="#b03030")
    ax.set_xlabel("4 台目を足した時に動いたキーの割合（%）")
    ax.set_ylabel("回数（全 1,000 回）")
    ax.set_xlim(0, 90)
    clean(ax)
    save(fig, "consistent-hashing_trials.webp")


def vnodes():
    vs = [int(v) for v in R["vnodes"]]
    med, p95 = [], []
    for v in R["vnodes"].values():
        xs = sorted(v)
        med.append(xs[int(0.5 * (len(xs) - 1))])
        p95.append(xs[int(0.95 * (len(xs) - 1))])
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(vs, p95, "o--", color="#e15759", label="200 回のうち 95% 点")
    ax.plot(vs, med, "o-", color=INK, label="200 回の中央値")
    for v, a, b in zip(vs, med, p95):
        ax.text(v, b + 0.12, f"{b:.2f}", ha="center", fontsize=10, color="#b03030")
        # 中央値の値は点の真下、1.0 の横線より下に白地で置き、線と重ねない
        ax.text(v, min(a - 0.12, 0.93), f"{a:.2f}", ha="center", va="top", fontsize=10,
                bbox=dict(facecolor="#ffffff", edgecolor="none", pad=1))
    ax.axhline(1, color=SUB, lw=1, zorder=0)
    ax.set_xscale("log", base=2)
    ax.set_xticks(vs, [str(v) for v in vs])
    ax.set_xlabel("1 台あたりの点の数（仮想ノードの数）")
    ax.set_ylabel("一番多く受け持つサーバーの割合 ÷ 平均")
    ax.set_ylim(0.55, 4.6)
    ax.legend(frameon=False)
    clean(ax)
    save(fig, "consistent-hashing_vnodes.webp")


def fail():
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    for ax, key, title in [(axes[0], "ring1", "1 台に 1 点"), (axes[1], "ring100", "1 台に 100 点")]:
        d = R["fail"][key]
        servers = list(d["after"])
        for i, s in enumerate(servers):
            own = d["before"][s]
            got = d["to"][s]
            ax.bar(i, own, color=COLOR[s], width=0.6)
            ax.bar(i, got, bottom=own, color=COLOR["cache-2"], width=0.6, hatch="//", edgecolor="#ffffff")
            ax.text(i, own + got + 0.015, f"{(own + got) * 100:.1f}%", ha="center", fontsize=11,
                    bbox=dict(boxstyle="square,pad=0.15", fc="#ffffff", ec="none"))
        ax.axhline(1 / 3, color=SUB, ls="--", lw=1, zorder=0)
        ax.set_xticks(range(len(servers)), servers)
        ax.set_title(title, fontsize=13)
        ax.set_ylim(0, 0.65)
        ax.set_yticks([0, .2, .4, .6], ["0%", "20%", "40%", "60%"])
        clean(ax)
    axes[0].set_ylabel("cache-2 を外した後に受け持つ割合")
    # 縦軸の線に掛からないよう、右のパネルの外側に置く
    axes[1].text(2.42, 1 / 3, "平均（1/3）", ha="left", va="center", fontsize=10, color=SUB, clip_on=False)
    fig.text(0.5, -0.02, "斜線は、外した cache-2 から引き継いだキー", ha="center", fontsize=11, color=SUB)
    save(fig, "consistent-hashing_fail.webp")


def replica():
    names = ["node-1", "node-2", "node-3", "node-4"]
    pts = ring_points(names, 100)
    # キーを 1 つ選び、その位置の周りの点を並べる
    key = h("user:2")
    from bisect import bisect_left
    i0 = bisect_left([p for p, _ in pts], key)
    window = [pts[(i0 + k) % len(pts)] for k in range(-3, 7)]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axes[0]
    ax.plot([-0.5, len(window) - 0.5], [0, 0], color=SUB, lw=2)
    for k, (p, s) in enumerate(window):
        picked = 3 <= k < 6
        ax.plot(k, 0, "o", ms=20, color=NODE_COLOR[s], mec=INK, mew=2.5 if picked else 0.8)
        ax.text(k, -0.32, s[-1], ha="center", va="center", fontsize=12)
    ax.annotate("user:2", xy=(2.5, 0.05), xytext=(2.5, 0.55), ha="center", fontsize=12,
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.5))
    ax.annotate("", xy=(5.4, 0.24), xytext=(3.0, 0.24), arrowprops=dict(arrowstyle="->", color=SUB, lw=1.2))
    ax.text(4.3, 0.36, "時計回りに次の 3 点", ha="center", fontsize=11, color=SUB)
    sv = [window[k][1][-1] for k in range(3, 6)]
    distinct = []
    for k in range(3, len(window)):
        if window[k][1] not in distinct:
            distinct.append(window[k][1])
        if len(distinct) == 3:
            break
    ax.text(4, -0.62, f"次の 3 点を取る: {', '.join(sv)}", ha="center", fontsize=11.5)
    ax.text(4, -0.85, f"同じサーバーを飛ばす: {', '.join(x[-1] for x in distinct)}", ha="center", fontsize=11.5)
    ax.text(-0.5, -0.32, "サーバー", ha="right", va="center", fontsize=10.5, color=SUB)
    ax.set_xlim(-1.6, len(window) - 0.3)
    ax.set_ylim(-1.0, 0.85)
    ax.axis("off")
    ax.set_title("4 台・1 台に 100 点のリングの一部", fontsize=12.5)
    ax = axes[1]
    ns = list(R["replica"])
    vals = [R["replica"][n] * 100 for n in ns]
    ax.bar(range(len(ns)), vals, color="#b5b5b5", width=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 2, f"{v:.1f}%", ha="center", fontsize=11)
    ax.set_xticks(range(len(ns)), [f"{n} 台" for n in ns])
    ax.set_ylim(0, 90)
    ax.set_title("同じサーバーに 2 つ以上載るキー", fontsize=12.5)
    ax.set_ylabel("キーの割合（%）", labelpad=8)
    clean(ax)
    save(fig, "consistent-hashing_replica.webp")
    return sv


def hot():
    d = R["hot"]
    servers = list(d["keys"])
    fig, ax = plt.subplots(figsize=(9, 4))
    x = range(len(servers))
    ax.bar([i - 0.18 for i in x], [d["keys"][s] * 100 for s in servers], width=0.34, color="#d9d9d9", label="キーの数")
    ax.bar([i + 0.18 for i in x], [d["requests"][s] * 100 for s in servers], width=0.34,
           color="#666666", label="要求の数")
    for i, s in enumerate(servers):
        # 25% の破線と重ならないよう、値は棒の内側の根元に書く
        ax.text(i - 0.18, 1.5, f"{d['keys'][s] * 100:.1f}", ha="center", va="bottom", fontsize=10, color=INK)
        ax.text(i + 0.18, 1.5, f"{d['requests'][s] * 100:.1f}", ha="center", va="bottom", fontsize=10,
                color="#ffffff")
    t = servers.index(d["top_owner"])
    ax.annotate(f"1 番人気のキーだけで {d['top_share'] * 100:.1f}%", xy=(t + 0.1, d["requests"][d["top_owner"]] * 100 + 2.2),
                xytext=(t - 1.1, 38), fontsize=11, arrowprops=dict(arrowstyle="->", color=INK))
    ax.axhline(25, color=SUB, ls="--", lw=1, zorder=0)  # 棒の後ろに描き、棒の中の値と重ねない
    ax.set_xticks(list(x), servers)
    ax.set_ylabel("4 台の中での割合（%）")
    ax.set_ylim(0, 42)
    ax.legend(frameon=False, loc="upper left")
    clean(ax)
    save(fig, "consistent-hashing_hot.webp")


if __name__ == "__main__":
    (HERE / "images").mkdir(exist_ok=True)
    cover()
    ring()
    trials()
    vnodes()
    fail()
    print("replica window:", replica())
    hot()
