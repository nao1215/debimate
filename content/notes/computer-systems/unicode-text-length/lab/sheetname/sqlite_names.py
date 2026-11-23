# SQLite が、大文字と小文字だけが違う表の名前を別の表として扱うかを確かめる。
import sqlite3

con = sqlite3.connect(":memory:")
for name in ["xay", "xAy", "x\u00e4y", "x\u00c4y"]:
    try:
        con.execute(f'CREATE TABLE "{name}" (v TEXT)')
        print(f"CREATE TABLE {name}: ok")
    except sqlite3.OperationalError as e:
        print(f"CREATE TABLE {name}: {e}")
