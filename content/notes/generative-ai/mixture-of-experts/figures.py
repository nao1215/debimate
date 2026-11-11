"""MoE のノートの図を作る。

- moe_concept.webp : dense の FFN と MoE の FFN の比較（Python 標準ライブラリで SVG を手書き）
- moe_decode.webp  : 1 トークンで読む重みのバイト数と decode の速さ（matplotlib）
- moe_memory.webp  : 総パラメーターのバイト数と ollama ps の size（matplotlib）

計測値は ../local-llm-speed/lab/ の runs.jsonl・gguf.json・mem.json から読む。

使い方:
    python3 figures.py
"""
import json
import os
import statistics
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, "..", "local-llm-speed", "lab")
IMG = os.path.join(HERE, "images")

BLUE, BLUE_F = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_F = "#d4a24c", "#f8eed8"
INK, SUB, GRAY_F = "#1f1f1f", "#666666", "#f2f2f2"
FONT = "Noto Sans CJK JP, sans-serif"


def png_to_webp(png, name):
    Image.open(png).convert("RGB").save(os.path.join(IMG, name), "WEBP", quality=90, method=6)


def svg_to_webp(svg_text, w, h, name):
    """手書きの SVG を Chrome で 2 倍の解像度に描き、WebP にする。"""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        png_to_webp(png, name)


def text(x, y, s, size=24, color=INK, anchor="middle"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}">{s}</text>')


def concept():
    w, h = 960, 540
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
         f'<defs><marker id="a" viewBox="0 0 10 10" markerWidth="5" markerHeight="5" refX="9" refY="5" orient="auto">'
         f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>']
    # 左: dense
    o.append(text(220, 52, "dense の FFN", 28))
    o.append(f'<rect x="90" y="150" width="260" height="230" rx="8" fill="{BLUE_F}" stroke="{BLUE}" stroke-width="3"/>')
    o.append(text(220, 275, "1 つの大きな FFN", 24))
    o.append(f'<line x1="220" y1="85" x2="220" y2="145" stroke="{SUB}" stroke-width="3" marker-end="url(#a)"/>')
    o.append(text(200, 122, "トークン", 22, SUB, "end"))
    o.append(text(220, 448, "毎回、全部を読む", 24))
    o.append(text(220, 488, "載せるのも全部", 24, SUB))
    # 区切り
    o.append(f'<line x1="430" y1="70" x2="430" y2="490" stroke="#d0d0d0" stroke-width="2"/>')
    # 右: MoE
    o.append(text(700, 52, "MoE の FFN（32 個から 4 個）", 28))
    o.append(text(682, 100, "トークン", 22, SUB, "end"))
    o.append(f'<line x1="700" y1="74" x2="700" y2="105" stroke="{SUB}" stroke-width="3" marker-end="url(#a)"/>')
    o.append(f'<rect x="620" y="108" width="160" height="40" rx="6" fill="{OCHRE_F}" stroke="{OCHRE}" stroke-width="3"/>')
    o.append(text(700, 137, "ルーター", 22))
    chosen = {1, 3, 4, 6}             # 線が他の箱を横切らないように 1 段目から選ぶ（どれが選ばれるかはトークンで変わる）
    cols, size, gap = 8, 46, 10
    x0, y0 = 700 - (cols * size + (cols - 1) * gap) / 2, 190
    for i in range(32):
        r, c = divmod(i, cols)
        x, y = x0 + c * (size + gap), y0 + r * (size + gap)
        if i in chosen:
            o.append(f'<line x1="700" y1="148" x2="{x + size / 2}" y2="{y}" stroke="{SUB}" stroke-width="2"/>')
    for i in range(32):
        r, c = divmod(i, cols)
        x, y = x0 + c * (size + gap), y0 + r * (size + gap)
        if i in chosen:
            o.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="5" fill="{BLUE_F}" stroke="{BLUE}" stroke-width="3"/>')
        else:
            o.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="5" fill="{GRAY_F}" stroke="#bdbdbd" stroke-width="2"/>')
    o.append(text(700, 448, "読むのは選ばれた 4 個だけ", 24))
    o.append(text(700, 488, "載せるのは 32 個全部", 24, SUB))
    o.append("</svg>")
    svg_to_webp("\n".join(o) + "\n", w, h, "moe_concept.webp")


# ---- matplotlib の図 -------------------------------------------------------------
MODELS = [  # (Ollama の名前, gguf.json のキー, 表示名, 色)
    ("qwen3:8b", "qwen3-8b", "qwen3:8b\n（dense）", BLUE),
    ("hf.co/ggml-org/gpt-oss-20b-GGUF:latest", "gpt-oss-20b", "gpt-oss-20b\n（MoE 4/32）", OCHRE),
    ("qwen3-coder:30b", "qwen3-coder-30b", "qwen3-coder:30b\n（MoE 8/128）", OCHRE),
]


def plt_setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 13,
                         "axes.edgecolor": SUB, "axes.labelcolor": INK,
                         "xtick.color": INK, "ytick.color": INK})
    return plt


