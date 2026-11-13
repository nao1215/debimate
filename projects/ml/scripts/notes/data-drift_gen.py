"""data-drift ノートの実験と図を生成するスクリプト。

本文に載せた実験（90 日分の監視、外挿するモデル、関係だけが変わる期間の予測スコア、
件数と列の数で変わるアラート、正例の割合だけが変わる時の補正、再学習の比較）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/data-drift_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、SciPy 1.18.1
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "mlops" / "data-drift"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"
SHADE = ["#ffffff", "#eef4f8", "#fbecec"]


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


# ============================================================
# 実験 1: 90 日分の監視（変化なし → 入力が動く → 関係が変わる）
# ============================================================
rng = np.random.default_rng(0)


def make_day(n, mean=(0.0, 0.0), w=(2.0, 2.0)):
    """x1, x2 は標準正規分布を mean だけずらしたもの。y=1 の確率は sigmoid(w1*x1 + w2*x2)"""
    X = rng.normal(size=(n, 2)) + np.array(mean)
    y = (rng.random(n) < sigmoid(X @ np.array(w))).astype(int)
    return X, y


def day_condition(day):
    if day < 30:
        return {}                      # 変化なし
    if day < 60:
        return {"mean": (1.0, 0.0)}    # 入力が動く: x1 の平均が 1 ずれる。y と x の関係は同じ
    return {"w": (2.0, 0.0)}           # 関係が変わる: 入力は学習時と同じ。x2 が y に効かなくなる


X_train, y_train = make_day(5000)
model = LogisticRegression().fit(X_train, y_train)

days = []
for day in range(90):
    X, y = make_day(1000, **day_condition(day))
    p_ks = [stats.ks_2samp(X_train[:, j], X[:, j]).pvalue for j in range(2)]
    score = model.predict_proba(X)[:, 1]
    days.append({"day": day + 1, "X": X, "y": y, "p_x1": p_ks[0], "p_x2": p_ks[1],
                 "score_mean": score.mean(), "acc": (model.predict(X) == y).mean()})

for lo, hi, name in [(0, 30, "変化なし"), (30, 60, "入力が動く"), (60, 90, "関係が変わる")]:
    part = days[lo:hi]
    alarm = sum(min(d["p_x1"], d["p_x2"]) < 0.05 for d in part)
    print(f"{lo + 1:2d}〜{hi:2d} 日目 {name:6s}: アラート {alarm:2d} / 30 日、"
          f"予測スコアの平均 {np.mean([d['score_mean'] for d in part]):.3f}、"
          f"正解率 {np.mean([d['acc'] for d in part]):.3f}")

fig, axes = plt.subplots(3, 1, figsize=(9, 6.6), sharex=True,
                         gridspec_kw={"height_ratios": [1.2, 0.8, 1.0]})
x = [d["day"] for d in days]
for ax in axes:
    for k, (lo, hi) in enumerate([(0.5, 30.5), (30.5, 60.5), (60.5, 90.5)]):
        ax.axvspan(lo, hi, color=SHADE[k], zorder=0)
ax = axes[0]
ax.plot(x, [max(d["p_x1"], 1e-30) for d in days], "o-", ms=2.5, lw=1, color=BLUE, label="x1")
ax.plot(x, [max(d["p_x2"], 1e-30) for d in days], "s-", ms=2.5, lw=1, color=GRAY, label="x2")
ax.axhline(0.05, color=RED, lw=1, ls="--")
quiet = [d for d in days[:30] if min(d["p_x1"], d["p_x2"]) < 0.05]
ax.plot([d["day"] for d in quiet], [min(d["p_x1"], d["p_x2"]) for d in quiet], "o", ms=7,
        mfc="none", mec=RED, mew=1.2)
ax.text(2, 1e-6, "点線 p = 0.05 より下の日にアラート", color=RED, fontsize=8.5)
ax.text(2, 1e-9, f"赤丸は 1〜30 日目に鳴った {len(quiet)} 日", color=RED, fontsize=8.5)
ax.set_yscale("log")
ax.set_ylim(1e-31, 3)
ax.set_ylabel("KS 検定の p 値")
ax.legend(loc="lower right", fontsize=8.5, ncol=2)
ax.set_title("入力のアラート（上）・予測スコアの平均（中）・正解率（下）", fontsize=10)
for k, (cx, name) in enumerate([(15.5, "変化なし"), (45.5, "入力が動く"), (75.5, "関係が変わる")]):
    ax.text(cx, 1e-16, name, ha="center", fontsize=10, color=[INK, "#3b6e8f", RED][k])
ax.text(45.5, 1e-31 * 30, "x1 の p 値は 1e-30 未満", ha="center", fontsize=8, color=INK)
ax = axes[1]
ax.plot(x, [d["score_mean"] for d in days], "o-", ms=2.5, lw=1, color=INK)
ax.set_ylim(0.4, 0.8)
ax.set_ylabel("予測スコア\nの平均")
ax = axes[2]
ax.plot(x, [d["acc"] for d in days], "o-", ms=2.5, lw=1, color=GREEN)
ax.set_ylim(0.6, 0.9)
ax.set_ylabel("正解率")
ax.set_xlabel("日")
for lo, hi in [(0, 30), (30, 60), (60, 90)]:
    m = np.mean([d["acc"] for d in days[lo:hi]])
    ax.hlines(m, lo + 1, hi, color=INK, lw=1, ls=":")
    ax.text((lo + hi) / 2 + 0.5, m + 0.03, f"平均 {m:.2f}", ha="center", fontsize=8.5)
fig.align_ylabels(axes)
save(fig, "data-drift_cover.webp")

# ============================================================
# 実験 2: 同じ入力の変化でも、外挿するモデルだけ精度が落ちる
# ============================================================
rng = np.random.default_rng(1)


def truth_logit(X):
    return 3 * (X[:, 1] - 0.5 * X[:, 0] ** 2 + 0.5)   # 境界は放物線 x2 = 0.5 * x1^2 - 0.5


def make_shift(n, shift):
    X = rng.normal(size=(n, 2))
    X[:, 0] += shift                                    # x1 だけ平均を shift ずらす
    y = (rng.random(n) < sigmoid(truth_logit(X))).astype(int)
    return X, y


X_tr, y_tr = make_shift(5000, 0.0)
linear = LogisticRegression().fit(X_tr, y_tr)
quad = make_pipeline(PolynomialFeatures(2), LogisticRegression(max_iter=1000)).fit(X_tr, y_tr)

shifts = np.round(np.arange(0, 2.51, 0.25), 2)
res = {"linear": [], "quad": [], "ks": []}
for s in shifts:
    X, y = make_shift(20000, s)
    res["linear"].append((linear.predict(X) == y).mean())
    res["quad"].append((quad.predict(X) == y).mean())
    res["ks"].append(stats.ks_2samp(X_tr[:, 0], X[:1000, 0]).pvalue)
    if s in (0.0, 1.0, 2.0):
        print(f"x1 のずれ {s:.1f}: KS の p 値 {res['ks'][-1]:.1e}  "
              f"線形 {res['linear'][-1]:.3f}  2 次の項あり {res['quad'][-1]:.3f}")

fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw={"width_ratios": [1, 1.15]})
ax = axes[0]
Xs, ys = make_shift(600, 2.0)
ax.scatter(X_tr[:600, 0], X_tr[:600, 1], s=6, color=BLUE, alpha=0.5, label="学習時")
ax.scatter(Xs[:, 0], Xs[:, 1], s=6, color=RED, alpha=0.5, label="x1 が 2 ずれた後")
g = np.linspace(-3, 5, 200)
ax.plot(g, 0.5 * g ** 2 - 0.5, color=INK, lw=1.5, label="本当の境界")
w, b = linear.coef_[0], linear.intercept_[0]
ax.plot(g, -(w[0] * g + b) / w[1], color=GRAY, lw=1.5, ls="--", label="線形モデルの境界")
ax.set_xlim(-3, 5)
ax.set_ylim(-3.5, 4)
ax.set_xlabel("x1")
ax.set_ylabel("x2")
ax.legend(fontsize=8, loc="upper left")
ax.set_title("学習時の範囲では、放物線の底を直線で近似できる", fontsize=10)
ax = axes[1]
ax.plot(shifts, res["linear"], "o-", color=GRAY, label="線形のロジスティック回帰")
ax.plot(shifts, res["quad"], "s-", color=GREEN, label="2 次の項を足したロジスティック回帰")
ax.set_xlabel("x1 の平均のずれ")
ax.set_ylabel("正解率")
ax.set_ylim(0.5, 1.0)
ax.legend(fontsize=8.5, loc="upper left")
ax.set_title("同じ入力の変化で、正解率が上がるモデルと下がるモデル", fontsize=10)
ax.text(0.0, 0.535, "KS 検定の p 値（2 つのモデルで共通）", fontsize=7.5, color=INK)
for s, p in zip(shifts, res["ks"]):
    if s in (0.5, 1.0, 2.0):
        ax.text(s, 0.51, f"{p:.0e}", ha="center", fontsize=7.5, color=INK)
save(fig, "data-drift_extrapolate.webp")

# ============================================================
# 実験 3: 関係が変わった期間の予測スコア（実験 1 のデータ）
# ============================================================
before = days[0:30]
after = days[60:90]
s_before = np.concatenate([model.predict_proba(d["X"])[:, 1] for d in before])
s_after = np.concatenate([model.predict_proba(d["X"])[:, 1] for d in after])
y_before = np.concatenate([d["y"] for d in before])
y_after = np.concatenate([d["y"] for d in after])
print(f"予測スコアの KS 検定（1〜30 日目と 61〜90 日目）: p = {stats.ks_2samp(s_before, s_after).pvalue:.2f}")
bins = np.linspace(0, 1, 11)
rate_b, rate_a = [], []
for lo, hi in zip(bins[:-1], bins[1:]):
    mb, ma = (s_before >= lo) & (s_before < hi), (s_after >= lo) & (s_after < hi)
    rate_b.append(y_before[mb].mean())
    rate_a.append(y_after[ma].mean())
print("予測スコア 0.9〜1.0 の実際の正例率:", f"{rate_b[-1]:.2f} → {rate_a[-1]:.2f}")
print("予測スコア 0.0〜0.1 の実際の正例率:", f"{rate_b[0]:.2f} → {rate_a[0]:.2f}")

fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
ax = axes[0]
ax.hist(s_before, bins=20, range=(0, 1), color=BLUE, alpha=0.6, label="1〜30 日目（変化なし）")
ax.hist(s_after, bins=20, range=(0, 1), histtype="step", lw=1.8, color=RED, label="61〜90 日目（関係が変わる）")
ax.set_xlabel("予測スコア（y=1 の予測確率）")
ax.set_ylabel("件数")
ax.legend(fontsize=8.5, loc="upper center")
ax.set_title("予測スコアの分布はほぼ重なる", fontsize=10)
ax = axes[1]
mid = (bins[:-1] + bins[1:]) / 2
ax.plot([0, 1], [0, 1], color=GRAY, lw=1, ls=":")
ax.plot(mid, rate_b, "o-", color=BLUE, label="1〜30 日目")
ax.plot(mid, rate_a, "s-", color=RED, label="61〜90 日目")
ax.set_xlabel("予測スコア（0.1 刻みの区間）")
ax.set_ylabel("実際に y=1 だった割合")
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.legend(fontsize=8.5, loc="upper left")
ax.set_title("同じスコアでも、当たる割合が違う", fontsize=10)
save(fig, "data-drift_concept.webp")

# ============================================================
# 実験 4: 件数と列の数で変わるアラート
# ============================================================
rng = np.random.default_rng(2)
sizes = [100, 300, 1000, 3000, 10000, 30000, 100000]
detect = {}
for shift in [0.0, 0.05, 0.15]:
    ks_rate, wd_rate = [], []
    for n in sizes:
        ks_hit = wd_hit = 0
        for _ in range(100):
            ref = rng.normal(size=n)
            cur = rng.normal(size=n) + shift          # 平均が標準偏差の shift 倍だけずれる
            ks_hit += stats.ks_2samp(ref, cur).pvalue < 0.05
            wd_hit += stats.wasserstein_distance(ref, cur) / np.std(ref) >= 0.1
        ks_rate.append(ks_hit / 100)
        wd_rate.append(wd_hit / 100)
    detect[shift] = (ks_rate, wd_rate)
    print(f"ずれ {shift:.2f}: KS でアラート {[round(float(r), 2) for r in ks_rate]}")
    print(f"           距離でアラート {[round(float(r), 2) for r in wd_rate]}")

cols, n_days = 50, 60
ref = rng.normal(size=(5000, cols))
raw, bonf = [], []
for _ in range(n_days):
    cur = rng.normal(size=(1000, cols))               # 50 列とも分布は変わらない
    p = np.array([stats.ks_2samp(ref[:, j], cur[:, j]).pvalue for j in range(cols)])
    raw.append((p < 0.05).sum())
    bonf.append((p < 0.05 / cols).sum())
raw, bonf = np.array(raw), np.array(bonf)
print(f"50 列・60 日: 1 列でもアラートが出た日 {np.sum(raw > 0)} / 60（p < 0.05）、"
      f"{np.sum(bonf > 0)} / 60（p < 0.05 / 50）。1 日あたりのアラートの平均 {raw.mean():.1f} 列")

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0), gridspec_kw={"width_ratios": [1.25, 1]})
ax = axes[0]
for shift, color in [(0.0, GRAY), (0.05, BLUE), (0.15, RED)]:
    ks_rate, wd_rate = detect[shift]
    ax.plot(sizes, ks_rate, "o-", color=color)
    ax.plot(sizes, wd_rate, "s--", color=color)
ax.set_xscale("log")
ax.set_xlabel("比べる件数（基準と今日で同じ件数）")
ax.set_ylabel("100 回のうちアラートが出た割合")
ax.set_ylim(-0.03, 1.05)
from matplotlib.lines import Line2D
handles = [Line2D([], [], color=INK, marker="o", ls="-", label="KS 検定 p < 0.05"),
           Line2D([], [], color=INK, marker="s", ls="--", label="距離 ≥ 0.1")]
handles += [Line2D([], [], color=c, lw=4, label=f"ずれ {sh}") for sh, c in [(0.0, GRAY), (0.05, BLUE), (0.15, RED)]]
ax.legend(handles=handles, fontsize=8, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.17),
          frameon=False, columnspacing=1.0, handlelength=2.2)
ax.set_title("KS 検定は件数が多いと、距離は件数が少ないと鳴りやすい", fontsize=10)
ax = axes[1]
ax.bar(np.arange(1, n_days + 1), raw, color=BLUE, width=0.8, label="p < 0.05")
ax.bar(np.arange(1, n_days + 1), bonf, color=RED, width=0.8, label="p < 0.05 / 50")
ax.set_xlabel("日")
ax.set_ylabel("アラートが出た列の数")
ax.legend(fontsize=8.5, loc="upper right")
ax.set_title("分布が変わらない 50 列を毎日検定する", fontsize=10)
fig.subplots_adjust(wspace=0.28)
save(fig, "data-drift_alarm.webp")

# ============================================================
# 実験 5: 正例の割合だけが変わる（P(x|y) は同じ）
# ============================================================
rng = np.random.default_rng(3)


def make_label(n, prior):
    y = (rng.random(n) < prior).astype(int)
    X = rng.normal(size=(n, 2)) + np.where(y[:, None] == 1, 1.0, 0.0)   # y=1 は平均 (1, 1)
    return X, y


prior_train = 0.1
X_l, y_l = make_label(20000, prior_train)
clf = LogisticRegression().fit(X_l, y_l)
rows = []
for prior in [0.1, 0.3, 0.5]:
    X, y = make_label(20000, prior)
    p = clf.predict_proba(X)[:, 1]
    q = prior_train                                   # 正解を使わずに今の正例率を推定する（EM）
    for _ in range(100):
        a = p * q / prior_train
        b = (1 - p) * (1 - q) / (1 - prior_train)
        q = np.mean(a / (a + b))
    a = p * q / prior_train
    b = (1 - p) * (1 - q) / (1 - prior_train)
    p_adj = a / (a + b)                               # 推定した正例率で予測確率を補正
    recall = lambda s: ((s > 0.5) & (y == 1)).sum() / (y == 1).sum()
    rows.append((prior, q, ((p > 0.5) == y).mean(), ((p_adj > 0.5) == y).mean(), recall(p), recall(p_adj)))
    print(f"正例率 {prior:.1f}: 推定 {q:.3f}  正解率 {rows[-1][2]:.3f} → {rows[-1][3]:.3f}  "
          f"再現率 {rows[-1][4]:.3f} → {rows[-1][5]:.3f}  "
          f"KS の p 値（x1）{stats.ks_2samp(X_l[:1000, 0], X[:1000, 0]).pvalue:.1e}")

fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
labels = [f"{r[0]:.1f}\n（推定 {r[1]:.2f}）" for r in rows]
idx = np.arange(len(rows))
for ax, k0, k1, title in [(axes[0], 2, 3, "正解率"), (axes[1], 4, 5, "再現率（y=1 を見つけた割合）")]:
    ax.bar(idx - 0.18, [r[k0] for r in rows], width=0.36, color=GRAY, label="そのまま")
    ax.bar(idx + 0.18, [r[k1] for r in rows], width=0.36, color=GREEN, label="推定した正例率で補正")
    for i, r in enumerate(rows):
        ax.text(i - 0.18, r[k0] + 0.02, f"{r[k0]:.2f}", ha="center", fontsize=8)
        ax.text(i + 0.18, r[k1] + 0.02, f"{r[k1]:.2f}", ha="center", fontsize=8)
    ax.set_xticks(idx, labels)
    ax.set_xlabel("本番の正例率（学習時は 0.1）")
    ax.set_ylim(0, 1.08)
    ax.set_title(title, fontsize=10)
axes[0].legend(fontsize=8.5, loc="lower left")
save(fig, "data-drift_label.webp")

# ============================================================
# 実験 6: 再学習で戻るもの、戻らないもの（実験 1 のデータ、正解は 7 日遅れで届く）
# ============================================================
DELAY, WINDOW = 7, 14
acc = {"fixed": [], "window": [], "all": []}
for t in range(30, 90):                               # 31〜90 日目
    known = range(0, t - DELAY + 1)                   # 正解が揃っている日（7 日前まで）
    Xw = np.vstack([days[k]["X"] for k in known][-WINDOW:])
    yw = np.concatenate([days[k]["y"] for k in known][-WINDOW:])
    Xa = np.vstack([X_train] + [days[k]["X"] for k in known])
    ya = np.concatenate([y_train] + [days[k]["y"] for k in known])
    X, y = days[t]["X"], days[t]["y"]
    acc["fixed"].append((model.predict(X) == y).mean())
    acc["window"].append((LogisticRegression().fit(Xw, yw).predict(X) == y).mean())
    acc["all"].append((LogisticRegression().fit(Xa, ya).predict(X) == y).mean())
for name, key in [("固定", "fixed"), ("直近 14 日で再学習", "window"), ("全期間で再学習", "all")]:
    a = np.array(acc[key])
    print(f"{name:10s}: 31〜60 日目 {a[:30].mean():.3f}  61〜67 日目 {a[30:37].mean():.3f}  "
          f"75〜90 日目 {a[44:].mean():.3f}")

fig, ax = plt.subplots(figsize=(9, 3.8))
xs = np.arange(31, 91)
ax.axvspan(30.5, 60.5, color=SHADE[1], zorder=0)
ax.axvspan(60.5, 90.5, color=SHADE[2], zorder=0)
ax.plot(xs, acc["fixed"], "o-", ms=2.5, lw=1, color=GRAY, label="固定（学習時のまま）")
ax.plot(xs, acc["all"], "^-", ms=2.5, lw=1, color=BLUE, label="毎日、全期間で再学習")
ax.plot(xs, acc["window"], "s-", ms=2.5, lw=1, color=GREEN, label="毎日、直近 14 日分で再学習")
ax.axvline(60.5 + DELAY, color=RED, lw=1, ls="--")
ax.text(60.5 + DELAY + 0.5, 0.885, "変わった日の正解が届く", color=RED, fontsize=8.5)
ax.text(45.5, 0.60, "入力が動く", ha="center", fontsize=10, color="#3b6e8f")
ax.text(75.5, 0.60, "関係が変わる", ha="center", fontsize=10, color=RED)
ax.set_ylim(0.58, 0.9)
ax.set_xlabel("日")
ax.set_ylabel("正解率")
ax.legend(fontsize=8.5, loc="lower left", bbox_to_anchor=(0.0, 0.08))
ax.set_title("正解が 7 日遅れで届く時の、再学習のやり方ごとの正解率", fontsize=10)
save(fig, "data-drift_retrain.webp")
