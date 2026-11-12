"""名詞を「の」で 3 つ以上つなぐ表現（A の B の C）を見つける。

2026-11-12 著者「名詞をつなぐ『の』が連続する表現は NG。これはスキルやコミット時の評価に入れてほしい」。
本人の技術記事（content/post/ja の 200 本）では 1 本あたり 1.0 個、当時の技術ノート 152 本は 1 本あたり 22 個だった。

判定は形態素解析を使わない近似。名詞らしい語（漢字・カタカナ・英数字の並び。末尾に送り仮名 1 字まで）が
「の」を挟んで 3 つ続く所を拾う。ひらがなの直後から始まる連続（「同じ姿勢の 3D の人形」）も拾う。「人形の奥行きの画像」「現実の比率の人形」「2 枚の脚の比」が当たる。
直し方: 語を言い換える（「人形の奥行きの画像」→「人形の奥行き」）、動詞でつなぐ（「人形から書き出した奥行き」）、
文を分ける。

使い方: python3 no_chain.py <index.md>...   # 見つけた所を行番号付きで出す。0 件なら終了コード 0
"""
import re
import sys

NOUN = r"[一-龥々〆ァ-ヶーA-Za-z0-9][一-龥々〆ァ-ヶーA-Za-z0-9.\-]*[ぁ-ゖ]?"
CHAIN = re.compile(rf"(?<![一-龥々〆ァ-ヶーA-Za-z0-9])({NOUN}) ?の ?({NOUN}) ?の ?({NOUN})")


def visible(line):
    """読者に見える文だけにする。リンクは文字だけ、インラインのコードは 1 語、shortcode は caption だけ。"""
    if line.lstrip().startswith("{{<"):
        m = re.search(r'caption="([^"]*)"', line)
        line = m.group(1) if m else ""
    elif line.lstrip().startswith(("<", ">")):
        return ""
    line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)
    line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)
    line = re.sub(r"`[^`]*`", "X", line)
    return line


def chains(line):
    """1 行の中の「A の B の C」を返す。"""
    return [m.group(0) for m in CHAIN.finditer(visible(line))]


def scan(text):
    """front matter とコードブロックを除いた本文から、(行番号, 見つけた表現) の列を返す。"""
    out, incode = [], False
    lines = text.split("\n")
    start = 0
    if lines and lines[0] == "---":
        start = lines.index("---", 1) + 1
    for i, line in enumerate(lines[start:], start + 1):
        if line.lstrip().startswith("```"):
            incode = not incode
            continue
        if not incode:
            out += [(i, c) for c in chains(line)]
    return out


if __name__ == "__main__":
    bad = 0
    for path in sys.argv[1:]:
        for n, c in scan(open(path, encoding="utf-8").read()):
            print(f"{path}:{n}: {c}")
            bad += 1
    sys.exit(1 if bad else 0)
