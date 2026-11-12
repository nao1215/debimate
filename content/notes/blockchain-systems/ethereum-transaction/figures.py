"""Generate the figures of the Ethereum transaction note.

python3 figures.py
  -> images/ethereum-transaction_deversifi.webp  （lab/output/deversifi.json。2021-09-27 の 7,676 ETH の単価）
  -> images/ethereum-transaction_bytes.webp      （lab/output/results.json。署名済みの 119 バイトの区切り）
  -> images/ethereum-transaction_recover.webp    （lab/output/results.json。試した書き換えで別の送信元が復元された）
  -> images/ethereum-transaction_fee_split.webp  （lab/output/results.json。priority fee を変えた 3 件の内訳）
  -> images/ethereum-transaction_reserve.webp    （lab/output/results.json。上限分の額と残高）
  -> images/ethereum-transaction_nested.webp     （模式図。中の呼び出しの失敗と status）
  -> images/ethereum-transaction_basefee_rise.webp（EIP-1559 の式。満杯が続いた時の base fee）
matplotlib で dpi 200 の PNG に描き、Pillow で WebP（quality 90、method 6）にする。背景は白。
数値は lab の出力から読み、手で書かない。
"""

import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
IMG = HERE / "images"
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED, RED_PALE = "#e15759", "#fbe3e3"
GRAY, GRAY_PALE = "#9a9a9a", "#f2f2f2"

plt.rcParams.update({
    "font.family": ["Noto Sans CJK JP", "DejaVu Sans"],
    "font.size": 11,
    "axes.edgecolor": SUB,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "text.color": INK,
})


def save(fig, name):
    IMG.mkdir(exist_ok=True)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(IMG / name, "WEBP", quality=90, method=6)


def fmt(x):
    return f"{x:,.0f}" if x >= 100 else f"{x:,.1f}"


def deversifi():
    s = json.loads((OUT / "deversifi.json").read_text())["summary"]
    rows = [
        ("base fee（その時のブロック）", s["base_fee_gwei"], GRAY),
        ("maxPriorityFeePerGas（書いた値）", s["max_priority_fee_gwei"], OCHRE),
        ("maxFeePerGas（書いた値）", s["max_fee_gwei"], BLUE),
    ]
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    for i, (label, v, c) in enumerate(rows):
        ax.barh(i, v, color=c, height=0.55)
        ax.text(v * 1.4, i, f"{fmt(v)} gwei", va="center", fontsize=11)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlim(1, 1e11)
    ax.set_xlabel("gas 1 単位あたりの値（gwei、対数）")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(
        f"2021-09-27 のブロック {s['block']:,}：手数料 {s['fee_eth']:,.1f} ETH、"
        f"うち焼却 {s['burn_eth']:.4f} ETH",
        loc="left", fontsize=12)
    ax.text(1.2, 2.62,
            f"払った単価 = base fee + priority fee = {fmt(s['effective_gas_price_gwei'])} gwei"
            f"（maxFeePerGas には届いていない）× gasUsed {s['gas_used']:,}",
            fontsize=10, color=SUB, va="top")
    ax.set_ylim(2.95, -0.5)
    save(fig, "ethereum-transaction_deversifi.webp")


SEGMENTS = [  # (バイト数, 名前, 署名に含むか)
    (1, "型 02", "head"), (2, "長さ", "head"), (3, "chainId", "body"), (1, "nonce", "body"),
    (5, "maxPriority\nFeePerGas", "body"), (5, "maxFee\nPerGas", "body"), (3, "gasLimit", "body"),
    (21, "to（宛先）", "body"), (9, "value\n（額）", "body"), (1, "data", "body"),
    (1, "accessList", "body"), (1, "yParity", "sig"), (33, "r", "sig"), (33, "s", "sig"),
]


