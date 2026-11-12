"""Finality ノートの図を生成する。

再生成:
    uv run --with matplotlib --with numpy --with pillow python content/notes/blockchain-systems/finality/figures.py

概念図は SVG を組み立て、google-chrome の headless で PNG にしてから WebP に変換する。
グラフは matplotlib で PNG にしてから WebP に変換する。images/ には WebP だけを置く。
"""

import io
import math
import pathlib
import subprocess
import tempfile
from html import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "images"
OUT.mkdir(exist_ok=True)

INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#59a14f", "#e3f0e0"
GRAY, GRAY_PALE = "#9a9a9a", "#f2f2f2"
RED, RED_PALE = "#e15759", "#fbe3e3"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def to_webp(png_bytes: bytes, name: str) -> None:
    Image.open(io.BytesIO(png_bytes)).convert("RGB").save(OUT / name, "WEBP", quality=90, method=6)
    print(f"wrote {OUT / name}")


class Svg:
    def __init__(self, title, w=960, h=540):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
            '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
            f'markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls="", fill=None):
        c = f' class="{cls}"' if cls else ""
        f = f' style="fill:{fill}"' if fill else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}{f}>{escape(s)}</text>')

    def box(self, x, y, bw, bh, stroke, fill, sw=2.5, rx=8, dash=False):
        d = ' stroke-dasharray="7 5"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, arrow=True, dash=False, color=SUB, sw=2):
        m = ' marker-end="url(#arr)"' if arrow else ""
        d = ' stroke-dasharray="6 5"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{m}{d}/>')

    def raw(self, s):
        self.p.append(s)

    def save(self, name):
        svg_text = "\n".join(self.p + ["</svg>"]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = pathlib.Path(tmp) / "fig.svg", pathlib.Path(tmp) / "fig.png"
            svg.write_text(svg_text, encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            to_webp(png.read_bytes(), name)


def attacker_success_probability(q: float, z: int) -> float:
    """Bitcoin ホワイトペーパー (Nakamoto 2008) の AttackerSuccessProbability を写したもの。

    受け取り側がトランザクションの後ろに z ブロック積むまで待った時点で、攻撃者がなお
    追い付く確率を返す。攻撃者の進捗は期待値 z*q/p の Poisson 分布と仮定する。
    """
    p = 1.0 - q
    lam = z * (q / p)
    total = 1.0
    for k in range(z + 1):
        poisson = math.exp(-lam)
        for i in range(1, k + 1):
            poisson *= lam / i
        total -= poisson * (1 - (q / p) ** (z - k))
    return total


# --- 図1: 後ろに積むブロック数 z と、攻撃の成功確率 ---
def success_rate_figure() -> None:
    plt.rcParams.update({
        "figure.figsize": (6, 4),
        "font.size": 11,
        "font.family": ["Noto Sans CJK JP", "DejaVu Sans"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linewidth": 0.5,
    })
    z_values = list(range(0, 26))
    for q, color in [(0.10, BLUE), (0.30, GREEN), (0.45, RED)]:
        probs = [attacker_success_probability(q, z) for z in z_values]
        plt.semilogy(z_values, probs, marker="o", markersize=3, color=color, label=f"q = {q:.2f}")
    plt.axhline(0.001, color=SUB, linestyle="--", linewidth=1)
    plt.text(0.3, 0.0013, "0.1%", color=SUB, fontsize=9)
    plt.xlabel("トランザクションの後ろに積まれたブロック数 z")
    plt.ylabel("攻撃の成功確率（追い付く確率）")
    plt.ylim(1e-8, 2)
    plt.legend(title="攻撃者のハッシュ\n計算能力の割合 q", loc="upper left", bbox_to_anchor=(1.02, 1))
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close()
    to_webp(buf.getvalue(), "finality_success_rate.webp")


# --- 図2: slot・epoch・checkpoint。空 slot の checkpoint は直前のブロックを指す ---
def checkpoint_figure() -> None:
    s = Svg("epoch の先頭 slot が checkpoint になる。先頭 slot が空なら、直前のブロックを指す", h=410)
    # 2 つの epoch を、先頭の 2 slot と末尾の 1 slot だけ描いて間を省略する。
    sw, gap, y = 80, 8, 120
    epochs = [
        (130, "epoch N", [True, False, None, True]),
        (530, "epoch N+1", [False, True, None, True]),
    ]
    for x0, label, slots in epochs:
        width = len(slots) * (sw + gap) - gap
        s.raw(f'<path d="M{x0},{y - 34} V{y - 48} H{x0 + width} V{y - 34}" fill="none" stroke="{SUB}" stroke-width="2"/>')
        s.text(x0 + width / 2, y - 60, f"{label}（32 slot・6 分 24 秒）", 24)
        s.text(x0 + sw / 2, y - 10, "先頭 slot", 18, cls="sub")
        for i, has_block in enumerate(slots):
            x = x0 + i * (sw + gap)
            if has_block is None:
                s.text(x + sw / 2, y + 44, "…", 30, cls="sub")
                continue
            if has_block:
                s.box(x, y, sw, 64, BLUE, BLUE_PALE)
                s.text(x + sw / 2, y + 40, "ブロック", 18)
            else:
                s.box(x, y, sw, 64, GRAY, "#ffffff", dash=True)
                s.text(x + sw / 2, y + 40, "空", 20, cls="sub")
    last_block_x = 130 + 3 * (sw + gap) + sw / 2

    def flag(x, label, sub):
        s.line(x, y + 150, x, y + 70, color=OCHRE, sw=3)
        s.box(x - 128, y + 154, 256, 74, OCHRE, OCHRE_PALE, sw=2)
        s.text(x, y + 186, label, 20)
        s.text(x, y + 214, sub, 18, cls="sub")

    flag(130 + sw / 2, "epoch N の checkpoint", "先頭 slot のブロック")
    flag(last_block_x, "epoch N+1 の checkpoint", "先頭が空なので直前を指す")
    # 空 slot から直前のブロックへの破線
    s.raw(f'<path d="M{530 + sw / 2},{y + 66} C{530 + sw / 2},{y + 120} {last_block_x + 60},{y + 120} '
          f'{last_block_x + 14},{y + 76}" fill="none" stroke="{SUB}" stroke-width="2" stroke-dasharray="6 5" '
          'marker-end="url(#arr)"/>')
    s.text(480, 392, "1 マス＝1 slot（12 秒）。投票の対象は epoch ごとに 1 つの checkpoint", 22, cls="sub")
    s.save("finality_checkpoint.webp")


# --- 図3: 起点からターゲットへの 2/3 の投票で、justified と finalized が進む ---
def votes_figure() -> None:
    s = Svg("justified な起点から直後の checkpoint へ 2/3 の投票が張られると、ターゲットが justified、起点が finalized になる", h=380)
    xs = [130, 360, 590, 820]
    names = ["最初のブロック", "epoch 1", "epoch 2", "epoch 3"]
    states = [
        ("finalized", "確定済み", GREEN, GREEN_PALE),
        ("finalized", "確定済み", GREEN, GREEN_PALE),
        ("justified", "正当化済み", BLUE, BLUE_PALE),
        ("投票待ち", "", GRAY, "#ffffff"),
    ]
    y = 130
    for x, name, (st, ja, stroke, fill) in zip(xs, names, states):
        s.box(x - 90, y, 180, 80, stroke, fill, dash=(st == "投票待ち"))
        s.text(x, y + 34, "checkpoint", 20, cls="sub")
        s.text(x, y + 64, name, 22)
        s.text(x, y + 130, st, 24)
        if ja:
            s.text(x, y + 160, f"（{ja}）", 20, cls="sub")
    for i, lab in enumerate(["2/3 の投票", "2/3 の投票", "集計中"]):
        xa, xb = xs[i] + 20, xs[i + 1] - 20
        mid = (xa + xb) / 2
        dash = ' stroke-dasharray="6 5"' if lab == "集計中" else ""
        s.raw(f'<path d="M{xa},{y - 4} Q{mid},{y - 110} {xb},{y - 6}" fill="none" stroke="{SUB}" '
              f'stroke-width="2.5"{dash} marker-end="url(#arr)"/>')
        s.text(mid, y - 66, lab, 22, cls="sub" if lab == "集計中" else "")
    s.text(480, 360, "矢印は起点 → ターゲット。直後への 2/3 が張られると、起点が finalized になる", 22, cls="sub")
    s.save("finality_votes.webp")


# --- 図4: 矛盾する 2 つの checkpoint への 2/3 は必ず 1/3 以上重なる ---
def overlap_figure() -> None:
    s = Svg("矛盾する 2 つの checkpoint に 2/3 ずつ投票が集まると、1/3 以上のバリデータが両方に投票している")
    x0, x1 = 120, 840  # 預け入れ全体の 0 と 1
    third = (x1 - x0) / 3
    s.text(480, 56, "バリデータが預けた ether の全体", 26, cls="sub")
    s.raw(f'<rect x="{x0}" y="76" width="{x1 - x0}" height="16" fill="{GRAY_PALE}" stroke="{SUB}" stroke-width="1.5"/>')
    for x in (x0 + third, x0 + 2 * third):
        s.line(x, 104, x, 330, arrow=False, dash=True)
    s.box(x0, 120, 2 * third, 70, BLUE, BLUE_PALE, rx=6)
    s.text(x0 + third, 165, "checkpoint A を確定させた 2/3 の投票", 24)
    s.box(x0 + third, 220, 2 * third, 70, OCHRE, OCHRE_PALE, rx=6)
    s.text(x0 + 2 * third, 265, "A と矛盾する B に至る列の 2/3 の投票", 24)
    s.raw(f'<path d="M{x0 + third},345 V360 H{x0 + 2 * third} V345" fill="none" stroke="{SUB}" stroke-width="2"/>')
    s.text(480, 400, "少なくとも 1/3 は両方に投票している", 26)
    s.box(480 - 190, 420, 380, 56, RED, RED_PALE, sw=2, rx=6)
    s.text(480, 458, "スラッシング（slashing）の対象", 24)
    for x, label in ((x0, "0"), (x0 + third, "1/3"), (x0 + 2 * third, "2/3"), (x1, "1")):
        s.text(x, 520, label, 24, cls="sub")
    s.save("finality_overlap.webp")


# --- 図5: 3 つのブロックタグが指す位置（順調な時の目安）---
def tags_figure() -> None:
    s = Svg("latest は先頭、finalized は 2 epoch 前の checkpoint、safe はその間のどこかを指す", h=360)
    y, bw, gap = 90, 42, 6
    x = 140
    starts = []
    for e in range(3):
        starts.append(x)
        for i in range(5 if e < 2 else 3):
            s.box(x, y, bw, 56, BLUE, BLUE_PALE, sw=2, rx=6)
            x += bw + gap
        if e < 2:
            s.text(x + 18, y + 38, "…", 26, cls="sub")
            x += 44
    head = x - gap - bw / 2
    for i, sx in enumerate(starts):
        s.line(sx - 4, y - 60, sx - 4, y + 90, arrow=False, dash=True)
        s.text(sx + 4, y - 30, ["epoch N-2", "epoch N-1", "epoch N（現在）"][i], 22, anchor="start")
    s.text(head + 40, y + 38, "→ 時間", 20, anchor="start", cls="sub")

    def mark(xm, tag, ja, stroke, fill, row):
        yy = y + 90 + row * 0
        s.line(xm, yy + 20, xm, y + 60, color=stroke, sw=3)
        s.box(xm - 120, yy + 24, 240, 74, stroke, fill, sw=2)
        s.text(xm, yy + 56, tag, 24)
        s.text(xm, yy + 86, ja, 17, cls="sub")

    mark(starts[0] + bw / 2, "finalized", "2 epoch 前の checkpoint", GREEN, GREEN_PALE, 0)
    # safe の位置はコンセンサス・レイヤーの実装に任されるので、finalized と latest の間の幅で示す。
    xa, xb = starts[0] + bw / 2 + 8, head - bw / 2 - 4
    s.raw(f'<path d="M{xa},{y + 64} V{y + 76} H{xb} V{y + 64}" fill="none" stroke="{BLUE}" stroke-width="3" stroke-dasharray="7 5"/>')
    xm = (xa + xb) / 2 - 40
    s.line(xm, y + 76, xm, y + 112, arrow=False, color=BLUE, sw=3)
    s.box(xm - 120, y + 114, 240, 74, BLUE, BLUE_PALE, sw=2)
    s.text(xm, y + 146, "safe", 24)
    s.text(xm, y + 176, "この間のどこか（実装による）", 16, cls="sub")
    mark(head, "latest", "最新。外れ得る", GRAY, GRAY_PALE, 0)
    s.raw(f'<path d="M{starts[0] + bw / 2},{y + 205} V{y + 218} H{head} V{y + 205}" fill="none" stroke="{SUB}" stroke-width="2"/>')
    s.text((starts[0] + head) / 2, y + 252, "順調な時で 13〜19 分ほどの差", 22, cls="sub")
    s.save("finality_tags.webp")


# --- 図6: 取り込まれてから確定扱いにするまでの待ち時間の目安 ---
def wait_figure() -> None:
    plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "DejaVu Sans"], "font.size": 11})
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    rows = [
        ("Bitcoin 承認数 3", 20, 20, BLUE, "平均 約 20 分"),
        ("Bitcoin 承認数 6", 50, 50, BLUE, "平均 約 50 分"),
        ("Ethereum finalized", 12.8, 19.2, GREEN, "約 13〜19 分"),
    ]
    for i, (label, lo, hi, color, note) in enumerate(rows):
        ax.barh(i, lo, color=color, alpha=0.35 if hi > lo else 0.75, height=0.5)
        if hi > lo:
            ax.barh(i, hi - lo, left=lo, color=color, alpha=0.75, height=0.5)
        ax.text(hi + 1, i, note, va="center", fontsize=10, color=INK)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 65)
    ax.set_xlabel("ブロックに取り込まれてからの時間（分）")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", alpha=0.3, linewidth=0.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    to_webp(buf.getvalue(), "finality_wait.webp")


