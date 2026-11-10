"""応答の 1 トークン目について、モデルが付けた確率の上位を Ollama から取り出す（冒頭の図の元データ）。

format を付けずに、chat と同じ形のプロンプトを raw で /api/generate に送り、
logprobs と top_logprobs で 1 トークン目の候補の確率を受け取る。
各候補が、スキーマから作った文法の先頭（"{" の後に空白、続けて "person" のキー）に合うかも判定する。

使い方:
    OLLAMA_HOST=127.0.0.1:11435 python3 probe.py <モデル> <入力の番号> [出力の JSON]
"""
import json
import math
import os
import re
import sys
import urllib.request

from run import PROMPT
from texts import make_items

# 文法が 1 トークン目に許す文字列: "{"、空白、'"person"' の先頭部分の順
ALLOWED = re.compile(r'^\{[ \t\n]*(?:"(?:p(?:e(?:r(?:s(?:o(?:n(?:")?)?)?)?)?)?)?)?$')


def main():
    model, idx = sys.argv[1], int(sys.argv[2])
    out_path = sys.argv[3] if len(sys.argv) > 3 else None
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    text = make_items()[idx]["text"]
    # qwen3 のチャットテンプレートで think: false を指定した時と同じ並び
    # （テンプレートは最後のユーザー発言の末尾に " /no_think" を足す。
    #   /api/chat に "_debug_render_only": true を付けて描画した結果と照合した）
    prompt = ("<|im_start|>user\n" + PROMPT.format(text=text) + " /no_think<|im_end|>\n"
              "<|im_start|>assistant\n<think>\n\n</think>\n\n")
    body = {"model": model, "prompt": prompt, "raw": True, "stream": False,
            "logprobs": True, "top_logprobs": 10,
            "options": {"temperature": 0, "seed": 42, "num_predict": 1}}
    req = urllib.request.Request(f"http://{host}/api/generate", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        res = json.load(r)
    print(f"input {idx}: {text}")
    print(f"greedy first token: {res['response']!r}")
    cands = []
    for t in res["logprobs"][0]["top_logprobs"]:
        p = math.exp(t["logprob"])
        ok = bool(ALLOWED.match(t["token"]))
        cands.append({"token": t["token"], "p": p, "allowed": ok,
                      "shown": t["token"].replace("\n", "\\n")})
        print(f"  {t['token']!r:>12}  p={p:.4f}  {'allowed' if ok else 'rejected'}")
    if out_path:
        with open(out_path, "w") as f:
            json.dump({"model": model, "input": idx, "candidates": cands,
                       "prefix_shown": "1 トークン目",
                       "caption": f"点線はスキーマの文法に合わない候補（{model}、入力 {idx}）"},
                      f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
