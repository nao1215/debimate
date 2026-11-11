"""backpropagation ノートの実験と図を生成するスクリプト。

本文に載せた実験（2 層の手計算と数値微分、digits の 3 層 NN と backward の書き間違い、
勾配の照合、数値微分との速さの比較、層を深くした時の勾配と学習曲線）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/backpropagation_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
"""
import time
from io import BytesIO
from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "backpropagation"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#4e79a7", "#e15759", "#59a14f", "#333333", "#999999"
ORANGE, PURPLE = "#f28e2b", "#8e6bb0"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ---- 実験 1: 2 層の NN を 1 つのデータで手計算し、数値微分と比べる ----
x, w1, b1, w2, b2, y = 2.0, 3.0, -1.0, 0.5, 2.0, 5.0


def tiny_loss(w1, b1, w2, b2):
    a1 = max(0.0, w1 * x + b1)
    return (w2 * a1 + b2 - y) ** 2


# forward
z1 = w1 * x + b1             # 5
a1 = max(0.0, z1)            # 5（ReLU）
z2 = w2 * a1 + b2            # 4.5
L = (z2 - y) ** 2            # 0.25

# backward（出力側から連鎖律）
dL_dz2 = 2 * (z2 - y)        # -1
dL_dw2 = dL_dz2 * a1         # -5
dL_db2 = dL_dz2 * 1          # -1
dL_da1 = dL_dz2 * w2         # -0.5
dL_dz1 = dL_da1 * (1 if z1 > 0 else 0)  # -0.5
dL_dw1 = dL_dz1 * x          # -1
dL_db1 = dL_dz1 * 1          # -0.5

# 数値微分: 1 つのパラメータだけを ±eps 動かして損失の差を測る
eps = 1e-6
params = {"w1": w1, "b1": b1, "w2": w2, "b2": b2}
numeric = {}
for name in params:
    plus, minus = dict(params), dict(params)
    plus[name] += eps
    minus[name] -= eps
    numeric[name] = (tiny_loss(**plus) - tiny_loss(**minus)) / (2 * eps)

print(f"L = {L}")
print("backward:", {"w1": dL_dw1, "b1": dL_db1, "w2": dL_dw2, "b2": dL_db2})
print("数値微分:", {k: round(v, 6) for k, v in numeric.items()})


def fmt(v):
    return f"{v:g}"


fig, ax = plt.subplots(figsize=(12, 5.2))
R = 0.45
nodes = [
    ("x", 0.5, 3.0, x, None), ("w1", 0.5, 4.6, w1, dL_dw1), ("b1", 0.5, 1.4, b1, dL_db1),
    ("z1", 3.0, 3.0, z1, dL_dz1), ("a1", 5.3, 3.0, a1, dL_da1),
    ("w2", 5.3, 4.6, w2, dL_dw2), ("b2", 5.3, 1.4, b2, dL_db2),
    ("z2", 7.8, 3.0, z2, dL_dz2), ("L", 10.3, 3.0, L, 1.0),
]
pos = {}
for name, xx, yy, val, grad in nodes:
    pos[name] = (xx, yy)
    ax.add_patch(patches.Circle((xx, yy), R, facecolor="white", edgecolor="black", lw=1.3))
    ax.text(xx, yy + 0.12, name, ha="center", va="center", fontsize=11)
    ax.text(xx, yy - 0.18, f"={fmt(val)}", ha="center", va="center", fontsize=9.5, color=BLUE)
    if grad is not None:  # 勾配は矢印と重ならない位置に置く（上の段は上、それ以外は下）
        if yy > 4:
            gx, gy, ha = xx, yy + R + 0.12, "center"
        elif name == "z2":  # 下は逆向きの矢印が通るので右下に置く
            gx, gy, ha = xx + 0.35, yy - R - 0.45, "left"
        elif name == "L":  # 右下を z2 の勾配に譲り、上の矢印のさらに上に置く
            gx, gy, ha = xx, yy + R + 0.45, "center"
        else:
            gx, gy, ha = xx, yy - R - 0.35, "center"
        ax.text(gx, gy, f"∂L/∂{name} = {fmt(grad)}", ha=ha, va="bottom", fontsize=10, color=RED)
