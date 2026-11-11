"""Retry と Backoff のノートの図を生成する。

実行: python3 figures.py
lab/herd.json（python3 lab/herd.py lab/herd.json の出力）と lab/budget.json
（python3 lab/budget.py lab/budget.json の出力）を読み、images/ に WebP を書く。
待ち時間の図だけは、lab/herd.py の式から直接サンプルを引く。
"""
import io
import json
import random
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "lab"))
import budget  # noqa: E402
import herd  # noqa: E402

INK, SUB = "#1f1f1f", "#666666"
BLUE, OCHRE, OCHRE_PALE, GREEN, RED = "#7aa6c2", "#d4a24c", "#f8eed8", "#8fae86", "#e15759"
plt.rcParams.update({
    "font.family": "Noto Sans CJK JP", "font.size": 10,
    "axes.edgecolor": SUB, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "svg.fonttype": "path",
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})


def save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(ROOT / "images" / f"{name}.webp",
                                         "WEBP", quality=90, method=6)


def bins(xs, width=10):
    return [sum(xs[i:i + width]) for i in range(0, len(xs), width)]


def shade_down(ax, crashes, first=1.0, restart=1.0, until=25):
    spans = [(0, first)] + [(c, c + restart) for c in crashes if c < until]
    for a, b in spans:
        ax.axvspan(a, b, color=OCHRE_PALE, lw=0)
    for c in crashes:
        if c < until:
            ax.plot(c, 1060, marker="x", color=RED, ms=6, mew=1.6, clip_on=False)


def herd_figure(data):
    rows = [("exponential", "指数バックオフ（ジッターなし）", SUB),
            ("full jitter", "指数バックオフ + full jitter", BLUE)]
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.6), sharex=True)
    for ax, (key, title, color) in zip(axes, rows):
        d = data[key]
        y = bins(d["timeline_seed0"])
        x = [i * 0.1 for i in range(len(y))]
        shade_down(ax, d["crash_times_seed0"])
        ax.bar(x, y, width=0.1, align="edge", color=color, lw=0)
        ax.axhline(50, color=GREEN, lw=1.2)
        ax.axhline(100, color=SUB, lw=1.0, ls="--")
        ax.set_xlim(0, 25)
        ax.set_ylim(0, 1100)
        ax.set_title(title, loc="left", fontsize=11)
        ax.set_ylabel("100 ms あたりの到着数")
        fin = d["finish"][0]
        note = "120 s までに終わらない" if fin >= 120 else f"{fin:.1f} s で全員が成功\n（5 s 以降は数件ずつの裾）"
        ax.text(21.8, 820, note, ha="right", color=SUB, fontsize=10)
    axes[0].text(13.2, 560, "× サーバーが過負荷で落ちた時刻", color=SUB, fontsize=9)
    axes[1].text(5.2, 160, "緑の線: 容量（50 件）  破線: 落ちる閾値（100 件）",
                 color=SUB, fontsize=9)
    axes[1].set_xlabel("経過時間（s）。黄土の帯はサーバーが止まっている間")
    fig.tight_layout()
    save(fig, "retry-backoff_herd")


def waits_figure():
    rng = random.Random(1)
    n = list(range(1, 9))
    expo = [herd.expo(i) for i in n]
    panels = [("full jitter", herd.FullJitter), ("equal jitter", herd.EqualJitter),
              ("decorrelated jitter", herd.Decorrelated)]
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.4), sharey=True)
    for ax, (title, cls) in zip(axes, panels):
        for _ in range(40):
            p = cls()
            ys = [p.wait(i, rng) for i in n]
            ax.scatter([i + rng.uniform(-0.18, 0.18) for i in n], ys, s=6,
                       color=BLUE, alpha=1.0, lw=0)
        ax.plot(n, expo, color=SUB, lw=1.4, ls="--")
        ax.set_title(title, loc="left", fontsize=11)
        ax.set_xlabel("何回目の失敗の後か")
        ax.set_xticks(n)
    axes[0].set_ylabel("次の送信までの待ち時間（s）")
    axes[0].text(8.3, 10.6, "破線: ジッターなしの指数バックオフ", ha="right",
                 color=SUB, fontsize=9)
    axes[0].set_ylim(0, 11.5)
    fig.tight_layout()
    save(fig, "retry-backoff_waits")


