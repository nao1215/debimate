"""gpt-oss-20b の返答で、生成したトークンが本文・thinking のどちらに出るかを確かめる。

bench.py と同じ指定（think "low"、temperature 0）で、num_predict 128 と 1024 を 1 回ずつ送る。

使い方:
    python3 check_gptoss.py
"""
from bench import MODELS, TAIL, chat, filler

model, think = MODELS[2]
for n in (128, 1024):
    r = chat(model, think, "Session check\n" + filler(12, seed=0) + TAIL, num_predict=n)
    m = r["message"]
    print(f"num_predict {n:5d}: eval_count {r['eval_count']:5d} done_reason {r.get('done_reason')} | "
          f"thinking {len(m.get('thinking', '') or ''):5d} chars | content {len(m['content']):5d} chars")
    print("  thinking head:", repr((m.get("thinking") or "")[:120]))
    print("  content head :", repr(m["content"][:120]))
