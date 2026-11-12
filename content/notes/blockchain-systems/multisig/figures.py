"""Generate the figures of the Multisig note.

Each figure is built as SVG here, rendered by headless Chrome at 2x and saved
as WebP (Pillow). images/ keeps only the WebP files.

1. multisig_concept.webp: three columns answer two questions for the same
   3-key setup: where the m-of-n rule is checked, and how many signatures the
   chain sees.
   - Bitcoin P2WSH: Script checks 2 of 3; the witness carries 2 signatures and 3 keys.
   - Ethereum Safe: a contract checks threshold 2; calldata carries 2 signatures.
   - MuSig2 / MPC: the signers cooperate off-chain; the chain sees 1 key and 1 signature.
2. multisig_order.webp: OP_CHECKMULTISIG matches from the end and never goes back.
3. multisig_stack.webp: the stack just before OP_CHECKMULTISIG runs, and the
   order in which it pops the 8 items (the 8th is the extra dummy).
4. multisig_taproot.webp: a Taproot output is one key plus hidden backup
   scripts; MuSig2 signs the key path, a 2-of-3 tapscript is the script path.
5. multisig_p2wsh.webp: what the P2WSH output stores and what the spender puts
   in the witness. The byte sizes come from lab/output/bitcoin.txt.

Run: python3 content/notes/blockchain-systems/multisig/figures.py
(needs google-chrome and Pillow)
"""

from html import escape
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_F = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_F = "#d4a24c", "#f8eed8"
GRAY_F = "#f2f2f2"


