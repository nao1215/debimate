"""ログ漏洩のノートの図を作る。

実行: python3 figures.py  -> images/*.webp

SVG の文字列をここで組み、headless Chrome で 2 倍で描いて WebP にする（Pillow）。
images/ には WebP だけを残す。実験の値は lab/output.txt から読む。

- cover_figure(): シークレットがログへ混ざる層と、層ごとの事故。
- filter_figure(): キーの名前で消すフィルターを、文字列にまとめた値が素通りする（lab の filter）。
- stack_figure(): 値で渡した配列が、どの出力に出るか（lab の stack・panic・otel）。
- pattern_figure(): 後段のパターンでの消去は、秘密鍵と取引のハッシュを区別できない。
"""

import base64
import re
import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output.txt"
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
RED, RED_PALE, GREEN, GREEN_PALE = "#c43c3c", "#fbe3e3", "#3f7f4d", "#e3f1e6"
YELLOW_PALE = "#fff1c2"
LINE = "#9a9a9a"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono',monospace"


def render_svg(svg_text, w, h, name):
    """SVG の文字列 -> PNG（headless Chrome、2 倍）-> images/<name>（WebP）。"""
    work = HERE.parents[3] / ".note-review" / "work"   # /tmp が RAM の環境向け。無ければ既定の場所
    with tempfile.TemporaryDirectory(dir=work if work.exists() else None) as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        (HERE / "images").mkdir(exist_ok=True)
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
                  f'<style>text{{font-family:{FONT};fill:{INK}}} .m{{font-family:{MONO}}}</style>',
                  '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
                  f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
                  f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

    def box(self, x, y, bw, bh, fill, stroke=SUB, rx=6, width=1.2, dash=False):
        d = ' stroke-dasharray="6 4"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{width}"{d}/>')

    def text(self, x, y, s, size=15, color=INK, anchor="middle", mono=False):
        cls = ' class="m"' if mono else ""
        self.p.append(f'<text{cls} x="{x}" y="{y}" font-size="{size}" fill="{color}" '
                      f'text-anchor="{anchor}" style="fill:{color}" xml:space="preserve">{escape(s)}</text>')

    def spans(self, x, y, parts, size=15, anchor="start", mono=True):
        """parts: [(文字列, 文字色, 背景色 or None)]。等幅で横に並べ、背景色のある所に下地を敷く。"""
        cw = size * 0.602  # DejaVu Sans Mono の文字幅
        total = sum(len(s) for s, _, _ in parts) * cw
        x0 = x - total / 2 if anchor == "middle" else x
        cx = x0
        for s, color, bg in parts:
            if bg:
                self.p.append(f'<rect x="{cx - 1}" y="{y - size * 0.95}" width="{len(s) * cw + 2}" '
                              f'height="{size * 1.3}" rx="3" fill="{bg}"/>')
            cx += len(s) * cw
        cx = x0
        for s, color, _ in parts:
            self.text(cx, y, s, size=size, color=color, anchor="start", mono=mono)
            cx += len(s) * cw
        return total

    def line(self, x1, y1, x2, y2, color=LINE, width=1.5, arrow=True, dash=False):
        m = ' marker-end="url(#a)"' if arrow else ""
        d = ' stroke-dasharray="5 4"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                      f'stroke-width="{width}"{m}{d}/>')

    def image(self, x, y, w, h, path):
        data = base64.b64encode(path.read_bytes()).decode()
        self.p.append(f'<image x="{x}" y="{y}" width="{w}" height="{h}" href="data:image/png;base64,{data}"/>')

    def done(self):
        return "\n".join(self.p + ["</svg>"])



def text_width(t, size):
    """全角は size、半角は 0.56×size で幅を見積もる。"""
    return sum(size if ord(c) > 0x2000 else size * 0.56 for c in t)


def lab_line(prefix, after=None):
    """lab/output.txt から prefix で始まる最初の行を返す（図の文字を実験の出力と揃える）。
    after を渡すと、その行より後ろだけを探す（GOTRACEBACK=none の実行の出力を拾うため）。"""
    text = OUT.read_text()
    if after:
        text = text.split(after, 1)[1]
    for line in text.splitlines():
        if line.lstrip().startswith(prefix):
            return line.strip()
    raise SystemExit(f"lab/output.txt に {prefix!r} が無い")


