"""Consistent Hashing のノートの実験（Python 3 の標準ライブラリだけで動く）。

    python3 experiment.py > output.txt

キーとサーバー名の位置は MD5 の先頭 8 バイトで決める。乱数を使う所は
シードを固定しているので、何度走らせても同じ数字が出る。
結果は output.txt（人が読む形）と results.json（図を描く側が読む形）に出る。
"""
import json
import random
import statistics
import subprocess
import sys
from bisect import bisect_left
from collections import Counter
from hashlib import md5
from pathlib import Path

SPACE = 2**64
KEYS = [f"user:{i}" for i in range(100_000)]


def h(text):
    return int.from_bytes(md5(text.encode()).digest()[:8], "big")


KEY_HASH = [h(k) for k in KEYS]


# --- 振り分け方 -------------------------------------------------------------

def mod_n(servers):
    n = len(servers)
    return [servers[x % n] for x in KEY_HASH]


class Ring:
    """各サーバーを v 個の点としてリングに置き、キーは時計回りで最初の点の持ち主へ。"""

    def __init__(self, servers, v):
        pts = sorted((h(f"{s}#{i}"), s) for s in servers for i in range(v))
        self.pos = [p for p, _ in pts]
        self.owner = [s for _, s in pts]

    def index(self, x):
        # x と同じ位置か、それより後ろで最初の点。末尾を越えたら先頭の点に戻る
        return bisect_left(self.pos, x) % len(self.pos)

    def lookup(self, x):
        return self.owner[self.index(x)]

    def assign(self):
        return [self.lookup(x) for x in KEY_HASH]

    def arc_share(self):
        """リングの弧の長さから、キーが無限にある時に受け持つ割合を出す。"""
        share = Counter()
        n = len(self.pos)
        for i in range(n):
            prev = self.pos[i - 1] if i else self.pos[-1] - SPACE
            share[self.owner[i]] += (self.pos[i] - prev) / SPACE
        return share


def jump(servers):
    """Lamping と Veach の Jump Consistent Hash。番号 0..n-1 のバケツを返す。"""
    n = len(servers)
    out = []
    for key in KEY_HASH:
        b, j = -1, 0
        while j < n:
            b = j
            key = (key * 2862933555777941757 + 1) % SPACE
            j = int((b + 1) * (float(1 << 31) / float((key >> 33) + 1)))
        out.append(servers[b])
    return out


def rendezvous(servers):
    """Rendezvous（HRW）: キーとサーバー名を組にしたハッシュが最大のサーバー。"""
    out = []
    for k in KEYS:
        out.append(max(servers, key=lambda s: h(f"{s}|{k}")))
    return out


def maglev(servers, m=65537):
    """Maglev の参照表（論文の Pseudocode 1）。表の大きさ m は素数。"""
    n = len(servers)
    offset = [h(f"off:{s}") % m for s in servers]
    skip = [h(f"skip:{s}") % (m - 1) + 1 for s in servers]
    nxt = [0] * n
    table = [-1] * m
    filled = 0
    while True:
        for i in range(n):
            c = (offset[i] + nxt[i] * skip[i]) % m
            while table[c] >= 0:
                nxt[i] += 1
                c = (offset[i] + nxt[i] * skip[i]) % m
            table[c] = i
            nxt[i] += 1
            filled += 1
            if filled == m:
                return [servers[table[x % m]] for x in KEY_HASH]


def moved(before, after):
    return sum(a != b for a, b in zip(before, after)) / len(before)


def shares(assign, servers):
    c = Counter(assign)
    return {s: c[s] / len(assign) for s in servers}


def pct(x):
    return f"{x * 100:5.1f}%"


R = {}

