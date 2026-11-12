"""同じ到着列を各方式に通し、通した件数を数える。Python 標準ライブラリだけで動く。

上限は「60 秒あたり 60 件」に揃える。トークンバケットは 1 秒に 1 個溜まり、
容量 60（ウィンドウと同じ量を一度に許す）と容量 10 の 2 通りを試す。

  python3 simulate.py            # 結果を表示し、results.json に書く
"""
import json
import math
import os
from fractions import Fraction

from limiters import (GCRA, FixedWindow, LeakyBucketQueue, SlidingLog,
                      SlidingWindowCounter, TokenBucket)

LIMIT, WINDOW = 60, 60.0


def make_limiters():
    return {
        "fixed": FixedWindow(LIMIT, WINDOW),
        "log": SlidingLog(LIMIT, WINDOW),
        "counter": SlidingWindowCounter(LIMIT, WINDOW),
        "bucket60": TokenBucket(rate=1.0, capacity=60),
        "bucket10": TokenBucket(rate=1.0, capacity=10),
    }


def boundary_burst():
    """ウィンドウの境目（60 秒）の前後 1 秒に 60 件ずつ。59.0〜60.0 秒と 60.0〜61.0 秒に均等に並べる。"""
    return [59 + i / 60 for i in range(60)] + [60 + i / 60 for i in range(60)]


def idle_then_steady():
    """100 秒の間なにも送らず、100 秒から 220 秒まで 1 秒に 2 件ずつ送る。"""
    return [100 + i / 2 for i in range(240)]


def max_in_window(times, span):
    """通した時刻の列で、長さ span 秒の任意の区間（左を含み右を含まない）に入る最大件数。"""
    best, j = 0, 0
    for i in range(len(times)):
        while times[i] - times[j] >= span:
            j += 1
        best = max(best, i - j + 1)
    return best


def run(arrivals):
    out = {}
    for name, lim in make_limiters().items():
        passed = [t for t in arrivals if lim.allow(t)]
        out[name] = {
            "passed": len(passed),
            "max_60s": max_in_window(passed, 60.0),
            "max_2s": max_in_window(passed, 2.0),
            "times": passed,
        }
    q = LeakyBucketQueue(rate=1.0, size=10)
    done, waits = [], []
    for t in arrivals:
        ok, start = q.allow(t)
        if ok:
            done.append(start)
            waits.append(start - t)
    out["leaky_queue"] = {
        "passed": len(done),
        "max_60s": max_in_window(done, 60.0),
        "max_2s": max_in_window(done, 2.0),
        "times": done,              # こちらは処理された時刻
        "max_wait": max(waits),
    }
    return out


def gcra_equivalence():
    """トークンバケット（rate r、容量 b）と GCRA(I = 1/r, L = (b-1)/r) が、
    同じ到着列に同じ判定を返すかを確かめる。丸め誤差を避けるため Fraction で計算する。"""
    import random
    rng = random.Random(20261111)
    mismatches, total = 0, 0
    for _ in range(200):
        r = Fraction(rng.choice([1, 2, 5]))
        b = rng.choice([1, 3, 10, 60])
        tb, g = TokenBucket(r, b), GCRA(1 / r, Fraction(b - 1) / r)
        t = Fraction(0)
        for _ in range(300):
            t += Fraction(rng.randint(0, 40), 20)     # 0〜2 秒の間隔（0.05 秒刻み）
            total += 1
            mismatches += tb.allow(t) != g.allow(t)
    return {"arrivals": total, "mismatches": mismatches}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    results = {
        "limit": LIMIT, "window": WINDOW,
        "boundary_burst": run(boundary_burst()),
        "idle_then_steady": run(idle_then_steady()),
        "gcra_equivalence": gcra_equivalence(),
    }
    for key, title in [("boundary_burst", "境目の前後 1 秒に 60 件ずつ（計 120 件）"),
                       ("idle_then_steady", "100 秒から 1 秒に 2 件を 120 秒（計 240 件）")]:
        print(f"# {title}")
        print(f"{'method':12} {'passed':>6} {'max_60s':>7} {'max_2s':>6}")
        for name, r in results[key].items():
            print(f"{name:12} {r['passed']:6} {r['max_60s']:7} {r['max_2s']:6}")
        print(f"leaky_queue の最大の待ち: {results[key]['leaky_queue']['max_wait']:.2f} 秒")
        print()
    eq = results["gcra_equivalence"]
    print(f"# GCRA とトークンバケット: {eq['arrivals']} 件中 判定の違い {eq['mismatches']} 件")
    with open(os.path.join(here, "results.json"), "w") as f:
        json.dump(results, f, indent=1)


if __name__ == "__main__":
    main()
