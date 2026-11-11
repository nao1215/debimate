"""PBS ノートの図を生成する（標準ライブラリで SVG を手書きし、Chrome の headless で WebP にする）。

python3 figures.py  ->  images/pbs_concept.webp   （4 つの役割と、それぞれが見るもの・渡すもの）
                        images/pbs_signed.webp    （proposer が署名するブロックの入れ子と、relay が中身を探した block_hash）
                        images/pbs_incident.webp  （2023 年 4 月の relay の事故と修正の前後）
                        images/pbs_epbs.webp      （プロトコルに組み込んだ PBS で、ブロックが 2 つに分かれる様子）

SVG を組み立て、Chrome の headless で 2 倍の解像度に描いてから WebP にする。images/ には WebP だけを置く。

再生成:
    uv run --with pillow python content/notes/blockchain-systems/pbs/figures.py
"""

import pathlib
import subprocess
import tempfile
from html import escape

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FILL, LINE = "#f2f2f2", "#bbbbbb"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.w, self.h = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="5" markerHeight="5" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, rx=10, dash=False):
        d = ' stroke-dasharray="8 6"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def arrow(self, x1, y1, x2, y2, color=SUB, sw=3):
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" marker-end="url(#arrow)"/>')

    def save(self, name):
        svg_text = "\n".join(self.parts + ["</svg>"]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = pathlib.Path(tmp) / "fig.svg", pathlib.Path(tmp) / "fig.png"
            svg.write_text(svg_text, encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            (HERE / "images").mkdir(exist_ok=True)
            Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def rows(f, x, y, w, labels, hidden=False):
    """ブロックの中身（取引の並び）を細い行で描く。hidden なら灰色の点線で中身を伏せる。"""
    for i, label in enumerate(labels):
        yy = y + i * 40
        if hidden:
            f.box(x, yy, w, 32, FILL, LINE, sw=1.5, rx=4, dash=True)
            f.text(x + w / 2, yy + 23, "見えない", 18, SUB)
        else:
            f.box(x, yy, w, 32, "#ffffff", LINE, sw=1.5, rx=4)
            f.text(x + w / 2, yy + 23, label, 20)


def concept_figure():
    f = Svg(960, 540, "searcher・builder・relay・proposer が見るものと渡すもの")
    cols = [  # (中心 x, 名前, 役割, 線, 面)
        (115, "searcher", "機会を探す", BLUE, PALE),
        (355, "builder", "ブロックを組む", BLUE, PALE),
        (600, "relay", "検証して仲介", SUB, FILL),
        (840, "proposer", "署名して提案", OCHRE, OCHRE_PALE),
    ]
    for cx, name, role, stroke, fill in cols:
        f.box(cx - 105, 40, 210, 380, fill, stroke)
        f.text(cx, 82, name, 26)
        f.text(cx, 116, role, 20, SUB)
    # searcher: bundle だけ
    f.text(115, 160, "bundle", 20, SUB)
    rows(f, 45, 174, 140, ["B 買い", "A 利用者", "C 売り"])
    # builder と relay: ブロックの中身が見える
    for cx in (355, 600):
        f.text(cx, 160, "ブロックの中身", 20, SUB)
        rows(f, cx - 80, 174, 160, ["B 買い", "A 利用者", "C 売り", "他の取引", "proposer へ送金"])
    # proposer: ヘッダーだけ
    f.text(840, 160, "ヘッダーと入札額", 20, SUB)
    f.box(770, 174, 140, 32, "#ffffff", OCHRE, sw=2, rx=4)
    f.text(840, 196, "ヘッダー・入札額", 16)
    rows(f, 770, 214, 140, ["", "", "", "", ""], hidden=True)
    # 流れ（列の下に、左から右へ渡すもの）
    centers = [c[0] for c in cols]
    for (a, b), label in zip(zip(centers, centers[1:]), ["bundle", "ブロックと入札額", "ヘッダーと入札額"]):
        f.text((a + b) / 2, 452, label, 20, SUB)
        f.arrow(a + 30, 468, b - 30, 468)
    f.text(480, 522, "proposer は中身を見ずに署名し、署名を受けた relay が中身を公開する", 22)
    f.save("pbs_concept.webp")


def signed_figure():
    f = Svg(960, 490, "proposer が署名するブロックの入れ子と、relay が中身を探した block_hash")
    # 外側: proposer が署名する合意側のブロック
    f.text(40, 44, "proposer が署名する合意側のブロック（beacon block）", 20, anchor="start")
    f.box(40, 60, 560, 360, FILL, SUB)
    f.text(70, 100, "slot・proposer の番号", 20, anchor="start")
    for i, (name, note) in enumerate([("parent_root", "直前のブロックを指す値"), ("state_root", "合意側の状態のハッシュ値")]):
        y = 120 + i * 52
        f.box(66, y, 508, 42, "#ffffff", LINE, sw=1.5, rx=6)
        f.text(84, y + 28, name, 20, anchor="start")
        f.text(250, y + 28, note, 20, SUB, anchor="start")
    # 内側: 実行内容を指すヘッダー
    f.box(66, 262, 508, 108, PALE, BLUE, sw=2, rx=6)
    f.text(84, 292, "execution payload header（中身を指すヘッダー）", 20, anchor="start")
    f.box(84, 308, 300, 44, "#ffffff", BLUE, sw=2, rx=4)
    f.text(100, 337, "block_hash", 20, anchor="start")
    f.text(234, 337, "中身のハッシュ値", 18, SUB, anchor="start")
    f.text(574, 404, "block_hash は事故でもそのまま", 18, SUB, anchor="end")
    # 右: 中身
    f.text(780, 30, "relay が持つ中身", 20)
    f.text(780, 54, "（execution payload）", 18, SUB)
    f.box(660, 66, 240, 354, PALE, BLUE)
    for i, label in enumerate(["bot の買い", "囮の交換", "bot の売り", "他の取引", "proposer へ送金"]):
        f.box(690, 96 + i * 62, 180, 40, "#ffffff", LINE, sw=1.5, rx=4)
        f.text(780, 96 + i * 62 + 27, label, 20)
    f.arrow(388, 330, 652, 330)
    f.text(630, 318, "指す", 18, SUB)
    f.text(480, 466, "relay は block_hash で自分の中身を探し、署名されたブロックが有効かは確かめなかった", 21)
    f.save("pbs_signed.webp")


def incident_figure():
    f = Svg(960, 440, "2023 年 4 月の relay の事故と、修正の前後")
    xs, w, h = [20, 256, 492, 728], 212, 110
    rows_ = [
        ("修正前", 70, [("block_hash で", "自分のブロックと判断"), ("中身を返した後に", "別の処理で公開"),
                        ("公開は拒否されたが", "中身は渡った"), ("中身を得た攻撃者の", "ブロックが通る")],
         (OCHRE_PALE, OCHRE), {1, 3}),
        ("修正後", 260, [("block_hash で", "自分のブロックと判断"), ("先に公開を試み", "beacon node が拒否"),
                        ("公開に失敗したら", "中身を返さない"), ("中身を知らないので", "差し替えられない")],
         (PALE, BLUE), {2, 3}),
    ]
    for title, y, labels, (fill, stroke), marked in rows_:
        f.text(20, y - 18, title, 24, anchor="start")
        for k, (x, (l1, l2)) in enumerate(zip(xs, labels)):
            bf, bs = (fill, stroke) if k in marked else (FILL, LINE)
            f.box(x, y, w, h, bf, bs)
            f.text(x + w / 2, y + 45, l1, 21)
            f.text(x + w / 2, y + 78, l2, 21)
            if k < 3:
                f.arrow(x + w + 3, y + h / 2, xs[k + 1] - 5, y + h / 2)
    f.text(480, 420, "あわせて、relay の beacon node も、検証してから配る必要があった", 20, SUB)
    f.save("pbs_incident.webp")


def epbs_figure():
    f = Svg(960, 420, "プロトコルに組み込んだ PBS で、ブロックが 2 つに分かれる様子")
    # proposer のブロック
    f.text(240, 44, "1. proposer が署名するブロック", 24)
    f.box(40, 66, 400, 230, OCHRE_PALE, OCHRE)
    f.box(70, 96, 340, 110, "#ffffff", LINE, sw=1.5, rx=6)
    f.text(240, 136, "builder の入札", 22)
    f.text(240, 172, "支払いの約束 ＋ 中身のハッシュ値", 20, SUB)
    f.text(240, 256, "proposer の署名", 22)
    # builder の中身
    f.text(720, 44, "2. builder が後で公開する中身", 24)
    f.box(520, 66, 400, 230, PALE, BLUE)
    for i, label in enumerate(["B 買い", "A 利用者", "C 売り", "他の取引"]):
        f.box(600, 90 + i * 48, 240, 38, "#ffffff", LINE, sw=1.5, rx=4)
        f.text(720, 90 + i * 48 + 27, label, 20)
    f.arrow(444, 181, 512, 181)
    f.text(478, 166, "後で", 20, SUB)
    f.text(480, 350, "支払いはプロトコルが builder の預けた残高から行い、", 22, SUB)
    f.text(480, 388, "中身が期限までに公開されたかは、一部のバリデータが投票で確かめる", 22, SUB)
    f.save("pbs_epbs.webp")


if __name__ == "__main__":
    concept_figure()
    signed_figure()
    incident_figure()
    epbs_figure()
