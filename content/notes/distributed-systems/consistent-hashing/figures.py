"""Generate the illustrative rings with Python 3 standard library.
Run: python3 figures.py. Positions are explanatory, not experiment results.

moved_figure() runs experiment.py and draws its output (moved keys and keys
per node after adding D) with matplotlib into images/.
"""
import re
import subprocess
import sys
from math import cos, sin, pi
from pathlib import Path

ROOT = Path(__file__).parent


def point(value, radius=104):
    angle = value / 100 * 2 * pi - pi / 2
    return 170 + radius * cos(angle), 165 + radius * sin(angle)


def ring(added):
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="340" height="340" viewBox="0 0 340 340">',
             '<rect width="340" height="340" fill="#fafbf9"/>',
             '<g font-family="sans-serif" font-size="14" fill="#28343b" text-anchor="middle">',
             f'<text x="170" y="25">{"After: A, B, C + D" if added else "Before: A, B, C"}</text>',
             '<circle cx="170" cy="165" r="104" fill="none" stroke="#7f8f99" stroke-width="2"/>']
    x1, y1 = point(20)
    x2, y2 = point(40)
    parts.append(f'<path d="M{x1},{y1} A104,104 0 0,1 {x2},{y2}" fill="none" stroke="#338573" stroke-width="9"/>')
    for label, value in [('A', 20), ('B', 60), ('C', 90)] + ([('D', 40)] if added else []):
        x, y = point(value)
        tx, ty = point(value, 135)
        parts.extend([f'<circle cx="{x}" cy="{y}" r="5" fill="#28343b"/>',
                      f'<text x="{tx}" y="{ty+5}">{label}: {value}</text>'])
    x, y = point(30)
    parts.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#b47721"/>')
    parts.extend(['<text x="170" y="51">0 / 100</text>',
                  '<text x="170" y="151">Clockwise</text>',
                  f'<text x="170" y="176">key: 30 → {"D" if added else "B"}</text>',
                  f'<text x="170" y="310">(20, 40] → {"D" if added else "B"}</text>', '</g></svg>'])
    (ROOT / ('ring-after.svg' if added else 'ring-before.svg')).write_text('\n'.join(parts))


