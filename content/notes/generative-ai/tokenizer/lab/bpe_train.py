"""バイト単位の小さな BPE を学習し、結合が進む様子を表示する（標準ライブラリだけ）。

使い方:
    git show 9bbbeb23:content/notes/blockchain-systems/wallet/index.md > wallet.md
    python3 bpe_train.py wallet.md [結果の JSON]
"""
import json
import re
import sys
from collections import Counter

from texts import SHORT, TEXTS

MERGES = 1000
CHECKPOINTS = [0, 10, 50, 100, 300, 1000]


def pairs_of(word):
    return zip(word, word[1:])


def merge(word, pair, new):
    out, i = [], 0
    while i < len(word):
        if i + 1 < len(word) and (word[i], word[i + 1]) == pair:
            out.append(new)
            i += 2
        else:
            out.append(word[i])
            i += 1
    return tuple(out)


def train(text, n):
    # 空白・記号で区切った断片の中だけで結合する（断片をまたぐトークンは作らない）
    pieces = Counter(re.findall(r"\w+|[^\w\s]+|\s+", text))
    words = {tuple(p.encode()): c for p, c in pieces.items()}  # 最初は 1 バイト = 1 記号
    vocab = {i: bytes([i]) for i in range(256)}
    merges = []
    for _ in range(n):
        counts = Counter()
        for w, c in words.items():
            for p in pairs_of(w):
                counts[p] += c
        if not counts:
            break
        # 最も多く隣り合う組を 1 つの新しい記号にする（同数なら記号の番号が小さい組）
        pair = min(counts, key=lambda p: (-counts[p], p))
        new = len(vocab)
        vocab[new] = vocab[pair[0]] + vocab[pair[1]]
        merges.append((pair, new, counts[pair]))
        words = {merge(w, pair, new): c for w, c in words.items()}
    return vocab, merges


def encode(s, merges):
    rank = {pair: (r, new) for r, (pair, new, _) in enumerate(merges)}
    out = []
    for piece in re.findall(r"\w+|[^\w\s]+|\s+", s):
        w = tuple(piece.encode())
        while True:  # 学習で早く覚えた組から順に結合する
            cands = [rank[p] for p in pairs_of(w) if p in rank]
            if not cands:
                break
            r, new = min(cands)
            w = merge(w, merges[r][0], new)
        out.extend(w)
    return out


def show(b):
    return b.decode("utf-8", "backslashreplace")


def main():
    text = open(sys.argv[1], encoding="utf-8").read()
    vocab, merges = train(text, MERGES)
    print(f"corpus: {len(text):,} chars, {len(text.encode()):,} bytes")
    print("first merges (new symbol <- pair, count)")
    for k, (pair, new, c) in enumerate(merges[:12], 1):
        a, b = (show(vocab[x]) for x in pair)
        print(f"  #{k:<3} [{show(vocab[new])}] <- [{a}] + [{b}]  ({c})")
    for m in CHECKPOINTS:
        print(f"\nafter {m} merges")
        for key in ("ja", "en"):
            ids = encode(SHORT[key], merges[:m])
            print(f"  {key} {len(ids):>3}  " + "|".join(show(vocab[i]) for i in ids))
    # グラフ用: Wallet の 2 文と英訳のトークン数を、結合の回数ごとに数える
    steps = list(range(0, MERGES + 1, 25))
    curve = {k: [len(encode(TEXTS[k], merges[:m])) for m in steps] for k in ("ja", "en")}
    print("\nWallet passage: " + ", ".join(
        f"{k} {v[0]} -> {v[-1]} tokens" for k, v in curve.items()))
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w") as f:
            json.dump({"merges": steps, "tokens": curve}, f)


if __name__ == "__main__":
    main()
