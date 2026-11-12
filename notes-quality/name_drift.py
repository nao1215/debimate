#!/usr/bin/env python3
"""呼び名のブレを、括弧の併記から機械的に見つける。

style_check.sh から呼ばれる。標準入力は、front matter とコードフェンスを
空行へ潰した本文 (行番号は原文と一致する)。

見るのは 2 つ。

1. kanji1 — `語（word）` のように英語と対にして定義した呼び名が 1 文字の漢字で、
   定義した h3 の外でも使われている。読者はその 1 文字が何を指すのか決められない
   (2026-09-04 nonce の「列」、2026-09-06 hash-function の「語」)。
   → 違反として報告する。writing_style.md §22。

2. mixed — 併記した和語と英語の両方を、定義の後も本文で使っている。
   記事で通す呼び名は 1 つに決める。→ 情報として報告する。writing_style.md §24。

出力は 1 件 1 行のタブ区切り。整形は呼び出し側が行う。
"""
import re
import sys

JPA = r"[ぁ-んァ-ヴー一-龥々]"          # 日本語の字全部 (境界の判定に使う)
JPT = r"[ァ-ヴー一-龥々]"                # 呼び名として扱う字種 (ひらがなを含めない)
EN = r"[A-Za-z][A-Za-z0-9._+-]*(?: [A-Za-z][A-Za-z0-9._+-]*)*"


def strip_noise(line):
    """呼び名の使用回数に数えない所を消す。

    見出し・インラインコード・リンクは、本文で呼び名を通しているかの判定に
    入れない。他ノートへのリンク文字列 (`[Hash Function](...)`) を数えると、
    英語名を使い続けているように見えてしまう。
    """
    line = re.sub(r"`[^`]*`", " ", line)
    line = re.sub(r"\[([^\]]*)\]\([^)]*\)", " ", line)
    line = re.sub(r"^#+ .*$", " ", line)
    return line


def main():
    lines = sys.stdin.read().split("\n")

    section, cur = [], 0
    for line in lines:
        if line.startswith("### "):
            cur += 1
        section.append(cur)

    # 括弧の併記から (和語, 英語) の組を拾う。定義した行を覚えておく。
    # 和語側は、直前が日本語でない所からしか取らない。これを外すと
    # 「コミットか中止（abort）」の「か中止」のように文の断片を拾う。
    pairs = {}
    for i, line in enumerate(lines):
        for m in re.finditer(r"(?<![A-Za-z0-9])(" + EN + r")（(" + JPT + r"{1,16})）", line):
            pairs.setdefault((m.group(2), m.group(1)), i)
        for m in re.finditer(r"(?<!" + JPA + r")(" + JPT + r"{1,16})（(" + EN + r")）", line):
            pairs.setdefault((m.group(1), m.group(2)), i)

    def used(pattern, defined_at):
        return [i for i, line in enumerate(lines)
                if i != defined_at and re.search(pattern, strip_noise(line))]

    for (jp, en), defined_at in sorted(pairs.items(), key=lambda kv: kv[1]):
        # 和語は前後を漢字・カタカナに挟まれていない所だけ数える
        # (「語」を数える時に「用語」「単語」「訳語」を拾わないため)
        jp_hits = used(r"(?<![ァ-ヴー一-龥])" + re.escape(jp) + r"(?![一-龥])", defined_at)
        en_hits = used(r"(?<![A-Za-z0-9])" + re.escape(en) + r"(?![A-Za-z0-9])", defined_at)
        crossing = [i for i in jp_hits if section[i] != section[defined_at]]

        if len(jp) == 1 and re.match(r"[一-龥]", jp) and crossing:
            print("kanji1\t%s\t%s\t%d\t%s" % (
                jp, en, defined_at + 1,
                ",".join(str(i + 1) for i in crossing[:6])))
        elif jp_hits and en_hits:
            print("mixed\t%s\t%s\t%d\t%s\t%s" % (
                jp, en, defined_at + 1,
                ",".join(str(i + 1) for i in jp_hits[:5]),
                ",".join(str(i + 1) for i in en_hits[:5])))


if __name__ == "__main__":
    main()
