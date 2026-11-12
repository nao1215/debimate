---
title: "Safe - コントラクトで署名を数えるマルチシグ"
date: 2026-11-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain", "ethereum", "multisig", "safe", "smart-contract", "security"]
weight: 20
wrapTables: true
topics: ["Transaction / Wallet"]
---

[Safe](https://github.com/safe-fndn/safe-smart-account/tree/v1.5.0)（旧 Gnosis Safe）は、Ethereum で[マルチシグ](../multisig/)を実現するコントラクトのウォレットです。「所有者 3 人のうち 2 人」のように、登録した所有者のうち必要数の署名が揃った時だけ、Safe が持つ資産を動かします。取引所や DAO（Decentralized Autonomous Organization、コントラクトで運営する団体）の資金の管理に使われています。

Ethereum の通常のアカウントは、1 個の秘密鍵の署名しか受け付けません。Bitcoin のスクリプトのように、署名を数える命令もプロトコルにはありません。では Safe は、複数の署名をどこで、どう数えているのでしょうか。

{{< figure src="images/safe_overview.webp" alt="左に所有者 A・B・C の丸があり、A と B がチェーンの外でハッシュに署名する。署名 2 個が送信する EOA に渡り、EOA は手数料を払って execTransaction を Safe のプロキシに送る。プロキシの中の破線の storage の枠に、所有者 A・B・C、必要数（threshold）2、nonce（通し番号）、実装のアドレスがあり、その外に ETH の残高がある。プロキシから破線の delegatecall の矢印が実装（singleton）に伸び、実装は署名を数えて（checkNSignatures）取引を実行するコードだけを持つ。宛先への送金・呼び出しの矢印はプロキシから出ており、送り主はプロキシ" caption="Safe で 2-of-3 の送金が実行されるまで" align="center" >}}

上記の図が答えの全体像です。所有者（owner）はチェーンの外でハッシュに署名するだけで、取引を送るのは誰の EOA（秘密鍵で操作する通常のアカウント）でも構いません。署名を数えるのは Safe のコードで、資産と設定を持つプロキシ（proxy）と、コードを持つ実装（singleton）の 2 つのコントラクトに分かれています。

宛先から見た送り主は、資産の持ち主であるプロキシです。図の用語は、以降の節で順に説明します。

<br>

本記事では、図の左から右へ、所有者が何に署名し、Safe がその署名をどう検査するかを説明し、手元の検証用チェーンで実際に送金して確認します。最後に、必要数の署名を集めても防げないことを扱います。m-of-n の考え方と Bitcoin のマルチシグは [Multisig](../multisig/)、EOA とコントラクトのアカウントの違いは [Ethereum Account Model](../ethereum-account-model/) を前提にします。

---

### コントラクトで署名を数える理由

Ethereum のアカウントには、秘密鍵で操作する EOA（Externally Owned Account）と、コードを持つコントラクトのアカウントがあります（[Ethereum Account Model](../ethereum-account-model/)）。EOA の取引の検査はプロトコルが固定しており、1 個の秘密鍵による 1 個の署名だけを受け付けます。2-of-3 のような規則を足す場所はありません。

一方、[コントラクト](../smart-contract/)のアカウントは、呼び出された時に自分のコードを実行し、自分の残高から送金できます。そこで、資産を EOA ではなくコントラクトに持たせ、「署名が必要数あり、全て所有者のものなら送金する」というコードを書けば、マルチシグになります。Safe はこの考え方の代表的な実装です。

<br>

#### プロキシと実装

Safe のコントラクトは、図の右側の 2 つに分かれています。資産の持ち主になり、設定（所有者・必要数・nonce）と、処理を回す先の実装のアドレスを自分の保存領域（storage）に持つのがプロキシで、利用者ごとに 1 個作られます。署名の検査と実行のコードを持つのが実装（singleton）で、多くのプロキシが同じ 1 個を共有します。

資産の持ち主といっても、資産が storage に入っているわけではありません。ETH はプロキシのアカウントの残高で、トークンの保有量はトークンのコントラクトの側に、プロキシのアドレスの分として記録されます。

プロキシは受けた呼び出しを [`delegatecall`](https://docs.soliditylang.org/en/latest/introduction-to-smart-contracts.html#delegatecall-and-libraries) で実装に回します。`delegatecall` は、呼び出し先のコードを呼び出し元の storage と残高のまま実行する命令です。実装のコードが読み書きするのはプロキシの storage なので、コードを共有しても、各 Safe の所有者や資産は混ざりません。

仕組みの詳細は [Upgradeable Proxy](../upgradeable-proxy/) で扱っています。以降は v1.5.0 のソースで説明します（リポジトリは safe-global から safe-fndn に移っています）。

---

### 所有者が署名する内容

送金は、プロキシの [`execTransaction`](https://github.com/safe-fndn/safe-smart-account/blob/v1.5.0/contracts/Safe.sol#L115-L207) を呼んで行います。引数は、取引の内容と、所有者の署名を連結したものです。送る EOA は手数料を払うだけで、所有者である必要はありません。宛先に Safe 自身を指定すれば、所有者や必要数を変える Safe の関数も、同じ手順（必要数の署名）で呼べます。

所有者が署名するのは、取引の内容から作った 32 バイトのハッシュです。Safe は、構造のあるデータを型付きでハッシュにする [EIP-712](../eip-712/) を使い、[SafeTx の型](https://github.com/safe-fndn/safe-smart-account/blob/v1.5.0/contracts/Safe.sol#L59-L62)を次のように定めています。EIP-712 の domain（署名がどのチェーンのどのコントラクト向けかを表す部分）には、chain ID と Safe 自身のアドレスだけを入れます。

```text
SafeTx(address to,uint256 value,bytes data,uint8 operation,uint256 safeTxGas,
       uint256 baseGas,uint256 gasPrice,address gasToken,address refundReceiver,uint256 nonce)
```

`to`・`value`・`data` が宛先・金額・呼び出す内容です。`operation` は 0 が通常の呼び出し、1 が `delegatecall` です。`nonce` は Safe が持つ通し番号で、実行のたびに 1 進みます。ハッシュに nonce が入るので、[実行済みの署名は次の取引のハッシュに合いません](../replay-protection/)。残りの項目はガスと手数料の払い戻しに関する値で、本記事では全て 0 にしています。

---

### Safe が署名を数える方法

`execTransaction` は、現在の nonce でハッシュを計算して nonce を 1 進め、署名を検査してから、`operation` に従って宛先を呼び出します。署名の検査に失敗すると取引は revert（途中の変更を全て取り消して失敗）するので、nonce も進みません。署名の検査は [`checkNSignatures`](https://github.com/safe-fndn/safe-smart-account/blob/v1.5.0/contracts/Safe.sol#L287-L342) が行います。

署名は 65 バイトずつ連結して渡し、`checkNSignatures` が先頭から必要数だけ検査します。65 バイトの署名は r（32 バイト）・s（32 バイト）・v（1 バイト）からなり、Ethereum の ECDSA では、ハッシュと署名から署名者のアドレスを計算で復元できます（ecrecover）。

Safe は各署名から署名者のアドレスを復元し、そのアドレスが所有者であることと、前の署名者のアドレスより大きいことを確認します。署名は所有者のアドレスの昇順に並べる決まりで、同じ所有者の署名を 2 回数える不正は、この大小の比較 1 回で防げます。

<br>

#### 署名の種類

通常の ECDSA の署名では、`v` は復元の計算に使う補助の値（27 か 28）です。Safe はこの `v` に別の値も割り当て、`v` の値で検査の方法を変えます（[signatures.md](https://github.com/safe-fndn/safe-smart-account/blob/v1.5.0/docs/signatures.md)）。

| `v` | 検査の方法 |
| --- | --- |
| 27・28 | ハッシュから ECDSA で署名者を復元する |
| 31・32 | `eth_sign` の接頭辞を付けたハッシュから復元する |
| 1 | 所有者が事前に `approveHash` で承認したか、送る EOA 自身が所有者か |
| 0 | 所有者のコントラクトに [ERC-1271](https://eips.ethereum.org/EIPS/eip-1271) の `isValidSignature(bytes32,bytes)` を問い合わせる |

27・28 は、EOA の秘密鍵で作る普通の署名です。`v = 0` の ERC-1271 は、コントラクトが「このハッシュを自分の署名として認めるか」に答えるための規格で、これを使うと所有者に秘密鍵を持たないコントラクト（別の Safe など）を置けます。v1.5.0 の Safe は、戻り値が `0x1626ba7e` の時だけ署名を有効とします。ecrecover でコントラクトのアドレスが復元されない理由と ERC-1271 の考え方は、[ERC-1271](../erc-1271/) のノートで扱っています。

---

### anvil で Safe を動かす

Ethereum の開発ツール群 [Foundry](https://getfoundry.sh/) の anvil（手元だけで動く Ethereum のノード）に、2-of-3 の Safe を作りました。所有者は EOA 2 個と、ERC-1271 を実装した学習用のコントラクト `StudySigner` 1 個です。

Safe は [safe-smart-account v1.5.0](https://github.com/safe-fndn/safe-smart-account/tree/v1.5.0)（LGPL-3.0-only）をそのままコンパイルしています。鍵は anvil の既定のテスト用の鍵だけで、公開ネットワークには繋いでいません。使った道具の版は [lab の README](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/safe-multisig/lab/README.txt) に記録しました。`StudySigner` は本記事のために書いたもので、監査を受けていません。

```solidity
// SPDX-License-Identifier: MIT
pragma solidity >=0.7.0 <0.9.0;

// Learning-only ERC-1271 signer. Not audited. Do not deploy with real assets.
// The admin approves a hash in advance; the Safe then asks this contract
// whether the hash is approved instead of recovering an ECDSA key.
contract StudySigner {
    bytes4 internal constant MAGIC = 0x1626ba7e; // isValidSignature(bytes32,bytes)
    address public immutable admin;
    mapping(bytes32 => bool) public approved;

    constructor(address admin_) {
        admin = admin_;
    }

    function approve(bytes32 hash) external {
        require(msg.sender == admin, "not admin");
        approved[hash] = true;
    }

    function isValidSignature(bytes32 hash, bytes calldata) external view returns (bytes4) {
        return approved[hash] ? MAGIC : bytes4(0xffffffff);
    }
}
```

0.1 ETH を送る SafeTx に署名し、署名の数・並び・nonce を変えて `execTransaction` を呼びます。要点は次の部分です。

```python
h0 = safe_tx_hash(0)                                  # EIP-712 hash, nonce 0
lo, hi = sorted([o1, o2], key=lambda a: int(a, 16))   # owners by address
ascending = sign(lo, h0) + sign(hi, h0)
for label, sigs in [('1 signature', sign(lo, h0)),
                    ('same owner twice', sign(lo, h0) * 2),
                    ('descending owners', sign(hi, h0) + sign(lo, h0))]:
    print(f'{label:24} -> {execute(sigs)}')           # eth_call, no state change
receipt = execute(ascending, dry=False)                # real transaction
print(f'{"replay nonce-0 sigs":24} -> {execute(ascending)}')
```

`safe_tx_hash` は SafeTx のハッシュをチェーンの外で計算し、`sign` は所有者の鍵で 65 バイトの署名を作ります。`execute` は既定では状態を変えない呼び出し（`eth_call`）で結果だけを確認し、`dry=False` の時に実際の取引を送ります。

続く nonce 1 では、EOA 1 人と `StudySigner` の署名で同じ送金を試します。`StudySigner` の署名は、r に所有者のアドレス、v に 0 を入れた形です。全体は以下です。

<br>

<details>
<summary>safe_multisig.py の全体</summary>

```python
#!/usr/bin/env python3
"""Local anvil only. 2-of-3 Safe (safe-smart-account v1.5.0) and execTransaction.

Run through run.sh. Keys are Anvil's public test mnemonic; never reuse them.
Owners: two EOAs and StudySigner (an ERC-1271 contract written for this lab).
"""
import json
import os
import socket
import subprocess
import time
import urllib.request

BIN = os.environ.get('ETH_BIN', '/opt/eth')
BUILD = json.load(open(os.environ['BUILD']))['contracts']
MNEMONIC = 'test test test test test test test test test test test junk'  # Anvil default, public
ZERO = '0x' + '00' * 20
SAFE_TX = ('SafeTx(address to,uint256 value,bytes data,uint8 operation,uint256 safeTxGas,'
           'uint256 baseGas,uint256 gasPrice,address gasToken,address refundReceiver,uint256 nonce)')
EXEC = 'execTransaction(address,uint256,bytes,uint8,uint256,uint256,uint256,address,address,bytes)'


def cast(*args):
    return subprocess.check_output([f'{BIN}/cast', *map(str, args)], text=True).strip()


with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    PORT = s.getsockname()[1]


def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}', body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        res = json.load(r)
    if 'error' in res:
        raise RuntimeError(res['error'])
    return res['result']


def send(sender, data, to=None, value=0):
    tx = {'from': sender, 'data': data, 'value': hex(value), 'gas': hex(8_000_000), 'gasPrice': hex(2 * 10**9)}
    if to:
        tx['to'] = to
    h = rpc('eth_sendTransaction', tx)
    for _ in range(200):
        receipt = rpc('eth_getTransactionReceipt', h)
        if receipt:
            return receipt
        time.sleep(0.05)
    raise TimeoutError(h)


def call(to, data, sender=None):
    """eth_call; returns (result, None) or (None, revert message)."""
    try:
        return rpc('eth_call', {'to': to, 'data': data, **({'from': sender} if sender else {})}, 'latest'), None
    except RuntimeError as e:
        return None, e.args[0]['message']


def deploy(sender, name, args=''):
    art = next(v for k, v in BUILD.items() if k.endswith(':' + name))
    receipt = send(sender, '0x' + art['bin'] + args)
    assert int(receipt['status'], 16) == 1
    return receipt['contractAddress']


def main():
    node = subprocess.Popen([f'{BIN}/anvil', '--host', '127.0.0.1', '--port', str(PORT), '--chain-id', '31337',
                             '--hardfork', 'prague', '--timestamp', '1700000000', '--accounts', '5', '--quiet'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(200):
            try:
                accounts = rpc('eth_accounts')
                break
            except OSError:
                time.sleep(0.05)
        relayer, o1, o2, admin, receiver = accounts
        pk = {a: cast('wallet', 'private-key', '--mnemonic', MNEMONIC, '--mnemonic-index', i)
              for i, a in enumerate(accounts)}

        singleton = deploy(relayer, 'Safe')
        factory = deploy(relayer, 'SafeProxyFactory')
        signer = deploy(relayer, 'StudySigner', cast('abi-encode', 'f(address)', admin)[2:])
        owners = [o1, o2, signer]
        setup = cast('calldata', 'setup(address[],uint256,address,bytes,address,address,uint256,address)',
                     '[' + ','.join(owners) + ']', 2, ZERO, '0x', ZERO, ZERO, 0, ZERO)
        create = cast('calldata', 'createProxyWithNonce(address,bytes,uint256)', singleton, setup, 0)
        safe = '0x' + call(factory, create, relayer)[0][-40:]
        assert int(send(relayer, create, factory)['status'], 16) == 1
        send(relayer, '0x', safe, 10**18)
        threshold = int(call(safe, cast('calldata', 'getThreshold()'))[0], 16)
        print(f'Safe proxy: 3 owners (2 EOAs + 1 ERC-1271 contract), threshold = {threshold}')

        def nonce():
            return int(call(safe, cast('calldata', 'nonce()'))[0], 16)

        def safe_tx_hash(nonce_, operation=0, to=receiver, value=10**17, data='0x'):
            """EIP-712 hash computed off-chain, the same bytes each owner signs."""
            struct = cast('keccak', cast('abi-encode',
                          'f(bytes32,address,uint256,bytes32,uint8,uint256,uint256,uint256,address,address,uint256)',
                          cast('keccak', SAFE_TX), to, value, cast('keccak', data), operation, 0, 0, 0, ZERO, ZERO, nonce_))
            domain = cast('keccak', cast('abi-encode', 'f(bytes32,uint256,address)',
                          cast('keccak', 'EIP712Domain(uint256 chainId,address verifyingContract)'), 31337, safe))
            return cast('keccak', '0x1901' + domain[2:] + struct[2:])

        def sign(owner, h):  # 65 bytes r || s || v with v = 27/28
            return cast('wallet', 'sign', '--no-hash', '--private-key', pk[owner], h)[2:]

        def execute(signatures, dry=True):
            data = cast('calldata', EXEC, receiver, 10**17, '0x', 0, 0, 0, 0, ZERO, ZERO, '0x' + signatures)
            if dry:
                return call(safe, data, relayer)[1]
            return send(relayer, data, safe)

        h0 = safe_tx_hash(0)
        onchain = call(safe, cast('calldata', 'getTransactionHash(address,uint256,bytes,uint8,uint256,uint256,uint256,address,address,uint256)',
                                  receiver, 10**17, '0x', 0, 0, 0, 0, ZERO, ZERO, 0))[0]
        print('off-chain SafeTx hash == getTransactionHash:', h0 == onchain)
        print('same tx with operation=1 (delegatecall) hash:', safe_tx_hash(0, operation=1)[:18] + '..',
              'vs', h0[:18] + '..')

        lo, hi = sorted([o1, o2], key=lambda a: int(a, 16))
        ascending = sign(lo, h0) + sign(hi, h0)
        print('== nonce 0')
        for label, sigs in [('1 signature', sign(lo, h0)),
                            ('same owner twice', sign(lo, h0) * 2),
                            ('descending owners', sign(hi, h0) + sign(lo, h0))]:
            print(f'{label:24} -> {execute(sigs)}')
        before = int(rpc('eth_getBalance', receiver, 'latest'), 16)
        receipt = execute(ascending, dry=False)
        gained = int(rpc('eth_getBalance', receiver, 'latest'), 16) - before
        print(f'{"ascending owners":24} -> status {int(receipt["status"], 16)},',
              f'receiver +{gained / 1e18} ETH, nonce now {nonce()}')
        print(f'{"replay nonce-0 sigs":24} -> {execute(ascending)}')

        print('== nonce 1 (EOA + ERC-1271 owner)')
        h1 = safe_tx_hash(1)
        parts = sorted([lo, signer], key=lambda a: int(a, 16))
        # Contract signature: r = owner address, s = offset of the dynamic part, v = 0.
        contract_sig = '00' * 12 + signer[2:].lower() + format(65 * 2, '064x') + '00'
        sigs = ''.join(sign(lo, h1) if p == lo else contract_sig for p in parts) + format(0, '064x')
        print(f'{"before approve(hash)":24} -> {execute(sigs)}')
        assert int(send(admin, cast('calldata', 'approve(bytes32)', h1), signer)['status'], 16) == 1
        receipt = execute(sigs, dry=False)
        print(f'{"after approve(hash)":24} -> status {int(receipt["status"], 16)}, nonce now {nonce()}')
    finally:
        node.terminate()
        node.wait()


if __name__ == '__main__':
    main()
```

</details>

<br>

実行結果は以下の通りです。

```text
Safe proxy: 3 owners (2 EOAs + 1 ERC-1271 contract), threshold = 2
off-chain SafeTx hash == getTransactionHash: True
same tx with operation=1 (delegatecall) hash: 0x48bb5c335f58c852.. vs 0xcb3548365f9ffb27..
== nonce 0
1 signature              -> execution reverted: GS020
same owner twice         -> execution reverted: GS026
descending owners        -> execution reverted: GS026
ascending owners         -> status 1, receiver +0.1 ETH, nonce now 1
replay nonce-0 sigs      -> execution reverted: GS026
== nonce 1 (EOA + ERC-1271 owner)
before approve(hash)     -> execution reverted: GS024
after approve(hash)      -> status 1, nonce now 2
```

チェーンの外で計算した SafeTx のハッシュは、Safe の `getTransactionHash` と一致しました。所有者が署名するのは、この 32 バイトです。

エラーの意味は Safe の[エラーコードの一覧](https://github.com/safe-fndn/safe-smart-account/blob/v1.5.0/docs/error_codes.md)にあります。署名が 1 個だと、長さの検査で `GS020`（Signatures data too short）になります。同じ所有者の 2 回と、降順の並びは `GS026`（Invalid owner provided）で、昇順の比較で止まりました。

<br>

実行済みの署名を使い回した場合も `GS026` です。Safe は nonce を別に照合していません。ハッシュが nonce 1 で計算し直されるため、古い署名から復元されるのは所有者ではない無関係のアドレスになり、所有者の検査で失敗します。

ERC-1271 の所有者は、コントラクトがハッシュを承認する前は `GS024`（Invalid contract signature provided）で、承認した後は EOA 1 人と合わせて 2 人分として通りました。

---

### 署名の数では防げないこと

m 個の署名を要求しても、所有者の全員が同じ偽の内容に署名すれば、検査は通ります。署名の数が守るのは鍵を盗まれる場合で、何に署名したかの確認は守りません。

危険なのが `operation = 1`（delegatecall）です。次の図の通り、`operation = 0` の通常の呼び出しでは、宛先のコードは宛先自身の storage で動きます。`operation = 1` では、プロキシから回された実装のコードが、さらに宛先を `delegatecall` で呼びます。宛先のコードがプロキシの storage のまま動くので、プロキシが持つ実装のアドレスも書き換えられます。

{{< figure src="images/safe_operation.webp" alt="左右 2 つの図。左の operation = 0（call）では、Safe のプロキシ（storage）から実線の call で宛先のコントラクトを呼び、宛先のコードは宛先の storage を使う。右の operation = 1（delegatecall）では、破線の delegatecall で攻撃者が用意できる宛先のコントラクトを呼び、宛先のコードからプロキシの storage の実装のアドレスへ赤い上書きの矢印が伸びる" caption="operation の値で、宛先のコードが動く storage が変わる" align="center" >}}

2025 年 2 月の [Bybit の事件](../wallet/#bybitsafe-の承認処理の乗っ取り)は、この経路で起きました。改ざんされた Web 画面で、承認者は攻撃者のコントラクトを宛先とする `operation = 1` の取引に署名しました。Safe は正しく署名を検査して実行し、宛先のコードが実装のアドレスを攻撃者の実装に書き換えました。以後、プロキシへの呼び出しは攻撃者のコードに回り、署名の検査なしに資産が移されました。

<br>

所有者が署名するのは 32 バイトのハッシュです。実験では、同じ宛先・金額のまま `operation` を 0 から 1 に変えると、ハッシュは `0xcb35…` から `0x48bb…` に変わりました。ハッシュの見た目からは、どちらが危険な取引かを判断できません。

内容を読めないまま承認すること（blind signing）を避けるには、ハードウェアウォレットの画面で宛先・金額・`operation`・nonce を読める形で確認するか、別の端末で内容からハッシュを計算し直して照合します（例: [safe-tx-hashes-util](https://github.com/pcaversaccio/safe-tx-hashes-util)）。

<br>

鍵の置き場所を分けても、所有者が共通して頼る部分が残ることがあります。

- 全員が同じ Web 画面で取引を作り、同じ表示を見て署名する。画面が改ざんされると、全員が同じ偽の内容に署名する。
- Safe のモジュール（Safe に機能を足す外部のコントラクト）は、[`execTransactionFromModule`](https://github.com/safe-fndn/safe-smart-account/blob/v1.5.0/contracts/base/ModuleManager.sol#L154-L163) で所有者の署名なしに実行できる。有効にしたモジュールは、必要数の署名と同じ権限を持つ。モジュールの追加は通常は必要数の署名を要するが、既存のモジュールからも追加できる。

---

### 利点

- プロトコルを変えずに、m-of-n の承認をコントラクトのコードで実現できる
- 誰が署名したかがチェーンに記録され、後から確認できる
- 所有者・必要数は、資産を移さずに設定の取引で変えられる
- ERC-1271 で、コントラクト（別の Safe など）も所有者にできる

---

### 欠点

- コントラクトなので、実装や `delegatecall`・モジュールの設定を誤ると、署名の検査ごと迂回される
- 取引ごとに署名の検査のコードが動き、EOA の送金より手数料が高い
- 所有者が署名するのは 32 バイトのハッシュで、内容の確認は所有者の端末と運用に任される

---

### 適さないケース

- 少額を頻繁に送る用途で、署名を集める手間と手数料が資産の保護に見合わない場合
- 所有者が取引の内容を自分の端末で確認する手段を持たず、共通の画面の表示を信じるしかない場合
- チェーン上で誰が承認したかを隠したい場合（所有者のアドレスと署名がチェーンに出る）
