#!/usr/bin/env python3
"""Oracle ノートの図を lab/output/results.json から作る。

Run: python3 content/notes/blockchain-systems/oracle/figures.py
出力: images/ の WebP 3 枚。
- oracle_attack_steps.webp: 同じトランザクションの中の手順ごとに、3 つの取り出し口が返した価格（表紙）
- oracle_crash.webp: 急落の 90 分を、チェーンの時刻の 600 倍速で再生する動く図
- oracle_feed_age.webp: プッシュ型の価格の最後の更新からの経過時間
"""
import io
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "images")
RES = json.load(open(os.path.join(HERE, "lab", "output", "results.json")))

JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_manager.fontManager.addfont(JP)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=JP).get_name()
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

INK, SUB, GRID = "#1f1f1f", "#666666", "#e4e4e4"
SPOT, TWAP, FEED, MARKET = "#e15759", "#4e79a7", "#59a14f", "#9c9c9c"
LAG = "#b07aa1"


def save(fig, name, dpi=200):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(os.path.join(IMG, name), "WEBP", quality=90, method=6)


def fig_attack():
    a = RES["attack"]
    steps = a["spot"]["steps"]
    labels = ["0 開始", "1 フラッシュ\nローン", "2 tETH を\n買う", "3 担保を\n預ける", "4 借りる", "5 tETH を\n売り戻す", "6 返済"]
    x = [s["step"] for s in steps]
    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    ax.plot(x, [s["spot"] for s in steps], color=SPOT, lw=2.6, marker="o", label="spot（プールの価格）")
    ax.plot(x, [s["twap"] for s in steps], color=TWAP, lw=2.6, marker="s", label="TWAP（30 分）")
    ax.plot(x, [s["feed"] for s in steps], color=FEED, lw=1.6, marker="^", ls="--", label="プッシュ型")
    ax.set_xticks(x, labels, fontsize=10)
    ax.set_ylabel("1 tETH の価格（tUSD）", fontsize=11)
    ax.set_ylim(0, 15500)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.grid(axis="y", color=GRID)
    ax.annotate(f"{steps[2]['spot']:,.0f}", (3, steps[3]["spot"]), xytext=(0, -20), textcoords="offset points",
                ha="center", fontsize=11, color=SPOT)
    ax.annotate(f"{steps[5]['spot']:,.0f}", (5, steps[5]["spot"]), xytext=(14, 8), textcoords="offset points",
                ha="left", fontsize=11, color=SPOT)
    ax.text(2.0, 1250, "TWAP とプッシュ型は 3,000 のまま", fontsize=10.5, color=TWAP)
    s, t = a["spot"], a["twap"]
    box = (f"spot を読むレンディング: {s['lending_debt_usd']:,.0f} tUSD を貸し、攻撃者は {s['attacker_profit_usd']:,.0f} tUSD を得た\n"
           f"TWAP・プッシュ型を読むレンディング: {t['revert']['borrowed']:,.0f} tUSD までで、"
           f"返済に {t['revert']['shortfall']:,.0f} tUSD 足りず全部取り消し")
    ax.text(0.0, 15300, box, fontsize=10.5, color=INK, va="top",
            bbox=dict(boxstyle="round,pad=0.5", fc="#f7f7f7", ec="#cfcfcf"))
    ax.legend(loc="center left", bbox_to_anchor=(0.0, 0.55), fontsize=10, frameon=False)
    ax.set_title("同じトランザクションの中で、レンディングが読む価格\n（100 tETH・300,000 tUSD のプールに、手元 0 から借りた 300,000 tUSD を入れる）",
                 fontsize=12, color=INK, loc="left")
    fig.tight_layout()
    save(fig, "oracle_attack_steps.webp")


