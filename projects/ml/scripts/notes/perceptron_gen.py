"""perceptron ノートの実験と図を生成するスクリプト。

本文に載せた実験（学習率を変えた Perceptron、更新の動く図、マージンと更新の回数、
scikit-learn の止まり方、乱数ごとのテストの正解率、引く線の比較、分岐予測のシミュレーション、XOR と手で組んだ隠れ層）を
本文と同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/perceptron_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2、Pillow 13.0.0
動く図は 1 回の更新を 1 秒ずつ表示し、最後のコマで 3 秒止める。
"""
import contextlib
import io
import re
import warnings
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import load_breast_cancer
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression, Perceptron, SGDClassifier
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

warnings.simplefilter("ignore", ConvergenceWarning)

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "perceptron"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY, LIGHT = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999", "#dddddd"


def to_image(fig, dpi=200):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ============================================================
# データ: breast_cancer を学習 426 行・テスト 143 行に分けて標準化する
# ============================================================
X, y = load_breast_cancer(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0, stratify=y)
scaler = StandardScaler().fit(X_train)
X_train, X_test = scaler.transform(X_train), scaler.transform(X_test)
print(f"学習 {len(X_train)} 行、テスト {len(X_test)} 行、列 {X_train.shape[1]}")

# ============================================================
# 実験 1（表紙）: 学習率 eta0 を 1e-6 から 1e6 まで変える
# ============================================================
print("\n# 実験 1: eta0 を変える（tol=None で 50 エポック）")
etas = [1e-6, 1e-4, 1e-2, 1.0, 1e2, 1e4, 1e6]
preds, norms = [], []
for eta in etas:
    clf = Perceptron(eta0=eta, tol=None, max_iter=50, random_state=0).fit(X_train, y_train)
    pred = clf.predict(X_test)
    preds.append(pred)
    norms.append(np.linalg.norm(clf.coef_))
    print(f"eta0={eta:<8g} 重みの長さ {norms[-1]:.3e}  テストの正解率 {clf.score(X_test, y_test):.3f}"
          f"  eta0=1e-6 と予測が違う行 {(pred != preds[0]).sum()}")

# 初期の重みが 0 でなければ、学習率で予測が変わる
print("\n# 実験 1 の補足: coef_init で初期の重みを 0 以外にする")
w0 = np.random.default_rng(1).normal(size=(1, X_train.shape[1]))
base = None
for eta in [1e-2, 1.0, 1e2]:
    clf = Perceptron(eta0=eta, tol=None, max_iter=50, random_state=0)
    clf.fit(X_train, y_train, coef_init=w0, intercept_init=np.zeros(1))
    pred = clf.predict(X_test)
    base = pred if base is None else base
    print(f"eta0={eta:<5g} テストの正解率 {clf.score(X_test, y_test):.3f}  eta0=0.01 と予測が違う行 {(pred != base).sum()}")

fig, (ax, axn) = plt.subplots(1, 2, figsize=(10, 3.6), gridspec_kw={"width_ratios": [3.2, 1]}, sharey=True)
img = np.array(preds)                  # テストの元の順のまま並べる
ax.imshow(img, aspect="auto", cmap=plt.matplotlib.colors.ListedColormap([RED, BLUE]),
          extent=[0, len(y_test), len(etas) - 0.5, -0.5])
ax.set_yticks(range(len(etas)), [f"eta0 = {e:g}" for e in etas])
ax.set_xlabel("テストの 143 行（元の順）")
ax.set_title("テストの各行の予測（赤 = 悪性、青 = 良性）", loc="left", fontsize=10)
for i in range(1, len(etas)):
    ax.axhline(i - 0.5, color="#ffffff", lw=2)
axn.barh(range(len(etas)), norms, color=GRAY, height=0.6)
axn.set_xscale("log")
axn.set_xlim(1e-6, 1e9)
for i, v in enumerate(norms):
    axn.text(v * 1.6, i, f"{v:.0e}", va="center", fontsize=8.5, color=INK)
axn.set_title("重みの長さ ||coef_||", loc="left", fontsize=10)
axn.set_xticks([1e-5, 1e0, 1e5])
fig.suptitle("正則化なしで止める仕組みを切り 50 エポック回すと、eta0 を 12 桁変えてもテストの予測は同じ（penalty=None、tol=None）", x=0.01, ha="left", fontsize=11.5)
fig.tight_layout()
save(fig, "pc_cover.webp")

# ============================================================
# 実験 2: 2 次元のデータで、更新のたびに線が動く様子（動く図）
# ============================================================
print("\n# 実験 2: 2 次元のデータで更新を追う")


def train_trace(X2, t, max_epochs=100):
    Xa = np.c_[X2, np.ones(len(X2))]       # 3 列目は切片の分の 1
    w = np.zeros(3)
    trace = []
    for epoch in range(1, max_epochs + 1):
        mistakes = 0
        for i in range(len(Xa)):
            if t[i] * (Xa[i] @ w) <= 0:     # 予測の符号が正解と違う（0 も誤りとする）
                trace.append((epoch, i, w.copy()))
                w = w + t[i] * Xa[i]        # 正解が +1 なら足し、-1 なら引く
                mistakes += 1
        if mistakes == 0:
            return w, trace, epoch


