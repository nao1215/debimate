"""model-performance-monitoring ノートの実験と図を生成するスクリプト。

本文に載せた実験（elec2 の週ごとの正解率と確信度、価格の区間ごとの UP の割合、
ラベル無しで見られる信号とアラートの数、日ごとの正解率の揺れ、正解ラベルが遅れて届く時の見え方）を
同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
elec2 は OpenML（data_id=151）から 1 回だけ取得し、scikit-learn のキャッシュに置く。
実行: cd projects/ml && .venv/bin/python scripts/notes/model-performance-monitoring_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、pandas 3.1.1、SciPy 1.18.1、matplotlib 3.11.2
動く図は 1 週を 0.16 秒ずつ表示する（実時間ではなく、週を単位にした再生）。
"""
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.stats import binom
from sklearn.datasets import fetch_openml
from sklearn.ensemble import HistGradientBoostingClassifier

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "mlops" / "model-performance-monitoring"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"
DARKBLUE = "#3d6f8e"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


def week_date(w):
    return date(1996, 5, 7) + timedelta(days=7 * int(w))


# ============================================================
# 実験 1: 半年分で学習したモデルを、残りの 2 年で週ごとに評価する
# ============================================================
frame = fetch_openml(data_id=151, as_frame=True, parser="liac-arff").frame
frame["day"] = frame["day"].astype(int)
cols = ["day", "period", "nswprice", "nswdemand"]
X = frame[cols].to_numpy()
y = (frame["class"] == "UP").to_numpy().astype(int)  # 直近 24 時間の平均より上がったら UP
week = np.arange(len(frame)) // (48 * 7)              # 30 分ごとに 1 行、1 週は 336 行

train = week < 22                                     # 1996-05-07 からの 22 週で学習
valid = (week >= 22) & (week < 26)                    # 続く 4 週で検証
model = HistGradientBoostingClassifier(random_state=0).fit(X[train], y[train])

p_up = model.predict_proba(X)[:, 1]
pred_up = p_up > 0.5
conf = np.maximum(p_up, 1 - p_up)                     # 予測したクラスの確率 = 確信度
correct = pred_up == y
print(f"検証の 4 週: 正解率 {correct[valid].mean():.3f}  平均確信度 {conf[valid].mean():.3f}")

weeks = np.arange(26, week.max() + 1)
acc_w = np.array([correct[week == w].mean() for w in weeks])
conf_w = np.array([conf[week == w].mean() for w in weeks])
print(f"運用の {len(weeks)} 週: 正解率と確信度の相関 {np.corrcoef(acc_w, conf_w)[0, 1]:.2f}")
i = np.argmin(acc_w)
print(f"正解率が最も低い週: 第 {weeks[i]} 週（{week_date(weeks[i])}） 正解率 {acc_w[i]:.3f}  確信度 {conf_w[i]:.3f}")
print(f"正解率 0.70 未満の週: {np.sum(acc_w < 0.70)} / {len(weeks)}  平均確信度 0.70 未満の週: {np.sum(conf_w < 0.70)}")

# ============================================================
# 実験 2: 学習時の価格の 10 分位ごとに、UP の割合を比べる
# ============================================================
test = week >= 26                                     # 運用の 109 週
edges = np.quantile(X[train, 2], np.linspace(0, 1, 11))  # 学習した期間の価格で 10 等分
bin_of = np.clip(np.searchsorted(edges, X[:, 2], side="right") - 1, 0, 9)
rows = []
for k in range(10):
    tr_k, te_k = train & (bin_of == k), test & (bin_of == k)
    rows.append((y[tr_k].mean(), y[te_k].mean(), pred_up[te_k].mean(), te_k.sum() / test.sum()))
    print(f"区間 {k + 1:>2}: 学習 UP {rows[-1][0]:.2f}  運用 UP {rows[-1][1]:.2f}"
          f"  予測 UP {rows[-1][2]:.2f}  運用の行の割合 {rows[-1][3]:.2f}")
