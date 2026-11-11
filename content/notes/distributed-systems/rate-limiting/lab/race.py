"""中央の Redis で数を共有する時、数え方で上限を超えるかを確かめる。

8 個のプロセス（8 台のサーバーの代わり）が、同じ利用者のキーに一斉に 50 件ずつ、
計 400 件の要求を送る。上限は 100 件。3 通りの数え方を 20 回ずつ試し、通した件数を数える。

  check_then_incr : GET で今の数を読み、100 未満なら INCR する（読んでから書く。不可分ではない）
  check_then_incr_1ms : 上と同じで、GET と INCR の間に 1 ms 待つ（別のホストまでの往復の代わり）
  incr            : INCR の戻り値で判定する（Redis の公式ドキュメントの Lua の形。INCR と EXPIRE を 1 つのスクリプトで）
  token_bucket    : トークンバケットの計算全体を Lua のスクリプトにして、Redis の中で 1 回で行う

前提: Redis を 127.0.0.1:16379 で起動しておく（run.sh を参照）。
  python3 race.py
"""
import json
import multiprocessing as mp
import os
import statistics
import time

from resp import Redis

WORKERS, PER_WORKER, LIMIT, TRIALS = 8, 50, 100, 20

INCR_LUA = """
local current = redis.call("INCR", KEYS[1])
if current == 1 then
  redis.call("EXPIRE", KEYS[1], 60)
end
return current
"""

TOKEN_BUCKET_LUA = """
local rate     = tonumber(ARGV[1])            -- 1 秒に溜まるトークン
local capacity = tonumber(ARGV[2])            -- バケットの容量
local now = redis.call("TIME")                -- Redis の時計を使い、サーバーごとの時計のずれを避ける
local t = tonumber(now[1]) + tonumber(now[2]) / 1000000
local s = redis.call("HMGET", KEYS[1], "tokens", "ts")
local tokens = tonumber(s[1]) or capacity
local ts     = tonumber(s[2]) or t
tokens = math.min(capacity, tokens + (t - ts) * rate)
local allowed = 0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
end
redis.call("HSET", KEYS[1], "tokens", tostring(tokens), "ts", tostring(t))
redis.call("EXPIRE", KEYS[1], math.ceil(capacity / rate) + 1)
return allowed
"""


def check_then_incr(r, key, gap=0.0):
    current = int(r.call("GET", key) or 0)
    if gap:
        time.sleep(gap)                  # 別のホストの Redis までの往復を真似た待ち
    if current < LIMIT:
        r.call("INCR", key)
        return True
    return False


def incr(r, key, sha):
    return r.call("EVALSHA", sha, 1, key) <= LIMIT


def token_bucket(r, key, sha):
    # 1 秒に 1 個、容量 100。400 件はほぼ同時に届くので、通るのは容量の 100 件前後になるはず
    return r.call("EVALSHA", sha, 1, key, 1, LIMIT) == 1


def worker(mode, key, shas, barrier, q):
    r = Redis()
    barrier.wait()                       # 8 プロセスの開始を揃える
    ok = 0
    for _ in range(PER_WORKER):
        if mode == "check_then_incr":
            ok += check_then_incr(r, key)
        elif mode == "check_then_incr_1ms":
            ok += check_then_incr(r, key, gap=0.001)
        elif mode == "incr":
            ok += incr(r, key, shas["incr"])
        else:
            ok += token_bucket(r, key, shas["token_bucket"])
    q.put(ok)


def trial(ctx, mode, n, shas):
    key = f"rl:{mode}:{n}:{time.time_ns()}"
    barrier, q = ctx.Barrier(WORKERS), ctx.Queue()
    ps = [ctx.Process(target=worker, args=(mode, key, shas, barrier, q)) for _ in range(WORKERS)]
    for p in ps:
        p.start()
    total = sum(q.get() for _ in ps)
    for p in ps:
        p.join()
    return total


def main():
    ctx = mp.get_context("fork")
    r = Redis()
    shas = {"incr": r.call("SCRIPT", "LOAD", INCR_LUA),
            "token_bucket": r.call("SCRIPT", "LOAD", TOKEN_BUCKET_LUA)}
    info = r.call("INFO", "server")
    version = next(l.split(":")[1] for l in info.splitlines() if l.startswith("redis_version"))

    # 1 回の往復の時間（参考）
    lat = []
    for _ in range(2000):
        t0 = time.perf_counter()
        r.call("PING")
        lat.append((time.perf_counter() - t0) * 1e6)

    results = {"redis_version": version, "workers": WORKERS, "per_worker": PER_WORKER,
               "limit": LIMIT, "ping_median_us": statistics.median(lat), "trials": {}}
    print(f"Redis {version}, {WORKERS} processes x {PER_WORKER} requests, limit {LIMIT}")
    print(f"PING の往復の中央値: {results['ping_median_us']:.0f} µs")
    for mode in ["check_then_incr", "check_then_incr_1ms", "incr", "token_bucket"]:
        got = [trial(ctx, mode, n, shas) for n in range(TRIALS)]
        results["trials"][mode] = got
        print(f"{mode:20} min {min(got):3} median {statistics.median(got):5.1f} max {max(got):3}  {got}")
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "race_results.json"), "w") as f:
        json.dump(results, f, indent=1)


if __name__ == "__main__":
    main()