def summary_figure(data):
    names = list(data)
    labels = {"immediate": "即時", "fixed 1s": "固定 1 s", "exponential": "指数",
              "full jitter": "full jitter", "equal jitter": "equal jitter",
              "decorrelated": "decorrelated jitter"}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.0, 3.4), sharey=True)
    ys = list(range(len(names)))[::-1]
    for y, k in zip(ys, names):
        d = data[k]
        jit = k in ("full jitter", "equal jitter", "decorrelated")
        color = BLUE if jit else SUB
        f = d["finish"]
        m = sum(f) / len(f)
        ax1.barh(y, m, color=color, height=0.6)
        if d["unfinished"]:
            ax1.text(m - 2, y, "120 s で打ち切り", va="center", ha="right",
                     color="#ffffff", fontsize=9)
        else:
            ax1.plot([min(f), max(f)], [y, y], color=INK, lw=1.2)
            ax1.text(max(f) + 2, y, f"{m:.1f} s", va="center", fontsize=9)
        s = d["sent"]
        ms = sum(s) / len(s)
        ax2.barh(y, ms, color=color, height=0.6)
        ax2.text(ms * 1.3, y, f"{ms:,.0f}", va="center", fontsize=9)
    ax1.set_yticks(ys, [labels[k] for k in names])
    ax1.set_xlim(0, 135)
    ax1.set_ylim(-1.1, len(names) - 0.4)
    ax1.set_title("全員が成功するまでの時間（20 回の平均と幅）", loc="left", fontsize=10.5)
    ax1.set_xlabel("s")
    ax2.set_xscale("log")
    ax2.set_xlim(500, 2e8)
    ax2.axvline(1000, color=GREEN, lw=1.2)
    ax2.text(1100, ys[-1] - 0.75, "1,000（クライアントの数）", color=SUB, fontsize=9)
    ax2.set_title("サーバーに届いた要求の総数（平均、対数軸）", loc="left", fontsize=10.5)
    fig.tight_layout()
    save(fig, "retry-backoff_summary")


def budget_figure(data):
    rows = [("4 attempts", "最大 4 回の試行（maxAttempts 4）、予算なし", SUB),
            ("4 attempts + gRPC throttling", "最大 4 回の試行 + gRPC の retryThrottling", BLUE)]
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.4), sharex=True)
    for ax, (key, title, color) in zip(axes, rows):
        d = data[key]
        a = d["arrivals_seed0"]
        x = list(range(len(a)))
        ax.axvspan(5, 15, color=OCHRE_PALE, lw=0)
        ax.bar(x, a, width=1.0, align="edge", color=color, lw=0)
        ax.step(x, d["new_seed0"], where="post", color=OCHRE if key == "4 attempts" else INK, lw=1.6)
        ax.axhline(500, color=GREEN, lw=1.2)
        ax.axhline(1000, color=SUB, lw=1.0, ls="--")
        ax.set_ylim(0, 1500)
        ax.set_xlim(0, 40)
        ax.set_title(title, loc="left", fontsize=11)
        ax.set_ylabel("1 秒あたりの到着数")
    axes[0].text(27.5, 700, "停止が終わった後も\n過負荷で落ち続ける", ha="center",
                 color="#ffffff", fontsize=10)
    axes[0].text(39.5, 1380, "黄土の線: 新しい要求  緑: 容量  破線: 落ちる閾値",
                 ha="right", color=SUB, fontsize=9)
    axes[1].text(39.5, 1150, "黒の線: 新しい要求  緑: 容量  破線: 落ちる閾値",
                 ha="right", color=SUB, fontsize=9)
    axes[1].set_xlabel("経過時間（s）。黄土の帯は下流が止まっていた 5〜15 s")
    fig.tight_layout()
    save(fig, "retry-backoff_budget")


