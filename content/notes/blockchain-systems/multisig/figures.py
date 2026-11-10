"""Generate the concept figure of the Multisig note (stdlib only).

Three columns answer two questions for the same 3-key setup:
where the m-of-n rule is checked, and how many signatures the chain sees.
- Bitcoin P2WSH: Script checks 2 of 3; the witness carries 2 signatures and 3 keys.
- Ethereum Safe: a contract checks threshold 2; calldata carries 2 signatures.
- MuSig2 / MPC: the signers cooperate off-chain; the chain sees 1 key and 1 signature.

Run: python3 content/notes/blockchain-systems/multisig/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_F = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_F = "#d4a24c", "#f8eed8"
GRAY_F = "#f2f2f2"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" '
            f'markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                          f'style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                          f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, x, y, r, fill, stroke):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')

    def line(self, x1, y1, x2, y2, color=SUB, sw=3, arrow=True):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                          f'stroke-width="{sw}" stroke-linecap="round"{m}/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def column(s, cx, title, rule, rule_sub, fill, stroke, sigs, keys, chain_label, dash=""):
    """One setup: 3 signer keys -> where the rule is checked -> what the chain stores."""
    s.text(cx, 46, title, size=28)
    for i, dx in enumerate((-70, 0, 70)):  # three signers A, B, C
        s.circle(cx + dx, 104, 26, "#ffffff", INK)
        s.text(cx + dx, 113, "ABC"[i], size=24)
    s.line(cx, 138, cx, 176)
    s.box(cx - 140, 184, 280, 108, fill, stroke, dash=dash)
    s.text(cx, 228, rule, size=26)
    s.text(cx, 266, rule_sub, size=24, color=SUB)
    s.line(cx, 298, cx, 336)
    # On-chain record: signature squares (ink) and key bars (gray).
    s.box(cx - 140, 344, 280, 170, GRAY_F)
    s.text(cx, 382, chain_label, size=24, color=SUB)
    w = 36
    x0 = cx - (sigs * w + (sigs - 1) * 10) / 2
    for i in range(sigs):
        s.box(x0 + i * (w + 10), 404, w, w, INK, rx=4)
    kx0 = cx - (keys * 64 + (keys - 1) * 10) / 2
    for i in range(keys):
        s.box(kx0 + i * 74, 460, 64, 20, "#ffffff", SUB, sw=2, rx=4)
    s.text(cx, 506, f"{sigs} sig{'s' if sigs > 1 else ''} / {keys} key{'s' if keys > 1 else ''}", size=24)


def concept_figure():
    s = Svg(960, 540, "Where the m-of-n rule is checked, and what the chain sees")
    column(s, 162, "Bitcoin P2WSH", "Script", "2 of 3", BLUE_F, BLUE, 2, 3, "witness")
    column(s, 480, "Ethereum Safe", "contract", "threshold 2", OCHRE_F, OCHRE, 2, 3, "calldata + storage")
    column(s, 798, "MuSig2 / MPC", "off-chain", "signers combine", "#ffffff", SUB, 1, 1, "on-chain", dash="8 6")
    s.save(HERE / "images" / "multisig_concept.svg")


RED = "#e15759"


def order_panel(s, cx, title, sub, sigs, ok):
    """Keys A, B, C on top; signatures below. Matching starts from the last pushed item."""
    kx = {"A": cx - 140, "B": cx, "C": cx + 140}
    sx = [cx - 70, cx + 70]
    s.text(cx, 64, title, 30)
    s.text(cx, 102, sub, 24, SUB)
    for k, x in kx.items():
        s.box(x - 50, 140, 100, 64, BLUE_F, BLUE)
        s.text(x, 182, f"鍵 {k}", 26)
    for name, x in zip(sigs, sx):
        s.box(x - 60, 330, 120, 64, OCHRE_F, OCHRE)
        s.text(x, 372, f"署名 {name}", 26)
    # the last pushed signature (right) is matched first; keys are tried from C down to A
    keys = ["C", "B", "A"]
    i = 0
    for j in (1, 0):
        x, name = sx[j], sigs[j]
        while i < 3 and keys[i] != name:
            s.line(x, 326, kx[keys[i]], 208, SUB, 2.5, arrow=False)
            s.parts[-1] = s.parts[-1].replace("/>", ' stroke-dasharray="6 6"/>')
            i += 1
        if i < 3:
            s.line(x, 326, kx[keys[i]], 210, INK, 3.5)
            i += 1
        else:
            s.line(x - 16, 408, x + 16, 440, RED, 5, arrow=False)
            s.line(x + 16, 408, x - 16, 440, RED, 5, arrow=False)
            s.text(x, 474, "残る鍵が無い", 24, SUB)
    s.text(cx, 474 if ok else 520, "最後まで一致して通る" if ok else "", 24, SUB)


def order_figure():
    s = Svg(960, 540, "OP_CHECKMULTISIG は末尾から照らし合わせ、飛ばした公開鍵には戻らない")
    s.line(480, 40, 480, 500, "#d9d9d9", 2, arrow=False)
    order_panel(s, 240, "公開鍵と同じ順", "A, B の順に積む", ["A", "B"], True)
    order_panel(s, 720, "逆の順", "B, A の順に積む", ["B", "A"], False)
    s.text(480, 528, "実線は一致、点線は一致せずに飛ばした公開鍵", 24, SUB)
    s.save(HERE / "images" / "multisig_order.svg")


if __name__ == "__main__":
    concept_figure()
    order_figure()
