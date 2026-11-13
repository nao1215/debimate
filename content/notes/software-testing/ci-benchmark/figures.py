"""Generate the figures of the CI benchmark note.

Run: python3 figures.py  -> images/*.webp

The numbers come from lab/output/*.csv (lab/extract.py turns the workflow
artifacts of https://github.com/nao1215/ci-bench-noise into them). Charts are
drawn with matplotlib; the diagram of the experiment is built as SVG text and
rendered by headless Chrome. Only WebP files are kept in images/.

- cpu_figure(): the cover. The base median of every job, by CPU model.
- order_figure(): the experiment, and the order of the runs in one job
  (interleaved by himorime compare, then sequential).
- within_figure(): the 20 runs of three A/A jobs in the order they ran.
- stored_figure(): comparing with a stored result of another job, by threshold,
  against comparing in the same job.
- same_job_figure(): himorime compare in the same job, by slowdown.
- instr_figure(): time and instruction count of the same build, by CPU model.
- verdict_figure(): how himorime decides, with the bootstrap of four real jobs.
- pair_figure(): one comparison on the author's desktop, round by round.
"""

import csv
import itertools
import io
import statistics as st
import subprocess
import tempfile
from collections import defaultdict
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
IMG = HERE / "images"
INK, SUB, LINE, PALE = "#1f1f1f", "#666666", "#9a9a9a", "#f2f2f2"
ACCENT, RED, AMBER = "#4f86a8", "#d64545", "#b7791f"
FONT = "'Noto Sans CJK JP','Hiragino Sans',sans-serif"
MONO = "'DejaVu Sans Mono',monospace"

plt.rcParams.update({
    "font.family": "Noto Sans CJK JP", "font.size": 11, "axes.edgecolor": LINE,
    "axes.labelcolor": INK, "xtick.color": SUB, "ytick.color": SUB, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "#ffffff",
    "axes.facecolor": "#ffffff",
})

# Short names for the CPU models, as printed in /proc/cpuinfo.
SHORT = {
    "AMD EPYC 9V74 80-Core Processor": "AMD EPYC 9V74",
    "AMD EPYC 7763 64-Core Processor": "AMD EPYC 7763",
    "AMD EPYC 9V45 96-Core Processor": "AMD EPYC 9V45",
    "INTEL(R) XEON(R) PLATINUM 8573C": "Intel Xeon Platinum 8573C",
    "Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz": "Intel Xeon Platinum 8370C",
    "Intel(R) Xeon(R) 6975P-C": "Intel Xeon 6975P-C",
    "Intel(R) Xeon(R) 6973P-C": "Intel Xeon 6973P-C",
}


def read(name):
    with (OUT / name).open() as f:
        return list(csv.DictReader(f))


def load():
    s = defaultdict(list)
    for r in read("samples.csv"):
        if r["mode"] != "hyperfine":
            s[(r["job"], r["mode"], r["side"])].append(int(r["ns"]) / 1e6)
    jobs = read("jobs.csv")
    for j in jobs:
        j["slowdown"] = int(j["slowdown"])
        j["base"] = s[(j["job"], "interleaved", "base")]
        j["head"] = s[(j["job"], "interleaved", "head")]
        j["med"] = st.median(j["base"])
    return jobs


def save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    IMG.mkdir(exist_ok=True)
    Image.open(buf).convert("RGB").save(IMG / name, "WEBP", quality=90, method=6)


def render_svg(svg_text, w, h, name):
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        IMG.mkdir(exist_ok=True)
        Image.open(png).convert("RGB").save(IMG / name, "WEBP", quality=90, method=6)


