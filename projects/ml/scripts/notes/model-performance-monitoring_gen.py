"""model-performance-monitoring ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/model-performance-monitoring_gen.py
"""
import os

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from scipy import stats

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/mlops/model-performance-monitoring"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Accuracy time series with thresholds and alert
# ============================================================
rng = np.random.default_rng(0)
days = np.arange(0, 120)
# Slow decay due to drift, then sudden drop at day 75 (external event)
true_acc = 0.92 - 0.0008 * days
true_acc[75:] -= 0.05
observed = true_acc + rng.normal(0, 0.006, len(days))

# 7-day moving average
window = 7
ma = np.array([observed[max(0, i - window):i + 1].mean() for i in range(len(days))])

plt.figure(figsize=(11, 4.5))
plt.scatter(days, observed, color=COLOR_GRAY, alpha=0.45, s=18, label="daily metric")
plt.plot(days, ma, color=COLOR_BLUE, lw=2, label="7-day moving avg")
# Thresholds
plt.axhline(0.88, color=COLOR_ORANGE, ls="--", lw=1.5, label="warning (0.88)")
plt.axhline(0.85, color=COLOR_RED, ls="--", lw=1.5, label="critical (0.85)")
# Alert marker
alert_day = np.argmax(ma < 0.85)
plt.axvline(alert_day, color=COLOR_RED, lw=1)
plt.annotate(f"page on-call\nday {alert_day}", (alert_day, 0.82),
             xytext=(alert_day + 5, 0.78), color=COLOR_RED, fontsize=10,
             arrowprops=dict(arrowstyle="->", color=COLOR_RED))
plt.xlabel("day in production")
plt.ylabel("model accuracy")
plt.title("Production accuracy time series with warning/critical thresholds")
plt.legend(loc="lower left", fontsize=9)
plt.grid(True, alpha=0.25)
plt.ylim(0.78, 0.95)
plt.tight_layout()
save("monitoring_accuracy_alert.svg")


# ============================================================
# Fig 2: Input drift via KS statistic & PSI over time
# ============================================================
rng2 = np.random.default_rng(1)
n_days = 120
n_per_day = 200
# Reference distribution (training set)
ref = rng2.normal(50, 10, 5000)
# Simulate: drift starts around day 60
ks_stats = []
psi_values = []
for d in range(n_days):
    if d < 60:
        live = rng2.normal(50, 10, n_per_day)
    else:
        shift = (d - 60) * 0.15
        live = rng2.normal(50 + shift, 10 + shift * 0.1, n_per_day)
    ks_stat, _ = stats.ks_2samp(ref, live)
    ks_stats.append(ks_stat)
    # PSI (simplified): use 10 quantile bins
    bins = np.quantile(ref, np.linspace(0, 1, 11))
    bins[0] -= 1; bins[-1] += 1
    ref_counts, _ = np.histogram(ref, bins=bins)
    live_counts, _ = np.histogram(live, bins=bins)
    ref_pct = np.clip(ref_counts / ref_counts.sum(), 1e-6, 1)
    live_pct = np.clip(live_counts / live_counts.sum(), 1e-6, 1)
    psi = ((live_pct - ref_pct) * np.log(live_pct / ref_pct)).sum()
    psi_values.append(psi)

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

ax = axes[0]
ax.plot(range(n_days), ks_stats, color=COLOR_BLUE, lw=2)
ax.axhline(0.1, color=COLOR_ORANGE, ls="--", label="threshold 0.1 (mild drift)")
ax.axhline(0.2, color=COLOR_RED, ls="--", label="threshold 0.2 (strong drift)")
ax.set_xlabel("day"); ax.set_ylabel("KS statistic")
ax.set_title("Kolmogorov-Smirnov statistic vs training distribution")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

ax = axes[1]
ax.plot(range(n_days), psi_values, color=COLOR_RED, lw=2)
ax.axhline(0.1, color=COLOR_ORANGE, ls="--", label="PSI = 0.1 (minor)")
ax.axhline(0.25, color=COLOR_RED, ls="--", label="PSI = 0.25 (major)")
ax.set_xlabel("day"); ax.set_ylabel("PSI")
ax.set_title("Population Stability Index")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

plt.suptitle("Input drift monitoring picks up the shift before accuracy collapses",
             y=1.02)
plt.tight_layout()
save("monitoring_input_drift.svg")


# ============================================================
# Fig 3: Ground truth lag - proxy metrics fill the gap
# ============================================================
fig, ax = plt.subplots(figsize=(11, 4.5))

# Timeline
ax.axhline(2, color=COLOR_BLUE, lw=3, alpha=0.7)
ax.axhline(1, color=COLOR_ORANGE, lw=3, alpha=0.7)
ax.axhline(0, color=COLOR_GREEN, lw=3, alpha=0.7)
ax.text(-3, 2, "Prediction\n(now)", ha="right", va="center", fontsize=10, fontweight="bold", color=COLOR_BLUE)
ax.text(-3, 1, "Proxy signals\n(clicks, errors)", ha="right", va="center", fontsize=10, color=COLOR_ORANGE)
ax.text(-3, 0, "Ground truth\n(actual label)", ha="right", va="center", fontsize=10, color=COLOR_GREEN)

# Event arrows
for i, day in enumerate([0, 1, 3, 7]):
    color = [COLOR_BLUE, COLOR_ORANGE, COLOR_ORANGE, COLOR_GREEN][i]
    label = ["t=0\n(predict)", "t+1d\n(user click)", "t+3d\n(conversion?)", "t+7d\n(actual outcome)"][i]
    y = [2, 1, 1, 0][i]
    ax.scatter([day], [y], s=400, color=color, edgecolor="black", linewidth=1.5, zorder=5)
    ax.text(day, y + 0.3, label, ha="center", fontsize=9)

ax.set_xlim(-5, 10)
ax.set_ylim(-0.7, 3)
ax.set_xticks([0, 1, 3, 7])
ax.set_xticklabels(["t=0", "t+1d", "t+3d", "t+7d"])
ax.set_yticks([])
ax.set_xlabel("time after prediction")
ax.set_title("Ground truth is delayed → use proxy metrics until it arrives")
plt.tight_layout()
save("monitoring_ground_truth_lag.svg")


# ============================================================
# Fig 4: Monitoring layers and ownership
# ============================================================
fig, ax = plt.subplots(figsize=(11, 5.5))

layers = [
    ("Business KPIs",
     "revenue / conversion / NPS",
     "Product / Business", COLOR_RED),
    ("Model performance",
     "accuracy / F1 / regression error",
     "ML Engineer", COLOR_ORANGE),
    ("Data quality",
     "schema / range / drift / null rate",
     "Data Engineer", COLOR_GREEN),
    ("Infrastructure",
     "latency / error rate / CPU / memory",
     "SRE / DevOps", COLOR_BLUE),
]

for i, (name, examples, owner, color) in enumerate(layers):
    rect = patches.Rectangle((0.05, 0.85 - i * 0.22), 0.9, 0.18,
                              facecolor=color, alpha=0.6,
                              edgecolor="black", linewidth=1.5)
    ax.add_patch(rect)
    ax.text(0.08, 0.94 - i * 0.22, name, fontsize=12, fontweight="bold")
    ax.text(0.08, 0.89 - i * 0.22, examples, fontsize=10)
    ax.text(0.95, 0.91 - i * 0.22, f"owner: {owner}", fontsize=10,
            ha="right", style="italic")

ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.set_xticks([]); ax.set_yticks([])
ax.set_title("4 layers of monitoring: each needs its own SLO and owner")
plt.tight_layout()
save("monitoring_layers.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
