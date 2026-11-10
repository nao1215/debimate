"""サンプリングのノートの図を生成する。値は lab/sampling.py と同じ説明用のロジット。

    python3 figures.py
"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, "lab")
from sampling import LOGITS, TOKENS, probs  # noqa: E402

plt.rcParams["font.family"] = ["Noto Sans CJK JP", "sans-serif"]
plt.rcParams["svg.fonttype"] = "none"

fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [3, 2]})

x = np.arange(len(TOKENS))
for i, (t, c) in enumerate([(0.5, "#222"), (1.0, "#777"), (1.5, "#bbb")]):
    a.bar(x + (i - 1) * 0.27, probs(LOGITS, t), 0.27, color=c, label=f"temperature {t}")
a.set_xticks(x, TOKENS, fontsize=10)
a.set_ylabel("選ばれる確率", fontsize=11)
a.set_title("temperature：確率の山を尖らせる・均す", fontsize=12, loc="left")
a.legend(frameon=False, fontsize=10)

p = probs(LOGITS, 1.0)
cum = np.cumsum(p) - p
keep = cum < 0.9
b.bar(x, p, 0.6, color=["#444" if k else "#ddd" for k in keep])
b.plot(x, np.cumsum(p), color="#222", marker="o", lw=1.5, label="上位からの累積")
b.axhline(0.9, color="#555", ls=":", lw=1)
b.text(len(TOKENS) - 0.6, 0.92, "top_p = 0.9", ha="right", fontsize=10, color="#333")
b.set_xticks(x, TOKENS, fontsize=10)
b.set_ylim(0, 1.05)
b.set_title("top-p：累積 0.9 までの候補だけを残す", fontsize=12, loc="left")
b.legend(frameon=False, fontsize=10, loc="center right")

for ax in (a, b):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig("images/sampling_concept.svg", facecolor="#ffffff")
