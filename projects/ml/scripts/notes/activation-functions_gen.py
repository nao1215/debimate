"""activation-functions ノートの実験と図を生成するスクリプト。

本文に載せた実験（学習率と 0 しか返さないユニット、活性化関数を外した MLP、関数の形と傾き、
sigmoid の MLP が止まる様子、更新ごとのユニットの様子、学習範囲の外の予測、softmax の二重掛け）を
同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/activation-functions_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、Matplotlib 3.11.2、Pillow 13.0.0
"""
import warnings
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.special import erf
from sklearn.datasets import load_digits, make_circles
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")  # 収束の警告が出ないことは本文の実験で別に数える
NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "activation-functions"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY, ORANGE = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999", "#f28e2b"


def to_image(fig, dpi=200):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def save(fig, name):
    to_image(fig).save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ============================================================
# 実験 1: 学習率を変えた時の、0 しか返さないユニットの数
# ============================================================
X, y = load_digits(return_X_y=True)
X = StandardScaler().fit_transform(X)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)


def dead_units(model, X):
    """隠れ層ごとに、全ての行で出力が 0 のユニットの数を返す。"""
    a, counts = X, []
    for W, b in zip(model.coefs_[:-1], model.intercepts_[:-1]):
        a = np.maximum(a @ W + b, 0)                   # ReLU の隠れ層を自分で計算する
        counts.append(int((a.max(axis=0) == 0).sum()))
    return counts


lrs = [0.001, 0.003, 0.01, 0.03, 0.1, 0.3]
res = {"relu": [], "tanh": [], "dead": [], "epochs": [], "warns": []}
for lr in lrs:
    acc_r, acc_t, dead, epochs, warns = [], [], [], [], []
    for seed in range(5):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            relu = MLPClassifier(hidden_layer_sizes=(64, 64), learning_rate_init=lr,
                                 random_state=seed).fit(X_train, y_train)
        tanh = MLPClassifier(hidden_layer_sizes=(64, 64), activation="tanh",
                             learning_rate_init=lr, random_state=seed).fit(X_train, y_train)
        acc_r.append(relu.score(X_test, y_test))
        acc_t.append(tanh.score(X_test, y_test))
        dead.append(dead_units(relu, X_train))
        epochs.append(relu.n_iter_)
        warns.append(len(caught))
        if seed == 0:
            print(f"lr={lr:<5} ReLU 0 しか返さないユニット（1 層目, 2 層目）{dead[-1]}  "
                  f"正解率 ReLU {acc_r[-1]:.3f}  tanh {acc_t[-1]:.3f}  "
                  f"エポック {relu.n_iter_}  警告 {len(caught)} 件")
    res["relu"].append(acc_r)
    res["tanh"].append(acc_t)
    res["dead"].append([d[1] for d in dead])
    res["epochs"].append(epochs)
    res["warns"].append(warns)
for lr, a_r, a_t, d, ep, wn in zip(lrs, res["relu"], res["tanh"], res["dead"], res["epochs"], res["warns"]):
    print(f"lr={lr:<5} 5 回の 2 層目 {d}  ReLU のエポック {ep}  警告 {sum(wn)} 件")
    print(f"{'':<9}正解率 ReLU {np.round(a_r, 2)}  tanh {np.round(a_t, 2)}")

relu = MLPClassifier(hidden_layer_sizes=(64, 64), learning_rate_init=0.3,
                     random_state=0).fit(X_train, y_train)
h1 = np.maximum(X_train @ relu.coefs_[0] + relu.intercepts_[0], 0)
z2 = h1 @ relu.coefs_[1] + relu.intercepts_[1]          # 2 層目の ReLU に入る前の値
dead = z2.max(axis=0) <= 0
print("1 層目で、0 より大きい値を返す行の割合が一番小さいユニット:", round(float((h1 > 0).mean(axis=0).min()), 2))
print("2 層目で 0 しか返さないユニットの、入る前の値の最大（中央値）:", round(float(np.median(z2[:, dead].max(axis=0))), 1))

fig, axes = plt.subplots(2, 1, figsize=(7, 5.6), sharex=True,
                         gridspec_kw={"height_ratios": [1.1, 1]})