bins = np.array(rows)
print(f"価格の中央値: 学習 {np.median(X[train, 2]):.4f}  運用 {np.median(X[test, 2]):.4f}")
hi = conf > 0.99
print(f"確信度 0.99 を超える行: 検証 {hi[valid].mean():.2f}  運用 {hi[test].mean():.2f}"
      f"  運用での正解率 {correct[test & hi].mean():.3f}")
band = np.digitize(conf, [0.6, 0.7, 0.8, 0.9, 0.95, 0.99])  # 確信度を 7 つの帯に分ける
gap = [abs(conf[valid & (band == b)].mean() - correct[valid & (band == b)].mean()) for b in range(7)]
print(f"検証の 4 週: 帯ごとの確信度と正解率の差 最大 {max(gap):.3f}")


# ============================================================
# 実験 3: ラベル無しで見られる信号は、正解率の低い週を拾えるか
# ============================================================
def psi(base, now, bins=10, eps=1e-4):
    """PSI。区間は base の 10 分位。空の区間の割合 0 は eps に置き換える。"""
    q = np.quantile(base, np.linspace(0, 1, bins + 1))
    q[0], q[-1] = -np.inf, np.inf
    b = np.clip(np.histogram(base, q)[0] / len(base), eps, None)
    n = np.clip(np.histogram(now, q)[0] / len(now), eps, None)
    return float(np.sum((n - b) * np.log(n / b)))


psi_price_w = np.array([psi(X[valid, 2], X[week == w, 2]) for w in weeks])
psi_demand_w = np.array([psi(X[valid, 3], X[week == w, 3]) for w in weeks])
psi_conf_w = np.array([psi(conf[valid], conf[week == w]) for w in weeks])
predup_w = np.array([pred_up[week == w].mean() for w in weeks])
print(f"検証の 4 週: UP と予測した割合 {pred_up[valid].mean():.2f}")
signals = {                                           # 正解を使わずに鳴らすアラート
    "平均確信度 < 0.70": conf_w < 0.70,
    "価格の PSI > 0.25": psi_price_w > 0.25,
    "需要の PSI > 0.25": psi_demand_w > 0.25,
    "確信度の PSI > 0.25": psi_conf_w > 0.25,
    "UP と予測した割合 < 0.30": predup_w < 0.30,
}
bad = acc_w < 0.70                                    # 答え: 正解率が 0.70 未満の週
for name, alarm in signals.items():
    print(f"{name:<20} アラート {alarm.sum():>3} 週  当たり {np.sum(alarm & bad):>2}"
          f"  誤検知 {np.sum(alarm & ~bad):>2}  見逃し {np.sum(bad & ~alarm):>2}")
print(f"UP と予測した割合と正解率の相関 {np.corrcoef(acc_w, predup_w)[0, 1]:.2f}")

# PSI の揺れ: 分布が同じなら 336 行でどこまで振れるか、検証の各週はどれだけ動いているか
rng_psi = np.random.default_rng(1)
base = X[valid, 2]
noise = np.array([psi(base, rng_psi.choice(base, 336, replace=False)) for _ in range(1000)])
print(f"検証の 4 週から 336 行を選んだ時の価格の PSI: 平均 {noise.mean():.3f}  0.1 を超えた割合 {np.mean(noise > 0.1):.3f}")
print("検証の各週の価格の PSI:", [round(psi(base, X[week == w, 2]), 2) for w in range(22, 26)])

# Prometheus で出す窓: 検証の 28 日で、直近 1 日と 7 日の UP と予測した割合を数える
day = np.arange(len(frame)) // 48                     # 1 日 48 行
for win in [1, 7]:
    r = np.array([pred_up[valid & (day >= d) & (day < d + win)].mean()
                  for d in range(day[valid].min(), day[valid].max() - win + 2)])
    print(f"検証の 28 日、直近 {win} 日: UP と予測した割合 標準偏差 {r.std():.3f}"
          f"  最小 {r.min():.3f}  0.30 を割った日 {np.sum(r < 0.30)}")

