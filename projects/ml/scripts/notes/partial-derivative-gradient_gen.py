"""partial-derivative-gradient ノートの実験と図を生成するスクリプト。

本文に載せた実験（2 つの重みの偏微分、向きごとの傾き、ロジスティック回帰の勾配と数値微分、
h を変えた時の誤差、誤差の内訳、float32 の損失と SciPy の check_grad、複素数ステップ、
列の単位と勾配の向き）を同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/partial-derivative-gradient_gen.py
確認した版: NumPy 2.5.4、scikit-learn 1.9.1、SciPy 1.18.1
"""
from decimal import Decimal, getcontext
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.optimize import approx_fprime, check_grad
from sklearn.datasets import load_breast_cancer
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "partial-derivative-gradient"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY, ORANGE = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999", "#f28e2b"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ============================================================
# データと損失: breast_cancer のロジスティック回帰
# ============================================================
data = load_breast_cancer()
X = StandardScaler().fit_transform(data.data)       # 569 行 × 30 列を標準化
X = np.column_stack([X, np.ones(len(X))])            # 31 列目は切片
y = data.target.astype(float)


def loss(w, X=X, y=y):
    z = X @ w
    return np.mean(np.log(1 + np.exp(z)) - y * z)    # 交差エントロピーの平均


def grad(w, X=X, y=y):
    p = 1 / (1 + np.exp(-(X @ w)))                   # 予測した確率
    return X.T @ (p - y) / len(y)


# ============================================================
# 実験 1: 2 つの重みだけのモデルの偏微分
# ============================================================
X2 = X[:, [0, 1]]                                    # mean radius と mean texture
P = np.array([-1.0, 1.5])                            # 偏微分を調べる点
h = 1e-5
d1 = (loss(P + [h, 0], X2) - loss(P - [h, 0], X2)) / (2 * h)
d2 = (loss(P + [0, h], X2) - loss(P - [0, h], X2)) / (2 * h)
print("実験 1: 2 つの重みのモデル")
print(f"  点 P = {P}  損失 {loss(P, X2):.4f}")
print(f"  ∂L/∂w1 = {d1:.4f}   ∂L/∂w2 = {d2:.4f}")
print(f"  式で求めた勾配 = {np.round(grad(P, X2), 4)}")

g1 = np.linspace(-4, 1.5, 221)
g2 = np.linspace(-2, 3.5, 221)
G1, G2 = np.meshgrid(g1, g2)
W = np.stack([G1.ravel(), G2.ravel()], axis=1)
Z = np.mean(np.log1p(np.exp(X2 @ W.T)) - y[:, None] * (X2 @ W.T), axis=0).reshape(G1.shape)
levels = [0.25, 0.3, 0.4, 0.5, 0.7, 1.0, 1.4, 1.9, 2.5, 3.2]

fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.9), gridspec_kw={"width_ratios": [1.15, 1, 1]})
ax = axes[0]
cs = ax.contour(G1, G2, Z, levels=levels, colors=GRAY, linewidths=0.8)
ax.clabel(cs, fontsize=7, fmt="%.2f")
ax.axhline(P[1], color=RED, lw=1.4, ls="--")
ax.axvline(P[0], color=GREEN, lw=1.4, ls="--")
ax.plot(*P, "o", color=INK, ms=6)
ax.text(P[0] + 0.12, P[1] + 0.15, "P", fontsize=10)
BOX = {"facecolor": "white", "edgecolor": "none", "pad": 1.5}
ax.text(-3.9, P[1] + 0.12, "w2 を固定して w1 だけ動かす", color=RED, fontsize=8.5, bbox=BOX)
ax.text(P[0] + 0.12, -1.75, "w1 を固定して\nw2 だけ動かす", color=GREEN, fontsize=8.5, bbox=BOX)
ax.set_xlabel("w1（mean radius の重み）")
ax.set_ylabel("w2（mean texture の重み）")
ax.set_title("損失の等高線", fontsize=10)
ax.set_aspect("equal")
for ax, axis, d, color, xs, label in [
        (axes[1], 0, d1, RED, g1, "w1"), (axes[2], 1, d2, GREEN, g2, "w2")]:
    pts = np.tile(P, (len(xs), 1))
    pts[:, axis] = xs
    ls_ = [loss(p, X2) for p in pts]
    ax.plot(xs, ls_, color=color, lw=2)
    t = np.linspace(P[axis] - 1.2, P[axis] + 1.2, 10)
    ax.plot(t, loss(P, X2) + d * (t - P[axis]), color=INK, lw=1.2, ls=":")
    ax.plot(P[axis], loss(P, X2), "o", color=INK, ms=6)
    ax.set_xlabel(label)
    ax.set_ylabel("損失")
    other = "w2" if axis == 0 else "w1"
    ax.set_title(f"{other} = {P[1 - axis]} で切った断面。P での傾き {d:.3f}", fontsize=10)
    ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "pdg_slices.webp")

