"""Generate the figures of the Gas / EIP-1559 note.

python3 figures.py
  -> images/gas-eip-1559_concept.webp   （手書きの SVG。使用量と次の base fee）
  -> images/gas-eip-1559_auction.webp   （手書きの SVG。London 以前と EIP-1559 の支払い）
  -> images/gas-eip-1559_measured.webp  （matplotlib。lab/output/output.txt の実測値）
  -> images/gas-eip-1559_limits.webp    （手書きの SVG。取引の gasLimit とブロックの gas 上限）
  -> images/gas-eip-1559_split.webp     （手書きの SVG。base fee と priority fee の分け方と行き先）
  -> images/gas-eip-1559_pool.webp      （手書きの SVG。上限を下回った取引の Anvil と geth の扱い）
SVG は Chrome の headless で 2 倍の解像度に描き、matplotlib は dpi 200 の PNG にしてから、
どちらも Pillow で WebP にする。
"""

import re
import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED, RED_PALE = "#e15759", "#fbe3e3"
NEUTRAL = "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def to_webp(png, name):
    (HERE / "images").mkdir(exist_ok=True)
    Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


class Svg:
    def __init__(self, title, w=960, h=540):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
            f'markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/>'
            '</marker></defs>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>'
                      f'{escape(s)}</text>')

    def rect(self, x, y, w, h, fill, stroke, sw=2, dash=False, rx=6):
        d = ' stroke-dasharray="7 5"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=INK, sw=2, arrow=True, dash=False):
        m = ' marker-end="url(#ar)"' if arrow else ""
        d = ' stroke-dasharray="8 6"' if dash is True else (f' stroke-dasharray="{dash}" stroke-linecap="round"' if dash else "")
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                      f'stroke-width="{sw}"{m}{d}/>')

    def save(self, name):
        svg_text = "\n".join(self.p + ["</svg>"]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text(svg_text, encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            to_webp(png, name)


def concept():
    """How full the parent block is decides the next base fee (x1.125, x1, x0.875)."""
    s = Svg("満杯のブロックの次は base fee が 1.125 倍、target ちょうどなら 1 倍、空なら 0.875 倍になる")
    top, bottom = 70, 400          # ブロックの箱（gas の上限）の上端と下端
    height = bottom - top
    mid = top + height / 2         # target（上限の半分）
    unit = 150                     # 今の base fee を表す棒の高さ
    groups = [("満杯", 1.0, 1.125, "×1.125"), ("target ちょうど", 0.5, 1.0, "×1"), ("空", 0.0, 0.875, "×0.875")]
    for i, (label, used, ratio, tag) in enumerate(groups):
        x0 = 50 + i * 310
        # ブロックの箱と使った gas
        s.rect(x0, top, 100, height, NEUTRAL, SUB, rx=4)
        if used:
            h = height * used
            s.rect(x0, bottom - h, 100, h, BLUE_PALE, BLUE, rx=4)
        s.line(x0 - 6, mid, x0 + 106, mid, INK, 2, arrow=False, dash=True)
        s.text(x0 + 115, bottom + 46, label, 26)
        # 次の base fee の棒（点線は今の base fee）
        bx = x0 + 170
        s.line(x0 + 112, mid, bx - 10, mid, INK, 2)
        bh = unit * ratio
        s.rect(bx, bottom - bh, 60, bh, OCHRE_PALE, OCHRE, rx=4)
        s.line(bx - 8, bottom - unit, bx + 68, bottom - unit, INK, 3, arrow=False, dash="0.1 7")
        s.text(bx + 74, bottom - unit + 7, "今", 18, anchor="start", cls="sub")
        s.text(bx + 30, min(bottom - max(bh, unit) - 16, mid - 36), tag, 26)
    s.text(50, top - 24, "灰の箱 = ブロックの gas 上限、青 = 使った gas、破線 = target（上限の半分）", 22, anchor="start", cls="sub")
    s.text(480, 520, "黄土の棒 = 次の base fee、点線 = 今の base fee", 22, cls="sub")
    s.save("gas-eip-1559_concept.webp")


def auction():
    """Before London everyone pays their own bid; with EIP-1559 everyone pays the same base fee plus a tip."""
    s = Svg("London 以前は各自の入札額を払い全額が採掘者に渡る。EIP-1559 では全員が同じ base fee を払って焼却され、tip だけが提案者に渡る")
    base_y = 430
    bids = [210, 150, 290, 180, 240]
    tips = [14, 8, 24, 10, 18]
    base = 120
    # 左: London 以前
    s.text(240, 50, "London 以前（gasPrice）", 28)
    for i, b in enumerate(bids):
        x = 70 + i * 70
        s.rect(x, base_y - b, 48, b, BLUE_PALE, BLUE, rx=3)
    s.text(240, base_y + 40, "各自の入札額をそのまま払う", 24)
    s.text(240, base_y + 76, "全額が採掘者へ", 22, cls="sub")
    # 右: EIP-1559
    s.text(700, 50, "EIP-1559", 28)
    for i, (b, t) in enumerate(zip(bids, tips)):
        x = 520 + i * 70
        s.rect(x, base_y - b, 48, b, "#ffffff", SUB, sw=1.5, dash=True, rx=3)   # maxFeePerGas の枠
        s.rect(x, base_y - base, 48, base, OCHRE_PALE, OCHRE, rx=3)            # base fee
        s.rect(x, base_y - base - t, 48, t, BLUE_PALE, BLUE, rx=2)             # priority fee
    s.line(505, base_y - base, 858, base_y - base, OCHRE, 2, arrow=False, dash=True)
    s.text(731, base_y - bids[2] - 12, "書いた上限（払わない）", 18, cls="sub")
    s.text(864, base_y - base + 8, "base fee", 22, anchor="start", cls="sub")
    s.text(700, base_y + 40, "同じ base fee + 各自の tip", 24)
    s.text(700, base_y + 76, "base fee は焼却、tip は提案者へ", 22, cls="sub")
    s.line(480, 80, 480, 500, "#cccccc", 2, arrow=False)
    s.save("gas-eip-1559_auction.webp")


def limits():
    """Two ceilings: gasLimit stops one transaction, the block gas limit caps the sum of transactions."""
    s = Svg("取引は命令ごとの gas を積み上げ、送り主が書いた gasLimit に達すると実行を止める。"
            "ブロックは取引の gas の合計を block gas limit まで詰める", h=430)
    x0, x1 = 210, 780
    # 上段: 取引 1 件
    y = 70
    s.text(40, y + 40, "取引 1 件", 26, anchor="start")
    s.rect(x0, y, x1 - x0, 64, "#ffffff", SUB)
    segs = [("ADD 3", 100), ("SSTORE 22,100", 200), ("ADD 3", 100), ("…", 170)]
    x = x0
    for label, w in segs:
        s.rect(x + 3, y + 6, w - 6, 52, BLUE_PALE, BLUE, rx=4)
        s.text(x + w / 2, y + 41, label, 20)
        x += w
    s.line(x1, y - 14, x1, y + 78, INK, 3, arrow=False)
    s.text(x1 + 12, y + 40, "使い切ったら", 20, anchor="start")
    s.text(x1 + 12, y + 66, "実行を止める", 20, anchor="start")
    s.text(x1, y + 106, "gasLimit（送り主が取引に書く上限）", 20, anchor="end", cls="sub")
    # 下段: ブロック 1 つ
    y = 250
    s.text(40, y + 40, "ブロック 1 つ", 26, anchor="start")
    s.rect(x0, y, x1 - x0, 64, "#ffffff", SUB)
    x = x0
    for i, w in enumerate((120, 70, 150, 90, 100)):
        s.rect(x + 3, y + 6, w - 6, 52, BLUE_PALE, BLUE, rx=4)
        s.text(x + w / 2, y + 41, f"取引 {i + 1}", 20)
        x += w
    s.line(x1, y - 14, x1, y + 78, INK, 3, arrow=False)
    s.text(x1, y + 106, "block gas limit（全ノードが実行し直す量の上限）", 20, anchor="end", cls="sub")
    s.text(40, 410, "箱の幅は gas の量に比例しない", 18, anchor="start", cls="sub")
    s.save("gas-eip-1559_limits.webp")


def split():
    """How the per-gas price is split into base fee and priority fee, for three senders at base fee 4.11 gwei."""
    s = Svg("base fee が 4.11 gwei のブロックで、3 人の送り主が 1 gas あたりに払う額。"
            "上限 10 gwei なら base fee と tip 1 gwei を払う。上限 5 gwei なら tip は残りの 0.89 gwei に減る。"
            "上限 2 gwei は base fee に届かず、ブロックに入れられない。base fee は焼却、tip は提案者へ", w=1040, h=560)
    scale = 36          # 1 gwei あたりの高さ
    base_y = 440
    base = 4.11
    cases = [("上限に余裕がある", 10.0, 1.0), ("上限に余裕が無い", 5.0, 1.0), ("上限が base fee 未満", 2.0, 1.0)]
    for i, (title, max_fee, max_tip) in enumerate(cases):
        cx = 140 + i * 250
        x = cx - 45
        s.text(cx, 40, title, 24)
        s.text(cx, 70, f"maxFeePerGas {max_fee:g} gwei", 18, cls="sub")
        s.rect(x, base_y - max_fee * scale, 90, max_fee * scale, "#ffffff", SUB, sw=1.5, dash=True, rx=3)
        if max_fee >= base:
            tip = min(max_tip, max_fee - base)
            s.rect(x, base_y - base * scale, 90, base * scale, OCHRE_PALE, OCHRE, rx=3)
            s.rect(x, base_y - (base + tip) * scale, 90, tip * scale, BLUE_PALE, BLUE, rx=3)
            s.text(x + 104, base_y - (base + tip / 2) * scale + 7, f"tip {tip:.2f} gwei", 20, anchor="start")
            s.text(cx, base_y + 36, f"払う額 {base + tip:.2f} gwei", 22)
        else:
            s.text(cx, base_y - max_fee * scale / 2 + 7, "届かない", 18, cls="sub")
            s.text(cx, base_y + 36, "ブロックに入れられない", 22)
    s.line(30, base_y - base * scale, 700, base_y - base * scale, OCHRE, 2, arrow=False, dash=True)
    s.text(706, base_y - base * scale + 7, "base fee 4.11 gwei", 18, anchor="start", cls="sub")
    s.line(30, base_y, 740, base_y, SUB, 1.5, arrow=False)
    # 行き先
    s.rect(815, 130, 215, 80, BLUE_PALE, BLUE)
    s.text(922, 164, "tip", 22)
    s.text(922, 192, "ブロックの提案者へ", 18)
    s.rect(815, 340, 215, 80, OCHRE_PALE, OCHRE)
    s.text(922, 374, "base fee", 22)
    s.text(922, 402, "焼却（誰にも渡らない）", 18)
    s.text(520, 520, "tip = min(maxPriorityFeePerGas 1 gwei, maxFeePerGas − base fee)。点線の枠の残りは払わない",
           18, cls="sub")
    s.save("gas-eip-1559_split.webp")


def pool():
    """What happens to a transaction whose max fee is below the base fee: Anvil 1.7.1 vs geth v1.17.10."""
    s = Svg("maxFeePerGas が base fee を下回った取引の扱い。Anvil 1.7.1 はブロックを作る時に検証して失敗した取引を "
            "mempool から取り除く。geth v1.17.10 はブロックの候補から外すだけで mempool に残し、base fee が下がれば候補に戻す",
            h=400)
    def box(x, y, w, label, sub="", fill=NEUTRAL, stroke=SUB):
        s.rect(x, y, w, 80, fill, stroke)
        s.text(x + w / 2, y + (36 if sub else 48), label, 20)
        if sub:
            s.text(x + w / 2, y + 62, sub, 17, cls="sub")
    for y, name in ((60, "Anvil 1.7.1"), (250, "geth v1.17.10")):
        s.text(30, y + 48, name, 22, anchor="start")
    # Anvil
    box(190, 60, 170, "mempool", "受け付けて置く")
    s.line(360, 100, 404, 100)
    box(406, 60, 270, "ブロックを作る時に検証", "maxFeePerGas < base fee で失敗")
    s.line(676, 100, 712, 100)
    box(714, 60, 230, "無効として取り除く", "その後も戻らない", RED_PALE, RED)
    # geth
    box(190, 250, 170, "mempool", "受け付けて置く")
    s.line(360, 290, 404, 290)
    box(406, 250, 270, "候補から外す", "base fee で絞り込む")
    s.line(676, 290, 712, 290)
    box(714, 250, 230, "mempool に残る", "", GREEN_PALE, GREEN)
    s.p.append(f'<path d="M829,250 C829,206 275,206 275,246" fill="none" stroke="{SUB}" stroke-width="2" '
               'stroke-dasharray="8 6" marker-end="url(#ar)"/>')
    s.text(552, 200, "base fee が下がれば、また候補になる", 18, cls="sub")
    s.text(480, 380, "どちらも、maxFeePerGas が base fee 未満の取引をブロックに入れない点は同じ（プロトコルの規則）", 18,
           cls="sub")
    s.save("gas-eip-1559_pool.webp")


def parse_output():
    rows = []
    pat = re.compile(r"^(target|full|empty)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s+(\d+)")
    for line in (HERE / "lab" / "output" / "output.txt").read_text().splitlines():
        if line.startswith("== (2)"):
            break
        m = pat.match(line)
        if m:
            phase, num, _txs, used, fee, exp = m.groups()
            rows.append((phase, int(num), float(used), int(fee) / 1e9, int(exp) / 1e9))
    return rows


def measured():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Noto Sans CJK JP", "svg.fonttype": "path", "font.size": 11,
                         "axes.edgecolor": SUB, "axes.labelcolor": INK, "xtick.color": SUB, "ytick.color": SUB})
    rows = parse_output()
    num = [r[1] for r in rows]
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(8.0, 5.4), sharex=True, facecolor="#ffffff",
                                 gridspec_kw={"height_ratios": [3, 1.1], "hspace": 0.08})
    # 段の塗り分け
    spans = {"target": (0.5, 3.5, "target"), "full": (3.5, 15.5, "満杯"), "empty": (15.5, 27.5, "混雑が止む")}
    for key, (a, b, label) in spans.items():
        if key == "full":
            ax.axvspan(a, b, color=OCHRE_PALE, lw=0)
            bx.axvspan(a, b, color=OCHRE_PALE, lw=0)
        ax.text((a + b) / 2, 5.68, label, ha="center", va="center", color=SUB, fontsize=11)
    ax.plot(num, [r[4] for r in rows], color=BLUE, lw=2, label="EIP-1559 の式（親ブロックから計算）", zorder=2)
    ax.scatter(num, [r[3] for r in rows], s=22, color=INK, label="Anvil の実測", zorder=3)
    ax.axhline(2, color=SUB, ls="--", lw=1.2)
    ax.axhline(5, color=SUB, ls="--", lw=1.2)
    ax.text(0.6, 2.08, "Alice の上限 2 gwei", ha="left", va="bottom", color=SUB, fontsize=10)
    ax.text(27.4, 4.82, "Carol の上限 5 gwei", ha="right", va="top", color=SUB, fontsize=10)
    fee16 = dict((r[1], r[3]) for r in rows)[16]
    ax.scatter([16], [fee16], s=120, facecolors="none", edgecolors=BLUE, lw=2, zorder=4)
    ax.annotate("16: Carol が入る", (16, fee16), (17.2, 4.25), color=INK, fontsize=10,
                arrowprops={"arrowstyle": "-", "color": SUB, "lw": 1})
    ax.scatter([16], [2], marker="x", s=70, color=RED, lw=2, zorder=4)
    ax.annotate("16: Alice が消える", (16, 2), (17.2, 1.35), color=INK, fontsize=10,
                arrowprops={"arrowstyle": "-", "color": SUB, "lw": 1})
    ax.set_ylim(0, 5.95)
    ax.set_ylabel("base fee（gwei）")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.8), frameon=False, fontsize=10)
    for a in (ax, bx):
        a.spines[["top", "right"]].set_visible(False)
        a.set_xlim(0.3, 27.7)
    bx.bar(num, [r[2] for r in rows], width=0.7, color=BLUE_PALE, edgecolor=BLUE, lw=1)
    bx.axhline(50, color=INK, ls="--", lw=1)
    bx.text(0.45, 58, "target 50%", color=SUB, fontsize=9, va="bottom")
    bx.set_ylim(0, 110)
    bx.set_yticks([0, 50, 100])
    bx.set_ylabel("使用率（%）")
    bx.set_xlabel("ブロック番号")
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff", bbox_inches="tight", pad_inches=0.15)
        to_webp(png, "gas-eip-1559_measured.webp")
    plt.close(fig)


if __name__ == "__main__":
    concept()
    auction()
    measured()
    limits()
    split()
    pool()
