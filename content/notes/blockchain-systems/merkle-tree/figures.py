"""Merkle Tree のノートの図を作る。

実行: python3 figures.py  -> images/merkle-tree_*.webp

- merkle-tree_cover.webp: 件数ごとの証明の大きさ（lab/proof_size.json と、lab/ct/ の公開ログの実測）。matplotlib。
- merkle-tree_path.webp: 7 件の木で、記録 2 を変えた時に変わるハッシュと、包含証明に入るハッシュ。SVG を headless Chrome で 2 倍に描き WebP に。
- merkle-tree_consistency.webp: 6 件の木と 8 件の木、その間の一貫性証明に入る 3 個。同じ作り方。
- merkle-tree_yeti.webp: Yeti 2022 で起きた順を小さなログで追う動く図。Pillow で 1 コマずつ描く。1 コマ 1.6 秒で表示し、最後のコマで 4 秒止める。

木の形は RFC 9162 の規則（左に n 未満で最大の 2 の累乗個、複製しない）で lab/merkle.py の split と同じ。
"""

from html import escape
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lab"))
from merkle import split  # noqa: E402

INK, SUB, LINE, FILL = "#1f1f1f", "#666666", "#9a9a9a", "#f2f2f2"
ACCENT, ACCENT_PALE = "#4f7fa0", "#e3eef5"
RED, RED_PALE = "#c4453f", "#fbe3e3"
OCHRE, OCHRE_PALE = "#b9862f", "#f8eed8"
GREEN, GREEN_PALE = "#5f8a55", "#e6f0e2"
FONT = "'Noto Sans CJK JP','Hiragino Sans','Yu Gothic',sans-serif"
JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
JP_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def save_webp(png, name):
    (HERE / "images").mkdir(exist_ok=True)
    Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def render(svg_text, w, h, name):
    """SVG -> PNG（headless Chrome、2 倍）-> images/<name>（WebP）。"""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        save_webp(png, name)


# ---------------------------------------------------------------- 木の配置

def layout(n, x0, x1, y_top, y_leaf, levels):
    """RFC 9162 の形の木の各ノード (a, b) の座標。葉は最下段に等間隔、内部ノードは深さで段を決める。"""
    pos = {}
    step = (x1 - x0) / max(n - 1, 1)
    dy = (y_leaf - y_top) / levels

    def walk(a, b, depth):
        if b - a == 1:
            pos[(a, b)] = (x0 + a * step, y_leaf)
            return
        k = split(b - a)
        walk(a, a + k, depth + 1)
        walk(a + k, b, depth + 1)
        lx, _ = pos[(a, a + k)]
        rx, _ = pos[(a + k, b)]
        pos[(a, b)] = ((lx + rx) / 2, y_top + depth * dy)

    walk(0, n, 0)
    return pos


def children(a, b):
    k = split(b - a)
    return (a, a + k), (a + k, b)


def name(a, b):
    return f"{a}" if b - a == 1 else f"{a}–{b - 1}"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=20, color=INK, anchor="middle"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                          f'style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2, dash="", rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                          f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=LINE, sw=2):
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                          f'stroke-width="{sw}"/>')

    def tree(self, n, x0, x1, y_top, y_leaf, levels, style, w=64, h=34):
        pos = layout(n, x0, x1, y_top, y_leaf, levels)
        for (a, b), (x, y) in pos.items():
            if b - a > 1:
                for c in children(a, b):
                    cx, cy = pos[c]
                    self.line(x, y + h / 2, cx, cy - h / 2)
        for (a, b), (x, y) in pos.items():
            fill, stroke, dash = style(a, b)
            self.box(x - w / 2, y - h / 2, w, h, fill, stroke, 2.5 if stroke != LINE else 1.5, dash)
            self.text(x, y + 7, name(a, b), 18)
        return pos

    def legend(self, x, y, items):
        for fill, stroke, dash, label in items:
            self.box(x, y - 16, 34, 22, fill, stroke, 2.5, dash, rx=5)
            self.text(x + 44, y, label, 17, anchor="start")
            x += 58 + 17 * len(label)

    def done(self):
        return "\n".join(self.parts + ["</svg>"])


