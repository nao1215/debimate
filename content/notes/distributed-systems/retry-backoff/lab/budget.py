"""下流が 10 秒止まった時に、再試行の予算（retry budget）があると負荷がどう変わるかを数える。

Python 標準ライブラリだけで動く、10 ms 刻みの離散時間のシミュレーション。

前提（本文の「実験の条件」と同じ）:
- 10 のクライアントのプロセスが、それぞれ毎秒 30 件（合計毎秒 300 件）の新しい要求を
  ポアソン到着で送る。サーバーの容量は herd.py と同じ毎秒 500 件。
- サーバーは t = 5〜15 s の間止まり、届いた要求を全て失敗で返す。
- herd.py と同じく、直近 100 ms の到着が 100 件を超えると過負荷で落ち、1 s 止まる。
- 再試行は gRPC の retryPolicy の例（maxAttempts 4、initialBackoff 0.1 s、
  backoffMultiplier 2、maxBackoff 1 s、待ち時間に random(0.8, 1.2) を掛ける）に従う。
- 予算は 2 種類。gRPC の retryThrottling（maxTokens 10、tokenRatio 0.1、
  トークンが maxTokens / 2 以下なら再試行しない）と、SRE 本の、クライアントごとの
  再試行の比率を 10% 未満に保つ方式（直近 1 s の送信で数える）。
"""

import json
import math
import random
import sys
from collections import deque

TICK = 0.01
CAPACITY = 5
WINDOW = 10
CRASH_LIMIT = 2 * CAPACITY * WINDOW
RESTART = 1.0
CLIENTS = 10
RATE = 30.0                  # 1 クライアントあたりの新しい要求（毎秒）
OUTAGE = (5.0, 15.0)
HORIZON = 40.0
MAX_ATTEMPTS = 4


def poisson(lam, rng):
    k, p = 0, rng.random()
    term = cum = math.exp(-lam)
    while p > cum:
        k += 1
        term *= lam / k
        cum += term
    return k


def grpc_backoff(n, rng):
    # n 回目の再試行の前の待ち時間（gRFC A6 の式）
    return min(0.1 * 2 ** (n - 1), 1.0) * rng.uniform(0.8, 1.2)


class NoRetry:
    def allow(self, t):
        return False

    def record(self, t, ok, retry):
        pass


class Unlimited:
    def allow(self, t):
        return True

    def record(self, t, ok, retry):
        pass


class GrpcThrottle:
    def __init__(self, max_tokens=10, ratio=0.1):
        self.max, self.ratio, self.tokens = max_tokens, ratio, max_tokens

    def allow(self, t):
        return self.tokens > self.max / 2

    def record(self, t, ok, retry):
        if ok:
            self.tokens = min(self.max, self.tokens + self.ratio)
        else:
            self.tokens = max(0, self.tokens - 1)


class RetryRatio:
    """直近 1 s に送った要求のうち、再試行の割合が 10% 未満の時だけ再試行する。"""

    def __init__(self, limit=0.1, span=1.0):
        self.limit, self.span, self.log = limit, span, deque()

    def allow(self, t):
        while self.log and self.log[0][0] < t - self.span:
            self.log.popleft()
        total = len(self.log)
        retries = sum(1 for _, r in self.log if r)
        return total == 0 or retries / total < self.limit

    def record(self, t, ok, retry):
        self.log.append((t, retry))


POLICIES = {
    "no retry": NoRetry,
    "4 attempts": Unlimited,
    "4 attempts + gRPC throttling": GrpcThrottle,
    "4 attempts + 10% retry ratio": RetryRatio,
}


def run(name, seed):
    rng = random.Random(seed)
    ticks = int(HORIZON / TICK)
    budgets = [POLICIES[name]() for _ in range(CLIENTS)]
    schedule = [[] for _ in range(ticks + 200)]     # (client, attempt)
    arrivals, ok_per_tick, new_per_tick = [], [], []
    down = [(int(OUTAGE[0] / TICK), int(OUTAGE[1] / TICK))]
    recent = [0] * WINDOW
    crashes = []
    failed_ops = 0
    for t in range(ticks):
        now = t * TICK
        batch = list(schedule[t])
        new = 0
        for c in range(CLIENTS):
            k = poisson(RATE * TICK, rng)   # 1 tick に平均 0.3 件
            batch.extend((c, 1) for _ in range(k))
            new += k
        new_per_tick.append(new)
        arrivals.append(len(batch))
        recent[t % WINDOW] = len(batch)
        is_down = any(a <= t < b for a, b in down)
        if not is_down and sum(recent) > CRASH_LIMIT:
            down.append((t, t + int(RESTART / TICK)))
            crashes.append(round(now, 2))
            is_down = True
        if is_down:
            served = set()
        else:
            idx = list(range(len(batch)))
            served = set(rng.sample(idx, min(CAPACITY, len(batch))))
        good = 0
        for i, (c, attempt) in enumerate(batch):
            ok = i in served
            budgets[c].record(now, ok, attempt > 1)
            if ok:
                good += 1
                continue
            if attempt < MAX_ATTEMPTS and budgets[c].allow(now):
                nt = t + 1 + int(round(grpc_backoff(attempt, rng) / TICK))
                schedule[nt].append((c, attempt + 1))
            else:
                failed_ops += 1
        ok_per_tick.append(good)
    return {"arrivals": arrivals, "ok": ok_per_tick, "new": new_per_tick,
            "crashes": crashes, "failed_ops": failed_ops}


def per_second(xs):
    step = int(1 / TICK)
    return [sum(xs[i:i + step]) for i in range(0, len(xs), step)]


def main(out=None):
    seeds = range(20)
    summary = {}
    print(f"{'policy':<30} {'load during outage':>19} {'crashes after':>14} "
          f"{'back to normal at':>18}")
    for name in POLICIES:
        rs = [run(name, s) for s in seeds]
        mult, crash_n, normal = [], [], []
        for r in rs:
            a, n = per_second(r["arrivals"]), per_second(r["new"])
            o = range(int(OUTAGE[0]), int(OUTAGE[1]))
            mult.append(sum(a[i] for i in o) / sum(n[i] for i in o))
            crash_n.append(len(r["crashes"]))
            ok = per_second(r["ok"])
            # 停止の終わり以降、成功が新しい要求の 9 割以上に戻った最初の秒
            back = next((i for i in range(int(OUTAGE[1]), len(ok))
                         if ok[i] >= 0.9 * n[i] and all(
                             ok[j] >= 0.9 * n[j] for j in range(i, min(i + 3, len(ok))))),
                        None)
            normal.append(back if back is not None else HORIZON)
        print(f"{name:<30} {sum(mult)/len(mult):>8.2f}x ({min(mult):.2f}-{max(mult):.2f})"
              f" {sum(crash_n)/len(crash_n):>10.1f}"
              f" {sum(normal)/len(normal):>10.1f} s ({min(normal):.0f}-{max(normal):.0f})")
        summary[name] = {"mult": mult, "crashes": crash_n, "normal": normal,
                         "arrivals_seed0": per_second(rs[0]["arrivals"]),
                         "ok_seed0": per_second(rs[0]["ok"]),
                         "new_seed0": per_second(rs[0]["new"])}
    if out:
        with open(out, "w") as f:
            json.dump(summary, f)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
