"""Yeti 2022 で起きたこと（記録を保存した後、葉のハッシュが 1 ビット反転した）を小さなログで再現する。

ログは記録と葉のハッシュを別々に保存し、STH（件数とルートハッシュへの署名）は保存済みの葉のハッシュから作る。
監視する側（monitor）は記録を全件取り直し、自分で葉のハッシュを計算してルートを作り直す。
"""
from merkle import (leaf_hash, root, inclusion_proof, verify_inclusion,
                    consistency_proof, verify_consistency)

entries = [f"certificate #{i}".encode() for i in range(11_500)]
stored = [leaf_hash(e) for e in entries[:10_000]]   # ログが保存した葉のハッシュ
sth1 = (10_000, root(stored))                         # 反転の前に署名した STH

stored += [leaf_hash(e) for e in entries[10_000:11_000]]
FLIP = 10_500
b = bytearray(stored[FLIP])
b[0] ^= 0x01                                          # 保存した葉のハッシュが 1 ビット反転
stored[FLIP] = bytes(b)
sth2 = (11_000, root(stored))                         # 反転に気付かず署名した STH

print("1. 一貫性証明 sth1→sth2       :",
      verify_consistency(*sth1[:1], sth2[0], sth1[1], sth2[1], consistency_proof(10_000, stored)))
mine = [leaf_hash(e) for e in entries[:11_000]]       # 監視する側が記録から作り直した葉
print("2. 記録から作り直したルート   :", "一致" if root(mine) == sth2[1] else "不一致")
print("   先頭 10,000 件のルート     :", "一致" if root(mine[:10_000]) == sth1[1] else "不一致")
print("3. 記録 10,500 の葉を探す     :", "見つかる" if mine[FLIP] in stored else "見つからない")
print("   記録 10,499 の包含証明     :",
      verify_inclusion(10_499, 11_000, mine[10_499], inclusion_proof(10_499, stored), sth2[1]))
bad = [s for s in range(10_001, 11_001) if root(mine[:s]) != root(stored[:s])]
print(f"4. 件数 10,001〜11,000 のルート: {len(bad)} 通りが不一致（{bad[0]:,} 件以上の全て）")
diff = bin(int.from_bytes(root(mine), "big") ^ int.from_bytes(sth2[1], "big")).count("1")
print(f"   ルートの違い               : 256 ビットのうち {diff} ビット")

# 直す: 保存した葉を正しい値に戻して、続きを足す
fixed = mine + [leaf_hash(e) for e in entries[11_000:]]
sth3 = (11_500, root(fixed))
print("5. 直した木への一貫性証明 sth2→sth3:",
      verify_consistency(sth2[0], sth3[0], sth2[1], sth3[1], consistency_proof(11_000, fixed)))
print("   直した木への一貫性証明 sth1→sth3:",
      verify_consistency(sth1[0], sth3[0], sth1[1], sth3[1], consistency_proof(10_000, fixed)))
