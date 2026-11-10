"""Raft leader election after a leader crash: split votes vs. timeout spread.

A simulation in the shape of Figure 16 of the Raft paper
(https://raft.github.io/raft.pdf), not a reproduction of its numbers.

Assumptions:
- 5 servers; the leader sends a heartbeat at t = 0 and crashes right after.
  Each of the 4 followers starts its election timer when that heartbeat
  arrives (one message delay later). A candidate needs 3 votes.
- Each election timeout is drawn uniformly from [150, 150 + spread] ms and is
  redrawn whenever a timer restarts.
- Every message takes a one-way delay drawn uniformly from [2, 8] ms
  (an assumed LAN latency), never lost. Logs are equal, so the log check in
  RequestVote never refuses a vote.
- A server grants its vote if the request's term is newer than its own, or
  equal and it has not voted yet; granting a vote restarts its timer
  (Raft paper, Figure 2). A server that sees a newer term steps down.
- The election ends when some candidate collects 3 votes. A trial with no
  leader after 10 s is counted as stuck and left out of the time columns.

Run: python3 election.py > election_output.txt
"""

import heapq
import random

SERVERS = 4  # survivors of a 5-server cluster
MAJORITY = 3
BASE = 150.0
SPREADS = [0, 1, 5, 25, 50, 150]
TRIALS = 10_000
DELAY = (2.0, 8.0)
GIVE_UP = 10_000.0  # ms; a trial without a leader by then counts as stuck


def elect(spread, rng):
    """Return (time to elect a leader in ms, number of terms used) or None."""
    term = [1] * SERVERS
    voted = [None] * SERVERS
    votes = [0] * SERVERS
    timer_id = [0] * SERVERS  # bumping it cancels the pending timeout
    events = []  # (time, seq, kind, ...)
    seq = 0

    def push(t, *ev):
        nonlocal seq
        seq += 1
        heapq.heappush(events, (t, seq) + ev)

    def reset_timer(i, now):
        timer_id[i] += 1
        push(now + BASE + rng.uniform(0, spread), "timeout", i, timer_id[i])

    for i in range(SERVERS):
        reset_timer(i, rng.uniform(*DELAY))  # the last heartbeat arrives
    first_term = 1
    while events:
        now, _, kind, *rest = heapq.heappop(events)
        if now > GIVE_UP:
            return None
        if kind == "timeout":
            i, tid = rest
            if tid != timer_id[i]:
                continue
            term[i] += 1  # become candidate, vote for itself
            voted[i], votes[i] = i, 1
            reset_timer(i, now)
            for j in range(SERVERS):
                if j != i:
                    push(now + rng.uniform(*DELAY), "request", j, i, term[i])
        elif kind == "request":
            j, cand, t = rest
            if t > term[j]:
                term[j], voted[j], votes[j] = t, None, 0
            grant = t == term[j] and voted[j] in (None, cand)
            if grant:
                voted[j] = cand
                reset_timer(j, now)
            push(now + rng.uniform(*DELAY), "reply", cand, t, grant)
        elif kind == "reply":
            cand, t, grant = rest
            if grant and t == term[cand] and voted[cand] == cand:
                votes[cand] += 1
                if votes[cand] == MAJORITY:
                    return now, t - first_term
    raise RuntimeError("no leader")


def percentile(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def run(spread, seed=1):
    rng = random.Random(seed)
    return [elect(spread, rng) for _ in range(TRIALS)]


def main():
    print(f"5 servers, leader crashed at t=0, {TRIALS} trials per spread, "
          f"message delay U{DELAY} ms")
    print("timeout_ms   split_vote  median_ms  p99_ms  max_ms  max_terms  stuck")
    for spread in SPREADS:
        res = run(spread)
        done = [r for r in res if r is not None]
        times = [t for t, _ in done]
        terms = [n for _, n in done]
        split = 1 - sum(n == 1 for n in terms) / len(res)
        stuck = len(res) - len(done)
        print(f"{BASE:g}-{BASE + spread:<6g} {split:>10.1%} {percentile(times, 0.5):>10.0f}"
              f" {percentile(times, 0.99):>7.0f} {max(times):>7.0f} {max(terms):>10d}"
              f" {stuck:>6d}")


if __name__ == "__main__":
    main()
