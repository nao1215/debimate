"""同じ SQL を PostgreSQL・MySQL・SQLite・DuckDB で実行し、結果を output/results.json に書く。

前提: docker で次の 2 つを起動しておく。DuckDB は CLI（duckdb）、SQLite は Python 標準の sqlite3 を使う。
  docker run -d --rm --name sqlnull-pg -e POSTGRES_PASSWORD=pw postgres:18
  docker run -d --rm --name sqlnull-my -e MYSQL_ROOT_PASSWORD=pw -e MYSQL_DATABASE=lab mysql:8.4
実行: python3 run.py
"""
import json
import pathlib
import sqlite3
import subprocess

HERE = pathlib.Path(__file__).resolve().parent

SCHEMA = """
DROP TABLE IF EXISTS members;
CREATE TABLE members (
    id          INT PRIMARY KEY,
    name        VARCHAR(20) NOT NULL,
    email       VARCHAR(50),
    referred_by INT,
    score       INT
);
INSERT INTO members VALUES
    (1, 'sato',     'sato@example.com',   NULL, 80),
    (2, 'suzuki',   'suzuki@example.com', 1,    NULL),
    (3, 'takahashi', NULL,                1,    60),
    (4, 'tanaka',    NULL,                NULL, 90),
    (5, 'ito',      'ito@example.com',    2,    NULL);
"""

