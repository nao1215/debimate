"""Replay delayed writes; this is not a lease grantor implementation."""
import sqlite3


def replay(fenced):
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE resource (id INTEGER PRIMARY KEY, value TEXT, token INTEGER)")
        db.execute("INSERT INTO resource VALUES (1, 'initial', 0)")
        for token, value in [(33, "A:first"), (34, "B:new"), (33, "A:delayed")]:
            sql = "UPDATE resource SET value = ?, token = ? WHERE id = 1"
            if fenced:
                sql += " AND token <= ?"
            args = (value, token, token) if fenced else (value, token)
            accepted = db.execute(sql, args).rowcount == 1
            print(f"token={token} value={value} {'ACCEPT' if accepted else 'REJECT'}")
        value, token = db.execute("SELECT value, token FROM resource").fetchone()
        print(f"final={value} token={token}")
        assert value == ("B:new" if fenced else "A:delayed")


for fenced in (False, True):
    print(f"[fencing={'on' if fenced else 'off'}]")
    replay(fenced)