# --- 1. 3 台から 4 台へ ------------------------------------------------------
print("## 1. cache-1..3 に cache-4 を足す（キー 100,000 個）")
s3 = ["cache-1", "cache-2", "cache-3"]
s4 = s3 + ["cache-4"]
R["add"] = {}
for label, f3, f4 in [
    ("mod", lambda: mod_n(s3), lambda: mod_n(s4)),
    ("ring1", lambda: Ring(s3, 1).assign(), lambda: Ring(s4, 1).assign()),
    ("ring100", lambda: Ring(s3, 100).assign(), lambda: Ring(s4, 100).assign()),
]:
    a3, a4 = f3(), f4()
    from_ = Counter(b for b, a in zip(a3, a4) if a != b)
    if label != "mod":
        # リングでは、保存先が変わったキーは全て足した cache-4 へ行く
        assert all(a == "cache-4" for b, a in zip(a3, a4) if a != b)
    R["add"][label] = {
        "moved": moved(a3, a4),
        "before": shares(a3, s3),
        "after": shares(a4, s4),
        "moved_from": {s: from_[s] / len(KEYS) for s in s3},
    }
    print(f"{label:8s} moved={pct(moved(a3, a4))}  from=" +
          " ".join(f"{s}:{pct(from_[s] / len(KEYS))}" for s in s3))
    print("         before " + " ".join(f"{s}:{pct(v)}" for s, v in shares(a3, s3).items()))
    print("         after  " + " ".join(f"{s}:{pct(v)}" for s, v in shares(a4, s4).items()))

# --- 2. 名前を変えて 1,000 回 -------------------------------------------------
print("\n## 2. サーバー名を変えて 1,000 回（1 台 1 点、3 台→4 台、弧の長さで計算）")
moves, maxes = [], []
for t in range(1000):
    names = [f"t{t}-cache-{j}" for j in range(1, 5)]
    a = Ring(names[:3], 1).arc_share()
    b = Ring(names, 1).arc_share()
    moves.append(b[names[3]])          # 新しいサーバーが取った分だけが動く
    maxes.append(max(a.values()) * 3)  # 3 台の時の最大の割合 / 平均
moves.sort()
maxes.sort()
q = lambda xs, p: xs[int(p * (len(xs) - 1))]
R["trials"] = {"moves": moves, "max3": maxes}
print(f"動いた割合: 最小 {pct(moves[0])} 中央 {pct(q(moves, .5))} 最大 {pct(moves[-1])}")
print(f"1 台に偏った度合い（最大の割合 / 平均）: 中央 {q(maxes, .5):.2f} 倍  95% 点 {q(maxes, .95):.2f} 倍")
print(f"最大の割合が 50% を超えた回: {sum(m / 3 > .5 for m in maxes)} / 1000")

# --- 3. 仮想ノードの数 ---------------------------------------------------------
print("\n## 3. 10 台、仮想ノードの数ごとの偏り（名前を変えて 200 回、弧の長さで計算）")
R["vnodes"] = {}
for v in [1, 4, 16, 64, 256, 1024]:
    ratios = []
    for t in range(200):
        names = [f"v{t}-node-{j}" for j in range(10)]
        sh = Ring(names, v).arc_share()
        ratios.append(max(sh.values()) * 10)
    ratios.sort()
    R["vnodes"][v] = ratios
    print(f"v={v:5d}  最大/平均 中央 {q(ratios, .5):.2f}  95% 点 {q(ratios, .95):.2f}  点の数 {10 * v}")

# --- 4. 1 台が落ちた時 ---------------------------------------------------------
print("\n## 4. 4 台から cache-2 を外す。cache-2 のキーがどこへ行くか")
R["fail"] = {}
s4b = ["cache-1", "cache-3", "cache-4"]
for label, v in [("ring1", 1), ("ring100", 100)]:
    a4 = Ring(s4, v).assign()
    a3 = Ring(s4b, v).assign()
    to = Counter(b for a, b in zip(a4, a3) if a == "cache-2")
    # 外した cache-2 のキーだけが動き、他のキーの保存先は変わらない
    assert all(a == b for a, b in zip(a4, a3) if a != "cache-2")
    R["fail"][label] = {
        "before": shares(a4, s4),
        "after": shares(a3, s4b),
        "to": {s: to[s] / len(KEYS) for s in s4b},
    }
    print(f"{label:8s} 引き継ぎ " + " ".join(f"{s}:{pct(to[s] / len(KEYS))}" for s in s4b))
    print("         after  " + " ".join(f"{s}:{pct(v)}" for s, v in shares(a3, s4b).items()))