ax = axes[0]
for key, color, label in [("tanh", BLUE, "tanh"), ("relu", RED, "ReLU（既定）")]:
    a = np.array(res[key])
    ax.fill_between(lrs, a.min(1), a.max(1), color=color, alpha=0.2)
    ax.plot(lrs, np.median(a, 1), "o-", color=color, label=label)
ax.set_ylabel("テストの正解率")
ax.set_ylim(0, 1.02)
ax.legend(loc="lower left", frameon=False)
ax.set_title("学習率ごとに 5 回（線は中央値、帯は最小〜最大）",
             fontsize=11, loc="left", color=INK)
ax = axes[1]
d = np.array(res["dead"])
ax.fill_between(lrs, d.min(1), d.max(1), color=RED, alpha=0.2)
ax.plot(lrs, np.median(d, 1), "o-", color=RED)
for lr, v in zip(lrs, np.median(d, 1)):
    ax.text(lr, v + (-10 if v > 50 else 3), f"{v:.0f}", ha="center",
            color=RED, fontsize=9)
ax.axhline(64, color=GRAY, ls=":", lw=1)
ax.text(0.001, 60, "2 層目のユニットは 64 個", color=GRAY, fontsize=9, va="top")
ax.set_ylabel("全ての行で 0 を返す\n2 層目のユニット（個）")
ax.set_ylim(0, 70)
ax.set_xscale("log")
ax.set_xticks(lrs)
ax.set_xticklabels([str(v) for v in lrs])
ax.set_xlabel("learning_rate_init（既定は 0.001）")
save(fig, "af_cover.webp")

# ============================================================
# 実験 2: 活性化関数を外した MLP（identity）と、関数を入れた MLP
# ============================================================
Xc, yc = make_circles(n_samples=400, noise=0.1, factor=0.4, random_state=0)
models = {}
for act in ["identity", "logistic", "tanh", "relu"]:
    models[act] = MLPClassifier(hidden_layer_sizes=(16, 16, 16), activation=act,
                                max_iter=3000, random_state=0).fit(Xc, yc)
    print(f"{act:<8} 訓練データの正解率 {models[act].score(Xc, yc):.3f}  エポック {models[act].n_iter_}")

m = models["identity"]
W, b = m.coefs_[0], m.intercepts_[0]
for W_next, b_next in zip(m.coefs_[1:], m.intercepts_[1:]):
    W, b = W @ W_next, b @ W_next + b_next             # 4 枚の重みを 1 枚にまとめる
z_mlp = Xc @ W + b
z_layers = Xc
for W_i, b_i in zip(m.coefs_, m.intercepts_):
    z_layers = z_layers @ W_i + b_i                    # 層を順に通した値
print("まとめた重み", W.ravel().round(4), "切片", b.round(4))
print("層を順に通した値との差の最大", float(np.abs(z_mlp - z_layers).max()))

xx, yy = np.meshgrid(np.linspace(-1.6, 1.6, 300), np.linspace(-1.6, 1.6, 300))
grid = np.c_[xx.ravel(), yy.ravel()]
fig, axes = plt.subplots(1, 4, figsize=(12, 3.4))
titles = {"identity": "identity（関数なし）", "logistic": "logistic（sigmoid）",
          "tanh": "tanh", "relu": "relu"}
for ax, (act, mdl) in zip(axes, models.items()):
    p = mdl.predict_proba(grid)[:, 1].reshape(xx.shape)
    ax.contourf(xx, yy, p, levels=[0, 0.5, 1], colors=["#dbe7ef", "#f6d5d5"], alpha=0.9)
    ax.contour(xx, yy, p, levels=[0.5], colors=INK, linewidths=1)
    ax.scatter(Xc[yc == 0, 0], Xc[yc == 0, 1], s=6, color="#4e79a7")
    ax.scatter(Xc[yc == 1, 0], Xc[yc == 1, 1], s=6, color=RED)
    ax.set_title(f"{titles[act]}\n正解率 {mdl.score(Xc, yc):.2f}、{mdl.n_iter_} エポックで停止",
                 fontsize=9.5)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
save(fig, "af_circles.webp")

