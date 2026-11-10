"""Generate the figures of the tool calling note.

concept_figure() は標準ライブラリだけで SVG を書く。グラフは lab/ の実測（*.jsonl）を
matplotlib で描く。
"""

import json
from collections import Counter
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab"
OUT = HERE / "images"

INK, SUB, FILL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED, RED_PALE = "#e15759", "#fbe3e3"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono','Noto Sans Mono',monospace"


class Svg:
    def __init__(self, width, height, title):
        marks = "".join(
            f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="8" refY="5" '
            f'markerUnits="userSpaceOnUse" markerWidth="20" markerHeight="20" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
            for n, c in (("ink", INK), ("sub", SUB), ("green", GREEN)))
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .mono{{font-family:{MONO}}}</style>',
            f'<defs>{marks}</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle",
             mono=False):
        cls = ' class="mono"' if mono else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}"{cls}>{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, rx=10, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def path(self, d, color=INK, sw=3, arrow="ink", dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color}" '
                          f'stroke-width="{sw}"{da}{m}/>')

    def raw(self, s):
        self.parts.append(s)

    def save(self, name):
        (OUT / name).write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    """モデル・呼ぶ側・ツールの 3 者と、要求 → 実行 → 結果 → 次の判断のループ。

    モデルは JSON の要求を返すだけで、実行するのは呼ぶ側。呼ぶ側の箱の中に
    検証・許可リスト・回数の上限の関所を置き、上限で打ち切る出口を赤の 1 点で示す。
    """
    f = Svg(960, 540, "モデルが返した要求を呼ぶ側が実行し、結果を戻して次を決めさせるループ")
    # --- 3 者
    f.box(30, 150, 220, 210, BLUE_PALE, BLUE, rx=14)
    f.text(140, 232, "モデル", 32, weight="normal")
    f.text(140, 276, "要求を返すだけ", 24, SUB)
    f.text(140, 310, "実行はしない", 24, SUB)

    f.box(370, 150, 250, 210, OCHRE_PALE, OCHRE, rx=14)
    f.text(495, 196, "呼ぶ側", 32, weight="normal")
    for i, s in enumerate(("スキーマ検証", "許可リスト", "回数の上限")):
        y = 216 + i * 44
        f.box(395, y, 200, 36, "#ffffff", OCHRE, sw=2, rx=6)
        f.text(495, y + 27, s, 24)

    f.text(830, 128, "ツール", 26, SUB)
    for i, s in enumerate(("calculate", "get_weather", "read_file")):
        y = 150 + i * 74
        f.box(730, y, 200, 58, FILL, SUB, sw=2, rx=8)
        f.text(830, y + 38, s, 24, mono=True)

    # --- 上: モデル → 呼ぶ側（JSON の要求）
    f.box(150, 22, 470, 84, "#ffffff", SUB, sw=1.5, rx=8)
    f.text(168, 56, '{"name": "get_weather",', 24, anchor="start", mono=True)
    f.text(168, 90, ' "arguments": {"city": "Tokyo"}}', 24, anchor="start", mono=True)
    f.path("M200,150 C200,118 250,118 290,118 L470,118 C490,118 495,130 495,146",
           sw=3.5)
    # --- 下: 呼ぶ側 → モデル（結果を会話に戻す）
    f.path("M495,360 C495,392 470,398 440,398 L230,398 C200,398 140,392 140,364",
           sw=3.5)
    f.box(180, 410, 340, 44, "#ffffff", SUB, sw=1.5, rx=8)
    f.text(350, 441, '{"temperature_c": 18}', 24, mono=True)
    # --- 呼ぶ側 ↔ ツール
    f.path("M620,236 L724,236", sw=3)
    f.text(672, 224, "実行", 24, SUB)
    f.path("M726,270 L626,270", sw=3)
    f.text(676, 302, "結果", 24, SUB)
    # --- 出口 1: tool_calls が空 = 最終回答
    f.path("M30,255 L10,255 L10,505 L60,505", color=GREEN, sw=3.5, arrow="green")
    f.box(70, 480, 300, 50, GREEN_PALE, GREEN, sw=2.5, rx=8)
    f.text(220, 514, "要求なし → 最終回答", 24)
    # --- 出口 2: 回数の上限で打ち切り（赤は 1 点だけ）
    f.path("M620,325 C660,330 680,380 690,470", color=SUB, sw=2.5, arrow="sub",
           dash="7 5")
    f.box(600, 478, 330, 50, RED_PALE, RED, sw=2.5, rx=8)
    f.text(765, 512, "8 回で打ち切り", 24)
    f.save("tool-calling_concept.svg")


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "tool-calling",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    return plt


