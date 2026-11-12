"""vector-matrix-ops ノートの実験と図を生成するスクリプト。

本文に載せた実験（足し算とスカラー倍、内積と長さ・角度、digits の内積・コサイン類似度・ユークリッド距離の近傍、
行列積で全ての組の内積をまとめて求める、ブロードキャストで MSE がずれる、掛ける順と時間）を
同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/vector-matrix-ops_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4（OpenBLAS 0.3.34）
"""
import time
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from PIL import Image
from sklearn.datasets import load_diabetes, load_digits
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "vector-matrix-ops"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ============================================================
# 実験 0: ベクトルの足し算・引き算とスカラー倍
# ============================================================
a0 = np.array([3, 1])
b0 = np.array([1, 2])
v0 = np.array([2, 1])
print("a + b:", a0 + b0, " a - b:", a0 - b0)
print("1.5 * v:", 1.5 * v0, " -1 * v:", -1 * v0, " 0 * v:", 0 * v0)

fig, (axl, axr) = plt.subplots(1, 2, figsize=(9.0, 3.6))


def arrow(ax, start, end, color, lw=2.2):
    ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="-|>", color=color, lw=lw))


arrow(axl, (0, 0), a0, BLUE)
arrow(axl, a0, a0 + b0, GREEN)
arrow(axl, (0, 0), a0 + b0, RED)
axl.text(1.6, 0.25, "a = (3, 1)", color=BLUE, fontsize=9)
axl.text(3.75, 1.5, "b = (1, 2)\n（a の先に継ぎ足す）", color=GREEN, fontsize=9)
axl.text(0.9, 1.9, "a + b = (4, 3)", color=RED, fontsize=9)
axl.set_xlim(-0.5, 6.2)
axl.set_ylim(-0.5, 3.6)
axl.set_title("足し算: 矢印の継ぎ足し", fontsize=10)
for k, color, dy in [(1.5, RED, 0.25), (1.0, BLUE, -0.45), (-1.0, GREEN, 0.25)]:
    end = k * v0
    arrow(axr, (0, 0), end, color, lw=3.0 if k == 1.0 else 2.2)
    label = {1.5: "1.5 * v = (3, 1.5)", 1.0: "v = (2, 1)", -1.0: "-1 * v = (-2, -1)"}[k]
    tx, ty = (end[0] - 0.2, end[1] + dy) if k > 0 else (end[0] - 0.6, end[1] - 0.5)
    axr.text(tx, ty, label, color=color, fontsize=9)
axr.plot(0, 0, "o", color=INK, ms=4)
axr.text(0.15, -0.55, "0 * v = (0, 0)", color=INK, fontsize=9)
axr.set_xlim(-3.0, 4.2)
axr.set_ylim(-1.9, 2.4)
axr.set_title("スカラー倍: 正なら同じ向き、負なら逆向き", fontsize=10)
for ax in (axl, axr):
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.25)
save(fig, "vmo_vector_basics.webp")

# ============================================================
# 実験 1: 内積は長さと角度の積
# ============================================================
def polar(r, deg):
    return r * np.array([np.cos(np.radians(deg)), np.sin(np.radians(deg))])


q = polar(2.0, 20)
a = polar(1.5, 30)   # q との角度 10 度、短い
b = polar(4.0, 70)   # q との角度 50 度、長い
for name, v in [("a", a), ("b", b)]:
    cos = q @ v / (np.linalg.norm(q) * np.linalg.norm(v))
    print(f"{name}: 長さ {np.linalg.norm(v):.1f}  角度 {np.degrees(np.arccos(cos)):.0f} 度  "
          f"内積 {q @ v:.2f}  コサイン類似度 {cos:.3f}")

fig, ax = plt.subplots(figsize=(6.2, 4.6))
u = q / np.linalg.norm(q)
for v, name, color in [(a, "a", GREEN), (b, "b", RED)]:
    ax.annotate("", xy=v, xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=color, lw=2.2))
    p = (v @ u) * u
    ax.plot([v[0], p[0]], [v[1], p[1]], ls=":", color=color, lw=1.2)
    ax.plot(*p, "o", color=color, ms=5)
    cos = q @ v / (np.linalg.norm(q) * np.linalg.norm(v))
    tx, ty = (v[0] + 0.08, v[1] + 0.05) if name == "b" else (2.55, 0.0)
    ax.text(tx, ty,
            f"{name}: 長さ {np.linalg.norm(v):.1f}、q との角度 {np.degrees(np.arccos(cos)):.0f} 度\n"
            f"内積 {q @ v:.2f}、コサイン類似度 {cos:.2f}", color=color, fontsize=9)
