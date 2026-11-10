"""30 個の課題 × seed（既定 3 個）でループを回し、止まった理由と失敗の種類を数える。

使い方: OLLAMA_HOST=127.0.0.1:11435 python3 run_bench.py qwen3:8b off bench_qwen3-8b_off.jsonl
（2 つ目の引数は思考モード。on なら think: true、off なら think: false を送る。
 4 つ目に seed の数を渡せる。既定は 3。qwen3:4b は時間が掛かるので 1 で回した）
"""
import json
import sys
from collections import Counter

from agent import run_agent
from tasks import TASKS, grade

SYSTEM = ("あなたはツールを使って質問に答えるアシスタントです。"
          "必要ならツールを呼び、結果を確かめてから日本語で簡潔に最終回答してください。"
          "ツールで分からないことは、分からないと答えてください。")
TOOL_NAMES = ["calculate", "get_weather", "convert_temperature", "list_files", "read_file"]


def main():
    model, think, out = sys.argv[1], sys.argv[2] == "on", sys.argv[3]
    seeds = range(1, (int(sys.argv[4]) if len(sys.argv) > 4 else 3) + 1)
    with open(out, "w") as f:
        for seed in seeds:
            for i, (kind, question, check) in enumerate(TASKS):
                r = run_agent(model, SYSTEM, question, TOOL_NAMES, seed, think)
                r.update(task=i, kind=kind, seed=seed)
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                r["correct"] = r["stop"] == "answer" and grade(r["answer"], check)
                f.flush()
                print(f"seed={seed} task={i:2d} {kind:8s} stop={r['stop']:12s} "
                      f"steps={r['steps']} ok={r['correct']} "
                      f"calls={[c['name'] + ('!' + c['error'] if 'error' in c else '') for c in r['calls']]}",
                      flush=True)
    rows = [json.loads(line) for line in open(out)]
    ok = sum(r["stop"] == "answer" and grade(r["answer"], TASKS[r["task"]][2]) for r in rows)
    print("\nruns:", len(rows), " correct:", ok)
    print("stop:", dict(Counter(r["stop"] for r in rows)))
    print("steps:", dict(sorted(Counter(r["steps"] for r in rows).items())))
    print("call errors:", dict(Counter(c.get("error", "ok") for r in rows for c in r["calls"])))


if __name__ == "__main__":
    main()