# ============================================================
# 実験 2: 向きごとの傾き
# ============================================================
gP = grad(P, X2)
ang = np.radians(np.arange(0, 360, 1.0))
slopes = []
for a in ang:
    u = np.array([np.cos(a), np.sin(a)])             # 長さ 1 の向き
    slopes.append((loss(P + h * u, X2) - loss(P - h * u, X2)) / (2 * h))
slopes = np.array(slopes)
best = np.degrees(ang[np.argmax(slopes)])
print("実験 2: 向きごとの傾き")
print(f"  傾きが最大の向き {best:.0f} 度、その傾き {slopes.max():.4f}")
print(f"  勾配の向き {np.degrees(np.arctan2(gP[1], gP[0])) % 360:.1f} 度、勾配の長さ {np.linalg.norm(gP):.4f}")
print(f"  0 度の傾き {slopes[0]:.4f}、90 度の傾き {slopes[90]:.4f}")

fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw={"width_ratios": [1, 1.25]})
ax = axes[0]
cs = ax.contour(G1, G2, Z, levels=levels, colors=GRAY, linewidths=0.8)
ax.clabel(cs, fontsize=7, fmt="%.2f")
ax.plot(*P, "o", color=INK, ms=6)
scale = 1.6 / np.linalg.norm(gP)
ax.annotate("", xy=P + gP * scale, xytext=P,
            arrowprops={"arrowstyle": "-|>", "color": RED, "lw": 2})
ax.annotate("", xy=P - gP * scale, xytext=P,
            arrowprops={"arrowstyle": "-|>", "color": BLUE, "lw": 2})
ax.text(*(P + gP * scale + [-0.3, 0.2]), "勾配", color=RED, fontsize=9)
ax.text(*(P - gP * scale + [-1.25, -0.35]), "勾配の逆", color=BLUE, fontsize=9,
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})
ax.set_xlabel("w1（mean radius の重み）")
ax.set_ylabel("w2（mean texture の重み）")
ax.set_title("P での勾配は等高線と直交する", fontsize=10)
ax.set_aspect("equal")
ax = axes[1]
deg = np.degrees(ang)
ax.plot(deg, slopes, color=INK, lw=1.8)
ax.axhline(0, color=GRAY, lw=0.8)
ax.axvline(best, color=RED, lw=1.2, ls="--")
ax.plot(best, slopes.max(), "o", color=RED)
ax.text(best + 5, slopes.max() + 0.04, f"{best:.0f} 度で最大 {slopes.max():.3f} = 勾配の長さ", color=RED, fontsize=9)
ax.set_ylim(-0.55, 0.62)
ax.plot([0, 90], [slopes[0], slopes[90]], "s", color=INK, ms=5)
ax.text(6, slopes[0] - 0.13, f"0 度 = ∂L/∂w1\n{slopes[0]:.3f}", fontsize=8.5)
ax.text(97, slopes[90] - 0.02, f"90 度 = ∂L/∂w2\n{slopes[90]:.3f}", fontsize=8.5)
ax.set_xticks(range(0, 361, 45))
ax.set_xlabel("動かす向き（度。0 度が w1 の正の向き）")
ax.set_ylabel("その向きに動かした時の損失の傾き")
ax.set_title("P から 360 通りの向きに動かした時の傾き", fontsize=10)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "pdg_direction.webp")

# ============================================================
# 実験 3: 31 個の重みの勾配を数値微分と比べ、h を変える（表紙）
# ============================================================
rng = np.random.default_rng(0)
w0 = rng.normal(scale=0.1, size=X.shape[1])          # 31 個の重み
g = grad(w0)


def numeric_grad(f, w, h, kind="central"):
    out = np.zeros(len(w))
    for i in range(len(w)):
        e = np.zeros_like(w)
        e[i] = h
        if kind == "forward":
            out[i] = (f(w + e) - f(w)) / h
        else:
            out[i] = (f(w + e) - f(w - e)) / (2 * h)
    return out


def rel_err(a):
    return np.linalg.norm(a - g) / np.linalg.norm(g)


X32, y32, w32 = X.astype(np.float32), y.astype(np.float32), w0.astype(np.float32)
loss32 = lambda w: loss(w, X32, y32)                 # 同じ損失を float32 で計算する

