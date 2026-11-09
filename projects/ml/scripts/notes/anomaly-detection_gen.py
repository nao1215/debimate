"""anomaly-detection ノート用の図を生成するスクリプト。"""
import os
import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_blobs
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.covariance import EllipticEnvelope

COLOR_BLUE, COLOR_RED, COLOR_GREEN, COLOR_ORANGE = "#7aa6c2", "#e15759", "#59a14f", "#f28e2b"

NOTE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "notes", "ml", "anomaly-detection"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name):
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# Generate normal + anomaly data
rng = np.random.default_rng(0)
n_normal = 300
n_anom = 20

X_normal, _ = make_blobs(n_samples=n_normal, centers=[(0, 0), (3, 3)], cluster_std=0.6,
                          random_state=0)
X_anom = rng.uniform([-3, -3], [6, 6], (n_anom, 2))
X = np.vstack([X_normal, X_anom])
y_true = np.concatenate([np.ones(n_normal), -np.ones(n_anom)])

# ============================================================
# Fig 1: 4 anomaly detection algorithms compared
# ============================================================
algorithms = {
    "Isolation Forest": IsolationForest(contamination=0.07, random_state=0),
    "Local Outlier Factor": LocalOutlierFactor(n_neighbors=20, contamination=0.07),
    "One-Class SVM": OneClassSVM(nu=0.07, kernel="rbf", gamma=0.5),
    "Elliptic Envelope": EllipticEnvelope(contamination=0.07, random_state=0),
}

xx, yy = np.meshgrid(np.linspace(-5, 7, 200), np.linspace(-5, 7, 200))

fig, axes = plt.subplots(2, 2, figsize=(13, 11))
for ax, (name, clf) in zip(axes.ravel(), algorithms.items()):
    if name == "Local Outlier Factor":
        pred = clf.fit_predict(X)
        # LOF doesn't have predict() for new points; use negative_outlier_factor_ for the decision
        Z = -clf.negative_outlier_factor_  # higher = more outlier
        # For visualization, we can't plot LOF boundary cleanly; just show points
        ax.scatter(X[pred == 1, 0], X[pred == 1, 1], color=COLOR_BLUE, s=20, alpha=0.6,
                    label="normal")
        ax.scatter(X[pred == -1, 0], X[pred == -1, 1], color=COLOR_RED, marker="x",
                    s=80, label=f"detected anomaly ({(pred==-1).sum()})")
    else:
        clf.fit(X)
        pred = clf.predict(X)
        Z = clf.decision_function(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
        ax.contourf(xx, yy, Z, levels=[Z.min(), 0, Z.max()], colors=[COLOR_RED, COLOR_BLUE], alpha=0.15)
        ax.contour(xx, yy, Z, levels=[0], colors="black", linewidths=1)
        ax.scatter(X[pred == 1, 0], X[pred == 1, 1], color=COLOR_BLUE, s=20, alpha=0.6,
                    label="normal")
        ax.scatter(X[pred == -1, 0], X[pred == -1, 1], color=COLOR_RED, marker="x",
                    s=80, label=f"detected anomaly ({(pred==-1).sum()})")
    # Show true anomalies
    ax.scatter(X[y_true == -1, 0], X[y_true == -1, 1], facecolors="none",
                edgecolors=COLOR_GREEN, s=200, linewidths=2, label="true anomaly")
    ax.set_title(name)
    ax.set_xlabel("x1"); ax.set_ylabel("x2")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.25)
plt.tight_layout()
save("anomaly_methods_compare.png")


# ============================================================
# Fig 2: Isolation Forest concept - random partition
# ============================================================
fig, ax = plt.subplots(figsize=(9, 7))

# Show: normal point needs many splits to isolate, anomaly needs few
# 本文の深さの実測と同じデータ（図ごとに乱数を作り直す）
rng_small = np.random.default_rng(0)
X_small = np.vstack([
    rng_small.normal([0, 0], 0.5, (50, 2)),
    np.array([[3, 3]]),  # anomaly
])

ax.scatter(X_small[:-1, 0], X_small[:-1, 1], color=COLOR_BLUE, s=40, alpha=0.7,
           label="normal")
ax.scatter(X_small[-1, 0], X_small[-1, 1], color=COLOR_RED, s=200, marker="*",
           label="anomaly")

