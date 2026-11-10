"""Generate the figures of the Proof of History note.

- images/proof-of-history_concept.svg: hand-written SVG (standard library only)
- images/proof-of-history_verify.svg: matplotlib, read from lab/output.txt
- images/proof-of-history_window.svg: hand-written SVG (standard library only)
- images/proof-of-history_lockout.svg: hand-written SVG (standard library only)

    uv run --with matplotlib python content/notes/blockchain-systems/proof-of-history/figures.py
"""

import re
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, FILL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def concept_figure():
    """One long sequential chain on top; the same chain cut into lanes below."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        + escape("ハッシュの連鎖は 1 本で順に作るが、区切って並列に検証できる")
        + "</title>",
        f"<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>",
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=26, anchor="start", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>'
                 f"{escape(s)}</text>")

    def bead(x, y, event=False, check=False):
        if event:
            fill, stroke = OCHRE_PALE, OCHRE
        elif check:
            fill, stroke = GREEN_PALE, GREEN
        else:
            fill, stroke = BLUE_PALE, BLUE
        p.append(f'<rect x="{x}" y="{y}" width="26" height="26" rx="3" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2.5"/>')

    def link(x1, x2, y):
        p.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{SUB}" stroke-width="2"/>')

    step, left, n = 38, 60, 22  # 22 beads, 38px apart
    events = {6: "取引 A", 15: "取引 B"}

    # Top: generation on one core, left to right.
    text(left, 52, "生成：1 本の連鎖を順に計算", 28)
    y = 120
    for i in range(n):
        x = left + i * step
        if i:
            link(x - step + 26, x, y + 13)
        bead(x, y, event=i in events)
        if i in events:
            cx = x + 13
            p.append(f'<line x1="{cx}" y1="82" x2="{cx}" y2="{y - 4}" stroke="{OCHRE}" '
                     'stroke-width="3"/>')
            p.append(f'<polygon points="{cx},{y - 2} {cx - 8},{y - 16} {cx + 8},{y - 16}" '
                     f'fill="{OCHRE}"/>')
            text(cx + 12, 98, events[i], 24)
    end_gen = left + (n - 1) * step + 26
    # Time arrow under the top chain.
    p.append(f'<line x1="{left}" y1="186" x2="{end_gen}" y2="186" stroke="{INK}" stroke-width="2.5"/>')
    p.append(f'<polygon points="{end_gen + 14},186 {end_gen},178 {end_gen},194" fill="{INK}"/>')
    text(end_gen + 22, 194, "時間", 24, cls="sub")

    p.append(f'<line x1="30" y1="232" x2="930" y2="232" stroke="{SUB}" stroke-width="1" '
             'stroke-dasharray="4 4"/>')

    # Bottom: the same 22 beads cut into 4 lanes, each starting from a recorded hash.
    text(left, 280, "検証：区切りの値から並列に計算し直す", 28)
    lanes = [(0, 5), (5, 11), (11, 17), (17, 22)]
    for k, (a, b) in enumerate(lanes):
        y = 312 + k * 52
        for j, i in enumerate(range(a, b)):
            x = left + j * step
            if j:
                link(x - step + 26, x, y + 13)
            bead(x, y, event=i in events, check=False)
        # Recorded start hash: a dark outline on the first bead of each lane.
        p.append(f'<rect x="{left - 4}" y="{y - 4}" width="34" height="34" rx="4" '
                 f'fill="none" stroke="{INK}" stroke-width="2"/>')
        xe = left + (b - a - 1) * step + 26
        p.append(f'<polyline points="{xe + 14},{y + 14} {xe + 22},{y + 22} {xe + 36},{y + 4}" '
                 f'fill="none" stroke="{GREEN}" stroke-width="4"/>')
    end_ver = left + 5 * step + 26
    p.append(f'<line x1="{left}" y1="526" x2="{end_ver}" y2="526" stroke="{INK}" stroke-width="2.5"/>')
    p.append(f'<polygon points="{end_ver + 14},526 {end_ver},518 {end_ver},534" fill="{INK}"/>')
    text(end_ver + 60, 534, "同じ連鎖を短い時間で", 24, cls="sub")
    text(560, 380, "枠：記録された区切りの値", 24, cls="sub")
    text(560, 420, "黄土：混ぜた出来事", 24, cls="sub")
    (HERE / "images" / "proof-of-history_concept.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


def verify_figure():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = (HERE / "lab" / "output.txt").read_text()
    gen = re.search(r"generate \(1 goroutine\)\s+([\d.]+)s \(range ([\d.]+)-([\d.]+)\)", out)
    rows = re.findall(r"verify\s+(\d+) goroutines\s+([\d.]+)s \(range ([\d.]+)-([\d.]+)\)\s+([\d.]+)x", out)
    ws = [int(r[0]) for r in rows]
    med = [float(r[1]) for r in rows]
    lo = [float(r[1]) - float(r[2]) for r in rows]
    hi = [float(r[3]) - float(r[1]) for r in rows]
    g = float(gen.group(1))

    plt.rcParams.update({
        "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "proof-of-history",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    x = list(range(len(ws)))
    ax.bar(x, med, color=BLUE_PALE, edgecolor=BLUE, linewidth=1.5, width=0.6,
           yerr=[lo, hi], ecolor=SUB, capsize=4, label="verify (median, min-max)")
    ax.axhline(g, color=OCHRE, lw=2.0, ls="--", label=f"generate on 1 goroutine ({g:.2f} s)")
    for xi, r in zip(x, rows):
        ax.text(xi, float(r[3]) * 1.12, f"{r[4]}x", ha="center", va="bottom", fontsize=9)
    ax.set_yscale("log")
    ax.set_xticks(x, [str(w) for w in ws])
    ax.set_xlabel("Goroutines used for verification")
    ax.set_ylabel("Seconds for 16.8M hashes (log)")
    ax.set_ylim(0.03, 4)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "proof-of-history_verify.svg", metadata={"Date": None})


def _svg_start(title):
    w, h = 960, 540
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>' + escape(title) + "</title>",
        f"<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>",
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]


def _text(p, x, y, s, size=26, anchor="start", cls=""):
    c = f' class="{cls}"' if cls else ""
    p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>'
             f"{escape(s)}</text>")


def window_figure():
    """A transaction is pinned between the blockhash it cites and the place it is mixed in."""
    p = _svg_start("取引が存在した時期は、含めた blockhash と混ぜた位置の間に挟まる")
    step, left, n, y = 38, 62, 22, 250
    j, k = 5, 15  # blockhash cited by the transaction, position where it is mixed in
    xj, xk = left + j * step + 13, left + k * step + 13
    # The window between the two positions.
    p.append(f'<rect x="{xj}" y="{y - 58}" width="{xk - xj}" height="142" fill="{OCHRE_PALE}"/>')
    for i in range(n):
        x = left + i * step
        if i:
            p.append(f'<line x1="{x - step + 26}" y1="{y + 13}" x2="{x}" y2="{y + 13}" '
                     f'stroke="{SUB}" stroke-width="2"/>')
        fill, stroke = (OCHRE_PALE, OCHRE) if i == k else (BLUE_PALE, BLUE)
        p.append(f'<rect x="{x}" y="{y}" width="26" height="26" rx="3" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2.5"/>')
    end = left + (n - 1) * step + 26
    p.append(f'<line x1="{left}" y1="{y + 70}" x2="{end}" y2="{y + 70}" stroke="{INK}" stroke-width="2.5"/>')
    p.append(f'<polygon points="{end + 14},{y + 70} {end},{y + 62} {end},{y + 78}" fill="{INK}"/>')
    _text(p, end + 20, y + 78, "連鎖", 24, cls="sub")
    # Upper side: what each end means.
    _text(p, xj, 92, "取引 A に含めた", 26, "middle")
    _text(p, xj, 126, "blockhash", 26, "middle")
    p.append(f'<line x1="{xj}" y1="140" x2="{xj}" y2="{y - 6}" stroke="{BLUE}" stroke-width="3"/>')
    _text(p, xk, 92, "取引 A を", 26, "middle")
    _text(p, xk, 126, "混ぜた位置", 26, "middle")
    p.append(f'<line x1="{xk}" y1="140" x2="{xk}" y2="{y - 6}" stroke="{OCHRE}" stroke-width="3"/>')
    p.append(f'<polygon points="{xk},{y - 2} {xk - 8},{y - 16} {xk + 8},{y - 16}" fill="{OCHRE}"/>')
    _text(p, (xj + xk) / 2, y + 120, "A が作られた時期はこの間", 26, "middle")
    # Lower side: the two bounds.
    _text(p, xj, 430, "下限：これより後に作られた", 24, "middle", cls="sub")
    _text(p, xk, 470, "上限：これより前に存在した", 24, "middle", cls="sub")
    p.append(f'<line x1="{xj}" y1="{y + 84}" x2="{xj}" y2="404" stroke="{SUB}" stroke-width="1.5" '
             'stroke-dasharray="4 4"/>')
    p.append(f'<line x1="{xk}" y1="{y + 84}" x2="{xk}" y2="444" stroke="{SUB}" stroke-width="1.5" '
             'stroke-dasharray="4 4"/>')
    _text(p, 480, 520, "リーダーが手元に置いたまま混ぜると、上限は後ろへずれる", 24, "middle", cls="sub")
    (HERE / "images" / "proof-of-history_window.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


def lockout_figure():
    """Lockout 2^n and the speed-up 2^n / n needed to overturn it, on a log axis."""
    p = _svg_start("積まれた票の数ごとの lockout と、それを覆すのに要る計算の速さ")
    x0, x1, y0, y1 = 150, 900, 470, 50  # plot area: n = 0..20, log2 value = 0..20
    def X(n):
        return x0 + (x1 - x0) * n / 20
    def Y(v):  # leave room under 1 for the labels of the first points
        return y0 - (y0 - y1) * (v + 2) / 22
    # Axes and log ticks.
    for e, label in [(0, "1"), (5, "32"), (10, "1,024"), (15, "3.3 万"), (20, "105 万")]:
        p.append(f'<line x1="{x0}" y1="{Y(e)}" x2="{x1}" y2="{Y(e)}" stroke="#e3e3e3" stroke-width="1"/>')
        _text(p, x0 - 12, Y(e) + 8, label, 24, "end", cls="sub")
    p.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="{SUB}" stroke-width="2"/>')
    p.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="{SUB}" stroke-width="2"/>')
    for n in (1, 5, 10, 15, 20):
        _text(p, X(n), y0 + 32, str(n), 24, "middle", cls="sub")
    _text(p, (x0 + x1) / 2, y0 + 64, "積まれた票の数 n", 24, "middle")
    import math
    series = [
        (OCHRE, lambda n: float(n), "lockout（スロット）= 2^n"),
        (BLUE, lambda n: n - math.log2(n), "覆すのに要る速さ（倍）= 2^n / n"),
    ]
    for color, f, _ in series:
        pts = " ".join(f"{X(n):.1f},{Y(f(n)):.1f}" for n in range(1, 21))
        p.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="3"/>')
        for n in (1, 3, 10, 20):
            p.append(f'<circle cx="{X(n):.1f}" cy="{Y(f(n)):.1f}" r="6" fill="#ffffff" '
                     f'stroke="{color}" stroke-width="3"/>')
    # Labels for the speed-up at the four points of the text.
    for n, s, dx, dy in [(1, "2 倍", 6, 36), (3, "約 2.7 倍", 12, 36), (10, "約 102 倍", 14, 34),
                         (20, "約 5 万 2 千倍", -12, 40)]:
        v = n - math.log2(n)
        _text(p, X(n) + dx, Y(v) + dy, s, 24, "end" if dx < 0 else "start")
    # Legend.
    for i, (color, _, label) in enumerate(series):
        yy = 92 + i * 40
        p.append(f'<line x1="{x0 + 30}" y1="{yy - 8}" x2="{x0 + 80}" y2="{yy - 8}" stroke="{color}" stroke-width="3"/>')
        _text(p, x0 + 92, yy, label, 24)
    (HERE / "images" / "proof-of-history_lockout.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


if __name__ == "__main__":
    concept_figure()
    verify_figure()
    window_figure()
    lockout_figure()