def load_summary():
    return json.loads((LAB / "summary.json").read_text())


def bench_figure():
    """課題を回した結末（正解・誤答・打ち切り）と、モデルへの問い合わせ回数の分布。

    設定ごとに回した回数が違う（seed 3 個と 1 個）ので、どちらも割合で描く。"""
    plt = _plt()
    summ = load_summary()
    labels = list(summ)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.6, 3.7),
                                   gridspec_kw={"width_ratios": [1.15, 1]})
    kinds = [("correct", "correct", BLUE), ("wrong_answer", "wrong answer", OCHRE),
             ("repeat_limit", "stopped: same call x3", SUB),
             ("step_limit", "stopped: 8 turns", RED)]
    y = list(range(len(labels)))[::-1]
    for yi, lab in zip(y, labels):
        left, n = 0, summ[lab]["runs"]
        for key, _, color in kinds:
            v = 100 * summ[lab]["outcome"].get(key, 0) / n
            if v:
                ax1.barh(yi, v, left=left, color=color, height=0.55)
                if v >= 5:
                    ax1.text(left + v / 2, yi, f"{v:.0f}", ha="center", va="center",
                             color="#ffffff" if color != OCHRE else INK, fontsize=10)
            left += v
    ax1.set_yticks(y, [lab.replace(" think=", "\nthink=") + f"\n(n={summ[lab]['runs']})"
                       for lab in labels], fontsize=10)
    ax1.set_xlim(0, 100)
    ax1.set_xlabel("Runs (%)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in kinds]
    ax1.legend(handles, [n for _, n, _ in kinds], loc="upper center",
               bbox_to_anchor=(0.5, -0.24), ncol=2, frameon=False, fontsize=10)
    ax1.spines[["top", "right"]].set_visible(False)

    turns = range(1, 9)
    width = 0.8 / len(labels)
    colors = [BLUE, OCHRE, SUB]
    for i, lab in enumerate(labels):
        st = summ[lab]["steps"]
        n = summ[lab]["runs"]
        ax2.bar([t + (i - (len(labels) - 1) / 2) * width for t in turns],
                [100 * st.get(str(t), 0) / n for t in turns], width=width, color=colors[i],
                label=lab)
    ax2.set_xticks(list(turns))
    ax2.set_xlabel("Model turns per run")
    ax2.set_ylabel("Runs (%)")
    ax2.legend(frameon=False, fontsize=10, loc="center right")
    ax2.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "tool-calling_bench.svg", metadata={"Date": None})


def injection_figure():
    """注入した文の種類ごとに、危険な模擬ツールを要求した割合と実行された割合。"""
    plt = _plt()
    panels = [(lab, task, s[f"injection_{task}"]) for lab, s in load_summary().items()
              for task in ("summarize", "act") if f"injection_{task}" in s]
    fig, axes = plt.subplots(1, len(panels), figsize=(8.5, 3.9), sharey=True,
                             squeeze=False)
    variants = ["none", "system_ja", "english", "polite_ja"]
    conds = [("raw", "as is", OCHRE), ("as_data", "marked as data", BLUE),
             ("allowlist", "caller allowlist", SUB)]
    for ax, (lab, task, inj) in zip(axes[0], panels):
        for i, (cond, name, color) in enumerate(conds):
            xs = [v + (i - 1) * 0.27 for v in range(len(variants))]
            n = [inj[f"{cond}/{v}"][0] for v in variants]
            att = [100 * inj[f"{cond}/{v}"][1] / k for v, k in zip(variants, n)]
            exe = [100 * inj[f"{cond}/{v}"][2] / k for v, k in zip(variants, n)]
            ax.bar(xs, att, width=0.27, color="#ffffff", edgecolor=color, lw=1.4,
                   label=f"{name}: requested")
            ax.bar(xs, exe, width=0.27, color=color, label=f"{name}: executed")
        ax.set_xticks(range(len(variants)), ["none", "JA\n[System]", "EN\nIgnore", "JA\npolite"],
                      fontsize=10)
        ax.set_title(f"{lab.split()[0]}, task: {task} (n={n[0]})", fontsize=10)
        if not any(v[1] for v in inj.values()):
            total = sum(v[0] for v in inj.values())
            ax.text(1.5, 50, f"no delete/send calls\nin {total} runs", ha="center",
                    va="center", color=SUB, fontsize=10)
        ax.set_ylim(0, 105)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0][0].set_ylabel("Runs that called delete/send (%)")
    h, l = axes[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, fontsize=10)
    fig.tight_layout(rect=(0, 0.15, 1, 1))
    fig.savefig(OUT / "tool-calling_injection.svg", metadata={"Date": None})


