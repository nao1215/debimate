"""5 つの実験の条件（プロンプト・ネガティブ・seed）を作る。

run.py が生成に、analyze.py が集計に使う。条件はすべてここで決まり、
1 条件 = 1 枚（名前・positive・negative・seed）。
"""

# --- 静物の共通部分（実験 1〜3） ---
STILL_POS = ("masterpiece, best quality, no humans, still life, {teapot}, lemons, glass bottle, "
             "white tablecloth, wooden table, window, indoors")
STILL_NEG_PERSON = "1girl, 1boy, person"

# 実験 2 で重みを付けるネガティブプロンプト（よく使われる品質の語と、白黒を避ける語）
NEG_WORDS = ["lowres", "worst quality", "bad quality", "low quality", "jpeg artifacts",
             "blurry", "text", "signature", "watermark", "logo", "monochrome", "greyscale"]

SEEDS_STILL = [101, 102, 103]


def weighted(word, w):
    return word if w == 1.0 else f"({word}:{w})"


def exp_positive():
    """実験 1: 色の語 1 つの重みを 1.0〜2.0 に振る。"""
    out = []
    for w in [1.0, 1.2, 1.4, 1.6, 1.8, 2.0]:
        pos = STILL_POS.format(teapot=weighted("blue ceramic teapot", w))
        neg = ", ".join(NEG_WORDS + [STILL_NEG_PERSON])
        for s in SEEDS_STILL:
            out.append({"name": f"w{w:.1f}", "w": w, "positive": pos, "negative": neg, "seed": s})
    return out


def exp_negative():
    """実験 2: ネガティブプロンプトの先頭 k 語に重み w を付ける（k = 1, 6, 12）。"""
    out = []
    pos = STILL_POS.format(teapot="white ceramic teapot")
    for k in [1, 6, 12]:
        for w in [1.0, 1.2, 1.3, 1.5, 1.8]:
            if w == 1.0 and k != 1:
                continue  # 重み 1.0 は k によらず同じプロンプトになるので 1 回だけ
            words = [weighted(x, w) if i < k else x for i, x in enumerate(NEG_WORDS)]
            neg = ", ".join(words + [STILL_NEG_PERSON])
            name = "w1.0" if w == 1.0 else f"k{k}_w{w:.1f}"
            for s in SEEDS_STILL:
                out.append({"name": name, "k": k if w != 1.0 else 0, "w": w,
                            "positive": pos, "negative": neg, "seed": s})
    # 切り分け: 12 語のうち、色に関わる 2 語（monochrome, greyscale）だけに重みを付ける場合と、
    # その 2 語を除いた 10 語に重みを付ける場合
    for label, picked in [("mono", {"monochrome", "greyscale"}),
                          ("k10", set(NEG_WORDS[:10]))]:
        for w in [1.3, 1.5, 1.8]:
            words = [weighted(x, w) if x in picked else x for x in NEG_WORDS]
            neg = ", ".join(words + [STILL_NEG_PERSON])
            for s in SEEDS_STILL:
                out.append({"name": f"{label}_w{w:.1f}", "k": len(picked), "w": w,
                            "positive": pos, "negative": neg, "seed": s})
    return out


# --- 実験 3: 同じ語を 77 トークンの区切りの前と後ろに置く ---
FILLER_1 = ("intricate details, highly detailed, sharp focus, depth of field, soft shadows, "
            "centered composition, ceramic texture, glass reflection, fabric texture, wood grain, "
            "clean lines, balanced composition, calm atmosphere, quiet mood")
FILLER_2 = ("simple arrangement, cup, spoon, saucer, folded napkin, small plate, bread, knife, jar, "
            "cork, sugar bowl, teacup, wooden tray, kitchen, curtain, shelf, picture frame, books, "
            "vase, pottery, still life painting, traditional media, illustration, scenery, no text, "
            "tidy, neat, symmetrical, quiet, still")
TARGET = "red background"
SEEDS_POSITION = [201, 202, 203, 204]


def position_prompt(where):
    head = STILL_POS.format(teapot="white ceramic teapot")
    t = TARGET
    parts = {
        "none":         [head, FILLER_1, FILLER_2],
        "front":        [head.replace("still life,", f"still life, {t},"), FILLER_1, FILLER_2],
        "chunk1_end":   [head, FILLER_1.replace(", quiet mood", f", {t}, quiet mood"), FILLER_2],
        "chunk2_start": [head, FILLER_1, f"{t}, " + FILLER_2],
        "chunk2_end":   [head, FILLER_1, FILLER_2 + f", {t}"],
    }[where]
    return ", ".join(parts)


def exp_position():
    out = []
    neg = ", ".join(NEG_WORDS + [STILL_NEG_PERSON])
    for where in ["none", "front", "chunk1_end", "chunk2_start", "chunk2_end"]:
        for s in SEEDS_POSITION:
            out.append({"name": where, "positive": position_prompt(where),
                        "negative": neg, "seed": s})
    return out


# --- 実験 4: 静物の語を 1 つずつ外して、絵全体を変えた語を探す ---
ABL_HEAD = ("masterpiece, best quality, no humans, still life, white ceramic teapot, "
            "white tablecloth, wooden table, window, indoors")
ABL_ITEMS = ["lemons", "glass bottle", "red apple", "candle", "books", "potted plant",
             "silver spoon", "blue cup"]
SEEDS_ABLATION = [301, 302]


def exp_ablation():
    """実験 4: 8 個の品を 1 つずつ外す（外さない full と合わせて 9 通り）。"""
    out = []
    neg = ", ".join(NEG_WORDS + [STILL_NEG_PERSON])
    for drop in [None] + ABL_ITEMS:
        items = [x for x in ABL_ITEMS if x != drop]
        pos = ", ".join([ABL_HEAD] + items)
        name = "full" if drop is None else "no_" + drop.replace(" ", "_")
        for s in SEEDS_ABLATION:
            out.append({"name": name, "drop": drop, "positive": pos, "negative": neg, "seed": s})
    return out


# --- 実験 5: 照明・時間帯の語と、ネガティブプロンプトの重みの組み合わせ ---
# 照明の語は、著者のプロンプトと検査の記録に出てきた語から選んだ（night, neon light, sunset）と、
# 「lighting」を含む語の例として dramatic lighting。プロンプトの末尾（indoors の後）に足す。
LIGHT_WORDS = [None, "night", "neon light", "sunset", "dramatic lighting"]
LIGHT_NEG_WEIGHTS = [1.0, 1.2, 1.3]   # 実験 2 の 12 語すべてに掛ける重み（1.0 は重みなし）


def exp_lighting():
    out = []
    base = STILL_POS.format(teapot="white ceramic teapot")
    for light in LIGHT_WORDS:
        pos = base if light is None else f"{base}, {light}"
        for w in LIGHT_NEG_WEIGHTS:
            neg = ", ".join([weighted(x, w) for x in NEG_WORDS] + [STILL_NEG_PERSON])
            lname = "none" if light is None else light.replace(" ", "_")
            for s in SEEDS_STILL:
                out.append({"name": f"{lname}_neg{w:.1f}", "light": light, "w": w,
                            "positive": pos, "negative": neg, "seed": s})
    return out


EXPERIMENTS = {"positive": exp_positive, "negative": exp_negative,
               "position": exp_position, "ablation": exp_ablation,
               "lighting": exp_lighting}
