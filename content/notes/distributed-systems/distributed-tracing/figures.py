"""Generate the waterfall SVGs of the distributed-tracing note.

The span timings are copied from lab/output.txt (rounded to 1 ms).
Run: python3 figures.py
"""

from pathlib import Path

OUT = Path(__file__).parent / "images"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB, LINE, FILL, ACCENT, RED = "#1f1f1f", "#666666", "#d0d0d0", "#f2f2f2", "#7aa6c2", "#e15759"

# (depth, name, service, start_ms, duration_ms, status)
NORMAL = [
    (0, "POST /checkout", "gateway", 0, 56, "OK"),
    (1, "create order", "gateway", 0, 56, "OK"),
    (2, "POST /orders", "orders", 1, 55, "OK"),
    (3, "reserve", "orders", 1, 22, "ERROR"),
    (4, "POST /reserve", "inventory", 2, 21, "ERROR"),
    (3, "reserve (resend 1)", "orders", 34, 22, "OK"),
    (4, "POST /reserve", "inventory", 35, 20, "OK"),
    (3, "publish order.created", "orders", 56, 0, "OK"),
    (4, "process (attempt 1)", "mailer", 57, 10, "ERROR"),
    (4, "process (attempt 2)", "mailer", 67, 10, "OK"),
]

# Same trace, inventory clock 100 ms behind (lab/output.txt, second run).
SKEWED = [
    (2, "POST /orders", "orders", 2, 60, "OK"),
    (3, "reserve", "orders", 2, 22, "ERROR"),
    (4, "POST /reserve", "inventory", -97, 20, "ERROR"),
    (3, "reserve (resend 1)", "orders", 38, 23, "OK"),
    (4, "POST /reserve", "inventory", -60, 21, "OK"),
]


def waterfall(rows, t_min, t_max, path, marks=()):
    label_w, plot_w, row_h, top = 250, 470, 26, 34
    width = label_w + plot_w + 20
    height = top + row_h * len(rows) + 40
    min_depth = min(r[0] for r in rows)

    def x(t):
        return label_w + (t - t_min) / (t_max - t_min) * plot_w

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="{FONT}" font-size="12">',
           f'<rect width="{width}" height="{height}" fill="#ffffff"/>']
    # time grid
    step = 20
    t = (t_min // step) * step
    while t <= t_max:
        if t >= t_min:
            out.append(f'<line x1="{x(t):.1f}" y1="{top - 6}" x2="{x(t):.1f}" '
                       f'y2="{height - 30}" stroke="{LINE}" stroke-width="1"/>')
            out.append(f'<text x="{x(t):.1f}" y="{height - 14}" fill="{SUB}" '
                       f'text-anchor="middle">{t:+d} ms</text>')
        t += step
    out.append(f'<text x="{label_w}" y="18" fill="{SUB}">time from the root span start '
               f'(each host records its own clock)</text>')
    for i, (depth, name, service, start, dur, status) in enumerate(rows):
        y = top + i * row_h
        indent = 10 + (depth - min_depth) * 14
        out.append(f'<text x="{indent}" y="{y + 16}" fill="{INK}">{name}</text>')
        out.append(f'<text x="{label_w - 8}" y="{y + 16}" fill="{SUB}" '
                   f'text-anchor="end">{service}</text>')
        color = RED if status == "ERROR" else ACCENT
        w = max(x(start + dur) - x(start), 2)
        dash = ' stroke-dasharray="4 2"' if status == "ERROR" else ""
        out.append(f'<rect x="{x(start):.1f}" y="{y + 5}" width="{w:.1f}" height="14" '
                   f'fill="{color}" fill-opacity="0.85" stroke="{INK}" stroke-width="0.8"{dash}/>')
        if status == "ERROR":
            out.append(f'<text x="{x(start) + w + 4:.1f}" y="{y + 16}" fill="{RED}">error</text>')
    for t, text in marks:
        out.append(f'<line x1="{x(t):.1f}" y1="{top - 2}" x2="{x(t):.1f}" y2="{height - 30}" '
                   f'stroke="{INK}" stroke-width="1.2" stroke-dasharray="5 3"/>')
        out.append(f'<text x="{x(t) - 6:.1f}" y="{top + 16}" fill="{INK}" text-anchor="end">{text}</text>')
    out.append("</svg>")
    path.write_text("\n".join(out) + "\n")


def main():
    OUT.mkdir(exist_ok=True)
    waterfall(NORMAL, 0, 80, OUT / "distributed_tracing_waterfall.svg")
    waterfall(SKEWED, -110, 60, OUT / "distributed_tracing_skew.svg",
              marks=[(2, "parent starts")])


if __name__ == "__main__":
    main()
