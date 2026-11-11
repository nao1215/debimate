"""How many (key, nonce) pairs get reused when a sender with one key restarts,
for counter nonces saved in different ways and for random nonces
(simulation for the counters, formula for the random nonces).

Model:
- One sender, one key, MESSAGES messages in total.
- The process crashes after a random number of messages; the gap between
  crashes is geometric with mean MEAN_GAP messages (seeded RNG).
- "save after use, every m": after the m-th, 2m-th, ... message the sender
  writes the next counter value to non-volatile memory. A crash right after
  a send loses everything since the last write, so on restart the counter
  resumes from the saved value and re-issues the numbers in between.
- "reserve ahead, block m": before using a block of m numbers the sender
  writes the end of the block; on restart it resumes from that value.
- random nonces of b bits: expected number of colliding pairs
  M(M-1)/2 / 2^b, independent of crashes.

Run: python3 lab/counter_restart.py
"""

import random

MESSAGES = 10_000_000
MEAN_GAP = 10_000  # messages between crashes on average
MS = [10, 1_000]
CHECKPOINTS = [10**4, 10**5, 10**6, 10**7]
SEED = 20261110


def crash_points(rng):
    """Message counts (cumulative) at which the process crashes."""
    points, total = [], 0
    while True:
        total += max(1, int(rng.expovariate(1 / MEAN_GAP)))
        if total >= MESSAGES:
            return points
        points.append(total)


def simulate(m, reserve, crashes, checkpoints=CHECKPOINTS):
    """Cumulative number of reused nonces at each checkpoint."""
    counter = 0      # next nonce to use
    saved = 0        # value in non-volatile memory
    max_used = -1    # highest nonce ever used
    reused = 0
    sent = 0
    out = {}
    events = crashes + [MESSAGES]
    cps = iter(checkpoints)
    cp = next(cps)
    for stop in events:
        while sent < stop:
            if reserve and counter >= saved:
                saved = counter + m                  # write before use
            if counter <= max_used:
                reused += 1
            max_used = max(max_used, counter)
            counter += 1
            sent += 1
            if not reserve and counter % m == 0:
                saved = counter                      # write after use
            if sent == cp:
                out[cp] = reused
                cp = next(cps, None)
        counter = saved                              # crash and restart
    return out


def main():
    rng = random.Random(SEED)
    crashes = crash_points(rng)
    print(f"messages={MESSAGES:,}  crashes={len(crashes):,}  "
          f"mean gap={MEAN_GAP:,}  seed={SEED}")
    print(f"{'messages sent':<28}" + "".join(f"{c:>12,}" for c in CHECKPOINTS))
    for m in MS:
        for reserve in (False, True):
            name = f"{'reserve ahead' if reserve else 'save after use'}, m={m:,}"
            res = simulate(m, reserve, crashes)
            print(f"{name:<28}" + "".join(f"{res[c]:>12,}" for c in CHECKPOINTS))
    for bits in (96, 192):
        cells = "".join(f"{m * (m - 1) / 2 / 2**bits:>12.1e}" for m in CHECKPOINTS)
        print(f"{f'random {bits}-bit (expected)':<28}{cells}")


if __name__ == "__main__":
    main()