ax.annotate("", xy=q, xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=INK, lw=2.2))
ax.text(q[0] + 0.1, q[1] - 0.05, "q: 長さ 2.0", color=INK, fontsize=9)
ax.plot([0, 4.0 * u[0]], [0, 4.0 * u[1]], color=GRAY, lw=0.8, ls="--")
ax.text(4.0 * u[0] + 0.05, 4.0 * u[1] + 0.05, "q の向き", color=GRAY, fontsize=9)
ax.set_xlim(-0.3, 5.2)
ax.set_ylim(-0.3, 4.3)
ax.set_aspect("equal")
ax.grid(True, alpha=0.25)
ax.set_title("内積 = q の長さ × q の向きに落とした影の長さ（逆向きなら負）", fontsize=10)
save(fig, "vmo_dot_geometry.webp")

# ============================================================
# 実験 2: digits で、内積・コサイン類似度・ユークリッド距離の一番近い画像
# ============================================================
digits = load_digits()
X = digits.data            # 1797 枚 × 64 画素（0〜16 の濃さ）
y = digits.target

G = X @ X.T                                    # 全ての組の内積（1797 × 1797）
norm = np.linalg.norm(X, axis=1)               # 各画像の長さ
cos_sim = G / np.outer(norm, norm)             # コサイン類似度
dist2 = norm[:, None] ** 2 + norm[None, :] ** 2 - 2 * G  # ユークリッド距離の 2 乗

nearest = {}
for name, S, larger in [("内積", G, True), ("コサイン類似度", cos_sim, True),
                        ("ユークリッド距離", dist2, False)]:
    S = S.astype(float).copy()
    np.fill_diagonal(S, -np.inf if larger else np.inf)   # 自分自身は除く
    nn = S.argmax(axis=1) if larger else S.argmin(axis=1)
    nearest[name] = nn
    hits = np.bincount(nn, minlength=len(X))           # 一番近いと選ばれた回数
    print(f"{name:<10}: 一番近い画像が同じ数字 {np.mean(y[nn] == y):.1%}  "
          f"一番近いと選ばれた画像 {np.count_nonzero(hits)} 枚  "
          f"最多 {hits.max()} 回（{hits.argmax()} 番、数字 {y[hits.argmax()]}）")

hub = int(np.bincount(nearest["内積"]).argmax())
print("内積で", hub, "番を選んだ画像の数字ごとの枚数:", np.bincount(y[nearest["内積"] == hub], minlength=10).tolist())
print(f"{hub} 番の長さ {norm[hub]:.1f}（全画像で {np.sum(norm > norm[hub]) + 1} 番目）  "
      f"長さの中央値 {np.median(norm):.1f}")
nn_dot = nearest["内積"]
print("内積で、一番近い画像が数字 1 だった枚数:", int(np.sum(y[nn_dot] == 1)),
      " そのうち本当は 1 以外:", int(np.sum((y[nn_dot] == 1) & (y != 1))))
print("数字ごとの一致率（内積）:", [f"{k}:{np.mean(y[nn_dot][y == k] == k):.0%}" for k in range(10)])

# 表紙: 内積ではハブを選び、コサイン類似度では同じ数字を選ぶ例
cands = [i for i in np.where(nn_dot == hub)[0] if y[i] != 1]
picks = []
for k in [4, 7, 8, 5, 9]:
    picks.append(next(i for i in cands if y[i] == k))
fig = plt.figure(figsize=(9.2, 4.6))
gsp = fig.add_gridspec(3, 7, width_ratios=[1.6, 0.9, 1, 1, 1, 1, 1],
                       hspace=0.45, wspace=0.15)
axh = fig.add_subplot(gsp[:, 0])
axh.imshow(X[hub].reshape(8, 8), cmap="gray_r", vmin=0, vmax=16)
axh.set_xticks([]); axh.set_yticks([])
for s in axh.spines.values():
    s.set_visible(True); s.set_color(RED); s.set_linewidth(2.5)
axh.set_title(f"{hub} 番（数字 1）\n長さ {norm[hub]:.1f} は全画像で最大", fontsize=9, color=RED)
row_names = ["問い合わせの画像", "内積で 1 位", "コサイン類似度で 1 位"]
for c, i in enumerate(picks):
    for r, idx in enumerate([i, nn_dot[i], nearest["コサイン類似度"][i]]):
        ax = fig.add_subplot(gsp[r, c + 2])
        ax.imshow(X[idx].reshape(8, 8), cmap="gray_r", vmin=0, vmax=16)
        ax.set_xticks([]); ax.set_yticks([])
        if r == 1:
            col = RED
        elif r == 2:
            col = GREEN if y[idx] == y[i] else GRAY   # 違う数字を選んだ所は灰色
        else:
            col = INK
        for s in ax.spines.values():
            s.set_visible(True); s.set_color(col); s.set_linewidth(1.6 if r else 0.8)
        ax.set_title(f"数字 {y[idx]}", fontsize=8.5, color=col, pad=2)
        if c == 0:
            ax.set_ylabel(row_names[r], fontsize=9, rotation=0, ha="right", va="center", labelpad=8)
