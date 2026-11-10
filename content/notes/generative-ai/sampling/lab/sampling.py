"""temperature と top-p で次のトークンの選ばれ方がどう変わるかを数える。

ロジットは説明用に決めた値で、実在のモデルの出力ではない。
    python3 lab/sampling.py
"""
import numpy as np

TOKENS = ["晴れ", "雨", "曇り", "雪", "最高", "微妙", "カレー"]
LOGITS = np.array([3.0, 2.2, 2.0, 0.8, 0.5, 0.0, -2.0])


def probs(logits, temperature):
    z = logits / temperature
    z = z - z.max()  # exp の桁あふれを防ぐ
    p = np.exp(z)
    return p / p.sum()


def top_p_filter(p, top_p):
    order = np.argsort(p)[::-1]
    keep = np.cumsum(p[order]) - p[order] < top_p  # 累積が top_p に届くまで残す
    q = np.zeros_like(p)
    q[order[keep]] = p[order[keep]]
    return q / q.sum()


def main():
    rng = np.random.default_rng(1)
    N = 10_000
    for label, t, top_p in [("T=0.5", 0.5, 1.0), ("T=1.0", 1.0, 1.0),
                            ("T=1.5", 1.5, 1.0), ("T=1.0, top_p=0.9", 1.0, 0.9)]:
        p = top_p_filter(probs(LOGITS, t), top_p)
        counts = np.bincount(rng.choice(len(TOKENS), size=N, p=p), minlength=len(TOKENS))
        row = "  ".join(f"{tok}:{c:5d}" for tok, c in zip(TOKENS, counts))
        print(f"{label:<17} {row}")
    print("T→0 (greedy)     ", TOKENS[int(np.argmax(LOGITS))], "だけが選ばれる")


if __name__ == "__main__":
    main()