for src, dst in [("x", "z1"), ("w1", "z1"), ("b1", "z1"), ("z1", "a1"),
                 ("a1", "z2"), ("w2", "z2"), ("b2", "z2"), ("z2", "L")]:
    ax.annotate("", xy=pos[dst], xytext=pos[src],
                arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.4, shrinkA=17, shrinkB=17))
# backward で ∂L/∂z2 を w2・a1・b2 の 3 つへ渡す様子（赤い破線の逆向きの矢印）
for dst, rad in [("w2", 0.35), ("a1", -0.35), ("b2", -0.35)]:
    ax.annotate("", xy=pos[dst], xytext=pos["z2"],
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.3, ls="--", shrinkA=17, shrinkB=17,
                                connectionstyle=f"arc3,rad={rad}"))
ax.annotate("", xy=pos["z2"], xytext=pos["L"],
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.3, ls="--", shrinkA=17, shrinkB=17,
                            connectionstyle="arc3,rad=0.35"))
ax.text(9.0, 1.3, "∂L/∂z2 = -1 を\nw2・b2・a1 の 3 つで使い回す", ha="left", va="center",
        fontsize=10, color=RED)
ax.text(5.5, 6.05, "forward（青）: 値を左から右へ計算する", ha="center", fontsize=11, color=BLUE)
ax.text(5.5, -0.05, "backward（赤）: ∂L/∂(各ノード) を右から左へ、連鎖律で求める",
        ha="center", fontsize=11, color=RED)
ax.set_xlim(-0.2, 11.4)
ax.set_ylim(-0.3, 6.4)
ax.set_aspect("equal")
ax.axis("off")
save(fig, "bp_tiny_network.webp")


# ---- 実験 2: digits を 3 層の NN で学習し、backward の 1 行を消した版と比べる ----
X, y_all = load_digits(return_X_y=True)
X_tr, X_te, y_tr, y_te = train_test_split(X, y_all, test_size=0.3, random_state=0, stratify=y_all)
scaler = StandardScaler().fit(X_tr)
X_tr, X_te = scaler.transform(X_tr), scaler.transform(X_te)

ACTS = {  # 活性化関数と、その微分（h は活性化した後の値）
    "sigmoid": (lambda z: 1 / (1 + np.exp(-z)), lambda z, h: h * (1 - h)),
    "relu": (lambda z: np.maximum(z, 0), lambda z, h: (z > 0).astype(float)),
}


def init(act, n_layers, rng, width=64):
    dims = [64] + [width] * (n_layers - 1) + [10]  # 入力 64 画素、出力 10 クラス
    # sigmoid は標準偏差 1/√n、ReLU は He の初期化の √(2/n)
    std = (lambda n: np.sqrt(2 / n)) if act == "relu" else (lambda n: 1 / np.sqrt(n))
    Ws = [rng.normal(0, std(dims[i]), (dims[i], dims[i + 1])) for i in range(n_layers)]
    bs = [np.zeros(dims[i + 1]) for i in range(n_layers)]
    return Ws, bs


def forward(Ws, bs, x, act):
    f, _ = ACTS[act]
    hs, zs = [x], []  # 各層の入力 h と、活性化する前の z を残す
    for i, (W, b) in enumerate(zip(Ws, bs)):
        zs.append(hs[-1] @ W + b)
        if i < len(Ws) - 1:
            hs.append(f(zs[-1]))  # 最後の層は活性化せず、softmax に渡す
    return hs, zs


