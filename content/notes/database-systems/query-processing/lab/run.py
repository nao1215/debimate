#!/usr/bin/env python3
"""Query Processing のノートの実験。PostgreSQL 18 と MySQL 8.4 で次を測る。

1. ORDER BY id LIMIT n の n を変えた時の実行計画と実行時間（PostgreSQL）
2. 同じ SQL で、行が散らばった利用者と、末尾に固まった利用者の実行時間
3. (user_id, id) の複合索引を足した時の実行時間
4. 関係のある 3 列の条件で、見積もった行の数と実際の行の数（拡張統計の有無）
5. 結合する表の数と、計画を作る時間（FROM に並べる書き方と JOIN で書く書き方）
6. MySQL で同じ形の SQL を実行した時の実行計画と実行時間

docker-compose.yml と同じディレクトリで

    python3 run.py

を実行すると、コンテナを作り直して表を作り、result.json と output.txt を書く。
終わるとコンテナを消す（--keep で残す）。表の作成に数分かかる。
"""
import json
import pathlib
import re
import statistics
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
LOG = []
RESULT = {}
REPEAT = 5


def log(msg=""):
    print(msg, flush=True)
    LOG.append(msg)


def run(*args, stdin=None):
    p = subprocess.run(args, input=stdin, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"{args}: {p.stderr.strip()}")
    return p.stdout


def pg(sql):
    return run("docker", "exec", "-i", "qplab-postgres", "psql", "-U", "postgres",
               "-At", "-v", "ON_ERROR_STOP=1", "-c", sql)


def my(sql, db="lab"):
    return run("docker", "exec", "-i", "qplab-mysql", "mysql", "-uroot", "-plab",
               db, "-N", "-e", sql)


def pg_explain(sql):
    """EXPLAIN ANALYZE を REPEAT 回流し、最後の計画と実行時間の中央値を返す。"""
    plans, times, plan_times = [], [], []
    pg(f"EXPLAIN ANALYZE {sql}")  # 1 回目はキャッシュを温めるだけ
    for _ in range(REPEAT):
        out = pg(f"EXPLAIN (ANALYZE, BUFFERS OFF) {sql}")
        plans.append(out)
        times.append(float(re.search(r"Execution Time: ([\d.]+)", out).group(1)))
        plan_times.append(float(re.search(r"Planning Time: ([\d.]+)", out).group(1)))
    return plans[-1], statistics.median(times), statistics.median(plan_times)


def top_node(plan):
    """Limit・Sort などを除いた、読み方を表す最初の節点の名前。"""
    for line in plan.splitlines():
        m = re.search(r"(Index Scan using \S+|Parallel Index Scan using \S+|"
                      r"Bitmap Heap Scan|Seq Scan|Parallel Seq Scan)", line)
        if m:
            return m.group(1)
    return "?"


def wait_ready():
    for _ in range(60):
        try:
            pg("SELECT 1")
            my("SELECT 1", db="mysql")
            return
        except RuntimeError:
            time.sleep(3)
    raise RuntimeError("DB が起動しない")


def limit_sweep():
    log("## 1. ORDER BY id LIMIT n（利用者 1、行は id の末尾に固まる）")
    rows = []
    for n in [1, 10, 100, 1000, 3000, 10000, None]:
        lim = f" LIMIT {n}" if n else ""
        sql = f"SELECT * FROM events WHERE user_id = 1 ORDER BY id{lim}"
        plan, t, _ = pg_explain(sql)
        node = top_node(plan)
        rows.append({"limit": n, "node": node, "ms": t})
        log(f"LIMIT {n or 'なし':>6}: {t:9.3f} ms  {node}")
    RESULT["limit_sweep"] = rows
    _, t, _ = pg_explain("SELECT * FROM events WHERE user_id = 1 ORDER BY id LIMIT 1")
    plan, _, _ = pg_explain("SELECT * FROM events WHERE user_id = 1 ORDER BY id LIMIT 1")
    log("-- LIMIT 1 の実行計画")
    log(plan.rstrip())
    other = pg("SET enable_indexscan = off; EXPLAIN SELECT * FROM events "
               "WHERE user_id = 1 ORDER BY id LIMIT 1")
    log("-- 比べて捨てられた方の計画（主キーの索引を使えなくした時に選ばれる）")
    log(other.rstrip())
    RESULT["other_plan_cost"] = float(re.search(r"cost=([\d.]+)\.\.", other).group(1))