def crash_frame(rows, upto, summ, final=False):
    t = [r["t"] / 60 for r in rows]
    fig, ax = plt.subplots(figsize=(9.6, 4.8))
    ax.set_xlim(0, 90)
    ax.set_ylim(1900, 3200)
    ax.grid(color=GRID)
    ax.set_xlabel("経過時間（分。12 秒ごとのブロック）", fontsize=11)
    ax.set_ylabel("1 tETH の価格（tUSD）", fontsize=11)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    liq = summ["borrower"]["debt_usd"] / summ["borrower"]["collateral_eth"] / summ["borrower"]["liquidation_threshold"]
    ax.axhline(liq, color=SUB, lw=1, ls=":")
    ax.text(89, liq + 18, f"この価格を下回ると清算できる（{liq:,.0f}）", ha="right", fontsize=10, color=SUB)
    n = upto + 1
    ax.plot(t[:n], [r["market"] for r in rows[:n]], color=MARKET, lw=4.5, alpha=0.6, label="市場（spot もほぼ同じ）")
    ax.plot(t[:n], [r["feed"] for r in rows[:n]], color=FEED, lw=1.8, label="プッシュ型（遅れなし、理想化）")
    ax.plot(t[:n], [r["feed_lag60"] for r in rows[:n]], color=LAG, lw=1.8, ls="--", drawstyle="steps-post",
            label="プッシュ型（書き込みが 60 秒遅れて届く）")
    ax.plot(t[:n], [r["twap"] for r in rows[:n]], color=TWAP, lw=2.6, label="TWAP（30 分）")
    now = rows[upto]
    ax.axvline(now["t"] / 60, color="#bbbbbb", lw=1)
    lf = summ["liquidatable_from"]
    for key, color, tx, ty in (("feed", FEED, 2, 2440), ("twap", TWAP, 36, 3060)):
        p = lf[key]
        if p and p["t"] <= now["t"]:
            ax.plot(p["t"] / 60, p["price_seen"], "o", color=color, ms=8)
            debt = summ["borrower"]["debt_usd"]
            cv = p["collateral_value_at_market"]
            vs = f" < 借入 {debt:,.0f} tUSD" if cv < debt else ""
            ax.annotate(f"{p['t'] / 60:.1f} 分: 清算できるようになる\n担保の市場価値 {cv:,.0f} tUSD{vs}",
                        (p["t"] / 60, p["price_seen"]), xytext=(tx, ty), textcoords="data",
                        fontsize=10, color=color, arrowprops=dict(arrowstyle="-", color=color))
    ax.legend(loc="center right", bbox_to_anchor=(1.0, 0.42), fontsize=10, frameon=False)
    head = (f"経過 {now['t'] / 60:4.1f} 分　市場 {now['market']:,.0f}　プッシュ型 {now['feed']:,.0f}"
            f"（60 秒遅れ {now['feed_lag60']:,.0f}）　TWAP {now['twap']:,.0f}")
    ax.set_title("急落する価格を、レンディングが読む価格はどう追うか（借入 22,000 tUSD・担保 10 tETH）\n" + head,
                 fontsize=12, color=INK, loc="left")
    ax.text(89, 1930, "チェーンの時刻の 90 分を 9 秒で再生（600 倍速）", ha="right", fontsize=9.5, color=SUB)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def fig_crash():
    rows, summ = RES["crash"], RES["crash_summary"]
    idx = list(range(0, len(rows), 15))   # 15 ブロック（3 分）ごとに 1 コマ
    if idx[-1] != len(rows) - 1:
        idx.append(len(rows) - 1)
    frames = [crash_frame(rows, i, summ) for i in idx]
    durs = [300] * (len(frames) - 1) + [3500]
    frames[0].save(os.path.join(IMG, "oracle_crash.webp"), "WEBP", save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, quality=72, method=6)


def fig_feed_age():
    rows, summ = RES["crash"], RES["crash_summary"]
    t = [r["t"] / 60 for r in rows]
    age = [r["feed_age"] / 60 for r in rows]
    fig, ax = plt.subplots(figsize=(9.6, 3.8))
    ax.fill_between(t, 0, age, where=[a > 15 for a in age], color="#fbe3e3", step="post")
    ax.step(t, age, where="post", color=FEED, lw=2)
    ax.axhline(15, color="#e15759", lw=1.2, ls="--")
    ax.text(89, 10.5, "古さの上限を 15 分にした場合、赤い所では読めずに revert", ha="right", fontsize=10, color="#c03d3f")
    ax.axhline(60, color=SUB, lw=1, ls=":")
    ax.text(1, 61.5, "heartbeat（60 分）", fontsize=10, color=SUB)
    ax.axvspan(20, 30, color="#f2f2f2", zorder=0)
    ax.text(25, 40, "急落の 10 分\n（更新 50 回）", ha="center", fontsize=10, color=SUB)
    ax.set_xlim(0, 90)
    ax.set_ylim(0, 68)
    ax.set_xlabel("経過時間（分）", fontsize=11)
    ax.set_ylabel("最後の更新からの経過（分）", fontsize=11)
    ax.grid(axis="y", color=GRID)
    share = summ["share_age_over_900_calm"] * 100
    ax.set_title(f"最後の更新からの経過：揺れを ±0.2% にした 30〜90 分では、{share:.0f}% のブロックで 15 分より古い",
                 fontsize=12, color=INK, loc="left")
    fig.tight_layout()
    save(fig, "oracle_feed_age.webp")


if __name__ == "__main__":
    os.makedirs(IMG, exist_ok=True)
    fig_attack()
    fig_crash()
    fig_feed_age()
