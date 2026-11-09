"""Check quorum intersection and an equivocating primary by exhaustive search."""

from itertools import combinations, product

VALUES = ("commit", "abort", None)  # None means the faulty node stays silent


def quorum_intersection(n, f):
    """Return the worst case of honest nodes shared by two quorums of size n - f."""
    q = n - f
    nodes = range(n)
    worst = None
    for q1, q2 in combinations(combinations(nodes, q), 2):
        shared = set(q1) & set(q2)
        for faulty in combinations(nodes, f):
            honest = shared - set(faulty)
            if worst is None or len(honest) < len(worst[0]):
                worst = (honest, q1, q2, faulty)
    return q, worst


def one_round(n, q, faulty, proposal="commit"):
    """Simplified pre-prepare + prepare round. Node 0 is the primary."""
    backups = range(1, n)
    others = lambda i: [j for j in range(n) if j != i]
    results = []
    # Faulty node: picks a value (or silence) for every receiver independently.
    for lie in product(VALUES, repeat=n - 1):
        lie = dict(zip(others(faulty), lie))
        if faulty == 0:
            pre_prepare = {i: lie[i] for i in backups}
        else:
            pre_prepare = {i: proposal for i in backups}
        votes = {i: {} for i in range(n)}  # votes[receiver][sender] = value
        for i in range(n):
            if i != faulty:
                own = proposal if i == 0 else pre_prepare[i]
                for j in range(n):
                    if own is not None:
                        votes[j][i] = own
            else:
                for j, value in lie.items():
                    if value is not None:
                        votes[j][i] = value
        prepared = {}
        for i in range(n):
            if i == faulty:
                continue
            for value in ("commit", "abort"):
                if sum(v == value for v in votes[i].values()) >= q:
                    prepared[i] = value
        results.append(prepared)
    split = [p for p in results if len(set(p.values())) > 1]
    stuck = [p for p in results if not p]
    return len(results), split, stuck


def main():
    print("== quorum intersection (quorum = n - f)")
    for n, f in [(3, 1), (4, 1), (5, 1), (6, 2), (7, 2)]:
        q, (honest, q1, q2, faulty) = quorum_intersection(n, f)
        verdict = "ok" if honest else f"counterexample Q1={q1} Q2={q2} faulty={faulty}"
        print(f"n={n} f={f} quorum={q} min honest in overlap={len(honest)} {verdict}")

    print("== one round, equivocating or silent node")
    for n, q in [(3, 2), (3, 3), (4, 3)]:
        for faulty, role in [(0, "primary"), (n - 1, "backup")]:
            total, split, stuck = one_round(n, q, faulty)
            example = f" e.g. {split[0]}" if split else ""
            print(f"n={n} quorum={q} faulty={role:7} cases={total:2} "
                  f"split={len(split):2} nobody_prepared={len(stuck):2}{example}")


if __name__ == "__main__":
    main()