# (id, SQL)。engine ごとに書き方が違う所だけ dict で分ける。
QUERIES = [
    ("ne", "SELECT count(*) FROM members WHERE email <> 'sato@example.com'"),
    ("not_in", "SELECT count(*) FROM members WHERE id NOT IN (SELECT referred_by FROM members)"),
    ("in", "SELECT count(*) FROM members WHERE id IN (SELECT referred_by FROM members)"),
    ("not_exists", "SELECT count(*) FROM members m WHERE NOT EXISTS "
                   "(SELECT 1 FROM members r WHERE r.referred_by = m.id)"),
    ("not_in_filtered", "SELECT count(*) FROM members WHERE id NOT IN "
                        "(SELECT referred_by FROM members WHERE referred_by IS NOT NULL)"),
    ("left_join", "SELECT count(*) FROM members m LEFT JOIN "
                  "(SELECT DISTINCT referred_by FROM members) r ON r.referred_by = m.id "
                  "WHERE r.referred_by IS NULL"),
    ("outer_join_all", "SELECT count(*) FROM members m LEFT JOIN members r ON r.id = m.referred_by"),
    ("outer_join_where_ne", "SELECT count(*) FROM members m LEFT JOIN members r ON r.id = m.referred_by "
                            "WHERE r.name <> 'sato'"),
    ("outer_join_on_ne", "SELECT count(*) FROM members m LEFT JOIN members r "
                         "ON r.id = m.referred_by AND r.name <> 'sato'"),
    ("outer_join_where_distinct", {
        "postgres": "SELECT count(*) FROM members m LEFT JOIN members r ON r.id = m.referred_by "
                    "WHERE r.name IS DISTINCT FROM 'sato'",
        "sqlite": "SELECT count(*) FROM members m LEFT JOIN members r ON r.id = m.referred_by "
                  "WHERE r.name IS DISTINCT FROM 'sato'",
        "duckdb": "SELECT count(*) FROM members m LEFT JOIN members r ON r.id = m.referred_by "
                  "WHERE r.name IS DISTINCT FROM 'sato'",
        "mysql": "SELECT count(*) FROM members m LEFT JOIN members r ON r.id = m.referred_by "
                 "WHERE NOT (r.name <=> 'sato')",
    }),
    ("count_star", "SELECT count(*) FROM members"),
    ("count_col", "SELECT count(score) FROM members"),
    ("avg", "SELECT round(avg(score), 2) FROM members"),
    ("sum_div_count", "SELECT round(sum(score) * 1.0 / count(*), 2) FROM members"),
    ("sum_empty", "SELECT coalesce(cast(sum(score) AS CHAR), 'NULL') FROM members WHERE id > 100"),
    ("count_distinct", "SELECT count(DISTINCT referred_by) FROM members"),
    ("select_distinct", "SELECT count(*) FROM (SELECT DISTINCT referred_by FROM members) d"),
    ("group_by_null", "SELECT count(*) FROM members GROUP BY referred_by HAVING referred_by IS NULL"),
    ("union_nulls", "SELECT count(*) FROM (SELECT referred_by FROM members WHERE referred_by IS NULL "
                    "UNION SELECT referred_by FROM members WHERE referred_by IS NULL) u"),
    ("top_score", "SELECT name FROM members ORDER BY score DESC LIMIT 1"),
    ("top_score_nulls_last", "SELECT name FROM members ORDER BY score DESC NULLS LAST LIMIT 1"),
    ("top_score_is_null", "SELECT name FROM members ORDER BY score IS NULL, score DESC LIMIT 1"),
    ("order_first", "SELECT coalesce(email, 'NULL') FROM members ORDER BY email LIMIT 1"),
    ("order_desc_first", "SELECT coalesce(email, 'NULL') FROM members ORDER BY email DESC LIMIT 1"),
    ("order_nulls_last", "SELECT coalesce(email, 'NULL') FROM members ORDER BY email DESC NULLS LAST LIMIT 1"),
    ("order_is_null", "SELECT coalesce(email, 'NULL') FROM members ORDER BY email IS NULL DESC, email DESC LIMIT 1"),
    ("eq_null", "SELECT coalesce(cast((NULL = NULL) AS CHAR), 'NULL')"),
    ("concat_op", {
        "postgres": "SELECT coalesce('a' || NULL, 'NULL')",
        "sqlite": "SELECT coalesce('a' || NULL, 'NULL')",
        "duckdb": "SELECT coalesce('a' || NULL, 'NULL')",
        "mysql": "SELECT coalesce('a' || NULL, 'NULL')",
    }),
    ("concat_ab", "SELECT 'a' || 'b'"),
    ("concat_ab_pipes_mode", {
        "postgres": "SELECT 'a' || 'b'",
        "sqlite": "SELECT 'a' || 'b'",
        "duckdb": "SELECT 'a' || 'b'",
        "mysql": "SET SESSION sql_mode = CONCAT(@@sql_mode, ',PIPES_AS_CONCAT'); SELECT 'a' || 'b'",
    }),
    ("concat_fn", "SELECT coalesce(concat('a', NULL), 'NULL')"),
    ("unique_two_nulls", """
        DROP TABLE IF EXISTS u;
        CREATE TABLE u (email VARCHAR(50) UNIQUE);
        INSERT INTO u VALUES (NULL);
        INSERT INTO u VALUES (NULL);
        SELECT count(*) FROM u"""),
    ("unique_nulls_not_distinct", """
        DROP TABLE IF EXISTS u2;
        CREATE TABLE u2 (email VARCHAR(50) UNIQUE NULLS NOT DISTINCT);
        INSERT INTO u2 VALUES (NULL);
        INSERT INTO u2 VALUES (NULL);
        SELECT count(*) FROM u2"""),
    ("is_not_distinct", "SELECT CASE WHEN NULL IS NOT DISTINCT FROM NULL THEN 'TRUE' ELSE 'not TRUE' END"),
    ("null_safe_eq", "SELECT CASE WHEN NULL <=> NULL THEN 'TRUE' ELSE 'not TRUE' END"),
    ("pk_two_nulls", """
        DROP TABLE IF EXISTS pk;
        CREATE TABLE pk (code VARCHAR(10) PRIMARY KEY);
        INSERT INTO pk VALUES (NULL);
        INSERT INTO pk VALUES (NULL);
        SELECT count(*) FROM pk"""),
    ("outer_null_not_in", "SELECT count(*) FROM (SELECT max(id) AS x FROM members WHERE id > 100) t WHERE x NOT IN (SELECT id FROM members)"),
    ("outer_null_not_exists", "SELECT count(*) FROM (SELECT max(id) AS x FROM members WHERE id > 100) t "
                              "WHERE NOT EXISTS (SELECT 1 FROM members m WHERE m.id = t.x)"),
    ("check_null", """
        DROP TABLE IF EXISTS c;
        CREATE TABLE c (score INT CHECK (score >= 0));
        INSERT INTO c VALUES (NULL);
        SELECT count(*) FROM c"""),
    ("check_negative", """
        DROP TABLE IF EXISTS c2;
        CREATE TABLE c2 (score INT CHECK (score >= 0));
        INSERT INTO c2 VALUES (-1);
        SELECT count(*) FROM c2"""),
]

