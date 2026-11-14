"""Snapshot Testing のノートの図を作る。

実行: python3 figures.py  -> images/*.webp

SVG の文字列をここで組み、headless Chrome で 2 倍で描いて WebP にする（Pillow）。
images/ には WebP だけを残す。中身は lab/output/ から読むので、実験を回し直したらこの script も回し直す。

- cover_figure(): 表紙。markdown v0.13.0 と v1.0.0 が書いた golden の中身と、それを mermaid で
  描いた結果（lab/output/flowchart.txt、deploy-*.png）。
- mask_figure(): ホームのディレクトリをマスクする処理が、atago v0.4.2 と v0.26.1 で同じ出力を
  どう書き換えるか（lab/output/atago.txt）。
- order_figure(): atago v0.4.2 の正規化の順番で、秘密とCRが golden まで残る流れ（lab/output/atago.txt）。
"""

import base64
import re
import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
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


def goldens():
    """lab/output/flowchart.txt から、版ごとの golden の中身と go test の結果を読む。"""
    text = (OUT / "flowchart.txt").read_text()
    result = {}
    for block in re.split(r"^== markdown ", text, flags=re.M)[1:]:
        version = block.split("\n", 1)[0].strip()
        golden = block.split("-- golden after UPDATE_GOLDEN=1\n", 1)[1].split("\n-- go test -count=3", 1)[0]
        lines = [line[4:] for line in golden.rstrip("\n").split("\n")]
        test = block.split("-- go test -count=3\n", 1)[1].split("\n", 1)[0].strip()
        texts = re.findall(r'^\s{8}"(.*)",?$', block, flags=re.M)
        result[version] = {"golden": lines, "test": test, "texts": texts}
    return result


def cover_figure():
    g = goldens()
    old, new = g["v0.13.0"], g["v1.0.0"]
    assert old["test"].startswith("ok") and new["test"].startswith("ok"), (old["test"], new["test"])
    assert "Deploy v1.0" in old["texts"] and "run make release" in old["texts"], old["texts"]
    assert "Deploy v1.0 #prod" in new["texts"], new["texts"]

    w, h = 860, 500
    s = Svg(w, h)
    cols = [(20, "markdown v0.13.0", old, "deploy-v0.13.0.png", False),
            (440, "markdown v1.0.0", new, "deploy-v1.0.0.png", True)]
    for x, label, data, png, good in cols:
        s.text(x + 200, 30, label, size=18)
        sub = "更新した golden で 3 回とも通る" if good else "golden テスト: 3 回とも通る"
        s.text(x + 200, 52, sub, size=13, color=SUB)
        # golden の中身
        s.box(x, 66, 400, 168, FILL, stroke=LINE)
        s.text(x + 12, 86, "testdata/deploy.mmd", size=12, color=SUB, anchor="start")
        for i, line in enumerate(data["golden"]):
            parts = []
            mark = None
            if not good:
                if "#prod" in line:
                    mark = "#prod"
                elif '"make release"' in line:
                    mark = '"make release"'
            else:
                if "#prod" in line:
                    mark = '"Deploy v1.0 #prod"'
                elif "#quot;" in line:
                    mark = "#quot;make release#quot;"
            if mark and mark in line:
                a, b = line.split(mark, 1)
                parts = [(a, INK, None), (mark, RED if not good else GREEN, RED_PALE if not good else GREEN_PALE),
                         (b, INK, None)]
            else:
                parts = [(line, INK, None)]
            s.spans(x + 14, 110 + i * 18, parts, size=13)
        s.line(x + 200, 238, x + 200, 262)
        s.text(x + 212, 256, "mermaid で描く", size=12, color=SUB, anchor="start")
        img = Image.open(OUT / png)
        iw, ih = img.size[0] / 2 * 0.8, img.size[1] / 2 * 0.8
        s.box(x + 200 - iw / 2 - 6, 268, iw + 12, ih + 10, "#ffffff", stroke=LINE)
        s.image(x + 200 - iw / 2, 273, iw, ih, OUT / png)
        msg = "書いた通りに描かれる" if good else "引用符と #prod が消えて描かれる"
        s.text(x + 200, 268 + ih + 34, msg, size=15, color=GREEN if good else RED)
    render_svg(s.done(), w, h, "cover.webp")


def atago_results():
    """lab/output/atago.txt を、(版, spec) -> {golden: [行], verify: 文} にする。"""
    text = (OUT / "atago.txt").read_text()
    result = {}
    for block in re.split(r"^== atago ", text, flags=re.M)[1:]:
        head = block.split("\n", 1)[0]
        version, spec = head.split()[0], head.split()[1]
        body = block.split("  golden:\n", 1)[1]
        golden = []
        for line in body.split("\n"):
            if not line.startswith("    "):
                break
            golden.append(line[4:])
        verify = re.findall(r"^  verify.*?: (\w+)", block, flags=re.M)
        result[(version, spec)] = {"golden": golden, "verify": verify}
    return result