for seed in range(100):
    r = np.random.default_rng(seed)
    P = r.uniform(-1, 1, (80, 2))
    d = P[:, 1] - (0.6 * P[:, 0] + 0.35)
    keep = np.abs(d) > 0.12
    X2, t2 = P[keep][:16], np.where(d[keep][:16] > 0, 1, -1)
    w_end, trace, n_epoch = train_trace(X2, t2)
    if 8 <= len(trace) <= 11:
        break
print(f"seed={seed} 点 {len(X2)} 個、更新 {len(trace)} 回、エポック {n_epoch}")
for epoch, i, w in trace:
    print(f"エポック {epoch} 点 {i:2d} を誤り（正解 {t2[i]:+d}）  更新前の w={np.round(w, 2)}")
print("最後の w:", np.round(w_end, 2))

xs = np.linspace(-1.2, 1.2, 50)


def draw_frame(w, k, total, epoch, idx, note):
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    if np.abs(w[:2]).sum() > 0:
        gx, gy = np.meshgrid(np.linspace(-1.2, 1.2, 241), np.linspace(-1.2, 1.2, 241))
        side = w[0] * gx + w[1] * gy + w[2] > 0
        ax.contourf(gx, gy, side, levels=[-0.5, 0.5, 1.5], colors=["#f6dcdc", "#dce9f2"])
        if abs(w[1]) > 1e-9:
            ax.plot(xs, -(w[0] * xs + w[2]) / w[1], color=INK, lw=2)
        else:
            ax.axvline(-w[2] / w[0], color=INK, lw=2)
    ax.scatter(*X2[t2 > 0].T, s=46, color=BLUE, label="正解 +1（青い側に来れば正しい）", zorder=3)
    ax.scatter(*X2[t2 < 0].T, s=46, color=RED, marker="s", label="正解 -1（赤い側に来れば正しい）", zorder=3)
    if idx is not None:
        ax.scatter(*X2[idx], s=320, facecolors="none", edgecolors=INK, lw=2, zorder=4)
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right", fontsize=8.5)
    fig.suptitle("パーセプトロンの更新（1 回の更新を 1 秒ずつ表示）", x=0.03, ha="left", fontsize=11)
    ax.set_title(f"更新 {k} / {total} 回　エポック {epoch}　{note}", loc="left", fontsize=10)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.86, bottom=0.08)
    return to_image(fig, dpi=110)


frames, durations = [], []
frames.append(draw_frame(np.zeros(3), 0, len(trace), 1, None, "w = 0 で線はまだ無い"))
durations.append(1000)
for k, (epoch, i, w) in enumerate(trace, start=1):
    frames.append(draw_frame(w, k - 1, len(trace), epoch, i, f"囲んだ点を誤った（正解 {t2[i]:+d}）"))
    durations.append(500)
    w_new = trace[k][2] if k < len(trace) else w_end
    frames.append(draw_frame(w_new, k, len(trace), epoch, i, "w に x を足した" if t2[i] > 0 else "w から x を引いた"))
    durations.append(500)
frames.append(draw_frame(w_end, len(trace), len(trace), n_epoch, None, f"エポック {n_epoch} で誤り 0、停止"))
durations.append(3000)
frames[0].save(NOTE_DIR / "pc_updates.webp", "WEBP", save_all=True, append_images=frames[1:],
               duration=durations, loop=0, quality=80, method=6)
print(f"動く図: {len(frames)} コマ、{sum(durations) / 1000:.1f} 秒、"
      f"{(NOTE_DIR / 'pc_updates.webp').stat().st_size // 1024} KB")

# 上限の式に出る R と γ を、上記の 16 点で描く（2 次元のまま測る模式。本文の上限は切片の 1 を足した x で測る）
svm16 = SVC(kernel="linear", C=1e8).fit(X2, t2)
w16, b16 = svm16.coef_[0], svm16.intercept_[0]
dist16 = t2 * (X2 @ w16 + b16) / np.linalg.norm(w16)
i_near, i_far = int(np.argmin(dist16)), int(np.argmax(np.linalg.norm(X2, axis=1)))
print(f"16 点の R と γ（2 次元で測る）: γ={dist16[i_near]:.3f}（点 {i_near}）、R={np.linalg.norm(X2[i_far]):.3f}（点 {i_far}）")
fig, ax = plt.subplots(figsize=(5.6, 5.0))
n16 = w16 / np.linalg.norm(w16)
for off, ls in [(0, "-"), (dist16[i_near], ":"), (-dist16[i_near], ":")]:
    ax.plot(xs, -(w16[0] * xs + b16 - off * np.linalg.norm(w16)) / w16[1], color=GREEN if off == 0 else GRAY, lw=2 if off == 0 else 1, ls=ls)
