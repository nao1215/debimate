#!/usr/bin/env python3
"""Local-only EIP-712 / ERC-2612 / ERC-1271 experiment. See README.txt.

Starts two fresh Anvil nodes on 127.0.0.1 (chain IDs 31337 and 31338) and uses
only Anvil's default test accounts. No public network, no real keys.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import urllib.request

from eip712 import digest, encode_type, hash_struct, type_hash
from keccak import keccak256

LAB = Path(__file__).resolve().parent
OUT = LAB / 'output'
OUT.mkdir(exist_ok=True)
OZ_SRC = Path(os.environ['OZ_SRC'])          # parent of the OpenZeppelin "oz" checkout
TOOLS = {n: os.environ.get(n.upper(), shutil.which(n)) for n in ('anvil', 'cast', 'solc')}
if not all(TOOLS.values()):
    raise SystemExit('Put anvil, cast and solc on PATH (or set ANVIL, CAST, SOLC).')
lines = []


def log(*parts):
    lines.append(' | '.join(str(p) for p in parts))


def cli(name, *args):
    return subprocess.check_output([TOOLS[name], *map(str, args)], text=True, cwd=LAB).strip()


# ---------------------------------------------------------------- 1. EIP-712 test vector
# The "Mail" example and expected values from EIP-712 (assets/eip-712/Example.js).
MAIL = {
    'types': {
        'EIP712Domain': [{'name': 'name', 'type': 'string'}, {'name': 'version', 'type': 'string'},
                         {'name': 'chainId', 'type': 'uint256'},
                         {'name': 'verifyingContract', 'type': 'address'}],
        'Person': [{'name': 'name', 'type': 'string'}, {'name': 'wallet', 'type': 'address'}],
        'Mail': [{'name': 'from', 'type': 'Person'}, {'name': 'to', 'type': 'Person'},
                 {'name': 'contents', 'type': 'string'}],
    },
    'primaryType': 'Mail',
    'domain': {'name': 'Ether Mail', 'version': '1', 'chainId': 1,
               'verifyingContract': '0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC'},
    'message': {'from': {'name': 'Cow', 'wallet': '0xCD2a3d9F938E13CD947Ec05AbC7FE734Df8DD826'},
                'to': {'name': 'Bob', 'wallet': '0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB'},
                'contents': 'Hello, Bob!'},
}
t = MAIL['types']
checks = [
    ('encodeType', encode_type('Mail', t),
     'Mail(Person from,Person to,string contents)Person(string name,address wallet)'),
    ('typeHash', '0x' + type_hash('Mail', t).hex(),
     '0xa0cedeb2dc280ba39b857546d74f5549c3a1d7bdc2dd96bf881f76108e23dac2'),
    ('domainSeparator', '0x' + hash_struct('EIP712Domain', MAIL['domain'], t).hex(),
     '0xf2cee375fa42b42143804025fc449deafd50cc031ca257e0b194a650a912090f'),
    ('hashStruct(message)', '0x' + hash_struct('Mail', MAIL['message'], t).hex(),
     '0xc52c0ee5d84264471806290a3f2c4cecfc5490626bf912d01f240d7a274b371e'),
    ('digest', '0x' + digest(MAIL).hex(),
     '0xbe609aee343fb3c4b28e1df9e632fca64fcfaede20f02e86244efddf30957bd2'),
]
lines.append('# 1. EIP-712 Mail example, hashed by hand')
for label, got, want in checks:
    assert got == want, (label, got, want)
    log(label, got, 'matches EIP-712')
MAIL_SIG = ('0x4355c47d63924e8a72e509b65029052eb6c299d53a04e167c5775fd466751c9d'
            '07299936d304c153f6443dfa05f40ff007d72911b6f72307f996231605b915621c')

# ---------------------------------------------------------------- compile
oz = OZ_SRC / 'oz'
compiled = json.loads(cli('solc', '--evm-version', 'cancun', '--base-path', '.', '--include-path', OZ_SRC,
                          '@openzeppelin/contracts/=oz/contracts/', '--combined-json', 'abi,bin',
                          'StudyPermitToken.sol', 'StudyAccount.sol', 'SigCheck.sol'))['contracts']
BIN = {k.split(':')[1]: v['bin'] for k, v in compiled.items() if k.split(':')[0] in
       ('StudyPermitToken.sol', 'StudyAccount.sol', 'SigCheck.sol')}


# ---------------------------------------------------------------- node helpers
class Node:
    def __init__(self, chain_id):
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            self.port = s.getsockname()[1]
        self.url = f'http://127.0.0.1:{self.port}'
        self.log = (OUT / f'node-{chain_id}.log').open('w')
        self.proc = subprocess.Popen(
            [TOOLS['anvil'], '--host', '127.0.0.1', '--port', str(self.port), '--chain-id', str(chain_id),
             '--hardfork', 'cancun', '--timestamp', '1700000000', '--accounts', '4', '--quiet'],
            stdout=self.log, stderr=self.log)
        for _ in range(200):
            try:
                self.accounts = self.rpc('eth_accounts')
                return
            except OSError:
                time.sleep(0.05)
        raise TimeoutError('anvil')

    def rpc(self, method, *params):
        req = urllib.request.Request(self.url, json.dumps(
            {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode(),
            {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as r:
            res = json.load(r)
        if 'error' in res:
            raise RuntimeError(res['error'])
        return res['result']

    def send(self, sender, data, to=None):
        tx = {'from': sender, 'data': data, 'gas': hex(3_000_000), 'gasPrice': hex(2_000_000_000)}
        if to:
            tx['to'] = to
        h = self.rpc('eth_sendTransaction', tx)
        for _ in range(200):
            rcpt = self.rpc('eth_getTransactionReceipt', h)
            if rcpt:
                return rcpt
            time.sleep(0.05)
        raise TimeoutError(h)

    def deploy(self, sender, name, *ctor):
        args = cli('cast', 'abi-encode', 'f(address)', *ctor)[2:] if ctor else ''
        rcpt = self.send(sender, '0x' + BIN[name] + args)
        assert int(rcpt['status'], 16) == 1
        return cli('cast', 'to-check-sum-address', rcpt['contractAddress'])

    def call(self, to, sig, *args, returns='uint256'):
        """eth_call; returns the decoded value, or 'revert <ErrorName>(...)'."""
        data = cli('cast', 'calldata', sig, *args)
        try:
            raw = self.rpc('eth_call', {'to': to, 'data': data}, 'latest')
        except RuntimeError as e:
            signer, expected = cli('cast', 'decode-error', e.args[0]['data'], '--sig', REVERTS).split()
            return f'revert ERC2612InvalidSigner(recovered={signer}, owner={expected})'
        return cli('cast', 'abi-decode', f'f()({returns})', raw)

    def stop(self):
        self.proc.terminate()
        self.proc.wait()
        self.log.close()


REVERTS = 'ERC2612InvalidSigner(address,address)'
a, b = Node(31337), Node(31338)
try:
    deployer, owner, spender, acct_owner = [cli('cast', 'to-check-sum-address', x) for x in a.accounts[:4]]
    # ------------------------------------------------------------ 2. same signature, other domains
    token = a.deploy(deployer, 'StudyPermitToken', owner)
    token_b = b.deploy(deployer, 'StudyPermitToken', owner)      # same deployer + nonce -> same address
    token_2 = a.deploy(deployer, 'StudyPermitToken', owner)      # same name, another address
    checker = a.deploy(deployer, 'SigCheck')
    assert token == token_b != token_2
    log('ecrecover(digest, signature in EIP-712)', a.call(checker, 'recover(bytes32,bytes)',
                                                    '0x' + digest(MAIL).hex(), MAIL_SIG, returns='address'))
    lines.append('')
    lines.append('# 2. permit signature from eth_signTypedData_v4')
    log('token on 31337', token)
    log('token on 31338', token_b)
    log('2nd token on 31337', token_2)

    deadline = 1700000000 + 3600
    def permit_typed(chain_id, contract, owner_addr, nonce=0):
        return {
            'types': {
                'EIP712Domain': MAIL['types']['EIP712Domain'],
                'Permit': [{'name': 'owner', 'type': 'address'}, {'name': 'spender', 'type': 'address'},
                           {'name': 'value', 'type': 'uint256'}, {'name': 'nonce', 'type': 'uint256'},
                           {'name': 'deadline', 'type': 'uint256'}],
            },
            'primaryType': 'Permit',
            'domain': {'name': 'Study Token', 'version': '1', 'chainId': chain_id,
                       'verifyingContract': contract},
            'message': {'owner': owner_addr, 'spender': spender, 'value': 100,
                        'nonce': nonce, 'deadline': deadline},
        }

    typed = permit_typed(31337, token, owner)
    sig = a.rpc('eth_signTypedData_v4', owner, typed)            # Anvil signs with the test key
    d = '0x' + digest(typed).hex()
    sep = '0x' + hash_struct('EIP712Domain', typed['domain'], typed['types']).hex()
    v, r, s = int(sig[130:132], 16), '0x' + sig[2:66], '0x' + sig[66:130]
    log('DOMAIN_SEPARATOR() == Python', a.call(token, 'DOMAIN_SEPARATOR()', returns='bytes32') == sep)
    log('owner', owner)
    log('ecrecover(Python digest, wallet signature)',
        a.call(checker, 'recover(bytes32,bytes)', d, sig, returns='address'))
    permit_args = (owner, spender, 100, deadline, v, r, s)
    psig = 'permit(address,address,uint256,uint256,uint8,bytes32,bytes32)'
    log('same signature, token on 31338', b.call(token_b, psig, *permit_args))
    log('same signature, 2nd token on 31337', a.call(token_2, psig, *permit_args))

    # ------------------------------------------------------------ 3. personal_sign of the digest
    lines.append('')
    lines.append('# 3. personal_sign over the same 32-byte digest')
    psig191 = a.rpc('personal_sign', d, owner)
    assert a.rpc('eth_sign', owner, d) == psig191              # Anvil's eth_sign also adds the prefix
    prefixed = '0x' + keccak256(b'\x19Ethereum Signed Message:\n32' + bytes.fromhex(d[2:])).hex()
    log('ecrecover(digest, personal_sign)', a.call(checker, 'recover(bytes32,bytes)', d, psig191, returns='address'))
    log('ecrecover(EIP-191 hash, personal_sign)',
        a.call(checker, 'recover(bytes32,bytes)', prefixed, psig191, returns='address'))

    # ------------------------------------------------------------ 4. permit + transferFrom by a third party
    lines.append('')
    lines.append('# 4. owner only signs; spender submits permit and transferFrom')
    def state(label):
        log(label,
            'owner txs', int(a.rpc('eth_getTransactionCount', owner, 'latest'), 16),
            'owner STK', a.call(token, 'balanceOf(address)', owner),
            'spender STK', a.call(token, 'balanceOf(address)', spender),
            'allowance', a.call(token, 'allowance(address,address)', owner, spender))
    state('after signing')
    rc = a.send(spender, cli('cast', 'calldata', psig, *permit_args), token)
    state(f'permit status={int(rc["status"], 16)}')
    rc = a.send(spender, cli('cast', 'calldata', 'transferFrom(address,address,uint256)',
                             owner, spender, 100), token)
    state(f'transferFrom status={int(rc["status"], 16)}')
    log('same permit again (nonce is now 1)', a.call(token, psig, *permit_args))

    # ------------------------------------------------------------ 5. ERC-1271 account
    lines.append('')
    lines.append('# 5. contract account (ERC-1271)')
    acct = a.deploy(deployer, 'StudyAccount', acct_owner)
    acct_2 = a.deploy(deployer, 'StudyAccount', acct_owner)
    acct, acct_2 = [cli('cast', 'to-check-sum-address', x) for x in (acct, acct_2)]
    typed_c = permit_typed(31337, token, acct)
    d_c = '0x' + digest(typed_c).hex()
    sig_c = a.rpc('eth_signTypedData_v4', acct_owner, typed_c)  # the account's owner EOA signs
    bad = sig_c[:-4] + ('1b' if sig_c[-2:] == '1c' else '1c')    # flip v -> another signer
    log('account', acct, 'code bytes', (len(a.rpc('eth_getCode', acct, 'latest')) - 2) // 2)
    log('account owner EOA', acct_owner)
    log('ecrecover(digest, sig)', a.call(checker, 'recover(bytes32,bytes)', d_c, sig_c, returns='address'))
    log('checkEcrecover(account, ...)', a.call(checker, 'checkEcrecover(address,bytes32,bytes)',
                                               acct, d_c, sig_c, returns='bool'))
    log('checkWith1271(account, ...)', a.call(checker, 'checkWith1271(address,bytes32,bytes)',
                                              acct, d_c, sig_c, returns='bool'))
    log('account.isValidSignature(digest, sig)',
        a.call(acct, 'isValidSignature(bytes32,bytes)', d_c, sig_c, returns='bytes4'))
    log('account.isValidSignature(digest, bad sig)',
        a.call(acct, 'isValidSignature(bytes32,bytes)', d_c, bad, returns='bytes4'))
    vc, rc_, sc = int(sig_c[130:132], 16), '0x' + sig_c[2:66], '0x' + sig_c[66:130]
    log('token.permit(owner=account, ...)', a.call(token, psig, acct, spender, 100, deadline, vc, rc_, sc))
    log('another account of the same owner .isValidSignature',
        a.call(acct_2, 'isValidSignature(bytes32,bytes)', d_c, sig_c, returns='bytes4'))
finally:
    a.stop()
    b.stop()

versions = '\n'.join(cli(n, '--version').splitlines()[0 if n != 'solc' else -1] for n in TOOLS)
(OUT / 'versions.txt').write_text(versions + f'\nOpenZeppelin Contracts {os.environ.get("OZ_COMMIT", "?")}\n')
(OUT / 'summary.txt').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
