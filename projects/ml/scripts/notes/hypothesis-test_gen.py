"""hypothesis-test ノートの実験と図を生成するスクリプト。

本文に載せた実験（差の無い A/B テストを毎日検定する、p 値を裾の面積で表す図、p 値の分布、有意になった施策の内訳、
見る回数と誤りの割合、検定力、z と t の信頼区間、交差検証のスコアの t 検定）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/hypothesis-test_gen.py
確認した版: NumPy 2.5.4、SciPy 1.18.1、scikit-learn 1.9.1
表紙の動く図は、28 日を 1 日 0.4 秒ずつで再生し、最後のコマで 3 秒止める。
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "hypothesis-test"
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
# 実験 1: 差の無い A/B テストを毎日検定する
# ============================================================
DAYS, PER_DAY = 28, 1000          # 28 日、1 日に 1 つのモデルあたり 1000 人


def ab_test(rate_a, rate_b, n_exp, rng):
    """n_exp 本の A/B テストを作り、各日までの累計で 2 群の割合の z 検定をした p 値を返す。"""
    a = rng.binomial(PER_DAY, rate_a, size=(n_exp, DAYS)).cumsum(axis=1)  # A をクリックした累計
    b = rng.binomial(PER_DAY, rate_b, size=(n_exp, DAYS)).cumsum(axis=1)
    n = PER_DAY * np.arange(1, DAYS + 1)                                   # 各日までの累計人数
    pooled = (a + b) / (2 * n)                                             # 差が無いとした時のクリック率
    se = np.sqrt(pooled * (1 - pooled) * 2 / n)
    z = (b / n - a / n) / se
    return 2 * stats.norm.sf(np.abs(z))                                    # 両側の p 値


rng = np.random.default_rng(0)
p_null = ab_test(0.05, 0.05, 10000, rng)    # 2 つともクリック率 5%
fixed = (p_null[:, -1] < 0.05).mean()       # 28 日目に 1 回だけ検定
peek = (p_null < 0.05).any(axis=1).mean()   # 毎日見て、一度でも 0.05 を下回ったら止める
print(f"28 日目に 1 回だけ検定: {fixed:.1%}")
print(f"毎日見て、0.05 を下回った日に止める: {peek:.1%}")
crossed_any = (p_null < 0.05).any(axis=1)
back = np.mean(p_null[crossed_any, -1] >= 0.05)
print(f"途中で 0.05 を下回った実験のうち、28 日目には 0.05 以上に戻っていた割合: {back:.1%}")
first_day = np.where((p_null < 0.05).any(axis=1), (p_null < 0.05).argmax(axis=1) + 1, 0)

# 表紙の動く図: 先頭 20 本の p 値の推移
W, H, S = 900, 560, 2
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
f_title = ImageFont.truetype(FONT, 22 * S, index=0)
f_mid = ImageFont.truetype(FONT, 17 * S, index=0)
f_small = ImageFont.truetype(FONT, 14 * S, index=0)
L, R, T, B = 90, 640, 120, 500                     # 描画の枠（縮める前の座標 / S）
YMIN, YMAX = -2.3, 0.0                             # p 値の log10


def xy(day, p):
    x = L + (R - L) * (day - 1) / (DAYS - 1)
    y = T + (B - T) * (YMAX - np.log10(max(p, 10**YMIN))) / (YMAX - YMIN)
    return x * S, y * S


def frame(day):
    im = Image.new("RGB", (W * S, H * S), "#ffffff")
    d = ImageDraw.Draw(im)
    d.text((30 * S, 18 * S), "差の無い 2 つのモデルを、毎日 p 値で比べる（20 本の A/B テスト）",
           font=f_title, fill=INK)
    # 経過日数の帯
    d.text((30 * S, 62 * S), f"経過 {day:2d} / 28 日", font=f_mid, fill=INK)
    d.rectangle([200 * S, 70 * S, 640 * S, 82 * S], outline=GRAY, width=S)
    d.rectangle([200 * S, 70 * S, (200 + 440 * day / DAYS) * S, 82 * S], fill=BLUE)
    # 軸
    for p_tick, lab in [(1, "1"), (0.1, "0.1"), (0.01, "0.01")]:
        _, y = xy(1, p_tick)
        d.line([L * S, y, R * S, y], fill="#e6e6e6", width=S)
        d.text((L * S - 70 * S, y - 10 * S), lab, font=f_small, fill=INK)
    _, y05 = xy(1, 0.05)
    for x0 in range(L, R, 12):
        d.line([x0 * S, y05, (x0 + 6) * S, y05], fill=RED, width=2 * S)
    d.text((R * S + 6 * S, y05 - 11 * S), "0.05", font=f_small, fill=RED)
    for dd in (1, 7, 14, 21, 28):
        x, _ = xy(dd, 1)
        d.text((x - 8 * S, (B + 8) * S), f"{dd}", font=f_small, fill=INK)
    d.text(((L + R) / 2 * S - 30 * S, (B + 30) * S), "経過日数", font=f_small, fill=INK)
    d.text((10 * S, (T - 32) * S), "p 値（対数）", font=f_small, fill=INK)
    # 20 本の線
    crossed = 0
    for i in range(20):
        hit = 0 < first_day[i] <= day
        crossed += hit
        pts = [xy(k + 1, p_null[i, k]) for k in range(day)]
        color = RED if hit else "#b8b8b8"
        if len(pts) > 1:
            d.line(pts, fill=color, width=2 * S)
        if hit:
            cx, cy = xy(first_day[i], p_null[i, first_day[i] - 1])
            d.ellipse([cx - 5 * S, cy - 5 * S, cx + 5 * S, cy + 5 * S], fill=RED)
    # 右の数字
    rate = ((first_day > 0) & (first_day <= day)).mean()
    d.text((665 * S, 150 * S), "一度でも 0.05 を", font=f_mid, fill=INK)
    d.text((665 * S, 175 * S), "下回った実験", font=f_mid, fill=INK)
    d.text((665 * S, 210 * S), f"図の 20 本: {crossed:2d} 本", font=f_mid, fill=RED)
    d.text((665 * S, 245 * S), f"10000 本: {rate:5.1%}", font=f_mid, fill=RED)
    d.text((665 * S, 385 * S), "28 日目に 1 回だけ", font=f_mid, fill=INK)
    d.text((665 * S, 410 * S), "検定した場合", font=f_mid, fill=INK)
    if day == DAYS:
        d.text((665 * S, 445 * S), f"10000 本: {fixed:5.1%}", font=f_mid, fill=BLUE)
    d.text((665 * S, 515 * S), "1 日を 0.4 秒ずつ再生", font=f_small, fill=GRAY)
    return im.resize((W, H), Image.LANCZOS)


frames = [frame(k) for k in range(1, DAYS + 1)]
durations = [400] * (DAYS - 1) + [3000]
frames[0].save(NOTE_DIR / "hypo_peeking.webp", "WEBP", save_all=True, append_images=frames[1:],
               duration=durations, loop=0, quality=80, method=6)

# 差が無い時の z の分布と、手元の z の両側の裾（p 値は面積）
idx = int(np.argmax((p_null[:, -1] > 0.1) & (p_null[:, -1] < 0.3)))  # 図に使う 1 本
z_obs = stats.norm.isf(p_null[idx, -1] / 2)
print(f"面積の図に使った実験: {idx} 本目  28 日目の |z| = {z_obs:.2f}  p = {p_null[idx, -1]:.3f}")
fig, ax = plt.subplots(figsize=(7, 3))
zz = np.linspace(-4, 4, 400)
ax.plot(zz, stats.norm.pdf(zz), color=INK, lw=1.2)
for side in (zz <= -z_obs, zz >= z_obs):
    ax.fill_between(zz[side], stats.norm.pdf(zz[side]), color=RED, alpha=0.55, lw=0)
for v in (-z_obs, z_obs):
    ax.axvline(v, color=RED, lw=1)
ax.text(z_obs + 0.1, 0.30, f"手元の z = {z_obs:.2f}", color=RED, fontsize=9)
ax.text(-z_obs - 0.1, 0.30, f"-{z_obs:.2f}", color=RED, fontsize=9, ha="right")
ax.annotate(f"両側の赤い面積の合計 = p 値 {p_null[idx, -1]:.3f}", xy=(z_obs + 0.5, 0.03),
            xytext=(1.9, 0.17), fontsize=9, color=RED, arrowprops=dict(arrowstyle="->", color=RED))
ax.set_xlabel("差が無い時の z（平均 0、標準偏差 1 の正規分布）")
ax.set_ylabel("出やすさ（確率密度）")
ax.set_ylim(0, 0.43)
save(fig, "hypo_z_area.webp")

# ============================================================
# 実験 2: 差が無い時と、ある時の p 値の分布
# ============================================================
p_lift = ab_test(0.05, 0.055, 10000, rng)   # B のクリック率が 5.5%（1 割増し）
for name, p in [("差が無い", p_null[:, -1]), ("B が 1 割高い", p_lift[:, -1])]:
    counts, _ = np.histogram(p, bins=20, range=(0, 1))
    print(f"{name}: p < 0.05 の割合 {np.mean(p < 0.05):.1%}  0.05 刻みの件数 {counts[:4]} ...")

fig, axes = plt.subplots(1, 2, figsize=(8, 3), sharey=True)
for ax, p, title, color in [(axes[0], p_null[:, -1], "差が無い（A も B も 5%）", GRAY),
                            (axes[1], p_lift[:, -1], "差がある（A は 5%、B は 5.5%）", BLUE)]:
    n_, bins, patches = ax.hist(p, bins=20, range=(0, 1), color=color, edgecolor="#ffffff")
    patches[0].set_facecolor(RED)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("28 日目の p 値")
    ax.text(0.1, 7000, f"p < 0.05 の割合: {np.mean(p < 0.05):.1%}", color=RED, fontsize=9.5)
axes[0].set_ylabel("実験の数（10000 本のうち）")
save(fig, "hypo_pvalue_hist.webp")

# ============================================================
# 実験 3: 有意になった施策のうち、差が無かったもの
# ============================================================
rate_null = (p_null[:, -1] < 0.05).mean()     # 差が無い施策が有意になる割合（10000 本から）
rate_true = (p_lift[:, -1] < 0.05).mean()     # 1 割増しの施策が有意になる割合
n_null_sig = round(900 * rate_null)           # 900 本は差が無い施策
n_true_sig = round(100 * rate_true)           # 100 本は 1 割増しの施策
print(f"有意になった施策: {n_null_sig + n_true_sig} 本（差が無い {n_null_sig} 本、差がある {n_true_sig} 本）")
print(f"有意のうち差が無かった割合: {n_null_sig / (n_null_sig + n_true_sig):.1%}")

fig, ax = plt.subplots(figsize=(8, 3.3))
cells = ([RED] * n_null_sig + ["#f2c4c5"] * (900 - n_null_sig)
         + [BLUE] * n_true_sig + ["#cfe0ea"] * (100 - n_true_sig))
for i, c in enumerate(cells):
    ax.add_patch(plt.Rectangle((i // 20, 19 - i % 20), 0.85, 0.85, color=c))
ax.set_xlim(-0.5, 50.5)
ax.set_ylim(-0.5, 20.5)
ax.set_aspect("equal")
ax.axis("off")
ax.axvline(45 - 0.08, color=INK, lw=1)
ax.text(22.5, 21, "差が無い 900 本", ha="center", fontsize=9.5)
ax.text(47.5, 21, "差がある 100 本", ha="center", fontsize=9.5)
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (RED, "#f2c4c5", BLUE, "#cfe0ea")]
ax.legend(handles, [f"差が無いのに有意（{n_null_sig}）", "差が無く、有意でない",
                    f"差があり有意（{n_true_sig}）", "差があるのに有意でない"],
          loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=4, fontsize=8.5, frameon=False)
save(fig, "hypo_base_rate.webp")

# ============================================================
# 実験 4: 見る回数と、差が無いのに有意になる割合
# ============================================================
looks_list = [1, 2, 4, 7, 14, 28]
naive, bonf = [], []
for looks in looks_list:
    days = np.linspace(DAYS / looks, DAYS, looks).round().astype(int) - 1  # 見る日（等間隔）
    naive.append((p_null[:, days] < 0.05).any(axis=1).mean())
    bonf.append((p_null[:, days] < 0.05 / looks).any(axis=1).mean())    # 見る回数で 0.05 を割る
    print(f"{looks:2d} 回見る: 0.05 のまま {naive[-1]:.1%}  0.05/{looks} にする {bonf[-1]:.1%}")
for name, days, alpha in [("28 日目に 1 回", [27], 0.05), ("毎日 0.05", range(28), 0.05),
                          ("毎日 0.05/28", range(28), 0.05 / 28),
                          ("週 1 回 0.05/4", [6, 13, 20, 27], 0.05 / 4)]:
    days = list(days)
    print(f"{name}: 差が無い時 {(p_null[:, days] < alpha).any(axis=1).mean():.1%}"
          f"  B が 1 割高い時 {(p_lift[:, days] < alpha).any(axis=1).mean():.1%}")

fig, ax = plt.subplots(figsize=(7, 3.2))
x = np.arange(len(looks_list))
ax.bar(x - 0.2, naive, 0.4, color=RED, label="毎回 0.05 と比べる")
ax.bar(x + 0.2, bonf, 0.4, color=BLUE, label="0.05 を見る回数で割る")
for i in range(len(x)):
    ax.text(x[i] - 0.2, naive[i] + 0.005, f"{naive[i]:.1%}", ha="center", fontsize=8)
    ax.text(x[i] + 0.2, bonf[i] + 0.005, f"{bonf[i]:.1%}", ha="center", fontsize=8,
            bbox=dict(facecolor="#ffffff", edgecolor="none", pad=0.6))
ax.axhline(0.05, color=INK, ls="--", lw=0.8, zorder=0)
ax.text(5.55, 0.055, "5%", fontsize=8.5)
ax.set_xticks(x, [f"{n} 回" for n in looks_list])
ax.set_xlabel("28 日のうち、p 値を見る回数（等間隔）")
ax.set_ylabel("差が無いのに有意になる割合")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.legend(fontsize=8.5, frameon=False, loc="upper left")
save(fig, "hypo_looks.webp")

# ============================================================
# 実験 5: 差があるのに有意にならない割合（検定力）
# ============================================================
day_axis = np.arange(1, 57)
fig, ax = plt.subplots(figsize=(7, 3.2))
for rate_b, color in [(0.06, GREEN), (0.055, BLUE), (0.0525, RED)]:
    n = PER_DAY * day_axis
    se = np.sqrt((0.05 * 0.95 + rate_b * (1 - rate_b)) / n)
    shift = (rate_b - 0.05) / se
    power = stats.norm.sf(1.96 - shift) + stats.norm.cdf(-1.96 - shift)
    lift = round((rate_b / 0.05 - 1) * 100)
    ax.plot(day_axis, power, color=color, label=f"B が {rate_b:.2%}（{lift}% 増し）")
    reach = f"{day_axis[np.argmax(power >= 0.8)]} 日目" if (power >= 0.8).any() else "56 日では届かない"
    print(f"B が {rate_b:.2%}: 28 日目の検定力 {power[27]:.1%}  80% に届く日 {reach}")
sim = (p_lift[:, -1] < 0.05).mean()
ax.plot(28, sim, "o", color=BLUE, ms=5)
ax.text(29, sim - 0.07, f"シミュレーション {sim:.1%}", fontsize=8.5, color=BLUE)
ax.axhline(0.8, color=INK, ls="--", lw=0.8)
ax.axvline(28, color=GRAY, ls=":", lw=0.8)
ax.set_xlabel("経過日数（1 日に 1 つのモデルあたり 1000 人）")
ax.set_ylabel("検定力（有意になる割合）")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.legend(fontsize=8.5, frameon=False, loc="lower right")
save(fig, "hypo_power.webp")

# ============================================================
# 実験 6: σ の代わりに s を使った区間（z と t）
# ============================================================
ns = [3, 4, 5, 7, 10, 15, 20, 30, 50]
cover_z, cover_t = [], []
for n in ns:
    x = rng.normal(size=(20000, n))            # 真の平均は 0
    m, s = x.mean(axis=1), x.std(axis=1, ddof=1)
    half_z = 1.96 * s / np.sqrt(n)
    half_t = stats.t.ppf(0.975, n - 1) * s / np.sqrt(n)
    cover_z.append(np.mean(np.abs(m) <= half_z))
    cover_t.append(np.mean(np.abs(m) <= half_t))
    print(f"n={n:2d}: 1.96 を使う {cover_z[-1]:.1%}  t 分布の {stats.t.ppf(0.975, n - 1):.2f} を使う {cover_t[-1]:.1%}")

fig, ax = plt.subplots(figsize=(7, 3.2))
ax.plot(ns, cover_z, "o-", color=RED, label=r"平均 ± 1.96 × $s\,/\sqrt{n}$")
ax.plot(ns, cover_t, "o-", color=BLUE, label=r"平均 ± t × $s\,/\sqrt{n}$（自由度 n - 1）")
ax.axhline(0.95, color=INK, ls="--", lw=0.8)
ax.text(1.01, 0.95, "95%", transform=ax.get_yaxis_transform(), fontsize=8.5, va="center")
for n, cz in zip(ns[:3], cover_z[:3]):
    ax.text(n * 1.06, cz, f"{cz:.1%}", fontsize=8.5, color=RED, va="center")
ax.set_xscale("log")
ax.set_xticks(ns, [str(n) for n in ns])
ax.set_xticks([], minor=True)
ax.set_xlabel("件数 n（正規分布から取る）")
ax.set_ylabel("区間が真の平均を含んだ割合")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.legend(fontsize=8.5, frameon=False, loc="lower right")
save(fig, "hypo_t_vs_z.webp")

# 区間と検定の対応: 0 が 95% 区間の外 ⇔ p < 0.05
x = rng.normal(loc=0.3, size=(10000, 10))
m, s = x.mean(axis=1), x.std(axis=1, ddof=1)
half = stats.t.ppf(0.975, 9) * s / np.sqrt(10)
outside = np.abs(m) > half
p = stats.ttest_1samp(x, 0, axis=1).pvalue
print(f"0 が区間の外と p < 0.05 が一致した回数: {np.sum(outside == (p < 0.05))} / 10000")

# ============================================================
# 実験 7: 交差検証のスコアの差を t 検定する
# ============================================================
N_ROWS, N_DATA, K = 200, 300, 10


def make_data(rng):
    """10 列のうち 0〜2 列目と 5〜7 列目が同じ強さで y に効く。前半と後半は対称。"""
    X = rng.normal(size=(N_ROWS, 10))
    logit = X[:, [0, 1, 2]].sum(axis=1) + X[:, [5, 6, 7]].sum(axis=1)
    y = (rng.random(N_ROWS) < 1 / (1 + np.exp(-logit))).astype(int)
    return X, y


p_cv = {"100 個に t 検定": [], "補正した t 検定": [], "10 分割 1 回の 10 個に t 検定": []}
for r in range(N_DATA):
    X, y = make_data(rng)
    cv = RepeatedStratifiedKFold(n_splits=K, n_repeats=10, random_state=r)
    acc_a = cross_val_score(LogisticRegression(), X[:, :5], y, cv=cv)  # モデル A は前半の 5 列
    acc_b = cross_val_score(LogisticRegression(), X[:, 5:], y, cv=cv)  # モデル B は後半の 5 列
    diff = acc_a - acc_b                                               # 100 個の差
    p_cv["100 個に t 検定"].append(stats.ttest_1samp(diff, 0).pvalue)
    p_cv["10 分割 1 回の 10 個に t 検定"].append(stats.ttest_1samp(diff[:K], 0).pvalue)
    n_train, n_test = N_ROWS * (K - 1) // K, N_ROWS // K
    var = np.var(diff, ddof=1) * (1 / len(diff) + n_test / n_train)  # Nadeau と Bengio の補正
    t = diff.mean() / np.sqrt(var)
    p_cv["補正した t 検定"].append(2 * stats.t.sf(abs(t), len(diff) - 1))
for name, ps in p_cv.items():
    print(f"{name}: 差が無いのに p < 0.05 になった割合 {np.mean(np.array(ps) < 0.05):.1%}")

fig, ax = plt.subplots(figsize=(7, 2.8))
names = ["10 分割 × 10 回の\n100 個に t 検定", "100 個に\n補正した t 検定", "10 分割 1 回の\n10 個に t 検定"]
vals = [np.mean(np.array(p_cv[k]) < 0.05) for k in ["100 個に t 検定", "補正した t 検定", "10 分割 1 回の 10 個に t 検定"]]
ax.barh(names[::-1], vals[::-1], color=[BLUE, BLUE, RED], height=0.55)
for i, v in enumerate(vals[::-1]):
    ax.text(v + 0.01, i, f"{v:.1%}", va="center", fontsize=9)
ax.axvline(0.05, color=INK, ls="--", lw=0.8)
ax.text(0.055, 2.38, "5%", fontsize=8.5)
ax.set_xlim(0, 0.75)
ax.set_xlabel("差の無い 2 つのモデルで p < 0.05 になった割合（300 個のデータセット）")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
save(fig, "hypo_cv.webp")
