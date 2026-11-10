"""Generate the figures of the tokenizer note from lab/counts.json, lab/bpe.json and lab/output_bpe.txt."""

import json
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, FILL = "#8fae86", "#f2f2f2"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "tokenizer",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono','Menlo','Consolas',monospace"


def load(name):
    return json.loads((HERE / "lab" / name).read_text())


def counts_figure():
    data = load("counts.json")["counts"]
    texts = [("ja", "Japanese (Wallet note)"), ("en", "English (translation)"),
             ("code", "Python code"), ("digits", "Numbers"), ("emoji", "Emoji")]
    toks = [("o200k_base", BLUE), ("cl100k_base", OCHRE),
            ("Qwen3", GREEN), ("LLM-jp-3", SUB)]
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    h = 0.19
    for j, (name, color) in enumerate(toks):
        ys = [i + (j - 1.5) * h for i in range(len(texts))]
        vals = [data[k][name] for k, _ in texts]
        ax.barh(ys, vals, height=h * 0.9, color=color, label=name)
        for y, v in zip(ys, vals):
            ax.text(v + 1, y, str(v), va="center", fontsize=10, color=INK)
    ax.set_yticks(range(len(texts)),
                  [f"{lab}\n{data[k]['chars']} chars / {data[k]['bytes']} bytes"
                   for k, lab in texts])
    ax.invert_yaxis()
    ax.set_xlabel("Tokens")
    ax.set_xlim(0, 105)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=10)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "tokenizer_counts.svg", metadata={"Date": None})


def bpe_figure():
    data = load("bpe.json")
    m = data["merges"]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(m, data["tokens"]["ja"], color=BLUE, lw=2.0,
            label="Japanese (in the training text)")
    ax.plot(m, data["tokens"]["en"], color=OCHRE, lw=2.0, ls="--",
            label="English translation (not in it)")
    counts = load("counts.json")["counts"]
    for key, color in (("ja", BLUE), ("en", OCHRE)):
        v = counts[key]["o200k_base"]
        ax.axhline(v, color=color, lw=1.0, ls=":")
        ax.text(15, v + 4, f"o200k_base: {v}", ha="left", fontsize=10, color=SUB)
    ax.set_xlabel("Merges learned from the Wallet note (37,097 chars)")
    ax.set_ylabel("Tokens of the passage")
    ax.set_xlim(0, 1000)
    ax.set_ylim(0, 310)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper right", frameon=False, fontsize=10)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "tokenizer_bpe_merges.svg", metadata={"Date": None})