fig.suptitle(f"digits の 1797 枚のうち {np.bincount(nn_dot).max()} 枚が、内積では {hub} 番を一番近いと選ぶ",
             fontsize=11, y=1.0)
save(fig, "vmo_cover.webp")

# 長さと、一番近いと選ばれた回数
fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.8), sharey=True)
for ax, name, color in [(axes[0], "内積", RED), (axes[1], "コサイン類似度", GREEN)]:
    hits = np.bincount(nearest[name], minlength=len(X))
    ax.scatter(norm, hits, s=9, color=color, alpha=0.6, edgecolors="none")
    ax.set_title(f"{name}で一番近い画像を選んだ時", fontsize=10)
    ax.set_xlabel("画像の長さ（64 画素のベクトルのノルム）")
    ax.grid(True, alpha=0.25)
    ax.text(0.03, 0.93, f"一番近いと選ばれた画像 {np.count_nonzero(hits)} 枚\n同じ数字を選んだ割合 "
            f"{np.mean(y[nearest[name]] == y):.1%}", transform=ax.transAxes, fontsize=9, va="top")
axes[0].set_ylabel("他の画像から一番近いと\n選ばれた回数")
axes[0].annotate(f"{hub} 番（数字 1）: {np.bincount(nn_dot).max()} 回", xy=(norm[hub], np.bincount(nn_dot).max()),
                 xytext=(57, 115), fontsize=9, color=RED,
                 arrowprops=dict(arrowstyle="->", color=RED))
save(fig, "vmo_norm_hits.webp")

# ============================================================
# 実験 3a: 行列とベクトルの積は、平面の変換
# ============================================================
th = np.radians(30)
R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])  # 30 度回す
S = np.array([[2.0, 0.0], [0.0, 1.0]])                              # 横に 2 倍
g = np.linspace(-1, 1, 5)
lines = [np.column_stack([g, np.full(5, c)]) for c in g] + [np.column_stack([np.full(5, c), g]) for c in g]
e1, e2 = np.array([1.0, 0.0]), np.array([0.0, 1.0])
print("S @ R の 1 列目と 2 列目:", np.round(S @ R, 3).T.tolist())
print("S @ (R @ e1) と (S @ R) @ e1:", np.round(S @ (R @ e1), 3), np.round((S @ R) @ e1, 3))

fig, axes = plt.subplots(1, 4, figsize=(11.6, 3.2))
for ax, M, title in [(axes[0], np.eye(2), "元の格子"), (axes[1], R, "R: 30 度回す"),
                     (axes[2], S, "S: 横に 2 倍"), (axes[3], S @ R, "S @ R: 回してから横に 2 倍")]:
    for ln in lines:
        pts = ln @ M.T                     # 各点 x を M @ x に移す
        ax.plot(pts[:, 0], pts[:, 1], color=BLUE, lw=0.9)
    for e, col, nm in [(e1, RED, "M の 1 列目"), (e2, GREEN, "M の 2 列目")]:
        tip = M @ e
        ax.annotate("", xy=tip, xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=col, lw=2))
    ax.set_xlim(-2.9, 2.9); ax.set_ylim(-1.9, 1.9)
    ax.set_aspect("equal"); ax.grid(True, alpha=0.2)
    ax.set_title(title, fontsize=10)
axes[0].text(1.05, -0.35, "(1, 0)", color=RED, fontsize=9)
axes[0].text(0.08, 1.15, "(0, 1)", color=GREEN, fontsize=9)
fig.text(0.5, 0.02, "赤い矢印は (1, 0) の、緑の矢印は (0, 1) の移った先で、それぞれ行列の 1 列目と 2 列目に等しい",
         ha="center", fontsize=9)
save(fig, "vmo_transform.webp")

P = np.array([[1.0, 0.0], [0.0, 0.0]])   # 平面の点を横軸の上に潰す
print("P @ (1, 2) と P @ (1, -3):", P @ np.array([1.0, 2.0]), P @ np.array([1.0, -3.0]))
try:
    np.linalg.inv(P)
except np.linalg.LinAlgError as e:
    print("np.linalg.inv(P):", type(e).__name__, e)

