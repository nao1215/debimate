"""ECDSA/secp256k1 message experiment, not Bitcoin transaction signing.
Requires cryptography==46.0.5. Keys are ephemeral and never saved or printed.
"""
from pathlib import Path
import cryptography
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

alice = ec.generate_private_key(ec.SECP256K1())
bob = ec.generate_private_key(ec.SECP256K1())
message = b'pay Bob 10'
signature = alice.sign(message, ec.ECDSA(hashes.SHA256()))


def valid(public_key, data):
    try:
        public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False


cases = [
    ('original', alice.public_key(), message, True),
    ('amount changed: 10 -> 90', alice.public_key(), b'pay Bob 90', False),
    ('different public key', bob.public_key(), message, False),
    ('same message replayed', alice.public_key(), message, True),
]
lines = []
for label, public_key, data, expected in cases:
    result = valid(public_key, data)
    assert result == expected
    lines.append(f'{label}: {"VALID" if result else "INVALID"}')
lines.append('Assertions: PASS')
output = '\n'.join(lines) + '\n'
Path(__file__).with_name('output.txt').write_text(output)
Path(__file__).with_name('versions.txt').write_text(f'cryptography {cryptography.__version__}\n')
print(output, end='')
