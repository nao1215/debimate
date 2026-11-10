"""EIP-712 hashing written by hand (structs, atomic types, string and bytes; no arrays)."""
from keccak import keccak256


def encode_type(primary, types):
    deps = set()

    def collect(name):
        for field in types[name]:
            t = field['type']
            if t in types and t not in deps:
                deps.add(t)
                collect(t)

    collect(primary)
    deps.discard(primary)
    def one(name):
        return name + '(' + ','.join(f"{f['type']} {f['name']}" for f in types[name]) + ')'
    return one(primary) + ''.join(one(d) for d in sorted(deps))


def type_hash(primary, types):
    return keccak256(encode_type(primary, types).encode())


def encode_value(t, value, types):
    if t in types:                      # nested struct -> its hashStruct
        return hash_struct(t, value, types)
    if t == 'string':                   # dynamic -> keccak256 of the contents
        return keccak256(value.encode())
    if t == 'bytes':
        return keccak256(bytes.fromhex(value.removeprefix('0x')))
    if t == 'address':
        return int(value, 16).to_bytes(32, 'big')
    if t == 'bool':
        return int(bool(value)).to_bytes(32, 'big')
    if t.startswith('uint'):
        return int(value).to_bytes(32, 'big')
    if t.startswith('int'):
        return (int(value) % 2**256).to_bytes(32, 'big')
    if t.startswith('bytes'):           # bytes1..bytes32, right padded
        return bytes.fromhex(value.removeprefix('0x')).ljust(32, b'\0')
    raise NotImplementedError(t)


def encode_data(primary, data, types):
    return b''.join(encode_value(f['type'], data[f['name']], types) for f in types[primary])


def hash_struct(primary, data, types):
    return keccak256(type_hash(primary, types) + encode_data(primary, data, types))


def digest(typed):
    types = typed['types']
    domain_separator = hash_struct('EIP712Domain', typed['domain'], types)
    return keccak256(b'\x19\x01' + domain_separator
                     + hash_struct(typed['primaryType'], typed['message'], types))