# ---------------------------------------------------------------- 図 1: 表紙

def fig_cover():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matplotlib.rcParams["font.family"] = "Noto Sans CJK JP"

    rows = json.load(open(HERE / "lab/proof_size.json"))
    sth = json.load(open(HERE / "lab/ct/sth1.json"))
    inc = json.load(open(HERE / "lab/ct/inclusion.json"))
    entry_len = 819
    cons_path = HERE / "lab/ct/consistency.json"
    big = sth["tree_size"]

    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    ns = [r["n"] for r in rows]
    ax.plot(ns + [big], [n * 32 for n in ns + [big]], color="#8a8a8a", lw=2.2)
    ax.text(3e4, 3e7, "葉のハッシュを全件（件数 × 32 バイト）", color="#555555", fontsize=11, rotation=24)
    ax.plot(ns, [r["inclusion"] * 32 for r in rows], "o-", color=ACCENT, lw=2, ms=6, label="包含証明（手元の木）")
    ax.plot(ns, [r["consistency"] * 32 for r in rows], "s-", color=GREEN, lw=2, ms=5, label="一貫性証明（手元の木）")
    p = len(inc["audit_path"]) * 32
    ax.plot([big], [p], "o", color=RED, ms=10)
    ax.annotate(f"公開ログ Argon 2026h2\n{big / 1e8:.1f} 億件で包含証明 {p:,} バイト",
                (big, p), (4e6, 4e3), fontsize=11, color=RED,
                arrowprops=dict(arrowstyle="-", color=RED, lw=1.2))
    if cons_path.exists():
        c = len(json.load(open(cons_path))["consistency"]) * 32
        n2 = json.load(open(HERE / "lab/ct/cons_sth2.json"))["tree_size"]
        ax.plot([n2], [c], "s", color=RED, ms=9, mfc="white", mew=2)
        ax.annotate(f"Wyvern 2027h1（{n2 / 1e8:.1f} 億件）の一貫性証明 {c:,} バイト", (n2, c), (2e5, 110),
                    fontsize=11, color=RED, arrowprops=dict(arrowstyle="-", color=RED, lw=1.2))
    ax.axhline(entry_len, color=OCHRE, lw=1.2, ls="--")
    ax.text(150, entry_len * 1.3, f"記録 1 件の大きさ（{entry_len} バイト）", color=OCHRE, fontsize=10)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(6, 2e10)
    ax.set_ylim(40, 4e11)
    ax.set_xlabel("ログの件数")
    ax.set_ylabel("送るデータ（バイト）")
    ax.set_title("ログの件数と、証明に必要なデータの大きさ", fontsize=13)
    ax.legend(loc="upper left", frameon=False, fontsize=11)
    ax.grid(True, which="major", color="#e4e4e4")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "c.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff")
        save_webp(png, "merkle-tree_cover.webp")
    plt.close(fig)


# ---------------------------------------------------------------- 図 2: 変わる経路と包含証明

def fig_path():
    W, H = 860, 430
    s = Svg(W, H, "7 件の木で記録 2 を変えた時に変わるハッシュと、包含証明に入るハッシュ")
    changed = {(2, 3), (2, 4), (0, 4), (0, 7)}
    proof = {(3, 4), (0, 2), (4, 7)}

    def style(a, b):
        if (a, b) in changed:
            return RED_PALE, RED, ""
        if (a, b) in proof:
            return OCHRE_PALE, OCHRE, ""
        return FILL, LINE, ""

    s.text(W / 2, 34, "記録 2 を 1 ビット変えると、変わるのは記録 2 からルートまでの 4 個", 21)
    pos = s.tree(7, 90, W - 90, 90, 330, 3, style)
    s.text(pos[(0, 7)][0] + 92, pos[(0, 7)][1] + 7, "ルート", 17, SUB, "start")
    s.text(45, 337, "葉", 17, SUB)
    s.legend(150, 395, [(RED_PALE, RED, "", "値が変わる"),
                        (OCHRE_PALE, OCHRE, "", "包含証明に入る（3 個）"),
                        (FILL, LINE, "", "変わらず、送らない")])
    render(s.done(), W, H, "merkle-tree_path.webp")


# ---------------------------------------------------------------- 図 3: 一貫性証明

