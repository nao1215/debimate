"""Generate the figures of the EVM Opcode History note.

Run: python3 figures.py  -> images/*.webp
Hand-drawn figures are built as SVG with the standard library, rendered with
headless Chrome at 2x and saved as WebP (Pillow). The opcode chart uses
matplotlib (PNG at 200 dpi -> WebP). Numbers come from lab/output/*.json
(written by lab/count_opcodes.sh and lab/eip_graph.py). The only typed values
are the mainnet activation dates, copied from go-ethereum's
params/chainspecs/mainnet.json (ddaa6957) and https://ethereum.org/ethereum-forks/.
"""

from datetime import date
from html import escape
import io
import json
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab" / "output"
IMG = HERE / "images"
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED, RED_PALE = "#e15759", "#fbe3e3"
GRAY_PALE = "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono','Menlo','Consolas',monospace"

GETH = json.loads((LAB / "geth_tables.json").read_text())
GRAPH = json.loads((LAB / "eip_graph.json").read_text())

# Mainnet activation (UTC). Block-number forks: ethereum.org; timestamp forks: mainnet.json.
FORK_DATES = {
    "Frontier": date(2015, 7, 30), "Homestead": date(2016, 3, 14),
    "Tangerine Whistle": date(2016, 10, 18), "Spurious Dragon": date(2016, 11, 22),
    "Byzantium": date(2017, 10, 16), "Constantinople": date(2019, 2, 28),
    "Istanbul": date(2019, 12, 8), "Berlin": date(2021, 4, 15), "London": date(2021, 8, 5),
    "Merge": date(2022, 9, 15), "Shanghai": date(2023, 4, 12), "Cancun": date(2024, 3, 13),
    "Prague": date(2025, 5, 7), "Osaka": date(2025, 12, 3),
}


