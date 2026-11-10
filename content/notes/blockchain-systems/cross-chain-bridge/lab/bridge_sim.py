"""Lock-and-mint bridge between two simulated chains (no network access).

The vault on the source chain holds locked coins, and the destination chain
mints wrapped coins when enough validators sign a deposit message. HMAC stands
in for digital signatures so that the script needs only the standard library.

Scenarios:
  1. honest deposits and a withdrawal: wrapped supply == locked coins
  2. an attacker holding 5 of the 9 keys signs a release that has no burn
  3. a verifier that trusts the zero root accepts messages nobody proved

Run: python3 bridge_sim.py
"""

import hashlib
import hmac

KEYS = [f"validator-{i}".encode() for i in range(9)]
THRESHOLD = 5


def message(kind, nonce, to, amount):
    return f"{kind}|{nonce}|{to}|{amount}".encode()


def sign(key, msg):
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def enough_signatures(msg, sigs):
    valid = {i for i, s in sigs.items() if hmac.compare_digest(s, sign(KEYS[i], msg))}
    return len(valid) >= THRESHOLD


class Bridge:
    def __init__(self):
        self.locked = 0  # coins held by the vault on the source chain
        self.wrapped = {}  # wrapped coins on the destination chain
        self.used = set()  # nonces already processed

    def supply(self):
        return sum(self.wrapped.values())

    def mint(self, nonce, to, amount, sigs):
        """Destination chain: mint after a signed deposit message."""
        msg = message("deposit", nonce, to, amount)
        if nonce in self.used or not enough_signatures(msg, sigs):
            return False
        self.used.add(nonce)
        self.wrapped[to] = self.wrapped.get(to, 0) + amount
        return True

    def release(self, nonce, to, amount, sigs):
        """Source chain: pay out of the vault after a signed burn message."""
        msg = message("burn", nonce, to, amount)
        if nonce in self.used or not enough_signatures(msg, sigs):
            return False
        self.used.add(nonce)
        self.locked -= amount
        return True


def all_sign(msg, signers):
    return {i: sign(KEYS[i], msg) for i in signers}


def report(label, b):
    print(f"{label:<36} locked={b.locked:>4} wrapped={b.supply():>4}")


b = Bridge()
honest = range(9)

# 1. Alice and Carol lock coins on the source chain; validators sign the deposits.
for nonce, (who, amount) in enumerate([("alice", 100), ("carol", 300)]):
    b.locked += amount
    b.mint(nonce, who, amount, all_sign(message("deposit", nonce, who, amount), honest))
report("after deposits", b)

# Alice burns 40 wrapped coins and gets 40 coins back from the vault.
b.wrapped["alice"] -= 40
b.release(2, "alice", 40, all_sign(message("burn", 2, "alice", 40), honest))
report("after alice withdraws 40", b)

# Four keys are not enough.
stolen4 = range(4)
ok = b.release(3, "mallory", 360, all_sign(message("burn", 3, "mallory", 360), stolen4))
print(f"release with 4 stolen keys accepted: {ok}")

# 2. With 5 stolen keys, a release without any burn passes the check.
stolen5 = range(5)
ok = b.release(3, "mallory", 360, all_sign(message("burn", 3, "mallory", 360), stolen5))
print(f"release with 5 stolen keys accepted: {ok}")
report("after forged release", b)
print(f"wrapped coins without backing: {b.supply() - b.locked}")

# 3. Optimistic verification: a message is accepted when its root was proved.
ZERO = "00" * 32
proven = {ZERO: True}  # the mistake: the initial root 0x00 is marked as proved
root_of = {}  # message -> root it belongs to; unknown messages give ZERO


def accept(msg):
    return proven.get(root_of.get(msg, ZERO), False)


print(f"unproved message accepted: {accept(message('deposit', 99, 'mallory', 1000))}")
proven = {}  # without the mistake
print(f"unproved message accepted after fix: {accept(message('deposit', 99, 'mallory', 1000))}")
