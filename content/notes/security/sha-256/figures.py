"""Hash Function - なぜ任意長のデータを固定長に変換できるのか の図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/security/hash-function/figures.py
"""

import hashlib
import pathlib

import matplotlib

matplotlib.use("Agg")  # 表示せずファイルへ書く
import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
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
rng = np.random.default_rng(20260904)  # seed を固定して同じ図が出るようにする

PAIRS = 2000
MSG_BYTES = 32


def popcount(data: bytes) -> int:
    return sum(bin(b).count("1") for b in data)


def differing_bits(a: bytes, b: bytes) -> int:
    return popcount(bytes(x ^ y for x, y in zip(a, b)))


def save(name: str) -> None:
    path = OUT / name
    plt.savefig(path)
    plt.close()
    print(f"wrote {path}")


# --- 1 bit だけ違う入力の組で、ハッシュ値の異なる bit 数を数える ---
counts = []
for _ in range(PAIRS):
    msg = bytearray(rng.integers(0, 256, size=MSG_BYTES, dtype=np.uint8).tolist())
    flipped = bytearray(msg)
    pos = int(rng.integers(0, MSG_BYTES * 8))
    flipped[pos // 8] ^= 1 << (pos % 8)
    h1 = hashlib.sha256(bytes(msg)).digest()
    h2 = hashlib.sha256(bytes(flipped)).digest()
    counts.append(differing_bits(h1, h2))

counts = np.array(counts)
print(f"mean={counts.mean():.2f} min={counts.min()} max={counts.max()}")

bins = np.arange(counts.min() - 0.5, counts.max() + 1.5, 1)
plt.hist(counts, bins=bins, color=COLOR_BLUE, edgecolor="white", linewidth=0.4)
plt.axvline(128, color=COLOR_RED, linestyle="--", linewidth=1.5, zorder=5,
            label=f"128 = half of 256 output bits\n(measured mean {counts.mean():.1f})")
plt.xlabel("Differing bits between the two SHA-256 digests")
plt.ylabel(f"Input pairs (out of {PAIRS})")
plt.ylim(0, np.histogram(counts, bins=bins)[0].max() * 1.35)  # 凡例が棒に重ならない余白
plt.legend(loc="upper right", fontsize=9, framealpha=0.9)
plt.annotate(f"min {counts.min()}", xy=(counts.min(), 0), xytext=(counts.min(), 22),
             color=COLOR_GRAY, fontsize=9, ha="left")
plt.annotate(f"max {counts.max()}", xy=(counts.max(), 0), xytext=(counts.max(), 22),
             color=COLOR_GRAY, fontsize=9, ha="right")
save("hash_function_avalanche.svg")
