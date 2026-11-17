"""NULL のノートの図（WebP）を描く。

数値と並び順は lab/output/results.json と lab/output/perf.json（lab/run.py・lab/perf.py の出力）から描く。
実行: python3 content/notes/database-systems/sql-null/figures.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"
OUT = HERE / "lab" / "output"
R = json.loads((OUT / "results.json").read_text())
PERF = json.loads((OUT / "perf.json").read_text())

for path in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if Path(path).exists():
        font_manager.fontManager.addfont(path)
plt.rcParams["font.family"] = ["Noto Sans CJK JP", "DejaVu Sans"]
plt.rcParams["font.size"] = 12

INK, SUB, GRID = "#1f1f1f", "#666666", "#dddddd"
BLUE, BLUE_PALE = "#4e79a7", "#e3ecf5"
RED, RED_PALE = "#d1495b", "#f8e1e4"
GRAY_PALE = "#eeeeee"
MONO = "DejaVu Sans Mono"

ENGINES = ["postgres", "mysql", "sqlite", "duckdb"]
ENGINE_LABEL = {"postgres": "PostgreSQL", "mysql": "MySQL", "sqlite": "SQLite", "duckdb": "DuckDB"}

MEMBERS = [  # lab/run.py の SCHEMA と同じ
    (1, "sato", "sato@example.com", None),
    (2, "suzuki", "suzuki@example.com", 1),
    (3, "takahashi", None, 1),
    (4, "tanaka", None, None),
    (5, "ito", "ito@example.com", 2),
]
REFERRERS = [m[3] for m in MEMBERS]


def save(fig, name):
    png = IMAGES / (name + ".png")
    fig.savefig(png, dpi=200, facecolor="#ffffff", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    Image.open(png).convert("RGB").save(IMAGES / (name + ".webp"), "WEBP", quality=90, method=6)
    png.unlink()


def chip(ax, x, y, text, kind, w=1.25, h=0.5, size=11):
    face, edge, color = {
        "TRUE": (BLUE_PALE, BLUE, BLUE),
        "FALSE": (GRAY_PALE, SUB, SUB),
        "UNKNOWN": (RED_PALE, RED, RED),
        "plain": ("#ffffff", SUB, INK),
    }[kind]
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=face, ec=edge, lw=1.2))
    ax.text(x, y, text, ha="center", va="center", color=color, fontsize=size,
            family=MONO if kind != "plain" or text.isascii() else None)


def not_in_value(mid):
    """id NOT IN (referrers) を三値論理で評価する（<> を AND でつないだ形）。"""
    if any(r == mid for r in REFERRERS if r is not None):
        return "FALSE"
    if any(r is None for r in REFERRERS):
        return "UNKNOWN"
    return "TRUE"


def not_exists_value(mid):
    return "FALSE" if any(r == mid for r in REFERRERS) else "TRUE"


def cover():
    """表紙: 会員ごとの NOT IN と NOT EXISTS の評価と、残る件数。"""
    q = R["queries"]
    assert all(q["not_in"][e] == "0" for e in ENGINES)
    assert all(q["not_exists"][e] == "3" for e in ENGINES)

    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.6, 6.6)
    ax.axis("off")

    ax.text(0.1, 6.3, "副問い合わせの結果（referred_by の 5 行）", fontsize=12, color=SUB, va="center")
    for i, r in enumerate(REFERRERS):
        chip(ax, 4.9 + i * 1.05, 6.3, "NULL" if r is None else str(r), "UNKNOWN" if r is None else "plain",
             w=0.9, h=0.48)

    ax.text(0.25, 5.4, "会員", fontsize=12, color=SUB, va="center")
    ax.text(5.6, 5.4, "id NOT IN (…)", fontsize=12, color=INK, ha="center", va="center", family=MONO)
    ax.text(8.4, 5.4, "NOT EXISTS (…)", fontsize=12, color=INK, ha="center", va="center", family=MONO)
    ax.plot([0.1, 9.9], [5.05, 5.05], color=GRID, lw=1)

    for i, (mid, name, _email, _ref) in enumerate(MEMBERS):
        y = 4.6 - i * 0.78
        ax.text(0.25, y, f"id={mid}  {name}", fontsize=12, color=INK, va="center", family=MONO)
        a, b = not_in_value(mid), not_exists_value(mid)
        chip(ax, 5.6, y, a, a, w=1.5)
        chip(ax, 8.4, y, b, b, w=1.5)
        if mid in (1, 2):
            ax.text(2.55, y, "誰かを紹介した", fontsize=10, color=SUB, va="center")
        else:
            ax.text(2.55, y, "誰も紹介していない", fontsize=10, color=SUB, va="center")

    ax.plot([0.1, 9.9], [0.95, 0.95], color=GRID, lw=1)
    ax.text(0.25, 0.45, "WHERE で残る行", fontsize=12, color=INK, va="center")
    ax.text(5.6, 0.45, f"{q['not_in']['postgres']} 件", fontsize=17, color=RED, ha="center", va="center")
    ax.text(8.4, 0.45, f"{q['not_exists']['postgres']} 件", fontsize=17, color=BLUE, ha="center", va="center")
    ax.text(7.0, -0.3, "PostgreSQL・MySQL・SQLite・DuckDB で同じ件数", fontsize=10, color=SUB,
            ha="center", va="center")
    save(fig, "sql-null_not_in")


def gates():
    """UNKNOWN（NULL）を受け取った時の、WHERE・CHECK・UNIQUE・GROUP BY の扱い。"""
    q = R["queries"]
    assert all(q["check_null"][e] == "1" for e in ENGINES)
    assert all(q["unique_two_nulls"][e] == "2" for e in ENGINES)
    assert all(q["group_by_null"][e] == "2" for e in ENGINES)

    panels = [
        ("WHERE", "email <> 'sato@…'", "TRUE の行だけ残す", "UNKNOWN の行は捨てる", RED,
         "email が NULL の 2 人は\n結果に入らない"),
        ("CHECK", "CHECK (score >= 0)", "FALSE の行だけ拒む", "UNKNOWN の行は入る", BLUE,
         "NULL は入り、-1 は拒否"),
        ("UNIQUE", "UNIQUE (email)", "等しい値の 2 行目を拒む", "NULL どうしは等しくない", BLUE,
         "NULL の行が 2 行とも入る"),
        ("GROUP BY・DISTINCT", "GROUP BY referred_by", "同じ値を 1 つにまとめる", "NULL は 1 つにまとまる", INK,
         "NULL の 2 人が\n1 つのグループになる"),
    ]
    fig, ax = plt.subplots(figsize=(12, 4.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    for i, (title, sql, rule, unknown, color, result) in enumerate(panels):
        x0 = 0.15 + i * 3.0
        ax.add_patch(FancyBboxPatch((x0, 0.2), 2.7, 4.2, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    fc="#ffffff", ec=GRID, lw=1.2))
        cx = x0 + 1.35
        ax.text(cx, 4.0, title, ha="center", va="center", fontsize=14, color=INK)
        ax.text(cx, 3.45, sql, ha="center", va="center", fontsize=9.5, color=SUB, family=MONO)
        ax.text(cx, 2.85, rule, ha="center", va="center", fontsize=11, color=INK)
        ax.add_patch(FancyArrowPatch((cx, 2.55), (cx, 2.15), arrowstyle="-|>", mutation_scale=14,
                                     color=SUB, lw=1.2))
        face = {RED: RED_PALE, BLUE: BLUE_PALE, INK: GRAY_PALE}[color]
        ax.add_patch(FancyBboxPatch((x0 + 0.1, 1.45), 2.5, 0.6, boxstyle="round,pad=0.02,rounding_size=0.1",
                                    fc=face, ec=color, lw=1.2))
        ax.text(cx, 1.75, unknown, ha="center", va="center", fontsize=10.5, color=color)
        ax.text(cx, 0.8, result, ha="center", va="center", fontsize=10, color=SUB, linespacing=1.4)
    save(fig, "sql-null_gates")


def order():
    """ORDER BY email の ASC と DESC で、NULL が並ぶ位置を DBMS ごとに並べる。"""
    q = R["queries"]
    emails = sorted(m[2] for m in MEMBERS if m[2])
    n_null = sum(1 for m in MEMBERS if m[2] is None)
    # 実測の先頭の行から、NULL が先頭か末尾かを決める
    first_asc = {e: q["order_first"][e] == "NULL" for e in ENGINES}
    first_desc = {e: q["order_desc_first"][e] == "NULL" for e in ENGINES}

    fig, ax = plt.subplots(figsize=(12, 4.9))
    ax.set_xlim(0, 12)
    ax.set_ylim(-0.4, 5.6)
    ax.axis("off")
    for i, e in enumerate(ENGINES):
        x0 = 0.2 + i * 2.95
        ax.text(x0 + 1.35, 5.3, ENGINE_LABEL[e], ha="center", va="center", fontsize=14, color=INK)
        for j, (label, desc, null_first) in enumerate([("ASC", False, first_asc[e]),
                                                       ("DESC", True, first_desc[e])]):
            cx = x0 + 0.65 + j * 1.4
            ax.text(cx, 4.75, label, ha="center", va="center", fontsize=11, color=SUB, family=MONO)
            vals = sorted(emails, reverse=desc)
            vals = (["NULL"] * n_null + vals) if null_first else (vals + ["NULL"] * n_null)
            for k, v in enumerate(vals):
                y = 4.2 - k * 0.78
                kind = "UNKNOWN" if v == "NULL" else "plain"
                chip(ax, cx, y, v.split("@")[0], kind, w=1.25, h=0.56, size=10)
    ax.text(6.0, -0.2, "上が先頭。email は @ より前だけを表示", ha="center", va="center", fontsize=10, color=SUB)
    save(fig, "sql-null_order")


def perf():
    """NOT IN と NOT EXISTS の実行時間（PostgreSQL 18、行数と work_mem を変える）。"""
    fig, ax = plt.subplots(figsize=(9, 4.8))
    series = [
        ("not_in", "64kB", "NOT IN（work_mem 64kB）", RED, "-"),
        ("not_in", "4MB", "NOT IN（work_mem 4MB）", RED, "--"),
        ("not_exists", "64kB", "NOT EXISTS（work_mem 64kB）", BLUE, "-"),
        ("not_exists", "4MB", "NOT EXISTS（work_mem 4MB）", BLUE, "--"),
    ]
    for qid, wm, label, color, ls in series:
        pts = [(r["rows"], r["ms"]) for r in PERF if r["query"] == qid and r["work_mem"] == wm]
        xs, ys = zip(*pts)
        ax.plot(xs, ys, ls, marker="o", color=color, label=label, lw=1.8, ms=5)
        if qid == "not_in" and wm == "64kB":
            for x, y in pts:
                text = f"{y / 1000:,.1f} 秒" if y >= 1000 else f"{y:.0f} ms"
                ax.annotate(text, (x, y), textcoords="offset points", xytext=(4, -16), ha="left",
                            fontsize=10, color=RED)
    ax.set_xscale("log")
    ax.set_yscale("log")
    rows = sorted({r["rows"] for r in PERF})
    ax.set_xticks(rows)
    ax.set_xticklabels([f"{r:,}" for r in rows])
    ax.minorticks_off()
    ticks = [1, 10, 100, 1000, 10000, 100000]
    ax.set_yticks(ticks)
    ax.set_yticklabels(["1 ms", "10 ms", "100 ms", "1 秒", "10 秒", "100 秒"])
    ax.set_xlabel("会員の行数")
    ax.set_ylabel("実行時間（対数）")
    ax.grid(True, color=GRID, lw=0.8)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    save(fig, "sql-null_not_in_time")


if __name__ == "__main__":
    IMAGES.mkdir(exist_ok=True)
    cover()
    gates()
    order()
    perf()
