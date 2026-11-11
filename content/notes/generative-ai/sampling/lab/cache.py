"""temperature 0 で 1 回目だけ出力が違う理由が、問いの計算の使い回し（prompt のキャッシュ）かを確かめる。

各回の応答のハッシュと、問いのトークン数（prompt_eval_count）、問いの処理に掛かった時間（prompt_eval_duration）を並べる。
使い方: python3 cache.py > output_cache.txt
前提: repeat.py と同じ。
"""
import hashlib
import json
import subprocess
import time
import urllib.request

URL = "http://localhost:11434/api/generate"
A = "日本の首都について 3 文で説明してください。"
B = "フランスの首都について 3 文で説明してください。"


def ask(prompt):
    body = {"model": "qwen3:8b", "prompt": prompt, "stream": False, "think": False,
            "options": {"temperature": 0, "num_predict": 120}}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    return hashlib.sha1(d["response"].encode()).hexdigest()[:8], d["prompt_eval_count"], d["prompt_eval_duration"] / 1e6


subprocess.run(["ollama", "stop", "qwen3:8b"], check=True, capture_output=True)
time.sleep(3)
for label, p in [("A 1 回目（読み込み直後）", A), ("A 2 回目", A), ("A 3 回目", A),
                 ("B（別の問い）", B), ("A 4 回目（B の後）", A), ("A 5 回目", A)]:
    h, n, ms = ask(p)
    print(f"{label:<22} 出力 {h}  問いのトークン数 {n}  問いの処理 {ms:6.1f} ms", flush=True)