def save(plt, fig, name):
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "fig.png")
        fig.savefig(png, dpi=200, facecolor="#ffffff", bbox_inches="tight")
        png_to_webp(png, name)
    plt.close(fig)


def short_decode():
    """各モデルの、いちばん短い入力（約 500 トークン）での decode の中央値。"""
    runs = [json.loads(x) for x in open(os.path.join(LAB, "runs.jsonl"))]
    runs = [r for r in runs if not r["disturbed"] and r["time"] != "2026-11-11T12:38:44"]  # 理由は local-llm-speed/figures.py の EXCLUDE
    out = {}
    for m, *_ in MODELS:
        rs = [r for r in runs if r["model"] == m]
        if rs:
            n = min(r["lines"] for r in rs)
            out[m] = statistics.median(r["decode_tps"] for r in rs if r["lines"] == n)
    return out


def decode_fig(gguf, dec):
    plt = plt_setup()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw={"width_ratios": [1.25, 1]})
    y = list(range(len(MODELS)))
    labels = [lab for _, _, lab, _ in MODELS]
    tot = [gguf[k]["total_bytes"] / 1e9 for _, k, _, _ in MODELS]
    act = [gguf[k]["decode_read_bytes"] / 1e9 for _, k, _, _ in MODELS]
    cols = [c for *_, c in MODELS]
    a1.barh(y, tot, color="#ffffff", edgecolor=SUB, height=0.6, label="重み全体（メモリに載せる）")
    a1.barh(y, act, color=cols, height=0.6, label="1 トークンで読む重み（青: dense、黄土: MoE）")
    for i in y:
        a1.text(tot[i] + 0.3, i, f"{act[i]:.1f} / {tot[i]:.1f} GB", va="center", fontsize=12)
    a1.set_yticks(y)
    a1.set_yticklabels(labels)
    a1.invert_yaxis()
    a1.set_xlim(0, max(tot) * 1.75)
    a1.set_xlabel("GB")
    h_, l_ = a1.get_legend_handles_labels()
    a1.set_title("重みのバイト数", fontsize=15, color=INK)
    v = [dec.get(m, 0) for m, *_ in MODELS]
    a2.barh(y, v, color=cols, height=0.6)
    for i in y:
        a2.text(v[i] + 1, i, f"{v[i]:.0f}", va="center", fontsize=12)
    a2.set_yticks(y)
    a2.set_yticklabels([])
    a2.invert_yaxis()
    a2.set_xlim(0, max(v) * 1.25 if max(v) else 1)
    a2.set_xlabel("トークン毎秒")
    a2.set_title("decode の速さ（中央値）", fontsize=15, color=INK)
    for a in (a1, a2):
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.legend(h_, l_, frameon=False, fontsize=11, loc="lower center", ncol=2)
    save(plt, fig, "moe_decode.webp")


def memory_fig(gguf, mem):
    plt = plt_setup()
    fig, ax = plt.subplots(figsize=(9, 3.6))
    y = list(range(len(MODELS)))
    act = [gguf[k]["decode_read_bytes"] / 1e9 for _, k, _, _ in MODELS]
    fsz = [gguf[k]["file_size"] / 1e9 for _, k, _, _ in MODELS]
    ps = []
    for m, *_ in MODELS:
        r = [x for x in mem if x["model"] == m and x["num_ctx"] == 4096]
        ps.append(r[0]["size"] / 1e9 if r else 0)
    h = 0.26
    ax.barh([i - h for i in y], act, height=h, color=[c for *_, c in MODELS], label="1 トークンで読む重み（青: dense、黄土: MoE）")
    ax.barh(y, fsz, height=h, color="#ffffff", edgecolor=SUB, label="GGUF ファイル")
    ax.barh([i + h for i in y], ps, height=h, color="#bdbdbd", label="ollama ps の SIZE（num_ctx 4,096）")
    for i in y:
        ax.text(act[i] + 0.2, i - h, f"{act[i]:.1f}", va="center", fontsize=11)
        ax.text(fsz[i] + 0.2, i, f"{fsz[i]:.1f}", va="center", fontsize=11)
        ax.text(ps[i] + 0.2, i + h, f"{ps[i]:.1f}", va="center", fontsize=11)
    ax.set_yticks(y)
    ax.set_yticklabels([lab for _, _, lab, _ in MODELS])
    ax.invert_yaxis()
    ax.set_xlabel("GB")
    ax.set_xlim(0, max(ps + fsz) * 1.15)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=11, loc="upper right")
    fig.tight_layout()
    save(plt, fig, "moe_memory.webp")


if __name__ == "__main__":
    os.makedirs(IMG, exist_ok=True)
    concept()
    gguf = json.load(open(os.path.join(LAB, "gguf.json")))
    if os.path.exists(os.path.join(LAB, "runs.jsonl")):
        decode_fig(gguf, short_decode())
    if os.path.exists(os.path.join(LAB, "mem.json")):
        memory_fig(gguf, json.load(open(os.path.join(LAB, "mem.json"))))