def cpu_figure(jobs):
    by = defaultdict(list)
    for j in jobs:
        by[j["cpu"]].append(j["med"])
    order = sorted(by, key=lambda c: st.median(by[c]))
    fig, ax = plt.subplots(figsize=(8.6, 4.1))
    for i, cpu in enumerate(order):
        xs = sorted(by[cpu])
        # Spread equal values vertically so every job stays visible.
        ys = [i + ((k % 7) - 3) * 0.07 for k in range(len(xs))]
        slow = [x > 135 and "9V74" in cpu for x in xs]
        ax.scatter([x for x, f in zip(xs, slow) if not f], [y for y, f in zip(ys, slow) if not f],
                   s=26, color=ACCENT, alpha=0.75, edgecolor="none")
        ax.scatter([x for x, f in zip(xs, slow) if f], [y for y, f in zip(ys, slow) if f],
                   s=34, color=RED, edgecolor="none")
    ax.set_yticks(range(len(order)), [f"{SHORT[c]}（{len(by[c])} 回）" for c in order])
    ax.set_xlabel("同じプログラムの実行時間（ジョブごとの中央値、ms）")
    ax.set_xlim(95, 150)
    lo, hi = min(j["med"] for j in jobs), max(j["med"] for j in jobs)
    ax.set_title(f"同じコードでも、ジョブが引いた CPU で {lo:.0f}〜{hi:.0f} ms（{hi / lo:.2f} 倍）",
                 loc="left", fontsize=13, color=INK, pad=12)
    i74 = order.index("AMD EPYC 9V74 80-Core Processor")
    ax.annotate("同じ型番でも約 142 ms の機械（4 回）", xy=(141.4, i74 - 0.1), xytext=(117, i74 - 0.75),
                fontsize=10, color=RED, arrowprops=dict(arrowstyle="->", color=RED, lw=1))
    ax.grid(axis="x", color="#e6e6e6", lw=0.8)
    ax.set_axisbelow(True)
    save(fig, "cpu.webp")