def mask_figure():
    r = atago_results()
    assert r[("v0.4.2", "home.atago.yaml")]["golden"][2] == "~ki/data$"
    assert r[("v0.26.1", "home.atago.yaml")]["golden"][2] == "/home/naoki/data$"
    assert r[("v0.4.2", "root.atago.yaml")]["golden"][0] == "installed: ~usr~local~bin~app$"
    assert r[("v0.26.1", "root.atago.yaml")]["golden"][0] == "installed: /usr/local/bin/app$"

    w, h = 860, 330
    s = Svg(w, h)
    s.text(150, 30, "プログラムの出力", size=15, color=SUB)
    s.text(500, 30, "v0.4.2 が書いた golden", size=15, color=SUB)
    s.text(740, 30, "v0.26.1 が書いた golden", size=15, color=SUB)

    def row(y, title, out_parts, old, new, note_old, note_new):
        s.text(20, y - 34, title, size=15, anchor="start")
        s.box(20, y - 24, 260, 40, FILL, stroke=LINE)
        s.spans(150, y + 2, out_parts, size=15, anchor="middle")
        s.line(286, y - 4, 384, y - 4)
        s.box(390, y - 24, 220, 40, RED_PALE, stroke=RED)
        s.spans(500, y + 2, [(old, RED, None)], size=15, anchor="middle")
        s.text(500, y + 40, note_old, size=13, color=RED)
        s.box(630, y - 24, 220, 40, GREEN_PALE, stroke=GREEN)
        s.spans(740, y + 2, [(new, GREEN, None)], size=15, anchor="middle")
        s.text(740, y + 40, note_new, size=13, color=GREEN)

    hl = YELLOW_PALE
    row(110, "ホームが /home/nao の時",
        [("/home/nao", INK, hl), ("ki/data", INK, None)],
        "~ki/data", "/home/naoki/data",
        "文字列として一致した所を ~ に", "次の文字 k はパスの区切りではない")
    root_parts = []
    for part in re.split(r"(/)", "/usr/local/bin/app"):
        if part:
            root_parts.append((part, INK, hl if part == "/" else None))
    row(250, "ホームが / の時（コンテナでよくある）",
        root_parts, "~usr~local~bin~app", "/usr/local/bin/app",
        "全ての / が ~ になる", "ホームが / ならマスクしない")
    s.text(20, 318, "黄色: ホームのディレクトリと文字列として一致した所", size=13, color=SUB, anchor="start")
    render_svg(s.done(), w, h, "mask.webp")


def order_figure():
    r = atago_results()
    assert r[("v0.4.2", "secret.atago.yaml")]["golden"] == ["token: s3cr3t-token$"]
    assert r[("v0.4.2", "secret.atago.yaml")]["verify"] == ["PASSED"]
    assert r[("v0.4.2", "crlf.atago.yaml")]["golden"][0] == "progress 50%\\r$"
    assert r[("v0.4.2", "crlf.atago.yaml")]["verify"] == ["FAILED"]

    w, h = 860, 380
    s = Svg(w, h)
    xs = [95, 290, 485, 700]
    heads = ["出力", "1. 秘密をマスクする", "2. CRLF を LF に\n（1 回だけ）", "3. エスケープを消す\n→ golden に書く"]
    for x, head in zip(xs, heads):
        for i, line in enumerate(head.split("\n")):
            s.text(x, 30 + i * 19, line, size=15, color=INK if i == 0 else SUB)

    def cell(x, y, parts, kind=None, width=170):
        fill, stroke = {None: (FILL, LINE), "bad": (RED_PALE, RED), "good": (GREEN_PALE, GREEN)}[kind]
        s.box(x - width / 2, y - 22, width, 36, fill, stroke=stroke)
        s.spans(x, y + 2, parts, size=14, anchor="middle")

    # 秘密の行
    y = 124
    s.text(20, 86, "秘密 s3cr3t-token の途中に色を戻すエスケープ \\e[0m がある出力", size=14, anchor="start")
    esc = ("\\e[0m", "#8a5a00", YELLOW_PALE)
    cell(xs[0], y, [("s3cr3t-", INK, None), esc, ("token", INK, None)])
    cell(xs[1], y, [("s3cr3t-", INK, None), esc, ("token", INK, None)])
    cell(xs[2], y, [("s3cr3t-", INK, None), esc, ("token", INK, None)])
    cell(xs[3], y, [("s3cr3t-token", RED, None)], kind="bad")
    for a, b in zip(xs, xs[1:]):
        s.line(a + 88, y - 4, b - 88, y - 4)
    s.text(xs[1], y + 34, "s3cr3t-token と一致しない", size=12, color=SUB)
    s.text(xs[3], y + 34, "秘密がそのまま残る（テストは通る）", size=12, color=RED)

    # CR の行
    y = 254
    s.text(20, 206, "行末に CR が 2 つ続く出力（進捗の表示などで起きる）", size=14, anchor="start")
    cell(xs[0], y, [("50%\\r\\r\\n", INK, None)])
    cell(xs[1], y, [("50%\\r\\r\\n", INK, None)])
    cell(xs[2], y, [("50%\\r", INK, None), ("\\n", INK, None)])
    cell(xs[3], y, [("50%\\r\\n", RED, None)], kind="bad")
    for a, b in zip(xs, xs[1:]):
        s.line(a + 88, y - 4, b - 88, y - 4)
    s.text(xs[2], y + 34, "\\r\\n を \\n にしても \\r が 1 つ残る", size=12, color=SUB)
    s.text(xs[3], y + 34, "比べる時は golden 側をもう 1 回揃える", size=12, color=RED)
    s.text(xs[3], y + 52, "50%\\n ≠ 50%\\r\\n で、更新の直後に落ちる", size=12, color=RED)
    s.text(20, 360, "atago v0.4.2 の正規化を、ここに関わる 3 つの段階だけに絞って描いた", size=13, color=SUB,
           anchor="start")
    render_svg(s.done(), w, h, "order.webp")


if __name__ == "__main__":
    cover_figure()
    mask_figure()
    order_figure()