def moved_figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ink, sub, accent, red = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
    plt.rcParams.update({
        "font.size": 10, "axes.edgecolor": sub, "axes.labelcolor": ink,
        "xtick.color": ink, "ytick.color": ink, "text.color": ink,
        "svg.fonttype": "path", "svg.hashsalt": "consistent-hashing",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    out = subprocess.run([sys.executable, str(ROOT / "experiment.py")],
                         capture_output=True, text=True, check=True).stdout
    rows = re.findall(r"^(\S+): changed=(\d+) \(([\d.]+)%\), A=(\d+) B=(\d+) "
                      r"C=(\d+) D=(\d+)$", out, re.M)
    assert len(rows) == 3, out
    names = {"modulo": "modulo", "ring-v1": "ring, 1 token",
             "ring-v128": "ring, 128 tokens"}
    labels = [names[r[0]] for r in rows]
    moved = [float(r[2]) for r in rows]
    keys = [[int(v) / 1000 for v in r[3:]] for r in rows]

    fig, (left, right) = plt.subplots(
        1, 2, figsize=(7.2, 4.0), gridspec_kw={"width_ratios": [1, 1.25]})
    y = list(range(len(rows)))[::-1]
    left.barh(y, moved, color=[red, sub, sub], height=0.6)
    for yi, v in zip(y, moved):
        left.text(v + 2, yi, f"{v:.2f}%", va="center", fontsize=10)
    left.set_yticks(y, labels)
    left.set_xlim(0, 100)
    left.set_xlabel("Keys whose owner changed (%)")

    width = 0.2
    for i, node in enumerate("ABCD"):
        xs = [k + (i - 1.5) * width for k in range(len(rows))]
        right.bar(xs, [ks[i] for ks in keys], width=width * 0.92,
                  color=accent if node == "D" else "#c8c8c8",
                  label="D (added)" if node == "D" else ("A, B, C" if node == "A" else None))
    right.axhline(25, color=sub, lw=1.2, ls="--", zorder=0)
    right.text(2.62, 26.5, "even 25k", ha="right", color=sub, fontsize=9)
    right.set_xticks(range(len(rows)), [l.replace(", ", ",\n") for l in labels])
    right.set_ylabel("Keys per node after adding D (thousand)")
    right.set_ylim(0, 80)
    right.legend(frameon=False, loc="upper right", fontsize=9)
    for ax in (left, right):
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    (ROOT / "images").mkdir(exist_ok=True)
    fig.savefig(ROOT / "images" / "consistent-hashing_moved.svg",
                metadata={"Date": None})
    plt.close(fig)


def replica_figure():
    """Walk clockwise from a key and skip tokens of a node already chosen."""
    ink, sub, accent, pale = "#1f1f1f", "#666666", "#7aa6c2", "#eaf1f5"
    ochre = "#d4a24c"
    cx, cy, r = 270, 285, 175

    def at(value, radius=r):
        a = value / 100 * 2 * pi - pi / 2
        return cx + radius * cos(a), cy + radius * sin(a)

    font = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" '
             'viewBox="0 0 960 540" role="img"><title>複製先を選ぶ時の進み方</title>',
             f'<style>text{{font-family:{font};fill:{ink}}}</style>',
             '<rect width="960" height="540" fill="#ffffff"/>',
             f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#c8c8c8" stroke-width="3"/>']
    key, last = 6, 80
    x1, y1 = at(key)
    x2, y2 = at(last)
    parts.append(f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 1,1 {x2:.1f},{y2:.1f}" '
                 f'fill="none" stroke="{accent}" stroke-width="8"/>')
    tokens = [("A:0", 15, 1), ("A:1", 32, 0), ("B:0", 48, 2), ("A:2", 64, 0),
              ("C:0", 80, 3), ("B:1", 93, None)]
    for name, v, order in tokens:
        x, y = at(v)
        tx, ty = at(v, r + 52)
        if order:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="22" fill="{pale}" '
                         f'stroke="{accent}" stroke-width="3"/>')
            parts.append(f'<text x="{x:.1f}" y="{y + 9:.1f}" font-size="24" '
                         f'text-anchor="middle">{order}</text>')
        else:
            dash = ' stroke-dasharray="5 5"' if order == 0 else ""
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="#f2f2f2" '
                         f'stroke="{sub}" stroke-width="2.5"{dash}/>')
        color = ink if order else sub
        parts.append(f'<text x="{tx:.1f}" y="{ty + 9:.1f}" font-size="26" '
                     f'text-anchor="middle" style="fill:{color}">{name}</text>')
    kx, ky = at(key)
    parts.append(f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="11" fill="{ochre}"/>')
    parts.append(f'<text x="{kx + 22:.1f}" y="{ky - 22:.1f}" font-size="24">key</text>')
    parts.append(f'<text x="{cx}" y="{cy + 9}" font-size="24" text-anchor="middle" '
                 f'style="fill:{sub}">時計回り</text>')
    rows = [("1", "A:0 → A"), ("", "A:1 は A なので飛ばす"), ("2", "B:0 → B"),
            ("", "A:2 は A なので飛ばす"), ("3", "C:0 → C")]
    y = 150
    for order, label in rows:
        if order:
            parts.append(f'<circle cx="610" cy="{y - 9}" r="22" fill="{pale}" '
                         f'stroke="{accent}" stroke-width="3"/>')
            parts.append(f'<text x="610" y="{y}" font-size="24" text-anchor="middle">{order}</text>')
            parts.append(f'<text x="650" y="{y}" font-size="26">{label}</text>')
        else:
            parts.append(f'<text x="650" y="{y}" font-size="24" style="fill:{sub}">{label}</text>')
        y += 62
    parts.append('<text x="590" y="480" font-size="24" style="fill:#666666">'
                 '3 台に複製する場合</text>')
    (ROOT / "images").mkdir(exist_ok=True)
    (ROOT / "images" / "consistent-hashing_replicas.svg").write_text(
        "\n".join(parts + ["</svg>"]) + "\n", encoding="utf-8")


if __name__ == '__main__':
    ring(False)
    ring(True)
    moved_figure()
    replica_figure()