LAYERS = [
    ("1", "値を文字列にするコード", "シークレットを含む値をログへ書く", ["Twitter・GitHub（2018）", "Facebook（2019）"]),
    ("2", "入力を含むエラー文", "変換に失敗した入力を文に入れる", ["Vault CVE-2025-4166", "Kubernetes CVE-2020-8564"]),
    ("3", "エラー報告とトレースの SDK", "エラーを丸ごと外部へ送る", ["Slope の Sentry", "OTel の RecordError（実験）"]),
    ("4", "panic とスタックトレース", "引数・クラッシュダンプに残る", ["Go のスタック（実験）", "Storm-0558（未立証に訂正）"]),
    ("5", "集めて消すログ基盤", "消す処理の抜けと回帰", ["Vault CVE-2024-8365", "GitHub の npm ログ（2022）"]),
    ("6", "診断ファイルを渡す人の手", "サポートへ添付する", ["Okta の HAR（2023）", "Tangem（2024）"]),
]


def cover_figure():
    w, top, bh, gap = 1120, 70, 74, 10
    h = top + len(LAYERS) * (bh + gap) + 70
    s = Svg(w, h)
    s.text(w / 2, 36, "シークレットがログへ混ざる層と、層ごとの事故", size=22)
    # 左の矢印: シークレットがメモリから外へ
    s.box(24, top, 120, 44, RED_PALE, stroke=RED)
    s.text(84, top + 20, "どこか 1 つの層で", size=12, color=RED)
    s.text(84, top + 37, "シークレットが混ざる", size=12, color=RED)
    s.line(84, top + 46, 84, h - 64, color=RED, width=2.5)
    s.box(24, h - 60, 120, 44, RED_PALE, stroke=RED)
    s.text(84, h - 32, "社外・攻撃者", size=15, color=RED)
    for i, (no, name, what, cases) in enumerate(LAYERS):
        y = top + i * (bh + gap)
        s.box(170, y, 930, bh, PALE if i % 2 == 0 else FILL)
        s.text(200, y + bh / 2 + 7, no, size=20, color=SUB)
        s.text(228, y + 31, name, size=19, anchor="start")
        s.text(228, y + 56, what, size=14, color=SUB, anchor="start")
        cx = 520
        for c in cases:
            tw = text_width(c, 14) + 28
            s.box(cx, y + 20, tw, 34, "#ffffff", stroke=LINE, rx=17)
            s.text(cx + tw / 2, y + 42, c, size=14)
            cx += tw + 10
    render_svg(s.done(), w, h, "cover.webp")


def filter_figure():
    w, h = 1120, 400
    s = Svg(w, h)
    s.text(w / 2, 34, "キーの名前で消すフィルターは、文字列にまとめた値を見分けない", size=20)
    s.box(30, 150, 230, 96, FILL)
    s.text(145, 182, "ImportParams", size=16, mono=True)
    s.text(145, 208, "WalletName: main", size=13, mono=True, color=SUB)
    s.text(145, 230, "Mnemonic: CANARY-…", size=13, mono=True, color=RED)
    rows = [
        ('"mnemonic", p.Mnemonic', "キー mnemonic が一致", lab_line("level=INFO msg=import mnemonic="), False),
        ('"params", fmt.Sprint(p)', "キー params は対象外", lab_line('level=INFO msg=import params="{main'), True),
        ('"params", fmt.Sprintf("%+v", p)', "キー params は対象外", lab_line('level=INFO msg=import params="{Wallet'), True),
    ]
    for i, (call, judge, out, leak) in enumerate(rows):
        y = 78 + i * 104
        s.line(262, 198, 300, y + 40)
        s.box(302, y, 300, 80, "#ffffff")
        s.text(452, y + 32, "log.Info(\"import\",", size=13, mono=True, color=SUB)
        s.text(452, y + 56, call, size=13, mono=True)
        s.line(604, y + 40, 640, y + 40)
        s.box(642, y + 16, 170, 48, GREEN_PALE if not leak else YELLOW_PALE)
        s.text(727, y + 46, judge, size=14)
        s.line(814, y + 40, 846, y + 40)
        body = out.split("msg=import ", 1)[1]
        s.box(848, y + 10, 250, 60, RED_PALE if leak else GREEN_PALE, stroke=RED if leak else GREEN)
        s.text(973, y + 34, "残る" if leak else "消える", size=14, color=RED if leak else GREEN)
        s.text(973, y + 56, body if len(body) < 34 else body[:31] + "…", size=11, mono=True)
    s.text(727, 64, "ReplaceAttr の判定", size=13, color=SUB)
    s.text(973, 64, "出力されたログ（lab の実行結果）", size=13, color=SUB)
    render_svg(s.done(), w, h, "filter.webp")


