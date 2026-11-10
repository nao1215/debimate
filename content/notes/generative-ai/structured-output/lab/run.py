"""同じ抽出課題を 3 つの方式で Ollama の /api/chat に解かせ、応答と時間を JSON Lines に保存する。

方式:
  prompt : プロンプトで JSON を頼むだけ（format を付けない）
  json   : format: "json"（JSON の構文だけを守らせる）
  schema : format: <JSON Schema>（スキーマから作った文法で生成を縛る）
  schema_bare : schema と同じ format で、プロンプトにはキーも形式も書かない（追加の比較）

使い方:
    OLLAMA_HOST=127.0.0.1:11435 python3 run.py <出力の .jsonl> <モデル> <繰り返し回数> [方式,...]
方式の既定は prompt,json,schema。
1 回目は 40 件全て、2 回目以降は時間を測るために先頭の 20 件だけを解かせる。
出力に既にある組（モデル・回・入力・方式）は飛ばすので、途中で止めても続きから再開できる。
Python 標準ライブラリだけで動く。
"""
import json
import os
import sys
import time
import urllib.request

from texts import make_items

SCHEMA = {
    "type": "object",
    "properties": {
        "person": {"type": "string"},
        "date": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
        "amount_yen": {"type": "integer"},
    },
    "required": ["person", "date", "amount_yen"],
    "additionalProperties": False,
}
FORMATS = {"prompt": None, "json": "json", "schema": SCHEMA, "schema_bare": SCHEMA}
N_ITEMS, TIMING_ITEMS = 40, 20

PROMPT = """次の文から、取引の当事者（お金を払った・受け取った・請求された人）の名前、日付、金額を取り出してください。
出力は JSON だけにしてください。キーは person（敬称を付けない名前）、date（YYYY-MM-DD 形式）、amount_yen（円単位の整数）の 3 つです。

文: {text}"""

# schema_bare 用: 何を取り出すかだけを書き、キー名・日付の形式・JSON で答えることは書かない
PROMPT_BARE = """次の文から、取引の当事者の名前、日付、金額を取り出してください。

文: {text}"""


def chat(host, model, text, fmt, prompt=PROMPT):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt.format(text=text)}],
        "stream": False,
        "think": False,  # qwen3 の思考モードを切る（qwen3:4b は切れない。本文参照）
        "options": {"temperature": 0, "seed": 42, "num_predict": 512},
    }
    if fmt is not None:
        body["format"] = fmt
    req = urllib.request.Request(f"http://{host}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=1800) as r:
        res = json.load(r)
    res["wall_s"] = time.perf_counter() - t0
    return res


def main():
    out_path, model, repeats = sys.argv[1], sys.argv[2], int(sys.argv[3])
    names = sys.argv[4].split(",") if len(sys.argv) > 4 else ["prompt", "json", "schema"]
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    items = make_items(N_ITEMS)
    done = set()
    if os.path.exists(out_path):
        for line in open(out_path):
            r = json.loads(line)
            done.add((r["model"], r["rep"], r["id"], r["method"]))
    with open(out_path, "a") as f:
        for rep in range(repeats):
            for it in items if rep == 0 else items[:TIMING_ITEMS]:
                k = (it["id"] + rep) % len(names)  # 方式の順番を回して、負荷の偏りを散らす
                for method in names[k:] + names[:k]:
                    if (model, rep, it["id"], method) in done:
                        continue
                    prompt = PROMPT_BARE if method == "schema_bare" else PROMPT
                    res = chat(host, model, it["text"], FORMATS[method], prompt)
                    f.write(json.dumps({
                        "model": model, "rep": rep, "id": it["id"], "method": method,
                        "content": res["message"]["content"],
                        "thinking": res["message"].get("thinking", ""),
                        "done_reason": res.get("done_reason"),
                        "eval_count": res.get("eval_count"),
                        "eval_s": res.get("eval_duration", 0) / 1e9,
                        "prompt_eval_s": res.get("prompt_eval_duration", 0) / 1e9,
                        "load_s": res.get("load_duration", 0) / 1e9,
                        "total_s": res.get("total_duration", 0) / 1e9,
                        "wall_s": res["wall_s"],
                    }, ensure_ascii=False) + "\n")
                    f.flush()
            print(f"{model} rep {rep} done", flush=True)


if __name__ == "__main__":
    main()