ax.scatter(*X2[t2 > 0].T, s=46, color=BLUE, label="正解 +1", zorder=3)
ax.scatter(*X2[t2 < 0].T, s=46, color=RED, marker="s", label="正解 -1", zorder=3)
foot = X2[i_near] - t2[i_near] * dist16[i_near] * n16
ax.annotate("", xy=foot, xytext=X2[i_near], arrowprops=dict(arrowstyle="<->", color=INK, lw=1.5))
ax.text(*(X2[i_near] + foot) / 2 + np.array([-0.08, 0.0]), f"γ = {dist16[i_near]:.2f}", fontsize=10, color=INK, ha="right", va="center")
ax.annotate("", xy=X2[i_far], xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.5))
ax.plot([0], [0], "o", color=INK, ms=4)
ax.text(*(X2[i_far] * 0.7 + np.array([-0.02, -0.12])), f"R = {np.linalg.norm(X2[i_far]):.2f}", fontsize=10, color=INK, ha="right")
ax.text(0.03, 0.03, "緑の実線: マージンが最大の線\n点線: 線から γ の幅", transform=ax.transAxes, fontsize=8.5, color=INK)
ax.set_xlim(-1.2, 1.2)
ax.set_ylim(-1.2, 1.2)
ax.set_aspect("equal")
ax.grid(True, alpha=0.25)
ax.legend(loc="upper right", fontsize=8.5)
ax.set_title("16 点で見た R と γ（原点 (0, 0) から測る）", loc="left", fontsize=10)
save(fig, "pc_gamma.webp")

# ============================================================
# 実験 3: マージンと、誤り 0 になるまでの更新の回数
# ============================================================
print("\n# 実験 3: マージンを狭めて更新の回数を数える")


def count_updates(Xa, t, rng=None, max_epochs=100000):
    w = np.zeros(Xa.shape[1])
    n = 0
    for epoch in range(1, max_epochs + 1):
        mistakes = 0
        idx = rng.permutation(len(Xa)) if rng is not None else range(len(Xa))
        for i in idx:
            if t[i] * (Xa[i] @ w) <= 0:
                w = w + t[i] * Xa[i]
                n += 1
                mistakes += 1
        if mistakes == 0:
            return n, epoch


gaps = [0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002]
med_upd, max_upd, bounds = [], [], []
u = np.array([np.cos(0.6), np.sin(0.6)])
for gap in gaps:
    ups, bs = [], []
    for s in range(20):
        r = np.random.default_rng(s)
        P = r.uniform(-1, 1, (4000, 2))
        d = P @ u - 0.2
        keep = np.abs(d) > gap                      # 線から gap 以内の点を捨ててマージンを作る
        Xa = np.c_[P[keep][:200], np.ones(200)]
        t = np.sign(d[keep][:200])
        w_star = np.r_[u, -0.2]
        gamma = (t * (Xa @ w_star)).min() / np.linalg.norm(w_star)
        R = np.linalg.norm(Xa, axis=1).max()
        ups.append(count_updates(Xa, t, r)[0])
        bs.append((R / gamma) ** 2)
    med_upd.append(np.median(ups))
    max_upd.append(max(ups))
    bounds.append(np.median(bs))
    print(f"gap={gap:<6g} 更新の回数 中央値 {np.median(ups):6.1f} 最大 {max(ups):4d}  上限 (R/γ)^2 の中央値 {np.median(bs):9.0f}")

y_pm = np.where(y_train == 1, 1, -1)
Xa_bc = np.c_[X_train, np.ones(len(X_train))]
svm_hard = SVC(kernel="linear", C=1e8).fit(X_train, y_train)
w_svm = np.r_[svm_hard.coef_[0], svm_hard.intercept_[0]]
gamma_bc = (y_pm * (Xa_bc @ w_svm)).min() / np.linalg.norm(w_svm)
R_bc = np.linalg.norm(Xa_bc, axis=1).max()
n_bc, ep_bc = count_updates(Xa_bc, y_pm)
print(f"breast_cancer: 学習データの正解率（線形 SVM、C=1e8）{svm_hard.score(X_train, y_train):.3f}")
print(f"breast_cancer: γ={gamma_bc:.4f} R={R_bc:.2f} 上限 {(R_bc / gamma_bc) ** 2:.0f}、実際 {n_bc} 回（{ep_bc} エポック）")

fig, ax = plt.subplots(figsize=(7.2, 4.2))
ax.loglog(gaps, bounds, "o--", color=GRAY, label="上限 (R/γ)²（点を作った線で測る、20 回の中央値）")
ax.loglog(gaps, max_upd, "s-", color=RED, ms=5, label="実際に更新した回数（20 回の最大）")
ax.loglog(gaps, med_upd, "o-", color=BLUE, label="実際に更新した回数（20 回の中央値）")
for g, v in zip(gaps, bounds):
    ax.annotate(f"{v:,.0f}", (g, v), textcoords="offset points", xytext=(4, 6), fontsize=8, color=INK)
for g, v in zip(gaps, med_upd):
    ax.annotate(f"{v:.0f}", (g, v), textcoords="offset points", xytext=(4, -13), fontsize=8, color=INK)
ax.invert_xaxis()
ax.set_xlabel("線から点を捨てた幅（右ほどマージンが狭い）")
ax.set_ylabel("誤り 0 になるまでの更新の回数")
ax.grid(True, which="major", alpha=0.25)
ax.legend(fontsize=9, loc="upper left")
ax.set_title("2 次元の 200 点で、マージンを狭めた時の更新の回数", loc="left", fontsize=10)
save(fig, "pc_margin.webp")