# --- 5. 複製を次の点に置く ----------------------------------------------------
print("\n## 5. 仮想ノード 100 個で、複製 3 つを時計回りの次の点から取る")
R["replica"] = {}
for n in [3, 4, 6, 10]:
    names = [f"node-{j}" for j in range(1, n + 1)]
    ring = Ring(names, 100)
    bad = 0
    for x in KEY_HASH:
        i = ring.index(x)
        picked = {ring.owner[(i + k) % len(ring.pos)] for k in range(3)}
        bad += len(picked) < 3
    R["replica"][n] = bad / len(KEYS)
    print(f"{n:3d} 台: 3 つの複製のうち 2 つ以上が同じサーバーに載るキー {pct(bad / len(KEYS))}")

# --- 6. 人気のキー -------------------------------------------------------------
print("\n## 6. 4 台・仮想ノード 100 個。要求の数が Zipf（s=1）に従う時")
ring = Ring(s4, 100)
a = ring.assign()
rng = random.Random(1)
rank = list(range(len(KEYS)))
rng.shuffle(rank)                      # どのキーが人気かはハッシュと無関係
weight = [1 / (r + 1) for r in rank]
total = sum(weight)
req = Counter()
for s, w in zip(a, weight):
    req[s] += w / total
top = max(range(len(KEYS)), key=lambda i: weight[i])
R["hot"] = {
    "keys": shares(a, s4),
    "requests": {s: req[s] for s in s4},
    "top_share": weight[top] / total,
    "top_owner": a[top],
    "top10_share": sum(sorted(weight, reverse=True)[:10]) / total,
}
print("キーの数   " + " ".join(f"{s}:{pct(v)}" for s, v in shares(a, s4).items()))
print("要求の数   " + " ".join(f"{s}:{pct(req[s])}" for s in s4))
print(f"1 番人気のキー {KEYS[top]} だけで要求の {pct(weight[top] / total)}（持ち主 {a[top]}）")
print(f"上位 10 個のキーで要求の {pct(R['hot']['top10_share'])}")

# --- 7. 他の振り分け方 ----------------------------------------------------------
print("\n## 7. 振り分け方の比較（キー 100,000 個）")
print("   足す: 3 台→4 台  外す: 4 台から cache-2  偏り: 4 台での最大の割合/平均")
R["compare"] = {}
methods = {
    "mod": mod_n,
    "ring1": lambda s: Ring(s, 1).assign(),
    "ring100": lambda s: Ring(s, 100).assign(),
    "jump": jump,
    "rendezvous": rendezvous,
    "maglev": maglev,
}
for label, f in methods.items():
    a3, a4, a3b = f(s3), f(s4), f(s4b)
    sh = shares(a4, s4)
    row = {"add": moved(a3, a4), "remove": moved(a4, a3b),
           "imbalance": max(sh.values()) * 4}
    R["compare"][label] = row
    print(f"{label:11s} 足す {pct(row['add'])}  外す {pct(row['remove'])}  偏り {row['imbalance']:.2f}")

# --- 8. Python の hash() -------------------------------------------------------
print("\n## 8. 組み込みの hash() で選ぶと、プロセスごとに保存先が変わる")
code = "print(hash('user:42') % 4)"
R["pyhash"] = {}
for seed in ["1", "2", "3"]:
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env={"PYTHONHASHSEED": seed}).stdout.strip()
    R["pyhash"][seed] = int(out)
    print(f"PYTHONHASHSEED={seed}: user:42 -> サーバー {out}")

Path(__file__).with_name("results.json").write_text(json.dumps(R, ensure_ascii=False))