# Random splits to isolate the anomaly
# 分割の一例（手で選んだ 1 本。実際の木は特徴量と閾値をランダムに選ぶ）
splits = [
    (1.5, "vertical"),    # x=1.5
]
for thresh, axis in splits:
    if axis == "vertical":
        ax.axvline(thresh, color=COLOR_GREEN, lw=2)
    else:
        ax.axhline(thresh, color=COLOR_GREEN, lw=2)

ax.set_xlim(-2, 4); ax.set_ylim(-2, 4)
ax.set_aspect("equal")
ax.set_title("Isolation Forest: one split (x1 = 1.5) isolates the anomaly")
ax.set_xlabel("x1"); ax.set_ylabel("x2")
ax.legend(loc="upper left")
ax.grid(True, alpha=0.25)
plt.tight_layout()
save("anomaly_isolation_concept.svg")


# ============================================================
# Fig 3: Threshold tuning - score histogram with cutoff
# ============================================================
clf = IsolationForest(contamination="auto", random_state=0).fit(X)
scores = clf.decision_function(X)
# Higher = more normal, lower = more anomaly

# Different contamination cutoffs
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.hist(scores[y_true == 1], bins=40, color=COLOR_BLUE, alpha=0.6, label="true normal",
         density=True)
ax.hist(scores[y_true == -1], bins=15, color=COLOR_RED, alpha=0.7, label="true anomaly",
         density=True)
for contam, color, ls in [(0.03, COLOR_GREEN, "--"), (0.07, COLOR_ORANGE, "-"),
                            (0.15, "purple", ":")]:
    thr = np.percentile(scores, contam * 100)
    ax.axvline(thr, color=color, ls=ls, lw=1.5,
                label=f"threshold @ contamination={contam}")
ax.set_xlabel("anomaly score (higher = more normal)")
ax.set_ylabel("density")
ax.set_title("Score histogram + threshold selection")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)
plt.tight_layout()
save("anomaly_threshold_tuning.svg")


# ============================================================
# Fig 4: Time-series anomaly detection (本文のコードと同じ計算)
# ============================================================
import pandas as pd

rng_ts = np.random.default_rng(0)
t = np.arange(500)
y_ts = 10 + 0.02 * t + 5 * np.sin(2 * np.pi * t / 50) + rng_ts.normal(0, 0.8, 500)
anom_idx = [120, 200, 320, 420]
y_ts[anom_idx] += 8
s_ts = pd.Series(y_ts)


def rolling_z(x, window=30):
    past = x.shift(1).rolling(window)
    return ((x - past.mean()) / past.std()).abs()


trend = s_ts.rolling(50, center=True, min_periods=1).median()
season = (s_ts - trend).groupby(t % 50).transform("median")
resid = s_ts - trend - season
z_raw = rolling_z(s_ts)
z_resid = rolling_z(resid)
threshold = 3
detected = np.where(z_raw > threshold)[0]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7.5), sharex=True)
ax1.plot(t, y_ts, color=COLOR_BLUE, lw=1, alpha=0.8, label="time series")
ax1.scatter(anom_idx, y_ts[anom_idx], facecolors="none", edgecolors=COLOR_GREEN,
            s=200, linewidths=2, label="true anomaly (+8)")
ax1.scatter(detected, y_ts[detected], color=COLOR_RED, marker="x", s=80,
            label=f"detected on raw series (|z|>{threshold})")
ax1.set_ylabel("value")
ax1.set_title("Rolling z-score on the raw series")
ax1.legend(loc="upper left", fontsize=9)
ax1.grid(True, alpha=0.25)

ax2.plot(t, z_raw, color="#999999", lw=1, label="|z| on raw series")
ax2.plot(t, z_resid, color="#333333", lw=1, label="|z| on residual (trend and season removed)")
ax2.axhline(threshold, color=COLOR_RED, ls="--", lw=1, label=f"|z| = {threshold}")
for i in anom_idx:
    ax2.axvline(i, color=COLOR_GREEN, ls=":", lw=1.5)
ax2.set_xlabel("time")
ax2.set_ylabel("|z|")
ax2.set_title("Same detector after removing trend and season (green dotted: true anomalies)")
ax2.legend(loc="upper left", fontsize=9)
ax2.grid(True, alpha=0.25)
plt.tight_layout()
save("anomaly_time_series.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