# ============================================================
# 実験 4: scikit-learn の Perceptron が止まる所
# ============================================================
print("\n# 実験 4: 既定の tol=1e-3 で eta0 を変える")
base = None
for eta in etas:
    clf = Perceptron(eta0=eta, random_state=0).fit(X_train, y_train)
    pred = clf.predict(X_test)
    base = pred if base is None else base
    print(f"eta0={eta:<8g} n_iter_={clf.n_iter_:2d}  学習データの正解率 {clf.score(X_train, y_train):.3f}"
          f"  テストの正解率 {clf.score(X_test, y_test):.3f}  eta0=1e-6 と予測が違う行 {(pred != base).sum()}")

default = Perceptron(random_state=0).fit(X_train, y_train)
train_err, test_acc = [], []
first_zero = None
for k in range(1, 401):
    clf = Perceptron(tol=None, max_iter=k, random_state=0).fit(X_train, y_train)
    train_err.append(int((clf.predict(X_train) != y_train).sum()))
    test_acc.append(clf.score(X_test, y_test))
    if first_zero is None and train_err[-1] == 0:
        first_zero = k
print(f"既定の Perceptron: n_iter_={default.n_iter_}、学習データの誤り {train_err[default.n_iter_ - 1]} 行")
print(f"学習データの誤りが初めて 0 になったエポック: {first_zero}、その時のテストの正解率 {test_acc[first_zero - 1]:.3f}")

# 止める判定に使う損失の平均は、verbose=1 の出力の「Avg. loss」で読める
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    Perceptron(tol=None, max_iter=20, random_state=0, verbose=1).fit(X_train, y_train)
losses = [float(v) for v in re.findall(r"Avg\. loss: ([0-9.e+-]+)", buf.getvalue())]
best_ep = int(np.argmin(losses[:default.n_iter_])) + 1
print("エポックごとの損失の平均（1〜20）:", [round(v, 3) for v in losses])
print(f"既定で止まるまでの最小: エポック {best_ep} の {losses[best_ep - 1]:.3f}")

fig, (axl, ax) = plt.subplots(2, 1, figsize=(8.2, 6.4), gridspec_kw={"height_ratios": [1, 1.1]})
el = np.arange(1, len(losses) + 1)
axl.axvspan(best_ep + 0.5, default.n_iter_ + 0.5, color="#f6dcdc")
axl.plot(el, losses, "o-", color=BLUE, ms=4, lw=1.2)
axl.axhline(losses[best_ep - 1], color=RED, lw=1, ls="--")
axl.text(default.n_iter_ + 0.7, losses[best_ep - 1] - 0.012,
         f"エポック {best_ep} の最小 {losses[best_ep - 1]:.3f}", color=RED, fontsize=8.5, va="top")
axl.text((best_ep + default.n_iter_) / 2 + 0.5, max(losses) * 1.12,
         f"最小より tol 以上下がらない 5 回 → エポック {default.n_iter_} で止まる", color=RED, fontsize=9, ha="center")
axl.set_xlim(0.5, len(losses) + 0.5)
axl.set_ylim(0, max(losses) * 1.25)
axl.set_xticks(el)
axl.set_ylabel("損失の平均")
axl.grid(True, alpha=0.25)
axl.set_title("上: 止める判定に使う損失の平均（エポック 1〜20）", loc="left", fontsize=10)
ep = np.arange(1, 401)
ax.plot(ep, train_err, color=BLUE, lw=1.2)
ax.axvline(default.n_iter_, color=RED, lw=1.5, ls="--")
ax.text(default.n_iter_ + 22, max(train_err) * 0.97,
        f"既定の tol=1e-3 で\n止まる所（エポック {default.n_iter_}、誤り {train_err[default.n_iter_ - 1]} 行）",
        color=RED, fontsize=9, va="top")
ax.axvline(first_zero, color=INK, lw=1.2, ls=":")
ax.text(first_zero + 3, max(train_err) * 0.55, f"誤りが初めて 0\n（エポック {first_zero}）", color=INK, fontsize=9, va="top")
ax.set_xlabel("エポック（学習データを 1 周した回数）")
ax.set_ylabel("学習データ 426 行の誤り")
ax.grid(True, alpha=0.25)
ax.set_title("下: 学習データの誤りの数（エポック 1〜400）", loc="left", fontsize=10)
fig.suptitle("breast_cancer で eta0=1、random_state=0 の時、エポックごとに測った値", x=0.01, ha="left", fontsize=11)
fig.tight_layout()
save(fig, "pc_stop.webp")