def order_figure():
    w, h = 880, 360
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
         f'<style>text{{font-family:{FONT};fill:{INK}}} .m{{font-family:{MONO}}}</style>',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

    def text(x, y, s, size=14, color=INK, anchor="start", mono=False):
        cls = ' class="m"' if mono else ""
        p.append(f'<text{cls} x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                 f'style="fill:{color}">{escape(s)}</text>')

    def box(x, y, bw, bh, fill, stroke=LINE, rx=6):
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>')

    text(24, 32, "1 つのジョブの中で測る順番（新しいランナーを 1 台ずつ使う）", 16)
    box(24, 50, 250, 58, PALE)
    text(40, 74, "base: slowdown.txt = 0", 13, mono=True)
    text(40, 96, "head: slowdown.txt = N", 13, mono=True)
    text(290, 84, "同じランナーで 2 つをビルドし、20 回ずつ実行する", 14, SUB)

    def row(y, label, seq, note):
        text(24, y + 19, label, 14)
        for k, side in enumerate(seq):
            x = 200 + k * 15.5
            fill = "#dbe8f1" if side == "B" else "#fbe3e3"
            stroke = ACCENT if side == "B" else RED
            box(x, y, 13, 26, fill, stroke, rx=2)
        text(200, y + 48, note, 13, SUB)

    # The order himorime compare used in one job is shuffled within each round;
    # this is the pattern of the rounds, not a recorded order.
    inter = []
    for k in range(20):
        inter += ["B", "H"] if k % 3 != 1 else ["H", "B"]
    row(140, "交互（himorime）", inter, "1 ラウンドで base と head を 1 回ずつ測る。ラウンドの中の順番は乱数で決める")
    row(224, "まとめて", ["B"] * 20 + ["H"] * 20, "base を 20 回測り終えてから head を 20 回")
    box(24, 304, 13, 18, "#dbe8f1", ACCENT, rx=2)
    text(44, 318, "base の 1 回", 13, SUB)
    box(150, 304, 13, 18, "#fbe3e3", RED, rx=2)
    text(170, 318, "head の 1 回", 13, SUB)
    text(290, 318, "どちらの後にも hyperfine で同じ 2 つを測り直す", 13, SUB)
    p.append("</svg>")
    render_svg("\n".join(p), w, h, "order.webp")


def within_figure(jobs):
    pick = [("aa2-s0-r10", "AMD EPYC 9V74"), ("aa2-s0-r21", "AMD EPYC 9V74"), ("aa2-s0-r25", "Intel Xeon 6973P-C")]
    by = {j["job"]: j for j in jobs}
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    colors = [RED, ACCENT, AMBER]
    for (job, name), c in zip(pick, colors):
        xs = by[job]["base"]
        ax.plot(range(1, len(xs) + 1), xs, "-o", color=c, ms=4, lw=1.2,
                label=f"{name}（中央値 {st.median(xs):.1f} ms）")
    ax.set_xlabel("ジョブの中の実行の順番（base の 20 回）")
    ax.set_ylabel("実行時間（ms）")
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.set_ylim(95, 155)
    ax.legend(frameon=False, fontsize=10, loc="center left", bbox_to_anchor=(0.02, 0.56))
    ax.set_title("ジョブの中ではほぼ一定、ジョブが変わると段がずれる", loc="left", fontsize=13, pad=10)
    ax.grid(axis="y", color="#e6e6e6", lw=0.8)
    ax.set_axisbelow(True)
    save(fig, "within.webp")


def stored_figure(jobs):
    aa = [j for j in jobs if j["slowdown"] == 0]
    s20 = [j for j in jobs if j["slowdown"] == 20]
    ts = list(range(0, 105, 5))
    fa, cg = [], []
    for t in ts:
        pairs = list(itertools.permutations(aa, 2))
        fa.append(100 * sum(b["med"] > a["med"] * (1 + t / 100) for a, b in pairs) / len(pairs))
        cg.append(100 * sum(st.median(h["head"]) > a["med"] * (1 + t / 100) for h in s20 for a in aa) / (len(s20) * len(aa)))
    fig, ax = plt.subplots(figsize=(8.6, 4.0))
    ax.plot(ts, cg, "-o", color=ACCENT, ms=4, label="20% 遅くした変更を警告した割合")
    ax.plot(ts, fa, "-o", color=RED, ms=4, label="何も変えていない変更を警告した割合（誤検知）")
    k = ts.index(10)
    ax.annotate(f"閾値 10%: 誤検知 {fa[k]:.0f}%・20% の検出 {cg[k]:.0f}%", xy=(10, cg[k]), xytext=(21, 50),
                fontsize=10, color=INK, arrowprops=dict(arrowstyle="->", color=SUB, lw=0.9))
    ax.scatter([10], [100], marker="*", s=150, color=ACCENT, zorder=5)
    ax.scatter([10], [0], marker="*", s=150, color=RED, zorder=5)
    ax.text(12.5, 97, "★ 同じジョブの中で交互に比べた himorime（閾値 10%）: 20% の検出 100%・誤検知 0%",
            fontsize=10, color=INK, va="center")
    ax.axvline(100, color=LINE, lw=0.9, ls="--")
    ax.text(98.5, 9, "github-action-benchmark の既定\n（200%、2 倍で警告）", fontsize=9.5, color=SUB, ha="right")
    ax.set_xlabel("閾値（前回の結果より何 % 遅ければ警告するか）")
    ax.set_ylabel("割合（%）")
    ax.set_ylim(-3, 103)
    ax.set_xlim(-3, 104)
    ax.legend(frameon=False, fontsize=10, loc="upper right", bbox_to_anchor=(1.0, 0.84))
    ax.set_title("前回のジョブの結果と比べると、誤検知と見逃しが同時に出る", loc="left", fontsize=13, pad=10)
    ax.grid(color="#eeeeee", lw=0.8)
    ax.set_axisbelow(True)
    save(fig, "stored.webp")


def same_job_figure(jobs):
    slows = sorted({j["slowdown"] for j in jobs})
    col = {"pass": ACCENT, "inconclusive": AMBER, "regression": RED}
    name = {"pass": "pass（劣化ではない）", "inconclusive": "inconclusive（判定できない）", "regression": "regression（劣化）"}
    fig, ax = plt.subplots(figsize=(8.6, 4.0))
    seen = set()
    for i, sd in enumerate(slows):
        js = sorted((j for j in jobs if j["slowdown"] == sd), key=lambda j: float(j["latency_change"]))
        for k, j in enumerate(js):
            v = j["latency_verdict"]
            ax.scatter(i + ((k % 10) - 4.5) * 0.045, float(j["latency_change"]), s=22, color=col[v],
                       edgecolor="none", label=name[v] if v not in seen else None)
            seen.add(v)
    ax.axhline(10, color=INK, lw=0.9, ls="--")
    ax.text(-0.35, 10.6, "閾値 10%", fontsize=10, color=INK)
    ax.set_xticks(range(len(slows)), [f"{s}%" + ("\n（A/A）" if s == 0 else "") for s in slows])
    ax.set_xlabel("head に足した仕事の量")
    ax.set_ylabel("himorime が測った変化（%）")
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    ax.set_title("同じジョブの中で比べると、A/A は 30 回とも ±0.6% 以内", loc="left", fontsize=13, pad=10)
    ax.grid(axis="y", color="#eeeeee", lw=0.8)
    ax.set_axisbelow(True)
    save(fig, "same_job.webp")


def instr_figure():
    rows = read("instructions.csv")
    by = defaultdict(list)
    for r in rows:
        by[r["cpu"]].append(r)
    order = sorted(by, key=lambda c: st.median(float(r["base_time_ms"]) for r in by[c]))
    t0 = min(st.median(float(r["base_time_ms"]) for r in by[c]) for c in order)
    i0 = min(st.median(int(r[f"base_irefs_{n}"]) for r in by[c] for n in (1, 2, 3)) for c in order)
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.4), sharey=True)
    for ax, title, vals in (
        (axes[0], "実行時間", [st.median(float(r["base_time_ms"]) for r in by[c]) / t0 for c in order]),
        (axes[1], "命令数（cachegrind）", [st.median(int(r[f"base_irefs_{n}"]) for r in by[c] for n in (1, 2, 3)) / i0 for c in order]),
    ):
        ax.barh(range(len(order)), [100 * (v - 1) for v in vals], color=ACCENT if "命令" in title else RED, height=0.55)
        for k, v in enumerate(vals):
            ax.text(100 * (v - 1) + 0.6, k, f"+{100 * (v - 1):.{1 if '命令' not in title else 3}f}%", va="center", fontsize=10)
        ax.set_title(title, fontsize=12, loc="left")
        ax.set_xlim(0, 30)
        ax.set_xlabel("このグラフで最も小さい CPU との差（%）")
    axes[0].set_yticks(range(len(order)), [f"{SHORT[c]}（{len(by[c])} 回）" for c in order])
    fig.suptitle("同じビルドでも、時間は CPU で最大 20% 違い、命令数（中央値）は 0.001% しか違わない", x=0.02, ha="left", fontsize=13)
    fig.tight_layout()
    save(fig, "instructions.webp")


