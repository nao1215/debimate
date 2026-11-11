"""サンプリングのノートの図を生成する。値は lab/ の出力から読む。

    python3 figures.py
"""
import colorsys
import io
import math
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "lab"))
from sampling import LOGITS, TOKENS, probs, top_p_filter  # noqa: E402

plt.rcParams["font.family"] = ["Noto Sans CJK JP", "sans-serif"]
INK, SUB, ACCENT, OCHRE, RED = "#222222", "#666666", "#4a7fa8", "#d4a24c", "#c8463c"


def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def _save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    Image.open(buf).convert("RGB").save(HERE / "images" / f"{name}.webp", "WEBP", quality=90, method=6)


def repeat_figure():
    """同じ問いを 30 回投げた結果。同じ出力は同じ色の点になる。"""
    text = (HERE / "lab" / "output_repeat.txt").read_text()
    blocks = re.findall(r"== (.+?): (\d+) 回 → (\d+) 種類\n((?:\s+\d+ 回 \[\w+\].*\n)+)", text)
    labels = ["指定なし（モデルの既定）", "temperature 0", "temperature 0、8 並列", "temperature 0.6、seed 42"]
    hashes = sorted({h for b in blocks for h in re.findall(r"\[(\w+)\]", b[3])})
    colors = {h: colorsys.hsv_to_rgb((i * 0.618) % 1, 0.55, 0.85) for i, h in enumerate(hashes)}
    colors.update({"bbdc1719": ACCENT, "8308da87": OCHRE})
    fig, ax = plt.subplots(figsize=(10, 3.4))
    for row, (b, label) in enumerate(zip(blocks, labels)):
        seq = []
        for k, h in re.findall(r"(\d+) 回 \[(\w+)\]", b[3]):
            seq += [h] * int(k)
        y = len(blocks) - 1 - row
        ax.scatter(range(len(seq)), [y] * len(seq), s=150, c=[colors[h] for h in seq], edgecolors="#333", linewidths=0.6)
        ax.text(len(seq) + 0.6, y, f"{b[2]} 種類", va="center", fontsize=12, color=INK)
    ax.set_yticks(range(len(blocks)), labels[::-1], fontsize=11)
    ax.set_xticks([0, 9, 19, 29], ["1", "10", "20", "30"], fontsize=10)
    ax.set_xlabel("何回目の問い合わせか（同じ色は同じ出力）", fontsize=11)
    ax.set_xlim(-1, 33)
    ax.set_ylim(-0.6, len(blocks) - 0.4)
    _style(ax)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    _save(fig, "sampling_repeat")


def nexttoken_figure():
    """qwen3:8b が「今日の天気は」の次に出した上位 10 個を、Ollama と同じ順（top-k → temperature → softmax → top-p）で処理する。"""
    text = (HERE / "lab" / "output_nexttoken.txt").read_text().split("== temperature 1.0")[1].split("==")[0]
    rows = re.findall(r"  '(.*?)'\s+([\d.]+)", text)
    names = {"��": "（文字の途中）", "？\\n": "？＋改行"}
    toks = [names.get(t, t) for t, _ in rows]
    logit = np.log(np.array([float(v) for _, v in rows]))
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw={"width_ratios": [3, 2]})
    x = np.arange(len(toks))
    styles = [(0.5, INK), (1.0, ACCENT), (1.5, "#bbbbbb")]
    for i, (t, c) in enumerate(styles):
        q = np.exp(logit / t)
        q = q / q.sum()
        a.bar(x + (i - 1) * 0.27, q, 0.27, color=c, label=f"temperature {t}")
        cum = np.cumsum(q)
        kept = int(np.sum(cum - q < 0.95))
        b.plot(np.arange(1, len(toks) + 1), cum, color=c, marker="o", lw=1.5, label=f"temperature {t}：{kept} 個が残る")
    a.set_xticks(x, toks, fontsize=10, rotation=30, ha="right")
    a.set_ylabel("選ばれる確率", fontsize=11)
    a.set_title("上位 10 個の中で計算し直した確率", fontsize=12, loc="left")
    a.legend(frameon=False, fontsize=10)
    b.axhline(0.95, color=RED, ls=":", lw=1.2)
    b.text(1.0, 0.965, "top_p 0.95", ha="left", fontsize=10, color=RED)
    b.set_xticks(range(1, len(toks) + 1))
    b.set_xlabel("上位から何個目まで", fontsize=11)
    b.set_ylim(0.2, 1.05)
    b.set_title("上位からの累積と top-p で残る数", fontsize=12, loc="left")
    b.legend(frameon=False, fontsize=10, loc="lower right")
    for ax in (a, b):
        _style(ax)
    fig.tight_layout()
    _save(fig, "sampling_nexttoken")


