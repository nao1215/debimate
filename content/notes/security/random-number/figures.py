"""Random Number - 暗号で乱数がなぜ重要なのか の図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/security/random-number/figures.py
"""

import pathlib

import matplotlib

matplotlib.use("Agg")  # 表示せずファイルへ書く
import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#666666"

plt.rcParams.update({
    "figure.figsize": (6, 4),
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

OUT = pathlib.Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)


def save(name: str) -> None:
    path = OUT / name
    plt.savefig(path)
    plt.close()
    print(f"wrote {path}")


# --- 図1: 種のビット数と探索候補数 ---
seed_bits = [8, 15, 32, 128, 256]
candidates = [2.0 ** b for b in seed_bits]
positions = np.arange(len(seed_bits))

plt.figure()
plt.bar(positions, candidates, width=0.55,
        color=[COLOR_RED, COLOR_RED, COLOR_BLUE, COLOR_BLUE, COLOR_BLUE],
        edgecolor="white", linewidth=0.5, log=True,
        label="Keys reachable from the seed ($2^{seed}$)")
plt.axhline(2.0 ** 256, color=COLOR_GRAY, linestyle="--", linewidth=1,
            label="Key space of a 256-bit key ($2^{256}$)")
for pos, bits, note in [(0, 8, "256"), (1, 15, "32,768")]:
    plt.text(pos, 2.0 ** bits * 30, note, ha="center", color=COLOR_RED, fontsize=9)
plt.xticks(positions, [f"{b}" for b in seed_bits])
plt.xlabel("Seed size (bits)")
plt.ylabel("Number of reachable keys")
plt.ylim(1, 10.0 ** 95)
plt.legend(loc="upper left", fontsize=9, framealpha=1.0)
save("random_number_seed_space.svg")


# --- 図2: 一様な分布と偏った分布の min-entropy ---
labels = [f"x{i}" for i in range(1, 9)]
uniform = np.full(8, 1.0 / 8.0)
biased = np.array([0.50] + [0.50 / 7.0] * 7)

fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for ax, (title, probs, color) in zip(
    axes,
    [("Uniform: min-entropy = 3.0 bits", uniform, COLOR_BLUE),
     ("Biased: min-entropy = 1.0 bit", biased, COLOR_RED)],
):
    ax.bar(labels, probs, color=color, edgecolor="white", linewidth=0.5)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("Output value")
    top = float(np.max(probs))
    ax.axhline(top, color=COLOR_GRAY, linestyle="--", linewidth=1)
    ax.text(0.05, top + 0.02, f"max p = {top:.3f}", color=COLOR_GRAY, fontsize=9)
axes[0].set_ylabel("Probability")
axes[0].set_ylim(0, 0.62)
save("random_number_min_entropy.svg")


# --- 図3: modulo bias ---
raw = np.arange(256)
mapped = raw % 200 + 1
values, counts = np.unique(mapped, return_counts=True)

plt.figure(figsize=(7, 3.6))
plt.bar(values, counts, width=1.0,
        color=[COLOR_RED if c == 2 else COLOR_BLUE for c in counts])
plt.xlabel("Value returned by (byte % 200) + 1")
plt.ylabel("Number of source bytes")
plt.yticks([0, 1, 2])
plt.xlim(0, 201)
plt.text(6, 2.18, "1-56: two source bytes each", color=COLOR_RED, fontsize=9)
plt.text(100, 1.18, "57-200: one source byte each", color=COLOR_GRAY, fontsize=9)
plt.ylim(0, 2.6)
save("random_number_modulo_bias.svg")


# --- 図4: nonce の衝突確率 ---
n = np.logspace(3, 15, 400)
plt.figure()
for bits, color in [(64, COLOR_RED), (96, COLOR_BLUE), (128, COLOR_GREEN)]:
    p = -np.expm1(-(n ** 2) / (2.0 * 2.0 ** bits))
    plt.loglog(n, p, color=color, linewidth=1.6, label=f"{bits}-bit nonce")
plt.axvline(2.0 ** 32, color=COLOR_GRAY, linestyle="--", linewidth=1)
plt.text(2.0 ** 32 * 1.6, 1e-8, "$2^{32}$ invocations", color=COLOR_GRAY, fontsize=9)
plt.xlabel("Number of nonces issued under one key")
plt.ylabel("Probability of at least one collision")
plt.ylim(1e-36, 2.0)
plt.legend(loc="lower right", fontsize=9, framealpha=1.0)
save("random_number_nonce_collision.svg")
