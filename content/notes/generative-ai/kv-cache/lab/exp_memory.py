"""実験 1: num_ctx を変えて読み込み、/api/ps の size と、ログの KV キャッシュの大きさを記録する。

同じ num_ctx で短いプロンプトと長いプロンプトを送り、size が入力の長さで変わるかも見る。
"""
import json
import sys
import time

from kvlab import filler, generate, load_log, ps, ps_line, unload

CASES = [
    ("qwen3:1.7b-q8_0", None), ("qwen3:1.7b-q8_0", 2048), ("qwen3:1.7b-q8_0", 4096),
    ("qwen3:1.7b-q8_0", 8192), ("qwen3:1.7b-q8_0", 16384), ("qwen3:1.7b-q8_0", 32768),
    ("qwen3:1.7b-q8_0", 40960),
    # 重みの形式だけを変える（KV キャッシュは同じ大きさになるはず）
    ("qwen3:1.7b-fp16", 4096), ("qwen3:1.7b-fp16", 32768),
    ("qwen3:1.7b-q4_K_M", None), ("qwen3:1.7b-q4_K_M", 4096),
]

results = []
for model, ctx in CASES:
    print(f"## {model} num_ctx={ctx}", flush=True)
    print("  ps before:", ps_line(ps()), flush=True)
    gone = unload(model)
    t0 = time.time() - 2
    r = generate(model, "Say hi.", num_ctx=ctx, num_predict=1, keep_alive="5m")
    time.sleep(1)
    after = ps()
    mine = [x for x in after if x["name"] == model]
    log = load_log(model, t0)
    row = {"model": model, "num_ctx": ctx, "unloaded_first": gone,
           "ps": mine[0] if mine else None, "log": log,
           "load_duration_s": r["load_duration"] / 1e9, "thinking_chars": r["thinking_chars"]}
    # 同じ num_ctx のまま長い入力（約 1,800 トークン）を送り、size が変わるかを見る
    r2 = generate(model, filler(70) + "\nHow many records are listed above? Answer with a number.",
                  num_ctx=ctx, num_predict=8, keep_alive="5m")
    mine2 = [x for x in ps() if x["name"] == model]
    row["long_prompt_eval_count"] = r2["prompt_eval_count"]
    row["ps_after_long"] = mine2[0] if mine2 else None
    row["long_load_duration_s"] = r2["load_duration"] / 1e9
    print("  ps after :", ps_line(after), flush=True)
    print("  log      :", json.dumps(log, ensure_ascii=False), flush=True)
    print(f"  long prompt {r2['prompt_eval_count']} tok -> size "
          f"{(mine2[0]['size'] / 1e9) if mine2 else float('nan'):.3f} GB", flush=True)
    results.append(row)
    unload(model)

json.dump(results, open(sys.argv[1] if len(sys.argv) > 1 else "memory.json", "w"),
          indent=1, ensure_ascii=False)