# ============================================================
# 実験 3: 行列積は全ての組の内積の表
# ============================================================
w = np.ones(X.shape[1])                  # 64 個の重み、形は (64,)
print("X @ w の形:", (X @ w).shape, " X @ w.reshape(-1, 1) の形:", (X @ w.reshape(-1, 1)).shape)


def best_time(f, repeat=50):
    f()                                   # 1 回目は計らない
    ts = []
    for _ in range(repeat):
        t = time.perf_counter()
        f()
        ts.append(time.perf_counter() - t)
    return float(np.min(ts))              # 他の処理に割り込まれにくい最短の回


t_mat = best_time(lambda: X @ X.T)
t0 = time.perf_counter()
G_loop = np.empty((len(X), len(X)))
for i in range(len(X)):
    for j in range(len(X)):
        G_loop[i, j] = X[i] @ X[j]          # 1 組ずつ内積を取る
t_loop = time.perf_counter() - t0
print(f"X @ X.T       : {t_mat * 1e3:.1f} ms")
print(f"二重ループ    : {t_loop * 1e3:.0f} ms（{t_loop / t_mat:.0f} 倍）  結果が一致: {np.allclose(G_loop, G)}")

fig, ax = plt.subplots(figsize=(8.6, 3.6))
ax.set_xlim(0, 10.6); ax.set_ylim(0, 4.4); ax.axis("off")
ax.add_patch(Rectangle((0.2, 0.6), 1.2, 3.2, fc="#eef4f8", ec=INK))
ax.add_patch(Rectangle((0.2, 2.6), 1.2, 0.22, fc=BLUE, ec="none"))
ax.text(0.8, 0.3, "X\n1797 × 64", ha="center", va="top", fontsize=9)
ax.text(0.8, 2.92, "i 行目", ha="center", va="bottom", fontsize=8.5, color=INK)
ax.text(1.85, 2.2, "@", fontsize=16, ha="center", va="center")
ax.add_patch(Rectangle((2.3, 2.6), 3.2, 1.2, fc="#eef4f8", ec=INK))
ax.add_patch(Rectangle((3.6, 2.6), 0.22, 1.2, fc=BLUE, ec="none"))
ax.text(3.9, 2.45, "X.T  64 × 1797", ha="center", va="top", fontsize=9)
ax.text(3.71, 3.9, "j 列目", ha="center", va="bottom", fontsize=8.5)
ax.text(6.0, 2.2, "=", fontsize=16, ha="center", va="center")
ax.add_patch(Rectangle((6.6, 0.6), 3.2, 3.2, fc="#fbeaea", ec=INK))
ax.add_patch(Rectangle((7.9, 2.6), 0.22, 0.22, fc=RED, ec="none"))
ax.plot([6.6, 7.9], [2.71, 2.71], color=RED, lw=0.8, ls=":")
ax.plot([8.01, 8.01], [3.8, 2.82], color=RED, lw=0.8, ls=":")
ax.text(8.2, 0.3, "X @ X.T  1797 × 1797", ha="center", va="top", fontsize=9)
ax.text(8.25, 2.5, "(i, j) の値 =\ni 行目と j 列目の内積", ha="left", va="top", fontsize=8.5, color=RED)
ax.set_title(f"1 回の行列積で 1797 × 1797 組の内積を求める（{t_mat * 1e3:.1f} ms。1 組ずつの二重ループは "
             f"{t_loop:.1f} 秒）", fontsize=10)
save(fig, "vmo_gram.webp")

# ============================================================
# 実験 4: 形が合わないまま引くと、ブロードキャストで行列になる
# ============================================================
diabetes = load_diabetes()
Xd, yd = diabetes.data, diabetes.target               # 442 人 × 10 列、yd の形は (442,)
model = LinearRegression().fit(Xd, yd.reshape(-1, 1))  # 目的変数を 1 列の表で渡した
pred = model.predict(Xd)                               # 形は (442, 1)
diff = yd - pred
print("yd の形:", yd.shape, " pred の形:", pred.shape, " yd - pred の形:", diff.shape)
mse_wrong = np.mean((yd - pred) ** 2)
mse_right = np.mean((yd - pred.ravel()) ** 2)
print(f"形を揃えずに計算した MSE: {mse_wrong:,.0f}")
print(f"pred.ravel() で揃えた MSE: {mse_right:,.0f}")
print(f"mean_squared_error         : {mean_squared_error(yd, pred):,.0f}")
print(f"yd の分散（平均で予測した時の MSE）: {yd.var():,.0f}")

