"""1 度止まったサーバーに、再試行の方式ごとに要求がどう戻ってくるかを数える。

Python 標準ライブラリだけで動く、10 ms 刻みの離散時間のシミュレーション。

前提（本文の「実験の条件」と同じ）:
- 1,000 のクライアントが t = 0 に 1 回ずつ要求を送る。サーバーは起動中で、
  t = 0〜1 s の間は全ての要求を失敗で返す。
- 動いている間の容量は 10 ms あたり 5 件（毎秒 500 件）。容量を超えた分は
  無作為に選んで失敗（503 のような過負荷の応答）を返す。
- 直近 100 ms に届いた要求が容量の 2 倍（100 件）を超えると、サーバーは
  過負荷で落ち、1 s 止まってから戻る。止まっている間に届いた要求も失敗する。
- 失敗を受けたクライアントは、方式ごとの待ち時間の後に同じ要求を送り直す。
  回数の上限は付けず、全員が成功するか 120 s を過ぎるまで続ける。
"""

import json
import random
import sys

TICK = 0.01             # s
CAPACITY = 5            # 1 tick あたりに処理できる件数
WINDOW = 10             # 過負荷を判定する窓（tick）= 100 ms
CRASH_LIMIT = 2 * CAPACITY * WINDOW
RESTART = 1.0           # s。落ちてから戻るまで
FIRST_DOWN = 1.0        # s。最初に止まっている時間
CLIENTS = 1000
HORIZON = 120.0         # s
BASE, CAP = 0.1, 10.0   # 指数バックオフの初期値と上限（s）
FIXED = 1.0             # 固定間隔（s）


def expo(n):
    return min(CAP, BASE * 2 ** n)


class Immediate:
    def wait(self, n, rng):
        return 0.0


class Fixed:
    def wait(self, n, rng):
        return FIXED


class Expo:
    def wait(self, n, rng):
        return expo(n)


class FullJitter:
    def wait(self, n, rng):
        return rng.uniform(0, expo(n))


class EqualJitter:
    def wait(self, n, rng):
        v = expo(n)
        return v / 2 + rng.uniform(0, v / 2)


class Decorrelated:
    def __init__(self):
        self.sleep = BASE

    def wait(self, n, rng):
        self.sleep = min(CAP, rng.uniform(BASE, self.sleep * 3))
        return self.sleep


STRATEGIES = {
    "immediate": Immediate,
    "fixed 1s": Fixed,
    "exponential": Expo,
    "full jitter": FullJitter,
    "equal jitter": EqualJitter,
    "decorrelated": Decorrelated,
}


def run(name, seed, spread=0.0):
    rng = random.Random(seed)
    ticks = int(HORIZON / TICK)
    schedule = [[] for _ in range(ticks + 1)]   # tick -> 送るクライアントの番号
    policies = [STRATEGIES[name]() for _ in range(CLIENTS)]
    failures = [0] * CLIENTS
    for c in range(CLIENTS):                    # spread > 0 なら最初の送信を散らす
        schedule[int(rng.uniform(0, spread) / TICK)].append(c)
    down_until = int(FIRST_DOWN / TICK)
    arrivals, crashes = [], []
    recent = [0] * WINDOW
    done, sent, finish = 0, 0, None
    for t in range(ticks):
        batch = schedule[t]
        arrivals.append(len(batch))
        sent += len(batch)
        recent[t % WINDOW] = len(batch)
        if t >= down_until and sum(recent) > CRASH_LIMIT:
            down_until = t + int(RESTART / TICK)   # 過負荷で落ちる
            crashes.append(round(t * TICK, 2))
        if t < down_until:
            ok = set()
        else:
            ok = set(rng.sample(batch, min(CAPACITY, len(batch))))
        for c in batch:
            if c in ok:
                done += 1
                continue
            failures[c] += 1
            w = policies[c].wait(failures[c], rng)
            nt = t + 1 + int(round(w / TICK))
            if nt <= ticks:
                schedule[nt].append(c)
        if done == CLIENTS:
            finish = round((t + 1) * TICK, 2)
            break
    return {"finish": finish, "sent": sent, "crashes": crashes,
            "arrivals": arrivals}


def main(out=None, spread=0.0):
    seeds = range(20)
    summary = {}
    print(f"{'strategy':<13} {'finish s (mean, min-max)':>26} "
          f"{'requests (mean, min-max)':>28} {'crashes':>8}")
    for name in STRATEGIES:
        rs = [run(name, s, spread) for s in seeds]
        fin = [r["finish"] if r["finish"] is not None else HORIZON for r in rs]
        unfinished = sum(r["finish"] is None for r in rs)
        sent = [r["sent"] for r in rs]
        cr = [len(r["crashes"]) for r in rs]
        mark = f" ({unfinished} unfinished)" if unfinished else ""
        print(f"{name:<13} {sum(fin)/len(fin):>9.2f} ({min(fin):6.2f}-{max(fin):6.2f})"
              f" {sum(sent)/len(sent):>11.0f} ({min(sent):6d}-{max(sent):6d})"
              f" {sum(cr)/len(cr):>8.1f}{mark}")
        summary[name] = {"finish": fin, "sent": sent, "crashes": cr,
                         "unfinished": unfinished,
                         "timeline_seed0": rs[0]["arrivals"][:3000],
                         "crash_times_seed0": rs[0]["crashes"]}
    if out:
        with open(out, "w") as f:
            json.dump(summary, f)


if __name__ == "__main__":
    # python3 herd.py [out.json] [spread 秒]
    main(sys.argv[1] if len(sys.argv) > 1 else None,
         float(sys.argv[2]) if len(sys.argv) > 2 else 0.0)