def cache_figure():
    """temperature 0 で 6 回送った時の出力と、問いの処理に掛かった時間。"""
    rows = re.findall(r"(\S.*?)\s+出力 (\w+)\s+問いのトークン数 \d+\s+問いの処理\s+([\d.]+) ms",
                      (HERE / "lab" / "output_cache.txt").read_text())
    labels = ["A 1 回目\n読み込み直後", "A 2 回目", "A 3 回目", "B\n別の問い", "A 4 回目\nB の後", "A 5 回目"]
    col = {"832a7755": OCHRE, "bbdc1719": ACCENT}
    fig, ax = plt.subplots(figsize=(10, 3.4))
    x = np.arange(len(rows))
    ms = [float(r[2]) for r in rows]
    ax.bar(x, ms, 0.6, color=[col.get(r[1], "#cccccc") for r in rows])
    for k, (r, m) in enumerate(zip(rows, ms)):
        name = {"832a7755": "出力 1\n832a7755", "bbdc1719": "出力 2\nbbdc1719"}.get(r[1], "B の出力\n" + r[1])
        ax.text(k, m + 6, f"{name}\n{m:.0f} ms", ha="center", fontsize=10, color=INK, linespacing=1.3)
    ax.set_xticks(x, labels, fontsize=10)
    ax.set_ylabel("問いの処理（ms）", fontsize=11)
    ax.set_ylim(0, max(ms) * 1.5)
    ax.set_title("temperature 0 で順に送った時の出力（同じ色は同じ出力）", fontsize=12, loc="left")
    _style(ax)
    _save(fig, "sampling_cache")


def counts_figure():
    """説明用のロジットで 1 万回選んだ結果（lab/sampling.py と同じ乱数）。"""
    rng = np.random.default_rng(1)
    conds = [("T=0.5", 0.5, 1.0), ("T=1.0", 1.0, 1.0), ("T=1.5", 1.5, 1.0), ("T=1.0, top_p=0.9", 1.0, 0.9)]
    shades = ["#2f5f86", "#4a7fa8", "#7ea6c6", "#b5cde0", "#d9d9d9", "#bdbdbd", RED]
    fig, ax = plt.subplots(figsize=(10, 3.2))
    for row, (label, t, tp) in enumerate(conds):
        pp = top_p_filter(probs(LOGITS, t), tp)
        c = np.bincount(rng.choice(len(TOKENS), size=10_000, p=pp), minlength=len(TOKENS))
        left = 0
        y = len(conds) - 1 - row
        for k, (tok, n) in enumerate(zip(TOKENS, c)):
            ax.barh(y, n, left=left, color=shades[k], edgecolor="#ffffff", label=tok if row == 0 else None)
            if n >= 600:
                ax.text(left + n / 2, y, f"{n:,}", ha="center", va="center", fontsize=9,
                        color="#ffffff" if k < 2 else INK)
            left += n
        ax.text(10_150, y, f"カレー {c[-1]} 回", va="center", fontsize=10, color=RED if c[-1] else SUB)
    ax.set_yticks(range(len(conds)), [c[0] for c in conds][::-1], fontsize=11)
    ax.set_xlim(0, 11_700)
    ax.set_xticks([0, 5_000, 10_000], ["0", "5,000", "10,000"])
    ax.set_xlabel("1 万回のうち選ばれた回数", fontsize=11)
    ax.legend(frameon=False, fontsize=9, ncol=7, loc="upper center", bbox_to_anchor=(0.45, 1.22))
    _style(ax)
    _save(fig, "sampling_counts")


def order_figure():
    """Ollama v0.22.1 の sample/samplers.go が候補を絞って 1 つ選ぶ順。"""
    from matplotlib.patches import FancyBboxPatch
    steps = [("ロジット", "全語彙の\n十数万個"), ("top-k", "上位 k 個を\n残す"), ("temperature", "ロジットを\nT で割る"),
             ("softmax", "k 個の中で\n合計 1 にする"), ("top-p", "累積 p まで\n残す"), ("min-p", "1 位の割合で\n切る"),
             ("1 つ選ぶ", "乱数で選ぶ\nseed で再現")]
    fig, ax = plt.subplots(figsize=(13, 2.9))
    w, gap = 1.55, 0.35
    for k, (title, sub) in enumerate(steps):
        x = k * (w + gap)
        ax.add_patch(FancyBboxPatch((x, 0.35), w, 1.1, boxstyle="round,pad=0.02,rounding_size=0.08",
                                    fc="#eef3f8" if 0 < k < 6 else "#f4f4f4", ec="#4a7fa8" if 0 < k < 6 else SUB, lw=1.4))
        ax.text(x + w / 2, 1.13, title, ha="center", va="center", fontsize=12, color=INK)
        ax.text(x + w / 2, 0.7, sub, ha="center", va="center", fontsize=10, color=SUB, linespacing=1.4)
        if k < len(steps) - 1:
            ax.annotate("", xy=(x + w + gap - 0.03, 0.9), xytext=(x + w + 0.03, 0.9),
                        arrowprops=dict(arrowstyle="->", color=INK, lw=1.3))
    ax.annotate("", xy=(6 * (w + gap) + w / 2, 1.5), xytext=(w / 2, 1.5),
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.3, ls="--", connectionstyle="arc3,rad=-0.12"))
    ax.text(3 * (w + gap) + w / 2, 2.05, "temperature が 0 なら、ここを飛ばして最大の 1 つを選ぶ（greedy decoding）",
            ha="center", fontsize=11, color=RED)
    ax.set_xlim(-0.1, 7 * (w + gap))
    ax.set_ylim(0.2, 2.3)
    ax.axis("off")
    _save(fig, "sampling_order")


if __name__ == "__main__":
    repeat_figure()
    nexttoken_figure()
    cache_figure()
    order_figure()
    counts_figure()
