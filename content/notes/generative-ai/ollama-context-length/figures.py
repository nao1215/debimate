"""Ollama の num_ctx のノートの図を作る。

実験のデータは KV キャッシュのノートの lab（../kv-cache/lab）にある。
- ollama-context-length_default.webp   : 既定の num_ctx が GPU のメモリで決まり、モデルの上限で頭打ちになる流れ
- ollama-context-length_breakdown.webp : q4_K_M の size を KV キャッシュとそれ以外に分ける
- ollama-context-length_truncate.webp  : num_ctx 2,048 で 3,084 トークンの入力を切り詰めた範囲
- ollama-context-length_slot.webp      : 枠が 1 組の時に別の要求が挟まると、共通の前置きだけが残る（cache.go の模式）

手書きの SVG を Chrome の headless で PNG にしてから WebP にする。images/ に SVG は残さない。

使い方:
    uv run --with pillow python figures.py
"""

import json
import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / "kv-cache" / "lab"
IMAGES = HERE / "images"

INK, SUB, ACCENT, OCHRE = "#1f1f1f", "#666666", "#7aa6c2", "#d4a24c"
PALE, OCHRE_PALE = "#eaf1f5", "#f8eed8"
FONT = "'Noto Sans CJK JP','Hiragino Sans','Yu Gothic',sans-serif"
# Qwen3-1.7B の 1 トークンあたりの K と V（f16）: 2 x 28 層 x KV ヘッド 8 x 128 x 2 バイト
PER_TOKEN = 2 * 28 * 8 * 128 * 2
# q4_K_M のファイルの大きさ（量子化のノートの ollama list の値）
Q4_FILE_GB = 1.36


class Svg:
    """手書きの SVG（文字は 24px 以上、太字なし、背景は白）。"""

    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        self.p.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
                      f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def rect(self, x, y, w, h, fill, stroke, sw=2, rx=4, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                      f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=SUB, sw=2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                      f'stroke="{color}" stroke-width="{sw}"{d}/>')

    def save(self, name):
        IMAGES.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.p + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)


def breakdown_figure():
    """q4_K_M を num_ctx 4,096 と未指定（40,960）で読み込んだ時の size を、KV キャッシュとそれ以外に分ける。"""
    rows = json.loads((LAB / "memory.json").read_text())
    q4 = sorted((r for r in rows if r["model"] == "qwen3:1.7b-q4_K_M" and r["ps"]),
                key=lambda r: (r["num_ctx"] is None, r["num_ctx"] or 0))
    s = Svg(960, 440, "q4_K_M の読み込み時の size を、KV キャッシュとそれ以外に分ける")
    x0, scale = 290, 95  # 1 GB あたりの px
    xf = x0 + Q4_FILE_GB * scale
    s.line(xf, 78, xf, 330, SUB, 2, "6 5")
    s.text(xf, 64, f"ファイル {Q4_FILE_GB:.2f} GB", 24, "middle", "sub")
    for i, r in enumerate(q4):
        y = 110 + i * 130
        ctx = r["ps"]["context_length"]
        total = r["ps"]["size"] / 1e9
        kv = PER_TOKEN * ctx / 1e9
        rest = total - kv
        label = f"num_ctx {ctx:,}" if r["num_ctx"] else "num_ctx 未指定"
        s.text(30, y + 44, label, 26, "start")
        if r["num_ctx"] is None:
            s.text(30, y + 80, f"（{ctx:,} で読み込み）", 24, "start", "sub")
        s.rect(x0, y, rest * scale, 70, PALE, ACCENT, 2.5)
        s.rect(x0 + rest * scale, y, kv * scale, 70, OCHRE_PALE, OCHRE, 2.5)
        s.text(x0 + rest * scale / 2, y + 44, f"{rest:.2f} GB", 24)
        if kv * scale > 200:
            s.text(x0 + rest * scale + kv * scale / 2, y + 44, f"KV キャッシュ {kv:.2f} GB", 24)
            s.text(x0 + total * scale, y + 104, f"計 {total:.2f} GB", 24, "end")
        else:
            s.text(x0 + total * scale + 14, y + 44, f"計 {total:.2f} GB（うち KV {kv:.2f}）",
                   24, "start")
    s.rect(290, 392, 28, 28, PALE, ACCENT, 2.5)
    s.text(328, 414, "重み・作業領域", 24, "start")
    s.rect(540, 392, 28, 28, OCHRE_PALE, OCHRE, 2.5)
    s.text(578, 414, "KV キャッシュ（num_ctx 個の枠）", 24, "start")
    s.save("ollama-context-length_breakdown.webp")


