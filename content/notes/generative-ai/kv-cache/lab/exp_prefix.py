"""実験 3: 同じプレフィックスを送り直した時に、KV キャッシュが使い回されるかを見る。

Ollama 0.22.1 の prompt_eval_count は、使い回した分も含めた入力の全トークン数を返す。
使い回せたかどうかは、prompt_eval_duration（キャッシュに無かった分を計算した時間）で見る。
"""
import json
import sys
import uuid

from kvlab import filler, generate, ps, ps_line

MODEL = "qwen3:1.7b-q8_0"
NUM_CTX = 32768
Q1 = "\nWhich sensor appears in Record 5? Answer briefly."
Q2 = "\nWhich sensor appears in Record 9? Answer briefly."

rows = []
generate(MODEL, "Say hi.", num_ctx=NUM_CTX, num_predict=1)
for rnd in range(3):
    head = f"Session {uuid.uuid4().hex}\n"
    lines = filler(320, seed=10 + rnd).split("\n")
    base = head + "\n".join(lines)
    mid = len(lines) // 2
    changed_mid = head + "\n".join(lines[:mid] + ["Record X: this line was edited."] + lines[mid + 1:])
    cases = [
        ("1 first send", base + Q1),
        ("2 same prompt again", base + Q1),
        ("3 same prefix, new question", base + Q2),
        ("4 one line edited in the middle", changed_mid + Q1),
        ("5 one char added at the head", "X" + base + Q1),
    ]
    for label, prompt in cases:
        r = generate(MODEL, prompt, num_ctx=NUM_CTX, num_predict=16)
        row = {"round": rnd + 1, "case": label, "prompt_eval_count": r["prompt_eval_count"],
               "prompt_eval_s": r["prompt_eval_duration"] / 1e9, "load_s": r["load_duration"] / 1e9,
               "thinking_chars": r["thinking_chars"], "response": r["response"], "ps": ps()}
        rows.append(row)
        print(f"round {rnd + 1} {label:34s} prompt {row['prompt_eval_count']:5d} tok "
              f"prompt_eval {row['prompt_eval_s']:6.3f} s | load {row['load_s']:.2f} s "
              f"| thinking {row['thinking_chars']} chars | {r['response'].strip()[:40]!r}", flush=True)
    print("    ps:", ps_line(ps()), flush=True)

json.dump(rows, open(sys.argv[1] if len(sys.argv) > 1 else "prefix.json", "w"), indent=1,
          ensure_ascii=False)
