"""Generate the cover diagram of the Zero-Knowledge Proof note (stdlib only).

concept_figure() draws the prover and the verifier as two frames. The secret
input (ochre) stays inside the prover's frame; only the public result and a small
proof cross the boundary. The verifier holds only the expected program ID (image ID), not the program run.

The SVG text is rendered with headless Chrome at 2x and saved as WebP (Pillow).
Only the WebP file is kept in images/. Needs google-chrome and Pillow.

Run: python3 content/notes/blockchain-systems/zero-knowledge-proof/figures.py
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    """A tiny hand-written SVG builder (960x540, white background)."""

    def __init__(self, title, width=960, height=540):
        self.width, self.height = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
                for name, color in (("sub", SUB), ("accent", ACCENT), ("red", RED)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10, opacity=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' fill-opacity="{opacity}"' if opacity != 1 else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}"{o} stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, r, fill, stroke="none", sw=2.5, dash="", opacity=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' fill-opacity="{opacity}"' if opacity != 1 else ""
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{o} '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def path(self, d, stroke, sw=4, fill="none"):
        self.parts.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            'stroke-linecap="round" stroke-linejoin="round"/>')

    def save(self, name):
        """SVG text -> PNG (headless Chrome, 2x) -> images/<name> (WebP)."""
        (HERE / "images").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu",
                            "--hide-scrollbars", "--force-device-scale-factor=2",
                            f"--window-size={self.width},{self.height}",
                            f"--screenshot={png}", svg.as_uri()],
                           check=True, capture_output=True)
            Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP",
                                                quality=90, method=6)


def concept_figure():
    f = Svg("秘密の入力は証明する側に残り、公開する結果と証明だけが検証する側に渡る")
    # Prover: the secret input never leaves this frame.
    f.text(262, 62, "証明する側", 28, weight="normal")
    f.box(40, 90, 444, 360, "#ffffff", SUB, sw=3, rx=16)
    f.box(72, 136, 176, 76, OCHRE_PALE, OCHRE, sw=3, rx=10)
    f.text(160, 184, "秘密の入力", 26)
    f.box(72, 300, 176, 76, FILL, SUB, sw=2.5)
    f.text(160, 348, "プログラム", 26)
    f.line(250, 190, 300, 232, SUB, sw=4, arrow="sub")
    f.line(250, 322, 300, 282, SUB, sw=4, arrow="sub")
    f.box(306, 212, 156, 90, PALE, ACCENT, sw=3)
    f.text(384, 254, "実行して", 24)
    f.text(384, 284, "証明を生成", 24)
    f.text(262, 494, "秘密は枠の外に出ない", 26, SUB)

    # Only the public result and a small proof cross the boundary.
    f.box(504, 244, 112, 52, ACCENT, rx=8)
    f.text(560, 279, "結果", 26)
    f.box(522, 306, 76, 44, ACCENT, rx=8)
    f.text(560, 337, "証明", 24)
    f.line(464, 250, 498, 268, ACCENT, sw=4)
    f.line(464, 286, 516, 326, ACCENT, sw=4)
    f.line(620, 270, 676, 270, ACCENT, sw=4, arrow="accent")
    f.line(602, 328, 676, 328, ACCENT, sw=4, arrow="accent")

    # Verifier: the same program and the check.
    f.text(790, 62, "検証する側", 28, weight="normal")
    f.box(660, 90, 260, 360, "none", SUB, sw=3, rx=16)
    f.box(686, 120, 208, 76, FILL, SUB, sw=2.5)
    f.text(790, 168, "プログラムの ID", 26)
    f.box(686, 248, 208, 100, GREEN_PALE, GREEN, sw=3)
    f.text(790, 292, "証明と結果を", 26)
    f.text(790, 326, "検証", 26)
    f.line(790, 198, 790, 240, SUB, sw=4, arrow="sub")
    f.text(790, 494, "入力を見ずに検証", 26, SUB)
    f.save("zero-knowledge-proof_concept.webp")


if __name__ == "__main__":
    concept_figure()
