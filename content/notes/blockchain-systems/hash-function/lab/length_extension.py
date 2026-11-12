"""sha256(秘密 || 本文) を署名代わりにした API に、秘密を知らずに追記する（伸長攻撃）。

攻撃者が知っているのは、本文・その値・秘密の長さだけ。
SHA-256 の出力は内部状態そのものなので、そこから計算を続けられる。

    python3 length_extension.py
"""

import hashlib
import hmac
import struct

K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]
M32 = 0xFFFFFFFF


def ror(x, n):
    return ((x >> n) | (x << (32 - n))) & M32


def compress(h, block):
    w = list(struct.unpack(">16I", block))
    for i in range(16, 64):
        s0 = ror(w[i - 15], 7) ^ ror(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = ror(w[i - 2], 17) ^ ror(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w.append((w[i - 16] + s0 + w[i - 7] + s1) & M32)
    a, b, c, d, e, f, g, hh = h
    for i in range(64):
        t1 = (hh + (ror(e, 6) ^ ror(e, 11) ^ ror(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i]) & M32
        t2 = ((ror(a, 2) ^ ror(a, 13) ^ ror(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) & M32
        a, b, c, d, e, f, g, hh = (t1 + t2) & M32, a, b, c, (d + t1) & M32, e, f, g
    return [(x + y) & M32 for x, y in zip(h, [a, b, c, d, e, f, g, hh])]


def padding(total_len):
    """SHA-256 が total_len バイトの入力の後ろに足すパディング"""
    return b"\x80" + b"\x00" * ((55 - total_len) % 64) + struct.pack(">Q", total_len * 8)


def extend(tag_hex, known_len, extra):
    """値 tag_hex から計算を再開し、パディングの後ろに extra を足した入力の値を返す"""
    h = list(struct.unpack(">8I", bytes.fromhex(tag_hex)))  # 出力 = 内部状態
    done = known_len + len(padding(known_len))
    data = extra + padding(done + len(extra))
    for off in range(0, len(data), 64):
        h = compress(h, data[off:off + 64])
    return struct.pack(">8I", *h).hex()


# --- サーバー側（攻撃者には secret が見えない） ---
secret = b"server-only-16by"  # 16 バイト
body = b"to=0xA11CE&amount=1"


def sign(msg):
    return hashlib.sha256(secret + msg).hexdigest()


def verify(msg, tag):
    return hmac.compare_digest(sign(msg), tag)


# --- 攻撃者側: 本文、その値、秘密の長さ 16 だけを使う ---
tag = sign(body)
extra = b"&amount=1000000"
forged_body = body + padding(16 + len(body)) + extra
forged_tag = extend(tag, 16 + len(body), extra)

print("元の本文     ", body)
print("元の値       ", tag)
print("偽の本文     ", forged_body)
print("偽の値       ", forged_tag)
print("sha256 で検証", verify(forged_body, forged_tag))

# 同じ追記を HMAC-SHA256 と SHA3-256 の値に試す
mac = hmac.new(secret, body, hashlib.sha256).hexdigest()
print("HMAC で検証  ", hmac.compare_digest(
    hmac.new(secret, forged_body, hashlib.sha256).hexdigest(),
    extend(mac, 16 + len(body), extra)))
s3 = hashlib.sha3_256(secret + body).hexdigest()
print("SHA3 で検証  ", hashlib.sha3_256(secret + forged_body).hexdigest() == extend(s3, 16 + len(body), extra))
