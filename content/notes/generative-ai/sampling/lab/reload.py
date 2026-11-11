"""temperature 0 の出力が、モデルの読み込み直しや num_ctx の違いで変わるかを確かめる。

使い方: python3 reload.py > output_reload.txt
前提: repeat.py と同じ。各条件の前に `ollama stop qwen3:8b` でモデルを外す。
"""
import hashlib
import subprocess
import time

from repeat import ask

for name, extra in [("読み込み直し 1", {}), ("読み込み直し 2", {}), ("読み込み直し 3", {}),
                    ("num_ctx 8192", {"num_ctx": 8192}), ("num_ctx 2048", {"num_ctx": 2048})]:
    subprocess.run(["ollama", "stop", "qwen3:8b"], check=True, capture_output=True)
    time.sleep(3)
    outs = [ask({"temperature": 0, **extra}) for _ in range(5)]
    hs = [hashlib.sha1(o.encode()).hexdigest()[:8] for o in outs]
    print(f"{name}: {' '.join(hs)}  {outs[0][:40]}", flush=True)
