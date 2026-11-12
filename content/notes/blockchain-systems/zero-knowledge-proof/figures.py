"""Zero-Knowledge Proof のノートの図を作る。

実行: python3 figures.py  -> images/*.webp

図の数値は lab/output/ の実験の出力（schnorr.json、iszero.txt、bench.tsv）から読む。
環境を変えたら、先に lab の実験を走らせ直す。

- cover_figure(): 表紙。Fiat-Shamir のチャレンジに R を入れない時と、制約が 1 つ足りない回路で、偽の証明が通った数
- order_figure(): 本物の対話・シミュレーター・R を入れない Fiat-Shamir で、R・c・s が決まる順
- survivors_figure(): 動く図。秘密鍵を知らない 1000 人が、1 ビットのチャレンジのラウンドごとに減る様子（1 ラウンドを 0.8 秒ずつ表示）
- circuit_figure(): y = (x² + 1)² + 1 を回路にした形と、各ステップの制約に値を当てはめた結果
- iszero_figure(): x = 5、inv = 0、out = 1 という値が、2 つの制約をそれぞれ満たすか
- bench_figure(): 計算の回数 N と、証明を作る時間・検証の時間・計算をやり直す時間
"""

import csv
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "lab" / "output"
IMG = HERE / "images"
INK, SUB, FILL, LINE = "#1f1f1f", "#666666", "#f2f2f2", "#9a9a9a"
ACCENT, ACCENT_PALE = "#4e79a7", "#e3ecf5"
RED, RED_PALE = "#c0392b", "#fbe3e3"
JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["font.size"] = 11
plt.rcParams["axes.unicode_minus"] = False


def save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(IMG / name, "WEBP", quality=90, method=6)


def frac(s):
    a, b = s.split("/")
    return int(a), int(b)


def cover_figure():
    r = json.loads((OUT / "schnorr.json").read_text())
    iz = (OUT / "iszero.txt").read_text()
    bug_ok = "iszero_bug cheat" in iz and 'iszero_bug cheat: 公開値 [out, x] = ["1","5"]  検証 OK!' in iz
    ok_ng = 'iszero_ok 偽の witness: 公開値 [out, x] = ["1","5"]  検証 Invalid proof' in iz
    assert bug_ok and ok_ng, "iszero.txt が想定と違う"
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6), gridspec_kw={"width_ratios": [1.15, 1]})
    # 左: Schnorr の Fiat-Shamir
    ax = axes[0]
    weak, n = frac(r["forged_weak"])
    strong, _ = frac(r["forged_strong"])
    labels = ["チャレンジのハッシュに\nR を入れない", "チャレンジのハッシュに\nR を入れる"]
    vals = [weak, strong]
    bars = ax.barh(labels, vals, color=[RED, ACCENT], height=0.55)
    ax.set_xlim(0, n * 1.35)
    ax.set_xticks([0, 250, 500, 750, 1000])
    ax.invert_yaxis()
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for b, v in zip(bars, vals):
        ax.text(v + n * 0.02, b.get_y() + b.get_height() / 2, f"{v} / {n}", va="center", color=INK)
    ax.set_title("秘密鍵を知らずに作った Schnorr の証明が\n検証を通った数", fontsize=12, color=INK, loc="left")
    ax.set_xlabel("個", color=SUB)
    # 右: circom の IsZero
    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("x = 5 を「0 と等しい」とした\nGroth16 で検証した結果", fontsize=12, color=INK, loc="left")
    rows = [("制約が 1 つ足りない回路", "通る（OK!）", RED, RED_PALE, 6.6),
            ("制約がそろった回路", "通らない", ACCENT, ACCENT_PALE, 2.4)]
    for name, res, c, pale, y in rows:
        ax.add_patch(FancyBboxPatch((0.2, y - 1.3), 9.4, 2.6, boxstyle="round,pad=0.05,rounding_size=0.3",
                                    facecolor=pale, edgecolor=c, linewidth=1.2))
        ax.text(0.6, y + 0.45, name, fontsize=11, color=INK, va="center")
        ax.text(0.6, y - 0.6, res, fontsize=15, color=c, va="center")
    fig.tight_layout()
    save(fig, "zkp_cover.webp")


