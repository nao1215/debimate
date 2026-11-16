"""data-leakage ノートの実験と図を生成するスクリプト。

本文に載せた実験（正解の無いデータで 6 通りの手順を比べる、実データで分割の前に標準化した差、
雑音の列の数と列を選ぶ漏れ、欠損値の割合と正解を入れた補完、Olivetti の同じ人の写真）を
同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
Olivetti faces は初回だけ scikit-learn の配布元（figshare）から取得する。
実行: cd projects/ml && .venv/bin/python scripts/notes/data-leakage_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
"""
import warnings
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import fetch_olivetti_faces, load_breast_cancer, load_wine
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.impute import IterativeImputer, SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, KFold, StratifiedKFold, cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "data-leakage"
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
# 実験 1: 正解の無いデータで、6 通りの手順を比べる
# ============================================================
def noise(seed, n=100, p=2000):
    """正解と無関係な列だけのデータ。正解は 0 と 1 が半分ずつ"""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, p))
    y = rng.permutation(np.repeat([0, 1], n // 2))
    return X, y, rng


# 本文に載せた 1 回分（seed=0）。分割の前に標準化する手順と、分割の前に列を選ぶ手順
rng = np.random.default_rng(0)
X = rng.normal(size=(100, 2000))                 # 正解と無関係な 2000 列
y = rng.permutation(np.repeat([0, 1], 50))       # 正解は 0 と 1 が 50 行ずつ
cv = StratifiedKFold(5, shuffle=True, random_state=0)
lr = LogisticRegression(max_iter=1000)

# 標準化: 全ての行で平均と標準偏差を求めてから分ける / 分割ごとに学習側だけで求める
leak = cross_val_score(lr, StandardScaler().fit_transform(X[:, :20]), y, cv=cv).mean()
safe = cross_val_score(make_pipeline(StandardScaler(), lr), X[:, :20], y, cv=cv).mean()
print(f"標準化         : 分割の前 {leak:.2f}  Pipeline {safe:.2f}")

# 列を選ぶ: 全ての行で正解と関係の強い 20 列を選んでから分ける / 分割ごとに学習側だけで選ぶ
leak = cross_val_score(lr, SelectKBest(f_classif, k=20).fit_transform(X, y), y, cv=cv).mean()
safe = cross_val_score(make_pipeline(SelectKBest(f_classif, k=20), lr), X, y, cv=cv).mean()
print(f"20 列を選ぶ    : 分割の前 {leak:.2f}  Pipeline {safe:.2f}")

rf = RandomForestClassifier(n_estimators=200, random_state=0)
faces = fetch_olivetti_faces()              # 40 人 × 10 枚の顔写真
SEEDS = range(20)
score = {}
for seed in SEEDS:
    X, y, rng = noise(seed)
    cv = StratifiedKFold(5, shuffle=True, random_state=seed)

    def cvs(model, data, target=y, **kw):
        return cross_val_score(model, data, target, cv=kw.pop("cv", cv), **kw).mean()

    X20 = X[:, :20]
    Xm = X20.copy()
    Xm[rng.random(Xm.shape) < 0.95] = np.nan  # 95% の値を欠損値にする
    rows = {
        # 正解を使わない前処理
        "標準化": (cvs(lr, StandardScaler().fit_transform(X20)),
                 cvs(make_pipeline(StandardScaler(), lr), X20)),
        "平均で補完": (cvs(lr, SimpleImputer().fit_transform(Xm)),
                   cvs(make_pipeline(SimpleImputer(), lr), Xm)),
        "PCA で 10 列に": (cvs(lr, PCA(10, random_state=0).fit_transform(X)),
                        cvs(make_pipeline(PCA(10, random_state=0), lr), X)),
        # 正解を使う前処理
        "2000 列から 20 列を選ぶ": (cvs(lr, SelectKBest(f_classif, k=20).fit_transform(X, y)),
                              cvs(make_pipeline(SelectKBest(f_classif, k=20), lr), X)),
        "正解の列も入れて補完": (
            cvs(rf, IterativeImputer(random_state=0).fit_transform(np.column_stack([Xm, y]))[:, :-1]),
            cvs(make_pipeline(IterativeImputer(random_state=0), rf), Xm)),
    }
    # 同じ人の写真: 40 人に 0 と 1 を半分ずつ配り、その人の写真 10 枚の正解にする
    coin = rng.permutation(np.repeat([0, 1], 20))
    yf = coin[faces.target]
    knn = KNeighborsClassifier(n_neighbors=1)
    rows["同じ人の写真を分けずに CV"] = (
        cvs(knn, faces.data, yf, cv=KFold(5, shuffle=True, random_state=seed)),
        cvs(knn, faces.data, yf, cv=GroupKFold(5), groups=faces.target))
    for k, v in rows.items():
        score.setdefault(k, []).append(v)

print("手順ごとの正解率の平均（20 回）: 分割の前に処理 / Pipeline か GroupKFold")
for k, v in score.items():
    v = np.array(v)
    print(f"  {k:<16} {v[:, 0].mean():.3f} / {v[:, 1].mean():.3f}")

fig, ax = plt.subplots(figsize=(8.6, 4.4))
names = list(score)
for i, k in enumerate(names):
    v = np.array(score[k])
    yy = len(names) - 1 - i
    jit = np.linspace(-0.12, 0.12, len(v))
    ax.scatter(v[:, 1], yy - 0.17 + jit * 0.5, s=14, color=BLUE, alpha=0.7,
               label="Pipeline か GroupKFold（正しい手順）" if i == 0 else None)
    ax.scatter(v[:, 0], yy + 0.17 + jit * 0.5, s=14, color=RED, alpha=0.7,
               label="分割の前に処理（漏れる手順）" if i == 0 else None)
    # 破線のすぐ下の行は、数字が破線に重ならないよう少し下げる
    ax.text(v[:, 0].mean(), yy + (0.36 if yy == 2 else 0.42), f"{v[:, 0].mean():.2f}", color=RED, ha="center", va="center",
            fontsize=9)
ax.axhline(2.5, color=GRAY, lw=0.8, ls="--")
ax.text(0.62, 2.6, "↑ 正解を使わない前処理", color=INK, fontsize=9)
ax.text(0.62, 2.27, "↓ 正解が学習に届く手順", color=INK, fontsize=9)
ax.axvline(0.5, color=INK, lw=0.8, ls=":")
ax.set_yticks(range(len(names)))
ax.set_yticklabels(names[::-1])
ax.set_xlim(0.28, 1.02)
ax.set_ylim(-0.6, len(names) - 0.3)
ax.set_xlabel("5 分割の交差検証の正解率（点線の 0.5 が偶然の水準）")
ax.set_title("正解と無関係なデータで、手順ごとに 20 回測った正解率", fontsize=10)
ax.legend(loc="upper right", fontsize=8.5, frameon=False)
fig.tight_layout()
save(fig, "data-leakage_cover.webp")


# ============================================================
# 図: 5 分割の各回で fit に使う行（動く図。1 回を 1.6 秒ずつ表示）
# ============================================================
from matplotlib.patches import Rectangle  # noqa: E402

LIGHT, ORANGE = "#dbe7f0", "#f2b36b"


def fold_frame(k, final=False):
    """k=0 は準備、1〜5 は第 k 回の検証、final は最後のまとめ"""
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    ax.set_position([0.01, 0.01, 0.98, 0.98])
    ax.set_xlim(-1.9, 10.2)
    ax.set_ylim(-1.5, 6.4)
    ax.axis("off")
    head = "準備" if k == 0 else f"第 {k} 回の検証 / 全 5 回"
    ax.text(-1.8, 6.05, head, fontsize=12, color=INK, va="center")
    for i in range(5):  # 進み具合の帯
        ax.add_patch(Rectangle((6.0 + i * 0.8, 5.88), 0.7, 0.32,
                               color=INK if 0 < i + 1 <= k else LIGHT))
    for row, (yb, title) in enumerate([(3.0, "分割の前に fit（漏れる手順）"),
                                       (0.0, "Pipeline（分割ごとに学習側だけで fit）")]):
        ax.text(-1.8, yb + 2.15, title, fontsize=10.5, color=INK, va="center")
        for i in range(5):
            x = i * 2.0
            val = (i + 1 == k)
            ax.add_patch(Rectangle((x, yb), 1.85, 0.9, color=ORANGE if val else LIGHT))
            lab = "検証" if val else ("学習" if k > 0 else f"{i * 20 + 1}〜{i * 20 + 20} 行")
            ax.text(x + 0.925, yb + 0.45, lab, ha="center", va="center", fontsize=9.5, color=INK)
            # fit に使う行の帯
            if row == 0:
                use = True
            else:
                use = k > 0 and not val
            if use:
                ax.add_patch(Rectangle((x, yb + 1.05), 1.85, 0.32,
                                       color=RED if row == 0 else BLUE, alpha=0.85))
        if row == 0:
            ax.text(-0.1, yb + 1.21, "fit", ha="right", va="center", fontsize=9, color=RED)
            note = "全 100 行で 1 回だけ fit" if k == 0 else "検証の行も fit に入っている"
            if k > 0:
                ax.add_patch(Rectangle(((k - 1) * 2.0, yb), 1.85, 1.37, fill=False,
                                       ec=RED, lw=2.2))
        else:
            ax.text(-0.1, yb + 1.21, "fit", ha="right", va="center", fontsize=9,
                    color=BLUE if k > 0 else GRAY)
            note = "まだ fit しない" if k == 0 else "fit は学習の 80 行だけ。検証の行は入らない"
        ax.text(10.1, yb + 2.15, note, ha="right", va="center", fontsize=9.5,
                color=RED if row == 0 else INK)
    foot = ("5 回とも、上は検証の行が fit に入り、下は入らない" if final else
            "fit で求めるもの: 標準化は列ごとの平均と標準偏差、列を選ぶ処理は正解と揃う 20 列")
    ax.text(-1.8, -1.05, foot, fontsize=10 if final else 9, color=INK, va="center")
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110, facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


frames = [fold_frame(k) for k in range(6)] + [fold_frame(5, final=True)]
frames[0].save(NOTE_DIR / "data-leakage_folds.webp", "WEBP", save_all=True,
               append_images=frames[1:], duration=[2000] + [1600] * 5 + [3500],
               loop=0, lossless=True, method=6)


# ============================================================
# 実験 2: 実データで、分割の前に標準化した時の差
# ============================================================
diffs = {}
for dname, loader in [("breast_cancer", load_breast_cancer), ("wine", load_wine)]:
    X, y = loader(return_X_y=True)
    for mname, model in [("ロジスティック回帰", LogisticRegression(max_iter=5000)),
                         ("kNN", KNeighborsClassifier())]:
        d = []
        for s in range(50):
            cv = StratifiedKFold(5, shuffle=True, random_state=s)
            wrong = cross_val_score(model, StandardScaler().fit_transform(X), y, cv=cv).mean()
            right = cross_val_score(make_pipeline(StandardScaler(), model), X, y, cv=cv).mean()
            d.append(wrong - right)
        d = np.array(d)
        diffs[f"{dname}\n{mname}"] = d
        print(f"{dname:<13} {mname:<9} 差の平均 {d.mean():+.4f}  最大の差 {np.abs(d).max():.4f}"
              f"  上がった回数 {(d > 0).sum()} / 下がった回数 {(d < 0).sum()}")

fig, ax = plt.subplots(figsize=(8.0, 3.4))
for i, (k, d) in enumerate(diffs.items()):
    jit = np.random.default_rng(i).uniform(-0.18, 0.18, len(d))
    ax.scatter(i + jit, d, s=12, color=RED, alpha=0.6)
    ax.plot([i - 0.28, i + 0.28], [d.mean()] * 2, color=INK, lw=1.6)
ax.axhline(0, color=GRAY, lw=0.8)
ax.set_xticks(range(len(diffs)))
ax.set_xticklabels(list(diffs), fontsize=9)
ax.set_ylim(-0.03, 0.03)
ax.set_ylabel("正解率の差\n（分割の前に標準化 − Pipeline）")
ax.set_title("50 通りの分け方での差。黒い横線は平均", fontsize=10)
fig.tight_layout()
save(fig, "data-leakage_scaler.webp")


# ============================================================
# 実験 3: 雑音の列の数と、分割の前に列を選んだ時の正解率
# ============================================================
P = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
sel = {p: [] for p in P}
for seed in range(10):
    X, y, _ = noise(seed, p=max(P))
    cv = StratifiedKFold(5, shuffle=True, random_state=seed)
    for p in P:
        Xs = SelectKBest(f_classif, k=20).fit_transform(X[:, :p], y)  # 全ての行で 20 列を選ぶ
        sel[p].append(cross_val_score(lr, Xs, y, cv=cv).mean())
print("雑音の列の数と、分割の前に 20 列を選んだ時の正解率（10 回の平均）")
for p in P:
    print(f"  {p:>5} 列: {np.mean(sel[p]):.3f}")

fig, ax = plt.subplots(figsize=(7.2, 3.6))
m = np.array([np.mean(sel[p]) for p in P])
lo = np.array([np.min(sel[p]) for p in P])
hi = np.array([np.max(sel[p]) for p in P])
ax.fill_between(P, lo, hi, color=RED, alpha=0.15, label="10 回の最小〜最大")
ax.plot(P, m, color=RED, marker="o", label="10 回の平均")
for p, v in zip(P, m):
    if p in (20, 100, 1000, 10000):
        ax.text(p, v + 0.035, f"{v:.2f}", color=RED, ha="center", fontsize=9)
ax.axhline(0.5, color=INK, lw=0.8, ls=":")
ax.set_xscale("log")
ax.set_ylim(0.35, 1.02)
ax.set_xlabel("候補の列の数（全て正解と無関係。行は 100）")
ax.set_ylabel("交差検証の正解率")
ax.set_title("全ての行で 20 列を選んでから交差検証した正解率", fontsize=10)
ax.legend(loc="upper left", fontsize=9, frameon=False)
fig.tight_layout()
save(fig, "data-leakage_select.webp")


# ============================================================
# 実験 4: 欠損値の割合と、正解の列も入れて補完した時の正解率
# ============================================================
MISS = [0.0, 0.2, 0.5, 0.8, 0.95]
imp = {m: [] for m in MISS}
for seed in range(10):
    X, y, rng = noise(seed, p=20)
    cv = StratifiedKFold(5, shuffle=True, random_state=seed)
    u = rng.random(X.shape)
    for miss in MISS:
        Xm = X.copy()
        Xm[u < miss] = np.nan
        Z = np.column_stack([Xm, y])                           # 正解を最後の列に足す
        Xi = IterativeImputer(random_state=0).fit_transform(Z)[:, :-1]
        imp[miss].append(cross_val_score(rf, Xi, y, cv=cv).mean())
print("欠損値の割合と、正解の列も入れて全ての行で補完した時の正解率（10 回の平均）")
for miss in MISS:
    print(f"  {miss:.0%}: {np.mean(imp[miss]):.3f}")

fig, ax = plt.subplots(figsize=(7.2, 3.6))
xs = [m * 100 for m in MISS]
m = np.array([np.mean(imp[k]) for k in MISS])
ax.fill_between(xs, [np.min(imp[k]) for k in MISS], [np.max(imp[k]) for k in MISS],
                color=RED, alpha=0.15, label="10 回の最小〜最大")
ax.plot(xs, m, color=RED, marker="o", label="10 回の平均")
for x, v in zip(xs, m):
    ax.text(x, v + 0.035, f"{v:.2f}", color=RED, ha="center", fontsize=9)
ax.axhline(0.5, color=INK, lw=0.8, ls=":")
ax.set_ylim(0.35, 1.02)
ax.set_xticks(xs)
ax.set_xticklabels([f"{x:.0f}%" for x in xs])
ax.set_xlabel("欠損値にした割合（20 列とも正解と無関係。行は 100）")
ax.set_ylabel("交差検証の正解率")
ax.set_title("正解の列も入れて全ての行で補完してから交差検証した正解率", fontsize=10)
ax.legend(loc="upper left", fontsize=9, frameon=False)
fig.tight_layout()
save(fig, "data-leakage_impute.webp")


# ============================================================
# 実験 5: Olivetti の同じ人の写真。分け方で 1 人あたりの正解の当たり方を見る
# ============================================================
rng = np.random.default_rng(0)
coin = rng.permutation(np.repeat([0, 1], 20))   # 40 人に 0 と 1 を半分ずつ配る
yf = coin[faces.target]                         # その人の写真 10 枚とも同じ正解
knn = KNeighborsClassifier(n_neighbors=1)
res = {}
for name, cv, groups in [("KFold(5, shuffle=True)", KFold(5, shuffle=True, random_state=0), None),
                         ("GroupKFold(5)、人ごと", GroupKFold(5), faces.target)]:
    acc, nn_same = [], []
    for tr, te in cv.split(faces.data, yf, groups):
        knn.fit(faces.data[tr], yf[tr])
        acc.append((knn.predict(faces.data[te]) == yf[te]).mean())
        nn = knn.kneighbors(faces.data[te], return_distance=False)[:, 0]  # 学習側で最も近い写真
        nn_same.append((faces.target[tr][nn] == faces.target[te]).mean())
    res[name] = (np.mean(nn_same), np.mean(acc))
    print(f"{name:<24} 正解率 {np.mean(acc):.3f}  最も近い写真が同じ人だった割合 {np.mean(nn_same):.2f}")

# 図: 1-NN が選んだ最も近い学習側の写真が同じ人だった割合と、正解率
fig, ax = plt.subplots(figsize=(7.0, 3.4))
w = 0.36
labels = ["KFold\n（写真ごとに分ける）", "GroupKFold\n（人ごとに分ける）"]
for i, (a, b) in enumerate(res.values()):
    ax.bar(i - w / 2, a, w, color=GRAY, label="最も近い写真が同じ人だった割合" if i == 0 else None)
    ax.bar(i + w / 2, b, w, color=RED if i == 0 else BLUE,
           label="正解率（写真ごと）" if i == 0 else "正解率（人ごと）")
    ax.text(i - w / 2, a + 0.02, f"{a:.2f}", ha="center", fontsize=9)
    ax.text(i + w / 2, b + 0.02, f"{b:.2f}", ha="center", fontsize=9)
ax.axhline(0.5, color=INK, lw=0.8, ls=":")
ax.set_xticks(range(len(res)))
ax.set_xticklabels(labels)
ax.set_ylim(0, 1.12)
ax.set_ylabel("割合・正解率")
ax.set_title("1 人ごとに配った 0 と 1 を、顔写真から 1-NN で当てる", fontsize=10)
ax.legend(loc="upper right", fontsize=8.5, frameon=False)
fig.tight_layout()
save(fig, "data-leakage_groups.webp")

# 正解を行ごとに並べ替えると、同じ人の行の正解がばらばらになり、KFold でも漏れが見えなくなる
perm = [cross_val_score(knn, faces.data, rng.permutation(yf),
                        cv=KFold(5, shuffle=True, random_state=0)).mean() for _ in range(3)]
print("正解を行ごとに並べ替えて KFold:", np.round(perm, 3))


# ============================================================
# 図: 解約の予測で、列ごとに値が確定した時刻と集計の期間の例（実験ではなく説明用）
# ============================================================
# 値は (名前, 期間の始め, 期間の終わり)。始めと終わりが同じ列は、1 時点で確定する値
cols = [("契約した月", -5.0, -5.0),
        ("先月の利用回数", -1.0, 0.0),
        ("直近 3 か月の問い合わせ回数", -3.0, 0.0),
        ("同じ列を表の作成日から数えた", -1.0, 2.0),
        ("解約の申し込み日", 0.8, 0.8),
        ("解約アンケートの回答", 1.6, 1.6)]
fig, ax = plt.subplots(figsize=(7.6, 3.4))
for i, (name, t0, t1) in enumerate(cols):
    yy = len(cols) - 1 - i
    ok = t1 <= 0
    c = BLUE if ok else RED
    if t1 > t0:
        ax.barh(yy, t1 - t0, left=t0, height=0.32, color=c, alpha=0.55, zorder=2)
    else:
        ax.scatter([t1], [yy], s=40, color=c, zorder=3)
    ax.text(t1 + 0.12, yy + 0.22, "使える" if ok else "使えない", fontsize=8.5, color=c)
ax.axvline(0, color=INK, lw=1.2)
ax.text(0.05, len(cols) - 0.35, "予測する時刻", fontsize=9, color=INK)
ax.set_yticks(range(len(cols)))
ax.set_yticklabels([c[0] for c in cols][::-1])
ax.set_xlim(-5.6, 2.9)
ax.set_ylim(-0.6, len(cols) - 0.1)
ax.set_xticks([-5, -4, -3, -2, -1, 0, 1, 2])
ax.set_xlabel("値が確定した時刻と、集計に含む期間（予測する時刻を 0 とした月）")
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0)
fig.tight_layout()
save(fig, "data-leakage_timing.webp")
