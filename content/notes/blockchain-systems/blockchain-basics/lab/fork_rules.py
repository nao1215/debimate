"""規則を変えた時に、チェーンが 1 本に戻るかを試す小さなブロックチェーン。

2 つのノードの組（古い規則・新しい規則）が、本物の SHA-256 で Proof of Work を解きながら
ブロックを作る。見つけたブロックはすぐ両方に届き、各ノードは自分の規則で有効と判断できる
ブロックだけで作れる列のうち、最も長い列（難易度が一定なので、最も計算量が多い列）を選ぶ。

規則はブロックの大きさの上限だけにした。
  古い規則            1000 バイトまで
  厳しくした規則      500 バイトまで（ソフトフォーク）
  緩めた規則          2000 バイトまで（ハードフォーク）

最も割れやすい条件として、規則の違いに触れるブロックを毎回作らせる。
  厳しくした場合: 古い規則のマイナーは 800 バイト（新しい規則では無効）、新しい規則のマイナーは 400 バイト
  緩めた場合:     古い規則のマイナーは 800 バイト（どちらでも有効）、新しい規則のマイナーは 1500 バイト（古い規則では無効）

実行: python3 fork_rules.py > output.txt
"""

import hashlib
import json
import sys

BITS = 12                     # ハッシュ値の先頭 12 ビットが 0 なら成功（平均 4,096 回に 1 回）
TARGET = 1 << (256 - BITS)
BLOCKS = 100                  # 両方の組を合わせて、このブロック数が見つかるまで掘る
SEEDS = 20
OLD_LIMIT = 1000
RULES = {"soft": 500, "hard": 2000}
SIZES = {"soft": {"old": 800, "new": 400}, "hard": {"old": 800, "new": 1500}}


class Block:
    def __init__(self, prev, height, miner, size, salt):
        self.prev, self.height, self.miner, self.size = prev, height, miner, size
        body = hashlib.sha256(f"{salt}:{miner}:{height}".encode()).digest()
        self.header = (prev.hash if prev else b"\0" * 32) + height.to_bytes(4, "little") + body + size.to_bytes(4, "little")
        self.hash = None

    def try_nonce(self, nonce):
        h = hashlib.sha256(self.header + nonce.to_bytes(8, "little")).digest()
        if int.from_bytes(h, "big") < TARGET:
            self.hash = h
            return True
        return False


class Node:
    """1 つの規則でブロックを検証し、最も長い有効な列の先頭（tip）を持つ。"""

    def __init__(self, limit, genesis):
        self.limit, self.tip, self.valid = limit, genesis, {genesis.hash}

    def receive(self, block):
        if block.size > self.limit or block.prev.hash not in self.valid:
            return False                     # 自分の規則で無効、または無効な親の子
        self.valid.add(block.hash)
        if block.height > self.tip.height:   # 同じ長さなら先に届いた方を保つ
            self.tip = block
        return True

    def chain(self):
        out, b = [], self.tip
        while b.prev:
            out.append(b)
            b = b.prev
        return out[::-1]


def split(a, b):
    """2 つの列が共有する先頭からの長さと、そこから先の長さ（a 側、b 側）。"""
    common = 0
    while common < min(len(a), len(b)) and a[common] is b[common]:
        common += 1
    return common, len(a) - common, len(b) - common


def run(kind, new_share, seed, record=False):
    genesis = Block(None, 0, "genesis", 0, "g")
    genesis.hash = b"\0" * 32
    nodes = {"old": Node(OLD_LIMIT, genesis), "new": Node(RULES[kind], genesis)}
    share = {"new": round(new_share * 10), "old": 10 - round(new_share * 10)}
    work = {g: Block(nodes[g].tip, nodes[g].tip.height + 1, g, SIZES[kind][g], f"{seed}:0") for g in nodes}
    nonce = {"old": 0, "new": 0}
    attempts, found, events, serial = 0, 0, [], 0
    mined = {"old": 0, "new": 0}
    while found < BLOCKS:
        for g in ("new", "old"):             # 10 回の試行を計算量の割合で分ける
            for _ in range(share[g]):
                attempts += 1
                if not work[g].try_nonce(nonce[g]):
                    nonce[g] += 1
                    continue
                block, found = work[g], found + 1
                mined[g] += 1
                for n in nodes.values():
                    n.receive(block)
                if record:
                    events.append({"attempt": attempts, "miner": g,
                                   "old": [b.miner for b in nodes["old"].chain()],
                                   "new": [b.miner for b in nodes["new"].chain()],
                                   "common": split(nodes["old"].chain(), nodes["new"].chain())[0]})
                for h in nodes:              # 先頭が変わった組は、新しい先頭の上で掘り直す
                    if work[h] is block or work[h].prev is not nodes[h].tip:
                        serial += 1
                        work[h] = Block(nodes[h].tip, nodes[h].tip.height + 1, h, SIZES[kind][h], f"{seed}:{serial}")
                        nonce[h] = 0
                break
            else:
                continue
            break
    old, new = nodes["old"].chain(), nodes["new"].chain()
    common, old_only, new_only = split(old, new)
    return {"kind": kind, "new_share": new_share, "seed": seed, "attempts": attempts,
            "common": common, "old_only": old_only, "new_only": new_only,
            # 自分の組のノードの列から外れたブロックの割合（マイナーにとっては報酬を失ったブロック）
            "old_lost": 1 - sum(b.miner == "old" for b in old) / mined["old"],
            "new_lost": 1 - sum(b.miner == "new" for b in new) / mined["new"],
            "events": events}


def main():
    cases = [("soft", 0.7), ("soft", 0.3), ("hard", 0.7), ("hard", 0.3)]
    print(f"# difficulty {BITS} bits, {BLOCKS} blocks per run, {SEEDS} seeds")
    print("# common = blocks both nodes share; old_only / new_only = blocks after the split (median of seeds, then min-max)")
    print("# old_lost / new_lost = share of blocks a group mined that fell off its own node's chain (median)")
    print("kind new_share  common  old_only  new_only  old_lost  new_lost")
    trace = {}
    for kind, s in cases:
        rs = [run(kind, s, seed, record=(seed == 1)) for seed in range(1, SEEDS + 1)]
        def stat(k):
            v = sorted(r[k] for r in rs)
            return f"{v[SEEDS // 2]:>3} ({v[0]}-{v[-1]})"
        lost = lambda k: sorted(r[k] for r in rs)[SEEDS // 2]  # noqa: E731
        print(f"{kind} {s:.1f}  {stat('common')}  {stat('old_only')}  {stat('new_only')}  {lost('old_lost'):.0%}  {lost('new_lost'):.0%}")
        trace[f"{kind}-{s}"] = rs[0]
    with open("trace.json", "w") as f:
        json.dump(trace, f)
    print("# seed 1, chain each node holds at the end (o = old-rule miner, n = new-rule miner)")
    for key, r in trace.items():
        print(key, "old:", "".join(m[0] for m in r["events"][-1]["old"]))
        print(key, "new:", "".join(m[0] for m in r["events"][-1]["new"]))


if __name__ == "__main__":
    sys.exit(main())
