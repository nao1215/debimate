"""モデルレジストリノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/model-registry_gen.py

ノートの lab/run.py を lab/requirements.txt の環境（Python 3.12）で実際に実行し、
その出力から図を描く。MLflow の取得に初回はネットワークが必要。
生成画像は projects/ml/notes/mlops/model-registry/ に直接保存される。
"""
import os
import re
import subprocess

import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 12, "svg.hashsalt": "debimate"})

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "notes", "mlops", "model-registry"
)
LAB_DIR = os.path.join(NOTE_DIR, "lab")


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


result = subprocess.run(
    ["uv", "run", "--no-project", "--python", "3.12",
     "--with-requirements", "requirements.txt", "python", "run.py"],
    cwd=LAB_DIR, capture_output=True, text=True, check=True,
)
rows = re.findall(r"^(.+): alias=v(\d+), prediction=([\d.]+)$", result.stdout, re.M)
assert len(rows) == 5, result.stdout
print("\n".join(f"{label}: alias=v{v}, prediction={p}" for label, v, p in rows))

labels = [label for label, _, _ in rows]
alias = [int(v) for _, v, _ in rows]
pred = [float(p) for _, _, p in rows]
# x=4 の入力に対し、v1 (y=x) は 4、v2 (y=2x) は 8 を返す
loaded = [{4.0: 1, 8.0: 2}[p] for p in pred]

xs = range(len(rows))
fig, ax = plt.subplots(figsize=(8, 3.6))
for x, a, m in zip(xs, alias, loaded):
    if a != m:
        ax.axvspan(x - 0.4, x + 0.4, color=COLOR_RED, alpha=0.12, linewidth=0)
ax.plot(xs, alias, color=COLOR_BLUE, marker="o", markersize=12, linewidth=2.5,
        label="champion alias points to")
ax.plot(xs, loaded, color=COLOR_RED, marker="s", markersize=8, linewidth=2,
        linestyle="--", label="model in memory (resident)")
for x, m, p in zip(xs, loaded, pred):
    ax.annotate(f"pred={p:g}", (x, m), textcoords="offset points",
                xytext=(0, -24 if m == 1 else 16), ha="center", fontsize=10)
ax.set_xticks(list(xs), [label.replace(" ", "\n", 1) for label in labels], fontsize=9)
ax.set_yticks([1, 2], ["v1 (y=x)", "v2 (y=2x)"])
ax.set_ylim(0.4, 2.6)
ax.set_xlim(-0.5, len(rows) - 0.5)
ax.set_title("Moving the alias does not swap the loaded model (red = mismatch)",
             fontsize=11)
ax.legend(loc="upper left", fontsize=9, frameon=False)
plt.tight_layout()
save("model-registry_alias_vs_loaded.svg")
