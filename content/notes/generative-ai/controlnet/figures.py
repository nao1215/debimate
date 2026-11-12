"""ControlNet のノートの図を作る。

- controlnet_concept.svg: SDXL の U-Net と、学習するコピー・ゼロ畳み込みのつながり（Python 標準ライブラリで SVG を手書き）
- controlnet_error.svg: 条件ごとの関節のずれ（lab/pose_metrics.json を読む。Python 標準ライブラリで SVG を手書き）

    python3 figures.py
"""

import json
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab"
IMAGES = HERE / "images"
INK, SUB, BLUE, OCHRE, RED = "#1f1f1f", "#666666", "#7aa6c2", "#d4a24c", "#e15759"
BLUE_F, OCHRE_F, NEUTRAL = "#eaf1f5", "#f8eed8", "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def text(x, y, s, size=24, color=INK, anchor="middle"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" dominant-baseline="middle">{escape(s)}</text>')


def rect(x, y, w, h, stroke, fill, rx=8, sw=2.5):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def line(x1, y1, x2, y2, color=SUB, sw=2.5, dash=None, arrow=False):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = ' marker-end="url(#arrow)"' if arrow else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{d}{m}/>'


def concept_figure():
    """上段: 固定した U-Net（縮める段 → 中央 → 広げる段、skip connection で対の段をつなぐ）。
    下段: 縮める段と中央の学習するコピーを、対になる広げる段の真下に右から左へ並べる。
    コピーの各段の出力は、ゼロ畳み込み（0 の四角）を通って真上の段に足される。"""
    W, H = 960, 540
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
         '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
         f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    bw = 62
    enc_x, heights = [150, 245, 340], [150, 110, 76]   # 縮める段（解像度が下がるほど低い）
    dec_x = [750, 655, 560]                            # 縮める段 i と対になる広げる段
    mid_x, mid_h = 450, 56
    top_c, bot_c, zy = 150, 400, 278
    for x, h in zip(enc_x, heights):
        o.append(rect(x, top_c - h / 2, bw, h, SUB, NEUTRAL))
    o.append(rect(mid_x, top_c - mid_h / 2, bw, mid_h, SUB, NEUTRAL))
    for x, h in zip(dec_x, heights):
        o.append(rect(x, top_c - h / 2, bw, h, SUB, NEUTRAL))
    chain = enc_x + [mid_x] + dec_x[::-1]
    for a, b in zip(chain, chain[1:]):
        o.append(line(a + bw, top_c, b, top_c, arrow=True))
    o.append(line(dec_x[0] + bw, top_c, 875, top_c, arrow=True))
    o.append(text(910, top_c, "出力", 22, SUB))
    o.append(text(60, top_c - 18, "ノイズを", 22, SUB))
    o.append(text(60, top_c + 14, "含む潜在", 22, SUB))
    o.append(line(105, top_c, enc_x[0], top_c, arrow=True))
    for i, h in enumerate(heights):  # skip connection
        x1, x2, y = enc_x[i] + bw / 2, dec_x[i] + bw / 2, top_c - h / 2
        yy = 40 + i * 18
        o.append(f'<path d="M{x1},{y} L{x1},{yy} L{x2},{yy} L{x2},{y - 4}" fill="none" stroke="{SUB}" '
                 f'stroke-width="2" marker-end="url(#arrow)"/>')
    o.append(text(260, 258, "SDXL の U-Net（固定）", 24, INK))
    # 下段: 学習するコピー（黄土）。右から左へ: 縮める段 1, 2, 3, 中央
    copy_x, copy_h = dec_x + [mid_x], heights + [mid_h]
    for x, h in zip(copy_x, copy_h):
        o.append(rect(x, bot_c - h / 2, bw, h, OCHRE, OCHRE_F))
    for a, b in zip(copy_x, copy_x[1:]):
        o.append(line(a, bot_c, b + bw, bot_c, arrow=True))
    o.append(text(640, 510, "学習するコピー（縮める段と中央）", 24, INK))
    o.append(rect(860, bot_c - 60, 80, 120, BLUE, BLUE_F))
    o.append(text(900, bot_c - 18, "条件の", 20, INK))
    o.append(text(900, bot_c + 14, "画像", 20, INK))
    o.append(line(860, bot_c, dec_x[0] + bw, bot_c, color=BLUE, arrow=True))
    # ゼロ畳み込みを通して、真上の段（広げる段・中央）に足す
    for x, h in zip(copy_x, copy_h):
        cx = x + bw / 2
        top_h = dict(zip(dec_x, heights)).get(x, mid_h)
        o.append(line(cx, bot_c - h / 2, cx, zy + 16, color=OCHRE))
        o.append(rect(cx - 16, zy - 16, 32, 32, OCHRE, "#ffffff", rx=4, sw=2))
        o.append(text(cx, zy + 1, "0", 20, INK))
        o.append(f'<path d="M{cx},{zy - 16} L{cx},{top_c + top_h / 2 + 6}" fill="none" stroke="{OCHRE}" '
                 f'stroke-width="2.5" marker-end="url(#arrow)"/>')
    o.append(text(420, 330, "ゼロ畳み込みを通して足す", 22, INK, "end"))
    o.append(text(420, 362, "（重みを 0 から学習する）", 20, SUB, "end"))
    o.append("</svg>")
    (IMAGES / "controlnet_concept.svg").write_text("\n".join(o) + "\n")


