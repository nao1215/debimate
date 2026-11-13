"""件数ごとに木を作り、包含証明と一貫性証明のハッシュの個数を数える。"""
import json, time
from merkle import leaf_hash, root, inclusion_proof, verify_inclusion, consistency_proof

rows = []
for n in [10, 100, 1_000, 10_000, 100_000, 1_000_000]:
    leaves = [leaf_hash(i.to_bytes(8, "big")) for i in range(n)]
    t = time.perf_counter()
    r = root(leaves)
    build = time.perf_counter() - t
    m = n * 3 // 5                      # 証明する記録の位置
    p = inclusion_proof(m, leaves)
    t = time.perf_counter()
    ok = verify_inclusion(m, n, leaves[m], p, r)
    verify = time.perf_counter() - t
    c = consistency_proof(n * 3 // 5, leaves)
    rows.append({"n": n, "inclusion": len(p), "consistency": len(c), "all_bytes": n * 32,
                 "build_s": build, "verify_us": verify * 1e6, "ok": ok})
    print(f"{n:>9,} 件  包含証明 {len(p):>2} 個  一貫性証明 {len(c):>2} 個"
          f"  全件の葉 {n * 32:>10,} バイト  ルートの計算 {build:6.2f} 秒  検証 {verify * 1e6:5.0f} µs  {ok}")
json.dump(rows, open("proof_size.json", "w"), indent=1)