class Svg:
    def __init__(self, width, height, title):
        self.size = (width, height)
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
        """Render the SVG with headless Chrome at 2x and save it as WebP."""
        path.parent.mkdir(exist_ok=True)
        w, h = self.size
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={w},{h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(path, "WEBP", quality=90, method=6)


def column(s, cx, title, rule, rule_sub, fill, stroke, sigs, keys, chain_label, dash="", key_word="鍵"):
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
    s.text(cx, 506, f"署名 {sigs} 個・{key_word} {keys} 個", size=24)


def concept_figure():
    s = Svg(960, 540, "m-of-n の規則を検査する場所と、チェーンに残るもの")
    column(s, 162, "Bitcoin P2WSH", "スクリプト", "2-of-3 を検査", BLUE_F, BLUE, 2, 3, "チェーンに残るもの")
    column(s, 480, "Ethereum Safe", "コントラクト", "必要数 2 を検査", OCHRE_F, OCHRE, 2, 3, "チェーンに残るもの", key_word="アドレス")
    column(s, 798, "しきい値署名（MPC）", "オフチェーン", "署名者が協力", "#ffffff", SUB, 1, 1, "チェーンに残るもの", dash="8 6")
    s.save(HERE / "images" / "multisig_concept.webp")


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
    # The last pushed signature (right) is matched first; keys are tried from C down to A.
    # Like Bitcoin Core, stop as soon as fewer keys than signatures remain.
    keys = ["C", "B", "A"]
    i = step = 0
    for j in (1, 0):
        x, name = sx[j], sigs[j]
        failed = False
        while keys[i] != name:
            s.line(x, 326, kx[keys[i]], 208, SUB, 2.5, arrow=False)
            s.parts[-1] = s.parts[-1].replace("/>", ' stroke-dasharray="6 6"/>')
            step += 1
            s.circle((x + kx[keys[i]]) / 2, 262, 15, "#ffffff", SUB)
            s.text((x + kx[keys[i]]) / 2, 270, str(step), 20)
            i += 1
            if 3 - i < j + 1:  # remaining keys < remaining signatures
                failed = True
                break
        if failed:
            s.line(x - 16, 408, x + 16, 440, RED, 5, arrow=False)
            s.line(x + 16, 408, x - 16, 440, RED, 5, arrow=False)
            s.text(cx, 474, "残る鍵 1 個に署名 2 個で足りず、失敗", 24, SUB)
            break
        s.line(x, 326, kx[keys[i]], 210, INK, 3.5)
        step += 1
        s.circle((x + kx[keys[i]]) / 2, 262, 15, "#ffffff", INK)
        s.text((x + kx[keys[i]]) / 2, 270, str(step), 20)
        i += 1
    s.text(cx, 474 if ok else 520, "最後まで一致して通る" if ok else "", 24, SUB)


def order_figure():
    s = Svg(960, 540, "OP_CHECKMULTISIG は末尾から照らし合わせ、飛ばした公開鍵には戻らない")
    s.line(480, 40, 480, 500, "#d9d9d9", 2, arrow=False)
    order_panel(s, 240, "公開鍵と同じ順", "A, B の順に積む", ["A", "B"], True)
    order_panel(s, 720, "逆の順", "B, A の順に積む", ["B", "A"], False)
    s.text(480, 528, "数字は照らし合わせる順。実線は一致、点線は一致せずに飛ばした公開鍵", 24, SUB)
    s.save(HERE / "images" / "multisig_order.webp")


def p2wsh_figure():
    """Output keeps only the hash; the witness brings the signatures and the script itself."""
    s = Svg(960, 470, "P2WSH の出力はハッシュ値だけを持ち、使う時の witness が署名と条件の本体を出す")
    # Output (top).
    s.text(40, 52, "出力（scriptPubKey）", 26, anchor="start")
    s.box(40, 72, 880, 70, GRAY_F, SUB, sw=2)
    s.text(70, 117, "0", 26, anchor="start")
    s.box(120, 84, 780, 46, "#ffffff", SUB, sw=2, rx=6)
    s.text(510, 116, "条件の本体の SHA-256（32 バイト）", 24)
    # Witness (bottom). Widths follow the byte sizes 0 / 71 / 71 / 105, with a minimum for the dummy.
    s.text(40, 252, "使う時の witness", 26, anchor="start")
    items = [("空", "ダミー", 0, "#ffffff", SUB), ("署名 A", "71 バイト", 71, OCHRE_F, OCHRE),
             ("署名 B", "71 バイト", 71, OCHRE_F, OCHRE), ("条件の本体", "witnessScript 105 バイト", 105, BLUE_F, BLUE)]
    x, unit = 40, 2.6
    boxes = []
    for label, sub, n, fill, stroke in items:
        w = max(110, n * unit)
        s.box(x, 272, w, 96, fill, stroke)
        s.text(x + w / 2, 312, label, 26)
        s.text(x + w / 2, 348, sub, 22, color=SUB)
        boxes.append((x, w))
        x += w + 12
    bx, bw = boxes[-1]
    cx = bx + bw / 2
    s.line(cx, 268, cx, 186, arrow=False)
    s.text(cx + 14, 222, "SHA-256 が一致するか", 22, color=SUB, anchor="start")
    s.line(cx, 186, cx, 146, arrow=True)
    s.text(40, 420, "一致したら、条件の本体（2 <公開鍵A> <公開鍵B> <公開鍵C> 3 OP_CHECKMULTISIG）を", 22, color=SUB, anchor="start")
    s.text(40, 452, "左の 3 個を積んだ状態で実行する", 22, color=SUB, anchor="start")
    s.save(HERE / "images" / "multisig_p2wsh.webp")


def stack_figure():
    """Left: who pushes what. Right: the stack, top first, with the pop order."""
    s = Svg(960, 590, "OP_CHECKMULTISIG の直前のスタックと、取り出す順")
    s.text(225, 44, "積む順", 28)
    s.box(30, 70, 390, 110, OCHRE_F, OCHRE)
    s.text(225, 110, "1. 使う側が積む", 26)
    s.text(225, 152, "空（ダミー）→ 署名 A → 署名 B", 24, color=SUB)
    s.box(30, 210, 390, 110, BLUE_F, BLUE)
    s.text(225, 250, "2. 条件の 1 行が積む", 26)
    s.text(225, 292, "2 → 鍵 A → 鍵 B → 鍵 C → 3", 24, color=SUB)
    s.text(225, 380, "後から積んだものが上に来て、", 22, color=SUB)
    s.text(225, 412, "上から順に取り出される", 22, color=SUB)
    s.text(660, 44, "スタック（上が先に取り出される）", 26)
    rows = [("3", "公開鍵の数 n", BLUE_F, BLUE), ("鍵 C", "公開鍵", BLUE_F, BLUE), ("鍵 B", "公開鍵", BLUE_F, BLUE),
            ("鍵 A", "公開鍵", BLUE_F, BLUE), ("2", "署名の数 m", BLUE_F, BLUE),
            ("署名 B", "署名", OCHRE_F, OCHRE), ("署名 A", "署名", OCHRE_F, OCHRE),
            ("空", "ダミー（余分な 1 個）", "#ffffff", SUB)]
    for i, (v, sub, fill, stroke) in enumerate(rows):
        y = 70 + i * 62
        s.text(500, y + 38, str(i + 1), 24, color=SUB)
        s.box(530, y, 150, 52, fill, stroke, sw=2, dash="6 5" if v == "空" else "")
        s.text(605, y + 35, v, 24)
    # Brackets: the chunks OP_CHECKMULTISIG pops, in order.
    for (top, bottom, label) in ((0, 0, "公開鍵の数 n"), (1, 3, "公開鍵 n 個"), (4, 4, "署名の数 m"), (5, 6, "署名 m 個"), (7, 7, "余分な 1 個")):
        y1, y2 = 74 + top * 62, 70 + bottom * 62 + 48
        s.parts.append(f'<path d="M700 {y1} h12 V{y2} h-12" fill="none" stroke="{SUB}" stroke-width="2"/>')
        s.text(726, (y1 + y2) / 2 + 8, label, 22, color=SUB, anchor="start")
    s.save(HERE / "images" / "multisig_stack.webp")


def taproot_figure():
    """One output, two ways to spend it."""
    s = Svg(960, 490, "Taproot の出力は 1 個の鍵に予備の条件を隠して持つ")
    s.box(300, 30, 360, 120, GRAY_F, SUB, sw=2)
    s.text(480, 72, "Taproot の出力", 28)
    s.text(480, 112, "32 バイトの鍵 1 個だけが見える", 22, color=SUB)
    s.line(400, 152, 240, 222)
    s.line(560, 152, 715, 222)
    s.box(30, 230, 420, 150, OCHRE_F, OCHRE)
    s.text(240, 272, "鍵で使う（key path）", 26)
    s.text(240, 314, "A・B・C から作る集約鍵への署名 1 個", 21, color=SUB)
    s.text(240, 350, "全員が揃う時（MuSig2）", 22, color=SUB)
    s.box(500, 230, 430, 150, BLUE_F, BLUE, dash="8 6")
    s.text(715, 272, "予備の条件で使う（script path）", 24)
    s.text(715, 314, "tapscript・control block・署名 2 個", 21, color=SUB)
    s.text(715, 350, "揃わない時。使った時だけ条件が出る", 21, color=SUB)
    s.text(480, 430, "どちらで使うかは使う時に選ぶ。", 22, color=SUB)
    s.text(480, 460, "予備の条件は出力の鍵に埋め込まれ、普段は見えない", 22, color=SUB)
    s.save(HERE / "images" / "multisig_taproot.webp")


if __name__ == "__main__":
    stack_figure()
    taproot_figure()
    concept_figure()
    order_figure()
    p2wsh_figure()