def template_figure():
    """チャットテンプレートで 1 本の文字列にした会話。ツールの結果は user の枠に入る。"""
    f = Svg(960, 540, "関数の定義は system の文章に、ツールの結果は user の枠に置かれる")
    rows = [
        ("system", "<tools> 関数の定義 </tools>", FILL, SUB),
        ("user", "東京の今の気温は何度ですか。", FILL, SUB),
        ("assistant", "<tool_call> 要求の JSON </tool_call>", BLUE_PALE, BLUE),
        ("user", "<tool_response> 結果の JSON </tool_response>", OCHRE_PALE, OCHRE),
        ("assistant", "次の返事", FILL, SUB),
    ]
    for i, (role, body, fill, stroke) in enumerate(rows):
        y = 20 + i * 88
        f.box(30, y, 180, 74, "#ffffff", SUB, sw=2, rx=8)
        f.text(120, y + 46, role, 24, mono=True)
        f.box(225, y, 705, 74, fill, stroke, sw=2.5, rx=8)
        f.text(250, y + 46, body, 24, anchor="start")
    f.text(480, 500, "ツールの結果も、ユーザーの発言と同じ枠に並ぶ文字列", 26)
    f.save("tool-calling_template.svg")


def defense_figure():
    """結果に紛れた指示への 2 つの守りが、ループのどこで効くか。"""
    f = Svg(960, 540, "データとして包む守りはモデルの判断に、許可リストは呼ぶ側の作りに頼る")
    cy = 130
    f.box(20, cy - 60, 180, 120, FILL, SUB, rx=12)
    f.text(110, cy - 8, "ツールの結果", 24)
    f.text(110, cy + 30, "指示が紛れる", 24, SUB)
    f.box(260, cy - 60, 150, 120, BLUE_PALE, BLUE, rx=12)
    f.text(335, cy + 9, "モデル", 28)
    f.box(480, cy - 60, 190, 120, OCHRE_PALE, OCHRE, rx=12)
    f.text(575, cy - 8, "呼ぶ側", 26)
    f.box(495, cy + 6, 160, 40, "#ffffff", OCHRE, sw=2, rx=6)
    f.text(575, cy + 35, "許可リスト", 24)
    f.box(730, cy - 60, 210, 120, "#ffffff", SUB, rx=12, dash="8 6")
    f.text(835, cy - 10, "delete_file", 24, SUB, mono=True)
    f.raw(f'<path d="M762,{cy + 14} l22,22 M784,{cy + 14} l-22,22" stroke="{RED}" '
          'stroke-width="5" stroke-linecap="round"/>')
    f.text(798, cy + 35, "実行しない", 24, SUB, anchor="start")
    f.path(f"M202,{cy} L254,{cy}", sw=3)
    f.path(f"M412,{cy} L474,{cy}", sw=3)
    f.text(443, cy - 14, "要求", 24, SUB)
    f.path(f"M672,{cy} L724,{cy}", color=SUB, sw=3, arrow="sub", dash="7 5")
    # 2 つの守りの説明
    f.box(110, 280, 380, 200, BLUE_PALE, BLUE, sw=2, rx=12)
    f.text(300, 325, "データとして包む", 26)
    f.text(300, 370, "モデルが従わないかで決まる", 24, SUB)
    f.text(300, 425, "対応の課題: 30 回中 25 回", 24)
    f.text(300, 460, "が実行された", 24)
    f.path("M300,280 L330,196", color=BLUE, sw=2.5, arrow=None)
    f.box(530, 280, 380, 200, OCHRE_PALE, OCHRE, sw=2, rx=12)
    f.text(720, 325, "許可リスト", 26)
    f.text(720, 370, "呼ぶ側の作りで決まる", 24, SUB)
    f.text(720, 425, "要求は 40 回中 33 回", 24)
    f.text(720, 460, "実行は 0 回", 24)
    f.path("M690,280 L600,196", color=OCHRE, sw=2.5, arrow=None)
    f.save("tool-calling_defense.svg")

if __name__ == "__main__":
    concept_figure()
    template_figure()
    defense_figure()
    if (LAB / "summary.json").exists():
        bench_figure()
        injection_figure()