def spread_vs_tail():
    log("\n## 2. 同じ SQL で利用者だけを変える")
    out = {}
    for uid in [500, 1]:
        sql = f"SELECT * FROM events WHERE user_id = {uid} ORDER BY id LIMIT 1"
        plan, t, _ = pg_explain(sql)
        removed = re.search(r"Rows Removed by Filter: (\d+)", plan)
        est = re.search(r"Index Scan using events_pkey on events .*?rows=(\d+)", plan)
        out[str(uid)] = {"ms": t, "removed": int(removed.group(1)) if removed else 0,
                         "estimated_rows": int(est.group(1)) if est else None,
                         "node": top_node(plan)}
        log(f"user_id = {uid:>3}: {t:9.3f} ms  捨てた行 {out[str(uid)]['removed']:>9,}"
            f"  見積もった行 {out[str(uid)]['estimated_rows']}")
        if uid == 500:
            log(plan.rstrip())
    RESULT["spread_vs_tail"] = out
    first = pg("SELECT min(id) FROM events WHERE user_id = 1").strip()
    log(f"利用者 1 の最初の id: {first}")
    RESULT["user1_first_id"] = int(first)


def composite_index():
    log("\n## 3. (user_id, id) の複合索引を足す")
    pg("CREATE INDEX events_user_id_id_idx ON events (user_id, id)")
    plan, t, _ = pg_explain("SELECT * FROM events WHERE user_id = 1 ORDER BY id LIMIT 1")
    log(f"LIMIT 1: {t:.3f} ms  {top_node(plan)}")
    RESULT["composite_ms"] = t
    pg("DROP INDEX events_user_id_id_idx")


def correlated():
    log("\n## 4. 関係のある 3 列の条件で見積もる行の数")
    where = "c.city = 7 AND c.pref = 0 AND c.region = 0"
    single = f"SELECT * FROM customers c WHERE {where}"
    join = (f"SELECT count(*) FROM customers c JOIN orders o ON o.customer_id = c.id "
            f"WHERE {where}")
    res = {}
    for label in ["before", "after"]:
        if label == "after":
            pg("CREATE STATISTICS customers_dep (dependencies) ON city, pref, region "
               "FROM customers")
            pg("ANALYZE customers")
        p1, _, _ = pg_explain(single)
        est1 = int(re.search(r"rows=(\d+) width", p1).group(1))
        act1 = int(float(re.search(r"actual time=[\d.]+\.\.[\d.]+ rows=([\d.]+)",
                                   p1).group(1)))
        p2, t2, _ = pg_explain(join)
        m = re.search(r"Nested Loop .*?rows=(\d+) width.*?rows=([\d.]+) loops=(\d+)", p2)
        if m:
            est2 = int(m.group(1))
            act2 = round(float(m.group(2)) * int(m.group(3)))
        else:
            est2 = act2 = None
        res[label] = {"filter_estimated": est1, "filter_actual": act1,
                      "join_estimated": est2, "join_actual": act2, "join_ms": t2,
                      "join_node": "Nested Loop" if m else "?"}
        log(f"[{label}] 絞り込み: 見積もり {est1} 行 / 実際 {act1} 行  "
            f"結合: 見積もり {est2} 行 / 実際 {act2} 行  {t2:.1f} ms")
    pg("DROP STATISTICS customers_dep")
    pg("ANALYZE customers")
    RESULT["correlated"] = res
    stats = pg("SELECT attname, n_distinct FROM pg_stats WHERE tablename = 'customers' "
               "AND attname IN ('city', 'pref', 'region') ORDER BY attname")
    log("pg_stats の n_distinct:\n" + stats.rstrip())