def order_figure():
    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    ax.set_xlim(0, 30)
    ax.set_ylim(0, 12.6)
    ax.axis("off")
    cols = [
        (0.3, "本物の対話", "秘密鍵 x を知る証明者と、検証者", [
            ("1", "k を選び R = k·G を送る", INK),
            ("2", "検証者がチャレンジ c を返す", ACCENT),
            ("3", "s = k + c·x を返す（x が要る）", INK),
        ], "c は R の後に決まる"),
        (10.3, "シミュレーター", "x を知らない人が、1 人で記録を作る", [
            ("1", "チャレンジ c を自分で決める", ACCENT),
            ("2", "答え s を適当に決める", INK),
            ("3", "R = s·G − c·P を逆算する", INK),
        ], "c を先に知っていれば x は要らない"),
        (20.3, "R を入れない Fiat-Shamir", "チャレンジを c = H(P, m) で作る", [
            ("1", "c = H(P, m) を計算する", RED),
            ("2", "答え s を適当に決める", INK),
            ("3", "R = s·G − c·P を逆算する", INK),
        ], "誰でも c を先に知れる → 偽造できる"),
    ]
    for x0, title, sub, steps, foot in cols:
        is_fs = x0 > 20
        edge = RED if is_fs else LINE
        ax.add_patch(FancyBboxPatch((x0, 0.4), 9.4, 11.7, boxstyle="round,pad=0.05,rounding_size=0.3",
                                    facecolor="#ffffff", edgecolor=edge, linewidth=1.2))
        ax.text(x0 + 0.5, 11.2, title, fontsize=13, color=INK, va="center")
        ax.text(x0 + 0.5, 10.2, sub, fontsize=9.5, color=SUB, va="center")
        for i, (num, text, c) in enumerate(steps):
            y = 8.4 - i * 2.4
            ax.add_patch(FancyBboxPatch((x0 + 0.5, y - 0.8), 8.4, 1.6, boxstyle="round,pad=0.02,rounding_size=0.2",
                                        facecolor=FILL if c == INK else (ACCENT_PALE if c == ACCENT else RED_PALE),
                                        edgecolor="none"))
            ax.text(x0 + 0.9, y, num, fontsize=12, color=c, va="center")
            ax.text(x0 + 1.7, y, text, fontsize=10, color=INK, va="center")
            if i < 2:
                ax.annotate("", xy=(x0 + 4.7, y - 1.55), xytext=(x0 + 4.7, y - 0.85),
                            arrowprops=dict(arrowstyle="->", color=SUB, lw=1))
        ax.text(x0 + 0.5, 1.2, foot, fontsize=10, color=RED if is_fs else SUB, va="center")
    save(fig, "zkp_order.webp")


