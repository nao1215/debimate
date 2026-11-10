"""memory.json（実験 1 の記録）を表にする。Ollama には接続しない。"""
import json
import sys

PER_TOKEN = 2 * 28 * 8 * 128 * 2  # K と V × 層 × KV ヘッド × head_dim × f16 の 2 バイト

rows = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "memory.json"))
print(f"{'model':18s} {'num_ctx':>7s} {'loaded':>7s} {'ps size':>14s} {'after 1.8k':>14s} "
      f"{'log kv cache':>12s} {'calc kv cache':>13s}")
for r in rows:
    ctx = r["ps"]["context_length"]
    calc = ctx * PER_TOKEN / 2**20
    calc_s = f"{calc:.1f} MiB" if calc < 1024 else f"{calc / 1024:.3f} GiB"
    print(f"{r['model']:18s} {str(r['num_ctx']):>7s} {ctx:>7d} {r['ps']['size']:>14,d} "
          f"{r['ps_after_long']['size']:>14,d} {r['log']['kv cache ROCm0']:>12s} {calc_s:>13s}")
