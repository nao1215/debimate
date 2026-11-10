"""Count deadlocks of concurrent transfers on PostgreSQL 17 (measured, not simulated).

Each transfer is one transaction that updates two different accounts:
debit account a, wait 5 ms (stands for other work in the transaction),
then credit account b. a and b are drawn uniformly from 1..N (a != b).

  random  : lock a first, then b (the order the request arrived in)
  ordered : lock the smaller id first, then the larger one

Conditions: postgres:17 in Docker, deadlock_timeout = 100ms (default 1s,
shortened so a run finishes quickly), pgbench -t 200 per client,
--max-tries=1 (no retry), --random-seed=1. Interleaving of the clients
is decided by the OS scheduler, so counts of the random order change a
little between runs; the ordered runs must stay at 0.

Run: python3 deadlock_rate.py > deadlock_rate_output.txt   (needs docker)
"""

import re
import subprocess
import tempfile
from pathlib import Path

NAME = "note-deadlock"
IMAGE = "postgres:17"
ACCOUNTS = [10, 100]
CLIENTS = [1, 2, 4, 8, 16, 32]
TX_PER_CLIENT = 200

PICK = r"""\set a random(1, :naccounts)
\set b random(1, :naccounts - 1)
\set b case when :b >= :a then :b + 1 else :b end
"""
SCRIPTS = {
    "random": PICK + r"""BEGIN;
UPDATE accounts SET balance = balance - 1 WHERE id = :a;
SELECT pg_sleep(0.005);
UPDATE accounts SET balance = balance + 1 WHERE id = :b;
END;
""",
    "ordered": PICK + r"""\set lo least(:a, :b)
\set hi greatest(:a, :b)
\set dlo case when :lo = :a then -1 else 1 end
BEGIN;
UPDATE accounts SET balance = balance + :dlo WHERE id = :lo;
SELECT pg_sleep(0.005);
UPDATE accounts SET balance = balance - :dlo WHERE id = :hi;
END;
""",
}


def sh(*args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True).stdout


def psql(sql):
    return sh("docker", "exec", NAME, "psql", "-U", "postgres", "-qAtc", sql)


def main():
    sh("docker", "rm", "-f", NAME, check=False)
    sh("docker", "run", "-d", "--name", NAME, "-e", "POSTGRES_HOST_AUTH_METHOD=trust",
       IMAGE, "-c", "deadlock_timeout=100ms", "-c", "max_connections=200")
    try:
        # TCP answers only after the image has finished its init and restarted the server
        sh("sh", "-c", f"until docker exec {NAME} psql -h 127.0.0.1 -U postgres -qc 'SELECT 1' >/dev/null 2>&1; do sleep 0.5; done")
        with tempfile.TemporaryDirectory() as d:
            for k, body in SCRIPTS.items():
                p = Path(d) / f"{k}.sql"
                p.write_text(body)
                sh("docker", "cp", str(p), f"{NAME}:/tmp/{k}.sql")
        print(psql("SELECT version()").split(" on ")[0])
        print("accounts  order    clients  transfers  deadlocks  rate(%)")
        for n in ACCOUNTS:
            for order in SCRIPTS:
                for c in CLIENTS:
                    psql("DROP TABLE IF EXISTS accounts;"
                         "CREATE TABLE accounts (id int PRIMARY KEY, balance int NOT NULL);"
                         f"INSERT INTO accounts SELECT g, 10000 FROM generate_series(1, {n}) g;")
                    out = sh("docker", "exec", NAME, "pgbench", "-U", "postgres", "-n",
                             "-f", f"/tmp/{order}.sql", "-D", f"naccounts={n}",
                             "-c", str(c), "-j", str(c), "-t", str(TX_PER_CLIENT),
                             "--max-tries=1", "--failures-detailed", "--random-seed=1",
                             "postgres")
                    dead = int(re.search(r"number of deadlock failures: (\d+)", out).group(1))
                    total = c * TX_PER_CLIENT
                    # the money must not move: aborted transfers leave nothing behind
                    assert psql("SELECT sum(balance) FROM accounts").strip() == str(10000 * n)
                    print(f"{n:8d}  {order:7s}  {c:7d}  {total:9d}  {dead:9d}  {100 * dead / total:7.2f}")
    finally:
        sh("docker", "rm", "-f", NAME, check=False)


if __name__ == "__main__":
    main()