# DuckDB と PostgreSQL の CHAR は長さ 1 の型ではないが、MySQL の cast は CHAR しか取らないので揃えた。
FIX = {
    "postgres": lambda s: s.replace("AS CHAR)", "AS TEXT)"),
    "duckdb": lambda s: s.replace("AS CHAR)", "AS VARCHAR)"),
    "sqlite": lambda s: s.replace("AS CHAR)", "AS TEXT)"),
    "mysql": lambda s: s,
}


def run_postgres(sql):
    p = subprocess.run(["docker", "exec", "-i", "sqlnull-pg", "psql", "-U", "postgres", "-At",
                        "-v", "ON_ERROR_STOP=1", "-q"], input=sql + ";", capture_output=True, text=True)
    err = "\n".join(l for l in p.stderr.splitlines() if not l.startswith("NOTICE"))
    return p.stdout.strip().splitlines()[-1:] if p.returncode == 0 else ["ERROR: " + err.strip()]


def run_mysql(sql):
    p = subprocess.run(["docker", "exec", "-i", "sqlnull-my", "mysql", "-uroot", "-ppw", "-N", "-B", "lab"],
                       input=sql + ";", capture_output=True, text=True)
    err = "\n".join(l for l in p.stderr.splitlines() if "password on the command line" not in l)
    return p.stdout.strip().splitlines()[-1:] if p.returncode == 0 else ["ERROR: " + err.strip()]


SQLITE = sqlite3.connect(":memory:")


def run_sqlite(sql):
    try:
        cur = None
        for stmt in [s for s in sql.split(";") if s.strip()]:
            cur = SQLITE.execute(stmt)
        SQLITE.commit()
        row = cur.fetchone()
        return [str(row[0])] if row else []
    except sqlite3.Error as e:
        SQLITE.rollback()
        return ["ERROR: " + str(e)]


DUCK = HERE / "output" / "lab.duckdb"


def run_duckdb(sql):
    p = subprocess.run(["duckdb", str(DUCK), "-list", "-noheader"], input=sql + ";",
                       capture_output=True, text=True)
    if p.returncode != 0 or "Error" in p.stderr:
        return ["ERROR: " + p.stderr.strip()]
    return p.stdout.strip().splitlines()[-1:]


RUNNERS = {"postgres": run_postgres, "mysql": run_mysql, "sqlite": run_sqlite, "duckdb": run_duckdb}


def versions():
    return {
        "postgres": run_postgres("SHOW server_version")[0],
        "mysql": run_mysql("SELECT version()")[0],
        "sqlite": sqlite3.sqlite_version,
        "duckdb": subprocess.run(["duckdb", "--version"], capture_output=True, text=True).stdout.strip(),
    }


def main():
    (HERE / "output").mkdir(exist_ok=True)
    DUCK.unlink(missing_ok=True)
    results = {"versions": versions(), "queries": {}}
    for engine, run in RUNNERS.items():
        run(SCHEMA.strip().rstrip(";"))
    for qid, sql in QUERIES:
        results["queries"][qid] = {}
        for engine, run in RUNNERS.items():
            s = sql[engine] if isinstance(sql, dict) else sql
            s = FIX[engine](s.strip())
            out = run(s)
            results["queries"][qid][engine] = out[0] if out else ""
    DUCK.unlink(missing_ok=True)
    (HERE / "output" / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    w = max(len(q) for q, _ in QUERIES)
    print("versions:", results["versions"])
    print(f"{'query':<{w}}  " + "  ".join(f"{e:<10}" for e in RUNNERS))
    for qid, r in results["queries"].items():
        print(f"{qid:<{w}}  " + "  ".join(f"{(r[e][:60]):<10}" for e in RUNNERS))


if __name__ == "__main__":
    main()
