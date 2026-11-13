"""Blockchain Basics のノートの図を作る。

rules_figure()     lab/trace.json（lab/fork_rules.py の seed 1 の記録）から、規則を変えた 4 通りで
                   古い規則のノードと新しい規則のノードが持つ列が、ブロックが見つかる度にどう変わるかを
                   動く WebP にする。時間の軸は 2 組を合わせたハッシュの試行回数（実測）。
link_figure()      Bitcoin のブロック構造で、トランザクションの書き換えが Merkle root とヘッダのハッシュ値を経て
                   次のブロックの prev と合わなくなる順を描く。
validity_figure()  3 つの規則で有効なブロックの範囲を、入れ子の枠で描く。

実行: python3 content/notes/blockchain-systems/blockchain-basics/figures.py
（先に lab で python3 fork_rules.py > output.txt と python3 hash_link.py > hash_link_output.txt を実行する）
"""

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab"
IMAGES = HERE / "images"
S = 2  # 2 倍で描いて縮める
JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
INK, SUB, LINE = "#28343b", "#5f6d75", "#9cabb5"
OLD, NEW, RED = "#a9b4bb", "#2f6f8f", "#c0392b"
SHARED = "#eef3f6"


def font(n, mono=False):
    return ImageFont.truetype(MONO if mono else JP, int(n * S))


def canvas(w, h):
    img = Image.new("RGB", (w * S, h * S), "#ffffff")
    return img, ImageDraw.Draw(img)