hs = 10.0 ** -np.arange(1, 16.01, 0.25)
curves = {}
for name, f, w, dt in [("前進差分 float64", loss, w0, np.float64), ("中心差分 float64", loss, w0, np.float64),
                       ("前進差分 float32", loss32, w32, np.float32), ("中心差分 float32", loss32, w32, np.float32)]:
    kind = "forward" if name.startswith("前進") else "central"
    curves[name] = np.array([rel_err(numeric_grad(f, w, dt(hh), kind).astype(float)) for hh in hs])

print("実験 3: 勾配の相対誤差（31 個の重み）")
show = [1e-2, 1e-3, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9, 1e-12]
for name, c in curves.items():
    i = np.argmin(c)
    vals = "  ".join(f"h={s:.0e}:{c[np.argmin(np.abs(np.log10(hs) - np.log10(s)))]:.1e}" for s in show)
    print(f"  {name}: 一番小さい誤差 {c[i]:.1e}（h={hs[i]:.0e}）")
    print(f"    {vals}")
for name in ["前進差分 float32", "中心差分 float32"]:
    j = np.argmin(np.abs(np.log10(hs) - np.log10(1.49e-8)))
    print(f"  {name}: h={hs[j]:.2e} の誤差 {curves[name][j]:.1f}、最大 {curves[name].max():.1f}")
# gradcheck と同じ成分ごとの判定 |式 - 数値| <= atol + rtol * |数値| を float32 の中心差分（h=1e-6）に当てる
n6 = numeric_grad(loss32, w32, np.float32(1e-6)).astype(float)
tol6 = 1e-5 + 1e-3 * np.abs(n6)
print(f"  中心差分 float32 h=1e-6: 判定を超えた成分 {(np.abs(g - n6) > tol6).sum()} / {len(g)}、"
      f"ずれと許容の比の最大 {(np.abs(g - n6) / tol6).max():.0f} 倍")

fig, ax = plt.subplots(figsize=(8.6, 4.6))
style = {"前進差分 float64": (BLUE, "-"), "中心差分 float64": (INK, "-"),
         "前進差分 float32": (ORANGE, "--"), "中心差分 float32": (RED, "--")}
for name, c in curves.items():
    color, ls = style[name]
    ax.plot(hs, np.minimum(c, 50), color=color, ls=ls, lw=2, label=name)
    i = np.argmin(c)
    ax.plot(hs[i], c[i], "o", color=color, ms=6)
ax.axvline(1.4901161193847656e-08, color=GRAY, lw=1, ls=":")
ax.text(1.2e-8, 1e-11, "SciPy の check_grad の\n既定の h（1.49e-8）", fontsize=8.5, color=INK)
ax.axhline(1, color=GRAY, lw=0.8)
ax.text(3e-10, 1.6, "誤差 1 = 勾配と同じ大きさの誤差", fontsize=8.5, color=INK)
ax.set_xscale("log")
ax.set_yscale("log")
ax.invert_xaxis()
ax.set_ylim(1e-12, 1e2)
ax.set_xlabel("ずらす幅 h（右へ行くほど小さい）")
ax.set_ylabel("式で求めた勾配との相対誤差")
ax.set_title("breast_cancer のロジスティック回帰、31 個の重みの勾配を数値微分で求めた誤差", fontsize=10)
ax.grid(True, which="major", alpha=0.25)
ax.legend(loc="lower right", fontsize=8.5, frameon=False)
fig.tight_layout()
save(fig, "pdg_cover.webp")

# ============================================================
# 実験 4: 誤差の内訳（1 つの重み、Decimal で 60 桁の計算と比べる）
# ============================================================
getcontext().prec = 60
k = 0                                                # mean radius の重み
Xd = [[Decimal(float(v)) for v in row] for row in X]
yd = [Decimal(float(v)) for v in y]
wd = [Decimal(float(v)) for v in w0]
n = Decimal(len(y))


def loss_dec(i, dh):
    total = Decimal(0)
    for row, t in zip(Xd, yd):
        z = sum(a * b for a, b in zip(row, wd)) + row[i] * dh
        total += (Decimal(1) + z.exp()).ln() - t * z
    return total / n


true_k = Decimal(0)                                  # 60 桁で求めた ∂L/∂w_k
for row, t in zip(Xd, yd):
    z = sum(a * b for a, b in zip(row, wd))
    true_k += (Decimal(1) / (Decimal(1) + (-z).exp()) - t) * row[k]