def truncate_figure():
    """3,084 トークンの入力を num_ctx 2,048 に収めた時に、残した部分と捨てた部分。

    数はサーバーのログ（truncating input prompt limit=2048 prompt=3084 keep=4 new=2048）から。
    """
    prompt, limit, keep = 3084, 2048, 4
    drop = prompt - limit
    s = Svg(960, 400, "num_ctx を超えた入力を、先頭の数トークンと後ろの部分だけ残して切り詰める")
    x0, width = 40, 880
    sc = width / prompt
    y = 150
    kw = max(keep * sc, 10)  # 4 トークンは細すぎるので見える幅にする
    s.rect(x0, y, kw, 70, PALE, ACCENT, 2.5, 2)
    s.rect(x0 + kw, y, drop * sc - kw + keep * sc, 70, "#ffffff", SUB, 2.5, 4, "7 5")
    s.rect(x0 + (keep + drop) * sc, y, (limit - keep) * sc, 70, PALE, ACCENT, 2.5)
    s.text(x0, 60, f"入力 {prompt:,} トークン、num_ctx {limit:,}", 26, "start")
    s.text(x0, y - 18, f"先頭 {keep}（keep={keep}）", 24, "start", "sub")
    s.text(x0 + (keep + drop / 2) * sc, y + 45, f"捨てる {drop:,}", 26)
    s.text(x0 + (keep + drop + (limit - keep) / 2) * sc, y + 45, f"残す {limit - keep:,}", 26)
    # 合言葉は先頭の文、質問は末尾
    s.line(x0 + 30, y + 70, x0 + 30, y + 110, INK, 2)
    s.text(x0 + 16, y + 140, "合言葉の文（捨てられる）", 24, "start")
    xe = x0 + width - 20
    s.line(xe, y + 70, xe, y + 110, INK, 2)
    s.text(xe + 14, y + 140, "最後の質問（残る）", 24, "end")
    s.text(480, 380, "モデルに届くのは計 2,048 トークン（new=2048）。エラーは返らない", 24, "middle", "sub")
    s.save("ollama-context-length_truncate.webp")


def default_figure():
    """GPU のメモリから既定の num_ctx が決まり、モデルの上限で頭打ちになる流れ（手元の 2 つのモデル）。"""
    s = Svg(960, 420, "既定の num_ctx は GPU のメモリで決まり、モデルの上限で頭打ちになる")
    s.rect(30, 40, 900, 64, "#ffffff", SUB, 2)
    s.text(480, 82, "GPU のメモリ 94.7 GiB（48 GiB 以上）→ 既定の num_ctx は 262,144", 26)
    x0, scale = 290, 600 / 262144
    rows = (("Qwen3-1.7B", 40960, "上限 40,960 で頭打ち", 2 * 28 * 8 * 128 * 2),
            ("Qwen3-4B", 262144, "上限 262,144 のまま", 2 * 36 * 8 * 128 * 2))
    s.text(x0, 150, "読み込んだ num_ctx（点線は既定の 262,144）", 22, "start", "sub")
    for i, (name, ctx, note, per) in enumerate(rows):
        y = 175 + i * 110
        s.text(30, y + 40, name, 26, "start")
        s.rect(x0, y, 262144 * scale, 56, "#ffffff", SUB, 1.5, 4, "6 5")
        s.rect(x0, y, ctx * scale, 56, OCHRE_PALE, OCHRE, 2.5)
        s.text(x0 + ctx * scale + 12 if ctx < 262144 else x0 + ctx * scale - 12, y + 37,
               f"{ctx:,}（{note}）", 24, "start" if ctx < 262144 else "end")
        gib = per * ctx / 2**30
        s.text(x0, y + 86, f"KV キャッシュ {gib:.1f} GiB", 22, "start", "sub")
    s.save("ollama-context-length_default.webp")


def slot_figure():
    """並列数 1（枠が 1 組）で、要求 A の間に要求 B が挟まった時に使い回せる範囲。

    Ollama 0.22.1 の runner/ollamarunner/cache.go は、枠に残ったトークン列と新しい入力を
    先頭から比べ、一致した数だけ使い回す。実測ではなく、コードの動きを描いた模式。
    """
    s = Svg(960, 470, "枠が 1 組の時に別の要求が挟まると、共通の前置きだけが残る")
    s.rect(300, 28, 28, 28, PALE, ACCENT, 2.5)
    s.text(338, 50, "枠から使い回す", 24, "start")
    s.rect(560, 28, 28, 28, OCHRE_PALE, OCHRE, 2.5)
    s.text(598, 50, "計算する", 24, "start")
    x0, unit = 300, 30
    # (表示名, [(区間の名前, 長さ, 使い回すか)])
    rows = (("1 要求 A", [("共通の前置き", 6, False), ("資料 A と質問", 14, False)]),
            ("2 要求 B", [("共通の前置き", 6, True), ("資料 B と質問", 14, False)]),
            ("3 要求 A をもう一度", [("共通の前置き", 6, True), ("資料 A と質問", 14, False)]))
    for i, (label, segs) in enumerate(rows):
        y = 100 + i * 90
        s.text(30, y + 33, label, 24, "start")
        x = x0
        for name, n, reused in segs:
            w = n * unit
            fill, stroke = (PALE, ACCENT) if reused else (OCHRE_PALE, OCHRE)
            s.rect(x, y, w, 48, fill, stroke, 2.5)
            s.text(x + w / 2, y + 33, name, 22)
            x += w
    s.text(480, 400, "3 の時、枠の組には 2 の要求 B が入っているので、資料 A の K・V は残っていない", 22, "middle", "sub")
    s.text(480, 440, "並列数 1。Ollama 0.22.1 の cache.go の動きを描いた模式（実測ではない）", 22, "middle", "sub")
    s.save("ollama-context-length_slot.webp")


if __name__ == "__main__":
    default_figure()
    breakdown_figure()
    truncate_figure()
    slot_figure()
