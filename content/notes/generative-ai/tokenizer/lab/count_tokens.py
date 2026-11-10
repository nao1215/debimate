"""同じ内容の文を 4 つのトークナイザーで区切り、文字数・バイト数・トークン数を比べる。

使い方:
    TIKTOKEN_CACHE_DIR=<保存先>/tiktoken \
      uv run --with tiktoken==0.12.0 --with tokenizers==0.22.1 \
      python count_tokens.py <fetch.sh の保存先> [結果の JSON]
"""
import json
import re
import sys

import tiktoken
from tokenizers import Tokenizer

from texts import SHORT, TEXTS


def byte_level_table():
    """GPT-2 系の ByteLevel が 1 バイトを 1 文字に写す表の逆引き。"""
    bs = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {chr(c): b for b, c in zip(bs, cs)}


def load(root):
    inv = byte_level_table()

    def tk(enc):
        def f(s):
            ids = enc.encode(s, disallowed_special=())
            return [enc.decode_single_token_bytes(i) for i in ids]
        return f

    def qwen(t):  # ByteLevel: トークンの文字列を元のバイト列に戻す
        def f(s):
            toks = t.encode(s, add_special_tokens=False).tokens
            return [bytes(inv[c] for c in tok) for tok in toks]
        return f

    def spm(t):  # SentencePiece 形式: <0xE3> はバイト、▁ は空白
        def f(s):
            out = []
            for tok in t.encode(s, add_special_tokens=False).tokens:
                m = re.fullmatch(r"<0x([0-9A-F]{2})>", tok)
                out.append(bytes([int(m[1], 16)]) if m else tok.replace("\u2581", " ").encode())
            return out
        return f

    return {
        "o200k_base": tk(tiktoken.get_encoding("o200k_base")),
        "cl100k_base": tk(tiktoken.get_encoding("cl100k_base")),
        "Qwen3": qwen(Tokenizer.from_file(f"{root}/qwen3/tokenizer.json")),
        "LLM-jp-3": spm(Tokenizer.from_file(f"{root}/llmjp3/tokenizer.json")),
    }


def main():
    root = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    toks = load(root)
    result = {"counts": {}, "short": {}}

    print(f"{'text':<7}{'chars':>6}{'bytes':>6}  " +
          "".join(f"{n:>12}" for n in toks))
    for key, s in TEXTS.items():
        row = {"chars": len(s), "bytes": len(s.encode())}
        for name, fn in toks.items():
            row[name] = len(fn(s))
        result["counts"][key] = row
        print(f"{key:<7}{row['chars']:>6}{row['bytes']:>6}  " +
              "".join(f"{row[n]:>12}" for n in toks))

    print("\nchars per token")
    for key in ("ja", "en"):
        row = result["counts"][key]
        print(f"{key:<7}" + "".join(f"{row['chars'] / row[n]:>12.2f}" for n in toks))

    print("\nsplit of short sentences ('|' = token boundary, \\xNN = part of a char)")
    for key, s in SHORT.items():
        for name, fn in toks.items():
            ps = fn(s)
            shown = "|".join(p.decode("utf-8", "backslashreplace") for p in ps)
            result["short"].setdefault(key, {})[name] = [list(p) for p in ps]
            print(f"{key} {name:<12}{len(ps):>3}  {shown}")

    if out_path:
        with open(out_path, "w") as f:
            json.dump(result, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