# ============================================================
# 実験 5: 乱数ごとのテストの正解率（50 通り）
# ============================================================
print("\n# 実験 5: random_state を 50 通り変える")
results = {"既定（tol=1e-3）": [], "誤り 0 まで（tol=None）": [], "平均化（average=True）": []}
iters = []
for s in range(50):
    m = Perceptron(random_state=s).fit(X_train, y_train)
    results["既定（tol=1e-3）"].append(m.score(X_test, y_test))
    iters.append(m.n_iter_)
    m = Perceptron(tol=None, max_iter=1000, random_state=s).fit(X_train, y_train)
    assert m.score(X_train, y_train) == 1.0
    results["誤り 0 まで（tol=None）"].append(m.score(X_test, y_test))
    m = SGDClassifier(loss="perceptron", learning_rate="constant", eta0=1, penalty=None,
                      average=True, random_state=s).fit(X_train, y_train)
    results["平均化（average=True）"].append(m.score(X_test, y_test))
for name, v in results.items():
    print(f"{name:<22} 最小 {min(v):.3f}  中央値 {np.median(v):.3f}  最大 {max(v):.3f}")
print(f"既定の n_iter_: 最小 {min(iters)}、最大 {max(iters)}")
lr_acc = LogisticRegression().fit(X_train, y_train).score(X_test, y_test)
svc_acc = SVC(kernel="linear").fit(X_train, y_train).score(X_test, y_test)
print(f"LogisticRegression（既定）{lr_acc:.3f}、SVC(kernel='linear')（既定の C=1）{svc_acc:.3f}")

fig, ax = plt.subplots(figsize=(8.2, 3.6))
jit = np.random.default_rng(0)
for i, (name, v) in enumerate(results.items()):
    yy = i + jit.uniform(-0.18, 0.18, len(v))
    ax.scatter(v, yy, s=18, color=[BLUE, RED, GREEN][i], alpha=0.7)
    ax.plot([np.median(v)] * 2, [i - 0.3, i + 0.3], color=INK, lw=2)
ax.axvline(lr_acc, color=GRAY, ls="--", lw=1)
ax.text(lr_acc, 2.55, f"LogisticRegression\nと線形 SVC（{lr_acc:.3f}）" if abs(lr_acc - svc_acc) < 1e-9
        else f"LogisticRegression {lr_acc:.3f}", fontsize=8.5, color=INK, ha="center", va="bottom")
ax.set_yticks(range(3), list(results))
ax.set_ylim(-0.5, 3.2)
ax.set_xlabel("テストの正解率（143 行）")
ax.grid(True, axis="x", alpha=0.25)
ax.set_title("random_state を 50 通り変えた時のテストの正解率（黒い縦線は中央値）", loc="left", fontsize=10)
save(fig, "pc_seeds.webp")

# ============================================================
# 実験 6: 同じ点に引く線（パーセプトロン 30 通りと、ロジスティック回帰・SVM）
# ============================================================
print("\n# 実験 6: 2 次元のデータに引く線")
r = np.random.default_rng(3)
A = r.normal([0.0, 0.2], 0.45, (40, 2))
B = r.normal([2.0, 1.6], 0.45, (40, 2))
X6 = np.r_[A, B]
y6 = np.r_[np.zeros(40), np.ones(40)]
lines = []
for s in range(30):
    m = Perceptron(tol=None, max_iter=1000, random_state=s).fit(X6, y6)
    assert m.score(X6, y6) == 1.0
    lines.append((m.coef_[0] / np.linalg.norm(m.coef_[0]), m.intercept_[0] / np.linalg.norm(m.coef_[0])))
svm6 = SVC(kernel="linear", C=1e6).fit(X6, y6)
lr6 = LogisticRegression(C=1e6, max_iter=10000).fit(X6, y6)


def min_dist(w, b):
    n = np.linalg.norm(w)
    return np.min(np.abs(X6 @ w + b) / n)


dists = [min_dist(w, b) for w, b in lines]
print(f"パーセプトロン 30 通り: 一番近い点までの距離 最小 {min(dists):.3f} 中央値 {np.median(dists):.3f} 最大 {max(dists):.3f}")
print(f"線形 SVM（C=1e6）: {min_dist(svm6.coef_[0], svm6.intercept_[0]):.3f}")
print(f"LogisticRegression（C=1e6）: {min_dist(lr6.coef_[0], lr6.intercept_[0]):.3f}")
angs = [np.degrees(np.arctan2(w[1], w[0])) for w, _ in lines]
print(f"パーセプトロン 30 通りの線の向きの幅: {max(angs) - min(angs):.1f} 度")

fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
xx = np.linspace(-1.8, 3.8, 50)
for ax in axes:
    ax.scatter(*A.T, s=22, color=RED, marker="s")
    ax.scatter(*B.T, s=22, color=BLUE)
    ax.set_xlim(-1.8, 3.8)
    ax.set_ylim(-1.6, 3.4)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.25)
for w, b in lines:
    axes[0].plot(xx, -(w[0] * xx + b) / w[1], color=INK, lw=0.8, alpha=0.5)
axes[0].set_title(f"パーセプトロン（random_state 30 通り、どれも誤り 0）", loc="left", fontsize=10)
for m, c, ls, name in [(svm6, GREEN, "-", "線形 SVM（C=1e6）"), (lr6, INK, "--", "LogisticRegression（C=1e6）")]:
    w, b = m.coef_[0], m.intercept_[0]
    axes[1].plot(xx, -(w[0] * xx + b) / w[1], color=c, lw=2, ls=ls, label=name)
