"""information-theory ノートの実験と図を生成するスクリプト。

本文に載せた実験（breast_cancer の目的変数のエントロピー、KL ダイバージェンスの向き、
相互情報量を数えて計算する、乱数の列のカテゴリ数を増やす、独立な 2 変数の相互情報量、
補正した相互情報量、ドリフトの無い PSI）を同じ順に実行し、出力を標準出力に、
図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/information-theory_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、SciPy 1.18.1、pandas 3.1.1、matplotlib 3.11.2
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import patches
from matplotlib.ticker import FormatStrFormatter
from PIL import Image
from scipy.stats import chi2_contingency, entropy
from sklearn.datasets import load_breast_cancer
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import (adjusted_mutual_info_score, mutual_info_score,
                             normalized_mutual_info_score)
from sklearn.model_selection import train_test_split

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "information-theory"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


bc = load_breast_cancer()
X, y = bc.data, bc.target
names = list(bc.feature_names)

# ---- 実験 1: 目的変数のエントロピー ----
p = np.bincount(y) / len(y)
print("クラスの割合（悪性, 良性）:", p.round(3))
print("H(Y) =", (-(p * np.log(p)).sum()).round(3), "nat =", (-(p * np.log2(p)).sum()).round(3), "bit")
print("scipy.stats.entropy:", entropy(p).round(3))
H_Y = entropy(p)

fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
ax = axes[0]
pp = np.linspace(0.005, 1, 400)
ax.plot(pp, -np.log2(pp), color=BLUE, lw=2)
for pv, lab in [(1, "確実に起きる\n0 bit"), (0.5, "コインの表\n1 bit"), (0.125, "8 通りの 1 つ\n3 bit")]:
    ax.scatter([pv], [-np.log2(pv)], color=INK, zorder=5, s=18)
    ax.annotate(lab, (pv, -np.log2(pv)), xytext=(8, 6), textcoords="offset points", fontsize=9)
ax.set_xlabel("事象の確率 p")
ax.set_ylabel("自己情報量 -log2 p（bit）")
ax.set_title("珍しい事象ほど自己情報量が大きい", fontsize=10)
ax.set_ylim(0, 8)
ax.grid(True, alpha=0.25)
ax = axes[1]
ps = np.linspace(0.001, 0.999, 400)
ax.plot(ps, -(ps * np.log(ps) + (1 - ps) * np.log(1 - ps)), color=BLUE, lw=2)
ax.axhline(np.log(2), color=GRAY, lw=0.8, ls=":")
ax.text(0.02, np.log(2) + 0.015, "最大 log 2 = 0.693 nat（1 bit）", fontsize=9, color=INK)
ax.scatter([p[1]], [H_Y], color=RED, zorder=5)
ax.annotate(f"breast_cancer の目的変数\n良性 {p[1]:.3f} で H = {H_Y:.3f} nat", (p[1], H_Y),
            xytext=(0.32, 0.12), textcoords="data", fontsize=9,
            arrowprops=dict(arrowstyle="->", color=INK))
ax.set_xlabel("2 クラスのうち一方の割合")
ax.set_ylabel("エントロピー H（nat）")
ax.set_title("2 クラスのエントロピーは半々で最大", fontsize=10)
ax.set_ylim(0, 0.8)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "it_entropy.webp")

# ---- 実験 2: KL ダイバージェンスの向き ----
P = np.array([0.25, 0.25, 0.25, 0.25])
Q = np.array([0.4, 0.3, 0.2, 0.1])
R = np.array([0.5, 0.3, 0.2, 0.0])  # 4 つ目の値が一度も出ていない分布
for a, b, la, lb in [(P, Q, "P", "Q"), (P, R, "P", "R")]:
    print(f"KL({la} || {lb}) = {entropy(a, b):.3f}   KL({lb} || {la}) = {entropy(b, a):.3f}  （nat）")

fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
xs = np.arange(4)
for ax, other, lab in [(axes[0], Q, "Q"), (axes[1], R, "R")]:
    ax.bar(xs - 0.2, P, 0.4, color=BLUE, label="P（一様）")
    ax.bar(xs + 0.2, other, 0.4, color=RED, label=lab)
    if other[3] == 0:
        ax.text(3.2, 0.015, f"{lab} は 0", fontsize=9, ha="center", color=RED)
    ax.set_xticks(xs, ["値 1", "値 2", "値 3", "値 4"])
    kl1, kl2 = entropy(P, other), entropy(other, P)
    t1 = "inf" if np.isinf(kl1) else f"{kl1:.3f}"
    ax.set_title(f"KL(P || {lab}) = {t1}　KL({lab} || P) = {kl2:.3f}", fontsize=10)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, axis="y", alpha=0.25)
axes[0].set_ylabel("確率")
axes[0].set_ylim(0, 0.6)
fig.tight_layout()
save(fig, "it_kl.webp")

# ---- 実験 3: 相互情報量を数えて計算する ----
rng = np.random.default_rng(0)
wp = pd.qcut(X[:, names.index("worst perimeter")], 10, labels=False)  # 10 個に区切った列
row_id = rng.permutation(len(y))                                     # 行ごとに違う ID


def mi_by_hand(y, x):
    joint = pd.crosstab(y, x).to_numpy() / len(y)  # 同時分布 P(y, x)
    py, px = joint.sum(axis=1), joint.sum(axis=0)  # 周辺分布
    nz = joint > 0
    return (joint[nz] * np.log(joint[nz] / np.outer(py, px)[nz])).sum()


for name, col in [("worst perimeter（10 区間）", wp), ("行ごとの ID", row_id)]:
    print(f"{name}: 手で計算 {mi_by_hand(y, col):.3f}、mutual_info_score {mutual_info_score(y, col):.3f}、"
          f"H(X) {entropy(np.bincount(col)):.3f}")

fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
for ax, title, hx, mi in [(axes[0], "worst perimeter（10 区間）", np.log(10), mutual_info_score(y, wp)),
                          (axes[1], "行ごとの ID（569 通り）", np.log(len(y)), mutual_info_score(y, row_id))]:
    ry, rx = 1.0, 1.0 * np.sqrt(hx / H_Y) * 0.55  # 円の面積を量に比例させず、見える範囲で大小を付ける
    d = rx + ry - 2 * ry * (mi / H_Y)               # 重なりの幅を I / H(Y) に合わせる
    cy, cx = (0, 0), (d, 0)
    ax.add_patch(patches.Circle(cy, ry, facecolor=RED, alpha=0.35, edgecolor=RED))
    ax.add_patch(patches.Circle(cx, rx, facecolor=BLUE, alpha=0.35, edgecolor=BLUE))
    ax.text(-ry - 0.05, ry + 0.15, f"H(Y) = {H_Y:.3f}", fontsize=9, color=RED)
    ax.text(cx[0] + rx * 0.2, rx + 0.12, f"H(X) = {hx:.3f}", fontsize=9, color="#3b6f8f")
    ax.text((d - rx + ry) / 2 - 0.0, -0.08, f"I = {mi:.3f}", fontsize=10, ha="center", color=INK)
    left = abs(H_Y - mi)
    ax.text(-ry - 0.05, -ry - 0.2, f"H(Y|X) = {left:.3f}", fontsize=9, color=INK)
    ax.set_title(title, fontsize=10)
    ax.set_xlim(-1.4, d + rx + 0.3)
    ax.set_ylim(-max(rx, ry) - 0.3, max(rx, ry) + 0.5)
    ax.set_aspect("equal")
    ax.axis("off")
fig.suptitle("目的変数 Y のエントロピーのうち、列 X を知ると減る分が相互情報量 I（nat）", fontsize=10)
fig.tight_layout()
save(fig, "it_venn.webp")

# ---- 実験 4（表紙）: 乱数の列のカテゴリ数を増やす ----
rng = np.random.default_rng(1)
real = np.array([mutual_info_score(y, pd.qcut(X[:, j], 10, labels=False, duplicates="drop"))
                 for j in range(X.shape[1])])
ks = [2, 5, 10, 20, 50, 100, 200, 300, 400, len(y)]
mi_rand, ami_rand = [], []
for k in ks:
    v, a = [], []
    for _ in range(20):
        col = rng.permutation(len(y)) % k  # 0〜k-1 をほぼ同じ数ずつ、無作為に並べた列
        v.append(mutual_info_score(y, col))
        a.append(adjusted_mutual_info_score(y, col))
    mi_rand.append(np.mean(v))
    ami_rand.append(np.mean(a))
    print(f"カテゴリ {k:3d}: 相互情報量 {np.mean(v):.3f}、AMI {np.mean(a):+.3f}、"
          f"これより低い 30 列 {(real < np.mean(v)).sum()} / 30")
print(f"30 列（10 区間）の相互情報量: 最小 {real.min():.3f}、中央値 {np.median(real):.3f}、最大 {real.max():.3f}")

fig, ax = plt.subplots(figsize=(8, 4.6))
for r in real:
    ax.axhline(r, color=GRAY, lw=0.6, alpha=0.7)
ax.axhline(real.max(), color=INK, lw=1, ls="--")
ax.text(2.1, real.max() + 0.012, f"30 列で最大の worst perimeter（{real.max():.3f}）", fontsize=9, color=INK)
ax.text(2.1, np.median(real) + 0.012, "灰色の線: breast_cancer の 30 列（10 区間に区切った値）", fontsize=9, color="#666666")
ax.plot(ks, mi_rand, color=RED, lw=2.2, marker="o", ms=4, label="乱数の列の相互情報量")
ax.plot(ks, ami_rand, color=BLUE, lw=2.2, marker="s", ms=4, label="同じ列の AMI（偶然の分を補正した値）")
ax.axhline(H_Y, color=RED, lw=0.8, ls=":")
ax.text(2.1, H_Y + 0.012, f"H(Y) = {H_Y:.3f}（上限）", fontsize=9, color=RED)
ax.annotate("569 通り = 行ごとに違う ID", (len(y), mi_rand[-1]), xytext=(-170, -30),
            textcoords="offset points", fontsize=9, arrowprops=dict(arrowstyle="->", color=INK))
ax.set_xscale("log")
ax.set_xticks(ks[:-1] + [len(y)], [str(k) for k in ks[:-1]] + ["569"])
ax.set_xlabel("乱数の列のカテゴリ数（対数目盛）")
ax.set_ylabel("目的変数との相互情報量（nat）")
ax.set_ylim(-0.03, 0.72)
ax.legend(fontsize=9, loc="center left", bbox_to_anchor=(0.0, 0.42))
ax.grid(True, axis="x", alpha=0.2)
fig.tight_layout()
save(fig, "it_cover.webp")

# ---- 実験 5: 独立な 2 変数の相互情報量 ----
rng = np.random.default_rng(2)
ns = [50, 100, 200, 500, 1000, 2000, 5000]
fig, ax = plt.subplots(figsize=(8, 4.2))
for k, color in [(2, GREEN), (10, BLUE), (50, RED)]:
    means = []
    for n in ns:
        v = [mutual_info_score(rng.integers(0, 2, n), rng.integers(0, k, n)) for _ in range(300)]
        means.append(np.mean(v))
    print(f"カテゴリ {k:2d}: " + "、".join(f"n={n} {m:.4f}（式 {(k - 1) / (2 * n):.4f}）" for n, m in zip(ns, means)))
    ax.plot(ns, means, color=color, lw=2, marker="o", ms=4, label=f"{k} カテゴリの列（実測の平均）")
    ax.plot(ns, [(k - 1) / (2 * n) for n in ns], color=color, lw=1, ls="--")
ax.plot([], [], color=GRAY, ls="--", label="式 (k - 1)(c - 1) / (2n)")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xticks(ns, [str(n) for n in ns])
ax.yaxis.set_major_formatter(FormatStrFormatter("%g"))
ax.set_xlabel("件数 n（対数目盛）")
ax.set_ylabel("相互情報量の平均（nat、対数目盛）")
ax.set_title("独立な 2 クラスの目的変数と k カテゴリの列（各 300 回）", fontsize=10)
ax.legend(fontsize=9)
ax.grid(True, which="both", alpha=0.2)
fig.tight_layout()
save(fig, "it_bias.webp")

n = len(y)
rng = np.random.default_rng(3)
r200 = rng.permutation(n) % 200
g, _, dof, _ = chi2_contingency(pd.crosstab(y, r200), lambda_="log-likelihood")
print(f"200 カテゴリの乱数の列: 2n × 相互情報量 = {2 * n * mutual_info_score(y, r200):.1f}、G = {g:.1f}、自由度 {dof}")

# ---- 実験 6: 補正した値と mutual_info_classif ----
for name, col in [("worst perimeter（10 区間）", wp), ("200 カテゴリの乱数", r200), ("行ごとの ID", row_id)]:
    print(f"{name}: MI {mutual_info_score(y, col):.3f}、NMI {normalized_mutual_info_score(y, col):.3f}、"
          f"AMI {adjusted_mutual_info_score(y, col):+.3f}")
real_nmi = np.array([normalized_mutual_info_score(y, pd.qcut(X[:, j], 10, labels=False, duplicates="drop"))
                     for j in range(X.shape[1])])
print(f"NMI が行ごとの ID より低い 30 列: {(real_nmi < normalized_mutual_info_score(y, row_id)).sum()} / 30")
for name, kw in [("連続の値として（既定）", {}), ("離散の値として", {"discrete_features": True})]:
    v = mutual_info_classif(row_id.reshape(-1, 1), y, random_state=0, **kw)[0]
    print(f"mutual_info_classif、行ごとの ID を{name}: {v:.3f}")
print("mutual_info_classif、並べ替えない行番号:",
      mutual_info_classif(np.arange(n).reshape(-1, 1), y, random_state=0)[0].round(3))
print("57 行ごとの良性の割合:", [round(float(y[i:i + 57].mean()), 2) for i in range(0, n, 57)])

# ---- 実験 7: ドリフトの無い PSI ----
x_tr, _ = train_test_split(X[:, names.index("mean area")], test_size=0.3, random_state=0, stratify=y)
edges = np.quantile(x_tr, np.linspace(0, 1, 11))
edges[0], edges[-1] = -np.inf, np.inf
b = np.histogram(x_tr, edges)[0] / len(x_tr)  # 学習時の 10 区間の割合（どれも約 0.1）
rng = np.random.default_rng(4)


def psi(q, b, eps):
    q, b = np.clip(q, eps, 1), np.clip(b, eps, 1)
    return ((q - b) * np.log(q / b)).sum()


ms = [30, 50, 100, 200, 500, 1000]
eps_list = [1e-6, 1e-4, 1e-2]
psi_mean, over01, empty_psi = [], [], {}
for m in ms:
    vals, empty = {e: [] for e in [1e-6, 1e-4, 1e-2]}, []
    for _ in range(3000):
        live = rng.choice(x_tr, m, replace=True)  # 学習時と同じ分布から m 件
        q = np.histogram(live, edges)[0] / m
        empty.append((q == 0).any())
        for e in vals:
            vals[e].append(psi(q, b, e))
    empty, v = np.array(empty), np.array(vals[1e-6])
    print(f"m={m:4d}: 空の区間がある回 {empty.mean():.1%}、空の無い回の PSI の平均 {v[~empty].mean():.3f}"
          f"（(10 - 1) / m = {9 / m:.3f}）、0.1 を超えた回 {(v > 0.1).mean():.1%}")
    if m == 30:
        print("  空の区間がある回の PSI の中央値:",
              "、".join(f"ε={e:g} で {np.median(np.array(x)[empty]):.2f}" for e, x in vals.items()))
        empty_psi = {e: np.median(np.array(x)[empty]) for e, x in vals.items()}
    psi_mean.append(v[~empty].mean())
    over01.append((v > 0.1).mean())

fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw={"width_ratios": [1.6, 1]})
ax = axes[0]
ax.plot(ms, psi_mean, color=RED, lw=2, marker="o", ms=4, label="PSI の平均（空の区間が無い回）")
ax.plot(ms, [9 / m for m in ms], color=INK, lw=1, ls="--", label="(区間の数 - 1) / 件数")
for t in [0.1, 0.25]:
    ax.axhline(t, color=GRAY, lw=0.8, ls=":")
    ax.text(ms[-1], t * 1.06, f"{t}", fontsize=9, color="#666666", ha="right")
for m, mv, o in zip(ms, psi_mean, over01):
    if m in (50, 100, 200):
        ax.annotate(f"0.1 超え {o:.1%}", (m, mv), xytext=(6, 6), textcoords="offset points", fontsize=9)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xticks(ms, [str(m) for m in ms])
ax.yaxis.set_major_formatter(FormatStrFormatter("%g"))
ax.set_xlabel("比べる側の件数（対数目盛）")
ax.set_ylabel("PSI（対数目盛）")
ax.set_title("分布が同じでも PSI は件数に反比例して残る", fontsize=10)
ax.legend(fontsize=9, loc="lower left")
ax.grid(True, which="both", alpha=0.2)
ax = axes[1]
labels = [f"{e:g}" for e in eps_list]
ax.bar(labels, [empty_psi[e] for e in eps_list], color=[RED, "#ec8f90", "#f4c2c3"])
for i, e in enumerate(eps_list):
    ax.text(i, empty_psi[e] + 0.03, f"{empty_psi[e]:.2f}", ha="center", fontsize=9)
ax.set_xlabel("0 を置き換える小さな値 ε")
ax.set_ylabel("PSI の中央値")
ax.set_title("30 件で空の区間が出た回の PSI", fontsize=10)
ax.grid(True, axis="y", alpha=0.25)
fig.tight_layout()
save(fig, "it_psi.webp")