def stack_figure():
    w, h = 1120, 470
    s = Svg(w, h)
    s.text(w / 2, 34, "値で渡した配列の中身は、どの出力に出るか", size=20)
    s.box(250, 56, 620, 46, FILL)
    s.text(560, 85, "秘密鍵に見立てた配列 {0xdeadbeefcafe0001, 0x1122…} を値で渡す", size=14)
    key = "0xdeadbeefcafe0001, 0x1122334455667788"
    rows = [
        ("panicSign で panic", "GOTRACEBACK 既定", lab_line("main.panicSign("), True),
        ("panicSign で panic", "GOTRACEBACK=none", "panic: sign failed", False),
        ("sign で debug.Stack()", "GOTRACEBACK=none", lab_line("main.sign(", after="GOTRACEBACK=none ./loglab stack"), True),
        ("record で RecordError", "WithStackTrace(true)", lab_line("main.record("), True),
    ]
    for i, (where, cond, out, leak) in enumerate(rows):
        y = 140 + i * 78
        s.line(560, 104, 560, 124, arrow=False)
        s.line(560, 124, 140, 124, arrow=False) if i == 0 else None
        s.line(560, 124, 980, 124, arrow=False) if i == 0 else None
        s.box(40, y, 220, 60, FILL)
        s.text(150, y + 26, where, size=15)
        s.text(150, y + 47, cond, size=12, color=SUB, mono=True)
        s.line(262, y + 30, 300, y + 30)
        s.box(302, y, 780, 60, RED_PALE if leak else GREEN_PALE, stroke=RED if leak else GREEN)
        line = out.split(" +0x")[0]
        if key in line:
            a, b = line.split(key, 1)
            parts = [(a, INK, None), (key, RED, "#ffffff"), (b, INK, None)]
        else:
            parts = [(line, INK, None)]
        s.spans(322, y + 36, parts, size=13)
    s.text(w / 2, h - 18, "関数は lab の別々の実行。赤い文字が渡した配列の中身。Go 1.26.4・OTel SDK v1.47.0", size=13, color=SUB)
    render_svg(s.done(), w, h, "stack.webp")


def pattern_figure():
    w, h = 1120, 360
    s = Svg(w, h)
    s.text(w / 2, 34, "後段の消去が見るのは文字列の形だけで、何の値かは分からない", size=20)
    key = "35ecbb73773827d96576852766a91cb8be32a4e7bcc90b8ca9874c40d6f0437b"
    txh = "57cc9103ff616805d300881f6b26c9c9b62d20ed7e62ec149c18f35ff0e38a3b"
    for i, (label, val, secret) in enumerate([("秘密鍵（説明用の偽の値）", key, True),
                                               ("取引のハッシュ（説明用の偽の値）", txh, False)]):
        y = 70 + i * 90
        s.text(40, y + 22, label, size=15, anchor="start", color=RED if secret else INK)
        s.box(40, y + 34, 700, 36, RED_PALE if secret else FILL, stroke=RED if secret else LINE)
        s.text(390, y + 58, val, size=13, mono=True)
    s.line(745, 140, 790, 140)
    s.box(792, 96, 300, 88, YELLOW_PALE)
    s.text(942, 126, "正規表現 [0-9a-f]{64}", size=15, mono=True)
    s.text(942, 152, "両方を消すか、両方を残す", size=15)
    s.text(942, 172, "（形が同じなので分けられない）", size=12, color=SUB)
    s.box(40, 262, 1052, 66, GREEN_PALE, stroke=GREEN)
    s.text(566, 290, "どの値がシークレットかを知っているのは、値を作って受け取るアプリのコード", size=16)
    s.text(566, 314, "後段の消去は、アプリの手前で減らした後の最後の網として置く", size=14, color=SUB)
    render_svg(s.done(), w, h, "pattern.webp")


if __name__ == "__main__":
    cover_figure()
    filter_figure()
    stack_figure()
    pattern_figure()