# ============================================================
# 実験 3: 関数の形と傾き
# ============================================================
z = np.linspace(-5, 5, 1001)
sig = 1 / (1 + np.exp(-z))
gelu = 0.5 * z * (1 + erf(z / np.sqrt(2)))
phi = np.exp(-z**2 / 2) / np.sqrt(2 * np.pi)
funcs = {
    "sigmoid": (sig, sig * (1 - sig), BLUE, "-"),
    "tanh": (np.tanh(z), 1 - np.tanh(z) ** 2, GREEN, "-"),
    "ReLU": (np.maximum(z, 0), (z > 0).astype(float), RED, "-"),
    "Leaky ReLU 0.1": (np.where(z > 0, z, 0.1 * z), np.where(z > 0, 1, 0.1), ORANGE, "--"),
    "GELU": (gelu, 0.5 * (1 + erf(z / np.sqrt(2))) + z * phi, INK, ":"),
}
for name, (_, g, _, _) in funcs.items():
    print(f"{name:<16} 傾きの最大 {g.max():.3f}  z=-3 の傾き {g[np.argmin(np.abs(z + 3))]:.3f}")
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
for name, (f, g, color, ls) in funcs.items():
    axes[0].plot(z, f, color=color, ls=ls, lw=1.8, label=name)
    axes[1].plot(z, g, color=color, ls=ls, lw=1.8, label=name)
axes[0].set_ylim(-1.3, 3)
axes[0].set_title("出力", fontsize=10)
axes[1].set_ylim(-0.15, 1.2)
axes[1].set_title("傾き（微分）", fontsize=10)
axes[1].axhline(0.25, color=BLUE, lw=0.8, alpha=0.6)
axes[1].text(4.9, 0.28, "sigmoid の最大 0.25", color=BLUE, fontsize=8.5, ha="right")
for ax in axes:
    ax.axhline(0, color=GRAY, lw=0.6)
    ax.axvline(0, color=GRAY, lw=0.6)
    ax.set_xlabel("入力 z（重み付き和にバイアスを足した値）")
axes[0].legend(frameon=False, fontsize=8.5, loc="upper left")
save(fig, "af_shapes.webp")

# ============================================================
# 実験 4: sigmoid の MLP が止まる様子（既定の停止と、待った時）
# ============================================================
curves = {}
for label, act, patience in [("logistic、既定", "logistic", 10),
                             ("logistic、n_iter_no_change=3000", "logistic", 3000),
                             ("tanh、既定", "tanh", 10), ("relu、既定", "relu", 10)]:
    mdl = MLPClassifier(hidden_layer_sizes=(16, 16, 16), activation=act, max_iter=3000,
                        n_iter_no_change=patience, random_state=0).fit(Xc, yc)
    lc = np.array(mdl.loss_curve_)
    curves[label] = lc
    below = int(np.argmax(lc < 0.6)) + 1 if (lc < 0.6).any() else None
    print(f"停止 {mdl.n_iter_:>4} エポック  正解率 {mdl.score(Xc, yc):.2f}  最初の損失 {lc[0]:.4f}  "
          f"最後の損失 {lc[-1]:.4f}  損失が 0.6 を切った {str(below):>4}  {label}")
print("log(2) =", round(float(np.log(2)), 4))

fig, ax = plt.subplots(figsize=(8, 3.8))
style = {"logistic、既定": (BLUE, "-", 2.6), "logistic、n_iter_no_change=3000": (BLUE, "--", 1.4),
         "tanh、既定": (GREEN, "-", 1.4), "relu、既定": (RED, "-", 1.4)}
for label, lc in curves.items():
    color, ls, lw = style[label]
    ax.plot(np.arange(1, len(lc) + 1), lc, color=color, ls=ls, lw=lw, label=label)
end = curves["logistic、既定"]
ax.plot(len(end), end[-1], "o", color=BLUE, ms=7)
ax.annotate(f"{len(end)} エポックで「収束」として停止", (len(end), end[-1]), (40, 0.95),
            color=BLUE, fontsize=9, arrowprops={"arrowstyle": "->", "color": BLUE})
ax.axhline(np.log(2), color=GRAY, ls=":", lw=1)
ax.text(1.2, np.log(2) + 0.03, "log 2 = 0.693（どの点も確率 0.5 と答える時の損失）", color=GRAY, fontsize=8.5)
ax.set_xscale("log")
ax.set_ylim(0, 1.1)
ax.set_xlabel("エポック（対数）")
ax.set_ylabel("訓練データの損失")
ax.legend(frameon=False, fontsize=8.5, loc="lower left")
save(fig, "af_sigmoid_stall.webp")

