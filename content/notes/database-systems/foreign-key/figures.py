"""Generate the cover diagram of the foreign key note (stdlib only).

concept_figure() draws members (parent) and orders (child) side by side.
Left: without a foreign key, DELETE of member 42 succeeds and the orders
that pointed to 42 are left with an empty target (orphan records).
Right: with a foreign key (default NO ACTION), the same DELETE is rejected.
Parents are blue, children ochre; red marks only the orphan records.

Run: python3 content/notes/database-systems/foreign-key/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED_PALE = "#fbe3e3"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    """Minimal hand-written SVG canvas (stdlib only)."""

    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                for n, c in (("red", RED), ("sub", SUB), ("accent", ACCENT)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


PARENT = [41, 42, 43]
CHILD = [41, 42, 42, 43]


def tables(f, ox, with_fk):
    px, pw, cx, cw = ox + 40, 140, ox + 270, 150
    f.text(px + pw / 2, 132, "members（親）", 22, SUB)
    f.text(cx + cw / 2, 132, "orders（子）", 22, SUB)
    p_y = {k: 170 + i * 84 for i, k in enumerate(PARENT)}
    for k, y in p_y.items():
        gone = k == 42 and not with_fk
        if gone:
            f.box(px, y, pw, 60, "#ffffff", SUB, sw=3, dash="9 6")
            f.text(px + pw / 2, y + 40, "削除済み", 24, SUB)
        else:
            f.box(px, y, pw, 60, PALE, ACCENT)
            f.text(px + pw / 2, y + 40, f"id {k}", 26)
    for i, k in enumerate(CHILD):
        y = 160 + i * 66
        orphan = k == 42 and not with_fk
        color = RED if orphan else SUB
        f.line(cx, y + 28, px + pw + 6, p_y[k] + 30, color, sw=4 if orphan else 3,
               arrow="red" if orphan else "sub")
        f.box(cx, y, cw, 54, RED_PALE if orphan else OCHRE_PALE, RED if orphan else OCHRE,
              sw=3 if orphan else 2.5)
        f.text(cx + cw / 2, y + 37, f"→ {k}", 26, INK)


def concept_figure():
    f = Svg(960, 540, "外部キーの有無と、親を消した時の子のレコード")
    f.text(240, 66, "外部キーなし", 30, weight="normal")
    tables(f, 0, with_fk=False)
    f.text(240, 460, "DELETE は成功し、子だけが残る", 26, INK)
    f.text(240, 500, "参照先の無い注文（孤児レコード）", 24, SUB)

    f.line(480, 40, 480, 510, "#dddddd", sw=2)

    f.text(720, 66, "外部キーあり", 30, weight="normal")
    tables(f, 480, with_fk=True)
    f.text(720, 460, "DELETE はエラーで止まる", 26, INK)
    f.text(720, 500, "子が残る限り親は消えない", 24, SUB)
    f.save(HERE / "images" / "foreign-key_concept.svg")


def delete_time_figure():
    """Parent DELETE time by child rows, from lab/fk_delete_output.txt (PostgreSQL measurement)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "foreign-key",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    rows = {"no": [], "yes": []}
    for line in (HERE / "lab" / "fk_delete_output.txt").read_text().splitlines():
        f = line.split()
        if len(f) >= 4 and f[0].isdigit():
            rows[f[1]].append((int(f[0]), float(f[2])))
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for key, color, mk, label in (("no", RED, "o", "no index on orders.member_id"),
                                  ("yes", ACCENT, "s", "index on orders.member_id")):
        xs, ys = zip(*rows[key])
        ax.plot(xs, ys, color=color, marker=mk, lw=2.4, ms=6, label=label)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks([10_000, 100_000, 1_000_000], ["10k", "100k", "1M"])
    ax.set_yticks([1, 10, 100], ["1", "10", "100"])
    ax.set_xlabel("Rows in orders (child)")
    ax.set_ylabel("DELETE of one member (ms)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "foreign-key_delete_time.svg", metadata={"Date": None})
    plt.close(fig)


def on_delete_figure():
    """What remains of member 42 and its order after DELETE, per ON DELETE."""
    f = Svg(960, 540, "ON DELETE の指定ごとに、会員 42 を DELETE した後に残るレコード")
    cols = [
        (("NO ACTION /", "RESTRICT"), True, "member_id=42", "DELETE はエラー", RED),
        (("CASCADE",), False, None, "子も消える", INK),
        (("SET NULL",), False, "member_id=NULL", "参照だけ外れる", INK),
        (("SET DEFAULT",), False, "member_id=既定値", "既定値に替わる", INK),
    ]
    f.text(480, 46, "会員 42 を DELETE した後", 26)
    for k, (head, parent_left, child, result, color) in enumerate(cols):
        cx = 122 + k * 238
        for j, h in enumerate(head):
            f.text(cx, 104 + j * 30 + (15 if len(head) == 1 else 0), h, 24, SUB)
        # Parent row (member 42).
        if parent_left:
            f.box(cx - 105, 170, 210, 60, PALE, ACCENT)
            f.text(cx, 209, "会員 42", 24)
        else:
            f.box(cx - 105, 170, 210, 60, "#ffffff", SUB, sw=2, dash="7 6")
            f.text(cx, 209, "会員 42", 24, SUB)
        # Child row (an order of member 42).
        if child:
            f.box(cx - 116, 300, 232, 90, OCHRE_PALE, OCHRE)
            f.text(cx, 336, "注文", 24)
            f.text(cx, 372, child, 24)
        else:
            f.box(cx - 116, 300, 232, 90, "#ffffff", SUB, sw=2, dash="7 6")
            f.text(cx, 354, "注文", 24, SUB)
        if parent_left:
            f.line(cx, 298, cx, 236, SUB, sw=2.5, arrow="sub")
        f.text(cx, 460, result, 24, color)
    f.save(HERE / "images" / "foreign-key_on_delete.svg")


if __name__ == "__main__":
    concept_figure()
    delete_time_figure()
    on_delete_figure()