def byte_layout():
    raw = json.loads((OUT / "results.json").read_text())["tamper"]["raw"]
    n = (len(raw) - 2) // 2
    assert n == sum(seg[0] for seg in SEGMENTS)
    # 1 バイトの欄も名前が入るよう、表示の幅は最低 13 にする（幅はバイト数に比例しない）。
    # 上の段に型・長さと署名する欄、下の段に署名を置き、1 本の帯を 2 段に折り返して描く。
    width = lambda size: max(size, 15) if size == 5 else max(size, 13)
    rows = [[seg for seg in SEGMENTS if seg[2] != "sig"], [seg for seg in SEGMENTS if seg[2] == "sig"]]
    total = max(sum(width(seg[0]) for seg in row) for row in rows)
    fig, ax = plt.subplots(figsize=(11, 4.2))
    colors = {"head": (GRAY_PALE, GRAY), "body": (BLUE_PALE, BLUE), "sig": (OCHRE_PALE, OCHRE)}
    signed = sum(seg[0] for seg in SEGMENTS if seg[2] == "body")
    sig = sum(seg[0] for seg in SEGMENTS if seg[2] == "sig")
    labels = {"body": f"署名する欄（{signed} バイト。リストにまとめ直し、前に型 02 を付けてハッシュする）", "sig": f"署名（{sig} バイト）"}
    line_colors = {"body": BLUE, "sig": OCHRE}
    for r, row in enumerate(rows):
        y = 2.6 - r * 2.0
        x = 0
        spans = {}
        for size, name, kind in row:
            fc, ec = colors[kind]
            w = width(size)
            ax.add_patch(Rectangle((x, y), w, 1, facecolor=fc, edgecolor=ec, lw=1.2))
            ax.text(x + w / 2, y + 0.5, f"{name}\n{size} バイト", ha="center", va="center", fontsize=10)
            spans.setdefault(kind, [x, x])
            spans[kind][1] = x + w
            x += w
        for kind in ("body", "sig"):
            if kind not in spans:
                continue
            x0, x1 = spans[kind]
            c = line_colors[kind]
            ax.plot([x0 + 0.5, x0 + 0.5, x1 - 0.5, x1 - 0.5], [y + 1.1, y + 1.25, y + 1.25, y + 1.1], color=c, lw=1.5)
            ax.text((x0 + x1) / 2, y + 1.32, labels[kind], ha="center", va="bottom", fontsize=11)
    ax.text(0, 4.35, f"Anvil で署名した 1 ETH の送金（type 2）、全体 {n} バイト。送信元（from）の欄は無い",
            fontsize=12.5, va="bottom")
    ax.text(0, 0.45, "上の段の後ろに下の段が続く。バイト数は長さを表す先頭のバイトを含む。小さな欄は広げて描いた（幅はバイト数に比例しない）",
            fontsize=9.5, color=SUB, va="top")
    ax.set_xlim(-1, total + 1)
    ax.set_ylim(0.0, 4.8)
    ax.axis("off")
    save(fig, "ethereum-transaction_bytes.webp")


def short(a):
    return a[:6] + "…" + a[-4:]


def box(ax, x, y, w, h, text, fc, ec, size=10, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                facecolor=fc, edgecolor=ec, lw=1.3, ls=ls))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size)


def arrow(ax, x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12,
                                 color=INK, lw=1.2))


def recover():
    t = json.loads((OUT / "results.json").read_text())["tamper"]
    orig, forged = t["rows"][0], t["rows"][1]
    fig, ax = plt.subplots(figsize=(10, 4.3))
    lanes = [
        (2.35, "元のバイト列\nvalue = 1 ETH", BLUE_PALE, BLUE, short(orig["signer"]),
         "Anvil のアカウント 0\n（署名した鍵）", GREEN_PALE, GREEN, "受け付けて実行"),
        (0.35, "value を書き換え\nvalue = 2 ETH", RED_PALE, RED, short(forged["signer"]),
         "鍵の持ち主はいない\n（残高 0）", RED_PALE, RED,
         "残高不足で拒否\n残高を入れると\n実行された"),
    ]
    for y, src, fc, ec, addr, who, fc2, ec2, node in lanes:
        box(ax, 0.0, y, 2.2, 1.1, src, fc, ec)
        arrow(ax, 2.2, y + 0.55, 2.75, y + 0.55)
        box(ax, 2.75, y, 1.9, 1.1, "署名する欄を\nハッシュ", GRAY_PALE, GRAY)
        arrow(ax, 4.65, y + 0.55, 5.2, y + 0.55)
        box(ax, 5.2, y, 2.0, 1.1, "同じ r, s, yParity\nから公開鍵を復元", GRAY_PALE, GRAY)
        arrow(ax, 7.2, y + 0.55, 7.75, y + 0.55)
        box(ax, 7.75, y, 2.2, 1.1, f"送信元 {addr}\n{who}", fc2, ec2, size=9.5)
        ax.text(10.1, y + 0.55, node, ha="left", va="center", fontsize=9.5)
    sig = sum(seg[0] for seg in SEGMENTS if seg[2] == 'sig')
    ax.text(0, 3.75, f"署名の {sig} バイトに触れずに試した {len(t['rows']) - 1} 件の書き換えでは、どれも公開鍵の復元は失敗せず、別の送信元が復元された", fontsize=11.5)
    ax.set_xlim(-0.1, 12.3)
    ax.set_ylim(0.1, 4.1)
    ax.axis("off")
    save(fig, "ethereum-transaction_recover.webp")