# ============================================================
# 実験 5: 更新のたびに、2 層目のユニットが 0 しか返さなくなる様子（動く図）
# ============================================================


def active_ratio(model, X):
    """最後の隠れ層の各ユニットが、0 より大きい値を返す行の割合。"""
    a = X
    for W, b in zip(model.coefs_[:-1], model.intercepts_[:-1]):
        a = np.maximum(a @ W + b, 0)
    return (a > 0).mean(axis=0)


history = {}
for lr in [0.001, 0.3]:
    mdl = MLPClassifier(hidden_layer_sizes=(64, 64), learning_rate_init=lr, random_state=0)
    rng = np.random.default_rng(0)
    frames = []
    for step in range(1, 41):
        idx = rng.choice(len(X_train), 200, replace=False)  # 既定の batch_size と同じ 200 行
        mdl.partial_fit(X_train[idx], y_train[idx], classes=np.arange(10))
        frames.append((active_ratio(mdl, X_train), mdl.score(X_test, y_test)))
    history[lr] = frames
    for step in (1, 5, 10, 20, 40):
        r, acc = frames[step - 1]
        print(f"lr={lr:<5} {step:>2} 回目の更新の後: 0 しか返さないユニット {int((r == 0).sum()):>2} / 64  "
              f"テストの正解率 {acc:.2f}")
    # 赤（全ての行で 0）から青に戻ったマスを、更新ごとに数える
    back = [int(((frames[s - 1][0] == 0) & (frames[s][0] > 0)).sum()) for s in range(1, 40)]
    print(f"lr={lr:<5} 赤から青に戻ったマス: 計 {sum(back)} 回、"
          f"戻った更新 {[s + 2 for s, n in enumerate(back) if n]}、"
          f"11 回目以降 {sum(back[9:])} 回")

