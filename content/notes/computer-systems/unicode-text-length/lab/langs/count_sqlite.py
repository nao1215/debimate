import sqlite3
s = "\U0001F468\u200d\U0001F469\u200d\U0001F467"  # 👨‍👩‍👧
con = sqlite3.connect(":memory:")
print("sqlite", sqlite3.sqlite_version)
print("sqlite length(text)         =", con.execute("SELECT length(?)", (s,)).fetchone()[0])
print("sqlite octet_length(text)   =", con.execute("SELECT octet_length(?)", (s,)).fetchone()[0])