fig = plt.figure(figsize=(9.6, 3.8))
ax = fig.add_axes([0.0, 0.0, 0.52, 1.0])
ax.set_xlim(0, 6); ax.set_ylim(0, 5); ax.axis("off")
ax.add_patch(Rectangle((1.6, 4.2), 4.0, 0.3, fc="#eef4f8", ec=INK))
ax.text(3.6, 4.6, "yd  形 (442,)", ha="center", va="bottom", fontsize=9)
ax.add_patch(Rectangle((0.9, 0.2), 0.3, 3.8, fc="#fbeaea", ec=INK))
ax.text(0.75, 2.1, "pred\n形 (442, 1)", ha="right", va="center", fontsize=9)
ax.add_patch(Rectangle((1.6, 0.2), 4.0, 3.8, fc="#f4f4f4", ec=INK))
ax.text(3.6, 2.35, "yd - pred\n形 (442, 442)", ha="center", va="center", fontsize=10)
ax.text(3.6, 1.45, f"(i, j) = yd[j] - pred[i]\n442 × 442 = {442 * 442:,} 個の差", ha="center",
        va="center", fontsize=8.5, color=RED)
ax2 = fig.add_axes([0.62, 0.15, 0.36, 0.72])
vals = [mse_right, yd.var(), mse_wrong]
labels = ["形を揃えた\nMSE", "平均で予測した\nMSE（分散）", "形を揃えない\nMSE"]
bars = ax2.bar(labels, vals, color=[GREEN, GRAY, RED], width=0.6)
for bb, v in zip(bars, vals):
    ax2.text(bb.get_x() + bb.get_width() / 2, v + 120, f"{v:,.0f}", ha="center", fontsize=9)
ax2.set_ylim(0, 10500)
ax2.set_title("diabetes の線形回帰の MSE", fontsize=10)
ax2.tick_params(axis="x", labelsize=8.5)
ax2.grid(True, axis="y", alpha=0.25)
save(fig, "vmo_broadcast.webp")

# ============================================================
# 実験 5: 掛ける順で計算量が変わる
# ============================================================
v = np.random.default_rng(0).normal(size=len(X))      # 1797 個の重み
left = X @ X.T @ v            # Python の @ は左から: (X @ X.T) @ v
right = X @ (X.T @ v)
print("2 つの結果が一致:", np.allclose(left, right))
t_left = best_time(lambda: X @ X.T @ v)
t_right = best_time(lambda: X @ (X.T @ v))
t_multi = best_time(lambda: np.linalg.multi_dot([X, X.T, v]))
t_gram = best_time(lambda: X @ X.T)                 # 途中の X @ X.T だけ
n, d = X.shape
mul_left = n * d * n + n * n          # X @ X.T と、その結果 @ v の掛け算の回数
mul_right = d * n + n * d             # X.T @ v と、X @ その結果
print(f"(X @ X.T) @ v : {t_left * 1e3:.2f} ms  掛け算 {mul_left:,} 回")
print(f"X @ (X.T @ v) : {t_right * 1e3:.3f} ms  掛け算 {mul_right:,} 回")
print(f"multi_dot     : {t_multi * 1e3:.3f} ms")
print(f"途中の X @ X.T: {t_gram * 1e3:.2f} ms")
print(f"時間の比 {t_left / t_right:.0f} 倍、掛け算の回数の比 {mul_left / mul_right:.0f} 倍")

fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4))
names = ["(X @ X.T) @ v\n途中に 1797 × 1797", "X @ (X.T @ v)\n途中に 64 個"]
for ax, vals, title, fmt in [(axes[0], [mul_left, mul_right], "掛け算の回数", ["{:,.0f} 回"] * 2),
                             (axes[1], [t_left * 1e3, t_right * 1e3], "かかった時間（50 回の最短）",
                              ["{:.2f} ms", "{:.3f} ms"])]:
    bars = ax.bar(names, vals, color=[RED, GREEN], width=0.55)
    ax.set_yscale("log")
    ax.set_title(title, fontsize=10)
    ax.set_ylim(min(vals) / 3, max(vals) * 8)
    for bb, val, f in zip(bars, vals, fmt):
        ax.text(bb.get_x() + bb.get_width() / 2, val * 1.4, f.format(val), ha="center", fontsize=9)
    ax.tick_params(axis="x", labelsize=9)
    ax.grid(True, axis="y", alpha=0.25)
fig.suptitle(f"同じ答えでも、掛ける順で掛け算は {mul_left / mul_right:.0f} 倍、時間は {t_left / t_right:.0f} 倍違う",
             fontsize=11, y=1.03)
save(fig, "vmo_chain.webp")
