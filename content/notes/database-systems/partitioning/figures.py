"""Partitioning - 表をキーで分ける の図を生成する。

local_global() と concept_figure() は標準ライブラリだけで SVG を書く。
pruning_figure() と hot_figure() は lab/output.txt の値から標準ライブラリで SVG を書く。
timing_figure() は lab/output.txt の実測値（psql の \\timing）を matplotlib で描く。

再生成:
    python3 content/notes/database-systems/partitioning/figures.py
"""

import pathlib
import re
from html import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = pathlib.Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)

INK = "#1f1f1f"
GRAY = "#666666"
FILL = "#f2f2f2"
BLUE = "#7aa6c2"
RED = "#e15759"
FONT = "font-family=\"-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif\""


def rect(x, y, w, h, fill=FILL, stroke=INK, dash=None, sw=1.2):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')


def text(x, y, s, size=14, color=INK, anchor="middle", weight="normal"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'font-weight="{weight}" {FONT}>{s}</text>')


def line(x1, y1, x2, y2, color=GRAY, dash=None, sw=1.2):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}"{d}/>')


def panel(ox, title, subtitle, global_index):
    parts = [text(ox + 165, 28, title, size=17, weight="normal"),
             text(ox + 165, 50, subtitle, size=14, color=GRAY)]
    months = ["2026-10", "2026-11", "2026-12"]
    px = [ox + 10 + i * 110 for i in range(3)]
    # パーティション（表）
    for i, (x, m) in enumerate(zip(px, months)):
        dropped = i == 0
        parts.append(rect(x, 170, 90, 70, fill="#ffffff" if dropped else FILL,
                          stroke=RED if dropped else INK, dash="5 4" if dropped else None))
        parts.append(text(x + 45, 198, m, color=RED if dropped else INK))
        parts.append(text(x + 45, 220, "partition", size=13, color=GRAY))
    parts.append(text(px[0] + 45, 262, "DROP PARTITION" if global_index else "DROP",
                      size=13, color=RED))
    if not global_index:
        # パーティションごとの索引
        for i, x in enumerate(px):
            dropped = i == 0
            parts.append(rect(x + 10, 80, 70, 40, fill="#ffffff" if dropped else "#e3eef5",
                              stroke=RED if dropped else BLUE, dash="5 4" if dropped else None))
            parts.append(text(x + 45, 106, "index", size=14, color=RED if dropped else INK))
            parts.append(line(x + 45, 120, x + 45, 170, color=RED if dropped else GRAY,
                              dash="4 3" if dropped else None))
        parts.append(text(ox + 165, 300, "The index is dropped with its partition.", size=13, color=GRAY))
    else:
        # 全パーティションにまたがる 1 本の索引
        parts.append(rect(px[0], 80, 310, 40, fill="#e3eef5", stroke=BLUE))
        parts.append(text(ox + 165, 106, "one global index", size=14))
        for i, x in enumerate(px):
            dropped = i == 0
            for dx in (25, 65):
                parts.append(line(x + dx, 120, x + dx, 170, color=RED if dropped else GRAY,
                                  dash="4 3" if dropped else None))
        parts.append(text(ox + 165, 300, "Entries pointing to the dropped partition", size=13, color=GRAY))
        parts.append(text(ox + 165, 320, "need index maintenance", size=13, color=GRAY))
        parts.append(text(ox + 165, 340, "(rebuild or UPDATE INDEXES).", size=13, color=GRAY))
    return parts


def local_global():
    w, h = 720, 360
    body = [f'<rect width="{w}" height="{h}" fill="#ffffff"/>']
    body += panel(10, "Local index", "e.g. PostgreSQL", global_index=False)
    body.append(line(360, 20, 360, 340, color="#dddddd"))
    body += panel(380, "Global index", "e.g. Oracle Database", global_index=True)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
           + "".join(body) + "</svg>\n")
    path = OUT / "local-global-index.svg"
    path.write_text(svg, encoding="utf-8")
    print(f"wrote {path}")


# ---- 冒頭の概念図（960x540、標準ライブラリだけ） ----

ACCENT, PALE = BLUE, "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
JP_FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def jtext(x, y, s, size=24, color=INK, weight="normal"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="middle" style="font-family:{JP_FONT};fill:{color}">{escape(s)}</text>')


def arrow(x, y1, y2, color, name):
    return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{color}" stroke-width="5" '
            f'stroke-linecap="round" marker-end="url(#{name})"/>')


