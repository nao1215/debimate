"""Stop QBFT validators one by one and record what the chain does.

Run after `./net.sh up`. Prints one summary per phase and a fork check.
Usage: python3 scenario.py [--vote]
"""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rpc import block, call, head, qbft_extra  # noqa: E402

HERE = Path(__file__).resolve().parent
IP = {i: f"10.231.12.1{i}" for i in range(1, 6)}
NAME = {(open(HERE.parent / f"keys/node{i}/address").read().strip()): f"node{i}"
        for i in range(1, 6)}


def net(*args):
    subprocess.run([str(HERE / "net.sh"), *map(str, args)], check=True)


def alive_head():
    for i in (1, 2, 3, 4):
        h = head(IP[i])
        if h:
            return i, h[0]
    raise RuntimeError("no node answers")


PHASES = [  # (label, action before the phase, seconds after the first new block)
    ("4/4 running", None, 30),
    ("node4 stopped (3/4)", ("stop", 4), 40),
    ("node3 stopped too (2/4)", ("stop", 3), 40),
    ("node3 restarted (3/4)", ("start", 3), 20),
    ("node4 restarted (4/4)", ("start", 4), 20),
]
WAIT_MAX = 600  # give up waiting for the first new block after this


def main():
    marks = []
    for label, action, secs in PHASES:
        if action:
            net(*action)
        _, start = alive_head()
        t0 = time.time()
        first_new = None
        halted = action and action[0] == "stop" and action[1] == 3
        while True:
            el = time.time() - t0
            _, n = alive_head()
            if first_new is None and n > start:
                first_new = el
            if halted and el >= secs:
                break  # the 2/4 phase is expected to stay silent
            if first_new is not None and el >= first_new + secs:
                break
            if el >= WAIT_MAX:
                break
            time.sleep(0.5)
        _, end = alive_head()
        marks.append((label, start, end, first_new))

    src, tip = alive_head()
    print(f"{'phase':26} {'blocks':>6} {'first new':>9}  proposers / max round / seals")
    for label, start, end, first_new in marks:
        props, rounds, seals = [], 0, set()  # rounds: highest round seen
        for n in range(start + 1, end + 1):
            b = block(IP[src], n)
            x = qbft_extra(b["extraData"])
            props.append(NAME[b["miner"]][-1])
            rounds = max(rounds, x["round"])
            seals.add(x["seals"])
        fn = f"{first_new:.1f}s" if first_new is not None else "-"
        print(f"{label:26} {end - start:6} {fn:>9}  {''.join(props[:16])}"
              f"{'...' if len(props) > 16 else ''} / {rounds} / {sorted(seals)}")

    time.sleep(6)  # let restarted nodes catch up before comparing
    diff = sum(len({(block(IP[i], n) or {}).get("hash") for i in (1, 2, 3, 4)}) > 1
               for n in range(1, tip + 1))
    print(f"heights 1..{tip}: {diff} heights differ between nodes")

    if "--vote" in sys.argv:
        vote()


def vote():
    """Add node5 as a validator by votes from node1..node3."""
    net("add5")
    time.sleep(20)
    for i in (1, 2, 3):
        call(IP[i], "qbft_proposeValidatorVote", [
            open(HERE.parent / "keys/node5/address").read().strip(), True])
        _, n = alive_head()
        print(f"node{i} voted to add node5 at height {n}: validators =",
              len(call(IP[1], "qbft_getValidatorsByBlockNumber", ["latest"])))
        time.sleep(4)
    time.sleep(10)
    _, n = alive_head()
    print(f"height {n}: validators =",
          len(call(IP[1], "qbft_getValidatorsByBlockNumber", ["latest"])))


if __name__ == "__main__":
    main()
