"""Keccak-256 と SHA3-256 を同じコードで計算する（標準ライブラリだけ）。

2 つの違いは、最後のブロックに足す区切りのバイト（0x01 か 0x06）だけ。
SHA3-256 の結果は hashlib.sha3_256 と照合する。

    python3 keccak.py
"""

import hashlib

RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
ROT = [1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 2, 14, 27, 41, 56, 8, 25, 43, 62, 18, 39, 61, 20, 44]
PI = [10, 7, 11, 17, 18, 3, 5, 16, 8, 21, 24, 4, 15, 23, 19, 13, 12, 2, 20, 14, 22, 9, 6, 1]
M64 = (1 << 64) - 1


def rotl(x, n):
    return ((x << n) | (x >> (64 - n))) & M64


def keccak_f(s):
    for rc in RC:
        c = [s[i] ^ s[i + 5] ^ s[i + 10] ^ s[i + 15] ^ s[i + 20] for i in range(5)]
        for i in range(5):
            d = c[(i + 4) % 5] ^ rotl(c[(i + 1) % 5], 1)
            for j in range(0, 25, 5):
                s[i + j] ^= d
        t = s[1]
        for r, p in zip(ROT, PI):
            s[p], t = rotl(t, r), s[p]
        for j in range(0, 25, 5):
            row = s[j:j + 5]
            for i in range(5):
                s[i + j] = row[i] ^ (~row[(i + 1) % 5] & row[(i + 2) % 5])
        s[0] ^= rc


def sponge256(data: bytes, pad: int) -> bytes:
    rate = 136  # 1088 ビット。残りの 512 ビットは外に出さない
    msg = bytearray(data)
    msg.append(pad)  # Keccak-256 は 0x01、SHA3-256 は 0x06
    msg.extend(b"\x00" * (-len(msg) % rate))
    msg[-1] |= 0x80
    s = [0] * 25
    for off in range(0, len(msg), rate):
        for i in range(rate // 8):
            s[i] ^= int.from_bytes(msg[off + 8 * i: off + 8 * i + 8], "little")
        keccak_f(s)
    return b"".join(x.to_bytes(8, "little") for x in s[:4])


def keccak256(data: bytes) -> bytes:
    return sponge256(data, 0x01)


def sha3_256(data: bytes) -> bytes:
    return sponge256(data, 0x06)


if __name__ == "__main__":
    for data in [b"", b"transfer(address,uint256)"]:
        assert sha3_256(data) == hashlib.sha3_256(data).digest()
        print(f"入力       {data!r}")
        print(f"keccak256  {keccak256(data).hex()}")
        print(f"sha3_256   {hashlib.sha3_256(data).hexdigest()}")
    for sig in ["transfer(address,uint256)",
                "putCurEpochConPubKeyBytes(bytes)",
                "f1121318093(bytes,bytes,uint64)"]:
        print(f"{keccak256(sig.encode())[:4].hex()}  {sig}")
