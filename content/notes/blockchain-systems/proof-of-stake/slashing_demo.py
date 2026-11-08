"""Run with Python 3.10+: python3 slashing_demo.py.

Compare attestation data only. No signatures, keys, network, or validator state.
The strings stand in for block roots; they are not Ethereum encodings.
"""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Checkpoint:
    epoch: int
    root: str


@dataclass(frozen=True)
class Vote:
    slot: int
    index: int
    head: str
    source: Checkpoint
    target: Checkpoint


def conflict(a: Vote, b: Vote) -> str:
    if a != b and a.target.epoch == b.target.epoch:
        return "double vote"
    if (a.source.epoch < b.source.epoch
            and b.target.epoch < a.target.epoch):
        return "surround vote"
    if (b.source.epoch < a.source.epoch
            and a.target.epoch < b.target.epoch):
        return "surround vote"
    return "none"


def vote(source: int, target: int, head: str = "head-A") -> Vote:
    return Vote(
        slot=target * 32,
        index=0,
        head=head,
        source=Checkpoint(source, f"block-{source}"),
        target=Checkpoint(target, f"block-{target}"),
    )


a = vote(2, 5)
cases = [
    ("same data", a, replace(a), "none"),
    ("changed head", a, replace(a, head="head-B"), "double vote"),
    ("surrounded", a, vote(3, 4), "surround vote"),
    ("reverse order", vote(3, 4), a, "surround vote"),
    ("equal source", a, vote(2, 4), "none"),
    ("crossing", a, vote(3, 6), "none"),
    ("next vote", a, vote(5, 6), "none"),
]
for label, left, right, expected in cases:
    result = conflict(left, right)
    assert result == expected, (label, result, expected)
    print(f"{label}: {result}")