def boot(base, head, seed=1, n=2000):
    import random
    rnd = random.Random(seed)
    return [(st.median(rnd.choices(head, k=len(head))) / st.median(rnd.choices(base, k=len(base))) - 1) * 100
            for _ in range(n)]


def verdict_figure(jobs):
    by = {j["job"]: j for j in jobs}
    pick = [("aa2-s0-r1", "A/A（同じコード）"), ("slow2-s10-r4", "10% 遅くした変更"),
            ("slow2-s10-r2", "10% 遅くした変更"), ("slow2-s20-r1", "20% 遅くした変更")]
    col = {"pass": ACCENT, "inconclusive": AMBER, "regression": RED}
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    for i, (job, label) in enumerate(pick):
        j = by[job]
        ch = boot(j["base"], j["head"])
        y = len(pick) - 1 - i
        ys = [y + ((k % 41) - 20) * 0.006 for k in range(len(ch))]
        ax.scatter(ch, ys, s=3, color=col[j["latency_verdict"]], alpha=0.12, edgecolor="none")
        over = sum(c > 10 for c in ch) / len(ch) * 100
        ax.text(21.5, y, f"{j['latency_verdict']}", va="center", fontsize=11, color=col[j["latency_verdict"]])
        ax.text(-1.2, y + 0.3, f"{label}: 測った変化 {float(j['latency_change']):+.1f}%、"
                f"選び直した変化のうち ±10% 以内 {100 - over:.0f}%・10% 超 {over:.0f}%", fontsize=9.5, color=INK)
    ax.axvline(10, color=INK, lw=0.9, ls="--")
    ax.text(10.2, len(pick) - 0.45, "閾値 10%", fontsize=10)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_xlim(-1.5, 25)
    ax.set_ylim(-0.5, len(pick) - 0.3)
    ax.set_xlabel("base から head への変化（%）。点 1 つが選び直し 1 回")
    ax.set_title("選び直した変化の 95% 以上が閾値のどちら側にあるかで判定する", loc="left", fontsize=13, pad=10)
    save(fig, "verdict.webp")