def softmax(z):
    e = np.exp(z - z.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def loss_only(Ws, bs, x, y, act):
    p = softmax(forward(Ws, bs, x, act)[1][-1])
    return -np.log(p[np.arange(len(y)), y]).mean()  # 交差エントロピー


def loss_and_grads(Ws, bs, x, y, act, bug=False):
    _, df = ACTS[act]
    hs, zs = forward(Ws, bs, x, act)
    p = softmax(zs[-1])
    loss = -np.log(p[np.arange(len(y)), y]).mean()  # 交差エントロピー
    g = p.copy()
    g[np.arange(len(y)), y] -= 1
    g /= len(y)  # ∂L/∂z（最後の層）
    gWs, gbs = [None] * len(Ws), [None] * len(Ws)
    for i in reversed(range(len(Ws))):
        if i < len(Ws) - 1 and not bug:
            g = g * df(zs[i], hs[i + 1])  # 活性化関数の微分を掛ける（bug=True はこの 1 行を飛ばす）
        gWs[i] = hs[i].T @ g  # ∂L/∂W_i
        gbs[i] = g.sum(axis=0)  # ∂L/∂b_i
        g = g @ Ws[i].T  # 1 つ入力側の層へ渡す
    return loss, gWs, gbs


def accuracy(Ws, bs, x, y, act):
    return (forward(Ws, bs, x, act)[1][-1].argmax(axis=1) == y).mean()


def train(act, n_layers, epochs=100, lr=0.1, seed=0, bug=False):
    rng = np.random.default_rng(seed)
    Ws, bs = init(act, n_layers, rng)
    history = []  # エポックごとの (テストの正解率, 1 層目の勾配の大きさ)
    for _ in range(epochs):
        idx = rng.permutation(len(X_tr))
        for s in range(0, len(X_tr), 32):  # 32 件ずつのミニバッチで SGD
            b = idx[s:s + 32]
            _, gWs, gbs = loss_and_grads(Ws, bs, X_tr[b], y_tr[b], act, bug)
            for i in range(n_layers):
                Ws[i] -= lr * gWs[i]
                bs[i] -= lr * gbs[i]
        g1 = loss_and_grads(Ws, bs, X_tr, y_tr, act)[1][0]
        history.append((accuracy(Ws, bs, X_te, y_te, act), np.linalg.norm(g1)))
    return np.array(history)


runs = {}
for bug in [False, True]:
    accs = []
    for seed in range(5):
        h = train("sigmoid", n_layers=3, seed=seed, bug=bug)
        accs.append(h[-1, 0])
        if seed == 0:
            runs[bug] = h  # 冒頭の図に描いた seed 0 の学習曲線
    label = "微分を掛け忘れた backward" if bug else "正しい backward"
    print(f"{label}: テストの正解率 seed 0 {accs[0]:.3f}、seed 0〜4 {min(accs):.3f}〜{max(accs):.3f}")

fig, ax = plt.subplots(figsize=(7.2, 3.8))
ep = np.arange(1, 101)
ax.plot(ep, runs[False][:, 0], color=BLUE, lw=2, label=f"正しい backward（{runs[False][-1, 0]:.1%}）")
ax.plot(ep, runs[True][:, 0], color=RED, lw=2, ls="--",
        label=f"活性化関数の微分を掛け忘れた backward（{runs[True][-1, 0]:.1%}）")
ax.set_xlabel("エポック")
ax.set_ylabel("テストの正解率")
ax.set_ylim(0.8, 1.0)
ax.set_title("digits を 3 層の NN で学習した時のテストの正解率", fontsize=11)
ax.legend(loc="lower right", frameon=False)
ax.grid(True, alpha=0.25)
save(fig, "bp_cover.webp")


# ---- 実験 3: 勾配の照合（数値微分と backward を比べる） ----
rng = np.random.default_rng(0)
Ws, bs = init("sigmoid", 3, rng)
xb, yb = X_tr[:32], y_tr[:32]


def numeric_grad(W, eps=1e-5):
    num = np.zeros_like(W)
    for idx in np.ndindex(W.shape):  # 1 要素ずつ ±eps 動かして損失を 2 回測る
        old = W[idx]
        W[idx] = old + eps
        lp = loss_only(Ws, bs, xb, yb, "sigmoid")
        W[idx] = old - eps
        lm = loss_only(Ws, bs, xb, yb, "sigmoid")
        W[idx] = old
        num[idx] = (lp - lm) / (2 * eps)
    return num


num_W1 = numeric_grad(Ws[0])
check = {}
for bug in [False, True]:
    g = loss_and_grads(Ws, bs, xb, yb, "sigmoid", bug)[1][0]
    rel = np.linalg.norm(g - num_W1) / (np.linalg.norm(g) + np.linalg.norm(num_W1))
    cos = (g * num_W1).sum() / (np.linalg.norm(g) * np.linalg.norm(num_W1))
    check[bug] = (g, rel)
    label = "微分を掛け忘れた backward" if bug else "正しい backward"
    ratio = np.linalg.norm(g) / np.linalg.norm(num_W1)
    print(f"{label}: 相対誤差 {rel:.1e}、コサイン類似度 {cos:.3f}、大きさの比 {ratio:.1f}")

fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.9))
lim = np.abs(num_W1).max() * 1.1
for ax, bug, color, title in [(axes[0], False, BLUE, "正しい backward"),
                              (axes[1], True, RED, "活性化関数の微分を掛け忘れた backward")]:
    g, rel = check[bug]
    ylim = np.abs(g).max() * 1.1
    ax.plot([-lim, lim], [-lim, lim], color=GRAY, lw=1, ls=":", label="数値微分と一致する線")
    ax.scatter(num_W1.ravel(), g.ravel(), s=5, color=color, alpha=0.5)
    ax.set_title(f"{title}\n相対誤差 {rel:.1e}", fontsize=10)
    ax.set_xlabel("数値微分で求めた勾配")
    ax.set_xlim(-lim, lim)
    ax.set_xticks([-0.005, 0, 0.005])
    ax.set_ylim(-ylim, ylim)
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("backward で求めた勾配")
axes[0].legend(loc="upper left", frameon=False, fontsize=9)
save(fig, "bp_gradcheck.webp")

