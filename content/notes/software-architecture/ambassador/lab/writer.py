# 100ms ごとに通し番号を RPUSH で 1 回書き、結果を 1 行ずつ JSON で書く。
# MODE=static   : 最初の master の IP に直接繋ぐ
# MODE=sentinel : redis-py の Sentinel クライアントで master を探す
# MODE=ambassador: 同じネットワークを共有する HAProxy（127.0.0.1:6380）に繋ぐ
# MODE=ambassador_new: 同じ HAProxy に、書くたびに新しい接続で繋ぐ
import json, os, time
import redis
from redis.sentinel import Sentinel

mode = os.environ["MODE"]
opts = dict(socket_timeout=0.5, socket_connect_timeout=0.5, retry=None)
if mode == "static":
    r = redis.Redis(host="172.28.0.11", port=6379, **opts)
elif mode == "sentinel":
    s = Sentinel([("172.28.0.21", 26379), ("172.28.0.22", 26379), ("172.28.0.23", 26379)],
                 socket_timeout=0.5)
    r = s.master_for("mymaster", **opts)
else:
    r = redis.Redis(host="127.0.0.1", port=6380, **opts)

out = open(f"/out/{mode}.jsonl", "w", buffering=1)
seq = 0
while True:
    t0 = time.time()
    seq += 1
    err = ""
    try:
        r.rpush(f"log:{mode}", seq)
        res = "ok"
    except redis.exceptions.ReadOnlyError as e:
        res, err = "readonly", str(e)
    except redis.exceptions.TimeoutError as e:
        res, err = "timeout", str(e)
    except redis.exceptions.ConnectionError as e:
        res, err = ("readonly" if "slave" in str(e) or "replica" in str(e) else "conn"), str(e)
    except redis.exceptions.RedisError as e:
        res, err = type(e).__name__, str(e)
    finally:
        if mode == "ambassador_new":
            r.connection_pool.disconnect()   # 次の書き込みは新しい接続になる
    out.write(json.dumps({"t": t0, "seq": seq, "res": res, "err": err[:80], "ms": round((time.time() - t0) * 1000)}) + "\n")
    time.sleep(max(0, 0.1 - (time.time() - t0)))