# ============================================================
# 実験 4: 正解率が変わらなくても、日ごとの正解率はしきい値を割る
# ============================================================
print(f"1 日 48 件で正解率 0.78 のモデルが 0.70 を割る確率 {binom.cdf(np.ceil(0.70 * 48) - 1, 48, 0.78):.3f}")
print(f"1 日 48 件を独立とみなした時の、UP と予測した割合の標準偏差 {np.sqrt(0.58 * 0.42 / 48):.3f}")
rng = np.random.default_rng(0)
true_acc = np.r_[np.full(365, 0.78), np.full(120, 0.65)]   # 366 日目から 0.65 に落ちる
daily = rng.binomial(48, true_acc) / 48                     # 1 日 48 件の正解率
for win in [1, 7, 28]:
    false_alarm, delay = [], []
    for _ in range(2000):
        d = rng.binomial(48, true_acc)
        roll = np.convolve(d, np.ones(win), "valid") / (48 * win)  # 直近 win 日の正解率
        end = np.arange(win - 1, len(d))                          # 窓の最後の日
        alarm = roll < 0.70
        false_alarm.append(np.sum(alarm & (end < 365)) * 365 / np.sum(end < 365))
        after = np.flatnonzero(alarm & (end >= 365))
        delay.append(end[after[0]] - 365 + 1 if len(after) else np.nan)
    print(f"直近 {win:>2} 日: 誤検知 年 {np.mean(false_alarm):5.1f} 回  落ちてから鳴るまで 中央値 {np.nanmedian(delay):4.0f} 日")

# ============================================================
# 実験 5: 正解が 8 週遅れて届く時、どの週に気づけるか
# ============================================================
LAG = 8
two_acc = bad[1:] & bad[:-1]                          # 2 週続けて 0.70 未満
two_up = (predup_w[1:] < 0.30) & (predup_w[:-1] < 0.30)
first_acc = weeks[1:][np.argmax(two_acc)]
first_up = weeks[1:][np.argmax(two_up)]
print(f"正解率が 2 週続けて 0.70 を割った最初の週: 第 {first_acc} 週。正解が {LAG} 週遅れるなら、分かるのは第 {first_acc + LAG} 週")
print(f"UP と予測した割合が 2 週続けて 0.30 を割った最初の週: 第 {first_up} 週")
for w in [46, 61, 96]:
    j = w - 26
    print(f"第 {w} 週: 正解率 {acc_w[j]:.3f}  UP と予測した割合 {predup_w[j]:.3f}  価格の PSI {psi_price_w[j]:.2f}")

# ============================================================
# 図
# ============================================================
# 表紙: 週ごとの正解率と確信度
fig, ax = plt.subplots(figsize=(9.6, 3.9))
xw = np.arange(22, week.max() + 1)
acc_all = np.array([correct[week == w].mean() for w in xw])
conf_all = np.array([conf[week == w].mean() for w in xw])
ax.axvspan(22, 26, color=GREEN, alpha=0.12)
ax.text(24, 0.405, "検証", ha="center", color=GREEN, fontsize=9)
ax.plot(xw, conf_all, color=INK, lw=1.6, label="平均確信度（正解が無くても出せる）")
ax.plot(xw, acc_all, color=RED, lw=1.6, label="正解率（正解が届いてから出せる）")
ax.axhline(0.70, color=GRAY, lw=0.8, ls="--")
ax.text(xw[-1] + 1.5, 0.705, "0.70", va="bottom", color=GRAY, fontsize=9)
ax.set_xlim(20, xw[-1] + 5)
j = int(np.argmin(acc_w)) + 26
ax.annotate(f"第 {j} 週（{week_date(j):%Y-%m}）\n正解率 {acc_w[j - 26]:.3f}\n確信度 {conf_w[j - 26]:.3f}",
            xy=(j, acc_w[j - 26]), xytext=(j + 5, 0.42), fontsize=9, color=INK,
            arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.8))