def fig_consistency():
    W, H = 980, 430
    s = Svg(W, H, "6 件の木と 8 件の木の間の一貫性証明")
    same = {(0, 4), (4, 6)}
    new = {(6, 8)}
    proof = same | new

    def style_old(a, b):
        if (a, b) in same:
            return GREEN_PALE, GREEN, ""
        return FILL, LINE, ""

    def style_new(a, b):
        if (a, b) in same:
            return GREEN_PALE, GREEN, ""
        if (a, b) in new:
            return ACCENT_PALE, ACCENT, ""
        return FILL, LINE, ""

    s.text(220, 40, "前の STH：6 件", 20)
    s.text(710, 40, "後の STH：8 件", 20)
    old = s.tree(6, 50, 390, 95, 330, 3, style_old, w=56)
    new_pos = s.tree(8, 480, 940, 95, 330, 3, style_new, w=56)
    for pos in (old, new_pos):
        for key in proof:
            if key in pos:
                x, y = pos[key]
                s.box(x - 36, y - 25, 72, 50, "none", OCHRE, 2.5, "6 4", rx=10)
    s.line(435, 70, 435, 345, "#d0d0d0", 1.5)
    s.legend(110, 395, [(GREEN_PALE, GREEN, "", "前の木と同じ部分木"),
                        (ACCENT_PALE, ACCENT, "", "後から足した部分木"),
                        ("#ffffff", OCHRE, "6 4", "一貫性証明に入る（3 個）")])
    render(s.done(), W, H, "merkle-tree_consistency.webp")


# ---------------------------------------------------------------- 図 4: Yeti 2022 の順を追う動く図

SCALE = 2
FW, FH = 900, 520


def font(size, bold=False):
    return ImageFont.truetype(JP_BOLD if bold else JP, size * SCALE)


def yeti_frames():
    """(件数, 反転した記録, STH 1, STH 2, 状態の文, 判定の行) のコマ。"""
    return [
        dict(n=4, flip=None, heads=[("STH 1", 4, "R1")], title="1. 4 件でSTH 1 に署名して公開する",
             lines=[]),
        dict(n=6, flip=None, heads=[("STH 1", 4, "R1")], title="2. 記録 4・5 を受け付け、葉のハッシュを保存する",
             lines=[]),
        dict(n=6, flip=5, heads=[("STH 1", 4, "R1")], title="3. 保存した記録 5 の葉のハッシュが 1 ビット反転する",
             lines=[("記録 5 の本体は正しいまま。ハッシュだけが変わった", SUB)]),
        dict(n=7, flip=5, heads=[("STH 1", 4, "R1"), ("STH 2", 7, "R2")],
             title="4. 記録 6 を足し、反転したハッシュのままSTH 2 に署名する", lines=[]),
        dict(n=7, flip=5, heads=[("STH 1", 4, "R1"), ("STH 2", 7, "R2")],
             title="5. STH 1 → STH 2 の一貫性証明は通る",
             lines=[("前の 4 件の部分木は変わっていないので、検証は成功", GREEN)]),
        dict(n=7, flip=5, heads=[("STH 1", 4, "R1"), ("STH 2", 7, "R2")],
             title="6. 監視する側が全件を取り直してルートを作ると、R2 と合わない",
             lines=[("記録から計算したルート R2′ ≠ 署名された R2", RED)]),
        dict(n=7, flip=None, heads=[("STH 1", 4, "R1"), ("STH 2", 7, "R2"), ("直した木", 7, "R2′")],
             title="7. ハッシュを正しく戻すと、同じ 7 件に 2 つのルートが並ぶ",
             lines=[("署名済みの R2 と矛盾する。R2 に合う記録 5 を探すには、ハッシュから入力を逆算する必要がある", RED)]),
        dict(n=7, flip=5, heads=[("STH 1", 4, "R1"), ("STH 2", 7, "R2")],
             title="8. 残る手は、新しい記録を受け付けない読み取り専用にすること",
             lines=[("Yeti 2022 は 2021-07-03 に読み取り専用、07-21 に Chrome で Retired", INK)]),
    ]