def fee_split():
    rows = json.loads((OUT / "results.json").read_text())["fee"]["rows"]
    fig, ax = plt.subplots(figsize=(9, 3.4))
    for i, r in enumerate(rows):
        base, eff, cap = r["base_gwei"], r["eff_gwei"], r["max_fee_gwei"]
        tip = eff - base
        ax.barh(i, base, color=GRAY, height=0.55)
        ax.barh(i, tip, left=base, color=OCHRE, height=0.55)
        ax.barh(i, cap - eff, left=eff, color="#ffffff", edgecolor=BLUE, hatch="//", height=0.55, lw=1)
        ax.text(base / 2, i, f"{base:.0f}", ha="center", va="center", fontsize=9.5, color="#ffffff")
        if tip >= 8:
            ax.text(base + tip / 2, i, f"{tip:.0f}", ha="center", va="center", fontsize=9.5)
        else:
            ax.text(base + tip + 0.8, i - 0.42, f"{tip:.0f}", ha="left", va="center", fontsize=9.5)
        if cap - eff > 0:
            ax.text(eff + (cap - eff) / 2, i, f"払わない {cap - eff:.0f}", ha="center", va="center",
                    fontsize=9.5, color=SUB, bbox=dict(facecolor="#ffffff", edgecolor="none", pad=1))
        ax.text(cap + 2, i, f"手数料 {r['fee_eth']:.6f} ETH", va="center", fontsize=9.5)
    ax.set_yticks(range(len(rows)), [f"priority fee {r['prio_gwei']} gwei" for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 135)
    ax.axvline(100, color=BLUE, lw=1.2, ls="--")
    ax.text(101, -0.62, "maxFeePerGas 100", color=BLUE, ha="left", fontsize=9.5)
    ax.set_xlabel("gas 1 単位あたり（gwei）")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=GRAY, label="base fee（焼却）"),
                       Patch(color=OCHRE, label="tip（ブロックを作った側へ）"),
                       Patch(facecolor="#ffffff", edgecolor=BLUE, hatch="//", label="払わない分")],
              loc="upper center", bbox_to_anchor=(0.45, -0.25), ncol=3, frameon=False, fontsize=9.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(2.5, -0.85)
    save(fig, "ethereum-transaction_fee_split.webp")


def reserve():
    rows = json.loads((OUT / "results.json").read_text())["reserve"]
    fig, ax = plt.subplots(figsize=(9, 3.2))
    left = rows[0]["balance_eth"] - 1.0
    for i, r in enumerate(rows):
        pre = r["need_eth"] - 1.0
        ok = r["node"] == "受け付けた"
        ax.barh(i, pre, color=GREEN if ok else RED, height=0.5)
        res = "受け付けた" if ok else "拒否（Insufficient funds）"
        tx = max(pre * 1.25, left * 1.15)  # 残りの点線と文字が重ならない位置
        ax.text(tx, i, f"{pre:.5f} ETH　{res}", va="center", fontsize=9.5)
        if ok:
            ax.text(tx, i + 0.32, f"実際の手数料 {r['fee_eth']:.6f} ETH", va="center",
                    fontsize=9, color=SUB)
    ax.axvline(left, color=INK, lw=1.2, ls="--")
    ax.text(left * 1.08, -0.6, f"1 ETH を送った残り {left:.3f} ETH", ha="left", fontsize=9.5)
    ax.set_yticks(range(len(rows)),
                  [f"gasLimit {r['gas_limit']:,} × maxFeePerGas {r['max_fee_gwei']} gwei" for r in rows])
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlim(1e-4, 1)
    ax.set_xlabel("上限分の額 = gasLimit × maxFeePerGas（ETH、対数）")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(2.6, -0.85)
    save(fig, "ethereum-transaction_reserve.webp")


