"""regression-metrics ノートの実験と図を生成するスクリプト。

本文に載せた実験（地域ごとの RMSE と R²、R² の分母、平均・中央値と損失の違い、
誤差の偏り、MAPE と予測の縮小、0 を含む正解の MAPE）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
データは scikit-learn の fetch_california_housing（初回だけ StatLib の配布元から取得）。
実行: cd projects/ml && .venv/bin/python scripts/notes/regression-metrics_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from PIL import Image
from sklearn.datasets import fetch_california_housing
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import (mean_absolute_error, mean_absolute_percentage_error,
                             mean_squared_error, r2_score, root_mean_squared_error)
from sklearn.model_selection import KFold, train_test_split

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "regression-metrics"
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
# 実験 1: 地域ごとの RMSE（冒頭）
# ============================================================
X, y = fetch_california_housing(return_X_y=True, as_frame=True)  # y の単位は 10 万ドル
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
model = HistGradientBoostingRegressor(random_state=0).fit(X_train, y_train)
pred = model.predict(X_test)

lat, lon = X_test["Latitude"], X_test["Longitude"]
regions = {
    "ベイエリア": (37.2 < lat) & (lat < 38.3) & (lon < -121.5),
    "ロサンゼルス": (33.6 < lat) & (lat < 34.4) & (-118.7 < lon) & (lon < -117.6),
    "セントラルバレー": (35.0 < lat) & (lat < 38.5) & (-121.5 < lon) & (lon < -118.5),
}
for name, mask in regions.items():
    rmse = root_mean_squared_error(y_test[mask], pred[mask])
    print(f"{name:<8} {mask.sum():>5} 件  RMSE {rmse:.3f}")

print("--- R² も出す")
for name, mask in regions.items():
    rmse = root_mean_squared_error(y_test[mask], pred[mask])
    r2 = r2_score(y_test[mask], pred[mask])
    print(f"{name:<8} RMSE {rmse:.3f}  R² {r2:.3f}")
print(f"テスト全体 RMSE {root_mean_squared_error(y_test, pred):.3f}  R² {r2_score(y_test, pred):.3f}")

fig, axes = plt.subplots(1, 3, figsize=(11, 3.9), sharex=True, sharey=True)
for ax, (name, mask) in zip(axes, regions.items()):
    rmse = root_mean_squared_error(y_test[mask], pred[mask])
    r2 = r2_score(y_test[mask], pred[mask])
    color = RED if name == "セントラルバレー" else BLUE
    ax.scatter(y_test[mask], pred[mask], s=5, alpha=0.45, color=color, edgecolors="none")
    ax.plot([0, 5.6], [0, 5.6], color=INK, lw=0.8, ls="--")
    ax.set_title(f"{name}\nRMSE {rmse:.2f}　R² {r2:.2f}", fontsize=11, color=INK)
    ax.set_xlim(0, 5.6)  # 予測の最大は 5.47 なので、5.2 で切ると点が欠ける
    ax.set_ylim(0, 5.6)
    ax.set_aspect("equal")
    ax.set_xlabel("正解の住宅価格（10 万ドル）")
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("予測（10 万ドル）")
fig.tight_layout()
save(fig, "rm_cover.webp")

# ============================================================
# 実験 2: R² の分母（評価データの分散）
# ============================================================
print("--- R² の分母")
rows = list(regions.items()) + [("テスト全体", np.ones(len(y_test), dtype=bool))]
stats = []
for name, mask in rows:
    yt, yp = y_test[mask].to_numpy(), pred[mask]
    mse = np.mean((yt - yp) ** 2)
    var = np.mean((yt - yt.mean()) ** 2)  # 評価データ自身の平均を当てた時の MSE
    stats.append((name, mse, var))
    print(f"{name:<8} MSE {mse:.3f}  分散 {var:.3f}  1 - MSE/分散 {1 - mse / var:.3f}"
          f"  r2_score {r2_score(yt, yp):.3f}")

fig = plt.figure(figsize=(11, 4.2))
axm = fig.add_axes([0.0, 0.08, 0.36, 0.84])
axb = fig.add_axes([0.47, 0.13, 0.5, 0.75])
sc = axm.scatter(X_test["Longitude"], X_test["Latitude"], c=y_test, s=3, cmap="Greys",
                 vmin=-2.0, vmax=5.2, edgecolors="none")
boxes = {"ベイエリア": (-123.0, 37.2, 1.5, 1.1), "ロサンゼルス": (-118.7, 33.6, 1.1, 0.8),
         "セントラルバレー": (-121.5, 35.0, 3.0, 3.5)}
label_at = {"ベイエリア": (-124.5, 36.4), "ロサンゼルス": (-117.45, 33.85), "セントラルバレー": (-118.3, 37.8)}
for name, (x0, y0, w, h) in boxes.items():
    c = RED if name == "セントラルバレー" else BLUE
    axm.add_patch(Rectangle((x0, y0), w, h, fill=False, ec=c, lw=1.6))
    axm.text(*label_at[name], name, color=c, fontsize=9.5, va="center",
             bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none", alpha=0.85))
axm.set_xlim(-124.6, -114)
axm.set_ylim(32.4, 42.2)
axm.set_aspect("equal")
axm.set_xticks([])
axm.set_yticks([])
for s in axm.spines.values():
    s.set_visible(False)
axm.set_title("テストデータの位置（濃いほど高い）", fontsize=10)
yy = np.arange(len(stats))[::-1]
axb.barh(yy + 0.2, [s[2] for s in stats], height=0.38, color=GRAY, label="正解の分散（平均を当てた時の MSE）")
axb.barh(yy - 0.2, [s[1] for s in stats], height=0.38, color=RED, label="モデルの MSE")
for yi, (name, mse, var) in zip(yy, stats):
    axb.text(max(var, mse) + 0.03, yi, f"R² = 1 − {mse:.3f} / {var:.3f} = {1 - mse / var:.3f}",
             va="center", fontsize=9, color=INK)
axb.set_yticks(yy)
axb.set_yticklabels([s[0] for s in stats])
axb.set_xlim(0, 2.4)
axb.set_xlabel("10 万ドルの 2 乗")
axb.legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=2, fontsize=8.5, frameon=False)
save(fig, "rm_r2_ratio.webp")

# 同じ評価データなら R² と MSE の順位は一致する / 相関の 2 乗とは違う
print("--- 予測をずらす")
for shift in [0.0, 0.3, 0.6]:
    q = pred + shift
    print(f"+{shift:.1f}  R² {r2_score(y_test, q):.3f}  相関の 2 乗 {np.corrcoef(y_test, q)[0, 1] ** 2:.3f}")
band = (y_test >= 1.5) & (y_test < 2.5)
print(f"正解が 1.5〜2.5 の {band.sum()} 件  RMSE {root_mean_squared_error(y_test[band], pred[band]):.3f}"
      f"  R² {r2_score(y_test[band], pred[band]):.3f}")

# ============================================================
# 実験 3: 定数の予測と、学習の損失
# ============================================================
print("--- 定数の予測と損失（5 分割の平均）")
Xa, ya = X.to_numpy(), y.to_numpy()
names = ["平均を返す", "中央値を返す", "squared_error", "absolute_error"]
scores = {n: [] for n in names}
for tr, te in KFold(5, shuffle=True, random_state=0).split(Xa):
    preds = {"平均を返す": np.full(len(te), ya[tr].mean()),
             "中央値を返す": np.full(len(te), np.median(ya[tr]))}
    for loss in ["squared_error", "absolute_error"]:
        m = HistGradientBoostingRegressor(loss=loss, random_state=0).fit(Xa[tr], ya[tr])
        preds[loss] = m.predict(Xa[te])
    for n in names:
        scores[n].append([root_mean_squared_error(ya[te], preds[n]),
                          mean_absolute_error(ya[te], preds[n]),
                          mean_absolute_percentage_error(ya[te], preds[n])])
for n in names:
    s = np.array(scores[n]).mean(axis=0)
    print(f"{n:<14} RMSE {s[0]:.3f}  MAE {s[1]:.3f}  MAPE {s[2]:.3f}")

sq, ab = np.array(scores["squared_error"]), np.array(scores["absolute_error"])
ratio = ab / sq
print("absolute_error / squared_error（分割ごと）")
for j, met in enumerate(["RMSE", "MAE", "MAPE"]):
    print(f"  {met:<5}", np.round(ratio[:, j], 3).tolist())

fig, ax = plt.subplots(figsize=(7.2, 3.8))
for j, met in enumerate(["RMSE", "MAE", "MAPE"]):
    r = ratio[:, j]
    c = RED if r.min() > 1 else (GREEN if r.max() < 1 else GRAY)
    ax.scatter(np.full(5, j) + np.linspace(-0.12, 0.12, 5), r, s=40, color=c, zorder=3)
    ax.text(j, r.max() + 0.006, f"平均 {r.mean():.3f}", ha="center", fontsize=9, color=INK)
ax.axhline(1.0, color=INK, lw=0.8, ls="--")
ax.text(2.45, 1.002, "同じ", fontsize=9, color=INK, va="bottom", ha="right")
ax.set_xticks([0, 1, 2])
ax.set_xticklabels(["RMSE", "MAE", "MAPE"])
ax.set_xlim(-0.5, 2.5)
ax.set_ylim(0.92, 1.10)
ax.set_ylabel("absolute_error の値 ÷ squared_error の値")
ax.text(-0.45, 1.093, "1 より上: squared_error の方が良い", fontsize=9, color=RED)
ax.text(-0.45, 0.925, "1 より下: absolute_error の方が良い", fontsize=9, color=GREEN)
ax.grid(True, axis="y", alpha=0.25)
fig.tight_layout()
save(fig, "rm_loss_folds.webp")

# ============================================================
# 実験 4: 大きな誤差がどれだけを占めるか
# ============================================================
print("--- 誤差の偏り（冒頭のテストデータ）")
err = np.abs(y_test.to_numpy() - pred)
cap = y_test.to_numpy() >= 5.0
print(f"5.0 以上の行: テスト {cap.sum()} 件 / 全体 {(y >= 5.0).sum()} 件")
print(f"  うち 5.00001: テスト {(y_test.to_numpy() == 5.00001).sum()} 件 / 全体 {(y == 5.00001).sum()} 件"
      f"  ちょうど 5.0: 全体 {(y == 5.0).sum()} 件")
print(f"予測の最大 {pred.max():.2f}（冒頭の図の軸に収まるか）")
order = np.argsort(err)[::-1]
share_sq = np.cumsum(err[order] ** 2) / np.sum(err ** 2)
share_ab = np.cumsum(err[order]) / np.sum(err)
k = int(len(err) * 0.05)
print(f"誤差の大きい 5% の行が占める割合: 2 乗誤差の和 {share_sq[k - 1]:.3f}  絶対誤差の和 {share_ab[k - 1]:.3f}")
print(f"頭打ちの行が占める割合: 2 乗誤差の和 {np.sum(err[cap] ** 2) / np.sum(err ** 2):.3f}"
      f"  絶対誤差の和 {np.sum(err[cap]) / np.sum(err):.3f}  行数 {cap.mean():.3f}")

fig, ax = plt.subplots(figsize=(7.2, 4.0))
frac = np.arange(1, len(err) + 1) / len(err) * 100
ax.plot(frac, share_sq * 100, color=RED, lw=2, label="2 乗誤差の和（MSE・RMSE の中身）")
ax.plot(frac, share_ab * 100, color=BLUE, lw=2, label="絶対誤差の和（MAE の中身）")
ax.plot([0, 100], [0, 100], color=GRAY, lw=0.8, ls=":", label="どの行も同じ誤差なら")
ax.axvline(5, color=INK, lw=0.6, ls="--")
ax.annotate(f"{share_sq[k - 1] * 100:.0f}%", (5, share_sq[k - 1] * 100), xytext=(12, share_sq[k - 1] * 100 - 4),
            color=RED, fontsize=10, arrowprops=dict(arrowstyle="-", color=RED, lw=0.8))
ax.annotate(f"{share_ab[k - 1] * 100:.0f}%", (5, share_ab[k - 1] * 100), xytext=(12, share_ab[k - 1] * 100 - 6),
            color=BLUE, fontsize=10, arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.8))
ax.set_xlim(0, 100)
ax.set_ylim(0, 102)
ax.set_xlabel("誤差の大きい順に並べた行（上位何 %）")
ax.set_ylabel("合計に占める割合（%）")
ax.legend(loc="lower right", fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "rm_error_share.webp")

# ============================================================
# 実験 5: 予測を一律に縮めた時の MAPE
# ============================================================
print("--- 予測を c 倍する")
cs = np.round(np.arange(0.80, 1.101, 0.01), 2)
curves = {"RMSE": [], "MAE": [], "MAPE": []}
for c in cs:
    q = pred * c
    curves["RMSE"].append(root_mean_squared_error(y_test, q))
    curves["MAE"].append(mean_absolute_error(y_test, q))
    curves["MAPE"].append(mean_absolute_percentage_error(y_test, q))
for c in [0.90, 0.93, 0.95, 1.00]:
    i = int(np.argmin(np.abs(cs - c)))
    print(f"c={c:.2f}  RMSE {curves['RMSE'][i]:.4f}  MAE {curves['MAE'][i]:.4f}  MAPE {curves['MAPE'][i]:.4f}")
for met in curves:
    i = int(np.argmin(curves[met]))
    print(f"{met} が最小になる c: {cs[i]:.2f}")

fig, ax = plt.subplots(figsize=(7.2, 4.0))
i1 = int(np.argmin(np.abs(cs - 1.0)))
for met, c in [("RMSE", RED), ("MAE", BLUE), ("MAPE", GREEN)]:
    v = np.array(curves[met]) / curves[met][i1]
    ax.plot(cs, v, color=c, lw=2, label=met)
    j = int(np.argmin(v))
    ax.scatter([cs[j]], [v[j]], color=c, s=30, zorder=3)
ax.axvline(1.0, color=INK, lw=0.6, ls="--")
ax.text(1.003, 1.33, "学習したままの予測", fontsize=9, color=INK)
ax.set_xlabel("予測に掛ける倍率 c")
ax.set_ylabel("c = 1 の時の値との比")
ax.set_ylim(0.9, 1.4)
ax.legend(loc="upper center", fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "rm_mape_scale.webp")

# ============================================================
# 実験 6: 正解に 0 がある時の MAPE
# ============================================================
print("--- 正解に 0 を含む MAPE")
print(mean_absolute_percentage_error([0.0, 1.0], [0.1, 1.0]))
print(mean_absolute_percentage_error([1.0, 1.0], [1.1, 1.0]))
print(mean_squared_error([0.0, 1.0], [0.1, 1.0]) ** 0.5)
