"""COMMIT が返った書き込みが、Follower の昇格で消えるかを見る。

1. 100 行を書き、Follower に届くのを待つ
2. Follower をネットワークから外し（Leader から WAL が届かない状態）、Leader に 10 行を書く
3. Leader を docker kill で落とし、Follower を戻して昇格させる
4. 昇格した Follower の行数を数える
5. 落とした Leader をもう一度起動し、2 台の両方に書いてみる

引数 async / sync / sync-cancel で、2 の書き込みの待ち方を変える。
"""
import subprocess
import sys
import threading
import time

import psycopg

MODE = sys.argv[1]
LEADER = "host=localhost port=55432 user=postgres connect_timeout=3"
FOLLOWER = "host=localhost port=55433 user=postgres connect_timeout=3"


def sh(*args):
    subprocess.run(args, check=True, capture_output=True)


def connect(dsn):
    for _ in range(60):
        try:
            return psycopg.connect(dsn, autocommit=True)
        except psycopg.OperationalError:
            time.sleep(0.5)
    raise RuntimeError(dsn)


def log(msg):
    print(f"{time.perf_counter() - T0:6.1f}s  {msg}", flush=True)


subprocess.run(["./cluster.sh", "up"], check=True, capture_output=True)
T0 = time.perf_counter()
leader, follower = connect(LEADER), connect(FOLLOWER)
if MODE != "async":
    leader.execute("alter system set synchronous_standby_names = '*'")
    leader.execute("select pg_reload_conf()")
leader.execute("insert into t select g, 0 from generate_series(1, 100) g")
while follower.execute("select count(*) from t").fetchone()[0] < 100:
    time.sleep(0.1)
log("100 行を書き、Follower にも 100 行ある")

sh("docker", "network", "disconnect", "lf-net", "lf-follower")
log("Follower をネットワークから外した")

if MODE == "async":
    for i in range(101, 111):
        leader.execute("insert into t values (%s, 0)", (i,))
        log(f"Leader: insert id={i} -> COMMIT が返った")
else:
    # 同期: COMMIT は Follower の応答を待って止まる
    def cancel_later():
        time.sleep(5)
        other = connect(LEADER)
        if MODE == "sync-cancel":
            log("別の接続から pg_cancel_backend で待ちを取り消す")
            other.execute("select pg_cancel_backend(pid) from pg_stat_activity "
                          "where wait_event = 'SyncRep'")
        else:
            n = other.execute("select count(*) from t").fetchone()[0]
            log(f"5 秒待っても COMMIT が返らない（別の接続から見た行数 {n}）")
            sh("docker", "kill", "lf-leader")
    threading.Thread(target=cancel_later, daemon=True).start()
    leader.add_notice_handler(lambda d: log(f"Leader: {d.severity}: {d.message_primary} / {d.message_detail}"))
    log("Leader: insert id=101 ...")
    try:
        leader.execute("insert into t values (101, 0)")
        log("Leader: insert id=101 -> COMMIT が返った")
    except psycopg.Error as e:
        log(f"Leader: insert id=101 -> {type(e).__name__}")
    if MODE == "sync-cancel":
        n = connect(LEADER).execute("select count(*) from t").fetchone()[0]
        log(f"Leader を別の接続で数えると {n} 行")

subprocess.run(["docker", "kill", "lf-leader"], capture_output=True)
log("Leader を docker kill で落とした")
sh("docker", "network", "connect", "lf-net", "lf-follower")
follower = connect(FOLLOWER)
follower.execute("select pg_promote()")
log(f"Follower を昇格させた: 行数 {follower.execute('select count(*) from t').fetchone()[0]}")

# 落とした Leader を、そのまま起動し直す
sh("docker", "start", "lf-leader")
old = connect(LEADER)
log(f"起動し直した古い Leader: recovery={old.execute('select pg_is_in_recovery()').fetchone()[0]} "
    f"行数 {old.execute('select count(*) from t').fetchone()[0]}")
if MODE == "async":
    old.execute("insert into t values (500, 1)")
    follower.execute("insert into t values (500, 2)")
    for name, c in [("古い Leader", old), ("昇格した Follower", follower)]:
        n, v = c.execute("select count(*), (select v from t where id = 500) from t").fetchone()
        log(f"{name}: insert id=500 -> COMMIT が返った（行数 {n}、id=500 の v={v}）")
