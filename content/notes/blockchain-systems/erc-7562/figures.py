"""Generate the concept figure of the ERC-7562 note (standard library only).

Run: python3 figures.py  -> images/erc-7562_concept.svg
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, NEUTRAL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED = "#e15759"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def concept_figure():
    """Validation reads only what the simulation can pin; the environment is fenced off."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("検証は自分の storage と関連する slot だけを読み、時刻や他のコントラクトの storage は柵の外に置く")}'
        f'</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
        f'markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
    ]

    def text(x, y, s, size=26, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def box(x, y, bw, bh, fill, stroke, rx=10, sw=2, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    # Left: the environment, which differs between simulation and the block.
    text(140, 92, "changes before", 24, cls="sub")
    text(140, 122, "the block", 24, cls="sub")
    env = [("TIMESTAMP", 160), ("NUMBER", 260), ("other storage", 360)]
    for label, y in env:
        box(30, y, 220, 64, OCHRE_PALE, OCHRE)
        text(140, y + 42, label, 25)
    # Arrows converge on the fence and stop there.
    fx, fy = 318, 292
    for _, y in env:
        p.append(f'<line x1="250" y1="{y + 32}" x2="{fx - 14}" y2="{fy + (y - 260) * 0.25}" '
                 f'stroke="{SUB}" stroke-width="2"/>')
    # The only red mark: the blocked access.
    p.append(f'<g stroke="{RED}" stroke-width="7" stroke-linecap="round">'
             f'<line x1="{fx - 20}" y1="{fy - 20}" x2="{fx + 20}" y2="{fy + 20}"/>'
             f'<line x1="{fx - 20}" y1="{fy + 20}" x2="{fx + 20}" y2="{fy - 20}"/></g>')

    # Centre: the sandboxed validation phase.
    box(340, 70, 300, 400, BLUE_PALE, BLUE, rx=16, sw=3)
    text(490, 118, "validation", 30)
    text(490, 152, "ERC-7562 rules", 24, cls="sub")
    box(370, 190, 240, 76, "#ffffff", BLUE)
    text(490, 237, "own storage", 26)
    box(370, 296, 240, 76, "#ffffff", BLUE)
    text(490, 343, "keccak(A||x)+n", 26)
    text(490, 412, "one write,", 24, cls="sub")
    text(490, 444, "one account", 24, cls="sub")

    # Right: the execution phase, no rules.
    p.append(f'<line x1="640" y1="270" x2="694" y2="270" stroke="{SUB}" stroke-width="2.5" '
             f'marker-end="url(#arrow)"/>')
    box(700, 170, 230, 200, NEUTRAL, SUB, rx=12, dash="8 6")
    text(815, 250, "execution", 30)
    text(815, 300, "any code", 26, cls="sub")

    p.append("</svg>")
    (HERE / "images" / "erc-7562_concept.svg").write_text("\n".join(p) + "\n")


class Svg:
    """Small helper for the figures below (960x540, text 24px or larger)."""

    def __init__(self, title, w=960, h=540):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                          f'style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", rx=10, sw=2, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                          f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def arrow(self, x1, y1, x2, y2):
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" '
                          f'stroke-width="2.5" marker-end="url(#arrow)"/>')

    def save(self, name):
        (HERE / "images" / name).write_text("\n".join(self.parts + ["</svg>"]) + "\n",
                                            encoding="utf-8")


def checks_figure():
    """The bundler validates one UserOperation three times before it pays for it."""
    f = Svg("Bundler は 1 件の UserOperation を 3 回検証してから送る")
    steps = [("受け取った時", "1 件だけ"), ("バンドルに入れる前", "1 件ずつ"),
             ("送る直前", "バンドル全体")]
    xs = [20, 290, 560]
    for x, (head, sub) in zip(xs, steps):
        f.box(x, 150, 240, 130, BLUE_PALE, BLUE)
        f.text(x + 120, 205, head, 24)
        f.text(x + 120, 250, sub, 24, SUB)
        f.text(x + 120, 340, {20: "規則を当てる", 290: "状態の変化を見る",
                              560: "組み合わせを見る"}[x], 24, SUB)
    for x in xs[:2]:
        f.arrow(x + 244, 215, x + 266, 215)
    f.arrow(804, 215, 826, 215)
    f.box(830, 150, 115, 130, OCHRE_PALE, OCHRE)
    f.text(887, 205, "チェーン", 24)
    f.text(887, 250, "で実行", 24, SUB)
    f.text(410, 80, "オフチェーンの検証（eth_call・debug_traceCall）", 26)
    f.text(480, 440, "3 回目で、バンドルの中だけ revert する主体を見つける", 24)
    f.text(480, 490, "チェーンの上で失敗すると、手数料は Bundler が払う", 24, SUB)
    f.save("erc-7562_checks.svg")


def paid_figure():
    """Stage 3 of lab/output/summary.txt: who paid for the invalidated bundle."""
    import re
    out = (HERE / "lab" / "output" / "summary.txt").read_text(encoding="utf-8")
    attacker = int(re.search(r"attacker paid\s*: (\d+) gwei", out).group(1))
    bundler = int(re.search(r"bundler paid\s*: (\d+) gwei", out).group(1))
    accounts = int(re.search(r"10 GateAccounts\s*: (\d+) gwei", out).group(1))
    rows = [("Bundler", bundler, BLUE_PALE, BLUE),
            ("攻撃者", attacker, OCHRE_PALE, OCHRE),
            ("10 個の GateAccount", accounts, NEUTRAL, SUB)]
    f = Svg("Gate を閉じた攻撃者より、revert したバンドルを送った Bundler が多く払った")
    f.text(480, 70, "無効になったバンドル 1 件で払った額（gwei）", 26)
    x0, wmax, top = 300, 520, 130
    for i, (label, v, fill, stroke) in enumerate(rows):
        y = top + i * 120
        f.text(x0 - 20, y + 50, label, 24, anchor="end")
        w = wmax * v / bundler
        if w:
            f.box(x0, y + 15, w, 56, fill, stroke, rx=4)
        else:
            f.parts.append(f'<line x1="{x0}" y1="{y + 10}" x2="{x0}" y2="{y + 76}" '
                           f'stroke="{SUB}" stroke-width="2.5"/>')
        f.text(x0 + w + 16, y + 52, f"{v:,}", 24, anchor="start")
    f.text(480, 510, "同じブロックで Gate.close() を先に入れた場合（3 段目）", 24, SUB)
    f.save("erc-7562_paid.svg")


if __name__ == "__main__":
    concept_figure()
    checks_figure()
    paid_figure()
