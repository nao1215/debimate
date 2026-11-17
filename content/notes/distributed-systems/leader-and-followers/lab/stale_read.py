"""Leader で UPDATE を COMMIT した直後に、Follower で同じ行を読む。

4 つのやり方ごとに N 回繰り返し、
  - Follower が古い値を返した回数
  - COMMIT から Follower で読み終えるまでの時間（中央値）
を数える。cluster.sh up で作った 2 台が要る。
"""
import json
import statistics
import time

import psycopg

LEADER = "host=localhost port=55432 user=postgres"
FOLLOWER = "host=localhost port=55433 user=postgres"
N = 2000

leader = psycopg.connect(LEADER, autocommit=True)
follower = psycopg.connect(FOLLOWER, autocommit=True)
leader.execute("insert into t values (1, 0) on conflict (id) do update set v = 0")


def set_sync_standby(names):
    # synchronous_standby_names が空なら非同期、'*' なら Follower の応答を待つ
    leader.execute(f"alter system set synchronous_standby_names = '{names}'")
    leader.execute("select pg_reload_conf()")
    time.sleep(1)


CASES = [
    # (名前, synchronous_standby_names, synchronous_commit, LSN を待つか)
    ("async", "", "on", False),
    ("sync(on)", "*", "on", False),
    ("sync(remote_apply)", "*", "remote_apply", False),
    ("async + LSN を待つ", "", "on", True),
]
result = {}
for name, standby, commit, wait_lsn in CASES:
    set_sync_standby(standby)
    leader.execute(f"set synchronous_commit = {commit}")
    commit_ms, read_ms, stale = [], [], 0
    for i in range(1, N + 1):
        t0 = time.perf_counter()
        leader.execute("update t set v = %s where id = 1", (i,))  # autocommit なので 1 文で COMMIT
        t1 = time.perf_counter()
        if wait_lsn:
            # 自分の書き込みが入った WAL の位置を覚え、Follower がそこまで適用するのを待つ
            lsn = leader.execute("select pg_current_wal_lsn()").fetchone()[0]
            while not follower.execute(
                    "select pg_last_wal_replay_lsn() >= %s::pg_lsn", (lsn,)).fetchone()[0]:
                pass
        v = follower.execute("select v from t where id = 1").fetchone()[0]
        t2 = time.perf_counter()
        commit_ms.append((t1 - t0) * 1000)
        read_ms.append((t2 - t0) * 1000)
        if v != i:
            stale += 1
            while follower.execute("select v from t where id = 1").fetchone()[0] != i:
                pass
    result[name] = {"stale": stale, "n": N,
                    "commit_median_ms": statistics.median(commit_ms),
                    "write_to_read_median_ms": statistics.median(read_ms)}
    print(f"{name:20} 古い値 {stale:4}/{N} ({stale / N:5.1%})  "
          f"COMMIT {statistics.median(commit_ms):.2f}ms  "
          f"書いてから読み終えるまで {statistics.median(read_ms):.2f}ms（中央値）")

set_sync_standby("")
json.dump(result, open("out_stale_read.json", "w"), ensure_ascii=False, indent=1)
