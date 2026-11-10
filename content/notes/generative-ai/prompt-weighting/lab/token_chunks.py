"""プロンプトを CLIP のトークンに分け、ComfyUI と同じ規則で 77 トークンの区切りに詰める。

ComfyUI v0.35.0 の comfy/sd1_clip.py の parse_parentheses()・token_weights()・
SDTokenizer.tokenize_with_weights() の詰め方を、埋め込み（embedding:）の処理を除いて写した。
括弧で区切った塊（重みの付いた部分と、付いていない部分）ごとに tokenizer に通し、
塊が区切りに収まらない時は、8 トークン以上の塊なら区切りの途中で割り、
8 トークン未満の塊なら丸ごと次の区切りへ送る。

使い方:
    uv run --with transformers python token_chunks.py <ComfyUI の comfy/sd1_tokenizer> "<プロンプト>"
"""
import sys

from transformers import CLIPTokenizer

MAX_LENGTH = 77      # 始まりと終わりの記号を含む 1 区切りの長さ
MAX_WORD_LENGTH = 8  # これ以上長い塊は区切りの途中で割る


def parse_parentheses(string):
    result, current, depth = [], "", 0
    for ch in string:
        if ch == "(":
            if depth == 0:
                if current:
                    result.append(current)
                current = "("
            else:
                current += ch
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                result.append(current + ")")
                current = ""
            else:
                current += ch
        else:
            current += ch
    if current:
        result.append(current)
    return result


def token_weights(string, current_weight):
    out = []
    for x in parse_parentheses(string):
        weight = current_weight
        if len(x) >= 2 and x[0] == "(" and x[-1] == ")":
            x = x[1:-1]
            colon = x.rfind(":")
            weight *= 1.1                      # 数字の無い (word) は 1.1 倍
            if colon > 0:
                try:
                    weight = float(x[colon + 1:])  # (word:1.3) は掛け算ではなく置き換え
                    x = x[:colon]
                except ValueError:
                    pass
            out += token_weights(x, weight)
        else:
            out += [(x, current_weight)]
    return out


def chunks(tok, text):
    groups = []
    for segment, weight in token_weights(text, 1.0):
        ids = tok(segment)["input_ids"][1:-1]  # 始まり 49406 と終わり 49407 を外す
        if ids:
            groups.append([(t, weight) for t in ids])
    out, batch = [], []
    for group in groups:
        is_large = len(group) >= MAX_WORD_LENGTH
        while group:
            if len(batch) + len(group) > MAX_LENGTH - 2:   # 始まりと終わりの 2 個を除く 75
                if is_large:
                    room = MAX_LENGTH - 2 - len(batch)
                    batch += group[:room]
                    group = group[room:]
                out.append(batch)
                batch = []
            else:
                batch += group
                group = []
    out.append(batch)
    return out


def main():
    tok = CLIPTokenizer.from_pretrained(sys.argv[1])
    text = sys.argv[2]
    for i, batch in enumerate(chunks(tok, text)):
        words = tok.decode([t for t, _ in batch])
        weights = sorted({w for _, w in batch})
        print(f"chunk {i + 1}: {len(batch):2d} tokens, weights {weights}")
        print(f"  {words}")


if __name__ == "__main__":
    main()
