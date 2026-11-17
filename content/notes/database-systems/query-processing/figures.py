"""Query Processing のノートの図（WebP）を描く。

数値の図は lab/result.json（lab/run.py の出力）から描く。
実行: python3 content/notes/database-systems/query-processing/figures.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"
R = json.loads((HERE / "lab" / "result.json").read_text())

for path in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if Path(path).exists():
        font_manager.fontManager.addfont(path)
plt.rcParams["font.family"] = ["Noto Sans CJK JP", "DejaVu Sans"]
plt.rcParams["font.size"] = 12

INK, SUB, GRID = "#1f1f1f", "#666666", "#dddddd"
BLUE, BLUE_PALE = "#4e79a7", "#e3ecf5"
RED, RED_PALE = "#d1495b", "#f8e1e4"
FILL = "#f2f2f2"


def save(fig, name):
    png = IMAGES / (name + ".png")
    fig.savefig(png, dpi=200, facecolor="#ffffff", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    Image.open(png).convert("RGB").save(IMAGES / (name + ".webp"), "WEBP", quality=90, method=6)
    png.unlink()


def fmt_ms(ms):
    if ms >= 100:
        return f"{ms:,.0f} ms"
    if ms >= 1:
        return f"{ms:.1f} ms"
    return f"{ms:.2f} ms"


def is_pkey(node):
    return "events_pkey" in node


def limit_figure():
    """表紙: ORDER BY id LIMIT n の n ごとの実行時間と、選ばれた読み方。"""
    rows = R["limit_sweep"]
    labels = [f"{r['limit']:,}" if r["limit"] else "なし" for r in rows]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    for i, r in enumerate(rows):
        color = RED if is_pkey(r["node"]) else BLUE
        parallel = r["node"].startswith("Parallel")
        ax.bar(i, r["ms"], color=color, width=0.62, hatch="///" if parallel else None,
               edgecolor="#ffffff" if parallel else color, linewidth=0)
        ax.text(i, r["ms"] * 1.25, fmt_ms(r["ms"]), ha="center", va="bottom", fontsize=11,
                color=INK)
    ax.set_yscale("log")
    ax.set_ylim(0.5, 20000)
    ax.set_xticks(range(len(rows)), labels)
    ax.set_ylabel("実行時間（対数目盛）")
    ax.set_xlabel("LIMIT の件数")
    ax.set_title("実行した SQL: SELECT * FROM events WHERE user_id = 1 ORDER BY id LIMIT n", fontsize=12,
                 color=INK, pad=12)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.bar(0, 0, color=RED, label="主キーの索引を id の順に読み、user_id で捨てる")
    ax.bar(0, 0, color=RED, hatch="///", edgecolor="#ffffff", linewidth=0,
           label="同じ読み方を複数のプロセスで分けて読む（並列）")
    ax.bar(0, 0, color=BLUE, label="user_id の索引で 10,000 行を集めて並べ替える")
    ax.legend(loc="upper right", frameon=False, fontsize=11)
    save(fig, "qp_limit")


def stages_figure():
    """SQL から結果までの段階と、各段階が次へ渡すもの。"""
    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.set_xlim(0, 110)
    ax.set_ylim(0, 36)
    ax.axis("off")
    stages = [("パーサー", "文法を解析する"), ("アナライザと\nリライタ", "表と列を解決し\nビューを展開"),
              ("プランナ", "候補を比べて\n1 つ選ぶ"), ("エグゼキュータ", "計画どおりに\n行を作る")]
    passed = ["SQL 文", "構文木", "問い合わせ\nツリー", "実行計画", "結果の行"]
    x0, w, gap = 13, 16.5, 7.2
    xs = [x0 + i * (w + gap) for i in range(4)]
    for i, (name, desc) in enumerate(stages):
        hot = name == "プランナ"
        ax.add_patch(FancyBboxPatch((xs[i], 15), w, 13, boxstyle="round,pad=0.4",
                                    fc=RED_PALE if hot else FILL, ec=RED if hot else INK, lw=1.6))
        ax.text(xs[i] + w / 2, 24.6, name, ha="center", va="center", fontsize=13, color=INK,
                linespacing=1.1)
        ax.text(xs[i] + w / 2, 18.6, desc, ha="center", va="center", fontsize=10.5, color=SUB,
                linespacing=1.25)
    centers = [x0 - 6.5] + [xs[i] + w + gap / 2 for i in range(4)]
    for i, label in enumerate(passed):
        ax.text(centers[i], 31.5, label, ha="center", va="bottom", fontsize=10.5, color=INK,
                linespacing=1.1)
    for i in range(5):
        start = 1 if i == 0 else xs[i - 1] + w + 0.6
        end = xs[i] - 0.6 if i < 4 else 109
        ax.add_patch(FancyArrowPatch((start, 21.5), (end, 21.5), arrowstyle="-|>",
                                     mutation_scale=14, color=INK, lw=1.4))
    px = xs[2] + w / 2
    ax.add_patch(FancyBboxPatch((px - 14, 1.5), 28, 6.5, boxstyle="round,pad=0.3",
                                fc="#ffffff", ec=SUB, lw=1.2, ls="--"))
    ax.text(px, 4.75, "統計情報（列ごとの値の分布）", ha="center", va="center", fontsize=10.5,
            color=INK)
    ax.add_patch(FancyArrowPatch((px, 8.6), (px, 14.4), arrowstyle="-|>", mutation_scale=14,
                                 color=SUB, lw=1.3))
    save(fig, "qp_stages")


def pull_figure():
    """上の節点が下の節点に 1 行ずつ要求する形。Limit は途中で止まり、Sort は止まれない。"""
    sp = R["spread_vs_tail"]["500"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    panels = [
        ("LIMIT 1（利用者 500）", ["Limit", "Index Scan\n（主キーの索引を id 順）"],
         f"{sp['removed'] + 1:,} 行を読んだ所で\n1 行目が見つかり、止まる", RED),
        ("LIMIT 3,000（利用者 1）", ["Limit", "Sort（id で並べる）", "Bitmap Heap Scan\n（user_id の索引）"],
         "Sort は 10,000 行を全部\n受け取るまで 1 行目を返せない", BLUE),
    ]
    for ax, (title, nodes, note, color) in zip(axes, panels):
        ax.set_xlim(0, 50)
        ax.set_ylim(0, 46)
        ax.axis("off")
        ax.text(25, 44, title, ha="center", va="center", fontsize=13, color=INK)
        ys = [33, 20, 7][: len(nodes)]
        for y, n in zip(ys, nodes):
            ax.add_patch(FancyBboxPatch((6, y - 4), 22, 8, boxstyle="round,pad=0.3", fc=FILL,
                                        ec=INK, lw=1.4))
            ax.text(17, y, n, ha="center", va="center", fontsize=11, color=INK, linespacing=1.15)
        for a, b in zip(ys, ys[1:]):
            ax.add_patch(FancyArrowPatch((14, a - 4.6), (14, b + 4.6), arrowstyle="-|>",
                                         mutation_scale=12, color=SUB, lw=1.2))
            ax.add_patch(FancyArrowPatch((20, b + 4.6), (20, a - 4.6), arrowstyle="-|>",
                                         mutation_scale=12, color=color, lw=1.8))
        ax.text(11.5, (ys[0] + ys[1]) / 2, "次の\n1 行を", ha="right", va="center",
                fontsize=10, color=SUB, linespacing=1.1)
        ax.text(22.5, (ys[0] + ys[1]) / 2, "1 行", ha="left", va="center", fontsize=10,
                color=color)
        ax.text(31, ys[-1], note, ha="left", va="center", fontsize=11, color=color,
                linespacing=1.3)
    save(fig, "qp_pull")


def bet_figure():
    """主キーの索引を id 順に読む時、利用者の行がどこにあるか。プランナの想定と実際。"""
    total = 5_000_000
    first = R["user1_first_id"]
    fig, ax = plt.subplots(figsize=(11, 3.9))
    ax.set_xlim(-0.6e6, total * 1.02)
    ax.set_ylim(0, 32)
    ax.axis("off")
    lanes = [
        (24, "利用者 500", "id の全体に散らばる", BLUE, "spread"),
        (15, "利用者 1（想定）", "プランナは散らばっていると見る", SUB, "assumed"),
        (6, "利用者 1（実際）", "最後の 10,000 行に固まる", RED, "tail"),
    ]
    for y, name, desc, color, kind in lanes:
        ax.add_patch(Rectangle((0, y - 1.6), total, 3.2, fc=FILL, ec=GRID, lw=0.8))
        ax.text(-0.08e6, y + 0.6, name, ha="right", va="center", fontsize=11.5, color=INK)
        ax.text(-0.08e6, y - 1.6, desc, ha="right", va="center", fontsize=9.5, color=SUB)
        if kind in ("spread", "assumed"):
            step = 62_500
            for x in range(step // 2, total, step):
                ax.plot([x, x], [y - 1.6, y + 1.6], color=color, lw=1.2,
                        ls="-" if kind == "spread" else (0, (2, 1.5)))
        else:
            ax.add_patch(Rectangle((first, y - 1.6), total - first + 1, 3.2, fc=color, ec=color))
    ax.annotate("", xy=(first, 2.6), xytext=(0, 2.6),
                arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.6))
    ax.text(first / 2, 1.0, f"最初の 1 行に着くまで {first - 1:,} 行を読んで捨てる", ha="center",
            va="center", fontsize=11, color=RED)
    ax.text(0, 28.6, "id = 1", ha="left", va="center", fontsize=10, color=SUB)
    ax.text(total, 28.6, f"id = {total:,}", ha="right", va="center", fontsize=10, color=SUB)
    ax.annotate("", xy=(3.9e6, 28.6), xytext=(0.6e6, 28.6),
                arrowprops=dict(arrowstyle="-|>", color=SUB, lw=1.0))
    ax.text(2.25e6, 29.6, "主キーの索引を読む向き", ha="center", va="bottom", fontsize=10,
            color=SUB)
    save(fig, "qp_bet")


def estimate_figure():
    """関係のある 3 列の条件で、見積もった行の数と実際の行の数。"""
    c = R["correlated"]
    groups = ["customers の絞り込み", "orders との結合"]
    est_b = [c["before"]["filter_estimated"], c["before"]["join_estimated"]]
    est_a = [c["after"]["filter_estimated"], c["after"]["join_estimated"]]
    act = [c["before"]["filter_actual"], c["before"]["join_actual"]]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    w = 0.26
    for i in range(2):
        for off, val, color, hatch in [(-w, est_b[i], RED, None), (0, est_a[i], BLUE, None),
                                       (w, act[i], "#9a9a9a", None)]:
            ax.bar(i + off, val, width=w * 0.92, color=color, hatch=hatch)
            ax.text(i + off, val * 1.2, f"{val:,}", ha="center", va="bottom", fontsize=11)
    ax.set_yscale("log")
    ax.set_ylim(1, 30000)
    ax.set_xticks(range(2), groups)
    ax.set_ylabel("行数（対数目盛）")
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.bar(0, 0, color=RED, label="見積もり（列ごとの統計だけ）")
    ax.bar(0, 0, color=BLUE, label="見積もり（拡張統計情報を足した後）")
    ax.bar(0, 0, color="#9a9a9a", label="実際")
    ax.legend(loc="upper left", frameon=False, fontsize=11)
    ax.set_title("条件: WHERE city = 7 AND pref = 0 AND region = 0", fontsize=12,
                 color=INK, pad=10)
    save(fig, "qp_estimate")


def planning_figure():
    """結合する表の数と、計画を作る時間。"""
    rows = R["planning"]
    n = [r["tables"] for r in rows]
    comma = [r["comma_plan_ms"] for r in rows]
    joined = [r["join_plan_ms"] for r in rows]
    exe = [r["comma_exec_ms"] for r in rows]
    geqo = int(R["settings"]["geqo_threshold"])
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.axvspan(geqo - 0.5, max(n) + 0.5, color=FILL, zorder=0)
    ax.text(geqo + 0.0, max(comma) * 0.97, f"{geqo} 表から\n遺伝的アルゴリズム",
            ha="left", va="top", fontsize=10.5, color=SUB)
    ax.plot(n, comma, marker="o", color=RED, lw=2, label="計画: FROM に表を並べる")
    ax.plot(n, joined, marker="s", color=BLUE, lw=2, label="計画: JOIN で順に書く")
    ax.plot(n, exe, marker="^", color="#9a9a9a", lw=1.6, ls="--", label="実行（FROM に並べた方）")
    peak = max(rows, key=lambda r: r["comma_plan_ms"])
    ax.annotate(fmt_ms(peak["comma_plan_ms"]), xy=(peak["tables"], peak["comma_plan_ms"]),
                xytext=(peak["tables"] - 3.2, peak["comma_plan_ms"] * 0.92), fontsize=11,
                color=RED, arrowprops=dict(arrowstyle="-", color=RED, lw=0.8))
    ax.set_xlabel("結合する表の数")
    ax.set_ylabel("時間（ms）")
    ax.set_xticks(n)
    ax.set_xlim(min(n) - 0.5, max(n) + 0.5)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, fontsize=11)
    save(fig, "qp_planning")


if __name__ == "__main__":
    IMAGES.mkdir(exist_ok=True)
    limit_figure()
    stages_figure()
    pull_figure()
    bet_figure()
    estimate_figure()
    planning_figure()