def basefee_rise():
    """Base fee when every block is full: x1.125 per block (EIP-1559), from 10 gwei."""
    start, cap = 10.0, 30.0
    blocks = list(range(0, 13))
    fees = [start * 1.125 ** n for n in blocks]
    first = next(n for n, f in zip(blocks, fees) if f > cap)
    fig, ax = plt.subplots(figsize=(8.0, 3.4))
    colors = [RED if n >= first else GRAY for n in blocks]
    ax.bar(blocks, fees, color=colors, width=0.7)
    ax.axhline(cap, color=BLUE, ls="--", lw=1.4)
    ax.text(0, cap + 0.8, f"maxFeePerGas {cap:.0f} gwei（送った時の 3 倍）", color=BLUE, fontsize=10, ha="left")
    for n, f in zip(blocks, fees):
        ax.text(n, f + 0.4, f"{f:.1f}", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(blocks)
    ax.set_xticklabels([f"{n}\n{n * 12} 秒" if n % 2 == 0 else f"{n}" for n in blocks])
    ax.set_xlabel("満杯のブロックが続いた数（1 ブロック 12 秒）")
    ax.set_ylabel("base fee の値（gwei）")
    ax.set_ylim(0, max(fees) * 1.15)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(f"1 ブロックごとに 1.125 倍。{first} ブロック目（約 {first * 12} 秒）で上限を超える（赤）",
                 fontsize=11, loc="left")
    save(fig, "ethereum-transaction_basefee_rise.webp")


def nested():
    """A failed inner call: the caller ignores it (status 1) or sees it and reverts (status 0)."""
    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    ax.set_xlim(0, 9.6)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    rows = (
        (2.45, "トップレベルの実行：中の失敗を受け流す", "③ 戻り値を見ず\n最後まで進む",
         "status 1\n成功として残る", GREEN_PALE, GREEN),
        (0.15, "トップレベルの実行：中の失敗を見て止める", "③ 失敗を見て\nREVERT で中止",
         "status 0\n状態の変更を\n取り消す", RED_PALE, RED),
    )
    for y, title, step3, result, rfc, rec in rows:
        ax.add_patch(FancyBboxPatch((0.1, y), 7.2, 1.95, boxstyle="round,pad=0.02,rounding_size=0.1",
                                    facecolor=GRAY_PALE, edgecolor=SUB, lw=1.2))
        ax.text(0.3, y + 1.68, title, ha="left", va="center", fontsize=11)
        by, bh = y + 0.2, 1.15
        mid = by + bh / 2
        box(ax, 0.3, by, 1.7, bh, "① 処理を\n始める", BLUE_PALE, BLUE, 11)
        box(ax, 2.45, by, 2.3, bh, "② 別のコントラクト\nを呼ぶ\n× 中で失敗", RED_PALE, RED, 11, ls="--")
        box(ax, 5.2, by, 1.9, bh, step3, BLUE_PALE, BLUE, 11)
        arrow(ax, 2.05, mid, 2.4, mid)
        arrow(ax, 4.8, mid, 5.15, mid)
        arrow(ax, 7.15, mid, 7.75, mid)
        box(ax, 7.8, by, 1.7, bh, result, rfc, rec, 11)
    save(fig, "ethereum-transaction_nested.webp")


if __name__ == "__main__":
    deversifi()
    byte_layout()
    recover()
    fee_split()
    reserve()
    nested()
    basefee_rise()