# --- 図7: 2023 年 5 月の finalize の停止（Prysm の事後報告の epoch 数から）---
def incident_figure() -> None:
    plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "DejaVu Sans"], "font.size": 11})
    epoch_min = 6.4
    fig, ax = plt.subplots(figsize=(6.4, 2.2))
    # (行, 止まった epoch 数, leak が始まるまでの epoch 数)
    rows = [("5 月 11 日", 4, None), ("5 月 12 日", 9, 5)]
    for i, (label, n, leak) in enumerate(rows):
        stop = n * epoch_min
        head = (leak if leak else n) * epoch_min
        ax.barh(i, head, color=BLUE, alpha=0.75, height=0.5)
        if leak:
            ax.barh(i, stop - head, left=head, color=RED, alpha=0.75, height=0.5)
        ax.text(stop + 1, i, f"{n} epoch", va="center", fontsize=10, color=INK)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 80)
    ax.set_xlabel("finalize が止まっていた時間（分）")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=BLUE, alpha=0.75, label="finalize の停止"),
                       Patch(color=RED, alpha=0.75, label="inactivity leak による残高の減少あり")],
              loc="lower right", bbox_to_anchor=(1, 1.02), ncol=2, fontsize=9, frameon=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", alpha=0.3, linewidth=0.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    to_webp(buf.getvalue(), "finality_incident.webp")


success_rate_figure()
incident_figure()
wait_figure()
checkpoint_figure()
votes_figure()
overlap_figure()
tags_figure()

# 本文と表の値が式と一致するかを、生成のたびに確かめる
if __name__ == "__main__":
    print("\n--- 本文で使っている値 ---")
    for z in (0, 5, 10):
        print(f"q=0.10 z={z}: {attacker_success_probability(0.10, z):.7f}")
    print("\n--- 表: 成功確率が 0.1% を下回る最小の z ---")
    for q in (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45):
        z = 0
        while attacker_success_probability(q, z) >= 0.001:
            z += 1
        print(f"q={q:.2f}: z={z} (承認数 {z + 1})")
