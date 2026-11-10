"""Lost updates and retries of a stock reservation by isolation level (PostgreSQL 17, measured).

One stock row starts at qty = 1,000,000. Every transaction reads qty,
records an order and writes back the value it computed itself, as in
the opening example of the note:

  BEGIN;
  SELECT qty FROM stock WHERE id = 1            -> :qty
  INSERT INTO orders (item_id) VALUES (1);
  UPDATE stock SET qty = :qty - 1 WHERE id = 1;
  END;

lost updates = committed orders - (1,000,000 - final qty).
pgbench runs each client for 200 transactions; a transaction that fails
with a serialization error is rolled back and retried from BEGIN
(--max-tries=10000; a transaction that still fails is
counted in gave_up and not committed), and pgbench counts the retries.
Conditions: postgres:17 in Docker, isolation set with
default_transaction_isolation, --random-seed=1. How the clients
interleave is decided by the OS scheduler, so the counts change a
little between runs; SERIALIZABLE must stay at 0 lost updates.

Run: python3 lost_update.py > lost_update_output.txt   (needs docker)
"""

import re
import subprocess
import tempfile
from pathlib import Path

NAME = "note-transaction-isolation"
IMAGE = "postgres:17"
LEVELS = ["read committed", "serializable"]
CLIENTS = [1, 2, 4, 8, 16, 32]
TX_PER_CLIENT = 200
INITIAL = 1_000_000

SCRIPT = r"""BEGIN;
SELECT qty FROM stock WHERE id = 1 \gset
INSERT INTO orders (item_id) VALUES (1);
UPDATE stock SET qty = :qty - 1 WHERE id = 1;
END;
"""


def sh(*args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True).stdout


def psql(sql):
    return sh("docker", "exec", NAME, "psql", "-U", "postgres", "-qAtc", sql)


def main():
    sh("docker", "rm", "-f", NAME, check=False)
    sh("docker", "run", "-d", "--name", NAME, "-e", "POSTGRES_HOST_AUTH_METHOD=trust",
       IMAGE, "-c", "max_connections=200")
    try:
        # TCP answers only after the image has finished its init and restarted the server
        sh("sh", "-c", f"until docker exec {NAME} psql -h 127.0.0.1 -U postgres -qc 'SELECT 1' >/dev/null 2>&1; do sleep 0.5; done")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "reserve.sql"
            p.write_text(SCRIPT)
            sh("docker", "cp", str(p), f"{NAME}:/tmp/reserve.sql")
        print(psql("SELECT version()").split(" on ")[0])
        print("level           clients  orders  stock_decrease  lost_updates  retried_tx  retries  gave_up")
        for level in LEVELS:
            for c in CLIENTS:
                psql("DROP TABLE IF EXISTS stock, orders;"
                     "CREATE TABLE stock (id int PRIMARY KEY, qty int NOT NULL);"
                     "CREATE TABLE orders (id bigserial PRIMARY KEY, item_id int NOT NULL);"
                     f"INSERT INTO stock VALUES (1, {INITIAL});")
                out = sh("docker", "exec", "-e", f"PGOPTIONS=-c default_transaction_isolation={level.replace(' ', '\\ ')}",
                         NAME, "pgbench", "-U", "postgres", "-n", "-f", "/tmp/reserve.sql",
                         "-c", str(c), "-j", str(c), "-t", str(TX_PER_CLIENT),
                         "--max-tries=10000", "--failures-detailed", "--random-seed=1",
                         "postgres")
                failed = int(re.search(r"number of failed transactions: (\d+)", out).group(1))
                m = re.search(r"number of transactions retried: (\d+)", out)
                retried = int(m.group(1)) if m else 0
                m = re.search(r"total number of retries: (\d+)", out)
                retries = int(m.group(1)) if m else 0
                orders = int(psql("SELECT count(*) FROM orders"))
                decrease = INITIAL - int(psql("SELECT qty FROM stock WHERE id = 1"))
                assert orders == c * TX_PER_CLIENT - failed
                print(f"{level:14s}  {c:7d}  {orders:6d}  {decrease:14d}  {orders - decrease:12d}  "
                      f"{retried:10d}  {retries:7d}  {failed:7d}")
    finally:
        sh("docker", "rm", "-f", NAME, check=False)


if __name__ == "__main__":
    main()