w, b = svm6.coef_[0], svm6.intercept_[0]
for off in (-1, 1):
    axes[1].plot(xx, -(w[0] * xx + b + off) / w[1], color=GREEN, lw=0.8, ls=":")
axes[1].legend(fontsize=9, loc="lower right")
axes[1].set_title("線形 SVM と LogisticRegression（どちらも 1 本）", loc="left", fontsize=10)
fig.tight_layout()
save(fig, "pc_lines.webp")

# ============================================================
# 実験 7: 分岐予測のシミュレーション
# ============================================================
print("\n# 実験 7: 分岐予測")
H, K, THETA, N_ITER, N_OTHER = 16, 8, 30, 30000, 5


def simulate(kind, seed=0):
    rng = np.random.default_rng(seed)
    hist = list(rng.choice([-1, 1], size=H))        # hist[0] が直前の分岐。+1 が成立、-1 が不成立
    w = np.zeros(H + 1)                              # 切片の分 + 履歴 16 個の重み
    wx = np.zeros(H + 2)                             # 上記に「3 個前 × 5 個前」の積を 1 列足したもの
    table = np.full(2 ** K, 1)                       # 直近 8 個の履歴で引く 2 ビットのカウンタ 256 個
    miss = {"表（直近 8 個の履歴、256 個のカウンタ）": [], "パーセプトロン（16 個の履歴、17 個の重み）": [],
            "パーセプトロン＋積の列（18 個の重み）": []}
    names = list(miss)
    for _ in range(N_ITER):
        for _ in range(N_OTHER):                     # 予測しない分岐が 5 個、ランダムに成立する
            hist.insert(0, rng.choice([-1, 1]))
            hist.pop()
        h = np.array(hist)
        if kind == "13 個前と同じ":
            t = h[12]
        else:                                        # 3 個前と 5 個前の排他的論理和
            t = -h[2] * h[4]
        idx = int("".join("1" if b > 0 else "0" for b in h[:K]), 2)
        p = 1 if table[idx] >= 2 else -1
        miss[names[0]].append(p != t)
        table[idx] = min(3, table[idx] + 1) if t > 0 else max(0, table[idx] - 1)
        for key, vec, x in [(names[1], w, np.r_[1, h]), (names[2], wx, np.r_[1, h, h[2] * h[4]])]:
            out = vec @ x
            p = 1 if out >= 0 else -1
            miss[key].append(p != t)
            if p != t or abs(out) <= THETA:          # 誤った時と、出力が閾値より小さい時に更新
                vec[:] = np.clip(vec + t * x, -128, 127)   # 重みは 8 ビットの範囲に収める
        hist.insert(0, t)
        hist.pop()
    return {k: float(np.mean(v[-10000:])) for k, v in miss.items()}, w


hs = np.arange(1, 33)
fig, ax = plt.subplots(figsize=(7.2, 3.8))
ax.semilogy(hs, 2.0 ** hs, "o-", color=GRAY, ms=3.5, label="表: 2 ビットのカウンタ 2^h 個")
ax.semilogy(hs, hs + 1, "o-", color=BLUE, ms=3.5, label="パーセプトロン: 重み h + 1 個")
for h_, c in [(8, GRAY), (13, GRAY), (16, GRAY)]:
    ax.annotate(f"h={h_}: {2 ** h_:,} 個", (h_, 2.0 ** h_), textcoords="offset points", xytext=(8, -12), fontsize=8.5, color=INK)
    ax.plot([h_], [2.0 ** h_], "o", color=INK, ms=5)
ax.annotate("h=16: 17 個", (16, 17), textcoords="offset points", xytext=(4, 8), fontsize=8.5, color=INK)
ax.set_xlabel("予測に使う履歴の長さ h（直前の分岐の数）")
ax.set_ylabel("カウンタ・重みの数")
ax.grid(True, which="major", alpha=0.25)
ax.legend(fontsize=9, loc="upper left")
ax.set_title("履歴を延ばした時の増え方: 表のカウンタとパーセプトロンの重み", loc="left", fontsize=10)
save(fig, "pc_storage.webp")

kinds = ["13 個前と同じ", "3 個前と 5 個前の排他的論理和"]
rates = {}
for kind in kinds:
    rates[kind], w_k = simulate(kind)
    for k, v in rates[kind].items():
        print(f"{kind:<16} {k:<26} 予測を外した割合 {v:.3f}")
    print(f"{kind}: パーセプトロンの重み（切片, 1 個前, 2 個前, ...）", np.round(w_k).astype(int).tolist())

fig, ax = plt.subplots(figsize=(8.4, 3.8))
names = list(rates[kinds[0]])
width = 0.26
for j, name in enumerate(names):
    vals = [rates[k][name] for k in kinds]
    pos = np.arange(len(kinds)) + (j - 1) * width
    shown = [max(v, 0.006) for v in vals]       # 0% の棒も色が見えるよう、最低の高さを付けて描く
    ax.bar(pos, shown, width * 0.92, color=[GRAY, BLUE, GREEN][j], label=name)
    for p_, v in zip(pos, vals):
        ax.text(p_, v + 0.01, f"{v * 100:.1f}%", ha="center", fontsize=8.5, color=INK)