def error_figure():
    """ポーズごとに、腕と脚の関節のずれ（3D モデルの背丈に対する %）を条件ごとの棒で並べる。
    棒は seed 2 本の平均、点は各 seed。破線は 3D モデルの深度マップそのものを検出した時のずれ（検出器の目安）。"""
    m = json.loads((LAB / "pose_metrics.json").read_text())
    poses = [("raise", "腕を上げる"), ("lunge", "突き"), ("lookback", "振り返る")]
    conds = [("text", "プロンプトだけ", "#bdbdbd", NEUTRAL), ("openpose", "骨格", BLUE, BLUE_F),
             ("depth", "深度マップ", OCHRE, OCHRE_F)]
    seeds = ["20261111", "20261112"]
    W, H = 960, 540
    x0, y0, ph, top = 70, 440, 350, 70.0  # 縦軸 0〜top %
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>']

    def yv(v):
        return y0 - min(v, top) / top * ph

    for t in range(0, int(top) + 1, 10):
        o.append(line(x0, yv(t), W - 20, yv(t), color="#e0e0e0", sw=1))
        o.append(text(x0 - 10, yv(t), f"{t}%", 18, SUB, "end"))
    o.append(text(x0 - 50, 62, "ずれ（背丈に対する %）", 18, SUB, "start"))
    pw = (W - 20 - x0) / 3
    for pi, (pose, label) in enumerate(poses):
        px = x0 + pi * pw
        o.append(text(px + pw / 2, 480, label, 22, INK))
        for gi, part in enumerate(["arms", "legs"]):
            gx = px + 20 + gi * (pw - 30) / 2
            gw = (pw - 30) / 2 - 20
            o.append(text(gx + gw / 2, 455, "腕" if part == "arms" else "脚", 18, SUB))
            base = m.get(f"{pose}_mannequin")
            if isinstance(base, dict):
                o.append(line(gx - 4, yv(base[part]), gx + gw + 4, yv(base[part]), color=INK, sw=1.5, dash="5 4"))
            bw = gw / 3
            for ci, (c, _, stroke, fill) in enumerate(conds):
                vals = [m[f"{pose}_{c}_{sd}"][part] for sd in seeds
                        if isinstance(m.get(f"{pose}_{c}_{sd}"), dict)]
                if not vals:
                    continue
                mean = sum(vals) / len(vals)
                bx = gx + ci * bw + 3
                o.append(rect(bx, yv(mean), bw - 6, y0 - yv(mean), stroke, fill, rx=2, sw=2))
                for v in vals:
                    o.append(f'<circle cx="{bx + (bw - 6) / 2}" cy="{yv(v)}" r="4" fill="{INK}"/>')
    o.append(line(x0, y0, W - 20, y0, color=SUB, sw=1.5))
    # 凡例
    lx = 330
    for _, name, stroke, fill in conds:
        o.append(rect(lx, 18, 22, 22, stroke, fill, rx=2, sw=2))
        o.append(text(lx + 30, 30, name, 20, INK, "start"))
        lx += 30 + 20 * len(name) + 30
    o.append(line(lx, 29, lx + 30, 29, color=INK, sw=1.5, dash="5 4"))
    o.append(text(lx + 38, 30, "3D モデルそのもの", 20, INK, "start"))
    o.append("</svg>")
    (IMAGES / "controlnet_error.svg").write_text("\n".join(o) + "\n")


if __name__ == "__main__":
    IMAGES.mkdir(exist_ok=True)
    concept_figure()
    if (LAB / "pose_metrics.json").exists():
        error_figure()
    print("wrote", IMAGES / "controlnet_concept.svg")