def to_webp(png, name):
    Image.open(png).convert("RGB").save(IMG / name, "WEBP", quality=90, method=6)


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img"><title>{escape(title)}</title>',
            f"<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}} .mono{{font-family:{MONO}}}</style>",
            '<defs>'
            f'<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
            f'<marker id="ab" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{BLUE}"/></marker>'
            '</defs>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls="", weight=None):
        c = f' class="{cls}"' if cls else ""
        wt = f' font-weight="{weight}"' if weight else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}{wt}>{escape(str(s))}</text>')

    def rect(self, x, y, w, h, fill, stroke, sw=2, rx=8, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=SUB, sw=2.5, arrow=True, dash=None, marker="a"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = f' marker-end="url(#{marker})"' if arrow else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{d}{m}/>')

    def path(self, d, color=SUB, sw=2.5, arrow=True, dash=None, fill="none"):
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        m = ' marker-end="url(#a)"' if arrow else ""
        self.p.append(f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{sw}"{ds}{m}/>')

    def cross(self, x, y, r=12):
        self.p.append(f'<path d="M{x - r} {y - r} L{x + r} {y + r} M{x + r} {y - r} L{x - r} {y + r}" '
                      f'stroke="{RED}" stroke-width="5" stroke-linecap="round"/>')

    def save(self, name):
        svg_text = "\n".join(self.p + ["</svg>"]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text(svg_text, encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            to_webp(png, name)


# 6. Precompiled contracts by the fork that added them (go-ethereum contracts.go).
def precompiles():
    pre = GETH["precompiles"]
    names = {
        "ecrecover": "ecrecover", "sha256hash": "sha256", "ripemd160hash": "ripemd160", "dataCopy": "identity",
        "bigModExp": "modexp", "bn256AddByzantium": "bn254 加算", "bn256AddIstanbul": "bn254 加算",
        "bn256ScalarMulByzantium": "bn254 乗算", "bn256ScalarMulIstanbul": "bn254 乗算",
        "bn256PairingByzantium": "ペアリング", "bn256PairingIstanbul": "ペアリング", "blake2F": "blake2f",
        "kzgPointEvaluation": "KZG 検証", "bls12381G1Add": "G1 加算", "bls12381G1MultiExp": "G1 MSM",
        "bls12381G2Add": "G2 加算", "bls12381G2MultiExp": "G2 MSM", "bls12381Pairing": "ペアリング",
        "bls12381MapG1": "G1 写像", "bls12381MapG2": "G2 写像", "p256Verify": "p256verify",
    }
    seen, columns = set(), []
    for fork in pre:
        new = sorted((a for a in fork["contracts"] if a not in seen), key=lambda a: int(a, 16))
        if new:
            columns.append((fork["fork"], [(a, names[fork["contracts"][a]]) for a in new]))
            seen.update(new)
    label = {"Homestead": "Frontier", "Prague": "Prague"}
    s = Svg(960, 660, "プリコンパイル 18 個を導入したフォークごとに並べた図。Frontier の 4 個、Byzantium の 4 個、Istanbul の 1 個、"
                      "Cancun の 1 個、Prague の BLS12-381 の 7 個、Osaka の P-256 検証")
    cw = 156
    for i, (fork, items) in enumerate(columns):
        x = 12 + i * cw
        s.text(x + cw / 2 - 4, 44, label.get(fork, fork), 24, weight="normal")
        newest = i == len(columns) - 1
        for j, (addr, name) in enumerate(items):
            y = 66 + j * 76
            s.rect(x, y, cw - 10, 68, BLUE_PALE if newest else "#ffffff", BLUE if newest else SUB, 2, rx=6)
            a = "0x" + addr[2:].rjust(2, "0")
            s.text(x + (cw - 10) / 2, y + 28, a, 24, cls="mono")
            s.text(x + (cw - 10) / 2, y + 58, name, 24)
    s.text(4 * cw + 12 + cw / 2 - 4, 622, "BLS12-381", 22, cls="sub")
    s.text(cw + 12 + cw / 2 - 4, 400, "0x06〜08 は", 22, cls="sub")
    s.text(cw + 12 + cw / 2 - 4, 430, "bn254", 22, cls="sub")
    s.save("evm-opcode-history_precompiles.webp")


# 7. EIP / ERC requires graph from lab/output/eip_graph.json.
def eip_graph():
    """Only the requires edges that cross from ERC / Interface to Core (lab/output/eip_graph.json)."""
    nodes = {n["id"]: n for n in GRAPH["nodes"]}
    edges = {(e["from"], e["to"]) for e in GRAPH["edges"]}
    crossing = [("ERC-165", "EIP-214"), ("EIP-712", "EIP-155"), ("ERC-4337", "EIP-7702")]
    for f, t in crossing:  # fail loudly if the extracted data disagrees with the figure
        assert (f, t) in edges and nodes[t]["category"] == "Core" and nodes[f]["category"] != "Core"
    left = {"ERC-165": ("対応の問い合わせ", 110), "EIP-712": ("型付きデータの署名", 250),
            "ERC-4337": ("コントラクトのウォレット", 390)}
    right = {"EIP-214": ("STATICCALL", 110), "EIP-155": ("署名に chain ID", 250),
             "EIP-7702": ("EOA の委任", 390)}
    face = {"ERC": (OCHRE_PALE, OCHRE), "Interface": (GREEN_PALE, GREEN), "Core": (BLUE_PALE, BLUE)}
    s = Svg(960, 500, "ERC と Interface の規格のうち、Core の EIP を requires に挙げるもの。ERC-165 は EIP-214（STATICCALL）、"
                      "EIP-712 は EIP-155（chain ID）、ERC-4337 は EIP-7702（EOA の委任）に依存する")
    s.text(220, 44, "フォーク不要（ERC / Interface）", 24)
    s.rect(500, 60, 440, 410, BLUE_PALE, BLUE, 1.5, rx=12)
    s.text(720, 44, "フォークが要る（Core）", 24)
    for nid, (sub, y) in left.items():
        f, e = face[nodes[nid]["category"]]
        s.rect(40, y - 45, 360, 90, f, e, 2.5, rx=8)
        s.text(220, y - 6, f"{nid} ({nodes[nid]['category']})", 26)
        s.text(220, y + 28, sub, 24, cls="sub")
    for nid, (sub, y) in right.items():
        s.rect(540, y - 45, 360, 90, "#ffffff", BLUE, 2.5, rx=8)
        s.text(720, y - 6, nid, 26)
        s.text(720, y + 28, sub, 24, cls="sub")
    for f, t in crossing:
        s.line(402, left[f][1], 534, right[t][1], SUB, 3)
    s.text(40, 470, "矢印 = requires", 24, "start", "sub")
    s.save("evm-opcode-history_eip_graph.webp")


def eip_types():
    s = Svg(960, 560, "EIP-1 の種類と分類。Standards Track の中に Core・Networking・Interface・ERC があり、"
                      "他に Meta と Informational がある。原則としてハードフォークが要るのは Core だけ")
    s.rect(380, 20, 200, 64, "#ffffff", SUB, 2.5)
    s.text(480, 62, "EIP", 28)
    s.line(480, 84, 480, 112, SUB, 2.5, arrow=False)
    s.line(360, 112, 945, 112, SUB, 2.5, arrow=False)
    s.line(360, 112, 360, 136)
    s.line(830, 112, 830, 136)
    s.line(945, 112, 945, 415, SUB, 2.5, arrow=False)
    s.line(945, 415, 934, 415)
    s.rect(20, 140, 680, 400, GRAY_PALE, SUB, 2, rx=12)
    s.text(40, 178, "Standards Track", 26, "start")
    cats = [
        (36, 200, "Core", ["命令・ガス・トランザクションの型", "原則フォークが要る"], True),
        (368, 200, "Networking", ["ノード間通信（devp2p）", "フォーク不要"], False),
        (36, 370, "Interface", ["ABI・メソッド名", "フォーク不要"], False),
        (368, 370, "ERC", ["トークン・署名など", "フォーク不要"], False),
    ]
    for x, y, name, lines, core in cats:
        s.rect(x, y, 316, 150, BLUE_PALE if core else "#ffffff", BLUE if core else SUB, 2.5 if core else 2, rx=8)
        s.text(x + 20, y + 42, name, 26, "start")
        s.text(x + 20, y + 84, lines[0], 18 if len(lines[0]) > 12 else 24, "start", "sub")
        s.text(x + 20, y + 122, lines[1], 24, "start", "" if core else "sub")
    for y, h, name, sub in ((140, 180, "Meta", ["手続き、", "更新の一覧", "フォーク不要"]),
                            (340, 150, "Informational", ["指針", "フォーク不要"])):
        s.rect(720, y, 210, h, "#ffffff", SUB, 2, rx=8)
        s.text(740, y + 42, name, 26, "start")
        for k, t in enumerate(sub):
            s.text(740, y + 84 + k * 34, t, 24, "start", "sub")
    s.save("evm-opcode-history_eip_types.webp")


# 5. The same byte 0x44 before and after The Merge.
def prevrandao():
    s = Svg(960, 300, "同じバイト 0x44 の命令が、The Merge の前は PoW の難易度を返す DIFFICULTY、後は PoS の乱数を返す PREVRANDAO になった")
    s.rect(40, 110, 160, 90, BLUE_PALE, BLUE, 2.5, rx=8)
    s.text(120, 166, "0x44", 32, cls="mono")
    s.text(120, 240, "同じバイト", 22, cls="sub")
    for y, era, name, sub in ((40, "The Merge の前（PoW）", "DIFFICULTY", "ブロックの計算の難しさ"),
                              (170, "The Merge の後（PoS）", "PREVRANDAO", "PoS で作る乱数")):
        s.text(300, y + 22, era, 22, "start", "sub")
        s.rect(300, y + 34, 600, 76, "#ffffff" if y < 100 else GREEN_PALE, SUB if y < 100 else GREEN, 2.5, rx=8)
        s.text(330, y + 82, name, 26, "start", "mono")
        s.text(580, y + 82, sub, 24, "start")
        s.line(202, 155, 296, y + 72, SUB, 2.5)
    s.save("evm-opcode-history_prevrandao.webp")


# 6b. Why 0x0a exists: the EVM cannot read a blob, only its hash, so a short proof is checked instead.
def kzg():
    s = Svg(960, 420, "blob を運ぶトランザクションには blob と versioned hash が入る。EVM は blob を読めず、BLOBHASH 命令で versioned hash だけを読む。"
                      "rollup のコントラクトは、versioned hash・commitment・点 z・値 y・証明を 0x0a に渡し、blob がその点でその値を取るかを確かめる")
    s.rect(30, 30, 360, 250, GRAY_PALE, SUB, 2, rx=10)
    s.text(50, 66, "blob を運ぶトランザクション", 24, "start")
    s.rect(50, 86, 320, 80, OCHRE_PALE, OCHRE, 2.5, rx=8)
    s.text(210, 122, "blob（128 KiB）", 24)
    s.text(210, 154, "EVM からは読めない", 20, cls="sub")
    s.rect(50, 186, 320, 74, "#ffffff", SUB, 2, rx=8)
    s.text(210, 220, "versioned hash", 24, cls="mono")
    s.text(210, 248, "commitment のハッシュ", 20, cls="sub")
    s.line(372, 223, 466, 223)
    s.text(419, 204, "BLOBHASH", 15, cls="sub")
    s.rect(470, 170, 200, 106, "#ffffff", SUB, 2.5, rx=8)
    s.text(570, 214, "rollup の", 24)
    s.text(570, 246, "コントラクト", 24)
    s.line(672, 223, 716, 223)
    s.rect(720, 150, 220, 146, BLUE_PALE, BLUE, 2.5, rx=8)
    s.text(830, 190, "0x0a で検証", 26)
    s.text(830, 226, "commitment が", 20, cls="sub")
    s.text(830, 252, "versioned hash と合うか", 18, cls="sub")
    s.text(830, 280, "点 z で値 y か", 20, cls="sub")
    s.text(480, 340, "z・y・commitment・証明は、送る側が blob から計算して渡す", 22, cls="sub")
    s.text(480, 376, "確かめられるのは、その blob のその点の値", 22, cls="sub")
    s.save("evm-opcode-history_kzg.webp")

# 7b. The name people use does not tell the category.
def names():
    s = Svg(960, 340, "よく使われる呼び名と、文書に書かれた分類。EIP-712 は Interface、EIP-1271 と呼ばれがちな規格は ERC、"
                      "EIP-1559 は Core。フォークが要るのは Core だけ")
    s.text(40, 44, "よく使う呼び名", 24, "start", "sub")
    s.text(560, 44, "文書の category", 24, "start", "sub")
    rows = [("EIP-712", "Interface", "フォーク不要", GREEN_PALE, GREEN),
            ("「EIP-1271」", "ERC", "フォーク不要", OCHRE_PALE, OCHRE),
            ("EIP-1559", "Core", "フォークが要る", BLUE_PALE, BLUE)]
    for i, (name, cat, fork, f, e) in enumerate(rows):
        y = 64 + i * 90
        s.rect(40, y, 300, 70, "#ffffff", SUB, 2, rx=8)
        s.text(190, y + 45, name, 26)
        s.line(342, y + 35, 556, y + 35, SUB, 2.5)
        s.rect(560, y, 360, 70, f, e, 2.5, rx=8)
        s.text(650, y + 45, cat, 24, "start")
        s.text(900, y + 45, fork, 22, "end", "sub")
    s.save("evm-opcode-history_names.webp")


def opcodes_chart():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    plt.rcParams.update({
        "font.size": 16, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
        "font.family": ["Noto Sans CJK JP", "DejaVu Sans"],
    })

    def save(fig, name):
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight", pad_inches=0.15)
        plt.close(fig)
        to_webp(buf, name)

    # Opcodes per fork on a date axis, and how many existing opcodes changed.
    rows = [r for r in GETH["instruction_sets"] if r["fork"] in FORK_DATES]
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(8.4, 6.4), sharex=True, gridspec_kw={"height_ratios": [3, 1.4]})
    ds = [FORK_DATES[r["fork"]] for r in rows]
    ax.step(ds + [date(2026, 11, 10)], [r["defined"] for r in rows] + [rows[-1]["defined"]], where="post", color=BLUE, lw=2.5)
    notes = {"Homestead": "DELEGATECALL", "Byzantium": "REVERT, STATICCALL", "Constantinople": "CREATE2, SHL",
             "Istanbul": "CHAINID", "London": "BASEFEE", "Shanghai": "PUSH0", "Cancun": "TLOAD, MCOPY", "Osaka": "CLZ"}
    for r, d in zip(rows, ds):
        if r["added"]:
            ax.plot(d, r["defined"], "o", color=BLUE, ms=6)
        if r["fork"] in notes:
            # Label offsets in points: below-right for early forks, above-left for later ones.
            dx, dy = {"London": (-30, 26), "Shanghai": (8, -16), "Cancun": (-4, 6), "Osaka": (-8, 20)}.get(r["fork"], (6, -18))
            ax.annotate(f"{r['fork']}: {notes[r['fork']]}", (d, r["defined"]), textcoords="offset points",
                        xytext=(dx, dy), ha="right" if dx < 0 else "left", fontsize=14,
                        arrowprops={"arrowstyle": "-", "color": SUB, "lw": 1} if r["fork"] in ("London", "Osaka") else None)
    ams = next(r for r in GETH["instruction_sets"] if r["fork"] == "Amsterdam")
    ax.text(date(2015, 9, 1), 155, f"geth の Amsterdam: {ams['defined']}（日付未定）", fontsize=14, color=SUB)
    ax.text(date(2015, 3, 1), rows[0]["defined"] - 4.6, f"Frontier: {rows[0]['defined']}", fontsize=14)
    ax.set_ylabel("命令の数")
    ax.set_ylim(123, 158)
    ax.spines[["top", "right"]].set_visible(False)
    bx.bar(ds, [len(r["changed"]) for r in rows], width=90, color=OCHRE)
    for r, d in zip(rows, ds):
        if len(r["changed"]) >= 4 or r["fork"] == "Merge":
            merge = r["fork"] == "Merge"
            bx.annotate("The Merge" if merge else r["fork"], (d, len(r["changed"])), textcoords="offset points",
                        xytext=(10, 34) if merge else (6, -4), ha="left",
                        fontsize=14, va="bottom" if merge else "top",
                        arrowprops={"arrowstyle": "-", "color": SUB, "lw": 1} if merge else None)
    bx.set_ylabel("変わった命令")
    bx.set_ylim(0, 13)
    bx.spines[["top", "right"]].set_visible(False)
    bx.xaxis.set_major_locator(mdates.YearLocator(2))
    bx.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    save(fig, "evm-opcode-history_opcodes_by_fork.webp")



if __name__ == "__main__":
    IMG.mkdir(exist_ok=True)
    opcodes_chart()
    precompiles()
    eip_types()
    eip_graph()
    prevrandao()
    kzg()
    names()
