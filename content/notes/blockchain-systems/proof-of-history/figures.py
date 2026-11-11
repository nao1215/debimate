"""Generate the figures of the Proof of History note.

- images/proof-of-history_concept.webp: hand-written SVG
- images/proof-of-history_entry.webp: hand-written SVG
- images/proof-of-history_verify.webp: matplotlib, read from lab/output.txt
- images/proof-of-history_window.webp: hand-written SVG
- images/proof-of-history_redo.webp: hand-written SVG
- images/proof-of-history_tower.webp: hand-written SVG
- images/proof-of-history_lockout.webp: hand-written SVG

The hand-written SVGs are rendered with headless Chrome at 2x and stored as WebP.
Needs google-chrome, matplotlib and Pillow.

    uv run --with matplotlib --with pillow python content/notes/blockchain-systems/proof-of-history/figures.py
"""

import io
import re
import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB, FILL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def save_svg(parts, name, w=960, h=540):
    """Render the SVG with headless Chrome at 2x and store it as WebP in images/."""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text("\n".join(parts + ["</svg>"]) + "\n", encoding="utf-8")
        subprocess.run(
            ["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--force-device-scale-factor=2", f"--window-size={w},{h}",
             f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def concept_figure():
    """One long sequential chain on top; the same chain cut into lanes below."""
    w, h = 960, 570
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
    text(end_ver + 22, 534, "時間（同じ連鎖を短い時間で）", 24, cls="sub")
    text(560, 380, "枠：計算を始める値", 24, cls="sub")
    text(560, 412, "（前の区切りに記録）", 24, cls="sub")
    text(560, 460, "黄土：混ぜた取引", 24, cls="sub")
    save_svg(p, "proof-of-history_concept.webp", w, h)


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
        "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "proof-of-history",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    x = list(range(len(ws)))
    ax.bar(x, med, color=BLUE_PALE, edgecolor=BLUE, linewidth=1.5, width=0.6,
           yerr=[lo, hi], ecolor=SUB, capsize=4, label="検証（verify）の中央値と最小〜最大")
    ax.axhline(g, color=OCHRE, lw=2.0, ls="--", label=f"1 本での生成（generate）{g:.2f} 秒")
    for xi, r in zip(x, rows):
        ax.text(xi, float(r[3]) * 1.12, f"{r[4]} 倍速い", ha="center", va="bottom", fontsize=9)
    ax.set_yscale("log")
    ax.set_xticks(x, [str(w) for w in ws])
    ax.set_xlabel("検証に使った goroutine の数")
    ax.set_ylabel("約 1,678 万回の計算にかかった秒数（対数）")
    ax.set_ylim(0.03, 12)
    ax.set_yticks([0.05, 0.1, 0.5, 1, 2], ["0.05", "0.1", "0.5", "1", "2"])
    ax.minorticks_off()
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper right", frameon=False, fontsize=9, ncol=2)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff")
    Image.open(buf).convert("RGB").save(HERE / "images" / "proof-of-history_verify.webp", "WEBP",
                                         quality=90, method=6)


def _svg_start(title, w=960, h=540):
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


def entry_figure():
    """The chain is cut into entries; a slot of the 400 ms era is 64 ticks of 62,500 hashes."""
    w, h = 960, 500
    p = _svg_start("連鎖は entry に区切って記録し、取引を含まない entry を tick と呼ぶ", w, h)
    _text(p, 40, 52, "連鎖を entry に区切って記録する", 28)
    beads, step, left, y = 5, 36, 60, 150
    gap = 26
    kinds = ["tick", "tick", "tx", "tick"]
    x = left
    for e, kind in enumerate(kinds):
        x_start = x
        for i in range(beads):
            last = i == beads - 1
            if x > left:
                p.append(f'<line x1="{x - step + 26 if i else x - gap - 10}" y1="{y + 13}" '
                         f'x2="{x}" y2="{y + 13}" stroke="{SUB}" stroke-width="2"/>')
            fill, stroke = (OCHRE_PALE, OCHRE) if (last and kind == "tx") else (BLUE_PALE, BLUE)
            p.append(f'<rect x="{x}" y="{y}" width="26" height="26" rx="3" fill="{fill}" '
                     f'stroke="{stroke}" stroke-width="2.5"/>')
            if last:  # the recorded hash of the entry
                p.append(f'<rect x="{x - 4}" y="{y - 4}" width="34" height="34" rx="4" '
                         f'fill="none" stroke="{INK}" stroke-width="2"/>')
            x += step
        x_end = x - step + 26
        # bracket under the entry
        by = y + 48
        p.append(f'<polyline points="{x_start},{by - 8} {x_start},{by} {x_end},{by} {x_end},{by - 8}" '
                 f'fill="none" stroke="{SUB}" stroke-width="2"/>')
        name = "取引を含む entry" if kind == "tx" else "tick"
        _text(p, (x_start + x_end) / 2, by + 30, name, 22, "middle")
        _text(p, (x_start + x_end) / 2, by + 58, "num_hashes = 5", 20, "middle", cls="sub")
        if kind == "tx":
            cx = x_end - 13
            p.append(f'<line x1="{cx}" y1="92" x2="{cx}" y2="{y - 6}" stroke="{OCHRE}" stroke-width="3"/>')
            p.append(f'<polygon points="{cx},{y - 4} {cx - 8},{y - 18} {cx + 8},{y - 18}" fill="{OCHRE}"/>')
            _text(p, cx, 84, "取引を混ぜる", 22, "middle")
        x += gap
    # legend
    _text(p, 40, 304, "枠：entry に記録する区切りの値（hash）", 22, cls="sub")
    _text(p, 40, 336, "num_hashes：前の区切りからの回数（図は説明用に 5 回で描いている）", 22, cls="sub")
    # slot bar: 64 ticks
    p.append(f'<line x1="30" y1="356" x2="930" y2="356" stroke="{SUB}" stroke-width="1" '
             'stroke-dasharray="4 4"/>')
    _text(p, 40, 396, "400ms の時期の 1 スロット = 64 tick", 26)
    bx, bw, bh, byy = 40, 880, 30, 418
    for i in range(64):
        cw = bw / 64
        p.append(f'<rect x="{bx + i * cw:.1f}" y="{byy}" width="{cw - 2:.1f}" height="{bh}" '
                 f'fill="{BLUE_PALE}" stroke="{BLUE}" stroke-width="1"/>')
    _text(p, 40, 484, "1 tick = 62,500 回。64 × 62,500 = 400 万回で、毎秒 1,000 万回なら 400ms", 22, cls="sub")
    save_svg(p, "proof-of-history_entry.webp", w, h)


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
    save_svg(p, "proof-of-history_window.webp")


def redo_figure():
    """After swapping A (entry 100) and B (entry 400), every value from entry 100 to the end changes."""
    w, h = 960, 500
    p = _svg_start("入れ替えた後に計算し直す範囲は entry 100 から末尾まで", w, h)
    left, width, n = 60, 840, 2048

    def x(i):
        return left + width * i / n

    def bar(y, marks, changed):
        p.append(f'<rect x="{left}" y="{y}" width="{width}" height="40" fill="{FILL}" '
                 f'stroke="{SUB}" stroke-width="1.5"/>')
        if changed:
            p.append(f'<rect x="{x(100)}" y="{y}" width="{left + width - x(100)}" height="40" '
                     f'fill="{OCHRE_PALE}" stroke="{OCHRE}" stroke-width="2"/>')
        for i, label in marks:
            p.append(f'<line x1="{x(i)}" y1="{y - 6}" x2="{x(i)}" y2="{y + 46}" stroke="{INK}" stroke-width="3"/>')
            _text(p, x(i), y - 14, label, 22, "middle")

    _text(p, left, 52, "元の連鎖（2,048 entry）", 26)
    bar(110, [(100, "A"), (400, "B"), (700, "C")], False)
    _text(p, left, 194, "entry 0", 20, cls="sub")
    _text(p, left + width, 194, "entry 2047", 20, "end", cls="sub")

    _text(p, left, 262, "A と B を入れ替えて作り直す", 26)
    bar(320, [(100, "B"), (400, "A"), (700, "C")], True)
    _text(p, (x(700) + left + width) / 2, 348, "値が全て変わる：entry 100 から末尾まで", 22, "middle")
    _text(p, left, 436, "entry 0〜99 はそのまま使える", 20, cls="sub")
    # The range that is not enough on its own.
    yb = 384
    p.append(f'<path d="M{x(100)},{yb - 8} V{yb} H{x(400)} V{yb - 8}" fill="none" stroke="{SUB}" '
             'stroke-width="2" stroke-dasharray="6 4"/>')
    _text(p, x(400) + 14, yb + 6, "entry 400 までだけでは足りない", 20, cls="sub")
    _text(p, left, 470, "計算し直す回数：約 1,595 万回（連鎖全体の約 1,678 万回の 95%）", 22)
    save_svg(p, "proof-of-history_redo.webp", w, h)


def tower_figure():
    """Votes stacked in the tower before and after vote 7 (example of the Tower BFT document)."""
    w, h = 960, 450
    p = _svg_start("新しい投票を積むと、下の投票の lockout が 2 倍になる", w, h)
    before = [("投票 6（スロット 10）", 2), ("投票 5（スロット 9）", 4), ("投票 2（スロット 2）", 8),
              ("投票 1（スロット 1）", 16)]
    after = [("投票 7（スロット 11）", 2)] + [(n, l * 2) for n, l in before]

    def stack(x, title, rows, new_top=False):
        _text(p, x + 170, 50, title, 26, "middle")
        bw, bh, gap = 340, 52, 10
        top = 80 + (5 - len(rows)) * (bh + gap)
        for i, (name, lock) in enumerate(rows):
            y = top + i * (bh + gap)
            fill, stroke = (OCHRE_PALE, OCHRE) if (new_top and i == 0) else (BLUE_PALE, BLUE)
            p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="4" fill="{fill}" '
                     f'stroke="{stroke}" stroke-width="2.5"/>')
            _text(p, x + 16, y + 34, name, 22)
            _text(p, x + bw - 16, y + 34, f"lockout {lock}", 22, "end")
        return top

    stack(60, "投票 7 を積む前", before)
    stack(560, "投票 7 を積んだ後", after, new_top=True)
    # arrow between the stacks
    p.append(f'<line x1="420" y1="260" x2="530" y2="260" stroke="{INK}" stroke-width="2.5"/>')
    p.append('<polygon points="544,260 530,252 530,268" fill="#1f1f1f"/>')
    _text(p, 480, 420, "下の投票ほど lockout（別の列へ移れないスロット数）が長い。1 票積むごとに 2 倍", 22,
          "middle", cls="sub")
    save_svg(p, "proof-of-history_tower.webp", w, h)


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
    for n, s, dx, dy in [(1, "2 倍", 10, 30), (3, "約 2.7 倍", 12, 36), (10, "約 102 倍", 14, 34),
                         (20, "約 5 万 2 千倍", -14, 100)]:
        v = n - math.log2(n)
        _text(p, X(n) + dx, Y(v) + dy, s, 24, "end" if dx < 0 else "start")
    # Legend.
    for i, (color, _, label) in enumerate(series):
        yy = 92 + i * 40
        p.append(f'<line x1="{x0 + 30}" y1="{yy - 8}" x2="{x0 + 80}" y2="{yy - 8}" stroke="{color}" stroke-width="3"/>')
        _text(p, x0 + 92, yy, label, 24)
    save_svg(p, "proof-of-history_lockout.webp")


if __name__ == "__main__":
    concept_figure()
    entry_figure()
    verify_figure()
    window_figure()
    redo_figure()
    tower_figure()
    lockout_figure()
