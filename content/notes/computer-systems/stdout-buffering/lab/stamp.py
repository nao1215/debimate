"""標準入力から届いた行に、起動からの経過秒を付けて出す。"""
import os
import sys
import time

t0 = float(os.environ["T0"])
for raw in iter(sys.stdin.buffer.readline, b""):
    print(f"{time.time() - t0:.2f} {raw.decode().rstrip()}", flush=True)