def concept_figure():
    w, h = 960, 540
    body = [
        '<defs>' + "".join(
            f'<marker id="{n}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" '
            f'markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
            for n, c in (("arrow-ochre", OCHRE), ("arrow-ink", INK))) + '</defs>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        # 親表は枠だけで、レコードを持たない
        f'<rect x="36" y="150" width="888" height="270" rx="14" fill="none" '
        f'stroke="{GRAY}" stroke-width="3" stroke-dasharray="10 7"/>',
        jtext(480, 400, "events（親表）は枠だけで、レコードを持たない", 24, GRAY),
    ]
    bw, gap, x0 = 128, 16, 56
    for i in range(6):
        x = x0 + i * (bw + gap)
        cx = x + bw / 2
        if i == 0:  # 古い月はパーティションごと DROP
            body.append(rect(x, 178, bw, 170, fill=OCHRE_PALE, stroke=OCHRE, dash="9 6", sw=3))
            body.append(jtext(cx, 272, "1 月", 28, INK))
        elif i == 2:  # 条件に合う月だけを読む
            body.append(rect(x, 178, bw, 170, fill=ACCENT, stroke=ACCENT, sw=3))
            body.append(jtext(cx, 272, "3 月", 28, INK, "normal"))
        else:  # 刈り込みで読まない
            body.append(rect(x, 178, bw, 170, fill=FILL, stroke=GRAY, sw=2.5))
            body.append(jtext(cx, 272, f"{i + 1} 月", 28, GRAY))
    c1, c3 = x0 + bw / 2, x0 + 2 * (bw + gap) + bw / 2
    body += [
        jtext(c1 + 20, 66, "古い月は DROP", 26, INK),
        arrow(c1, 82, 170, OCHRE, "arrow-ochre"),
        jtext(c3 + 40, 66, "3 月の条件で読む", 26, INK),
        arrow(c3, 82, 170, INK, "arrow-ink"),
        jtext(480, 472, "ほかの月は刈り込みで読まない", 26, GRAY),
    ]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
           f'height="{h}" role="img"><title>月ごとのパーティションと刈り込み・DROP</title>'
           + "".join(body) + "</svg>\n")
    (OUT / "partitioning_concept.svg").write_text(svg, encoding="utf-8")


# ---- lab/output.txt の時間の比較（matplotlib） ----

def lab_times():
    text = (pathlib.Path(__file__).parent / "lab" / "output.txt").read_text(encoding="utf-8")

    def after(header):
        return float(re.search(re.escape(header) + r".*?Time: ([\d.]+) ms", text, re.S).group(1))

    return [
        ("DELETE one month", after("== (1) 9 月分を DELETE で消す"), RED),
        ("DROP the partition", after("== (2) 10 月分をパーティションごと DROP で消す"), BLUE),
        ("ATTACH without CHECK", after("== (1) CHECK 制約なしで ATTACH"), RED),
        ("ATTACH with CHECK", after("== (2) CHECK 制約ありで ATTACH"), BLUE),
    ]


def timing_figure():
    rows = lab_times()
    with plt.rc_context({
        "font.size": 10, "axes.edgecolor": GRAY, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "partitioning",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    }):
        fig, ax = plt.subplots(figsize=(7.2, 3.6))
        ys = [3.4, 2.4, 1.0, 0.0]
        for y, (label, ms, color) in zip(ys, rows):
            ax.barh(y, ms, color=color, height=0.7)
            ax.text(ms * 1.15, y, f"{ms:,.0f} ms", va="center", fontsize=10)
        ax.set_yticks(ys, [r[0] for r in rows], fontsize=10)
        ax.set_xscale("log")
        ax.set_xlim(1, 10000)
        ax.set_ylim(-0.6, 4.0)
        ax.set_xlabel("Time (ms, log scale)")
        ax.text(9000, 2.9, "5 million rows / month", ha="right", va="center",
                color=GRAY, fontsize=9)
        ax.text(9000, 0.5, "5 million rows / table", ha="right", va="center",
                color=GRAY, fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(OUT / "partitioning_times.svg", metadata={"Date": None})
        plt.close(fig)


# ---- lab/output.txt の刈り込みと Hot Partition（標準ライブラリの SVG） ----

def lab_section(header, stop="\n== "):
    text = (pathlib.Path(__file__).parent / "lab" / "output.txt").read_text(encoding="utf-8")
    start = text.index(header)
    end = text.find(stop, start + len(header))
    return text[start:end if end != -1 else None]


def jtext_at(x, y, s, size=24, color=INK, anchor="middle"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
            f'style="font-family:{JP_FONT};fill:{color}">{escape(s)}</text>')


def save_svg(name, title, body, w=960, h=540):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
           f'height="{h}" role="img"><title>{escape(title)}</title>'
           f'<rect width="{w}" height="{h}" fill="#ffffff"/>' + "".join(body) + "</svg>\n")
    (OUT / name).write_text(svg, encoding="utf-8")


