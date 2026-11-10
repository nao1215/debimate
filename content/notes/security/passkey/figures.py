"""Generate the cover diagram of the Passkey note as a hand-written SVG (stdlib only).

concept_figure(): what reaches a look-alike phishing site. With a password the
same string goes to examp1e.com and is reused at example.com. With a passkey
the private key stays in the authenticator, keyed by RP ID, so only
example.com gets a signature and the look-alike site gets none.

Run: python3 content/notes/security/passkey/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=4, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")

    def arrow(self, x1, y1, x2, y2, color, sw=4, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        mid = {RED: "arrowR", SUB: "arrowS", OCHRE: "arrowO"}.get(color, "arrowA")
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d} marker-end="url(#{mid})"/>')

    def cross(self, cx, cy, r, color, sw=6):
        self.line(cx - r, cy - r, cx + r, cy + r, color, sw)
        self.line(cx - r, cy + r, cx + r, cy - r, color, sw)


def markers():
    return ('<defs>' + ''.join(
        f'<marker id="{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" '
        f'markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
        for i, c in (("arrowA", ACCENT), ("arrowR", RED), ("arrowS", SUB), ("arrowO", OCHRE))) + '</defs>')


def site(f, x, y, name, fake, sub=""):
    f.box(x, y, 190, 90, OCHRE_PALE if fake else PALE, OCHRE if fake else ACCENT,
          sw=3, dash="8 6" if fake else "")
    f.text(x + 95, y + (40 if sub else 54), name, 24)
    if sub:
        f.text(x + 95, y + 74, sub, 24, SUB)


def concept_figure():
    f = Svg(960, 540, "偽サイトに渡るものの違い")
    f.parts.insert(2, markers())
    f.line(480, 30, 480, 510, "#dddddd", sw=2)
    top, low = 120, 330  # y of the real site and the look-alike site

    # Left: a password is a string; the fake site receives it and reuses it.
    f.text(240, 60, "Password", 30, weight="normal")
    f.box(20, 220, 150, 100, FILL, SUB, sw=3)
    f.text(95, 262, "利用者", 24)
    f.text(95, 298, "password", 24, SUB)
    site(f, 270, top, "example.com", False)
    site(f, 270, low, "examp1e.com", True)
    f.arrow(170, 250, 262, 175, ACCENT, sw=5)
    f.arrow(170, 290, 262, 370, OCHRE, sw=5)
    f.arrow(365, low - 4, 365, top + 98, RED, sw=5, dash="10 8")
    f.text(240, 490, "同じ文字列で本物に入れる", 24)

    # Right: the private key stays in the authenticator, one key per RP ID.
    f.text(720, 60, "Passkey", 30, weight="normal")
    f.box(500, 150, 200, 230, FILL, SUB, sw=3)
    f.text(600, 190, "Authenticator", 24)
    f.box(518, 220, 164, 130, PALE, ACCENT, sw=3)
    f.text(600, 272, "秘密鍵", 24, weight="normal")
    f.text(600, 312, "example.com", 24)
    site(f, 760, top, "example.com", False, "公開鍵")
    site(f, 760, low, "examp1e.com", True)
    f.arrow(682, 250, 752, 180, ACCENT, sw=5)
    f.text(726, 246, "署名", 24, SUB, anchor="start")
    f.arrow(682, 320, 730, 362, SUB, sw=5, dash="8 7")
    f.cross(744, 375, 13, SUB)
    f.text(720, 490, "偽サイトには署名が出ない", 24)

    f.save(HERE / "images" / "passkey_concept.svg")


def signed_figure():
    """What the authenticator signs: authenticatorData plus the clientDataJSON hash."""
    f = Svg(960, 540, "署名の対象は authenticatorData と clientDataJSON のハッシュを繋いだ値")
    f.parts.append(markers())
    # authenticatorData, made by the authenticator (accent).
    f.text(40, 66, "authenticatorData（Authenticator が作る）", 24, SUB, anchor="start")
    segs = [(40, 360, "RP ID のハッシュ", "32 バイト"), (360, 520, "フラグ", "1 バイト"),
            (520, 690, "signCount", "4 バイト")]
    for x1, x2, name, size in segs:
        f.box(x1, 86, x2 - x1, 84, PALE, ACCENT, rx=0)
        f.text((x1 + x2) / 2, 122, name, 24)
        f.text((x1 + x2) / 2, 156, size, 24, SUB)
    # clientDataJSON hash, made from the client's data (ochre).
    f.text(825, 66, "clientDataJSON", 24, SUB)
    f.box(730, 86, 190, 84, OCHRE_PALE, OCHRE, rx=0)
    f.text(825, 122, "ハッシュ", 24)
    f.text(825, 156, "32 バイト", 24, SUB)
    f.text(710, 140, "+", 30, SUB)

    # The flag byte expanded.
    f.line(360, 172, 270, 236, SUB, sw=2)
    f.line(520, 172, 610, 236, SUB, sw=2)
    for i, name in enumerate(("UP", "UV", "BE", "BS")):
        x = 270 + i * 85
        f.box(x, 236, 85, 56, PALE, ACCENT, rx=0)
        f.text(x + 42.5, 273, name, 24)
    f.text(440, 326, "利用者の確認とバックアップなど", 24, SUB)

    # What goes into clientDataJSON.
    f.line(825, 172, 825, 214, SUB, sw=2)
    f.box(730, 214, 190, 128, "#ffffff", OCHRE, dash="7 6")
    for k, name in enumerate(("type", "challenge", "origin")):
        f.text(825, 250 + k * 36, name, 24)

    # Everything above is signed.
    f.line(40, 382, 920, 382, SUB, sw=2.5)
    f.line(40, 370, 40, 382, SUB, sw=2.5)
    f.line(920, 370, 920, 382, SUB, sw=2.5)
    f.arrow(480, 384, 480, 420, SUB, sw=2.5)
    f.box(300, 426, 360, 64, FILL, SUB)
    f.text(480, 467, "秘密鍵で署名 → signature", 24)
    f.text(480, 524, "どこを書き換えても署名の検証に失敗する", 24, SUB)
    f.save(HERE / "images" / "passkey_signed.svg")


if __name__ == "__main__":
    concept_figure()
    signed_figure()
