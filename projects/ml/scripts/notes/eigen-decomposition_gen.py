"""eigen-decomposition ノートの実験と図を生成するスクリプト。

本文に載せた実験（固有ベクトルの向き、対称行列の分解、固有値の差と固有ベクトルの揺れ、
wine の選び直し、eig と eigh、対角化できない行列、X^T X と SVD）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/eigen-decomposition_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、SciPy 1.18.1
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import load_wine
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "eigen-decomposition"
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
# 実験 1: A をかけても向きが変わらないベクトル
# ============================================================
A = np.array([[2.0, 1.0], [0.0, 3.0]])
eigvals, eigvecs = np.linalg.eig(A)
for lam, v in zip(eigvals.real, eigvecs.real.T):
    print(f"λ={lam:.1f}  v={np.round(v, 3)}  Av={np.round(A @ v, 3)}")

angles = np.linspace(0, np.pi, 18, endpoint=False)
vs = np.column_stack([np.cos(angles), np.sin(angles)])
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
for ax, M, title, lim in [(axes[0], np.eye(2), "A をかける前（長さ 1 のベクトル 18 本）", 1.5),
                          (axes[1], A, "A をかけた後", 4.0)]:
    for v in vs:
        ax.quiver(0, 0, *(M @ v), angles="xy", scale_units="xy", scale=1, color=BLUE,
                  alpha=0.55, width=0.005)
    for i in range(2):
        ev = eigvecs.real[:, i] / np.linalg.norm(eigvecs.real[:, i])
        lam = eigvals.real[i]
        label = "固有ベクトル" if M is not A else "固有値の倍数だけ伸びた固有ベクトル"
        tip = M @ ev
        ax.quiver(0, 0, *tip, angles="xy", scale_units="xy", scale=1, color=RED,
                  width=0.012, label=label if i == 0 else None)
        ax.text(tip[0] + 0.04 * lim, tip[1] - 0.06 * lim, f"λ={lam:.0f}", color=RED, fontsize=9)
    ax.set_xlim(-lim * 0.75, lim * 0.85)
    ax.set_ylim(-0.25 * lim, lim * 0.85)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.25)
    ax.set_title(title, fontsize=10)
    ax.legend(loc="lower left", fontsize=9)
fig.tight_layout()
save(fig, "eig_action.webp")


# ============================================================
# 実験 2: 対称行列の分解 A = Q Λ Q^T
# ============================================================
A = np.array([[3.0, 1.0], [1.0, 2.0]])  # 対称行列
eigvals, Q = np.linalg.eigh(A)          # 固有値の昇順で返る
eigvals, Q = eigvals[::-1], Q[:, ::-1]  # 大きい順に並べ替える
Lam = np.diag(eigvals)

print("λ =", np.round(eigvals, 3))
print("Q =", np.round(Q, 3).tolist())
print("q1・q2 =", round(float(Q[:, 0] @ Q[:, 1]), 3))
print("Q Λ Q^T == A:", np.allclose(Q @ Lam @ Q.T, A))

# ここから図のためだけの処理（本文には載せない）。
# 固有ベクトルの符号は任意なので、各列の第 1 成分を正にそろえ、
# 鏡映を含む（行列式が負）なら 2 列目を反転して、Q を回転にする。
Q = Q * np.sign(Q[0])
if np.linalg.det(Q) < 0:
    Q[:, 1] *= -1

theta = np.linspace(0, 2 * np.pi, 100)
circle = np.array([np.cos(theta), np.sin(theta)])
stages = [np.eye(2), Q.T, Lam @ Q.T, Q @ Lam @ Q.T]
titles = ["1. 元の単位円", "2. Q^T で回して\nq1・q2 を座標軸へ",
          f"3. Λ で軸ごとに\n{eigvals[0]:.2f} 倍・{eigvals[1]:.2f} 倍", "4. Q で戻す\n（A をかけた円と同じ形）"]
fig, axes = plt.subplots(1, 4, figsize=(13, 3.8), sharex=True, sharey=True)
for ax, M, title in zip(axes, stages, titles):
    shape = M @ circle
    ax.plot(shape[0], shape[1], color=BLUE, lw=2)
    ax.fill(shape[0], shape[1], color=BLUE, alpha=0.15)
    for j, (c, name) in enumerate([(RED, "q1"), (GREEN, "q2")]):
        ax.quiver(0, 0, *(M @ Q[:, j]), angles="xy", scale_units="xy", scale=1, color=c,
                  width=0.014, label=name)
    ax.axhline(0, color=GRAY, lw=0.5)
    ax.axvline(0, color=GRAY, lw=0.5)
    ax.set_aspect("equal")
    ax.set_xlim(-4, 4)
    ax.set_ylim(-4, 4)
    ax.grid(True, alpha=0.25)
    ax.set_title(title, fontsize=10)
axes[0].legend(loc="lower left", fontsize=9)
fig.tight_layout()
save(fig, "eig_steps.webp")


# ============================================================
# 実験 3: 固有値の差と、固有ベクトルの揺れ
# ============================================================
rng = np.random.default_rng(0)
fan = {}
for gap in [1.0, 0.1, 0.01]:
    A = np.diag([1.0 + gap, 1.0])  # 固有ベクトルは (1, 0) と (0, 1)
    v1s = []
    for _ in range(100):
        E = rng.normal(scale=0.01, size=(2, 2))
        E = (E + E.T) / 2                    # 大きさ 0.01 ほどの対称な揺れ
        _, V = np.linalg.eigh(A + E)
        v1s.append(V[:, 1])                  # 大きい方の固有値の固有ベクトル
    v1s = np.array(v1s)
    deg = np.degrees(np.arccos(np.abs(v1s[:, 0])))  # (1, 0) からの角度。符号は任意なので絶対値
    fan[gap] = v1s
    print(f"固有値の差 {gap:<5}: 角度の中央値 {np.median(deg):5.1f} 度、最大 {deg.max():5.1f} 度")

fig, axes = plt.subplots(1, 3, figsize=(11, 3.9))
for ax, gap in zip(axes, fan):
    for v in fan[gap]:
        ax.plot([-v[0], v[0]], [-v[1], v[1]], color=RED, alpha=0.25, lw=1)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.plot([-1, 1], [0, 0], color=INK, lw=1, ls=":")
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"固有値 {1 + gap:g} と 1（差 {gap:g}）", fontsize=10)
axes[0].text(0, -0.3, "点線: 揺らす前の固有ベクトル (1, 0)", ha="center", fontsize=8.5, color=INK)
fig.suptitle("大きさ 0.01 の揺れを 100 回足した時の、大きい方の固有値の固有ベクトル", fontsize=10.5)
fig.tight_layout(rect=(0, 0, 1, 0.93))
save(fig, "eig_gap.webp")


# ============================================================
# 実験 4: wine を選び直すと、主成分の向きはどれだけ動くか（表紙）
# ============================================================
wine = load_wine()
X = StandardScaler().fit_transform(wine.data)          # 178 行 × 13 列を標準化
C = np.cov(X, rowvar=False)
lam, V = np.linalg.eigh(C)
lam, V = lam[::-1], V[:, ::-1]                         # 固有値の大きい順
names = np.array(wine.feature_names)
print("元の PC4 で重みの絶対値が最大の列:", names[np.argmax(np.abs(V[:, 3]))])
K = 8
rng = np.random.default_rng(0)
ang = np.zeros((200, K))
swap = 0
shake = []                                             # 共分散行列の揺れの大きさ
top4 = []                                              # 選び直した PC4 で重みが最大の列
for b in range(200):
    Xb = X[rng.integers(0, len(X), len(X))]            # 重複を許して 178 行を選び直す
    Cb = np.cov(Xb, rowvar=False)
    _, Vb = np.linalg.eigh(Cb)
    Vb = Vb[:, ::-1]
    cos = np.abs(np.sum(V[:, :K] * Vb[:, :K], axis=0))  # 符号は任意なので絶対値
    ang[b] = np.degrees(np.arccos(np.clip(cos, 0, 1)))
    swap += abs(V[:, 4] @ Vb[:, 3]) > abs(V[:, 3] @ Vb[:, 3])  # 選び直した PC4 が元の PC5 に近い
    shake.append(np.linalg.norm(Cb - C, 2))            # 揺れの行列の 2 ノルム
    top4.append(names[np.argmax(np.abs(Vb[:, 3]))])
print("固有値:", lam[:K].round(3))
print("角度の中央値:", np.median(ang, axis=0).round(1))
print("角度の 90% 点:", np.percentile(ang, 90, axis=0).round(1))
print(f"選び直した PC4 が、元の PC4 より元の PC5 に近かった回数: {swap} / 200")
print(f"共分散行列の揺れの大きさ（中央値）: {np.median(shake):.2f}")
col, cnt = np.unique(top4, return_counts=True)
print("選び直した PC4 で重みが最大の列:", dict(sorted(zip(col.tolist(), cnt.tolist()), key=lambda t: -t[1])[:3]))

pcs = np.arange(1, K + 1)
hot = [3, 4]
colors = [RED if i in hot else BLUE for i in range(K)]
fig, axes = plt.subplots(2, 1, figsize=(7.5, 5.6), sharex=True,
                         gridspec_kw={"height_ratios": [1, 1.3]})
ax = axes[0]
ax.bar(pcs, lam[:K], color=colors, width=0.6)
for i in range(K):
    ax.text(pcs[i], lam[i] + 0.1, f"{lam[i]:.2f}", ha="center", fontsize=8.5)
ax.set_ylabel("固有値（分散）")
ax.set_ylim(0, 5.5)
ax.set_title("wine（標準化）の共分散行列の固有値と、行を選び直した時の固有ベクトルの角度", fontsize=10)
ax = axes[1]
med = np.median(ang, axis=0)
p90 = np.percentile(ang, 90, axis=0)
ax.bar(pcs, med, color=colors, width=0.6, label="200 回の中央値")
ax.scatter(pcs, p90, color=INK, marker="_", s=300, lw=2, zorder=5, label="200 回の 90% 点")
for i in range(K):
    ax.text(pcs[i], 1.5, f"{med[i]:.0f}°", ha="center", fontsize=8.5, color="#ffffff")
ax.set_ylabel("元の向きとの角度（度）")
ax.set_ylim(0, 90)
ax.set_yticks([0, 30, 60, 90])
ax.set_xticks(pcs)
ax.set_xticklabels([f"PC{i}" for i in pcs])
ax.legend(fontsize=8.5, loc="upper left")
ax.grid(True, axis="y", alpha=0.25)
fig.tight_layout()
save(fig, "eig_cover.webp")


# ============================================================
# 実験 5: 対称ではない行列を eigh に渡す
# ============================================================
P = np.array([[0.9, 0.1, 0.0],   # 晴 → 晴・曇・雨
              [0.2, 0.7, 0.1],   # 曇 → 晴・曇・雨
              [0.1, 0.3, 0.6]])  # 雨 → 晴・曇・雨

lam_e, V_e = np.linalg.eig(P.T)
pi_eig = V_e[:, np.argmax(lam_e.real)].real
pi_eig /= pi_eig.sum()

lam_l, V_l = np.linalg.eigh(P.T)               # 対称ではない行列を渡す（既定は下三角）
pi_l = V_l[:, -1] / V_l[:, -1].sum()
lam_u, V_u = np.linalg.eigh(P.T, UPLO="U")     # 上三角を使わせる
pi_u = V_u[:, -1] / V_u[:, -1].sum()

x = np.full(3, 1 / 3)
for _ in range(1000):                          # 実際に 1000 日分の遷移を掛ける
    x = x @ P

print("eig            : 最大の固有値", round(float(lam_e.real.max()), 4), "分布", pi_eig.round(4))
print("eigh（下三角）  : 最大の固有値", round(float(lam_l[-1]), 4), "分布", pi_l.round(4))
print("eigh（上三角）  : 最大の固有値", round(float(lam_u[-1]), 4), "分布", pi_u.round(4))
print("1000 日後       :", x.round(4))

fig, ax = plt.subplots(figsize=(7.5, 3.6))
labels = ["晴", "曇", "雨"]
rows = [("1000 日分の遷移を掛けた結果", x, INK), ("eig", pi_eig, BLUE),
        (f"eigh（既定の下三角、最大の固有値 {lam_l[-1]:.3f}）", pi_l, RED),
        (f"eigh（UPLO=\"U\"、最大の固有値 {lam_u[-1]:.3f}）", pi_u, "#f0a3a4")]
wbar = 0.2
for k, (name, vals, c) in enumerate(rows):
    pos = np.arange(3) + (k - 1.5) * wbar
    ax.bar(pos, vals, width=wbar, color=c, label=name)
    for p_, v_ in zip(pos, vals):
        ax.text(p_, v_ + 0.01, f"{v_:.2f}", ha="center", fontsize=7.5)
ax.set_xticks(range(3))
ax.set_xticklabels(labels)
ax.set_ylabel("長い目で見た各天気の割合")
ax.set_ylim(0, 0.8)
ax.legend(fontsize=8, loc="upper right")
ax.set_title("天気の遷移行列の定常分布（1000 日分の遷移と、eig・2 通りの eigh）", fontsize=10)
fig.tight_layout()
save(fig, "eig_markov.webp")


# ============================================================
# 実験 6: 固有値が重なると、固有ベクトルが平行になる
# ============================================================
for eps in [1.0, 1e-1, 1e-2, 1e-4, 1e-8, 0.0]:
    J = np.array([[1.0, 1.0], [0.0, 1.0 + eps]])  # 固有値は 1 と 1 + eps
    w, V = np.linalg.eig(J)
    w, V = w.real, V.real
    deg = np.degrees(np.arctan2(abs(V[0, 0] * V[1, 1] - V[1, 0] * V[0, 1]), abs(V[:, 0] @ V[:, 1])))
    print(f"eps={eps:<6g} 固有値 {np.round(w, 8)}  2 本の角度 {deg:9.2e} 度  cond(V) {np.linalg.cond(V):.1e}")

fig, axes = plt.subplots(1, 2, figsize=(10, 3.9), gridspec_kw={"width_ratios": [1, 1.4]})
ax = axes[0]
for eps, c in [(1.0, BLUE), (0.1, GREEN), (0.01, RED)]:
    J = np.array([[1.0, 1.0], [0.0, 1.0 + eps]])
    V = np.linalg.eig(J)[1].real
    v = V[:, 1] * np.sign(V[0, 1])
    ax.quiver(0, 0, *v, angles="xy", scale_units="xy", scale=1, color=c, width=0.012,
              label=f"差 {eps:g} の時の 2 本目")
ax.quiver(0, 0, 1, 0, angles="xy", scale_units="xy", scale=1, color=INK, width=0.012,
          label="1 本目 (1, 0)")
ax.set_xlim(-0.1, 1.1)
ax.set_ylim(-0.1, 0.8)
ax.set_aspect("equal")
ax.grid(True, alpha=0.25)
ax.legend(fontsize=8.5, loc="upper left")
ax.set_title("固有値の差が縮むと、2 本目が 1 本目に寄る", fontsize=10)
ax = axes[1]
epss = np.logspace(-15, 0, 61)
conds = [np.linalg.cond(np.linalg.eig(np.array([[1.0, 1.0], [0.0, 1.0 + e]]))[1]) for e in epss]
ax.loglog(epss, conds, color=RED, lw=2)
ax.axhline(1 / np.finfo(float).eps, color=GRAY, ls=":", lw=1)
ax.text(1e-14, 1 / np.finfo(float).eps * 2, "float64 の精度の限界 ≈ 4.5e15", fontsize=8.5, color=INK)
ax.set_xlabel("2 つの固有値の差 ε")
ax.set_ylabel("cond(V)")
ax.set_ylim(1, 1e17)
ax.set_title("固有ベクトルを並べた V の条件数", fontsize=10)
ax.grid(True, which="major", alpha=0.25)
fig.tight_layout()
save(fig, "eig_defective.webp")


# ============================================================
# 実験 7: scikit-learn の PCA で、小さい主成分の分散が消える
# ============================================================
rng = np.random.default_rng(0)
n = 1000
G = rng.normal(size=(n, 3))
G -= G.mean(axis=0)
U, _ = np.linalg.qr(G)                          # 平均 0 で、互いに直交する長さ 1 の 3 列
R, _ = np.linalg.qr(rng.normal(size=(3, 3)))    # 主成分の向きを列の軸からずらす回転
ss = 10.0 ** -np.arange(1, 12)
err = {"auto": [], "covariance_eigh": [], "full": []}
for s in ss:
    X = np.sqrt(n - 1) * U @ np.diag([1.0, 1.0, s]) @ R  # 主成分の分散は 1、1、s^2
    for solver in err:
        v = PCA(svd_solver=solver).fit(X).explained_variance_[-1]
        err[solver].append(abs(v - s**2) / s**2)
        if s in (1e-4, 1e-8, 1e-10):
            print(f"s={s:.0e} 正しい分散 {s**2:.1e}  {solver:<15} {v:.3e}")

fig, ax = plt.subplots(figsize=(7, 3.6))
ax.loglog(ss, err["full"], "o-", color=BLUE, lw=2, label='svd_solver="full"')
ax.loglog(ss, err["auto"], "s--", color=RED, lw=2,
          label='svd_solver="auto"（この形では covariance_eigh）')
ax.set_xlabel("一番小さい主成分の標準偏差 s")
ax.set_ylabel("分散の相対誤差")
ax.set_ylim(1e-17, 1e6)
ax.axhline(1, color=GRAY, ls=":", lw=1)
ax.text(1.2e-1, 2, "点線: 分散を 0 と返すとこの線に乗る", fontsize=8, color=INK)
ax.invert_xaxis()
ax.legend(fontsize=9, loc="lower right")
ax.grid(True, which="major", alpha=0.25)
ax.set_title("PCA が返す一番小さい分散（explained_variance_）の相対誤差", fontsize=10)
fig.tight_layout()
save(fig, "eig_svd.webp")

print("done:", sorted(p.name for p in NOTE_DIR.iterdir()))
