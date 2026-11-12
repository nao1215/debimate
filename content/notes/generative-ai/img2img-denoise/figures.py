"""img2img Denoise のノートの図を作る。

冒頭の概念図と、係数・金貨のグラフは Python 標準ライブラリだけで SVG を書く。
指標のグラフは matplotlib。どれも lab/ の JSON（schedule.py・metrics.py・coins_metrics.py の出力）を読むので、
ComfyUI もモデルも無しで描き直せる。

    python3 figures.py
"""

import json
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab"
IMAGES = HERE / "images"
INK, SUB, BLUE, OCHRE, GREEN = "#1f1f1f", "#666666", "#7aa6c2", "#d4a24c", "#8fae86"
BLUE_F, OCHRE_F, NEUTRAL = "#eaf1f5", "#f8eed8", "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def concept_figure():
    """denoise 0.6 の時に KSampler が作る 46 段のノイズの列。前の 18 段を飛ばし、残りの 28 段を描く。"""
    sched = json.loads((LAB / "schedule.json").read_text())
    row = next(r for r in sched["rows"] if r["denoise"] == 0.6)
    n, skipped = row["long_schedule"], row["skipped"]
    # 飛ばす 18 段は schedule.json に無いので、46 段の列全体を schedule.py と同じ式で計算し直す
    # （19 段目が schedule.json の sigma_start と一致することを assert で確かめる）
    import math
    betas = [((0.00085 ** 0.5) + i * ((0.012 ** 0.5 - 0.00085 ** 0.5) / 999)) ** 2 for i in range(1000)]
    ac, cum = [], 1.0
    for b in betas:
        cum *= 1 - b
        ac.append(cum)
    log_s = [math.log(((1 - a) / a) ** 0.5) for a in ac]

    def sigma(t):
        lo, hi = math.floor(t), math.ceil(t)
        w = t - lo
        return math.exp((1 - w) * log_s[lo] + w * log_s[hi])

    sig = [sigma(999 - 999 * i / (n - 1)) for i in range(n)]
    assert abs(sig[skipped] - row["sigma_start"]) < 1e-3, (sig[skipped], row["sigma_start"])
    share = [s / math.sqrt(1 + s * s) for s in sig]  # ノイズが占める割合（0〜1）

    w, h = 960, 540
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
         f'role="img"><title>{escape("denoise 0.6 は 46 段のノイズの列の 19 段目から描き始める")}</title>',
         f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

    def text(x, y, s, size=26, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    x0, x1, base, top = 60, 900, 400, 150
    bw = (x1 - x0) / n
    for i, s in enumerate(share):
        bh = s * (base - top)
        x = x0 + i * bw
        if i < skipped:
            p.append(f'<rect x="{x + 1:.1f}" y="{base - bh:.1f}" width="{bw - 2:.1f}" height="{bh:.1f}" '
                     f'fill="{NEUTRAL}" stroke="#bbbbbb" stroke-width="1" stroke-dasharray="3 3"/>')
        else:
            p.append(f'<rect x="{x + 1:.1f}" y="{base - bh:.1f}" width="{bw - 2:.1f}" height="{bh:.1f}" '
                     f'fill="{BLUE_F}" stroke="{BLUE}" stroke-width="1.5"/>')
    p.append(f'<line x1="{x0}" y1="{base}" x2="{x1}" y2="{base}" stroke="{SUB}" stroke-width="2"/>')

    # txt2img（denoise 1.0）の入口
    text(x0, 70, "txt2img", 26, anchor="start")
    text(x0, 102, "ノイズだけから", 24, anchor="start", cls="sub")
    p.append(f'<line x1="{x0 + 8}" y1="{112}" x2="{x0 + 8}" y2="{top - 8}" stroke="{SUB}" stroke-width="2"/>')
    p.append(f'<path d="M{x0 + 1},{top - 18} L{x0 + 8},{top - 4} L{x0 + 15},{top - 18} Z" fill="{SUB}"/>')

    # img2img（denoise 0.6）の入口: 下絵の札
    sx = x0 + skipped * bw
    sy = base - share[skipped] * (base - top)
    ix, iy, isz = sx - 6, 40, 88
    p.append(f'<rect x="{ix}" y="{iy}" width="{isz}" height="{isz}" fill="#ded8ca" stroke="{OCHRE}" stroke-width="4"/>')
    p.append(f'<rect x="{ix}" y="{iy + isz * 0.62:.1f}" width="{isz}" height="{isz * 0.38:.1f}" fill="#b08a66"/>')
    p.append(f'<circle cx="{ix + isz * 0.62:.1f}" cy="{iy + isz * 0.6:.1f}" r="{isz * 0.16:.1f}" fill="#cf6a5e"/>')
    p.append(f'<rect x="{ix + isz * 0.12:.1f}" y="{iy + isz * 0.55:.1f}" width="{isz * 0.3:.1f}" '
             f'height="{isz * 0.16:.1f}" fill="#6f86c6"/>')
    p.append(f'<line x1="{sx + 8}" y1="{iy + isz + 4}" x2="{sx + 8}" y2="{sy - 10:.1f}" stroke="{OCHRE}" stroke-width="3"/>')
    p.append(f'<path d="M{sx},{sy - 22:.1f} L{sx + 8},{sy - 6:.1f} L{sx + 16},{sy - 22:.1f} Z" fill="{OCHRE}"/>')
    text(ix + isz + 16, iy + 34, "denoise 0.6", 26, anchor="start")
    text(ix + isz + 16, iy + 68, "下絵 + ノイズから", 24, anchor="start", cls="sub")

    # 下の括弧: 飛ばす段と描く段
    def bracket(xa, xb, label, color):
        y = base + 22
        p.append(f'<path d="M{xa:.1f},{y} L{xa:.1f},{y + 12} L{xb:.1f},{y + 12} L{xb:.1f},{y}" '
                 f'fill="none" stroke="{color}" stroke-width="2.5"/>')
        text((xa + xb) / 2, y + 48, label, 26)

    bracket(x0 + 2, sx - 4, f"飛ばす {skipped} 段", "#999999")
    bracket(sx + 2, x1 - 2, f"描く {sched['steps']} 段", BLUE)
    text(x0, base + 120, "ノイズが多い", 24, anchor="start", cls="sub")
    text(x1, base + 120, "ノイズなし", 24, anchor="end", cls="sub")
    p.append("</svg>")
    (IMAGES / "denoise_concept.svg").write_text("\n".join(p) + "\n")


def metrics_figure():
    """下絵 3 種の SSIM・輪郭の一致・彩度を denoise ごとに並べる（lab/metrics.json）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "img2img-denoise",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
        "font.family": ["Noto Sans CJK JP", "sans-serif"],
    })
    rows = json.loads((LAB / "metrics.json").read_text())
    ctrl = next((r for r in rows if r["sketch"] == "control_txt2img"), None)
    style = {"crisp": (BLUE, "o", "-"), "blurred": (OCHRE, "s", "-"), "gray": (SUB, "^", "--")}
    panels = [("ssim", "SSIM（形の近さ）", (0, 1.05)),
              ("edge_f1", "輪郭の一致（F1）", (0, 1.05)),
              ("chroma", "彩度（a*b* の長さ）", None)]
    fig, axes = plt.subplots(1, 3, figsize=(8.5, 3.6))
    for ax, (key, title, ylim) in zip(axes, panels):
        for name, (c, mk, ls) in style.items():
            pts = [(r["denoise"], r[key]) for r in rows if r["sketch"] == name]
            if pts:
                ax.plot(*zip(*pts), color=c, marker=mk, linestyle=ls, linewidth=2, markersize=5, label=name)
        if ctrl is not None and key != "chroma":
            ax.axhline(ctrl[key], color=GREEN, linestyle=":", linewidth=2, label="txt2img")
        ax.set_title(title, fontsize=12)
        ax.set_xlabel("denoise")
        ax.set_xticks([0.3, 0.45, 0.6, 0.75, 0.86, 1.0])
        ax.tick_params(axis="x", labelsize=10)
        if ylim:
            ax.set_ylim(*ylim)
        ax.grid(axis="y", color="#e5e5e5")
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    axes[0].legend(frameon=False, fontsize=10, loc="lower left")
    fig.tight_layout()
    fig.savefig(IMAGES / "denoise_metrics.svg", format="svg", metadata={"Date": None})
    plt.close(fig)


def _svg(title, body, name):
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540" '
            f'role="img"><title>{escape(title)}</title>'
            f"<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>"
            '<rect width="960" height="540" fill="#ffffff"/>')
    (IMAGES / name).write_text(head + "\n" + "\n".join(body) + "\n</svg>\n", encoding="utf-8")


def _t(x, y, s, size=24, anchor="start", cls=""):
    c = f' class="{cls}"' if cls else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>'


def keep_figure():
    """denoise ごとに、開始の段で下絵の潜在表現に掛かる係数 1/sqrt(1+sigma^2)（lab/schedule.json）。"""
    rows = json.loads((LAB / "schedule.json").read_text())["rows"]
    x0, x1, y0, y1 = 150, 900, 450, 60  # denoise 0.25..1.0, keep 0..0.8
    X = lambda d: x0 + (x1 - x0) * (d - 0.25) / 0.75
    Y = lambda k: y0 - (y0 - y1) * k / 0.8
    b = []
    for k in (0, 0.2, 0.4, 0.6, 0.8):
        b.append(f'<line x1="{x0}" y1="{Y(k):.1f}" x2="{x1}" y2="{Y(k):.1f}" stroke="#e5e5e5" stroke-width="1"/>')
        b.append(_t(x0 - 14, Y(k) + 8, f"{k:.1f}", 24, "end", "sub"))
    b.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="{SUB}" stroke-width="2"/>')
    for d in (0.3, 0.45, 0.6, 0.75, 0.86, 1.0):
        b.append(_t(X(d), y0 + 34, f"{d:g}", 24, "middle", "sub"))
    b.append(_t((x0 + x1) / 2, y0 + 72, "denoise", 24, "middle"))
    b.append(_t(x0 - 110, 36, "下絵に掛かる係数", 24))
    pts = " ".join(f"{X(r['denoise']):.1f},{Y(r['keep']):.1f}" for r in rows)
    b.append(f'<polyline points="{pts}" fill="none" stroke="{BLUE}" stroke-width="3"/>')
    for r in rows:
        b.append(f'<circle cx="{X(r["denoise"]):.1f}" cy="{Y(r["keep"]):.1f}" r="7" fill="{BLUE_F}" '
                 f'stroke="{BLUE}" stroke-width="3"/>')
    labels = {0.3: (16, -14), 0.6: (16, -14), 0.86: (0, -22), 1.0: (0, -22)}
    for r in rows:
        if r["denoise"] in labels:
            dx, dy = labels[r["denoise"]]
            b.append(_t(X(r["denoise"]) + dx, Y(r["keep"]) + dy, f"{r['keep']:.3f}", 26,
                        "start" if dx else "middle"))
    _svg("denoise ごとの、開始の段で下絵の潜在表現に掛かる係数", b, "denoise_keep.svg")


def coins_figure():
    """描き直しの条件ごとの、明るい金色の画素の割合と 1 枚目との SSIM（lab/coins_metrics.json）。"""
    rows = {r["name"]: r for r in json.loads((LAB / "coins_metrics.json").read_text())}
    order = [("coins_base", "1 枚目"), ("coins_g_030", "0.3"), ("coins_g_045", "0.45"),
             ("coins_g_050", "0.5"), ("coins_g_060", "0.6"), ("coins_g_075", "0.75"),
             ("coins_c_060", "0.6 金貨あり")]
    x0, x1, top, step = 230, 700, 92, 60
    X = lambda g: x0 + (x1 - x0) * g / 0.035
    b = [_t(x0, 44, "金色の画素の割合", 24, "start", "sub"), _t(900, 44, "SSIM", 24, "end", "sub")]
    for i, (key, label) in enumerate(order):
        r, y = rows[key], top + i * step
        coin = key == "coins_c_060"
        fill, stroke = (OCHRE_F, OCHRE) if coin else ((NEUTRAL, SUB) if key == "coins_base" else (BLUE_F, BLUE))
        b.append(_t(x0 - 16, y + 30, label, 24, "end"))
        w = max(X(r["gold"]) - x0, 2)
        b.append(f'<rect x="{x0}" y="{y + 6}" width="{w:.1f}" height="34" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        b.append(_t(x0 + w + 12, y + 32, f"{r['gold'] * 100:.2f}%", 24))
        b.append(_t(900, y + 32, f"{r['ssim_vs_base']:.3f}", 24, "end", "sub"))
    b.append(f'<line x1="{x0}" y1="{top}" x2="{x0}" y2="{top + len(order) * step}" stroke="{SUB}" stroke-width="2"/>')
    _svg("描き直しの条件ごとの、金色の画素の割合と 1 枚目との SSIM", b, "denoise_coins.svg")


def main():
    IMAGES.mkdir(exist_ok=True)
    concept_figure()
    if (LAB / "metrics.json").exists():
        metrics_figure()
    keep_figure()
    coins_figure()


if __name__ == "__main__":
    main()
