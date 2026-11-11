"""Generate the figures of the reentrancy note.

python3 figures.py  ->  images/reentrancy_callstack.webp, images/reentrancy_balance.webp,
                        images/reentrancy_readonly.webp
- callstack: 手書きの SVG を Chrome の headless で 2 倍の解像度に描いて WebP にする
- readonly: 手書きの SVG。Curve の remove_liquidity の途中で、他のプロジェクトが価格を読む流れ
- balance: lab/output/results.json（lab/run.py の実測）から matplotlib で描く
"""

import io
import json
import subprocess
import tempfile
from html import escape
from pathlib import Path

import matplotlib
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED, RED_PALE = "#e15759", "#fbe3e3"
NEUTRAL = "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, title, w=960, h=540):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/>'
            '</marker></defs>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls="", fill=None):
        c = f' class="{cls}"' if cls else ""
        f = f' style="fill:{fill}"' if fill else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}{f}>'
                      f'{escape(s)}</text>')

    def rect(self, x, y, w, h, fill, stroke, sw=2, dash=False, rx=8):
        d = ' stroke-dasharray="7 5"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=INK, sw=2, arrow=True):
        m = ' marker-end="url(#ar)"' if arrow else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                      f'stroke-width="{sw}"{m}/>')

    def cross(self, x, y, r=11, color=RED):
        for dx in (-r, r):
            self.p.append(f'<line x1="{x - r}" y1="{y - dx}" x2="{x + r}" y2="{y + dx}" '
                          f'stroke="{color}" stroke-width="4" stroke-linecap="round"/>')

    def save(self, name):
        (HERE / "images").mkdir(exist_ok=True)
        svg_text = "\n".join(self.p + ["</svg>"]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text(svg_text, encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def callstack():
    """Nested frames: every withdraw reads the balance before any '= 0' runs."""
    s = Svg("銀行の withdraw と攻撃側の receive が交互に入れ子になり、どの withdraw も 0 になる前の残高 1 ETH を読む。"
            "残高を 0 にする処理は、深い呼び出しから順に戻る時に実行される", h=570)
    top, hgt, gap, step = 52, 50, 16, 30
    rows = [("bank", "銀行の withdraw（1 回目）"), ("attacker", "攻撃側の receive"),
            ("bank", "銀行の withdraw（2 回目）"), ("attacker", "攻撃側の receive"),
            ("bank", "銀行の withdraw（3 回目）"), ("more", "… 11 回目まで")]
    for d, (kind, label) in enumerate(rows):
        x0, x1 = 40 + d * step, 920 - d * step
        y = top + d * (hgt + gap)
        if kind == "bank":
            s.rect(x0, y, x1 - x0, hgt, BLUE_PALE, BLUE)
            s.text(x0 + 16, y + 33, "1 ETH を読む", 21, anchor="start")
            s.text(x1 - 16, y + 33, "残高を 0 にする", 19, anchor="end", cls="sub")
        elif kind == "attacker":
            s.rect(x0, y, x1 - x0, hgt, OCHRE_PALE, OCHRE)
        else:
            s.rect(x0, y, x1 - x0, hgt, NEUTRAL, SUB, dash=True)
        s.text(480 + (14 if kind == "bank" else 0), y + 33, label, 21, cls="sub" if kind == "more" else "")
        if d < len(rows) - 1:  # 次の段へ制御が移る矢印（送金、または呼び直し）
            ax = x0 + step + 30
            s.line(ax, y + hgt, ax, y + hgt + gap - 1, INK, 2)
    s.line(40, 26, 920, 26, SUB, 2)
    s.text(46, 18, "時間", 18, anchor="start", cls="sub")
    s.text(480, 466 + 24, "どの withdraw も、まだ 0 になっていない残高 1 ETH を読んで送る", 24)
    s.text(480, 506 + 24, "右端の「残高を 0 にする」は、深い呼び出しから順に戻る時に実行される", 24, cls="sub")
    s.save("reentrancy_callstack.webp")


def readonly():
    """Read-only reentrancy: during remove_liquidity, another project reads get_virtual_price mid-update."""
    s = Svg("Curve のプールの remove_liquidity は、LP トークンを焼いた後に ETH を先に送り、もう一方のトークンを後で送る。"
            "ETH を受け取った攻撃側のコードは、その間に他のプロジェクトの関数を呼び、そのプロジェクトは"
            "通常より高い get_virtual_price を価格として読む", h=470)
    steps = [("① LP トークンを焼く", "総量が減る"), ("② ETH を送る", "受け手のコードが動く"),
             ("③ もう一方のトークンを送る", "残高と総量が合う")]
    xs = [30, 340, 650]
    for (l1, l2), x in zip(steps, xs):
        s.rect(x, 70, 284, 80, BLUE_PALE, BLUE)
        s.text(x + 142, 104, l1, 20)
        s.text(x + 142, 132, l2, 18, cls="sub")
    s.line(314, 110, 338, 110)
    s.line(624, 110, 648, 110)
    s.text(40, 46, "Curve のプールの remove_liquidity", 22, anchor="start")
    # 合っていない区間
    s.rect(340, 168, 284, 34, RED_PALE, RED, sw=1.5, rx=4)
    s.text(482, 191, "残高と総量が合っていない", 18)
    # 攻撃側と他のプロジェクト
    s.line(480, 202, 480, 268)
    s.rect(330, 270, 300, 70, OCHRE_PALE, OCHRE)
    s.text(480, 300, "攻撃側の receive", 21)
    s.text(480, 326, "他のプロジェクトを呼ぶ", 18, cls="sub")
    s.line(630, 305, 668, 305)
    s.rect(670, 260, 260, 90, NEUTRAL, SUB)
    s.text(800, 290, "他のプロジェクト", 21)
    s.text(800, 316, "get_virtual_price を読む", 18, cls="sub")
    s.text(800, 340, "→ 通常より高い値", 18)
    s.text(480, 400, "ロックの無い view 関数は、呼び出しの途中の値をそのまま返す", 20, cls="sub")
    s.text(480, 432, "誤った値で動くのは、値を読んだ他のプロジェクトの側", 20, cls="sub")
    s.save("reentrancy_readonly.webp")


def balance():
    """Bank balance after each ETH arrival at the attacker (measured on Anvil)."""
    res = json.loads((HERE / "lab" / "output" / "results.json").read_text())["trajectory_wei"]
    vul = [v / 1e18 for v in res["VulnerableBank"]]
    safe = [v / 1e18 for v in res["CeiBank"]]
    assert res["CeiBank"] == res["GuardedBank"] == res["TransientGuardedBank"]

    plt.rcParams.update({"font.family": "Noto Sans CJK JP", "svg.fonttype": "path", "font.size": 12})
    fig, ax = plt.subplots(figsize=(8, 4.5))
    xs = list(range(len(vul)))
    ax.step(xs, vul, where="post", color=OCHRE, lw=3, label="残高を減らす前に送る銀行")
    ax.step(range(len(safe)), safe, where="post", color=BLUE, lw=3,
            label="CEI 版・ロック版 2 種（3 つとも同じ値）")
    ax.plot([len(safe) - 1, len(vul) - 1], [safe[-1], safe[-1]], color=BLUE, lw=3, ls=(0, (1, 2)))
    ax.scatter([len(vul) - 1], [0], marker="x", s=160, color=RED, lw=3, zorder=5)
    ax.annotate("被害者の預け金 10 ETH も抜かれる", (len(vul) - 1, 0), (3.2, 1.0),
                color=INK, fontsize=12, arrowprops=dict(arrowstyle="-", color=SUB))
    ax.annotate("2 回目の withdraw が拒否され、\n攻撃者は自分の 1 ETH だけ受け取る", (1, 10), (2.2, 10.6),
                color=INK, fontsize=12, arrowprops=dict(arrowstyle="-", color=SUB))
    ax.set_xlabel("攻撃側に ETH が届いた回数（1 回の取引の中）", color=INK)
    ax.set_ylabel("銀行の ETH 残高", color=INK)
    ax.set_xlim(-0.3, len(vul) - 0.5)
    ax.set_ylim(-0.6, 12.6)
    ax.set_xticks(xs)
    ax.set_yticks(range(0, 13, 2))
    ax.tick_params(colors=SUB)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(SUB)
    ax.grid(axis="y", color="#e6e6e6")
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.84), frameon=False, labelcolor=INK)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff")
    plt.close(fig)
    Image.open(buf).convert("RGB").save(HERE / "images" / "reentrancy_balance.webp", "WEBP",
                                        quality=90, method=6)


if __name__ == "__main__":
    callstack()
    readonly()
    balance()
