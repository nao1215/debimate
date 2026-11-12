"""Schnorr の知識の証明を secp256k1 の上で動かし、3 つの実験をする。

1. 1 ビットのチャレンジを繰り返す対話で、秘密鍵を知らない 1000 人が何ラウンドで全滅するか
2. 秘密鍵を知らないシミュレーターが、本物と同じ形のやり取りを作れるか
3. Fiat-Shamir のハッシュに R を入れないと、秘密鍵なしで証明を作れるか
"""
import hashlib
import json
import secrets
import sys

# secp256k1（Bitcoin・Ethereum の鍵の曲線）
P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    if a[0] == b[0] and (a[1] + b[1]) % P == 0:
        return None
    if a == b:
        m = 3 * a[0] * a[0] * pow(2 * a[1], -1, P) % P
    else:
        m = (b[1] - a[1]) * pow(b[0] - a[0], -1, P) % P
    x = (m * m - a[0] - b[0]) % P
    return (x, (m * (a[0] - x) - a[1]) % P)


def mul(k, pt=G):
    out = None
    while k:
        if k & 1:
            out = add(out, pt)
        pt = add(pt, pt)
        k >>= 1
    return out


def neg(pt):
    return (pt[0], (-pt[1]) % P)


def enc(pt):
    return bytes([2 + (pt[1] & 1)]) + pt[0].to_bytes(32, "big")


def h(*parts):
    return int.from_bytes(hashlib.sha256(b"".join(parts)).digest(), "big") % N


def verify(pub, R, c, s):
    """s·G = R + c·pub が成り立てば受け入れる。pub は本文の公開鍵 P"""
    return mul(s) == add(R, mul(c, pub))


x = secrets.randbelow(N - 1) + 1   # 秘密鍵（証明者だけが知る）
pub = mul(x)                        # 公開鍵（誰でも知っている）
results = {}

# --- 実験 1: 1 ビットのチャレンジを 20 ラウンド --------------------------------
def cheater_round():
    """秘密鍵を知らない人が、チャレンジを勘で予想して R を作る"""
    guess = secrets.randbelow(2)
    k = secrets.randbelow(N - 1) + 1
    R = mul(k) if guess == 0 else add(mul(k), neg(pub))  # guess=1 なら k·G - pub
    c = secrets.randbelow(2)       # 検証者が R を受け取った後に投げるチャレンジ
    s = k                          # 当たっていれば s = k で通る
    return verify(pub, R, c, s)

alive = 1000
survivors = [alive]
for _ in range(20):
    alive = sum(cheater_round() for _ in range(alive))
    survivors.append(alive)
results["survivors"] = survivors

honest_ok = 0
for _ in range(200):               # 秘密鍵を知る人は 20 ラウンドとも通るか
    ok = True
    for _ in range(20):
        k = secrets.randbelow(N - 1) + 1
        R = mul(k)
        c = secrets.randbelow(2)
        ok &= verify(pub, R, c, (k + c * x) % N)
    honest_ok += ok
results["honest_20rounds"] = f"{honest_ok}/200"

# --- 実験 2: 本物のやり取りと、シミュレーターが作ったやり取り ------------
TRIALS = 1000
real_ok = sim_ok = 0
for _ in range(TRIALS):
    k = secrets.randbelow(N)
    R = mul(k)                     # 1. 先に R を送る
    c = secrets.randbelow(N)       # 2. 検証者がチャレンジ c を返す
    s = (k + c * x) % N            # 3. 秘密鍵 x を使って答える
    real_ok += verify(pub, R, c, s)
    # シミュレーターは x を知らない。代わりに c と s を先に決め、R を後から作る
    c2 = secrets.randbelow(N)
    s2 = secrets.randbelow(N)
    R2 = add(mul(s2), neg(mul(c2, pub)))
    sim_ok += verify(pub, R2, c2, s2)
results["real_transcripts"] = f"{real_ok}/{TRIALS}"
results["simulated_transcripts"] = f"{sim_ok}/{TRIALS}"

# --- 実験 3: Fiat-Shamir でチャレンジをハッシュから作る ---------------------
msg = b"withdraw 1 ETH"
weak_ok = strong_ok = honest_weak = honest_strong = 0
for _ in range(TRIALS):
    # 偽造する人: x を知らない。s を選び、c を求めてから R を逆算する
    s = secrets.randbelow(N)
    c_weak = h(enc(pub), msg)                # R を入れないチャレンジ
    R = add(mul(s), neg(mul(c_weak, pub)))
    weak_ok += verify(pub, R, h(enc(pub), msg), s)
    c_strong = h(enc(R), enc(pub), msg)      # R を入れるチャレンジ（BIP340 と同じ順）
    strong_ok += verify(pub, R, c_strong, s)
    # 秘密鍵を知る人は、どちらでも通る
    k = secrets.randbelow(N)
    Rk = mul(k)
    cw = h(enc(pub), msg)
    honest_weak += verify(pub, Rk, cw, (k + cw * x) % N)
    cs = h(enc(Rk), enc(pub), msg)
    honest_strong += verify(pub, Rk, cs, (k + cs * x) % N)
results["forged_weak"] = f"{weak_ok}/{TRIALS}"
results["forged_strong"] = f"{strong_ok}/{TRIALS}"
results["honest_weak"] = f"{honest_weak}/{TRIALS}"
results["honest_strong"] = f"{honest_strong}/{TRIALS}"

json.dump(results, sys.stdout, ensure_ascii=False, indent=1)
print()
