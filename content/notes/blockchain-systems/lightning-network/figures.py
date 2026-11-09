"""Lightning Network ノートの図を生成する。

lab/simulate.py が書いた lab/result.json を読んでプロットする。

再生成:
    python3 content/notes/blockchain-systems/lightning-network/lab/simulate.py
    uv run --with matplotlib python content/notes/blockchain-systems/lightning-network/figures.py
"""

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR_BLUE = "#7aa6c2"
COLOR_GRAY = "#666666"
COLOR_TEXT = "#1f1f1f"

plt.rcParams.update({
    "figure.figsize": (6.4, 4),
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.5,
    "savefig.bbox": "tight",
    "savefig.dpi": 144,
    "svg.hashsalt": "lightning-network",
})

HERE = pathlib.Path(__file__).parent
OUT = HERE / "images"
OUT.mkdir(exist_ok=True)


def payment_success() -> None:
    data = json.loads((HERE / "lab" / "result.json").read_text())
    amounts = data["amounts"]
    styles = {
        "1": dict(color=COLOR_GRAY, marker="o", linestyle="-"),
        "2": dict(color=COLOR_GRAY, marker="s", linestyle=":"),
        "4": dict(color=COLOR_BLUE, marker="^", linestyle=":"),
        "8": dict(color=COLOR_BLUE, marker="D", linestyle="-"),
    }
    fig, ax = plt.subplots()
    for k, rates in data["success"].items():
        label = "single path" if k == "1" else f"split into {k} parts"
        ax.plot(amounts, [r * 100 for r in rates], label=label, **styles[k])
    ax.plot(amounts, [r * 100 for r in data["bound"]], color=COLOR_TEXT,
            linestyle="--", linewidth=1, label="endpoint balance bound")
    ax.set_xscale("log")
    ax.set_xlabel("Payment amount (sat)")
    ax.set_ylabel("Success rate (%)")
    ax.set_ylim(-3, 103)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    fig.savefig(OUT / "lightning_payment_success.svg", metadata={"Date": None})
    plt.close(fig)
    print("wrote", OUT / "lightning_payment_success.svg")


if __name__ == "__main__":
    payment_success()
