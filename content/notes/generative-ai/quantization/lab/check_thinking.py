"""実験 3・4 と同じ指定（"think": false）で、思考の文が出ていないかを確かめる。

各モデルに、実験 4 の 1 問と実験 3 のプロンプトを送り、
message.thinking の長さ、content に <think> が含まれるか、eval_count を表示する。
比較のため、実験 4 の 1 問だけは "think": true でも送る。

使い方:
    OLLAMA_HOST=127.0.0.1:11435 python3 check_thinking.py > output_check_thinking.txt
"""
import json

from bench_speed import MODELS, NOTES, TASK, post
from eval_accuracy import SYSTEM

QUESTION = "What is the capital city of Brazil?"


def show(label, res):
    msg = res["message"]
    content = msg["content"]
    print(f"  {label:22s} thinking {len(msg.get('thinking', '')):5d} chars | "
          f"<think> in content: {'<think>' in content} | eval_count {res['eval_count']:4d} | "
          f"content: {json.dumps(content[:50], ensure_ascii=False)}")


def main():
    for model in MODELS:
        print(model)
        for think in (False, True):
            res = post("/api/chat", {
                "model": model,
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": QUESTION}],
                "think": think, "stream": False,
                "options": {"temperature": 0, "seed": 1, "num_predict": 1024, "num_ctx": 4096},
            })
            show(f"quiz, think={think}", res)
        res = post("/api/chat", {
            "model": model,
            "messages": [{"role": "user", "content": f"Request check.\n{NOTES}\n\n{TASK}"}],
            "think": False, "stream": False,
            "options": {"temperature": 0, "seed": 1, "num_predict": 128, "num_ctx": 4096},
        })
        show("bench, think=False", res)


if __name__ == "__main__":
    main()
