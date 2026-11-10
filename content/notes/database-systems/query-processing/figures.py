"""Query Processing ノートの図を lab/output.txt（PostgreSQL 17 の実測）から生成する。

lab/run.sh > lab/output.txt で実測し直してから、次で再生成する。
    uv run --with matplotlib python content/notes/database-systems/query-processing/figures.py
"""

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
OUTPUT = (HERE / "lab" / "output.txt").read_text(encoding="utf-8")
USERS = 10000  # lab/experiment.sql の users の件数

INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
plt.rcParams.update({
    "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "query-processing",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    # 条件の値 '東京' をそのまま出すため、日本語の字形を持つフォントを後ろに足す。
    "font.family": ["DejaVu Sans", "Noto Sans CJK JP"],
})


def section(title: str) -> str:
    start = OUTPUT.index(title)
    end = OUTPUT.find("\n== ", start + 1)
    return OUTPUT[start:end if end != -1 else None]


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(HERE / "images" / name, metadata={"Date": None})
    plt.close(fig)


def selectivity_figure():
    """条件ごとの推定レコード数と実際のレコード数（EXPLAIN ANALYZE）。"""
    pair = re.compile(r"rows=(\d+) width=\d+\) \(actual rows=(\d+)")
    plain = pair.findall(section("== selectivity: no extended statistics"))
    stats = pair.findall(section("== selectivity: with CREATE STATISTICS"))
    cases = [
        ("country = 'JP'", plain[0]),
        ("city = '東京'", plain[1]),
        ("country AND city", plain[2]),
        ("country AND city\n+ CREATE STATISTICS", stats[0]),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    w = 0.36
    for i, (_, (est, act)) in enumerate(cases):
        for dx, value, color in ((-w / 2, int(est), ACCENT), (w / 2, int(act), RED)):
            ax.bar(i + dx, value / USERS, width=w, color=color)
            ax.text(i + dx, value / USERS * 1.25, f"{value:,}", ha="center", fontsize=10,
                    color=SUB)
    ax.bar(0, 0, color=ACCENT, label="estimated rows")
    ax.bar(0, 0, color=RED, label="actual rows")
    ax.set_yscale("log")
    ax.set_ylim(5e-5, 0.1)
    ax.set_yticks([1e-4, 1e-3, 1e-2, 1e-1], ["0.01%", "0.1%", "1%", "10%"])
    ax.set_ylabel(f"Rows / {USERS:,} users")
    ax.set_xticks(range(len(cases)), [label for label, _ in cases], fontsize=10)
    ax.legend(frameon=False, loc="upper right", fontsize=10, ncols=2)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "query_processing_selectivity.svg")


def plan_cost_figure():
    """3 候補の見積もりコスト（EXPLAIN）と実行時間の中央値（EXPLAIN ANALYZE 5 回）。"""
    measured = re.compile(r"^ (Hash Join|Nested Loop|Merge Join)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)",
                          re.M)
    rows = {node: (float(cost), float(ms)) for node, cost, ms in measured.findall(OUTPUT)}
    default = section("== plan: default").splitlines()[3].split()[0:2]
    chosen = " ".join(default)
    plans = [  # 下から上に並ぶ
        ("Plan 3: sort both,\nmerge join", "Merge Join"),
        ("Plan 1: seq scan orders,\nhash join", "Hash Join"),
        ("Plan 2: filter users,\nindex lookup", "Nested Loop"),
    ]
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.6), sharey=True)
    for ax, k, unit in ((left, 0, ""), (right, 1, " ms")):
        top = max(rows[node][k] for _, node in plans)
        for i, (_, node) in enumerate(plans):
            value = rows[node][k]
            color = ACCENT if node == chosen else SUB
            ax.barh(i, value, height=0.55, color=color, alpha=1.0 if node == chosen else 0.55)
            label = f"{value:,.0f}{unit}" if value >= 10 else f"{value:,.1f}{unit}"
            ax.text(value + top * 0.03, i, label, va="center", fontsize=10, color=INK)
        ax.set_xlim(0, top * 1.45)
        ax.xaxis.set_major_locator(plt.MaxNLocator(3))
        ax.xaxis.set_major_formatter(lambda x, _: f"{x:,.0f}")
        ax.spines[["top", "right"]].set_visible(False)
    left.set_yticks(range(len(plans)), [label for label, _ in plans], fontsize=10)
    left.set_xlabel("Estimated cost (EXPLAIN)")
    right.set_xlabel("Execution time, median of 5 (ms)")
    left.text(rows[chosen][0] + left.get_xlim()[1] * 0.2, 2, "chosen", va="center",
              fontsize=10, color=ACCENT)
    save(fig, "query_processing_plan_cost.svg")


def order_figure():
    """注文の並び（利用者ごとに連続／散らす）で、候補 1 と候補 2 の見積もりコストが入れ替わる。"""
    top = re.compile(r"^ (Hash Join|Nested Loop)\s+\(cost=[\d.]+\.\.([\d.]+)", re.M)
    clustered = {node: float(cost) for node, cost in top.findall(
        section("== plan 1:") + section("== plan 2:"))}
    scattered_text = section("== orders_scattered")
    scattered = {node: float(cost) for node, cost in top.findall(scattered_text)}
    chosen_scattered = top.search(scattered_text).group(1)  # 先頭はプランナの既定の選択
    chosen_clustered = section("== plan: default").splitlines()[3].split()[0:2]
    chosen_clustered = " ".join(chosen_clustered)
    groups = [("Orders stored\nper user", clustered, chosen_clustered),
              ("Orders scattered\nacross users", scattered, chosen_scattered)]
    plans = [("Plan 1: hash join", "Hash Join"), ("Plan 2: index lookup", "Nested Loop")]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    w = 0.36
    for g, (_, costs, chosen) in enumerate(groups):
        for j, (label, node) in enumerate(plans):
            x = g + (j - 0.5) * w
            value = costs[node]
            is_chosen = node == chosen
            ax.bar(x, value, width=w * 0.9, color=ACCENT if is_chosen else SUB,
                   alpha=1.0 if is_chosen else 0.55)
            ax.text(x, value + 600, f"{value:,.0f}", ha="center", fontsize=10, color=INK)
            ax.text(x, -1500, label.split(": ")[0], ha="center", va="top", fontsize=10,
                    color=SUB)
            if is_chosen:
                ax.text(x, value + 2600, "chosen", ha="center", fontsize=10, color=ACCENT)
    ax.set_xticks(range(len(groups)), [label for label, _, _ in groups], fontsize=10)
    ax.tick_params(axis="x", length=0, pad=22)
    ax.set_ylim(0, 27000)
    ax.set_ylabel("Estimated cost (EXPLAIN)")
    ax.yaxis.set_major_formatter(lambda y, _: f"{y:,.0f}")
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "query_processing_order.svg")


if __name__ == "__main__":
    selectivity_figure()
    plan_cost_figure()
    order_figure()
