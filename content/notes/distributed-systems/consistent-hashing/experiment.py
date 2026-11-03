"""Compare primary-owner mappings, not network transfers or server performance.
Run: python3 experiment.py (Python 3, standard library only).
"""
from bisect import bisect_left
from collections import Counter
from hashlib import sha256


def hash_value(value):
    return int.from_bytes(sha256(value.encode('utf-8')).digest(), 'big')


def make_ring(nodes, vnodes):
    entries = sorted((hash_value(f'node:{node}:{v}'), node)
                     for node in nodes for v in range(vnodes))
    points = [point for point, _ in entries]
    assert len(points) == len(set(points)), 'Token collision'
    return points, [node for _, node in entries]


def owner(ring, key_hash):
    points, nodes = ring
    return nodes[bisect_left(points, key_hash) % len(points)]


def main():
    keys = [hash_value(f'key:{i}') for i in range(100_000)]
    old_nodes = ['A', 'B', 'C']
    new_nodes = old_nodes + ['D']
    # Explicit boundary checks for the clockwise successor rule.
    tiny = ([20, 60, 90], ['A', 'B', 'C'])
    assert [owner(tiny, h) for h in [0, 20, 21, 60, 90, 99]] == [
        'A', 'A', 'B', 'B', 'C', 'A']
    print('keys=100000, nodes=3->4, primary owner only')
    for vnodes in [0, 1, 128]:
        label = 'modulo' if vnodes == 0 else f'ring-v{vnodes}'
        if vnodes == 0:
            before = [old_nodes[h % 3] for h in keys]
            after = [new_nodes[h % 4] for h in keys]
        else:
            old_ring = make_ring(old_nodes, vnodes)
            new_ring = make_ring(new_nodes, vnodes)
            before = [owner(old_ring, h) for h in keys]
            after = [owner(new_ring, h) for h in keys]
            assert all(a == b or b == 'D' for a, b in zip(before, after))
            removed_ring = make_ring(['A', 'C'], vnodes)
            assert all(a == 'B' or owner(removed_ring, h) == a
                       for h, a in zip(keys, before))
        changed = sum(a != b for a, b in zip(before, after))
        counts = Counter(after)
        print(f'{label}: changed={changed} ({changed / len(keys):.2%}), '
              + ' '.join(f'{n}={counts[n]}' for n in new_nodes))


if __name__ == '__main__':
    main()