def concept_figure():
    """Characters, bytes and tokens of the same short sentence (cl100k_base)."""
    short = load("counts.json")["short"]
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("同じ意味の文を文字・バイト・トークンで区切った図")}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}} '
        f'.mono{{font-family:{MONO}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def rect(x, y, wd, ht, fill, stroke, sw=1.5, rx=4):
        p.append(f'<rect x="{x:.1f}" y="{y}" width="{wd:.1f}" height="{ht}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def block(top, sentence, tokens, label):
        """3 rows: characters, bytes, tokens. x positions follow the bytes."""
        x0, width = 170, 700
        nbytes = len(sentence.encode())
        bw = width / nbytes
        rows = {"chars": top + 34, "bytes": top + 104, "tokens": top + 160}
        text(30, top + 18, label, 24, "start")
        for key, name in (("chars", "文字"), ("bytes", "バイト"), ("tokens", "トークン")):
            text(150, rows[key] + 33, name, 24, "end", cls="sub")
        # characters
        pos = 0
        for ch in sentence:
            n = len(ch.encode())
            rect(x0 + pos * bw, rows["chars"], n * bw, 48, FILL, SUB)
            if ch != " ":
                text(x0 + (pos + n / 2) * bw, rows["chars"] + 34, ch, 26,
                     cls="mono" if ch.isascii() else "")
            pos += n
        # bytes: one frame per character, divided into its bytes
        pos = 0
        for ch in sentence:
            n = len(ch.encode())
            bx, by = x0 + pos * bw + 2, rows["bytes"] + 6
            rect(bx, by, n * bw - 4, 28, "#ffffff", SUB, 1.5, 2)
            for k in range(1, n):
                xk = x0 + (pos + k) * bw
                p.append(f'<line x1="{xk:.1f}" y1="{by}" x2="{xk:.1f}" y2="{by + 28}" '
                         f'stroke="{SUB}" stroke-width="1"/>')
            pos += n
        # tokens: blue if the token is whole characters, ochre if it cuts a character
        pos = 0
        for tok in tokens:
            b = bytes(tok)
            try:
                s = b.decode("utf-8")
                fill, stroke = BLUE_PALE, BLUE
            except UnicodeDecodeError:
                s, fill, stroke = "", OCHRE_PALE, OCHRE
            rect(x0 + pos * bw + 2, rows["tokens"], len(b) * bw - 4, 48, fill, stroke, 2.5)
            if s.strip():
                text(x0 + (pos + len(b) / 2) * bw, rows["tokens"] + 34, s.strip(), 24,
                     cls="mono" if s.isascii() else "")
            pos += len(b)
        n_chars = len(sentence)
        for key, n in (("chars", n_chars), ("bytes", nbytes), ("tokens", len(tokens))):
            text(930, rows[key] + 33, str(n), 26, "end")

    text(930, 24, "cl100k_base", 24, "end", cls="sub")
    block(6, "秘密鍵を安全に保管する", short["ja"]["cl100k_base"], "日本語")
    p.append(f'<line x1="30" y1="266" x2="930" y2="266" stroke="{SUB}" '
             'stroke-width="1" stroke-dasharray="4 4"/>')
    block(276, "Store the private key safely", short["en"]["cl100k_base"], "英語")
    (HERE / "images" / "tokenizer_concept.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


def steps_figure():
    """How the Japanese short sentence is split after 0..1000 merges (lab/output_bpe.txt)."""
    import re
    out = (HERE / "lab" / "output_bpe.txt").read_text(encoding="utf-8")
    rows = re.findall(r"after (\d+) merges\n  ja\s+(\d+)  (.+)", out)

    def to_bytes(tok):
        b, i = bytearray(), 0
        while i < len(tok):
            if tok.startswith("\\x", i):
                b.append(int(tok[i + 2:i + 4], 16))
                i += 4
            else:
                b += tok[i].encode()
                i += 1
        return bytes(b)

    w, h = 960, 540
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'viewBox="0 0 {w} {h}" role="img"><title>'
         f'{escape("結合の回数ごとに「秘密鍵を安全に保管する」を区切った図")}</title>',
         f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    x0, width = 150, 690
    text(130, 40, "結合の回数", 24, "end", cls="sub")
    text(930, 40, "トークン数", 24, "end", cls="sub")
    for r, (merges, n, line) in enumerate(rows):
        toks = [to_bytes(t) for t in line.split("|")]
        total = sum(len(b) for b in toks)
        bw = width / total
        y = 58 + r * 74
        text(130, y + 34, f"{int(merges):,} 回", 24, "end")
        text(930, y + 34, n, 26, "end")
        pos = 0
        for b in toks:
            try:
                s = b.decode("utf-8")
                fill, stroke = BLUE_PALE, BLUE
            except UnicodeDecodeError:
                s, fill, stroke = "", OCHRE_PALE, OCHRE
            p.append(f'<rect x="{x0 + pos * bw + 1.5:.1f}" y="{y}" width="{len(b) * bw - 3:.1f}" '
                     f'height="48" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
            if s:
                text(x0 + (pos + len(b) / 2) * bw, y + 34, s, 24)
            pos += len(b)
    text(480, 528, "黄土色は文字の途中で切れたトークン（幅はバイト数）", 24, cls="sub")
    (HERE / "images" / "tokenizer_bpe_steps.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


if __name__ == "__main__":
    concept_figure()
    counts_figure()
    bpe_figure()
    steps_figure()
