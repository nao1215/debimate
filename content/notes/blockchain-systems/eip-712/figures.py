"""Generate the figures of the EIP-712 / ERC-1271 note (Python standard library only)."""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GRAY_PALE = "#f2f2f2"
RED, RED_PALE = "#e15759", "#fbe3e3"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono','Menlo','Consolas',monospace"


def concept_figure():
    """The signed digest = 0x1901 | domain separator | hashStruct(message)."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("署名する 32 バイトは 0x1901、domain separator、メッセージのハッシュを繋いだもののハッシュ")}'
        f'</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}} .mono{{font-family:{MONO}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
        f'markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
    ]

    def text(x, y, s, size=26, anchor="middle", cls="", fill=None):
        c = f' class="{cls}"' if cls else ""
        f = f' style="fill:{fill}"' if fill else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}{f}>{escape(s)}</text>')

    def box(x, y, bw, bh, stroke, fill, sw=2.5, rx=8):
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"/>')

    def line(x1, y1, x2, y2, arrow=True, dash=False):
        m = ' marker-end="url(#arr)"' if arrow else ""
        d = ' stroke-dasharray="6 5"' if dash else ""
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" stroke-width="2"{m}{d}/>')

    # keccak256 is taken over the whole row: 2 + 32 + 32 = 66 bytes.
    p.append(f'<path d="M40,84 V70 H920 V84" fill="none" stroke="{SUB}" stroke-width="2"/>')
    text(480, 52, "keccak256( whole row ) = the 32 bytes the key signs", 26)

    y0, bh = 92, 76
    box(40, y0, 90, bh, SUB, GRAY_PALE)
    text(85, y0 + 48, "1901", 26, cls="mono")
    box(130, y0, 390, bh, OCHRE, OCHRE_PALE)
    text(325, y0 + 48, "domain separator", 28)
    box(520, y0, 400, bh, BLUE, BLUE_PALE)
    text(720, y0 + 48, "hashStruct(message)", 28)

    # What goes into each 32-byte segment.
    top = 218
    box(150, top, 350, 230, OCHRE, "#ffffff", sw=2)
    for i, f in enumerate(["name", "version", "chainId", "verifyingContract"]):
        text(176, top + 44 + 50 * i, f, 26, anchor="start", cls="mono")
    line(325, y0 + bh, 325, top - 4)
    # One changed field: the same signature no longer matches.
    box(410, top + 120, 76, 40, RED, RED_PALE, sw=2, rx=6)
    text(448, top + 149, "≠", 28, fill=RED)

    box(530, top, 390, 230, BLUE, "#ffffff", sw=2)
    text(556, top + 44, "typeHash", 26, anchor="start", cls="mono")
    text(556, top + 80, "Permit(address owner,…)", 24, anchor="start", cls="sub mono")
    for i, f in enumerate(["owner / spender", "value / nonce / deadline"]):
        text(556, top + 144 + 46 * i, f, 24, anchor="start", cls="mono")
    line(720, y0 + bh, 720, top - 4)

    text(480, 506, "another chainId or contract → another digest → signature fails", 24, cls="sub")

    p.append("</svg>")
    (HERE / "images" / "eip-712_concept.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


def _canvas(title):
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}} .mono{{font-family:{MONO}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
        f'markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
    ]

    def text(x, y, s, size=26, anchor="middle", cls="", fill=None):
        c = f' class="{cls}"' if cls else ""
        f = f' style="fill:{fill}"' if fill else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}{f}>{escape(s)}</text>')

    def box(x, y, bw, bh, stroke, fill, sw=2.5, rx=8, dash=False):
        d = ' stroke-dasharray="7 5"' if dash else ""
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(x1, y1, x2, y2, arrow=True, dash=False):
        m = ' marker-end="url(#arr)"' if arrow else ""
        d = ' stroke-dasharray="6 5"' if dash else ""
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" stroke-width="2"{m}{d}/>')

    return p, text, box, line


def replay_figure():
    """One permit signature handed to three tokens (experiment 2 of lab/run.py)."""
    p, text, box, line = _canvas("同じ permit の署名を 3 つのトークンに渡すと、ドメインが違う 2 つでは別人のアドレスが復元される")
    # The single signature on the left.
    box(30, 200, 230, 140, BLUE, BLUE_PALE)
    text(145, 255, "1 signature", 28)
    text(145, 298, "owner 0x7099…", 24, cls="sub mono")

    rows = [
        (40, BLUE, BLUE_PALE, "token, chain 31337", "the signed domain", "recovers 0x7099… = owner"),
        (200, OCHRE, OCHRE_PALE, "same address, chain 31338", "chainId differs", "recovers 0x099c…"),
        (360, OCHRE, OCHRE_PALE, "2nd token, chain 31337", "verifyingContract differs", "recovers 0x0eEA…"),
    ]
    for y, st, fi, name, why, rec in rows:
        line(260, 270, 340, y + 70)
        box(345, y, 440, 140, st, fi)
        text(370, y + 42, name, 26, anchor="start")
        text(370, y + 80, why, 24, anchor="start", cls="sub")
        text(370, y + 118, rec, 24, anchor="start", cls="mono")
    text(860, 118, "permit OK", 26)
    # One failure mark shared by the two other domains.
    p.append(f'<path d="M795,250 H812 V450 H795" fill="none" stroke="{SUB}" stroke-width="2"/>')
    box(822, 318, 120, 64, RED, RED_PALE, sw=2, rx=6)
    text(882, 360, "revert", 26)
    text(480, 525, "≠ owner: the same signature reads as someone else's", 24, cls="sub")
    p.append("</svg>")
    (HERE / "images" / "eip-712_replay.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


def erc1271_figure():
    """How a verifier branches between ecrecover and isValidSignature."""
    p, text, box, line = _canvas("署名者のアドレスにコードが無ければ ecrecover、あればアカウントの isValidSignature に問い合わせる")
    box(30, 200, 250, 140, SUB, GRAY_PALE)
    text(155, 255, "signer address", 26)
    text(155, 298, "has code?", 26)

    # Upper lane: EOA.
    line(280, 240, 330, 130)
    text(300, 160, "no", 24, anchor="end", cls="sub")
    box(340, 50, 590, 160, OCHRE, OCHRE_PALE)
    text(365, 92, "EOA", 26, anchor="start")
    text(365, 138, "ecrecover(digest, sig)", 26, anchor="start", cls="mono")
    text(365, 182, "== signer address ?", 26, anchor="start", cls="mono")

    # Lower lane: contract account.
    line(280, 300, 330, 410)
    text(300, 395, "yes", 24, anchor="end", cls="sub")
    box(340, 330, 590, 160, BLUE, BLUE_PALE)
    text(365, 372, "contract account (ERC-1271)", 26, anchor="start")
    text(365, 418, "signer.isValidSignature(digest, sig)", 24, anchor="start", cls="mono")
    text(365, 462, "== 0x1626ba7e ?", 26, anchor="start", cls="mono")

    text(635, 268, "ecrecover only: StudyAccount → false", 24, cls="sub")
    text(635, 306, "with the branch: StudyAccount → true", 24, cls="sub")
    p.append("</svg>")
    (HERE / "images" / "eip-712_erc1271.svg").write_text("\n".join(p) + "\n", encoding="utf-8")


if __name__ == "__main__":
    concept_figure()
    replay_figure()
    erc1271_figure()
