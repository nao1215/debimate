"""Demonstrate Merkle construction ambiguity using SHA-256.
Bitcoin-style duplication ONLY: not Bitcoin txid/byte-order/double-SHA rules.
ct_root implements RFC 9162 section 2.1's hash construction on sample bytes;
this is not a complete Certificate Transparency protocol implementation.
"""
from hashlib import sha256
from pathlib import Path


def h(value):
    return sha256(value).digest()


def duplicate_root(values):
    nodes = [h(value) for value in values]
    assert nodes
    while len(nodes) > 1:
        if len(nodes) % 2:
            nodes.append(nodes[-1])
        nodes = [h(nodes[i] + nodes[i + 1]) for i in range(0, len(nodes), 2)]
    return nodes[0]


def ct_root(values):
    if not values:
        return h(b'')
    if len(values) == 1:
        return h(b'\x00' + values[0])
    split = 1 << ((len(values) - 1).bit_length() - 1)
    return h(b'\x01' + ct_root(values[:split]) + ct_root(values[split:]))


abc = [b'A', b'B', b'C']
abcc = abc + [b'C']
assert duplicate_root(abc) == duplicate_root(abcc)
assert ct_root(abc) != ct_root(abcc)
# The very same 64-byte input can be interpreted as a leaf or two child hashes.
children = h(b'A') + h(b'B')
assert len(children) == 64
assert duplicate_root([b'A', b'B']) == duplicate_root([children])
assert ct_root([b'A', b'B']) != ct_root([children])
lines = [
    'duplicate-last: root(A,B,C) == root(A,B,C,C): True',
    f'duplicate root: {duplicate_root(abc).hex()}',
    'RFC9162: root(A,B,C) == root(A,B,C,C): False',
    f'RFC9162 root(A,B,C):   {ct_root(abc).hex()}',
    f'RFC9162 root(A,B,C,C): {ct_root(abcc).hex()}',
    'no prefix: root(A,B) == root(single 64-byte leaf): True',
    'RFC9162: root(A,B) == root(single 64-byte leaf): False',
    'Assertions: PASS',
]
output = '\n'.join(lines) + '\n'
Path(__file__).with_name('output.txt').write_text(output)
print(output, end='')