ax.plot([j], [acc_w[j - 26]], "o", color=RED, ms=5)
ax.plot([j], [conf_w[j - 26]], "o", color=INK, ms=5)
ticks = [22, 40, 60, 80, 100, 120]
ax.set_xticks(ticks)
ax.set_xticklabels([f"第 {t} 週\n{week_date(t):%Y-%m}" for t in ticks], fontsize=8.5)
ax.set_ylim(0.38, 1.02)
ax.set_ylabel("週ごとの値")
ax.legend(loc="lower right", fontsize=9, frameon=False, ncol=2, bbox_to_anchor=(1.0, 1.0))
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "mpm_cover.webp")

# 価格の 10 分位ごとの UP の割合
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.9), gridspec_kw={"width_ratios": [2.2, 1]})
k = np.arange(1, 11)
wbar = 0.27
ax1.bar(k - wbar, bins[:, 0], wbar, color=GRAY, label="学習の 22 週で UP だった割合")
ax1.bar(k, bins[:, 1], wbar, color=RED, label="運用の 109 週で UP だった割合")
ax1.bar(k + wbar, bins[:, 2], wbar, color=BLUE, label="運用でモデルが UP と予測した割合")
ax1.set_xticks(k)
ax1.set_xticklabels([f"{i}" for i in k])
ax1.set_xlabel("価格の 10 分位（学習した期間で区切る。1 が最も安い 10%）")
ax1.set_ylabel("割合")
ax1.set_ylim(0, 1.05)
ax1.legend(fontsize=8.5, frameon=False, loc="upper left")
ax1.annotate(f"学習 {bins[0, 0]:.2f}\n運用 {bins[0, 1]:.2f}\n予測 {bins[0, 2]:.2f}", xy=(1, bins[0, 1]),
             xytext=(1.6, 0.42), fontsize=8.5, arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.8))
ax1.grid(True, axis="y", alpha=0.25)
ax2.bar(k, bins[:, 3], color=INK)   # 左の 3 色と混ざらないよう、1 色にする
ax2.set_xticks(k)
ax2.set_xlabel("価格の 10 分位")
ax2.set_ylabel("運用の行のうち、その区間に入る割合")
ax2.text(1.4, bins[0, 3], f"{bins[0, 3]:.0%}", va="center", fontsize=9, color=INK)
ax2.axhline(0.1, color=GRAY, lw=0.8, ls="--")
ax2.text(10.4, 0.1, "学習では 10%", ha="right", va="bottom", fontsize=8.5, color=GRAY)
ax2.grid(True, axis="y", alpha=0.25)
fig.tight_layout()
save(fig, "mpm_price_bins.webp")

# ラベル無しの信号と正解率の低い週
fig, ax = plt.subplots(figsize=(9.6, 3.6))
names = list(signals)
for r, name in enumerate(names):
    a = signals[name]
    for t, (al, b) in enumerate(zip(a, bad)):
        if al:
            ax.add_patch(plt.Rectangle((weeks[t] - 0.5, r - 0.38), 1, 0.76, color=RED if b else BLUE, lw=0))
r = len(names)
for t, b in enumerate(bad):
    if b:
        ax.add_patch(plt.Rectangle((weeks[t] - 0.5, r - 0.38), 1, 0.76, color=INK, lw=0))
ax.set_yticks(range(r + 1))
ax.set_yticklabels(names + ["正解率 < 0.70（答え）"], fontsize=9)
ax.set_ylim(r + 0.6, -0.6)
ax.set_xlim(25.5, weeks[-1] + 0.5)
ax.set_xticks(ticks[1:])
ax.set_xticklabels([f"第 {t} 週\n{week_date(t):%Y-%m}" for t in ticks[1:]], fontsize=8.5)
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=RED, label="アラートが鳴り、正解率も 0.70 未満（当たり）"),
                   Patch(color=BLUE, label="アラートが鳴ったが、正解率は 0.70 以上（誤検知）")],
          fontsize=8.5, frameon=False, loc="lower center", bbox_to_anchor=(0.45, 1.0), ncol=2)
fig.tight_layout()
save(fig, "mpm_signals.webp")

