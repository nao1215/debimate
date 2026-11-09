"""Partitioning - 表をキーで分ける の図を生成する。

再生成（標準ライブラリだけで動く）:
    python3 content/notes/database-systems/partitioning/figures.py
"""

import pathlib

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


def text(x, y, s, size=13, color=INK, anchor="middle", weight="normal"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'font-weight="{weight}" {FONT}>{s}</text>')


def line(x1, y1, x2, y2, color=GRAY, dash=None, sw=1.2):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}"{d}/>')


def panel(ox, title, subtitle, global_index):
    parts = [text(ox + 165, 28, title, size=15, weight="bold"),
             text(ox + 165, 48, subtitle, size=12, color=GRAY)]
    months = ["2026-10", "2026-11", "2026-12"]
    px = [ox + 10 + i * 110 for i in range(3)]
    # パーティション（表）
    for i, (x, m) in enumerate(zip(px, months)):
        dropped = i == 0
        parts.append(rect(x, 170, 90, 70, fill="#ffffff" if dropped else FILL,
                          stroke=RED if dropped else INK, dash="5 4" if dropped else None))
        parts.append(text(x + 45, 198, m, color=RED if dropped else INK))
        parts.append(text(x + 45, 218, "partition", size=11, color=GRAY))
    parts.append(text(px[0] + 45, 262, "DROP PARTITION" if global_index else "DROP",
                      size=11, color=RED))
    if not global_index:
        # パーティションごとの索引
        for i, x in enumerate(px):
            dropped = i == 0
            parts.append(rect(x + 10, 80, 70, 40, fill="#ffffff" if dropped else "#e3eef5",
                              stroke=RED if dropped else BLUE, dash="5 4" if dropped else None))
            parts.append(text(x + 45, 105, "index", size=12, color=RED if dropped else INK))
            parts.append(line(x + 45, 120, x + 45, 170, color=RED if dropped else GRAY,
                              dash="4 3" if dropped else None))
        parts.append(text(ox + 165, 300, "The index is dropped with its partition.", size=12, color=GRAY))
    else:
        # 全パーティションにまたがる 1 本の索引
        parts.append(rect(px[0], 80, 310, 40, fill="#e3eef5", stroke=BLUE))
        parts.append(text(ox + 165, 105, "one global index", size=12))
        for i, x in enumerate(px):
            dropped = i == 0
            for dx in (25, 65):
                parts.append(line(x + dx, 120, x + dx, 170, color=RED if dropped else GRAY,
                                  dash="4 3" if dropped else None))
        parts.append(text(ox + 165, 300, "Entries pointing to the dropped partition", size=12, color=GRAY))
        parts.append(text(ox + 165, 318, "need index maintenance (rebuild or UPDATE INDEXES).", size=12, color=GRAY))
    return parts


def local_global():
    w, h = 720, 340
    body = [f'<rect width="{w}" height="{h}" fill="#ffffff"/>']
    body += panel(10, "Local index", "e.g. PostgreSQL", global_index=False)
    body.append(line(360, 20, 360, 320, color="#dddddd"))
    body += panel(380, "Global index", "e.g. Oracle Database", global_index=True)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
           + "".join(body) + "</svg>\n")
    path = OUT / "local-global-index.svg"
    path.write_text(svg, encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    local_global()
