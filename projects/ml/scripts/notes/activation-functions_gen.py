"""activation-functions ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/activation-functions_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_PURPLE = "#b07aa1"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/activation-functions"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Common activation function shapes
# ============================================================
x = np.linspace(-5, 5, 400)
sigmoid = 1 / (1 + np.exp(-x))
tanh = np.tanh(x)
relu = np.maximum(0, x)
leaky_relu = np.where(x > 0, x, 0.1 * x)
gelu = 0.5 * x * (1 + np.tanh(np.sqrt(2 / np.pi) * (x + 0.044715 * x ** 3)))
step = np.where(x > 0, 1, 0).astype(float)

fig, axes = plt.subplots(2, 3, figsize=(13, 7))
for ax, (name, y_func, color) in zip(axes.ravel(), [
    ("step (classic perceptron)", step, COLOR_GRAY),
    ("sigmoid: 1/(1+e^-x)", sigmoid, COLOR_BLUE),
    ("tanh", tanh, COLOR_GREEN),
    ("ReLU: max(0, x)", relu, COLOR_RED),
    ("Leaky ReLU (α=0.1)", leaky_relu, COLOR_ORANGE),
    ("GELU", gelu, COLOR_PURPLE),
]):
    ax.plot(x, y_func, color=color, lw=2.5)
    ax.axhline(0, color="black", lw=0.5)
    ax.axvline(0, color="black", lw=0.5)
    ax.set_title(name, fontsize=10)
    ax.set_xlim(-5, 5)
    ax.set_ylim(-1.5, 5.2)
    ax.grid(True, alpha=0.25)
plt.suptitle("6 activation functions: shape determines what the network can express",
             y=1.0, fontsize=12)
plt.tight_layout()
save("activations_shapes.svg")


# ============================================================
# Fig 2: Gradients (derivative) - vanishing gradient problem
# ============================================================
sigmoid_grad = sigmoid * (1 - sigmoid)
tanh_grad = 1 - tanh ** 2
relu_grad = np.where(x > 0, 1, 0).astype(float)
leaky_grad = np.where(x > 0, 1, 0.1)
gelu_grad_approx = np.gradient(gelu, x[1] - x[0])

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(x, sigmoid_grad, color=COLOR_BLUE, lw=2.2, label="sigmoid' (max=0.25)")
ax.plot(x, tanh_grad, color=COLOR_GREEN, lw=2.2, label="tanh' (max=1.0)")
ax.plot(x, relu_grad, color=COLOR_RED, lw=2.2, label="ReLU' (1 or 0)")
ax.plot(x, leaky_grad, color=COLOR_ORANGE, lw=2.2, label="Leaky ReLU' (1 or α)")
ax.plot(x, gelu_grad_approx, color=COLOR_PURPLE, lw=2.2, label="GELU'")
ax.axhline(0, color="black", lw=0.5)
ax.axhline(1, color="black", ls=":", lw=0.7, alpha=0.5)
ax.set_xlim(-5, 5)
ax.set_ylim(-0.15, 1.3)
ax.set_xlabel("input z")
ax.set_ylabel("gradient da/dz")
ax.set_title("Derivative of each activation: sigmoid/tanh saturate → vanishing gradient")
ax.legend(loc="lower right")
ax.grid(True, alpha=0.25)
plt.tight_layout()
save("activations_gradients.svg")


# ============================================================
# Fig 3: Decision boundary - same MLP architecture, different activations
# ============================================================
from sklearn.datasets import make_moons
from sklearn.neural_network import MLPClassifier

X, y = make_moons(n_samples=400, noise=0.2, random_state=0)
xx, yy = np.meshgrid(np.linspace(-1.5, 2.5, 250), np.linspace(-1.2, 1.7, 250))

activations = ["logistic", "tanh", "relu"]
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for ax, act in zip(axes, activations):
    mlp = MLPClassifier(hidden_layer_sizes=(8, 8), activation=act,
                        max_iter=3000, random_state=0).fit(X, y)
    Z = mlp.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
    ax.contourf(xx, yy, Z, alpha=0.25, cmap="coolwarm")
    ax.scatter(X[:, 0], X[:, 1], c=y, cmap="coolwarm", edgecolor="white", s=25)
    acc = mlp.score(X, y)
    ax.set_title(f"activation={act}  train_acc={acc:.3f}", fontsize=11)
    ax.set_xlabel("x1"); ax.set_ylabel("x2")
plt.suptitle("Same architecture (8,8), same data — boundary shape depends on activation",
             y=1.02)
plt.tight_layout()
save("activations_decision_boundary.png")


# ============================================================
# Fig 4: Vanishing gradient simulation - 5-layer net loss curves
# ============================================================
# Simulate: 5-layer MLP on a simple regression, compare sigmoid vs ReLU
# Use synthetic 1D regression
rng = np.random.default_rng(0)
n = 1000
X_data = rng.uniform(-3, 3, (n, 1))
y_data = np.sin(X_data.squeeze()) + 0.1 * rng.normal(size=n)

epochs = []
train_loss_sigmoid = []
train_loss_relu = []

for act in ["logistic", "relu"]:
    mlp = MLPClassifier(hidden_layer_sizes=(16, 16, 16, 16, 16),
                        activation=act, solver="adam",
                        max_iter=1, warm_start=True, random_state=0,
                        learning_rate_init=0.01)
    # MLPClassifier is for classification; use MLPRegressor instead
from sklearn.neural_network import MLPRegressor

def train_curve(activation, n_epochs=80):
    mlp = MLPRegressor(hidden_layer_sizes=(16, 16, 16, 16, 16),
                       activation=activation, solver="adam",
                       max_iter=1, warm_start=True, random_state=0,
                       learning_rate_init=0.01)
    losses = []
    for _ in range(n_epochs):
        mlp.fit(X_data, y_data)
        losses.append(mlp.loss_)
    return losses

losses_sigmoid = train_curve("logistic")
losses_relu = train_curve("relu")
losses_tanh = train_curve("tanh")

epochs_arr = np.arange(1, len(losses_sigmoid) + 1)
plt.figure(figsize=(9, 4.5))
plt.plot(epochs_arr, losses_sigmoid, color=COLOR_BLUE, lw=2, label="sigmoid (5 layers)")
plt.plot(epochs_arr, losses_tanh, color=COLOR_GREEN, lw=2, label="tanh (5 layers)")
plt.plot(epochs_arr, losses_relu, color=COLOR_RED, lw=2, label="ReLU (5 layers)")
plt.xlabel("epoch")
plt.ylabel("training MSE")
plt.title("Deep net training: sigmoid converges slowly (vanishing gradient), ReLU is fastest")
plt.yscale("log")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("activations_training_curves.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