# ---- 補助の図: 正しい勾配と 90 度未満の向きなら、小さく進めば損失は下がる ----
fig, ax = plt.subplots(figsize=(6.4, 4.2))
w1g, w2g = np.meshgrid(np.linspace(-2.2, 2.2, 200), np.linspace(-1.6, 1.6, 200))
ax.contour(w1g, w2g, w1g ** 2 + 3 * w2g ** 2, levels=8, colors=GRAY, linewidths=0.7)
P = np.array([1.5, 0.6])
grad = np.array([2 * P[0], 6 * P[1]])
d = -grad / np.linalg.norm(grad) * 1.0


def rot(v, deg):
    t = np.deg2rad(deg)
    return np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]]) @ v


tangent = rot(d, 90)
ax.plot([P[0] - 1.4 * tangent[0], P[0] + 1.4 * tangent[0]],
        [P[1] - 1.4 * tangent[1], P[1] + 1.4 * tangent[1]], color=INK, ls=":", lw=1)
for v, color, label in [(d, BLUE, "正しい勾配の逆向き"), (rot(d, -17), RED, "間違えた勾配の逆向き（約 17 度ずれ）"),
                        (rot(d, 135), GRAY, "90 度を超えてずれた向き")]:
    ax.annotate("", xy=P + v, xytext=P, arrowprops=dict(arrowstyle="-|>", color=color, lw=2))
    ax.plot([], [], color=color, lw=2, label=label)
ax.plot([], [], color=INK, ls=":", lw=1, label="損失が変わらない向き（等高線の接線）")
ax.scatter([0], [0], color=INK, s=15)
ax.text(0.05, -0.15, "損失が最小の点", fontsize=9)
ax.scatter([P[0]], [P[1]], color=INK, s=15)
ax.set_aspect("equal")
ax.set_xlim(-2.2, 2.6)
ax.set_ylim(-1.6, 1.6)
ax.set_xlabel("重み 1")
ax.set_ylabel("重み 2")
ax.set_title("損失の等高線と、更新に使う向き", fontsize=10.5)
ax.legend(loc="upper left", fontsize=8.5, frameon=True, framealpha=0.9)
save(fig, "bp_descent.webp")


# ---- 実験 4: 数値微分と backward の速さ ----
n_params = sum(W.size + b.size for W, b in zip(Ws, bs))
t = time.perf_counter()
for _ in range(1000):
    loss_and_grads(Ws, bs, xb, yb, "sigmoid")
t_backprop = (time.perf_counter() - t) / 1000
t = time.perf_counter()
for W, b in zip(Ws, bs):
    numeric_grad(W)
    numeric_grad(b)
t_numeric = time.perf_counter() - t
print(f"パラメータ {n_params} 個: forward と backward {t_backprop * 1e3:.3f} ms、"
      f"数値微分 {t_numeric:.2f} s（損失の計算 {2 * n_params} 回）、{t_numeric / t_backprop:,.0f} 倍")