def spread_figure():
    """最初の送信を 0〜0.9 s に散らした時の到着数（seed 0）。間隔が同じなら幅は広がらない。"""
    rows = [("fixed 1s", "固定 1 s", SUB), ("exponential", "指数バックオフ（ジッターなし）", SUB)]
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.4), sharex=True)
    for ax, (key, title, color) in zip(axes, rows):
        r = herd.run(key, 0, spread=0.9)
        y = bins(r["arrivals"][:2500])
        x = [i * 0.1 for i in range(len(y))]
        shade_down(ax, r["crashes"])
        ax.bar(x, y, width=0.1, align="edge", color=color, lw=0)
        ax.axhline(50, color=GREEN, lw=1.2)
        ax.axhline(100, color=SUB, lw=1.0, ls="--")
        ax.set_xlim(0, 25)
        ax.set_ylim(0, 1100)
        ax.set_title(title, loc="left", fontsize=11)
        ax.set_ylabel("100 ms あたりの到着数")
        fin = r["finish"]
        note = "120 s までに終わらない" if fin is None else f"{fin:.1f} s で全員が成功"
        ax.text(24.5, 900, note, ha="right", color=SUB, fontsize=10)
    axes[0].text(24.5, 560, "最初の送信の幅（約 0.9 s）が\n毎回そのまま戻ってくる",
                 ha="right", color=SUB, fontsize=9)
    axes[1].text(24.5, 560, "緑の線: 容量（50 件）  破線: 落ちる閾値（100 件）\n× サーバーが過負荷で落ちた時刻",
                 ha="right", color=SUB, fontsize=9)
    axes[1].set_xlabel("経過時間（s）。黄土の帯はサーバーが止まっている間")
    fig.tight_layout()
    save(fig, "retry-backoff_spread")


def tokens_figure():
    """gRPC の retryThrottling で、1 つのクライアントのトークンがどう動くか（seed 0、クライアント 0）。"""
    log = []

    class Logged(budget.GrpcThrottle):
        def __init__(self):
            super().__init__()
            self.idx = Logged.count
            Logged.count += 1

        def record(self, t, ok, retry):
            super().record(t, ok, retry)
            if self.idx == 0:
                log.append((t, self.tokens))

    Logged.count = 0
    budget.POLICIES["logged"] = Logged
    budget.run("logged", 0)
    del budget.POLICIES["logged"]
    ts = [0.0] + [t for t, _ in log] + [budget.HORIZON]
    vs = [10.0] + [v for _, v in log] + [log[-1][1]]
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    ax.axvspan(5, 15, color=OCHRE_PALE, lw=0)
    ax.axhspan(0, 5, color="#f2f2f2", lw=0)
    ax.step(ts, vs, where="post", color=BLUE, lw=1.8)
    ax.axhline(5, color=SUB, lw=1.0, ls="--")
    ax.text(5.4, 4.4, "5 以下（maxTokens / 2）の間は再試行しない", color=SUB, fontsize=9, va="top")
    ax.text(15.4, 9.2, "成功のたびに 0.1 ずつ戻る", color=SUB, fontsize=9)
    ax.text(5.4, 2.0, "失敗のたびに 1 減る（4〜5 s の下り）", color=SUB, fontsize=9)
    ax.set_xlim(0, 25)
    ax.set_ylim(0, 11)
    ax.set_ylabel("トークンの残り")
    ax.set_xlabel("経過時間（s）。黄土の帯は下流が止まっていた 5〜15 s")
    fig.tight_layout()
    save(fig, "retry-backoff_tokens")


if __name__ == "__main__":
    herd_data = json.loads((ROOT / "lab" / "herd.json").read_text())
    herd_figure(herd_data)
    waits_figure()
    summary_figure(herd_data)
    spread_figure()
    tokens_figure()
    budget_figure(json.loads((ROOT / "lab" / "budget.json").read_text()))
