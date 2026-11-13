"""merkle.py の検証の手順を、全ての (位置, 件数) で総当たりする。"""
from merkle import *

for n in range(1, 70):
    leaves = [leaf_hash(str(i).encode()) for i in range(n)]
    r = root(leaves)
    for m in range(n):
        p = inclusion_proof(m, leaves)
        assert verify_inclusion(m, n, leaves[m], p, r), (m, n)
        if n > 1:
            assert not verify_inclusion((m + 1) % n, n, leaves[m], p, r) or leaves[m] == leaves[(m+1)%n] or len(p)==0
    for m in range(1, n + 1):
        p = consistency_proof(m, leaves)
        assert verify_consistency(m, n, root(leaves[:m]), r, p), (m, n)
        bad = bytearray(root(leaves[:m])); bad[0] ^= 1
        assert not verify_consistency(m, n, bytes(bad), r, p) or m == n and False
print("ok")
