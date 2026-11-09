"""Generate the hyperparameter-search figure. Run: uv run python scripts/notes/hyperparameter_gen.py"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_regression
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, KFold, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes/ml/hyperparameter"
NOTE_DIR.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

def save(name):
    path = NOTE_DIR / name
    plt.savefig(path, bbox_inches="tight", metadata={"Date": None})
    plt.close()
    path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")

# 150 rows x 60 features (10 informative): few rows per feature, so weak regularization overfits.
X, y = make_regression(n_samples=150, n_features=60, n_informative=10, noise=40, random_state=17)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=17)
alphas = np.logspace(-3, 3, 19)
search = GridSearchCV(make_pipeline(StandardScaler(), Ridge()),
    param_grid={"ridge__alpha": alphas}, cv=KFold(n_splits=5, shuffle=True, random_state=17),
    scoring="r2", return_train_score=True).fit(X_train, y_train)
result = search.cv_results_
test_r2 = search.score(X_test, y_test)
fig, ax = plt.subplots(figsize=(6, 3.7))
ax.semilogx(alphas, result["mean_train_score"], color="#8a8a8a", label="train R²")
ax.errorbar(alphas, result["mean_test_score"], yerr=result["std_test_score"], color="#537c91",
            marker="o", capsize=2, label="5-fold CV R²")
ax.axvline(search.best_params_["ridge__alpha"], color="#5f8075", linestyle="--",
           label=f"selected alpha={search.best_params_['ridge__alpha']:.3g}")
ax.set_xlabel("Ridge alpha")
ax.set_ylabel("R²")
ax.legend(frameon=False, fontsize=8)
plt.tight_layout()
save("hyperparameter_search.svg")
for i in range(0, len(alphas), 3):
    print(f"alpha={alphas[i]:>7g}  train R²={result['mean_train_score'][i]:.3f}  "
          f"CV R²={result['mean_test_score'][i]:.3f} ± {result['std_test_score'][i]:.3f}")
print(f"selected alpha={search.best_params_['ridge__alpha']:g}")
print(f"test R²={test_r2:.3f}")