def survivors_figure():
    r = json.loads((OUT / "schnorr.json").read_text())
    surv = r["survivors"]
    last = next(i for i, v in enumerate(surv) if v == 0)
    S = 2
    W, H = 760 * S, 470 * S
    fjp = ImageFont.truetype(JP, 22 * S)
    fjp_s = ImageFont.truetype(JP, 16 * S)
    fbig = ImageFont.truetype(JP, 30 * S)
    cols, rows = 50, 20
    cell = 13 * S
    gx, gy = 30 * S, 150 * S
    frames, durs = [], []
    for k in range(0, last + 1):
        im = Image.new("RGB", (W, H), "#ffffff")
        d = ImageDraw.Draw(im)
        d.text((30 * S, 18 * S), "秘密鍵を知らない 1000 人が、1 ビットのチャレンジに答え続ける", font=fjp, fill=INK)
        d.text((30 * S, 52 * S), "勘が当たった人だけが次のラウンドへ（1 ラウンドを 0.8 秒ずつ表示）", font=fjp_s, fill=SUB)
        d.text((30 * S, 92 * S), f"ラウンド {k}", font=fbig, fill=INK)
        d.text((230 * S, 92 * S), f"残り {surv[k]} 人", font=fbig, fill=RED if surv[k] else ACCENT)
        if k:
            d.text((450 * S, 100 * S), f"1/2 の {k} 乗 × 1000 = {1000 / 2 ** k:.1f}", font=fjp_s, fill=SUB)
        # 帯: ラウンドの進み
        bx, by, bw = 30 * S, 136 * S, 700 * S
        d.rectangle([bx, by, bx + bw, by + 4 * S], fill=FILL)
        d.rectangle([bx, by, bx + bw * k // last, by + 4 * S], fill=SUB)
        for i in range(1000):
            cx = gx + (i % cols) * (cell + S)
            cy = gy + 10 * S + (i // cols) * (cell + S)
            alive = i < surv[k]
            d.rectangle([cx, cy, cx + cell - S, cy + cell - S], fill=RED if alive else "#e6e6e6")
        d.text((30 * S, 440 * S), "赤 = まだ通っている人（実測。schnorr_zk.py の実験 1）", font=fjp_s, fill=SUB)
        frames.append(im.resize((W // S, H // S), Image.LANCZOS))
        durs.append(800)
    durs[-1] = 3000
    frames[0].save(IMG / "zkp_survivors.webp", "WEBP", save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, quality=80, method=6)


def circuit_figure():
    """y = (x² + 1)² + 1（N = 2）を回路にし、制約に値を当てはめる。値は例として x = 3"""
    x = 3
    t1 = x * x + 1
    y = t1 * t1 + 1
    fig, ax = plt.subplots(figsize=(10.5, 4.9))
    ax.set_xlim(0, 30)
    ax.set_ylim(0, 14)
    ax.axis("off")
    ax.text(0.3, 13.3, "計算 y = (x² + 1)² + 1 を回路にする（x² + 1 を N = 2 回）", fontsize=12.5, color=INK, va="center")

    def wire(x0, y0, name, val):
        ax.add_patch(FancyBboxPatch((x0 - 1.1, y0 - 0.75), 2.2, 1.5, boxstyle="round,pad=0.02,rounding_size=0.2",
                                    facecolor="#ffffff", edgecolor=INK, linewidth=1.0))
        ax.text(x0, y0 + 0.2, name, fontsize=12, color=INK, ha="center", va="center", family="DejaVu Sans Mono")
        ax.text(x0, y0 - 1.25, f"= {val}", fontsize=9.5, color=SUB, ha="center", va="center")

    def gate(x0, y0, label):
        ax.add_patch(plt.Circle((x0, y0), 0.8, facecolor=ACCENT_PALE, edgecolor=ACCENT, linewidth=1.1))
        ax.text(x0, y0, label, fontsize=12, color=ACCENT, ha="center", va="center")

    def arrow(a, b, rad=0.0):
        ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color=SUB, lw=1,
                                                        connectionstyle=f"arc3,rad={rad}"))

    yc = 10.2
    xs = [1.6, 5.4, 8.6, 12.2, 16.0, 19.2, 22.8]
    wire(xs[0], yc, "x", f"{x}（秘密）")
    gate(xs[1], yc, "×")
    gate(xs[2], yc, "+1")
    wire(xs[3], yc, "t1", t1)
    gate(xs[4], yc, "×")
    gate(xs[5], yc, "+1")
    wire(xs[6], yc, "y", f"{y}（公開）")
    for i, (a, b) in enumerate([(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6)]):
        ra = xs[a] + (1.1 if a in (0, 3, 6) else 0.8)
        lb = xs[b] - (1.1 if b in (0, 3, 6) else 0.8)
        if b in (1, 4):
            arrow((ra, yc + 0.3), (lb + 0.1, yc + 0.35), rad=-0.25)
            arrow((ra, yc - 0.3), (lb + 0.1, yc - 0.35), rad=0.25)
        else:
            arrow((ra, yc), (lb, yc))
    ax.text(7.0, 8.0, "制約 1:  t1 = x·x + 1", fontsize=11, color=INK, ha="center", va="center")
    ax.text(17.6, 8.0, "制約 2:  y = t1·t1 + 1", fontsize=11, color=INK, ha="center", va="center")
    for xa, xb in ((4.4, 9.6), (15.0, 20.2)):
        ax.plot([xa, xa, xb, xb], [8.7, 8.5, 8.5, 8.7], color=LINE, lw=1)
    ax.text(25.0, 10.2, "掛け算 1 つにつき\n制約 1 つ", fontsize=10, color=SUB, va="center")

    rows = [
        ("正しい値", f"x = {x},  t1 = {t1},  y = {y}", f"{t1} = {x}·{x} + 1", "満たす", f"{y} = {t1}·{t1} + 1", "満たす", False),
        ("嘘の y", f"x = {x},  t1 = {t1},  y = {y + 1}", f"{t1} = {x}·{x} + 1", "満たす", f"{y + 1} ≠ {t1}·{t1} + 1", "満たさない", True),
    ]
    for i, (name, vals, e1, r1, e2, r2, bad) in enumerate(rows):
        y0 = 5.4 - i * 2.6
        ax.add_patch(FancyBboxPatch((0.3, y0 - 1.0), 29.4, 2.0, boxstyle="round,pad=0.02,rounding_size=0.2",
                                    facecolor=RED_PALE if bad else FILL, edgecolor="none"))
        ax.text(0.8, y0 + 0.4, name, fontsize=11, color=RED if bad else INK, va="center")
        ax.text(0.8, y0 - 0.45, vals, fontsize=9.5, color=SUB, va="center", family="DejaVu Sans Mono")
        ax.text(10.4, y0, "制約 1", fontsize=9.5, color=SUB, va="center")
        ax.text(12.4, y0, e1, fontsize=10.5, color=INK, va="center", family="DejaVu Sans Mono")
        ax.text(17.0, y0, r1, fontsize=10.5, color=ACCENT, va="center")
        ax.text(19.0, y0, "制約 2", fontsize=9.5, color=SUB, va="center")
        ax.text(21.0, y0, e2, fontsize=10.5, color=INK, va="center", family="DejaVu Sans Mono")
        ax.text(26.6, y0, r2, fontsize=10.5, color=RED if bad else ACCENT, va="center")
    ax.text(0.3, 0.5, "値は全て、77 桁の素数で割った余りで計算する（本記事の実験で使う snarkjs の場合）", fontsize=9.5, color=SUB, va="center")
    save(fig, "zkp_circuit.webp")


def iszero_figure():
    fig, ax = plt.subplots(figsize=(10.0, 4.2))
    ax.set_xlim(0, 30)
    ax.set_ylim(0, 12.5)
    ax.axis("off")
    ax.text(0.3, 11.8, "偽の証明者が入れた値:  x = 5,  inv = 0,  out = 1", fontsize=12, color=INK, va="center")
    cols = [(0.3, "制約が 1 つ足りない回路", True), (15.3, "制約がそろった回路", False)]
    for x0, title, bug in cols:
        ax.add_patch(FancyBboxPatch((x0, 0.4), 14.4, 10.0, boxstyle="round,pad=0.05,rounding_size=0.3",
                                    facecolor="#ffffff", edgecolor=RED if bug else ACCENT, linewidth=1.2))
        ax.text(x0 + 0.6, 9.5, title, fontsize=13, color=INK, va="center")
        items = [("制約 1", "out = 1 − x·inv", "1 = 1 − 5·0", "満たす", ACCENT)]
        if bug:
            items.append(("制約 2", "（書いていない）", "見ない", "—", SUB))
        else:
            items.append(("制約 2", "x·out = 0", "5·1 = 5", "満たさない", RED))
        for i, (n, eq, sub, res, c) in enumerate(items):
            y = 7.1 - i * 2.9
            ax.add_patch(FancyBboxPatch((x0 + 0.6, y - 1.1), 13.2, 2.2, boxstyle="round,pad=0.02,rounding_size=0.2",
                                        facecolor=FILL, edgecolor="none"))
            ax.text(x0 + 1.0, y + 0.45, n, fontsize=10, color=SUB, va="center")
            ax.text(x0 + 3.2, y + 0.45, eq, fontsize=11.5, color=INK, va="center", family="DejaVu Sans Mono" if "=" in eq else None)
            ax.text(x0 + 3.2, y - 0.5, sub, fontsize=10, color=SUB, va="center")
            ax.text(x0 + 10.4, y, res, fontsize=12, color=c, va="center")
        verdict = "検証を通る：「5 は 0 と等しい」" if bug else "証明を作れない・通らない"
        ax.text(x0 + 0.6, 1.3, verdict, fontsize=12.5, color=RED if bug else ACCENT, va="center")
    save(fig, "zkp_iszero.webp")


def bench_figure():
    rows = list(csv.DictReader((OUT / "bench.tsv").open(), delimiter="\t"))
    n = [int(x["N"]) for x in rows]
    prove = [float(x["prove_ms"]) for x in rows]
    verify = [float(x["verify_ms"]) for x in rows]
    redo = [float(x["recompute_ms"]) for x in rows]
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    ax.plot(n, prove, "o-", color=INK, label="証明を作る時間")
    ax.plot(n, verify, "s-", color=ACCENT, label="証明を検証する時間")
    ax.plot(n, redo, "^--", color=RED, label="x を知る人が計算をやり直す時間")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_ylim(0.02, 1500)
    ax.set_xticks(n)
    ax.set_xticklabels([f"{v:,}" for v in n])
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_xlabel("計算の回数 N（= 制約の数）", color=INK)
    ax.set_ylabel("時間（ms、対数）", color=INK)
    for x, y in zip(n, prove):
        ax.annotate(f"{y:g}", (x, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=9, color=INK)
    for i, (x, y) in enumerate(zip(n, verify)):
        off = (0, -15) if i == len(n) - 1 else (0, 7)
        ax.annotate(f"{y:g}", (x, y), textcoords="offset points", xytext=off, ha="center", fontsize=9, color=ACCENT)
    for x, y in zip(n, redo):
        ax.annotate(f"{y:g}", (x, y), textcoords="offset points", xytext=(8, -12), ha="left", fontsize=9, color=RED)
    ax.text(0.02, 0.97, "証明の大きさは、どの N でも 256 バイト", transform=ax.transAxes, va="top", fontsize=10.5, color=INK)
    # 線は列ごとに 3 回の最小を取った値なので、同じ回どうしの比較を bench_runs.tsv から数えて添える
    runs = [r for r in csv.DictReader((OUT / "bench_runs.tsv").open(), delimiter="\t") if r["N"] == str(n[-1])]
    slower = sum(float(r["recompute_ms"]) > float(r["verify_ms"]) for r in runs)
    ax.text(0.02, 0.89, f"線は 3 回測った各値の最小。N = {n[-1]:,} を同じ回どうしで比べると、\nやり直す方が検証より遅いのは {len(runs)} 回中 {slower} 回",
            transform=ax.transAxes, va="top", fontsize=9.5, color=SUB)
    ax.grid(True, which="major", color="#e6e6e6")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=10)
    fig.tight_layout()
    save(fig, "zkp_bench.webp")


if __name__ == "__main__":
    IMG.mkdir(exist_ok=True)
    cover_figure()
    order_figure()
    survivors_figure()
    circuit_figure()
    iszero_figure()
    bench_figure()