fig, ax = plt.subplots(figsize=(7.2, 2.2))
vals = [t_backprop * 1e3, t_numeric * 1e3]
ax.barh([1, 0], vals, color=[BLUE, GRAY], height=0.55)
ax.set_xscale("log")
ax.set_yticks([1, 0], ["forward と backward 1 回ずつ", f"数値微分（損失を {2 * n_params:,} 回計算）"])
for yy, v in zip([1, 0], vals):
    ax.text(v * 1.15, yy, f"{v:,.0f} ms" if v >= 100 else f"{v:.3g} ms", va="center", fontsize=9.5)
ax.set_xlim(0.03, vals[1] * 20)
ax.set_xlabel("全パラメータの勾配を 1 回求める時間（ms、対数の軸）")
ax.set_title(f"パラメータ {n_params:,} 個の 3 層の NN、32 件のミニバッチ", fontsize=10.5)
save(fig, "bp_cost.webp")


# ---- 実験 5: 層を深くした時の、層ごとの勾配と学習曲線 ----
for act in ["sigmoid", "relu"]:
    Ws10, bs10 = init(act, 10, np.random.default_rng(0))
    norms = np.array([np.linalg.norm(gW) for gW in loss_and_grads(Ws10, bs10, X_tr, y_tr, act)[1]])
    print(f"{act} 10 層、初期化の直後: 1 層目の勾配は 10 層目の {norms[0] / norms[-1]:.1e} 倍")
    if act == "sigmoid":
        sig_norms = norms
    else:
        relu_norms = norms

fig, ax = plt.subplots(figsize=(7.2, 3.8))
layers = np.arange(1, 11)
ax.plot(layers, sig_norms / sig_norms[-1], marker="o", color=RED, lw=1.8,
        label="sigmoid（標準偏差 1/√n で初期化）")
ax.plot(layers, relu_norms / relu_norms[-1], marker="^", color=BLUE, lw=1.8,
        label="ReLU（He の初期化）")
ax.set_yscale("log")
ax.set_xticks(layers)
ax.set_xlabel("層の番号（1 が入力側、10 が出力側）")
ax.set_ylabel("10 層目の勾配に対する比")
ax.set_title("10 層の NN の初期化の直後に、各層の重みに届く勾配の大きさ", fontsize=10.5)
ax.legend(frameon=False)
ax.grid(True, alpha=0.25)
save(fig, "bp_layer_grad.webp")

curves = {}
for depth in [4, 6, 8, 10]:
    h = train("sigmoid", n_layers=depth, epochs=600)
    curves[f"sigmoid {depth} 層"] = h
    print(f"sigmoid {depth} 層: 100 エポック {h[99, 0]:.3f}、300 エポック {h[299, 0]:.3f}、"
          f"600 エポック {h[-1, 0]:.3f}")
h = train("relu", n_layers=10, epochs=600)
curves["ReLU 10 層"] = h
print(f"ReLU 10 層: 100 エポック {h[99, 0]:.3f}、600 エポック {h[-1, 0]:.3f}")

fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
ep = np.arange(1, 601)
styles = {"sigmoid 4 層": (GREEN, "-"), "sigmoid 6 層": (ORANGE, "-"),
          "sigmoid 8 層": (PURPLE, "-"), "sigmoid 10 層": (RED, "-"), "ReLU 10 層": (BLUE, "--")}
for name, h in curves.items():
    color, ls = styles[name]
    axes[0].plot(ep, h[:, 0], color=color, ls=ls, lw=1.6, label=name)
    axes[1].plot(ep, h[:, 1], color=color, ls=ls, lw=1.6, label=name)
axes[0].set_ylabel("テストの正解率")
axes[0].set_title("テストの正解率", fontsize=10.5)
axes[1].set_yscale("log")
axes[1].set_title("1 層目の重みに届く勾配の大きさ", fontsize=10.5)
for ax in axes:
    ax.set_xlabel("エポック")
    ax.grid(True, alpha=0.25)
axes[0].legend(frameon=False, fontsize=9)
save(fig, "bp_depth.webp")
