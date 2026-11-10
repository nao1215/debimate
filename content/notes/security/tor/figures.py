"""Generate the cover diagram of the Tor note as a hand-written SVG (stdlib only).

concept_figure(): Client, Guard, Middle, Exit and the Web server in one row.
The bands above show what each relay can see (only its neighbours), and the
nested boxes below show one layer of encryption peeled off at each relay.

guard_exposure_figure(): the chance of ever building a circuit whose Guard
and Exit are both the attacker's, from lab/guard_exposure.py (needs matplotlib).

Run: uv run --with matplotlib python content/notes/security/tor/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=4, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


# (name, center x, box width)
NODES = [("Client", 70, 120), ("Guard", 275, 120), ("Middle", 470, 120),
         ("Exit", 660, 120), ("Web サーバー", 858, 184)]


def concept_figure():
    f = Svg(960, 540, "Tor の各リレーに見える範囲と層ごとの暗号化")
    xs = [x for _, x, _ in NODES]

    # Bands: each relay sees only the node before it and the node after it.
    bands = [(xs[0], xs[2], 52, ACCENT, PALE, "Guard が知る範囲"),
             (xs[1], xs[3], 106, SUB, FILL, "Middle が知る範囲"),
             (xs[2], xs[4], 160, ACCENT, PALE, "Exit が知る範囲")]
    for x1, x2, y, stroke, fill, label in bands:
        f.box(x1, y, x2 - x1, 44, fill, stroke, sw=2.5, rx=22)
        f.text((x1 + x2) / 2, y + 31, label, 24)

    # Path and nodes.
    ny, nh = 238, 70
    f.line(xs[0], ny + nh / 2, xs[4], ny + nh / 2, SUB, sw=3)
    for i, (name, x, w) in enumerate(NODES):
        relay = 1 <= i <= 3
        f.box(x - w / 2, ny, w, nh, PALE if relay else FILL,
              ACCENT if relay else SUB, sw=3)
        f.text(x, ny + nh / 2 + 9, name, 26, weight="normal")

    # Nested boxes between nodes: 3, 2, 1, 0 Tor layers left.
    cy = 410
    for i, layers in enumerate((3, 2, 1, 0)):
        cx = (xs[i] + xs[i + 1]) / 2
        for k in range(layers, 0, -1):
            w, h = 70 + 30 * k, 40 + 26 * k
            f.box(cx - w / 2, cy - h / 2, w, h, "#ffffff" if k % 2 else PALE,
                  ACCENT, sw=3, rx=8)
        # The payload past Exit has no Tor layer: a caution area (ochre), not a failure.
        f.box(cx - 32, cy - 20, 64, 40, OCHRE_PALE if layers == 0 else FILL,
              OCHRE if layers == 0 else SUB, sw=3 if layers == 0 else 2, rx=6)
        f.text(cx, cy + 9, "中身", 24, INK)
        label = f"{layers} 層" if layers else "Tor の層なし"
        f.text(cx, 518, label, 24, INK if layers == 0 else SUB,
               weight="normal")

    f.save(HERE / "images" / "tor_concept.svg")


def guard_exposure_figure():
    import sys

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sys.path.insert(0, str(HERE / "lab"))
    import guard_exposure as ge

    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "tor-guard",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    rng = ge.random.Random(ge.SEED)
    sims = {(c, fixed): ge.simulate(c, fixed, rng)
            for c in ge.C_VALUES for fixed in (False, True)}
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ks = list(range(1, ge.CIRCUITS + 1))
    for c, ls in zip(ge.C_VALUES, ("-", "--")):
        for fixed, color, name in ((False, RED, "re-pick Guard every circuit"),
                                   (True, ACCENT, "keep one Guard")):
            exact = [100 * (c * (1 - (1 - c) ** k) if fixed else 1 - (1 - c * c) ** k)
                     for k in ks]
            ax.plot(ks, exact, color=color, lw=2.4, ls=ls, label=f"{name}, c = {c:.2f}")
            sim = sims[(c, fixed)]
            ax.plot(list(sim), [100 * v for v in sim.values()], "o", color=color,
                    ms=6, mfc="white", mew=1.6)
    ax.set_xscale("log")
    ax.set_xlim(1, ge.CIRCUITS)
    ax.set_ylim(0, 102)
    ax.set_xlabel("Circuits built by one user")
    ax.set_ylabel("Users with at least one\ncircuit seen at both ends (%)")
    ax.text(1.3, 88, "lines: exact formula, circles: simulation of 20,000 users",
            color=SUB, fontsize=10)
    ax.legend(loc="center left", frameon=False, fontsize=10, bbox_to_anchor=(0.0, 0.55))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.3, lw=0.6)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "tor_guard_exposure.svg", metadata={"Date": None})
    plt.close(fig)


def relay_early_figure():
    """The 2014 relay early attack: HSDir writes, the attacker's Guard reads."""
    f = Svg(960, 540, "relay early の cell で付けた印を Guard が読む")
    f.parts.insert(3, '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" '
                   'markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" '
                   f'fill="{SUB}"/></marker><marker id="arro" viewBox="0 0 10 10" refX="9" '
                   'refY="5" markerWidth="6" markerHeight="6" orient="auto"><path '
                   f'd="M0,0 L10,5 L0,10 z" fill="{OCHRE}"/></marker></defs>')
    ny, nh = 150, 70
    nodes = [("利用者", 100, FILL, SUB), ("Guard", 340, OCHRE_PALE, OCHRE),
             ("Middle", 570, PALE, ACCENT), ("HSDir", 820, OCHRE_PALE, OCHRE)]
    for name, x, fill, stroke in nodes:
        if stroke == OCHRE:
            f.text(x, ny - 16, "攻撃者のリレー", 24, SUB)
    for (_, x1, _, _), (_, x2, _, _) in zip(nodes, nodes[1:]):
        f.parts.append(f'<line x1="{x1 + 74}" y1="{ny + nh / 2}" x2="{x2 - 76}" '
                       f'y2="{ny + nh / 2}" stroke="{SUB}" stroke-width="3" marker-end="url(#arr)"/>')
    for name, x, fill, stroke in nodes:
        f.box(x - 70, ny, 140, nh, fill, stroke, sw=3)
        f.text(x, ny + nh / 2 + 9, name, 26)
    f.text(820, ny + nh + 36, "descriptor を預かる役", 24, SUB)
    f.text(40, 60, "descriptor を載せる・取りに来る経路", 24, SUB, anchor="start")

    # The mark travels back towards the client as a pattern of cells.
    ry = 340
    f.parts.append(f'<path d="M820,{ny + nh + 52} L820,{ry} L340,{ry} L340,{ny + nh + 6}" '
                   f'fill="none" stroke="{OCHRE}" stroke-width="3" stroke-dasharray="8 6" '
                   'marker-end="url(#arro)"/>')
    pattern = (1, 0, 0, 1, 1, 0, 1, 0)        # 1 = relay early, 0 = relay
    x = 470
    for bit in pattern:
        f.box(x, ry - 17, 34, 34, OCHRE if bit else "#ffffff", OCHRE, sw=2.5, rx=4)
        x += 42
    f.text(605, ry + 52, "relay と relay early の並びで名前を書く", 24, SUB)
    f.box(470, 448, 34, 34, OCHRE, OCHRE, sw=2.5, rx=4)
    f.text(514, 474, "relay early", 24, SUB, anchor="start")
    f.box(680, 448, 34, 34, "#ffffff", OCHRE, sw=2.5, rx=4)
    f.text(724, 474, "relay", 24, SUB, anchor="start")

    # Guard reads the mark and knows the client's IP address.
    f.text(358, 292, "印を読む", 24, anchor="start")
    f.box(30, 420, 380, 76, "#ffffff", RED, sw=2.5)
    f.text(220, 452, "接続元の IP アドレスと", 24)
    f.text(220, 484, "Onion Service が結び付く", 24)
    f.save(HERE / "images" / "tor_relay_early.svg")


if __name__ == "__main__":
    concept_figure()
    guard_exposure_figure()
    relay_early_figure()