def shrink(img):
    return img.resize((img.width // S, img.height // S), Image.LANCZOS)


def text(d, x, y, s, size, color=INK, mono=False, anchor="la"):
    d.text((x * S, y * S), s, font=font(size, mono), fill=color, anchor=anchor)


def rect(d, x, y, w, h, fill, outline=None, width=1.5, r=4):
    d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=r * S, fill=fill,
                        outline=outline, width=int(width * S))


# 1 秒で 4 万回分の試行を進める。コマは 300ms ごと。
ATTEMPTS_PER_SEC = 40_000
FRAME_MS = 300
ROWS = [
    ("soft-0.7", "上限を厳しくする（ソフトフォーク）・新マイナーが 70%"),
    ("soft-0.3", "上限を厳しくする（ソフトフォーク）・新マイナーが 30%"),
    ("hard-0.7", "上限を緩める（ハードフォーク）・新マイナーが 70%"),
    ("hard-0.3", "上限を緩める（ハードフォーク）・新マイナーが 30%"),
]


def verdicts():
    """lab/output.txt の 20 回の中央値で、共有する長さが 20 個を超える組を「1 本に戻る」とする。"""
    out = {}
    for kind, share, common in re.findall(r"^(soft|hard) (0\.\d)\s+(\d+)", (LAB / "output.txt").read_text(), re.M):
        out[f"{kind}-{share}"] = int(common) > 20
    return out


def rules_figure():
    trace = json.loads((LAB / "trace.json").read_text())
    end = max(trace[k]["events"][-1]["attempt"] for k, _ in ROWS)
    step = ATTEMPTS_PER_SEC * FRAME_MS // 1000
    times = list(range(0, end + step, step))
    W, H = 1000, 700
    BOX, GAP, X0 = 9, 2, 180
    one = verdicts()
    frames = []
    for t in times:
        img, d = canvas(W, H)
        text(d, 24, 16, "規則を変えた後に、旧ノードと新ノードが選ぶ列", 22)
        text(d, 24, 50, f"ハッシュの試行 {min(t, end) / 10000:5.1f} 万回目"
             f"（2 組の合計。試行 4 万回を 1 秒で表示）", 15, SUB)
        # 進み具合の帯
        rect(d, 24, 78, W - 48, 6, "#e6ebee", r=3)
        rect(d, 24, 78, (W - 48) * min(t, end) / end, 6, LINE, r=3)
        rect(d, 560, 52, 14, 14, OLD)
        text(d, 580, 49, "旧マイナーが作ったブロック", 14, SUB)
        rect(d, 775, 52, 14, 14, NEW)
        text(d, 795, 49, "新マイナーが作ったブロック", 14, SUB)
        for i, (key, title) in enumerate(ROWS):
            evs = [e for e in trace[key]["events"] if e["attempt"] <= t]
            y = 106 + i * 148
            text(d, 24, y, title, 16)
            if not evs:
                continue
            e = evs[-1]
            common = e["common"]
            for j, (lane, label) in enumerate((("old", "旧ノード（古い規則）"), ("new", "新ノード（新しい規則）"))):
                ly = y + 34 + j * 26
                text(d, 24, ly - 2, label, 14, SUB)
                chain = e[lane]
                if common:
                    rect(d, X0 - 3, ly - 3, common * (BOX + GAP) + 4, BOX + 6, SHARED, r=2)
                for k, miner in enumerate(chain):
                    rect(d, X0 + k * (BOX + GAP), ly, BOX, BOX, NEW if miner == "new" else OLD, r=2)
                text(d, X0 + len(chain) * (BOX + GAP) + 8, ly - 3, f"{len(chain)}", 14, SUB)
            old_only, new_only = len(e["old"]) - common, len(e["new"]) - common
            if t >= end and one[key]:
                # 緩い側のノードは、厳しい側の列が追い越せば乗り換える（同じ長さなら先に届いた方を保つ）
                strict = "new" if key.startswith("soft") else "old"
                loose = "old" if strict == "new" else "new"
                tail = len(e[loose]) - common
                name = {"old": "旧ノード", "new": "新ノード"}
                if tail:
                    note = f"{name[loose]}の末尾 {tail} 個は、{name[strict]}の列が {len(e[loose]) + 1} 個になれば外れる"
                else:
                    note = "末尾の数個は、次のブロック次第で入れ替わる"
                text(d, 24, y + 92, f"共有 {common} 個 → 1 本に戻る。{note}", 15)
            elif t >= end:
                text(d, 24, y + 92, f"共有 {common} 個 → 2 本のまま（分かれた後は旧ノード {old_only} 個・新ノード {new_only} 個）", 15, RED)
            else:
                text(d, 24, y + 92, f"共有 {common} 個。分かれた後は旧ノード {old_only} 個・新ノード {new_only} 個", 15, SUB)
        frames.append(shrink(img))
    durations = [FRAME_MS] * (len(frames) - 1) + [3500]
    frames[0].save(IMAGES / "blockchain-basics_rules.webp", "WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, lossless=True, quality=100, method=6)
    print("rules:", len(frames), "frames", sum(durations) / 1000, "s")


def link_figure():
    """Bitcoin のブロック構造で、トランザクション 2 の書き換えが Merkle root、ヘッダのハッシュ値を経て
    次のブロックの prev との不一致に届く順を描く。ハッシュ値の具体的な値は描かない。"""
    W, H = 1000, 430
    img, d = canvas(W, H)
    text(d, 24, 16, "ブロック 100 のトランザクション 2 を書き換えると", 20)
    bw, gap, x0, y0 = 270, 60, 24, 64
    hh, th = 132, 150  # ヘッダとトランザクションの並びの高さ
    for i in range(3):
        x = x0 + i * (bw + gap)
        bad = i == 0
        text(d, x, y0, f"ブロック {100 + i}", 16)
        hy = y0 + 30
        rect(d, x, hy, bw, hh, "#fbeceb" if bad else "#f4f7f9", RED if bad else LINE, width=2)
        text(d, x + 12, hy + 8, "ヘッダ", 13, SUB)
        prev_bad = i == 1
        rect(d, x + 12, hy + 32, bw - 24, 26, "#ffffff", RED if prev_bad else LINE, width=1.5)
        text(d, x + 22, hy + 45, "prev（直前ヘッダのハッシュ値）", 13, RED if prev_bad else INK, anchor="lm")
        rect(d, x + 12, hy + 64, bw - 24, 26, "#ffffff", RED if bad else LINE, width=1.5)
        text(d, x + 22, hy + 77, "Merkle root", 13, RED if bad else INK, mono=False, anchor="lm")
        rect(d, x + 12, hy + 96, bw - 24, 26, "#ffffff", LINE, width=1.5)
        text(d, x + 22, hy + 109, "nonce", 13, INK, anchor="lm")
        ty = hy + hh + 12
        rect(d, x, ty, bw, th, "#f4f7f9", LINE, width=2)
        text(d, x + 12, ty + 8, "トランザクションの並び", 13, SUB)
        for k in range(3):
            tbad = bad and k == 1
            rect(d, x + 12, ty + 32 + k * 36, bw - 24, 28, "#fbeceb" if tbad else "#ffffff",
                 RED if tbad else LINE, width=2 if tbad else 1.5)
            label = f"トランザクション {k + 1}" + ("（書き換え）" if tbad else "")
            text(d, x + 22, ty + 46 + k * 36, label, 13, RED if tbad else INK, anchor="lm")
        if bad:
            # 書き換え -> Merkle root の矢印
            ax, ay0, ay1 = x + bw - 30, ty + 32 + 36, hy + 90
            d.line([ax * S, ay0 * S, ax * S, (ay1 + 8) * S], fill=RED, width=3 * S)
            d.polygon([(ax * S, ay1 * S), ((ax - 7) * S, (ay1 + 12) * S), ((ax + 7) * S, (ay1 + 12) * S)], fill=RED)
        # 次のブロックの prev から前のブロックのヘッダへ
        if i > 0:
            px = x
            py = hy + 45
            color = RED if prev_bad else LINE
            d.line([((px - gap + 8) * S), py * S, px * S, py * S], fill=color, width=3 * S)
            tip = px - gap
            d.polygon([(tip * S, py * S), ((tip + 12) * S, (py - 7) * S), ((tip + 12) * S, (py + 7) * S)], fill=color)
            if prev_bad:
                text(d, px - gap / 2, py - 10, "合わない", 12, RED, anchor="mb")
    text(d, x0, H - 24, "Merkle root が変わるとヘッダのハッシュ値も変わり、ブロック 101 の prev と合わなくなる", 14, RED)
    img = shrink(img)
    img.save(IMAGES / "blockchain-basics_link.webp", "WEBP", quality=90, method=6)


def validity_figure():
    W, H = 1000, 380
    img, d = canvas(W, H)
    text(d, 24, 16, "ブロックの大きさの上限と、有効と判断するノード", 20)
    rect(d, 24, 60, 952, 300, "#f4f7f9", LINE, width=2, r=10)
    text(d, 40, 72, "緩めた規則で有効（2000 バイトまで）", 15)
    rect(d, 60, 110, 600, 230, "#eaf1f5", LINE, width=2, r=10)
    text(d, 76, 122, "古い規則で有効（1000 バイトまで）", 15)
    rect(d, 96, 160, 300, 160, "#dfeaf0", NEW, width=2, r=10)
    text(d, 112, 172, "厳しくした規則で有効", 15)
    text(d, 112, 196, "（500 バイトまで）", 15)
    for x, y, size, who in ((112, 232, "400", "全てのノードが受け取る"),
                            (430, 232, "800", "厳しくした規則のノードだけが拒む"),
                            (700, 232, "1500", "緩めた規則のノードしか受け取らない")):
        rect(d, x, y, 76, 36, "#ffffff", INK, width=1.5, r=4)
        text(d, x + 38, y + 18, f"{size} B", 14, INK, mono=True, anchor="mm")
        text(d, x, y + 46, who, 13, SUB)
    img = shrink(img)
    img.save(IMAGES / "blockchain-basics_validity.webp", "WEBP", quality=90, method=6)


if __name__ == "__main__":
    rules_figure()
    link_figure()
    validity_figure()
