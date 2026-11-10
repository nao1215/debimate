"""同じ問題集を 3 つのモデルに解かせ、正答率を数える。

思考モード（thinking）は "think": false で無効にし、答えだけを出させる。
温度 0・seed 固定なので、同じ環境なら同じ答えが返る想定。

使い方:
    OLLAMA_HOST=127.0.0.1:11435 python3 eval_accuracy.py problems.json accuracy.json
"""
import json
import os
import re
import sys
import urllib.request

MODELS = ["qwen3:1.7b-q4_K_M", "qwen3:1.7b-q8_0", "qwen3:1.7b-fp16"]
SYSTEM = "Answer with only the final answer. Do not explain."
BASE = "http://" + os.environ.get("OLLAMA_HOST", "127.0.0.1:11435")


def chat(model, question):
    body = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": question}],
        "think": False,                       # qwen3 の思考モードを無効にする
        "stream": False,
        "options": {"temperature": 0, "seed": 1, "num_predict": 128, "num_ctx": 4096},
    }
    req = urllib.request.Request(BASE + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        res = json.load(r)
    return res["message"]["content"], res["message"].get("thinking", "")


def is_correct(kind, reply, answers):
    text = reply.lower().replace(",", "")
    if kind == "math":
        nums = re.findall(r"-?\d+", text)
        return bool(nums) and nums[-1] == answers[0]       # 最後に出た整数で判定する
    return any(re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", text)
               for a in answers)


def main():
    problems = json.load(open(sys.argv[1]))
    out_path = sys.argv[2]
    result = {"models": {}}
    for model in MODELS:
        rows = []
        for p in problems:
            reply, thinking = chat(model, p["question"])
            ok = is_correct(p["kind"], reply, p["answers"])
            rows.append({"id": p["id"], "kind": p["kind"], "reply": reply.strip(),
                         "thinking_chars": len(thinking), "correct": ok})
        result["models"][model] = rows
        for kind in ("math", "knowledge"):
            sub = [r for r in rows if r["kind"] == kind]
            print(f"{model:20s} {kind:9s} {sum(r['correct'] for r in sub):3d} / {len(sub)}")
        total = sum(r["correct"] for r in rows)
        print(f"{model:20s} {'total':9s} {total:3d} / {len(rows)}"
              f"   (replies with thinking: {sum(r['thinking_chars'] > 0 for r in rows)})")
    # fp16 と答え（文字列）が一致した問題の数
    ref = result["models"][MODELS[-1]]
    for model in MODELS[:-1]:
        same = sum(a["reply"] == b["reply"] for a, b in zip(result["models"][model], ref))
        print(f"same reply as fp16: {model:20s} {same} / {len(ref)}")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