true_k /= n
hs_d = 10.0 ** -np.arange(1, 15.01, 0.5)
tot, trunc, rnd = [], [], []
for hh in hs_d:
    e = np.zeros_like(w0)
    e[k] = hh
    num64 = (loss(w0 + e) - loss(w0 - e)) / (2 * hh)  # float64 の中心差分
    dh = Decimal(float(hh))
    num_exact = (loss_dec(k, dh) - loss_dec(k, -dh)) / (2 * dh)  # 丸めの無い中心差分
    tot.append(abs(Decimal(num64) - true_k) / abs(true_k))
    trunc.append(abs(num_exact - true_k) / abs(true_k))
    rnd.append(abs(Decimal(num64) - num_exact) / abs(true_k))
tot, trunc, rnd = (np.array([float(v) for v in a]) for a in (tot, trunc, rnd))
print("実験 4: mean radius の重みの誤差の内訳（中心差分、float64）")
for hh, a, b, c in zip(hs_d, tot, trunc, rnd):
    if np.isclose(np.log10(hh) % 1, 0):
        print(f"  h={hh:.0e}  全体 {a:.1e}  打ち切り {b:.1e}  丸め {c:.1e}")
print(f"  損失 L(w) = {loss(w0)!r}")
e = np.zeros_like(w0)
e[k] = 1e-12
print(f"  L(w + 1e-12) = {loss(w0 + e)!r}")
print(f"  L(w - 1e-12) = {loss(w0 - e)!r}")

fig, ax = plt.subplots(figsize=(8.2, 4.3))
ax.plot(hs_d, tot, color=INK, lw=2.2, label="全体の誤差（float64 の中心差分）")
ax.plot(hs_d, trunc, color=BLUE, lw=1.6, ls="--", label="打ち切りの誤差（h が大きいほど増える）")
ax.plot(hs_d, np.maximum(rnd, 1e-17), color=RED, lw=1.6, ls="--", label="丸めの誤差（h が小さいほど増える）")
ax.set_xscale("log")
ax.set_yscale("log")
ax.invert_xaxis()
ax.set_ylim(1e-14, 1)
ax.set_xlabel("ずらす幅 h（右へ行くほど小さい）")
ax.set_ylabel("相対誤差")
ax.set_title("mean radius の重みの偏微分の誤差を 2 つに分けた結果", fontsize=10)
ax.grid(True, which="major", alpha=0.25)
ax.legend(loc="lower right", fontsize=8.5, frameon=False)
fig.tight_layout()
save(fig, "pdg_tradeoff.webp")

# ============================================================
# 実験 5: float32 の損失を SciPy の check_grad に渡す
# ============================================================
f64 = lambda w: loss(w)
f32 = lambda w: float(loss(w.astype(np.float32), X32, y32))
print("実験 5: SciPy の check_grad（既定の epsilon）")
print("  float64 の損失:", check_grad(f64, grad, w0))
print("  float32 の損失:", check_grad(f32, grad, w0))
a32 = approx_fprime(w0, f32)
print("  float32 の損失で求めた数値微分（先頭 5 個）:", a32[:5])
print("  式で求めた勾配（先頭 5 個）              :", g[:5].round(4))
print("  数値微分の値の種類:", sorted(set(a32.round(6).tolist())))
print("  損失 L(w) の float32 の間隔:", np.spacing(np.float32(loss32(w32))))
a32ok = approx_fprime(w0, f32, 1e-3)
print("  epsilon=1e-3 にした時の相対誤差:", rel_err(a32ok))

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharex=True)
lim = [-0.5, 0.5]
for ax, est, title in [(axes[0], a32, "既定の epsilon（1.49e-8）"),
                       (axes[1], a32ok, "epsilon = 1e-3")]:
    ax.plot(lim, lim, color=GRAY, lw=1.2, ls=":", label="数値微分 = 式の勾配となる線（正しい値）")
    ax.plot(g, est, "o", color=RED if est is a32 else BLUE, ms=5, alpha=0.8)
    ax.legend(loc="lower right", fontsize=8.5, frameon=False)
    ax.set_xlabel("式で求めた勾配（31 個の成分）")
    ax.set_ylabel("float32 の損失から求めた数値微分")
    ax.set_title(f"{title}、相対誤差 {rel_err(est):.1e}", fontsize=10)
    ax.grid(True, alpha=0.25)
axes[0].set_yticks([-8, -4, 0, 4, 8])
axes[1].set_ylim(-0.55, 0.55)
fig.tight_layout()
save(fig, "pdg_float32.webp")

