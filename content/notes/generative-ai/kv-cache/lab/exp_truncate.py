"""実験 4: 入力が num_ctx を超えた時に何が起きるか。

先頭に合言葉を置き、約 3,000 トークンの詰め物の後で合言葉を尋ねる（入力の全体は約 3,100 トークン）。
num_ctx 2048（足りない）と 8192（足りる）で比べる。
"""
import json
import subprocess
import sys

from kvlab import LOG_UNIT, filler, generate, ps, ps_line

MODEL = "qwen3:1.7b-q8_0"
PROMPT = ("The secret code is BLUE-FALCON-42. Remember it.\n" + filler(120, seed=7) +
          "\nWhat is the secret code given at the very beginning? Answer with the code only.")

rows = []
for ctx in (2048, 8192):
    print(f"## num_ctx={ctx}  ps before: {ps_line(ps())}", flush=True)
    # 送る直前のログの位置（cursor）を覚え、その後に出た行だけを見る
    cur = subprocess.run(["journalctl", "--user", "-u", LOG_UNIT, "-n", "0", "--show-cursor"],
                         capture_output=True, text=True).stdout.split("cursor: ")[-1].strip()
    try:
        r = generate(MODEL, PROMPT, num_ctx=ctx, num_predict=32)
        row = {"num_ctx": ctx, "prompt_eval_count": r["prompt_eval_count"],
               "done_reason": r.get("done_reason"), "thinking_chars": r["thinking_chars"],
               "response": r["response"]}
    except Exception as e:  # エラーで返る版もあるので、その時は本文を記録する
        body = e.read().decode() if hasattr(e, "read") else str(e)
        row = {"num_ctx": ctx, "error": body}
    # サーバーのログに切り詰めの警告が出たかを見る
    log = subprocess.run(["journalctl", "--user", "-u", LOG_UNIT, f"--after-cursor={cur}",
                          "--no-pager", "-o", "cat"], capture_output=True, text=True).stdout
    row["server_log"] = [ln.split("source=")[1] for ln in log.splitlines()
                         if "truncating input prompt" in ln]
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)
    print(f"   ps after: {ps_line(ps())}", flush=True)

json.dump(rows, open(sys.argv[1] if len(sys.argv) > 1 else "truncate.json", "w"), indent=1,
          ensure_ascii=False)
