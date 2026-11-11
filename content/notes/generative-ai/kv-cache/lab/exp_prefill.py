"""実験 2: num_ctx を 32768 に固定し、入力の長さだけを変えて、
プロンプトの処理の時間（prompt_eval_duration）と生成の速さを測る。

毎回、先頭に違う札（nonce）を置き、前回の KV キャッシュを使い回させない。
3 巡して、長さごとに中央値と最小・最大を出す。
"""
import json
import statistics
import sys
import time
import uuid

from kvlab import filler, generate, ps, ps_line

MODEL = "qwen3:1.7b-q8_0"
NUM_CTX = 32768
LINES = [19, 39, 79, 159, 319, 639, 1170]  # およそ 512〜30,000 トークン
ROUNDS = 3
TAIL = "\nIgnore the records. Write the integers from 1 to 300 separated by commas."

generate(MODEL, "Say hi.", num_ctx=NUM_CTX, num_predict=1)  # 読み込みを先に済ませる
rows = []
for rnd in range(ROUNDS):
    for n in LINES:
        before = ps()
        prompt = f"Session {uuid.uuid4().hex}\n" + filler(n, seed=rnd) + TAIL
        r = generate(MODEL, prompt, num_ctx=NUM_CTX, num_predict=64)
        after = ps()
        row = {"round": rnd + 1, "lines": n,
               "prompt_eval_count": r["prompt_eval_count"],
               "prompt_eval_s": r["prompt_eval_duration"] / 1e9,
               "eval_count": r["eval_count"], "eval_s": r["eval_duration"] / 1e9,
               "load_s": r["load_duration"] / 1e9, "thinking_chars": r["thinking_chars"],
               "ps_before": before, "ps_after": after, "time": time.strftime("%H:%M:%S")}
        rows.append(row)
        print(f"round {rnd + 1} prompt {row['prompt_eval_count']:6d} tok "
              f"prefill {row['prompt_eval_s']:7.3f} s ({row['prompt_eval_count'] / row['prompt_eval_s']:7.1f} tok/s) "
              f"| gen {row['eval_count']} tok {row['eval_count'] / row['eval_s']:5.1f} tok/s "
              f"| load {row['load_s']:.2f} s | thinking {row['thinking_chars']} chars", flush=True)
        print("    ps after:", ps_line(after), flush=True)

print("\n# median (min - max) over rounds")
for n in LINES:
    rs = [x for x in rows if x["lines"] == n]
    pe = [x["prompt_eval_s"] for x in rs]
    gen = [x["eval_count"] / x["eval_s"] for x in rs]
    print(f"prompt {statistics.median(x['prompt_eval_count'] for x in rs):6.0f} tok  "
          f"prefill {statistics.median(pe):7.3f} s ({min(pe):.3f}-{max(pe):.3f})  "
          f"gen {statistics.median(gen):5.1f} tok/s ({min(gen):.1f}-{max(gen):.1f})")

json.dump(rows, open(sys.argv[1] if len(sys.argv) > 1 else "prefill.json", "w"), indent=1)
