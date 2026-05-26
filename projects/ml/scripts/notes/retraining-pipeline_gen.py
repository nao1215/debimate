"""retraining-pipeline ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/retraining-pipeline_gen.py
"""
import os

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#bbbbbb"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/mlops/retraining-pipeline"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Trigger types comparison
# ============================================================
fig, axes = plt.subplots(1, 4, figsize=(16, 4))

trigger_types = [
    ("Scheduled\n(daily / weekly / monthly)",
     COLOR_BLUE, "predictable\nblind to drift"),
    ("Drift-based\n(input distribution change)",
     COLOR_ORANGE, "responsive to drift\nfalse-positive risk"),
    ("Performance-based\n(metric drop)",
     COLOR_RED, "reactive: damage\nis already done"),
    ("Manual / event-based\n(release, policy change)",
     COLOR_GREEN, "human-in-the-loop\nnot scalable"),
]

for ax, (name, color, comment) in zip(axes, trigger_types):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xticks([]); ax.set_yticks([])
    rect = patches.Rectangle((0.05, 0.4), 0.9, 0.3, facecolor=color, alpha=0.7,
                              edgecolor="black", linewidth=1.5)
    ax.add_patch(rect)
    ax.text(0.5, 0.55, name, ha="center", va="center", fontsize=10, color="white",
            fontweight="bold")
    ax.text(0.5, 0.2, comment, ha="center", va="center", fontsize=9, style="italic")
plt.suptitle("4 retraining triggers: when to start retraining?", y=1.02)
plt.tight_layout()
save("retraining_triggers.svg")


# ============================================================
# Fig 2: Model decay over time WITH vs WITHOUT retraining
# ============================================================
days = np.arange(0, 365)
# No retraining: gradual decay due to drift
rng = np.random.default_rng(0)
acc_no_retrain = 0.91 - 0.001 * days + rng.normal(0, 0.005, len(days))
# Periodic retraining (every 30 days): saw-tooth pattern
acc_retrain = np.zeros_like(days, dtype=float)
for i in range(len(days)):
    days_since_retrain = i % 30
    acc_retrain[i] = 0.91 - 0.001 * days_since_retrain + rng.normal(0, 0.005)

plt.figure(figsize=(10, 4.5))
plt.plot(days, acc_no_retrain, color=COLOR_RED, lw=2, label="No retraining")
plt.plot(days, acc_retrain, color=COLOR_GREEN, lw=2, label="Retrain every 30 days")
# Mark retrain events
for d in range(0, 365, 30):
    plt.axvline(d, color=COLOR_GREEN, ls=":", lw=0.6, alpha=0.6)
plt.axhline(0.85, color="black", lw=1, ls="--", label="SLO threshold (0.85)")
plt.xlabel("days in production")
plt.ylabel("test accuracy")
plt.title("Retraining keeps the model above SLO; no-retrain drifts below")
plt.legend(loc="lower left")
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("retraining_decay_vs_retrain.svg")


# ============================================================
# Fig 3: Pipeline cost vs degradation cost tradeoff
# ============================================================
intervals = [1, 3, 7, 14, 30, 60, 90, 180]
# Cost of retraining itself (compute + engineering)
retrain_cost = [50_000, 20_000, 10_000, 5_500, 3_000, 1_700, 1_200, 700]
# Cost of degraded predictions per day (depends on how stale the model is)
# Approximation: stale_cost grows roughly quadratically with interval
stale_cost = [200, 600, 1_400, 2_500, 5_000, 12_000, 25_000, 60_000]
total_cost = [r + s for r, s in zip(retrain_cost, stale_cost)]

plt.figure(figsize=(9, 4.5))
plt.plot(intervals, retrain_cost, "o-", color=COLOR_BLUE, lw=2, label="Retraining cost")
plt.plot(intervals, stale_cost, "s-", color=COLOR_RED, lw=2, label="Stale-model cost")
plt.plot(intervals, total_cost, "^-", color=COLOR_GREEN, lw=2.5, label="Total cost")
# Find min
min_idx = np.argmin(total_cost)
plt.axvline(intervals[min_idx], color="black", ls="--", lw=1,
            label=f"sweet spot: {intervals[min_idx]} days")
plt.xscale("log")
plt.xlabel("retraining interval (days, log scale)")
plt.ylabel("monthly cost (USD)")
plt.title("Tradeoff: too often = expensive retraining, too rare = expensive staleness")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("retraining_cost_tradeoff.svg")


# ============================================================
# Fig 4: Champion-challenger evaluation gates
# ============================================================
fig, ax = plt.subplots(figsize=(11, 5))

gates = [
    (1, "1. Schema check\n(input/output columns)", COLOR_BLUE, True),
    (2.3, "2. Smoke test\n(predict 100 samples)", COLOR_BLUE, True),
    (3.6, "3. Holdout eval\n(test acc ≥ champion?)", COLOR_BLUE, True),
    (5.0, "4. Shadow test\n(2 days mirror traffic)", COLOR_ORANGE, True),
    (6.3, "5. Canary 5% \n(metric watch)", COLOR_ORANGE, True),
    (7.7, "6. Canary 50%\n(metric watch)", COLOR_ORANGE, True),
    (9.0, "7. 100% rollout\n+ keep champion as fallback", COLOR_GREEN, True),
]

ax.axhline(0.5, color="black", lw=1, alpha=0.4)
for x, label, color, passed in gates:
    marker = "o" if passed else "X"
    ax.scatter([x], [0.5], s=600, color=color, marker=marker,
               edgecolor="black", linewidth=1.5, zorder=5)
    ax.annotate(label, (x, 0.5), xytext=(x, 0.85 if x % 2 == 0 else 0.15),
                ha="center", fontsize=9,
                arrowprops=dict(arrowstyle="-", color="gray", lw=0.6))

ax.text(10.2, 0.5, "→ Promote\nto Production",
        fontsize=10, color=COLOR_GREEN, fontweight="bold")
ax.set_xlim(0, 11)
ax.set_ylim(0, 1)
ax.set_xticks([]); ax.set_yticks([])
ax.set_title("7-gate evaluation: any failure → halt + alert + rollback")
plt.tight_layout()
save("retraining_evaluation_gates.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
