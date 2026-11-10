"""Simulate Slush, Snowflake and Snowball on two conflicting values (red=0, blue=1).

Model (a simplification, not avalanchego itself):
- Synchronous rounds. Every undecided correct node sends one query per round.
- A query picks k other nodes at random with replacement, and every one answers.
- Correct nodes answer with their current preference (or the decided value).
- Byzantine nodes are the first nb node IDs and use one of these strategies:
    "push"    always answer red, the value correct nodes do not start with
    "split"   answer each querier with the color its half started with,
              trying to make the two halves decide different values
    "balance" (Slush only) answer with the color fewer correct nodes hold
- One query costs 2k messages (k requests + k responses).
- A run stops when every correct node decides, when nobody decided for
  STALL rounds in a row, or at MAX_ROUNDS.
"""

from concurrent.futures import ProcessPoolExecutor
from functools import partial

import numpy as np

RED, BLUE, UNDECIDED = 0, 1, -1
MAX_ROUNDS, STALL = 5000, 1000


def sample(rng, n, queriers, k):
    """k peers for each querier, chosen with replacement, never the querier."""
    peers = rng.integers(0, n - 1, size=(len(queriers), k))
    return peers + (peers >= queriers[:, None])


def slush(n, k, alpha, rounds, byz=0.0, seed=1):
    """Return the share of correct nodes preferring blue after every round."""
    rng = np.random.default_rng(seed)
    nb = int(n * byz)
    correct = np.arange(nb, n)
    color = np.zeros(n, dtype=np.int8)
    color[nb + (n - nb) // 2:] = BLUE  # correct nodes start 50/50
    trace = [color[correct].mean()]
    for _ in range(rounds):
        peers = sample(rng, n, correct, k)
        answers = color[peers]
        if nb:  # "balance": Byzantine nodes back the minority color
            minority = BLUE if color[correct].mean() < 0.5 else RED
            answers[peers < nb] = minority
        blue = answers.sum(axis=1)
        color[correct[blue >= alpha]] = BLUE
        color[correct[k - blue >= alpha]] = RED
        trace.append(color[correct].mean())
    return trace


def snow(n, byz, k, alpha, beta, start="agree", protocol="snowball", seed=1):
    """Run Snowflake or Snowball once.

    start="agree": every correct node prefers blue, Byzantine nodes push red.
    start="split": correct nodes are 50/50, Byzantine nodes play "split".
    """
    rng = np.random.default_rng(seed)
    nb = int(n * byz)
    group = np.full(n, BLUE, dtype=np.int8)  # the color each correct node starts with
    if start == "split":
        group[nb:nb + (n - nb) // 2] = RED
    last = group.copy()  # Snowflake preference (last successful color)
    ball = group.copy()  # Snowball preference (more successful polls)
    strength = np.zeros((n, 2), dtype=np.int32)
    conf = np.zeros(n, dtype=np.int32)  # consecutive successful polls
    decided = np.full(n, UNDECIDED, dtype=np.int8)
    queries = np.zeros(n, dtype=np.int64)

    rounds = idle = 0
    while rounds < MAX_ROUNDS and idle < STALL:
        active = np.flatnonzero(decided[nb:] == UNDECIDED) + nb
        if active.size == 0:
            break
        rounds += 1
        public = ball if protocol == "snowball" else last
        answer_of = np.where(decided == UNDECIDED, public, decided)
        peers = sample(rng, n, active, k)
        answers = answer_of[peers]
        lie = peers < nb
        if start == "split":
            answers[lie] = np.broadcast_to(group[active][:, None], answers.shape)[lie]
        else:
            answers[lie] = RED
        blue = answers.sum(axis=1)
        ok = (blue >= alpha) | (k - blue >= alpha)
        choice = np.where(blue >= alpha, BLUE, RED)[ok]
        queries[active] += 1

        win = active[ok]
        # Snowball: count successful polls per color, prefer the larger count.
        strength[win, choice] += 1
        more = strength[win, choice] > strength[win, 1 - choice]
        ball[win[more]] = choice[more]
        # Snowflake: count consecutive successes for the same color.
        conf[win[last[win] != choice]] = 0
        last[win] = choice
        conf[win] += 1
        conf[active[~ok]] = 0
        done = win[conf[win] >= beta]
        decided[done] = last[done]
        idle = 0 if done.size else idle + 1

    final = decided[nb:]
    return {
        "rounds": rounds,
        "split": bool((final == RED).any() and (final == BLUE).any()),
        "red": bool((final == RED).any()),
        "undecided": int((final == UNDECIDED).sum()),
        "msgs_per_node": 2 * k * queries[nb:].mean(),
    }


def pbft_messages(n):
    """Messages for one request in PBFT normal case: pre-prepare, prepare, commit."""
    return (n - 1) + (n - 1) * (n - 1) + n * (n - 1)


def sweep(n, byz, k, alpha, beta, start="agree", protocol="snowball", trials=100):
    run = partial(snow, n, byz, k, alpha, beta, start, protocol)
    with ProcessPoolExecutor(max_workers=8) as pool:  # one seed per run
        runs = list(pool.map(run, range(trials)))
    finished = sorted(r["rounds"] for r in runs if r["undecided"] == 0)
    return {
        "median_rounds": finished[len(finished) // 2] if finished else None,
        "splits": sum(r["split"] for r in runs),
        "red": sum(r["red"] for r in runs),
        "unfinished": sum(r["undecided"] > 0 for r in runs),
        "msgs_per_node": float(np.median([r["msgs_per_node"] for r in runs])),
        "trials": trials,
    }


def row(label, r):
    rounds = "-" if r["median_rounds"] is None else r["median_rounds"]
    return (f"{label} {rounds:>6} {r['splits']:>6} {r['unfinished']:>10} "
            f"{r['msgs_per_node']:>9.0f}")


def main():
    head = "rounds splits unfinished msgs/node"
    print("== 1. agree start, Byzantine push red (n=500, k=20, alpha=15, beta=20, 100 seeds)")
    print(f"byz  red  {head}")
    for byz in (0.0, 0.1, 0.2, 0.25, 0.3):
        r = sweep(500, byz, 20, 15, 20, "agree")
        print(row(f"{byz:4.2f} {r['red']:4}", r))

    print("== 2. split start (n=500, k=20, alpha=15, snowball, 100 seeds)")
    print(f"byz  beta {head}")
    for byz in (0.0, 0.05, 0.1, 0.2):
        for beta in (1, 2, 4, 8, 20):
            print(row(f"{byz:4.2f} {beta:4}", sweep(500, byz, 20, 15, beta, "split")))

    print("== 3. snowflake vs snowball, split start (n=500, byz=0.05, alpha=15, 100 seeds)")
    print(f"protocol  beta {head}")
    for protocol in ("snowflake", "snowball"):
        for beta in (2, 4, 8):
            r = sweep(500, 0.05, 20, 15, beta, "split", protocol)
            print(row(f"{protocol:9} {beta:4}", r))

    print("== 4. alpha (n=500, k=20, beta=4 for split / beta=20 for agree, 100 seeds)")
    print("alpha  split_byz0.05:splits  agree_byz0.3:unfinished  agree_byz0.3:rounds")
    for alpha in (11, 13, 15, 17):
        s = sweep(500, 0.05, 20, alpha, 4, "split")
        a = sweep(500, 0.3, 20, alpha, 20, "agree")
        rounds = "-" if a["median_rounds"] is None else a["median_rounds"]
        print(f"{alpha:5} {s['splits']:21} {a['unfinished']:24} {rounds:>20}")

    print("== 5. total messages for one decision (agree start, byz=0, k=20, alpha=15, beta=20)")
    print("    n  snowball_total  per_node  rounds  pbft_total")
    for n in (50, 100, 200, 500, 1000, 2000, 5000):
        r = sweep(n, 0.0, 20, 15, 20, "agree", trials=20)
        print(f"{n:5} {r['msgs_per_node'] * n:15.0f} {r['msgs_per_node']:9.0f} "
              f"{r['median_rounds']:7} {pbft_messages(n):11}")

    print("== 6. same, split start (byz=0)")
    print("    n  snowball_total  per_node  rounds")
    for n in (50, 100, 200, 500, 1000, 2000, 5000):
        r = sweep(n, 0.0, 20, 15, 20, "split", trials=20)
        print(f"{n:5} {r['msgs_per_node'] * n:15.0f} {r['msgs_per_node']:9.0f} "
              f"{r['median_rounds']:7}")


if __name__ == "__main__":
    main()