anim = []
for i in range(40):
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.3))
    fig.suptitle(f"{i + 1} 回目の更新の後（1 回の更新を 0.25 秒ずつ表示）", fontsize=11, color=INK)
    for ax, lr in zip(axes, [0.001, 0.3]):
        r, acc = history[lr][i]
        img = np.ones((8, 8, 3))
        for k, v in enumerate(r):
            if v == 0:
                img[k // 8, k % 8] = (0.88, 0.34, 0.35)          # 0 しか返さないユニット
            else:
                img[k // 8, k % 8] = 1 - (1 - np.array([0.30, 0.47, 0.65])) * (0.25 + 0.75 * v)
        ax.imshow(img, interpolation="nearest")
        ax.set_xticks(np.arange(-0.5, 8, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, 8, 1), minor=True)
        ax.grid(which="minor", color="white", lw=2)
        ax.tick_params(which="both", length=0, labelbottom=False, labelleft=False)
        for s in ax.spines.values():
            s.set_visible(False)
        dead = int((r == 0).sum())
        ax.set_title(f"learning_rate_init={lr}\n0 しか返さない: {dead} / 64　正解率 {acc:.2f}",
                     fontsize=10, color=RED if dead else INK)
    bar = fig.add_axes([0.13, 0.04, 0.74, 0.025])
    bar.barh(0, i + 1, color=GRAY)
    bar.set_xlim(0, 40)
    bar.set_yticks([])
    bar.set_xticks([0, 10, 20, 30, 40])
    bar.tick_params(labelsize=9.5)
    bar.set_xlabel("更新の回数", fontsize=9.5)
    for s in bar.spines.values():
        s.set_visible(False)
    fig.text(0.5, 0.105, "濃い青ほど多くの行で 0 より大きい値を返す、赤は全ての行で 0",
             ha="center", fontsize=10.5, color=INK)
    anim.append(to_image(fig, dpi=110))
durations = [250] * 39 + [3000]
anim[0].save(NOTE_DIR / "af_dead_steps.webp", "WEBP", save_all=True, append_images=anim[1:],
             duration=durations, loop=0, quality=75, method=6)

# ============================================================
# 実験 6: 学習した範囲の外で返す値
# ============================================================
rng = np.random.default_rng(0)
x = rng.uniform(-2, 2, 300)
t = x**2 + rng.normal(0, 0.05, 300)                     # 正解は y = x^2
x_new = np.array([[-10.0], [-5.0], [-2.0], [0.0], [2.0], [5.0], [10.0]])
regs = {
    "relu": MLPRegressor(hidden_layer_sizes=(64, 64), max_iter=5000, random_state=0),
    "tanh": MLPRegressor(hidden_layer_sizes=(64, 64), activation="tanh", max_iter=5000,
                         random_state=0),
    "ランダムフォレスト": RandomForestRegressor(random_state=0),
}
print(x_new.ravel(), "x")
print(x_new.ravel() ** 2, "正解")
for name, reg in regs.items():
    reg.fit(x[:, None], t)
    print(reg.predict(x_new).round(1), name)

xs = np.linspace(-10, 10, 801)[:, None]
fig, ax = plt.subplots(figsize=(8, 4))
ax.axvspan(-2, 2, color="#eeeeee")
ax.text(0, 30, "学習に使った範囲\n-2 ≦ x ≦ 2", ha="center", fontsize=9, color=INK)
ax.plot(xs, xs**2, color=GRAY, ls=":", lw=1.5, label="正解 y = x²")
for (name, reg), color in zip(regs.items(), [RED, GREEN, BLUE]):
    ax.plot(xs, reg.predict(xs), color=color, lw=1.8, label=name)
ax.scatter(x, t, s=4, color=INK, alpha=0.4)
ax.set_ylim(-3, 40)
ax.set_xlabel("x")
ax.set_ylabel("予測")
ax.legend(frameon=False, fontsize=9, loc="upper right")
save(fig, "af_extrapolate.webp")

# ============================================================
# 実験 7: 出力層で softmax を二重に掛けた時の損失
# ============================================================


def softmax(z):
    e = np.exp(z - z.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


for k in [2, 10, 100]:
    perfect = np.full((1, k), -1e9)
    perfect[0, 0] = 1e9                                 # 正解のクラスにだけ大きい値を返す
    q = softmax(softmax(perfect))
    print(f"{k:>3} クラス: 完全に当てても二重に掛けた損失は {-np.log(q[0, 0]):.3f}"
          f"（式 log(1 + (k - 1) / e) = {np.log(1 + (k - 1) / np.e):.3f}）")

Y = np.eye(10)[y_train]
loss_hist = {}
for double in [False, True]:
    rng = np.random.default_rng(0)
    Wd = rng.normal(0, 0.01, (64, 10))
    bd = np.zeros(10)
    hist = []
    for epoch in range(300):
        z = X_train @ Wd + bd                            # 出力層の値（logits）
        p = softmax(z)
        if double:
            q = softmax(p)                              # 損失の側でもう一度 softmax が掛かる
            g_p = q - Y
            g = p * (g_p - (p * g_p).sum(axis=1, keepdims=True))
        else:
            q = p
            g = p - Y
        hist.append(-np.log(q[np.arange(len(Y)), y_train]).mean())
        Wd -= 0.5 * X_train.T @ g / len(Y)
        bd -= 0.5 * g.mean(axis=0)
    acc = (np.argmax(X_test @ Wd + bd, axis=1) == y_test).mean()
    loss_hist[double] = hist
    print(f"二重に掛ける={double!s:<5} 300 回後の損失 {hist[-1]:.3f}  テストの正解率 {acc:.3f}")

fig, ax = plt.subplots(figsize=(7.5, 3.6))
ax.plot(loss_hist[False], color=BLUE, lw=1.8, label="logits をそのまま損失へ")
ax.plot(loss_hist[True], color=RED, lw=1.8, label="softmax を掛けてから損失へ（二重）")
ax.axhline(np.log(1 + 9 / np.e), color=RED, ls=":", lw=1)
ax.text(300, np.log(1 + 9 / np.e) - 0.12, "二重に掛けた時の下限 1.461（10 クラス）",
        ha="right", color=RED, fontsize=8.5)
ax.set_ylim(0, 2.5)
ax.set_xlabel("更新の回数")
ax.set_ylabel("訓練データの交差エントロピー")
ax.legend(frameon=False, fontsize=9, loc="upper right")
save(fig, "af_double_softmax.webp")
