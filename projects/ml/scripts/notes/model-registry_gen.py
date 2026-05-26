"""model-registry ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/model-registry_gen.py
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
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/mlops/model-registry"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Model version timeline with stage transitions
# ============================================================
fig, ax = plt.subplots(figsize=(11, 4.5))

# Y axis: stages
stages = ["Archived", "None", "Staging", "Production"]
y_map = {s: i for i, s in enumerate(stages)}

# Each version's lifecycle: (version, [(stage, start_day, end_day)])
versions = [
    ("v1", [("None", 0, 5), ("Staging", 5, 12), ("Production", 12, 45),
             ("Archived", 45, 90)]),
    ("v2", [("None", 25, 30), ("Staging", 30, 38), ("Production", 38, 60),
             ("Archived", 60, 90)]),
    ("v3", [("None", 50, 55), ("Staging", 55, 60), ("Archived", 60, 90)]),
    ("v4", [("None", 55, 62), ("Staging", 62, 68), ("Production", 68, 90)]),
]
colors = {"None": COLOR_GRAY, "Staging": COLOR_ORANGE,
          "Production": COLOR_GREEN, "Archived": "#888888"}

for ver, transitions in versions:
    for stage, start, end in transitions:
        rect = patches.Rectangle((start, y_map[stage] - 0.3), end - start, 0.6,
                                  color=colors[stage], alpha=0.8,
                                  edgecolor="white", linewidth=1.5)
        ax.add_patch(rect)
        ax.text((start + end) / 2, y_map[stage], ver,
                ha="center", va="center", fontsize=9, color="white",
                fontweight="bold")

ax.set_yticks(range(len(stages))); ax.set_yticklabels(stages)
ax.set_xlim(0, 95); ax.set_ylim(-0.6, len(stages) - 0.4)
ax.set_xlabel("day since project start")
ax.set_title("Model version lifecycle: registry tracks stage transitions")
ax.grid(True, alpha=0.25, axis="x")
# Legend
from matplotlib.patches import Patch
legend = [Patch(facecolor=colors[s], label=s) for s in stages]
ax.legend(handles=legend, loc="upper right", ncol=4, fontsize=9)
plt.tight_layout()
save("registry_version_timeline.svg")


# ============================================================
# Fig 2: Naked file storage vs Model registry (concept)
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Naked file storage
ax = axes[0]
files = [
    "model_v1.pkl", "model_v2.pkl", "model_v2_final.pkl",
    "model_v2_FINAL2.pkl", "best_model.pkl", "model_2025-12-01.pkl",
    "model_for_test.pkl", "model_takashi_branch.pkl",
]
for i, f in enumerate(files):
    color = COLOR_RED if "FINAL" in f or "final" in f else COLOR_GRAY
    rect = patches.Rectangle((0.1, 0.85 - i * 0.1), 0.85, 0.08, facecolor=color, alpha=0.5,
                              edgecolor="black", linewidth=0.8)
    ax.add_patch(rect)
    ax.text(0.52, 0.89 - i * 0.1, f, ha="center", va="center", fontsize=10)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.set_xticks([]); ax.set_yticks([])
ax.set_title("S3 / shared drive (no governance)\n"
             "Which one is in production? Who knows?", fontsize=10)
ax.text(0.5, 0.05, "model files pile up with ambiguous names",
        ha="center", fontsize=9, style="italic", color=COLOR_RED)

# Model registry
ax = axes[1]
header = ["version", "stage", "metric", "owner", "promoted"]
rows = [
    ["v4", "Production", "f1=0.913", "alice", "2026-04-12"],
    ["v3", "Archived", "f1=0.897", "alice", "—"],
    ["v2", "Archived", "f1=0.881", "bob", "—"],
    ["v1", "Archived", "f1=0.842", "alice", "—"],
]
stage_color = {"Production": COLOR_GREEN, "Staging": COLOR_ORANGE,
               "Archived": COLOR_GRAY}
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.set_xticks([]); ax.set_yticks([])

col_x = [0.06, 0.22, 0.43, 0.62, 0.78]
# Header
for x, h in zip(col_x, header):
    ax.text(x, 0.88, h, fontsize=10, fontweight="bold")
ax.axhline(0.84, color="black", lw=0.7)
for i, row in enumerate(rows):
    y = 0.78 - i * 0.10
    for x, cell in zip(col_x, row):
        bg = None
        if cell in stage_color:
            rect = patches.Rectangle((x - 0.015, y - 0.025), 0.13, 0.05,
                                      facecolor=stage_color[cell], alpha=0.5,
                                      edgecolor="none")
            ax.add_patch(rect)
        ax.text(x, y, cell, fontsize=9.5)
ax.set_title("Model registry: stage, version, metric, owner, history\n"
             "Anyone can answer: 'what's running in production'", fontsize=10)
ax.text(0.5, 0.05, "single source of truth, with stage transitions and audit trail",
        ha="center", fontsize=9, style="italic", color=COLOR_GREEN)

plt.tight_layout()
save("registry_vs_naked_files.svg")


# ============================================================
# Fig 3: Champion-Challenger rollback flow (sequence-like)
# ============================================================
fig, ax = plt.subplots(figsize=(11, 5.5))

events = [
    ("Day 0", "v4 promoted to Production\n(champion)", COLOR_GREEN, 0),
    ("Day 14", "v5 trained, promoted to Staging\n(challenger)", COLOR_ORANGE, 1),
    ("Day 21", "Shadow test: v5 predictions logged\nbut not served", COLOR_BLUE, 1),
    ("Day 28", "Canary rollout: 5% traffic → v5", COLOR_ORANGE, 1.5),
    ("Day 30", "v5 metric drop detected\n(f1 0.88 → 0.84)", COLOR_RED, 1.5),
    ("Day 30", "Rollback: traffic → v4 (1 click)", COLOR_GREEN, 0),
    ("Day 30", "v5 status: Archived", COLOR_GRAY, -1),
]

for i, (when, what, color, y) in enumerate(events):
    x = 1 + i * 1.5
    ax.scatter([x], [y], s=400, color=color, zorder=5, edgecolor="black", linewidth=1)
    ax.annotate(f"{when}\n{what}", (x, y), xytext=(x, y + 0.5 if y >= 0 else y - 0.5),
                ha="center", fontsize=8.5,
                arrowprops=dict(arrowstyle="-", color="gray", lw=0.7))

# Lines connecting events
xs = [1 + i * 1.5 for i in range(len(events))]
ys = [e[3] for e in events]
ax.plot(xs, ys, color="black", lw=0.8, alpha=0.4, zorder=1)

ax.set_xlim(0, 12)
ax.set_ylim(-2, 3)
ax.set_yticks([-1, 0, 1, 1.5])
ax.set_yticklabels(["Archived", "Production", "Staging", "Canary"])
ax.set_xlabel("time →")
ax.set_title("Champion-Challenger pattern: registry enables 1-click rollback")
ax.grid(True, alpha=0.25, axis="x")
plt.tight_layout()
save("registry_champion_challenger.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
