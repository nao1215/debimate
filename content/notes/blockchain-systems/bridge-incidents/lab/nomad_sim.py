"""Nomad's initialization mistake, reduced to two dictionaries (no network access).

An optimistic bridge accepts a message when the Merkle root the message
belongs to has been proved and its waiting period has passed. Nomad's
upgrade registered the zero root 0x00 as proved. A message that belongs to
no proved root looks up the zero root, so every unproved message passed.

Run: python3 nomad_sim.py
"""


def message(kind, nonce, to, amount):
    return f"{kind}|{nonce}|{to}|{amount}".encode()


ZERO = "00" * 32
proven = {ZERO: True}  # the mistake: the initial root 0x00 is marked as proved
root_of = {}  # message -> root it belongs to; unknown messages give ZERO


def accept(msg):
    return proven.get(root_of.get(msg, ZERO), False)


forged = message("deposit", 99, "mallory", 1000)
print(f"unproved message accepted: {accept(forged)}")
proven = {}  # without the mistake
print(f"unproved message accepted after fix: {accept(forged)}")
