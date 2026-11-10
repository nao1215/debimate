"""100MB ずつメモリを確保し、確保した量を表示し続ける。

cgroup の上限を付けて実行し、OOM killer に終了されるまでを観察する。
    systemd-run --user --scope -p MemoryMax=200M -p MemorySwapMax=0 python3 lab/eat_memory.py
"""
import sys

chunks = []
for i in range(1, 51):  # 上限が効かなかった時のために 5GB で止める
    chunks.append(bytearray(100 * 1024 * 1024))  # 0 で埋めた 100MB を確保する
    print(f"{i * 100} MB allocated", flush=True)
print("finished without OOM", flush=True)
sys.exit(0)