ax.set_xticks(range(len(kinds)), [f"分岐 B が「{k}」" for k in kinds])
ax.set_ylabel("予測を外した割合（最後の 1 万回）")
ax.text(1.0, 0.6, "0.0% の棒は、色が見えるよう最低の高さで描いた", ha="right", fontsize=8, color=GRAY, transform=ax.get_yaxis_transform())
ax.set_ylim(0, 0.62)
ax.axhline(0.5, color=GRAY, lw=0.8, ls=":")
ax.legend(fontsize=8.5, loc="upper center", ncol=1, bbox_to_anchor=(0.5, -0.14), frameon=False)
ax.grid(True, axis="y", alpha=0.25)
ax.set_title("分岐 B の予測を外した割合（間に 5 個の分岐がランダムに入る）", loc="left", fontsize=10)
save(fig, "pc_branch.webp")
# ============================================================
# 実験 8: XOR の 4 点を、パーセプトロンと隠れ層のある MLP で学習する
# ============================================================
print("\n# 実験 8: XOR")
X_xor = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
y_xor = np.array([0, 1, 1, 0])
p = Perceptron(tol=None, max_iter=1000, random_state=0).fit(X_xor, y_xor)
print("Perceptron の予測:", p.predict(X_xor), " 正解:", y_xor)
mlp = MLPClassifier(hidden_layer_sizes=(4,), activation="tanh", solver="lbfgs", random_state=0).fit(X_xor, y_xor)
print("MLPClassifier（隠れ層 4 ユニット）の予測:", mlp.predict(X_xor))
h = np.tanh(X_xor @ mlp.coefs_[0] + mlp.intercepts_[0])
print("隠れ層の出力（行が 4 点、列が 4 ユニット）:")
print(np.round(h, 2))

fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.0))
gx, gy = np.meshgrid(np.linspace(-0.5, 1.5, 201), np.linspace(-0.5, 1.5, 201))
grid = np.c_[gx.ravel(), gy.ravel()]
for ax, model, title in [(axes[0], p, f"Perceptron（4 点中 {int(p.score(X_xor, y_xor) * 4)} 点）"),
                         (axes[1], mlp, f"MLPClassifier、隠れ層 4 ユニット（4 点中 {int(mlp.score(X_xor, y_xor) * 4)} 点）")]:
    zz = model.predict(grid).reshape(gx.shape)
    ax.contourf(gx, gy, zz, levels=[-0.5, 0.5, 1.5], colors=["#f6dcdc", "#dce9f2"])
    ax.scatter(*X_xor[y_xor == 1].T, s=120, color=BLUE, label="正解 1", zorder=3)
    ax.scatter(*X_xor[y_xor == 0].T, s=120, color=RED, marker="s", label="正解 0", zorder=3)
    ax.set_xlim(-0.5, 1.5)
    ax.set_ylim(-0.5, 1.5)
    ax.set_aspect("equal")
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_title(title, loc="left", fontsize=10)
axes[0].legend(fontsize=9, loc="upper right")
fig.suptitle("XOR の 4 点と、予測した領域（青 = 1、赤 = 0）", x=0.01, ha="left", fontsize=11)
fig.tight_layout()
save(fig, "pc_xor.webp")

# XOR で、最初の節の規則（w = 0 から、行の順番のまま）を回すと、重みはどう動くか
t_xor = 2 * y_xor - 1
Xa_xor = np.c_[X_xor, np.ones(4)]
w = np.zeros(3)
for epoch in range(1, 1001):
    mistakes = 0
    for i in range(4):
        if t_xor[i] * (Xa_xor[i] @ w) <= 0:
            w = w + t_xor[i] * Xa_xor[i]
            mistakes += 1
    if epoch <= 3:
        print(f"XOR エポック {epoch}: 誤り {mistakes} 点、エポックの終わりの w={w.tolist()}")
print(f"XOR エポック 1000: 誤り {mistakes} 点、エポックの終わりの w={w.tolist()}")

# ============================================================
# 実験 9: 重みを手で決めた 3 個のパーセプトロンで XOR を作る
# ============================================================
print("\n# 実験 9: 手で組んだ隠れ層")
step = lambda z: (z > 0).astype(int)
h1 = step(X_xor @ np.array([1, 1]) - 0.5)     # OR
h2 = step(X_xor @ np.array([-1, -1]) + 1.5)   # NAND（AND の否定）
out = step(h1 + h2 - 1.5)                     # AND
print("h1 =", h1, "h2 =", h2, "出力 =", out)
for xx, a, b_ in zip(X_xor, h1, h2):
    print(f"入力 {tuple(int(v) for v in xx)} → 隠れ層 ({a}, {b_})")

fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.7), gridspec_kw={"width_ratios": [1.15, 1, 1]})
# 左: 構造
ax = axes[0]
ax.set_xlim(0, 3.2)
ax.set_ylim(-0.2, 3.3)
ax.set_aspect("equal")
ax.axis("off")
nodes = {"x1": (0.4, 2.3), "x2": (0.4, 0.7), "h1": (1.6, 2.3), "h2": (1.6, 0.7), "y": (2.8, 1.5)}
labels = {"x1": "x1", "x2": "x2", "h1": "h1\nOR", "h2": "h2\nNAND", "y": "出力\nAND"}
edges = [("x1", "h1", "1"), ("x2", "h1", "1"), ("x1", "h2", "-1"), ("x2", "h2", "-1"), ("h1", "y", "1"), ("h2", "y", "1")]
label_pos = {("x1", "h1"): (1.0, 2.42), ("x2", "h2"): (1.0, 0.45), ("x1", "h2"): (0.88, 1.88),
             ("x2", "h1"): (0.88, 1.12), ("h1", "y"): (2.3, 2.0), ("h2", "y"): (2.3, 0.95)}
for a, b_, wt in edges:
    (xa, ya), (xb, yb) = nodes[a], nodes[b_]
    ax.annotate("", xy=(xb, yb), xytext=(xa, ya),
                arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=1.2, shrinkA=16, shrinkB=16))
    lx, ly = label_pos[(a, b_)]
    ax.text(lx, ly, wt, fontsize=10, color=INK, ha="center", va="center",
            bbox=dict(facecolor="#ffffff", edgecolor="none", pad=1))
for k, (xx, yy) in nodes.items():
    col = "#ffffff" if k.startswith("x") else ("#eef3ea" if k == "y" else "#e8f0f6")
    ax.add_patch(plt.Circle((xx, yy), 0.34, facecolor=col, edgecolor=INK, lw=1.2))
    ax.text(xx, yy, labels[k], ha="center", va="center", fontsize=10, color=INK)
ax.text(1.6, 2.75, "切片 -0.5", ha="center", fontsize=10, color=GRAY)
ax.text(1.6, 0.05, "切片 1.5", ha="center", fontsize=10, color=GRAY)
ax.text(2.8, 0.85, "切片 -1.5", ha="center", fontsize=10, color=GRAY)
ax.text(0.4, 3.05, "入力層", ha="center", fontsize=10, color=GRAY)
ax.text(1.6, 3.05, "隠れ層", ha="center", fontsize=10, color=GRAY)
ax.text(2.8, 3.05, "出力層", ha="center", fontsize=10, color=GRAY)
ax.set_title("手で重みを決めた構造", loc="left", fontsize=11)

def plot_pts(ax, P, ycls):
    for (px, py), c in zip(P, ycls):
        if c == 1:
            ax.scatter(px, py, s=130, color=BLUE, zorder=3)
        else:
            ax.scatter(px, py, s=130, color=RED, marker="s", zorder=3)

# 中: 入力の空間と、隠れ層の 2 本の線
ax = axes[1]
xs = np.linspace(-0.5, 1.5, 2)
ax.plot(xs, 0.5 - xs, color=BLUE, lw=1.2, ls="--")
ax.plot(xs, 1.5 - xs, color=BLUE, lw=1.2, ls="-.")
ax.text(-0.45, -0.4, "h1 の線\nx1+x2=0.5", fontsize=10, color=INK)
ax.text(0.95, 1.22, "h2 の線\nx1+x2=1.5", fontsize=10, color=INK)
plot_pts(ax, X_xor, y_xor)
for (px, py) in X_xor:
    ax.text(px + 0.07, py - 0.16, f"({px}, {py})", fontsize=10, color=INK)
ax.set_xlim(-0.5, 1.5)
ax.set_ylim(-0.5, 1.5)
ax.set_aspect("equal")
ax.set_xticks([0, 1])
ax.set_yticks([0, 1])
ax.set_xlabel("x1")
ax.set_ylabel("x2")
ax.set_title("入力の 4 点（線 1 本では無理）", loc="left", fontsize=11)

# 右: 隠れ層の出力の空間
ax = axes[2]
H = np.c_[h1, h2]
ax.plot(xs, 1.5 - xs, color=GREEN, lw=1.4)
ax.text(1.08, 0.62, "出力の線\nh1+h2=1.5", fontsize=10, color=INK)
plot_pts(ax, H, y_xor)
moved = {}
for xx, (a, b_) in zip(X_xor, H):
    moved.setdefault((a, b_), []).append(f"({xx[0]}, {xx[1]})")
label_xy = {(0, 1): (-0.3, 1.15), (1, 1): (0.5, 1.2), (1, 0): (0.62, -0.25)}
for (a, b_), src in moved.items():
    ax.text(*label_xy[(a, b_)], "入力 " + "・".join(src), fontsize=10, color=INK)
ax.set_xlim(-0.5, 1.5)
ax.set_ylim(-0.5, 1.5)
ax.set_aspect("equal")
ax.set_xticks([0, 1])
ax.set_yticks([0, 1])
ax.set_xlabel("h1")
ax.set_ylabel("h2")
ax.set_title("隠れ層が移した先（線 1 本で分かれる）", loc="left", fontsize=11)
fig.suptitle("XOR を 3 個のパーセプトロンで作る（青い丸 = 正解 1、赤い四角 = 正解 0）", x=0.01, ha="left", fontsize=12)
fig.tight_layout()
save(fig, "pc_hidden.webp")

print("\n図を保存:", sorted(p.name for p in NOTE_DIR.glob("pc_*.webp")))
