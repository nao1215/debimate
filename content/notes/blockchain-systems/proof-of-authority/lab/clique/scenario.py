"""Stop Clique signers, split them 2 | 2, and record what the chain does.

Run after `./net.sh up`. Prints one summary per phase, then which side's
blocks node1 keeps after the split was healed. Usage: python3 scenario.py [--hold]
"""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rpc import block, call, head  # noqa: E402

HERE = Path(__file__).resolve().parent
KEYS = HERE.parent / "keys"
A = {i: f"10.231.13.1{i}" for i in (1, 2, 3, 4)}          # shared network
SIDE = {1: "10.231.14.11", 2: "10.231.14.12",              # pair networks,
        3: "10.231.15.13", 4: "10.231.15.14"}              # also used for RPC
ADDR = {i: (KEYS / f"node{i}/address").read_text().strip() for i in A}
NAME = {a: i for i, a in ADDR.items()}
ORDER = sorted(A, key=lambda i: ADDR[i])  # in-turn index = sorted position


def net(*args):
    subprocess.run([str(HERE / "net.sh"), *map(str, args)], check=True)


def enode(i, ip):
    return f"enode://{(KEYS / f'node{i}/key.pub').read_text().strip()[2:]}@{ip}:30303"


def peer_all():
    """Static peers: pairs over their own network, cross pairs over A."""
    for i in A:
        for j in A:
            if i < j:
                same = (i <= 2) == (j <= 2)
                call(SIDE[i], "admin_addPeer", [enode(j, SIDE[j] if same else A[j]), True])


def signer(ip, b):
    return NAME.get(call(ip, "clique_getBlockSigner", [b["hash"]]), "?")


def chain(ip, lo, hi):
    """'n4*' = block signed by node4 out of turn (difficulty 1)."""
    out = []
    for n in range(lo, hi + 1):
        b = block(ip, n)
        if not b:
            break
        s = signer(ip, b)
        out.append(f"n{s}" + ("" if int(b["difficulty"], 16) == 2 else "*"))
    return " ".join(out)


def tip(nodes=(1, 2, 3, 4)):
    return max((head(SIDE[i]) or (0, ""))[0] for i in nodes)


def watch(label, secs, nodes=(1, 2, 3, 4), ip=SIDE[1]):
    start, t0, first = tip(nodes), time.time(), None
    while time.time() - t0 < secs:
        if first is None and tip(nodes) > start:
            first = time.time() - t0
        time.sleep(0.5)
    end = tip(nodes)
    fn = f"{first:.1f}s" if first is not None else "-"
    print(f"{label:28} {end - start:3} blocks  first new {fn:>6}  "
          f"{chain(ip, start + 1, min(end, start + 12))}")
    return start, end


def main():
    print("in-turn order:", " ".join(f"n{i}" for i in ORDER), "(block number % 4)")
    peer_all()
    while tip() < 2:
        time.sleep(1)
    watch("4/4 running", 30)
    net("stop", 4)
    watch("node4 stopped (3/4)", 30, (1, 2, 3))
    net("stop", 3)
    watch("node3 stopped too (2/4)", 30, (1, 2))
    net("start", 3)
    net("start", 4)
    time.sleep(8)
    peer_all()
    watch("node3, node4 restarted", 40)

    # Split right after two blocks signed by different pairs, so that the
    # recent-signer window does not favour one side.
    while True:
        n = tip()
        a, b = (signer(SIDE[1], block(SIDE[1], k)) for k in (n - 1, n))
        if (a <= 2) != (b <= 2):
            break
        time.sleep(0.3)
    net("cut")
    s, _ = watch("split: node1+node2", 30, (1, 2), SIDE[1])
    left = {n: block(SIDE[1], n)["hash"] for n in range(s + 1, tip((1, 2)) + 1)}
    right = {n: block(SIDE[3], n)["hash"] for n in range(s + 1, tip((3, 4)) + 1)}
    print(f"{'split: node3+node4':28} {len(right):3} blocks  {'':16}"
          f"{chain(SIDE[3], s + 1, tip((3, 4)))}")
    net("heal")
    while len(call(SIDE[1], "admin_peers") or []) < 3:
        time.sleep(1)
    watch("healed", 40)
    for i in A:
        n, h = head(SIDE[i])
        print(f"  node{i} head: {n} {h[:10]} signed by n{signer(SIDE[i], block(SIDE[i], n))}")
    kept = {n: (block(SIDE[1], n) or {}).get("hash") for n in set(left) | set(right)}
    for side, blocks in (("node1+node2", left), ("node3+node4", right)):
        lost = [n for n, h in blocks.items() if kept[n] != h]
        print(f"after heal, {side} side: {len(blocks) - len(lost)} kept, "
              f"{len(lost)} dropped {sorted(lost)}")
    if "--hold" in sys.argv:  # keep watching a stalled chain for 5 more minutes
        time.sleep(300)
        for i in A:
            n, h = head(SIDE[i])
            print(f"  +5 min node{i} head: {n} {h[:10]}")
    time.sleep(10)  # let every node import the latest blocks
    t = tip()
    diff = [n for n in range(1, t - 2)
            if len({(block(SIDE[i], n) or {}).get("hash") for i in A}) > 1]
    print(f"heights 1..{t - 3}: {len(diff)} heights differ between nodes {diff}")


if __name__ == "__main__":
    main()