# ============================================================
# 実験 6: 複素数ステップ
# ============================================================
def complex_step_grad(f, w, h):
    out = np.zeros(len(w))
    for i in range(len(w)):
        e = np.zeros(len(w), dtype=complex)
        e[i] = 1j * h                                # 虚部の向きにだけ h ずらす
        out[i] = f(w + e).imag / h
    return out


hs_c = 10.0 ** -np.arange(1, 40.01, 0.5)
cs_err = np.array([rel_err(complex_step_grad(loss, w0, hh)) for hh in hs_c])
ctr_err = np.array([rel_err(numeric_grad(loss, w0, hh)) for hh in hs_c])
print("実験 6: 複素数ステップの相対誤差")
for hh in [1e-5, 1e-8, 1e-12, 1e-20, 1e-40]:
    i = np.argmin(np.abs(np.log10(hs_c) - np.log10(hh)))
    print(f"  h={hh:.0e}  複素数ステップ {cs_err[i]:.1e}  中心差分 {ctr_err[i]:.1e}")
print(f"  h=1e-200 の複素数ステップ {rel_err(complex_step_grad(loss, w0, 1e-200)):.1e}")
try:
    np.logaddexp(0, np.array([0.1 + 1e-20j]))
except TypeError as err:
    print("  np.logaddexp に複素数を渡すと:", type(err).__name__)
print("  np.abs(-0.2 + 1e-20j) =", np.abs(-0.2 + 1e-20j), "（虚部が消える）")

fig, ax = plt.subplots(figsize=(8.2, 4.2))
ax.plot(hs_c, np.minimum(ctr_err, 50), color=INK, lw=2, label="中心差分 float64")
ax.plot(hs_c, cs_err, color=GREEN, lw=2, label="複素数ステップ float64")
ax.set_xscale("log")
ax.set_yscale("log")
ax.invert_xaxis()
ax.set_ylim(1e-17, 1e1)
ax.set_xlabel("ずらす幅 h（右へ行くほど小さい）")
ax.set_ylabel("式で求めた勾配との相対誤差")
ax.set_title("中心差分と複素数ステップの誤差（31 個の重み）", fontsize=10)
ax.grid(True, which="major", alpha=0.25)
ax.legend(loc="center right", fontsize=9, frameon=False)
fig.tight_layout()
save(fig, "pdg_complex.webp")

# ============================================================
# 実験 7: 列の単位と勾配の向き
# ============================================================
c = 10.0                                             # mean radius の列を 10 倍する
D = np.diag([c, 1.0])
Pc = P / [c, 1.0]                                    # 同じモデルを表す重み
g_scaled = grad(Pc, X2 @ D)                          # 10 倍した列での勾配
step_back = D @ g_scaled                             # 1 歩を元の列の重みに戻す
print("実験 7: 列の単位と勾配の向き")
print(f"  元の列の勾配 {np.round(gP, 4)}")
print(f"  10 倍した列の勾配 {np.round(g_scaled, 4)}")
cosang = gP @ step_back / np.linalg.norm(gP) / np.linalg.norm(step_back)
print(f"  元の列の重みに戻した 1 歩の向きと、元の勾配の向きの角度 {np.degrees(np.arccos(cosang)):.1f} 度")
print(f"  損失は同じか: {np.isclose(loss(P, X2), loss(Pc, X2 @ D))}")

fig, ax = plt.subplots(figsize=(5.6, 4.6))
cs = ax.contour(G1, G2, Z, levels=levels, colors=GRAY, linewidths=0.8)
ax.clabel(cs, fontsize=7, fmt="%.2f")
ax.plot(*P, "o", color=INK, ms=6)
for vec, color, label, off in [(-gP, BLUE, "元の列での勾配の逆", (-1.0, -0.35)),
                               (-step_back, RED, "mean radius を 10 倍した列での\n勾配の逆（元の重みに戻した）", (0.05, 0.2))]:
    v = vec / np.linalg.norm(vec) * 1.5
    ax.annotate("", xy=P + v, xytext=P, arrowprops={"arrowstyle": "-|>", "color": color, "lw": 2})
    ax.text(*(P + v + off), label, color=color, fontsize=8.5,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})
ax.set_xlabel("w1（mean radius の重み）")
ax.set_ylabel("w2（mean texture の重み）")
ax.set_title(f"同じ点、同じ損失で、勾配の逆の向きが {np.degrees(np.arccos(cosang)):.0f} 度回る", fontsize=10)
ax.set_aspect("equal")
fig.tight_layout()
save(fig, "pdg_units.webp")