def pruning_figure():
    """Which monthly partitions each of the three queries in 02_pruning.sql scanned."""
    rows = [("== (1) 範囲で書いた条件", "(1) 範囲で書いた条件", "プランの段階で外す"),
            ("== (2) 関数で包んだ条件", "(2) 関数で包んだ条件", "全て読み、捨てる"),
            ("== (3) パラメータを後から渡す generic plan", "(3) generic plan", "実行の開始時に外す")]
    body = []
    x0, cw, gap = 346, 88, 9
    for m in range(6):
        body.append(jtext_at(x0 + m * (cw + gap) + cw / 2, 62, f"{m + 1} 月", 24, GRAY))
    for r, (header, label, sub) in enumerate(rows):
        sec = lab_section(header)
        read = {int(mm) for mm in re.findall(r"Seq Scan on events_2026_(\d\d)", sec)}
        y = 90 + r * 128
        body.append(jtext_at(24, y + 40, label, 26, INK, "start"))
        body.append(jtext_at(24, y + 76, sub, 24, GRAY, "start"))
        for m in range(1, 7):
            x = x0 + (m - 1) * (cw + gap)
            if m not in read:
                body.append(rect(x, y, cw, 96, fill="#ffffff", stroke=GRAY, dash="6 5", sw=2))
            elif m == 3:
                body.append(rect(x, y, cw, 96, fill=PALE, stroke=ACCENT, sw=3))
            else:
                body.append(rect(x, y, cw, 96, fill=OCHRE_PALE, stroke=OCHRE, sw=3))
    # legend
    ly = 488
    for x, (fill, stroke, dash, label) in zip(
            (40, 330, 640),
            ((PALE, ACCENT, None, "読んで数えた"), (OCHRE_PALE, OCHRE, None, "読んで全て捨てた"),
             ("#ffffff", GRAY, "6 5", "読まなかった"))):
        body.append(rect(x, ly - 24, 40, 32, fill=fill, stroke=stroke, dash=dash, sw=2.5))
        body.append(jtext_at(x + 54, ly, label, 24, INK, "start"))
    save_svg("partitioning_pruning.svg", "同じ 3 月の条件で、書き方ごとに読んだパーティション", body)


def hot_figure():
    """Rows each partition received for one day of inserts (03_hot_partition.sql)."""
    sec = lab_section("== (1) パーティションごとに入った件数")
    counts = {name: int(n) for name, n in re.findall(r"(logs_\w+)\s+\|\s+(\d+)", sec)}
    groups = [("月ごとの Range", [("10 月", counts["logs_range_10"]), ("11 月", counts["logs_range_11"]),
                                  ("12 月", counts["logs_range_12"])]),
              ("id の Hash", [("余り 0", counts["logs_hash_0"]), ("余り 1", counts["logs_hash_1"]),
                              ("余り 2", counts["logs_hash_2"])])]
    top = max(counts.values())
    base, height = 420, 300
    body = [line(40, base, 920, base, color=GRAY, sw=2)]
    for g, (title, bars) in enumerate(groups):
        gx = 60 + g * 460
        body.append(jtext_at(gx + 200, 60, title, 28))
        for i, (label, n) in enumerate(bars):
            x = gx + 20 + i * 130
            h = height * n / top
            hot = g == 0 and n == top
            if n:
                body.append(rect(x, base - h, 100, h, fill=OCHRE_PALE if hot else PALE,
                                 stroke=OCHRE if hot else ACCENT, sw=2.5))
            body.append(jtext_at(x + 50, base - h - 14, f"{n:,}", 24, INK))
            body.append(jtext_at(x + 50, base + 36, label, 24, GRAY))
    body.append(jtext_at(480, 512, "1 秒 1 件で 1 日分（86,400 件）を入れた時の件数", 24, GRAY))
    save_svg("partitioning_hot.svg", "1 日分の INSERT が入ったパーティション", body)


if __name__ == "__main__":
    local_global()
    concept_figure()
    timing_figure()
    pruning_figure()
    hot_figure()
