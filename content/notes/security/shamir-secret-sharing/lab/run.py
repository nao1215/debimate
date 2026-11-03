"""Educational GF(13) interpolation, not a production secret-sharing library."""
from itertools import combinations

P = 13
THRESHOLD = 3


def recover(shares):
    if len(shares) < THRESHOLD:
        raise ValueError("at least 3 shares required")
    xs = [x % P for x, _ in shares]
    if 0 in xs or len(set(xs)) != len(xs):
        raise ValueError("x must be nonzero and distinct modulo 13")
    secret = 0
    for i, (x, y) in enumerate(shares):
        weight = 1
        for j, (other_x, _) in enumerate(shares):
            if i != j:
                weight = weight * (-other_x) * pow((x - other_x) % P, -1, P) % P
        secret = (secret + y * weight) % P
    return secret


shares = [(x, (4 + 2*x + 3*x*x) % P) for x in range(1, 6)]
subsets = list(combinations(shares, THRESHOLD))
assert all(recover(group) == 4 for group in subsets)
print(f"all {len(subsets)} subsets of 3 shares: secret=4")
original = shares[:3]
modified = original[:2] + [(3, 12)]
print(f"original {original}: secret={recover(original)}")
print(f"modified {modified}: secret={recover(modified)} (no error)")
assert recover(modified) == 5
for invalid in (shares[:2], [(1, 9), (1, 7), (3, 11)]):
    try:
        recover(invalid)
    except ValueError as error:
        print(f"invalid input: {error}")
    else:
        raise AssertionError("invalid input accepted")