def draw_frame(fr, idx, total):
    img = Image.new("RGB", (FW * SCALE, FH * SCALE), "#ffffff")
    d = ImageDraw.Draw(img)
    S = lambda v: v * SCALE  # noqa: E731

    # 上の帯: 何コマ目か
    d.text((S(24), S(16)), "Yeti 2022 で起きた順（説明用の 7 件のログ、1 コマ 1.6 秒で表示）", font=font(16), fill=SUB)
    bar_x0, bar_x1 = 24, FW - 24
    d.rounded_rectangle([S(bar_x0), S(44), S(bar_x1), S(52)], S(4), fill="#ececec")
    d.rounded_rectangle([S(bar_x0), S(44), S(bar_x0 + (bar_x1 - bar_x0) * (idx + 1) / total), S(52)],
                        S(4), fill=ACCENT)
    d.text((S(24), S(66)), fr["title"], font=font(21, True), fill=INK)

    # 木
    n_full = 7
    w, h = 58, 32
    # 件数 n の木で実際にあるノードだけを描く
    def nodes(a, b):
        out = {(a, b)}
        if b - a > 1:
            k = split(b - a)
            out |= nodes(a, a + k) | nodes(a + k, b)
        return out
    present = nodes(0, fr["n"])
    pos_n = layout(fr["n"], 120, 120 + 480 * (fr["n"] - 1) / (n_full - 1), 150, 390, 3)
    tainted = set()
    if fr["flip"] is not None:
        tainted = {k for k in present if k[0] <= fr["flip"] < k[1]}
    for (a, b) in present:
        if b - a > 1:
            x, y = pos_n[(a, b)]
            for c in children(a, b):
                cx, cy = pos_n[c]
                d.line([S(x), S(y + h / 2), S(cx), S(cy - h / 2)], fill=LINE, width=S(2))
    for (a, b) in present:
        x, y = pos_n[(a, b)]
        if (a, b) in tainted:
            fill, stroke = RED_PALE, RED
        elif b <= 4:
            fill, stroke = GREEN_PALE, GREEN
        else:
            fill, stroke = FILL, LINE
        d.rounded_rectangle([S(x - w / 2), S(y - h / 2), S(x + w / 2), S(y + h / 2)], S(7),
                            fill=fill, outline=stroke, width=S(2))
        label = name(a, b)
        tw = d.textlength(label, font=font(16))
        d.text((S(x) - tw / 2, S(y - 12)), label, font=font(16), fill=INK)
    if fr["flip"] is not None:
        x, y = pos_n[(fr["flip"], fr["flip"] + 1)]
        d.text((S(x - 34), S(y + 22)), "1 ビット反転", font=font(14), fill=RED)

    # 右: 公開した STH
    d.text((S(650), S(140)), "公開した STH", font=font(16), fill=SUB)
    for i, (label, size, r) in enumerate(fr["heads"]):
        y = 170 + i * 62
        bad = r == "R2" and fr["flip"] is not None or r == "R2′"
        fill = OCHRE_PALE if label != "直した木" else "#ffffff"
        d.rounded_rectangle([S(650), S(y), S(870), S(y + 48)], S(8), fill=fill,
                            outline=OCHRE if label != "直した木" else RED, width=S(2))
        d.text((S(664), S(y + 10)), f"{label}：{size} 件", font=font(16), fill=INK)
        d.text((S(820), S(y + 10)), r, font=font(16, True), fill=RED if r == "R2′" else INK)

    for i, (text, color) in enumerate(fr["lines"]):
        d.text((S(24), S(440 + i * 30)), text, font=font(17), fill=color)
    return img.resize((FW, FH), Image.LANCZOS)


def fig_yeti():
    frames = yeti_frames()
    imgs = [draw_frame(f, i, len(frames)) for i, f in enumerate(frames)]
    durations = [1600] * (len(imgs) - 1) + [4000]
    (HERE / "images").mkdir(exist_ok=True)
    imgs[0].save(HERE / "images/merkle-tree_yeti.webp", "WEBP", save_all=True, append_images=imgs[1:],
                 duration=durations, loop=0, quality=80, method=6)


if __name__ == "__main__":
    fig_cover()
    fig_path()
    fig_consistency()
    fig_yeti()
