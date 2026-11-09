"""Generate the cross-validation figures. Run: uv run python scripts/notes/cross-validation_gen.py

cross_validation_split.svg is not generated here (no source was kept when it was added).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_regression
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, KFold

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes/ml/cross-validation"
NOTE_DIR.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def save(name):
    path = NOTE_DIR / name
    plt.savefig(path, bbox_inches="tight", metadata={"Date": None})
    # Remove trailing whitespace so `git diff --check` passes.
    _svg_path = Path(path)
    if _svg_path.suffix == ".svg":
        _svg_path.write_text("\n".join(line.rstrip() for line in _svg_path.read_text().splitlines()) + "\n")
    plt.close()
    path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")


# Same data and grid as the code in index.md; only n_samples differs between the two curves.
alphas = np.logspace(-2, 3, 20)
cv = KFold(n_splits=5, shuffle=True, random_state=0)
results = {}
for n_samples in (60, 300):
    X, y = make_regression(n_samples=n_samples, n_features=50, n_informative=10,
                           noise=20, random_state=0)
    grid = GridSearchCV(Ridge(), param_grid={"alpha": alphas}, cv=cv, scoring="r2").fit(X, y)
    results[n_samples] = grid
    print(f"n_samples={n_samples}: best alpha={grid.best_params_['alpha']:.4g}  "
          f"best CV R2={grid.best_score_:.3f}")

fig, ax = plt.subplots(figsize=(6, 3.7))
styles = {60: ("#537c91", "o", "60 samples"), 300: ("#8a8a8a", "s", "300 samples")}
for n_samples, grid in results.items():
    color, marker, label = styles[n_samples]
    ax.errorbar(alphas, grid.cv_results_["mean_test_score"], yerr=grid.cv_results_["std_test_score"],
                color=color, marker=marker, markersize=4, capsize=2, label=f"{label} / 50 features")
best = results[60].best_params_["alpha"]
ax.axvline(best, color="#537c91", linestyle="--", linewidth=1,
           label=f"best alpha (60 samples) = {best:.2f}")
ax.set_xscale("log")
ax.set_xlabel("Ridge alpha (regularization strength)")
ax.set_ylabel("5-fold CV R² (mean ± std)")
ax.set_ylim(-0.45, 1.05)
ax.grid(alpha=0.25)
ax.legend(frameon=False, fontsize=8, loc="lower center")
plt.tight_layout()
save("cross_validation_alpha.svg")
