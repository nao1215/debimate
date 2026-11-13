"""WebAuthn の認証応答を、サーバー側でどの欄を照合すれば止まるかを 1 欄ずつ変えて調べる。

ブラウザと authenticator の役を Python で書き、正規の応答から 1 か所だけ変えた応答を作る。
照合は WebAuthn Level 3 の 7.2「Verifying an Authentication Assertion」の主な手順だけを実装した。
依存は cryptography だけ。実行: python3 verify.py
"""
import base64, hashlib, json, os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature

RP_ID = "app.example"
ORIGIN = "https://app.example"

def b64url(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

class Authenticator:
    """端末の中で秘密鍵を持つ役。synced=True は署名カウンタを常に 0 で返す同期型を表す。"""
    def __init__(self, rp_id, key=None, synced=False):
        self.rp_id, self.synced, self.count = rp_id, synced, 0
        self.key = key or ec.generate_private_key(ec.SECP256R1())
    def sign(self, client_data_json, uv=True):
        if not self.synced:
            self.count += 1
        flags = 0x01 | (0x04 if uv else 0)           # UP（触れた）と UV（ユーザー確認）
        auth_data = (hashlib.sha256(self.rp_id.encode()).digest()
                     + bytes([flags]) + self.count.to_bytes(4, "big"))
        sig = self.key.sign(auth_data + hashlib.sha256(client_data_json).digest(),
                            ec.ECDSA(hashes.SHA256()))
        return {"clientDataJSON": client_data_json, "authenticatorData": auth_data, "signature": sig}

def client_data(challenge, origin, typ="webauthn.get"):
    """ブラウザが作る clientDataJSON。origin はページの実際の origin が入る。"""
    return json.dumps({"type": typ, "challenge": b64url(challenge), "origin": origin}).encode()

class RelyingParty:
    """サーバー。登録時に保存した公開鍵と署名カウンタだけを持つ。

    require_uv=True は、ログインの要求で userVerification を required にした設定を表す。
    UV を求めるかは RP が選ぶ。求めない設定なら UV の無い応答も通す。
    """
    def __init__(self, public_key, check_origin=True, require_uv=True):
        self.public_key, self.stored_count, self.check_origin = public_key, 0, check_origin
        self.require_uv = require_uv
    def new_challenge(self):
        self.challenge = os.urandom(32)
        return self.challenge
    def verify(self, r):
        c = json.loads(r["clientDataJSON"])
        a = r["authenticatorData"]
        if c["type"] != "webauthn.get":
            return "拒否: type"
        if c["challenge"] != b64url(self.challenge):
            return "拒否: challenge"
        if self.check_origin and c["origin"] != ORIGIN:
            return "拒否: origin"
        if a[:32] != hashlib.sha256(RP_ID.encode()).digest():
            return "拒否: rpIdHash"
        if not a[32] & 0x01:
            return "拒否: UP フラグ"
        if self.require_uv and not a[32] & 0x04:
            return "拒否: UV フラグ"
        try:
            self.public_key.verify(r["signature"], a + hashlib.sha256(r["clientDataJSON"]).digest(),
                                   ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            return "拒否: 署名"
        count = int.from_bytes(a[33:37], "big")
        if count != 0 or self.stored_count != 0:
            if count <= self.stored_count:
                return f"通す（カウンタ {count} <= {self.stored_count}、複製の疑い）"
            self.stored_count = count
        return "通す"

def run(check_origin):
    dev = Authenticator(RP_ID)
    rp = RelyingParty(dev.key.public_key(), check_origin)
    out = {}
    ch = rp.new_challenge()
    out["正規の応答"] = rp.verify(dev.sign(client_data(ch, ORIGIN)))
    ch = rp.new_challenge()
    out["サブドメインのページ"] = rp.verify(dev.sign(client_data(ch, "https://uploads.app.example")))
    old = rp.challenge
    rp.new_challenge()
    out["前回の challenge"] = rp.verify(dev.sign(client_data(old, ORIGIN)))
    ch = rp.new_challenge()
    other = Authenticator("app-example.net", key=dev.key)
    out["似たドメインの rpId"] = rp.verify(other.sign(client_data(ch, ORIGIN)))
    ch = rp.new_challenge()
    out["UV なし"] = rp.verify(dev.sign(client_data(ch, ORIGIN), uv=False))
    ch = rp.new_challenge()
    r = dev.sign(client_data(ch, ORIGIN))
    r["clientDataJSON"] = r["clientDataJSON"].replace(b'"webauthn.get"', b'"webauthn.get" ')
    out["署名後に 1 byte 変更"] = rp.verify(r)
    ch = rp.new_challenge()
    out["別の鍵で署名"] = rp.verify(Authenticator(RP_ID).sign(client_data(ch, ORIGIN)))
    return out

def counters():
    """署名カウンタで鍵の複製に気付けるか。カウンタを 0 で返す鍵と 1 台の中で数える鍵を比べる。"""
    res = {}
    for synced in (False, True):
        a = Authenticator(RP_ID, synced=synced)
        b = Authenticator(RP_ID, key=a.key, synced=synced)   # 同じ秘密鍵を持つ 2 台目
        rp = RelyingParty(a.key.public_key())
        log = []
        for who, dev in (("端末 A", a), ("端末 A", a), ("端末 B", b)):
            ch = rp.new_challenge()
            r = dev.sign(client_data(ch, ORIGIN))
            log.append((who, int.from_bytes(r["authenticatorData"][33:37], "big"), rp.verify(r)))
        res["カウンタを 0 で返す鍵" if synced else "1 台の中で数える鍵"] = log
    return res

if __name__ == "__main__":
    full, no_origin = run(True), run(False)
    print("応答 | 全部チェックするサーバー | origin をチェックしないサーバー")
    for k in full:
        print(f"{k} | {full[k]} | {no_origin[k]}")
    print()
    for kind, log in counters().items():
        print(kind)
        for who, count, verdict in log:
            print(f"  {who} signCount={count} -> {verdict}")
