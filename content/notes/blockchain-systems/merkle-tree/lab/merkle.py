"""RFC 9162 (Certificate Transparency 2.0) section 2.1 の Merkle Tree。

葉は SHA-256(0x00 || データ)、内部ノードは SHA-256(0x01 || 左 || 右)。
葉の数が 2 の累乗でない時は、左に「n 未満で最大の 2 の累乗」個を置く（複製はしない）。
"""
import hashlib


def h(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def leaf_hash(data: bytes) -> bytes:
    return h(b"\x00" + data)


def node_hash(left: bytes, right: bytes) -> bytes:
    return h(b"\x01" + left + right)


def split(n: int) -> int:
    """n 未満で最大の 2 の累乗。"""
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def root(leaves: list[bytes]) -> bytes:
    """葉のハッシュの並びからルートハッシュを計算する。"""
    n = len(leaves)
    if n == 0:
        return h(b"")
    if n == 1:
        return leaves[0]
    k = split(n)
    return node_hash(root(leaves[:k]), root(leaves[k:]))


def inclusion_proof(m: int, leaves: list[bytes]) -> list[bytes]:
    """m 番目の葉からルートまでの兄弟のハッシュ（葉に近い順）。"""
    n = len(leaves)
    if n <= 1:
        return []
    k = split(n)
    if m < k:
        return inclusion_proof(m, leaves[:k]) + [root(leaves[k:])]
    return inclusion_proof(m - k, leaves[k:]) + [root(leaves[:k])]


def verify_inclusion(index, size, leaf, proof, expected_root) -> bool:
    """RFC 9162 2.1.3.2 の手順。"""
    if index >= size:
        return False
    fn, sn, r = index, size - 1, leaf
    for p in proof:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            r = node_hash(p, r)
            while not fn & 1 and fn != 0:
                fn >>= 1
                sn >>= 1
        else:
            r = node_hash(r, p)
        fn >>= 1
        sn >>= 1
    return sn == 0 and r == expected_root


def consistency_proof(m: int, leaves: list[bytes], whole: bool = True) -> list[bytes]:
    """先頭 m 件の木が、len(leaves) 件の木の先頭にそのまま入っていることの証明。"""
    n = len(leaves)
    if m == n:
        return [] if whole else [root(leaves)]
    k = split(n)
    if m <= k:
        return consistency_proof(m, leaves[:k], whole) + [root(leaves[k:])]
    return consistency_proof(m - k, leaves[k:], False) + [root(leaves[:k])]


def verify_consistency(first, second, first_root, second_root, proof) -> bool:
    """RFC 9162 2.1.4.2 の手順。"""
    if first == second:
        return not proof and first_root == second_root
    if first == 0 or first > second or not proof and first & (first - 1):
        return False
    if first & (first - 1) == 0:
        proof = [first_root] + list(proof)
    fn, sn = first - 1, second - 1
    while fn & 1:
        fn >>= 1
        sn >>= 1
    fr = sr = proof[0]
    for c in proof[1:]:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            fr = node_hash(c, fr)
            sr = node_hash(c, sr)
            while not fn & 1 and fn != 0:
                fn >>= 1
                sn >>= 1
        else:
            sr = node_hash(sr, c)
        fn >>= 1
        sn >>= 1
    return fr == first_root and sr == second_root and sn == 0
