"""Generate the RandomForest figures. Run: uv run python scripts/notes/random-forest_gen.py"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes/ml/random-forest"
NOTE_DIR.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

def save(name):
    path = NOTE_DIR / name
    plt.savefig(path, bbox_inches="tight", metadata={"Date": None})
    plt.close()
    path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")

X, y = make_classification(n_samples=900, n_features=10, n_informative=5,
                           n_redundant=2, class_sep=0.8, flip_y=0.08, random_state=12)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.35, stratify=y, random_state=12)
tree_scores, forest_scores = [], []
for seed in range(24):
    indices = np.random.default_rng(seed).choice(len(X_train), len(X_train), replace=True)
    tree = DecisionTreeClassifier(random_state=seed).fit(X_train[indices], y_train[indices])
    forest = RandomForestClassifier(n_estimators=200, max_features="sqrt", random_state=seed,
                                    n_jobs=1).fit(X_train[indices], y_train[indices])
    tree_scores.append(accuracy_score(y_test, tree.predict(X_test)))
    forest_scores.append(accuracy_score(y_test, forest.predict(X_test)))
fig, ax = plt.subplots(figsize=(6, 3.5))
box = ax.boxplot([tree_scores, forest_scores], tick_labels=["single tree", "random forest"],
                 patch_artist=True, showmeans=True)
for patch, color in zip(box["boxes"], ["#8a8a8a", "#537c91"]):
    patch.set_facecolor(color)
ax.set_ylabel("Test accuracy across 24 bootstrap samples")
ax.set_ylim(0.45, 1.0)
ax.set_title("Averaging reduces bootstrap variation")
plt.tight_layout()
save("random-forest_stability.svg")

sizes, oob_scores, test_scores = [20, 50, 100, 200], [], []
for n_estimators in sizes:
    model = RandomForestClassifier(n_estimators=n_estimators, max_features="sqrt", bootstrap=True,
                                   oob_score=True, random_state=12, n_jobs=1).fit(X_train, y_train)
    oob_scores.append(model.oob_score_)
    test_scores.append(model.score(X_test, y_test))
fig, ax = plt.subplots(figsize=(6, 3.5))
ax.plot(sizes, oob_scores, marker="o", color="#5f8075", label="OOB accuracy")
ax.plot(sizes, test_scores, marker="o", color="#537c91", label="held-out test accuracy")
ax.set_xscale("log")
ax.set_xticks(sizes, labels=[str(value) for value in sizes])
ax.set_xlabel("Number of trees")
ax.set_ylabel("Accuracy")
ax.set_ylim(0.45, 1.0)
ax.legend(frameon=False)
plt.tight_layout()
save("random-forest_oob.svg")
print(f"tree accuracy: mean={np.mean(tree_scores):.3f} sd={np.std(tree_scores):.3f}")
print(f"forest accuracy: mean={np.mean(forest_scores):.3f} sd={np.std(forest_scores):.3f}")
for size, oob, test in zip(sizes, oob_scores, test_scores):
    print(f"trees={size:3d} oob={oob:.3f} test={test:.3f}")
