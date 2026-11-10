"""think（思考モード）と format の組み合わせで、思考の文がどこに返るかを見る。

同じ入力 1 件を、think: false / true と format 無し / スキーマの組で解かせ、
content の先頭、thinking の長さ、生成したトークン数と時間を出す。
tokens と eval は Ollama の応答の eval_count と eval_duration、wall は要求を送ってから応答が返るまでの時間。

使い方:
    OLLAMA_HOST=127.0.0.1:11435 python3 think.py <モデル> <入力の番号> [think の値,...]
"""
import json
import os
import sys
import time
import urllib.request

from run import PROMPT, SCHEMA
from texts import make_items


def main():
    model, idx = sys.argv[1], int(sys.argv[2])
    thinks = [v == "true" for v in sys.argv[3].split(",")] if len(sys.argv) > 3 else [False, True]
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    text = make_items()[idx]["text"]
    for think in thinks:
        for name, fmt in (("none", None), ("schema", SCHEMA)):
            body = {"model": model, "stream": False, "think": think,
                    "messages": [{"role": "user", "content": PROMPT.format(text=text)}],
                    "options": {"temperature": 0, "seed": 42, "num_predict": 4096}}
            if fmt is not None:
                body["format"] = fmt
            req = urllib.request.Request(f"http://{host}/api/chat",
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            t0 = time.perf_counter()
            with urllib.request.urlopen(req, timeout=1800) as r:
                res = json.load(r)
            wall = time.perf_counter() - t0
            msg = res["message"]
            flat = " ".join(msg["content"].split())
            print(f"{model} think={str(think).lower():<5} format={name:<6} "
                  f"thinking={len(msg.get('thinking', '')):>5} chars  "
                  f"tokens={res['eval_count']:>4}  eval={res['eval_duration'] / 1e9:6.1f} s  "
                  f"wall={wall:6.1f} s  done={res['done_reason']}\n    content: {flat[:70]}")
            if len(flat) > 140:
                print(f"    ...末尾: {flat[-70:]}")


if __name__ == "__main__":
    main()
