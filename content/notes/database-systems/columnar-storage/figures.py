"""Generate the SVG figures of the Columnar Storage note (Python stdlib only).

Run: python3 content/notes/database-systems/columnar-storage/figures.py

The row group numbers in rowgroups.svg come from lab/output.txt
(DuckDB v1.5.5, lab/columnar.sql). Re-run the lab and update READ_SORTED
if the data generator changes. colsizes.svg parses the per-column byte tables
of lab/output.txt. vector.svg is a concept diagram whose call counts follow the
note (4,000,000 rows, DuckDB's default vector of 2,048 values).
"""

from html import escape
from pathlib import Path

OUT = Path(__file__).parent / "images"

TEXT = "#1f1f1f"
SUB = "#666666"
FILL = "#f2f2f2"
ACCENT = "#7aa6c2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Figure:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{TEXT}}} .sub{{fill:{SUB}}}</style>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=15, anchor="start", weight="normal", cls=""):
        c = f' class="{cls}"' if cls else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}"{c}>{escape(s)}</text>'
        )

    def rect(self, x, y, w, h, fill="#ffffff", stroke=SUB, dash=False, sw=1.2):
        d = ' stroke-dasharray="4 3"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>'
        )

    def line(self, x1, y1, x2, y2, dash=False):
        d = ' stroke-dasharray="4 3"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" stroke-width="1.2"{d}/>'
        )

    def save(self, name):
        OUT.mkdir(exist_ok=True)
        (OUT / name).write_text("\n".join(self.parts + ["</svg>"]) + "\n")


ROWS = [(1, "tokyo", 120), (2, "osaka", 80), (3, "tokyo", 450)]


def layout():
    """Same 3-row table laid out row by row and column by column."""
    f = Figure(720, 350, "同じ表を行ごとに並べた場合と列ごとに並べた場合のバイトの並び")
    cell_w, cell_h, x0 = 66, 40, 100

    def cell(x, y, value, col):
        hot = col == 2
        f.rect(x, y, cell_w, cell_h, ACCENT if hot else FILL, TEXT if hot else SUB)
        f.text(x + cell_w / 2, y + 27, str(value), 18, "middle")

    # Row store: id, region, amount of row 1, then row 2, ...
    f.text(20, 30, "Row Store（行ごとに連続）", 19, weight="normal")
    y = 48
    f.text(20, y + 27, "ファイル", 17, cls="sub")
    x = x0
    for r, row in enumerate(ROWS):
        for c, v in enumerate(row):
            cell(x, y, v, c)
            x += cell_w
        f.text(x0 + r * 3 * cell_w + 1.5 * cell_w, y + cell_h + 22, f"行 {r + 1}", 16, "middle", cls="sub")
    f.text(20, y + cell_h + 48, "amount は 3 か所に散る", 17, cls="sub")

    # Column store: all ids, then all regions, then all amounts.
    f.text(20, 192, "Column Store（列ごとに連続）", 19, weight="normal")
    y = 210
    f.text(20, y + 27, "ファイル", 17, cls="sub")
    x = x0
    for c, name in enumerate(["id", "region", "amount"]):
        start = x
        for row in ROWS:
            cell(x, y, row[c], c)
            x += cell_w
        f.text(start + 1.5 * cell_w, y + cell_h + 22, f"{name} 列", 16, "middle", cls="sub")
    f.text(20, y + cell_h + 48, "amount は 1 か所に続く", 17, cls="sub")

    # Legend
    f.rect(420, 322, 18, 16, ACCENT, TEXT)
    f.text(446, 336, "sum(amount) が必要とする値", 17)
    f.save("layout.svg")


TOTAL_ROW_GROUPS = 33
READ_SORTED = {6, 7}  # lab/output.txt: ts min/max overlaps 2026-03-01 only in these


def rowgroups():
    """Row groups read by the 1-day range query: sorted vs shuffled file."""
    f = Figure(640, 250, "1 日分の範囲条件で読んだ row group。ts 順のファイルは 2 個、順序を崩したファイルは 33 個")
    box, gap, x0 = 16, 2, 20

    def strip(y, read, label, note):
        f.text(x0, y - 12, label, 19, weight="normal")
        for i in range(TOTAL_ROW_GROUPS):
            hot = i in read
            f.rect(x0 + i * (box + gap), y, box, 34,
                   ACCENT if hot else "#ffffff", TEXT if hot else SUB, dash=not hot)
        f.text(x0, y + 58, note, 17, cls="sub")

    strip(44, READ_SORTED, "ts の順に書いた sales.parquet", "6 と 7 の 2 個だけを読む")
    strip(152, set(range(TOTAL_ROW_GROUPS)), "行の順序を崩した sales_shuffled.parquet", "33 個全部を読む")

    f.rect(380, 222, 16, 16, ACCENT, TEXT)
    f.text(402, 236, "読んだ", 17)
    f.rect(480, 222, 16, 16, "#ffffff", SUB, dash=True)
    f.text(502, 236, "飛ばした", 17)
    f.save("rowgroups.svg")


OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
PALE = "#eaf1f5"


def column_bytes(header):
    """Read one `col | <header>` table (or the encodings table) of lab/output.txt."""
    lines = (Path(__file__).parent / "lab" / "output.txt").read_text().splitlines()
    i = next(n for n, l in enumerate(lines) if header in l and "col" in l)
    out = {}
    for l in lines[i + 3:]:
        if l.startswith("└"):
            break
        cells = [c.strip() for c in l.strip("│").split("│")]
        out[cells[0]] = int(cells[-1])
    return out


def colsizes():
    """Per-column bytes of the same 4,000,000 rows written in three row orders."""
    files = [
        ("sales.parquet（ts の順）", column_bytes("bytes  │")),
        ("region の順に並べ替え", column_bytes("by_region_bytes")),
        ("行の順序を崩す", column_bytes("shuffled_bytes")),
    ]
    f = Figure(960, 540, "同じ 400 万行を 3 つの行の順序で書いた Parquet の、列ごとのバイト数")
    order = [("ts", OCHRE_PALE, OCHRE), ("id", OCHRE_PALE, OCHRE),
             ("region", PALE, ACCENT), ("status", FILL, SUB), ("amount", FILL, SUB)]
    x0, scale = 40, 720 / 47e6
    for r, (label, cols) in enumerate(files):
        y = 60 + r * 135
        tiny = [n for n, _, _ in order if cols[n] < 100_000]
        f.text(x0, y, label, 24)
        f.text(x0 + 330, y, "ほぼ 0 の列: " + ("・".join(tiny) or "なし"), 24, cls="sub")
        x = x0
        for name, fill, stroke in order:
            w = cols[name] * scale
            if w < 1:
                continue
            f.rect(x, y + 16, w, 56, fill, stroke, sw=2)
            if w > 70:
                f.text(x + w / 2, y + 54, name, 24, "middle")
            x += w
        total = sum(cols.values())
        f.text(x + 14, y + 54, f"列の合計 {total / 1e6:.1f} MB", 24)
    f.rect(x0, 452, 22, 22, OCHRE_PALE, OCHRE, sw=2)
    f.text(x0 + 32, 471, "ts・id（連番、Delta）", 24)
    f.rect(x0 + 330, 452, 22, 22, PALE, ACCENT, sw=2)
    f.text(x0 + 362, 471, "region（8 種類、Dictionary）", 24)
    f.rect(x0, 496, 22, 22, FILL, SUB, sw=2)
    f.text(x0 + 32, 515, "amount と、その左の細い status", 24)
    f.save("colsizes.svg")


def vector():
    """Tuple-at-a-time vs vector-at-a-time calls between operators."""
    f = Figure(960, 540, "1 行ずつ渡すエグゼキュータと、vector ずつ渡すエグゼキュータの呼び出し回数")
    x0, w, h = 380, 40, 48

    f.text(40, 70, "1 行ずつ", 26)
    f.text(40, 108, "呼び出し 約 400 万回", 24, cls="sub")
    f.text(40, 142, "1 回の中身: 足し算 1 回", 24, cls="sub")
    for i in range(10):
        x = x0 + i * (w + 14)
        f.rect(x, 150, w, h, FILL, SUB, sw=2)
        f.parts.append(f'<path d="M{x + w / 2} 140 L{x + w / 2} 100" stroke="{OCHRE}" stroke-width="3"/>')
        f.parts.append(f'<circle cx="{x + w / 2}" cy="96" r="6" fill="{OCHRE}"/>')
    f.text(x0 + 10 * (w + 14) - 14, 230, "…", 24, "end", cls="sub")

    f.text(40, 330, "vector ずつ", 26)
    f.text(40, 368, "呼び出し 約 2,000 回", 24, cls="sub")
    f.text(40, 402, "1 回の中身: 配列を回すループ", 24, cls="sub")
    group = 10 * (w + 14) - 14
    f.rect(x0 - 8, 412, group + 16, h + 16, PALE, ACCENT, sw=2.5)
    for i in range(10):
        f.rect(x0 + i * (w + 14), 420, w, h, "#ffffff", ACCENT, sw=1.5)
    mid = x0 + group / 2
    f.parts.append(f'<path d="M{mid} 404 L{mid} 330" stroke="{OCHRE}" stroke-width="3"/>')
    f.parts.append(f'<circle cx="{mid}" cy="326" r="6" fill="{OCHRE}"/>')
    f.text(mid, 512, "2,048 件を 1 回で渡す", 24, "middle", cls="sub")

    f.rect(560, 34, 22, 22, "#ffffff", OCHRE, sw=0)
    f.parts.append(f'<circle cx="571" cy="45" r="6" fill="{OCHRE}"/>')
    f.text(592, 54, "演算子間の呼び出し 1 回", 24)
    f.save("vector.svg")


if __name__ == "__main__":
    layout()
    rowgroups()
    colsizes()
    vector()