# 日ごとの正解率の揺れ
fig, ax = plt.subplots(figsize=(9.6, 3.6))
days = np.arange(1, len(daily) + 1)
below = daily < 0.70
ax.scatter(days[~below], daily[~below], s=6, color=BLUE, label="1 日 48 件の正解率")
ax.scatter(days[below], daily[below], s=9, color=RED, label="0.70 を割った日")
roll7 = np.convolve(daily, np.ones(7) / 7, "valid")
ax.plot(days[6:], roll7, color=INK, lw=1.3, label="直近 7 日の正解率")
ax.step(days, true_acc, where="post", color=GREEN, lw=1.2, ls="--", label="本当の正解率")
ax.axhline(0.70, color=GRAY, lw=0.8, ls="--")
ax.axvline(365.5, color=GRAY, lw=0.8)
ax.text(362, 1.0, "本当の正解率は\nここまで 0.78 のまま", ha="right", va="top", fontsize=8.5, color=INK)
ax.text(369, 1.0, "0.65 に\n落ちる", ha="left", va="top", fontsize=8.5, color=INK)
ax.set_xlabel("日")
ax.set_ylabel("正解率")
ax.set_ylim(0.45, 1.02)
ax.legend(fontsize=8.5, frameon=False, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0))
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "mpm_noise.webp")

# 動く図: 正解が 8 週遅れて届く時の見え方。1 週を 0.16 秒ずつ表示する
frames = []
end_week = 80
for now in range(26, end_week + 1):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.4, 4.6), sharex=True)
    seen = weeks <= now - LAG
    a1.plot(weeks[seen], acc_w[seen], color=RED, lw=1.8)
    wait0 = max(26, now - LAG)
    a1.axvspan(wait0, now, color=GRAY, alpha=0.15)
    if now - wait0 >= 4:                  # 帯が狭い間は文字を置かない（軸の外にはみ出すため）
        a1.text((wait0 + now) / 2, 0.97, "正解待ち", ha="center", va="top", fontsize=9, color=INK)
    a1.axhline(0.70, color=GRAY, lw=0.8, ls="--")
    a1.set_ylim(0.4, 1.0)
    a1.set_ylabel("正解率")
    a1.set_title(f"今日は第 {now} 週（{week_date(now):%Y-%m-%d}）。正解は {LAG} 週遅れて届く", fontsize=10, loc="left")
    if now >= first_acc + LAG:
        for w in (first_acc - 1, first_acc):   # 0.70 を割った 2 週に、値を添えて印を付ける
            a1.plot([w], [acc_w[w - 26]], "o", color=RED, ms=7, mec="white", mew=1)
            a1.annotate(f"{acc_w[w - 26]:.3f}", xy=(w, acc_w[w - 26]), xytext=(-6 if w < first_acc else 6, -14),
                        textcoords="offset points", ha="right" if w < first_acc else "left", fontsize=8, color=RED)
        a1.text(first_acc - 1, 0.45, f"第 {first_acc} 週の低下が、第 {first_acc + LAG} 週に分かる", ha="right", fontsize=8.5, color=RED)
    sv = weeks <= now
    a2.plot(weeks[sv], predup_w[sv], color=DARKBLUE, lw=1.8)
    a2.axhline(0.30, color=GRAY, lw=0.8, ls="--")
    a2.set_ylim(0, 0.75)
    a2.set_ylabel("UP と予測した割合", fontsize=9)
    if now >= first_up:
        a2.plot([first_up], [predup_w[first_up - 26]], "o", color=DARKBLUE)
        a2.text(first_up + 1, 0.55, f"第 {first_up} 週の低下は、その週のうちに分かる", fontsize=8.5, color=DARKBLUE)
    a2.set_xlim(26, end_week)
    a2.set_xlabel("予測した週（1 週を 0.16 秒ずつ表示）")
    for a in (a1, a2):
        a.grid(True, alpha=0.25)
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=100, facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    frames.append(Image.open(buf).convert("RGB"))
durations = [160] * (len(frames) - 1) + [3000]
frames[0].save(NOTE_DIR / "mpm_label_lag.webp", "WEBP", save_all=True, append_images=frames[1:],
               duration=durations, loop=0, quality=60, method=6)
print(f"動く図: {len(frames)} コマ、{sum(durations) / 1000:.1f} 秒")
