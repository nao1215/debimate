"""qwen3:8b に「今日の天気は」の続きを 1 トークンだけ出させ、上位 10 個の候補の確率を取る。

temperature を変えて、返る確率が変わるか（temperature を掛けた後の値か）も確かめる。
使い方: python3 nexttoken.py > output_nexttoken.txt
前提: Ollama 0.22.1 が localhost:11434 で動き、qwen3:8b を pull 済み。
"""
import json
import math
import urllib.request

URL = "http://localhost:11434/api/generate"


def top(temperature):
    body = {"model": "qwen3:8b", "prompt": "今日の天気は", "raw": True, "stream": False,
            "options": {"temperature": temperature, "num_predict": 1},
            "logprobs": True, "top_logprobs": 10}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["logprobs"][0]["top_logprobs"]


for t in [0.5, 1.0, 1.5]:
    print(f"== temperature {t}")
    for c in top(t):
        tok = bytes(c["bytes"]).decode("utf-8", errors="replace")
        print(f"  {tok!r:12} {math.exp(c['logprob']):.4f}")