def pair_figure():
    rows = read("desktop_samples.csv")
    b = [int(r["ns"]) / 1e6 for r in rows if r["job"] == "s20_r7" and r["side"] == "base"]
    h = [int(r["ns"]) / 1e6 for r in rows if r["job"] == "s20_r7" and r["side"] == "head"]
    x = range(1, len(b) + 1)
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6), gridspec_kw={"width_ratios": [1.7, 1]})
    ax = axes[0]
    ax.plot(x, b, "-o", color=ACCENT, ms=3.5, lw=1.1, label=f"base（中央値 {st.median(b):.0f} ms）")
    ax.plot(x, h, "-o", color=RED, ms=3.5, lw=1.1, label=f"head（中央値 {st.median(h):.0f} ms）")
    slower = sum(y > x0 for x0, y in zip(b, h))
    ax.set_xlabel(f"ラウンド（base と head を 1 回ずつ測る組）。{len(b)} ラウンドのうち {slower} ラウンドで head が遅い")
    ax.set_ylabel("実行時間（ms）")
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.legend(frameon=False, fontsize=9.5, loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=2)
    ax.grid(axis="y", color="#eeeeee", lw=0.8)
    r = [(y / x0 - 1) * 100 for x0, y in zip(b, h)]
    ax2 = axes[1]
    ax2.scatter([0] * len(r), r, s=18, color=INK, alpha=0.6, edgecolor="none")
    ax2.axhline(st.median(r), color=RED, lw=1.2)
    ax2.axhline((st.median(h) / st.median(b) - 1) * 100, color=ACCENT, lw=1.2, ls="--")
    ax2.text(0.06, st.median(r) + 2, f"ラウンドごとの比の中央値 {st.median(r):+.1f}%", fontsize=9.5, color=RED)
    ax2.text(0.06, (st.median(h) / st.median(b) - 1) * 100 - 6,
             f"中央値どうしの比 {(st.median(h) / st.median(b) - 1) * 100:+.1f}%", fontsize=9.5, color=ACCENT)
    ax2.set_xlim(-0.1, 0.9)
    ax2.set_xticks([])
    ax2.set_ylabel("head / base − 1（%）")
    ax2.set_title("ラウンドごとの比", loc="left", fontsize=11.5)
    ax2.grid(axis="y", color="#eeeeee", lw=0.8)
    fig.suptitle("20% 遅くした変更を、揺れの大きい手元の機械で測った 1 回", x=0.02, y=1.04, ha="left", fontsize=13)
    fig.tight_layout()
    save(fig, "pair.webp")


def main():
    jobs = load()
    cpu_figure(jobs)
    order_figure()
    within_figure(jobs)
    stored_figure(jobs)
    same_job_figure(jobs)
    instr_figure()
    verdict_figure(jobs)
    pair_figure()


main()