def planning():
    log("\n## 5. 結合する表の数と、計画を作る時間")
    rows = []
    for n in range(2, 15):
        tables = [f"t{k}" for k in range(1, n + 1)]
        conds = " AND ".join(f"t1.id = t{k}.id" for k in range(2, n + 1))
        comma = f"SELECT count(*) FROM {', '.join(tables)} WHERE {conds}"
        joined = "t1" + "".join(f" JOIN t{k} ON t1.id = t{k}.id" for k in range(2, n + 1))
        explicit = f"SELECT count(*) FROM {joined}"
        _, ex_ms, comma_ms = pg_explain(comma)
        _, _, join_ms = pg_explain(explicit)
        rows.append({"tables": n, "comma_plan_ms": comma_ms, "comma_exec_ms": ex_ms,
                     "join_plan_ms": join_ms})
        log(f"{n:>2} 表: FROM に並べる 計画 {comma_ms:8.1f} ms 実行 {ex_ms:6.1f} ms"
            f" / JOIN で書く 計画 {join_ms:6.1f} ms")
    RESULT["planning"] = rows
    settings = {k: pg(f"SHOW {k}").strip()
                for k in ["geqo_threshold", "join_collapse_limit", "from_collapse_limit"]}
    RESULT["settings"] = settings
    log(f"設定: {settings}")


def mysql():
    log("\n## 6. MySQL 8.4 で同じ形の SQL")
    my("SELECT 1")
    out = {}
    cases = {
        "order_by_id": "SELECT * FROM events WHERE user_id = 1 ORDER BY id LIMIT 1",
        "order_by_seq": "SELECT * FROM events WHERE user_id = 1 ORDER BY seq LIMIT 1",
        "order_by_seq_off": "SELECT * FROM events WHERE user_id = 1 ORDER BY seq LIMIT 1",
    }
    for key, sql in cases.items():
        prefix = ("SET optimizer_switch='prefer_ordering_index=off'; "
                  if key.endswith("_off") else "")
        times, plan = [], ""
        for i in range(3):
            plan = my(f"{prefix}EXPLAIN ANALYZE {sql}")
            times.append(float(re.search(r"actual time=[\d.e+]+\.\.([\d.e+]+)",
                                         plan).group(1)))
        idx = re.findall(r"(Index (?:lookup|scan) on events using \w+)", plan)
        out[key] = {"ms": statistics.median(times), "access": idx[-1] if idx else "?"}
        log(f"{key}: {out[key]['ms']:.1f} ms  {out[key]['access']}")
        log(plan.replace("\\n", "\n").rstrip())
    RESULT["mysql"] = out
    RESULT["mysql_version"] = my("SELECT version()").strip()


def main():
    keep = "--keep" in sys.argv
    run("docker", "compose", "-f", str(HERE / "docker-compose.yml"), "down", "-v")
    run("docker", "compose", "-f", str(HERE / "docker-compose.yml"), "up", "-d")
    try:
        wait_ready()
        RESULT["postgres_version"] = pg("SHOW server_version").strip()
        log(f"PostgreSQL {RESULT['postgres_version']}")
        run("docker", "exec", "-i", "qplab-postgres", "psql", "-U", "postgres", "-q",
            "-v", "ON_ERROR_STOP=1", stdin=(HERE / "pg_setup.sql").read_text())
        run("docker", "exec", "-i", "qplab-mysql", "mysql", "-uroot", "-plab",
            stdin=(HERE / "mysql_setup.sql").read_text())
        limit_sweep()
        spread_vs_tail()
        composite_index()
        correlated()
        planning()
        mysql()
    finally:
        (HERE / "result.json").write_text(json.dumps(RESULT, ensure_ascii=False, indent=2)
                                          + "\n")
        (HERE / "output.txt").write_text("\n".join(LOG) + "\n")
        if not keep:
            run("docker", "compose", "-f", str(HERE / "docker-compose.yml"), "down", "-v")


if __name__ == "__main__":
    main()
