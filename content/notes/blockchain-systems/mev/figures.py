"""MEV ノートの図を生成する。

lab/sandwich.py と同じ計算で、slippage tolerance ごとの被害額と攻撃者の利益を描く。

再生成:
    uv run --with matplotlib python content/notes/blockchain-systems/mev/figures.py
"""

import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lab"))
from sandwich import ETH, USDC, min_out, sweep_point  # noqa: E402

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GRAY = "#666666"

plt.rcParams.update({
    "figure.figsize": (6.4, 3.8),
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "-",
    "grid.linewidth": 0.5,
    "savefig.bbox": "tight",
    "savefig.dpi": 144,
    "svg.hashsalt": "mev",
})


def slippage_figure():
    victim = 10_000 * USDC
    quote = min_out(victim, 0)
    bps_list = list(range(10, 501, 10))
    loss, profit = [], []
    for bps in bps_list:
        r = sweep_point(victim, bps)
        loss.append((quote - r["A"]) * 3_000 / ETH)  # 3,000 USDC/ETH で換算
        profit.append(r["profit"] / USDC)
    x = [b / 100 for b in bps_list]

    fig, ax = plt.subplots()
    ax.plot(x, loss, color=COLOR_RED, linestyle="--", linewidth=2,
            label="Victim loss (USDC at 3,000/ETH)")
    ax.plot(x, profit, color=COLOR_BLUE, linewidth=2.2,
            label="Attacker profit (USDC, before gas)")
    ax.fill_between(x, profit, loss, color="#f2f2f2")
    ax.text(3.3, 215, "gap ≈ pool fees on\nthe attacker's 2 swaps", color=COLOR_GRAY,
            fontsize=10, ha="center")
    ax.set_xlabel("Slippage tolerance (%)")
    ax.set_ylabel("USDC")
    ax.set_xlim(0, 5.1)
    ax.set_ylim(0, None)
    ax.legend(loc="upper left", frameon=False)
    fig.savefig(HERE / "images" / "mev_slippage.svg", metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    slippage_figure()
