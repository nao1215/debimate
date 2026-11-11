"""同じ問いを Ollama に何度も投げ、出力が何種類になるかを数える。

使い方: python3 repeat.py > output_repeat.txt
前提: Ollama 0.22.1 が localhost:11434 で動き、qwen3:8b を pull 済み。
"""
import collections
import concurrent.futures
import hashlib
import json
import urllib.request

URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:8b"
PROMPT = "日本の首都について 3 文で説明してください。"
N = 30


def ask(options):
    body = {"model": MODEL, "prompt": PROMPT, "stream": False, "think": False,
            "options": {"num_predict": 120, **options}}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["response"]


def run(name, options, parallel=1):
    if parallel == 1:
        outs = [ask(options) for _ in range(N)]
    else:
        with concurrent.futures.ThreadPoolExecutor(parallel) as ex:
            outs = list(ex.map(lambda _: ask(options), range(N)))
    c = collections.Counter(outs)
    print(f"== {name}: {N} 回 → {len(c)} 種類")
    for i, (text, k) in enumerate(c.most_common()):
        h = hashlib.sha1(text.encode()).hexdigest()[:8]
        print(f"  {k:3d} 回 [{h}] {text[:60].replace(chr(10), ' ')}")
    print(flush=True)


if __name__ == "__main__":
  run("指定なし（モデルの既定 temperature 0.6, top_k 20, top_p 0.95）", {})
  run("temperature 0、1 つずつ", {"temperature": 0})
  run("temperature 0、8 並列", {"temperature": 0}, parallel=8)
  run("temperature 0.6、seed 42、1 つずつ", {"temperature": 0.6, "seed": 42})
