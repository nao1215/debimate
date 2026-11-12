---
title: "ERC-4337 - プロトコルを変えないアカウント抽象化"
date: 2026-11-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain", "ethereum", "erc-4337", "smart-contract", "account-abstraction"]
weight: 19
wrapTables: true
topics: ["Transaction / Wallet"]
---

[ERC-4337](https://eips.ethereum.org/EIPS/eip-4337) は、Ethereum のプロトコルを変えずに、スマートコントラクトのアカウントをトランザクションの送り主のように使えるようにする規格です。

Ethereum のアカウントには、秘密鍵で署名してトランザクションを送る EOA（Externally Owned Account）と、コードを持つ[コントラクト](../smart-contract/)の 2 種類があります。チェーンにトランザクションを送れるのは EOA だけです。コントラクトで作ったアカウント（スマートアカウント）は、署名の確かめ方を自分のコードで決められるので、複数人の承認や鍵の差し替えを組み込めます。しかし、自分ではトランザクションを送れません。

もう 1 つの制約は手数料です。例えば、[ERC-20](../erc-20/) のトークンである [USDC](https://www.circle.com/usdc)（米ドルに連動するステーブルコイン）だけを持ち、ETH を少しも持たないアドレスからは、通常は USDC を送れません。トランザクションの手数料（ガス代）は、送り主が ETH で払う決まりだからです。

<br>

ERC-4337 では、利用者はトランザクションの代わりに UserOperation という依頼を作ります。Bundler と呼ぶ第三者がそれを集め、自分の EOA から 普通のトランザクション 1 件として送ります。そのトランザクションの宛先は、全てのスマートアカウントが共有する EntryPoint というコントラクトです。

UserOperation は、普通のトランザクションとは別の置き場（UserOperation の mempool）で Bundler どうしの間を配られます。EntryPoint は依頼ごとにアカウントの検証と実行を呼び、使った分の手数料は、アカウントか肩代わり役の Paymaster の預け金（deposit）から Bundler に返します。

{{< figure src="images/erc-4337_concept.webp" alt="上段は破線で囲んだチェーンの外の層で、青い UserOperation のカード（署名の形式は自由）が黄土色の Bundler（EOA・ガス代を払う）に渡る。Bundler から handleOps のトランザクションが下段の灰色の層（チェーンの上、プロトコルは従来のまま）に下り、EntryPoint の中で 1. 検証（使える処理に制限）→ 2. 実行（任意のコード）の順に処理し、スマートアカウントと、使う場合は Paymaster を呼ぶ。EntryPoint から Bundler へ、手数料を ETH で返す破線の矢印が戻る" caption="チェーンの外の UserOperation と、チェーンに載る 1 件のトランザクション" align="center" >}}

上記の図の上段はチェーンの外、灰色の下段はチェーンの上です。下段は従来の Ethereum と何も変わらず、チェーンから見えるのは、Bundler の EOA が EntryPoint の `handleOps` という関数を呼ぶ普通のトランザクションだけです。

<br>

本記事では、ローカルの実験で確認しながら、ERC-4337 の部品と処理の流れを説明します。軸になるのは次の疑問です。

- ERC-4337 は、EOA の何を解決するのか。
- UserOperation は、誰がどうやってチェーンに載せるのか。
- 検証と実行を分けるのは、なぜか。
- スマートアカウントの手数料は、誰が払うのか。
- まだ存在しないアカウントのアドレスに、なぜ送金できるのか。
- 既存の EOA に機能を足す EIP-7702 とは、どういう関係にあるのか。

アカウントの状態や nonce（トランザクションの通し番号）は [Ethereum Account Model](../ethereum-account-model/)、トランザクションの項目と手数料の計算は [Ethereum Transaction](../ethereum-transaction/) で説明しています。

---

### アカウント抽象化が必要な理由

EOA のトランザクションは、プロトコルが決めた 1 通りの方法で検証されます。秘密鍵の[署名](../digital-signature/)から送り主を復元し、nonce と ETH の残高を確認します。そのため、次のことは EOA だけではできません。

| EOA の決まり | 困る場面 |
| --- | --- |
| 1 つの秘密鍵の署名だけを受け付ける | 鍵を失うと資産を取り戻せない。2 人の承認を必須にできない |
| 手数料は送り主が ETH で払う | ETH を持たない新しい利用者は、最初の操作ができない |
| 1 件のトランザクションで呼べる宛先は 1 つ | トークンの使用許可（`approve`）と交換を 1 回でまとめられない |

アカウント抽象化（account abstraction）は、検証と手数料の払い方をプロトコルの固定の規則から外し、アカウント自身のコードに任せる考え方です。[Wallet](../wallet/) で触れたスマートアカウントや[マルチシグ](../safe-multisig/)は、この考え方をコントラクトで実現しています。ただし冒頭で述べた通り、スマートアカウントは自分ではトランザクションを送れないので、誰かの EOA が呼び出す必要がありました。

<br>

ERC-4337 は Ethereum のプロトコルを変えた、と思うかもしれません。しかし、仕様の冒頭の要約（Abstract）が述べる通り、ERC-4337 はコンセンサス層（全ノードが守るブロックの規則）の変更を完全に避けています。トランザクションの型を足す代わりに、UserOperation を別の [mempool](../mempool/)（未確定の要求の置き場）で配り、EntryPoint というコントラクトで処理します。

EIP（Ethereum Improvement Proposal）は Ethereum の改善提案の総称で、ERC はそのうちアプリケーション層の規格の分類です。ERC-4337 は 2021 年 9 月に提案され、2026 年 6 月に Final（確定）になりました（[ethereum/ERCs の変更履歴](https://github.com/ethereum/ERCs/commits/master/ERCS/erc-4337.md)）。

---

### UserOperation と部品

UserOperation は、アカウントにさせたい操作を表す構造体です。トランザクションに似た項目（送り主・nonce・呼び出しデータの `callData`・手数料の上限・署名）に加えて、アカウントを作るための `initCode` や、手数料を肩代わりする Paymaster の指定を持ちます。`signature` の中身はプロトコルではなく、アカウントのコードが解釈します。コントラクトのアカウントの署名を他のコントラクトが確認する一般的な方法は、[ERC-1271](../erc-1271/) で説明しています。

UserOperation を受け取ってからチェーンに載るまでには、次の部品が関わります。

| 部品 | 役割 |
| --- | --- |
| スマートアカウント | `validateUserOp` で署名を検証し、操作を実行するコントラクト |
| Bundler | UserOperation を集め、`handleOps` を呼ぶトランザクションを EOA から送るノード |
| EntryPoint | 全てのアカウントが共有するコントラクト。検証と実行を順に呼ぶ |
| Factory | まだ無いアカウントを作るコントラクト |
| Paymaster | 手数料を肩代わりするかを判断するコントラクト |
| Aggregator | 複数の UserOperation の署名をまとめて 1 回で検証するコントラクト（本記事では扱いません） |
| UserOperation mempool | Bundler どうしが UserOperation を交換する P2P のネットワーク |

以下は、1 件の UserOperation がチェーンに載るまでの流れです。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant W as ウォレット
    participant B as Bundler
    participant E as EntryPoint
    participant A as スマートアカウント
    W->>B: eth_sendUserOperation
    B->>B: 検証をシミュレーション
    B->>E: handleOps（普通のトランザクション）
    E->>A: validateUserOp（検証）
    E->>A: callData を実行
    E->>B: deposit から手数料を払う
```

上記の図の `eth_sendUserOperation` は、Bundler が受け付ける JSON-RPC のメソッドです。ウォレットが Bundler に渡すのはトランザクションではありません。チェーンに載るトランザクションの送り主は Bundler で、UserOperation はその呼び出しデータの中に入ります。

---

### 検証と実行の分離

EntryPoint の `handleOps` は、ループを 2 回回します。1 回目は全ての UserOperation の検証で、必要ならアカウントを作り、`validateUserOp` を呼び、手数料の前払いを受け取ります。2 回目で、検証を通った UserOperation の `callData` を実行します。

{{< figure src="images/erc-4337_loops.webp" alt="EntryPoint の handleOps（Bundler が送る 1 件のトランザクション）。見出しの下に、検証は全て、どの実行よりも前に終わる（実行で他の検証の結果が変わらない）とある。左の青い枠「1 回目のループ：検証」（アカウントの作成・署名の確認・前払い）と右の緑の枠「2 回目のループ：実行」（callData を実行）が並び、それぞれに UserOperation 1〜3 の箱がある。全て通ったら左から右へ進む。左の枠から赤い矢印が下に伸び、1 件でも検証に失敗すると handleOps 全体が取り消し（FailedOp など）、前払いも戻り、ガス代は Bundler の損とある。右の枠の下には、実行が失敗しても使ったガスの手数料はアカウントか Paymaster が払うとある" caption="handleOps の 2 つのループと、失敗した時に損をする側" align="center" >}}

上記の図のように、参照実装の EntryPoint では、検証で 1 件でも失敗すると、`handleOps` は `FailedOp` などのエラーでトランザクションごと取り消されます。検証の中で受け取った前払いも取り消しで戻るので、手数料は誰からも入らず、そのトランザクションのガス代は Bundler の損です。一方、検証を通った後なら、実行が失敗しても前払いから使った分の手数料が払われます（Bundler がトランザクションに積んだガスが足りない場合を除く）。

検証を全て先に済ませるので、ある UserOperation の実行が、同じトランザクションに入った別の UserOperation で検証した結果を変えることもありません。手数料を払うかどうかは検証で決まり、その検証の結果は実行に左右されないわけです。

<br>

損を避けるため、Bundler は送る前に検証を手元でシミュレーションし、通ったものだけを載せます。しかし、検証のコードがブロックの時刻（`block.timestamp`）のような値や、多数のアカウントが共通に読む値を使うと、シミュレーションで通った検証がブロックの中では失敗し得ます。これを悪用すれば、Bundler に手数料を損させ続けられます。

そこで [ERC-7562](https://eips.ethereum.org/EIPS/eip-7562) が、検証の段階で使える命令と読める値を制限しています（2026 年 11 月時点の仕様の状態は意見募集中の Review）。制限が掛かるのは検証だけで、実行の段階では任意のコードが動きます。規則の中身と、それが防ぐ攻撃の流れは [ERC-7562](../erc-7562/) のノートで説明します。

---

### 手数料を払う主体

ETH を持たないアカウントの UserOperation でも、チェーンに載る以上はガス代が掛かります。チェーンに載るのは Bundler のトランザクションなので、[ガス代](../gas-eip-1559/)はまず Bundler の EOA が ETH で払います。

Bundler の負担は、EntryPoint が後で返します。EntryPoint は、アカウントか Paymaster ごとに預かった ETH の残高（deposit）を持っています。そこから使った分を引き、`handleOps` の引数 `beneficiary`（Bundler が指定する受取先）に払います。

{{< figure src="images/erc-4337_payflow.webp" alt="左にアカウントの残高（ETH）と Paymaster の箱。アカウントの残高から、検証の中で不足分を前払いする矢印が EntryPoint の中のアカウントの deposit へ伸びる。Paymaster から前もって預ける矢印が Paymaster の deposit へ伸びる。2 つの deposit から黄土色の矢印が右の Bundler（beneficiary）へ伸び、実際に使った分を払う、余りは deposit に残るとある。下に、Paymaster を指定した UserOperation は Paymaster の deposit から払うとある" caption="手数料の ETH の出どころと行き先" align="center" >}}

上記の図の左上の前払いは、検証の時点で、使い得る最大の手数料に deposit が足りない分です。アカウントは `validateUserOp` の中で、その分の ETH を EntryPoint に送ります。払う側は次のどちらかです。

| UserOperation の指定 | 手数料を払う主体 |
| --- | --- |
| Paymaster なし | アカウント自身。deposit の不足分を検証の中で前払いし、使わなかった分は deposit に残る |
| Paymaster あり | Paymaster の deposit。代わりに USDC を受け取る、アプリの運営者が負担する、などは Paymaster のコードで決める |

つまり、手数料が消えるわけではなく、ETH で払う主体が利用者からほかの誰かに移るだけです。Paymaster は、自分の deposit を減らす相手を選ぶ必要があるので、署名した承認やトークンの支払いを `validatePaymasterUserOp` で確認します。

<br>

EntryPoint が測れないガスもあります。どのトランザクションにも掛かる基本料 21,000 を束ねた UserOperation の数で割った分や、UserOperation を呼び出しデータとして載せる分です（トランザクションのデータもバイト数に応じてガスが掛かります）。これは UserOperation の `preVerificationGas` に書き、アカウントや Paymaster が一緒に払います。低すぎる値の UserOperation は Bundler の赤字になるので、受け取られません。

---

### 作る前から決まるアドレス

コントラクトを作る通常の方法（`CREATE` 命令や、EOA から送る作成用のトランザクション）では、作る側の [nonce でアドレスが変わる](../ethereum-address/)ので、先に別のトランザクションを出すと予定のアドレスからずれます。ERC-4337 の Factory は `CREATE2` という命令を使い、アドレスは次の式で作る前から決まります。

```text
address = keccak256(0xff ‖ factory ‖ salt ‖ keccak256(creationCode))[12:]
```

`‖` はバイト列の連結、`salt` は作る側が選ぶ任意の 32 バイトの値、`[12:]` は 32 バイトのハッシュの末尾 20 バイトをアドレスとして取る操作です。

`creationCode` は、作るコントラクトの生成用のコードです。実験で使う SimpleAccountFactory では、アカウントの初期化に渡す所有者のアドレスもここに入ります。そのため、別の人が先回りして同じアドレスにアカウントを作っても、所有者を自分に変えることはできません。仕様も、アドレスが最初の署名者に依存することが重要だと述べています。

<br>

ウォレットはこのアドレスを先に利用者に見せ、ETH やトークンを受け取れるようにします。アドレスに残高はあっても、まだコードはありません。最初の UserOperation の `initCode` に Factory のアドレスと `createAccount` の呼び出しを入れておくと、EntryPoint は検証の前にアカウントを作ります。

<br>

<details>
<summary>initCode を呼ぶのは誰か</summary>

`initCode` を呼ぶのは EntryPoint ではなく、専用の SenderCreator というコントラクトです。`initCode` には任意の宛先を書けるので、EntryPoint から呼ぶと、EntryPoint からの呼び出しを無条件に信頼するアカウントや Paymaster を操作できてしまいます。Factory も、呼び出し元が SenderCreator であることを確認します。

</details>

<br>

---

### ローカルでの UserOperation 実験

実験では、[Foundry](https://github.com/foundry-rs/foundry)（Ethereum の開発ツール群）のローカル開発用ノード [Anvil](https://getfoundry.sh/anvil/overview) の上で、ERC-4337 の参照実装 [eth-infinitism/account-abstraction](https://github.com/eth-infinitism/account-abstraction/tree/v0.9.0) の 4 つのコントラクトを使います。EntryPoint、所有者 1 人の署名で動く最小のスマートアカウントの [SimpleAccount](https://github.com/eth-infinitism/account-abstraction/blob/v0.9.0/contracts/accounts/SimpleAccount.sol)、その Factory、無条件に手数料を払う試験用の Paymaster です。

Bundler のソフトウェアと UserOperation の mempool は使いません。スクリプトが UserOperation を組み立て、テスト用の EOA から `handleOps` を直接呼んで Bundler の役を代わります。鍵は Anvil の公開されたテスト用のニーモニック（鍵を作る元になる単語列）から作ったものだけで、所有者の鍵には ETH を一度も入れません。

<br>

<details>
<summary>実験の環境とライセンス</summary>

| 部品 | 版と補足 |
| --- | --- |
| Anvil・[`cast`](https://getfoundry.sh/cast/overview)（Foundry） | 1.7.1。実行規則は Prague |
| コンパイラ | [solc 0.8.28](https://github.com/argotorg/solidity/releases/tag/v0.8.28)。設定はリポジトリの [Hardhat](https://hardhat.org/) の設定に合わせる |
| EntryPoint | v0.9.0（コミット `b36a1ed`）。GPL-3.0 |
| SimpleAccount と Factory | v0.9.0。MIT |
| `TestPaymasterAcceptAll` | v0.9.0。GPL-3.0。無条件に手数料を払う試験用で、本番には使えない |
| [OpenZeppelin Contracts](https://github.com/OpenZeppelin/openzeppelin-contracts/tree/v5.1.0) | v5.1.0。MIT |

ソースは本記事のリポジトリに複製せず、実行時に固定したコミットを取得します。

</details>

<br>

以下は、UserOperation を作って署名し、`handleOps` を送る部分の抜粋です。`cast` は Foundry の CLI、`call` は読み取りの呼び出し、`send` はトランザクションの送信、`entry_point` と `sender` はデプロイ済みの EntryPoint と、作る前のアカウントのアドレスです。

`u128x2` は 2 つの値を 32 バイトに詰める補助関数で、v0.7 以降の EntryPoint（版の違いは付録）はガスの上限 2 つと手数料の単価 2 つをこの形で受け取ります。`OP_TYPE` と `op_tuple` は構造体の型と値を `cast` に渡す文字列、`handle_ops` は `handleOps` の呼び出しデータを作る関数、`o` は送る UserOperation です。

```python
def user_op(nonce, to, init=b'', pm='0x'):
    return {'sender': sender, 'nonce': nonce, 'initCode': init or '0x',
            'callData': cast('calldata', 'execute(address,uint256,bytes)', to, ETH // 100, '0x'),
            'accountGasLimits': u128x2(400_000, 60_000),   # verificationGasLimit, callGasLimit
            'preVerificationGas': 50_000,
            'gasFees': u128x2(2 * GWEI, 2 * GWEI),          # maxPriorityFeePerGas, maxFeePerGas
            'paymasterAndData': pm, 'signature': '0x'}

def sign(op, key):
    op['signature'] = '0x'
    h = call(entry_point, f'getUserOpHash({OP_TYPE})(bytes32)', op_tuple(op))
    # SimpleAccount v0.9 recovers the signer from the raw EIP-712 userOpHash.
    op['signature'] = cast('wallet', 'sign', '--no-hash', '--private-key', key, h)
    return h

# Bundler role: a funded test EOA calls handleOps directly.
r = send(bundler, handle_ops(o, bundler), entry_point, gas=3_000_000)
```

署名の対象 `userOpHash` は、`signature`（v0.9 では Paymaster の署名も）以外の全項目と [chain ID、EntryPoint のアドレス](../replay-protection/)から作る [EIP-712](../eip-712/) の型付きハッシュです。起動・デプロイ・残高の検査を含む全体は以下です。

<br>

<details>
<summary>run.py の全体（268 行）</summary>

```python
#!/usr/bin/env python3
"""Local-only ERC-4337 experiment (EntryPoint v0.9.0). Run through run.sh.

The script plays the bundler itself: it builds UserOperations and calls
EntryPoint.handleOps directly from a funded test EOA. No bundler software,
no alt mempool, no external RPC. Keys are Anvil's public test mnemonic only.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import urllib.request

HERE = Path(__file__).resolve().parent
OUT = HERE / 'output'
OUT.mkdir(exist_ok=True)
TOOLS = {n: os.environ.get(n.upper(), shutil.which(n)) for n in ('anvil', 'cast')}
if not all(TOOLS.values()):
    raise SystemExit('Put anvil and cast on PATH (or set ANVIL, CAST).')
BUILD = json.loads(Path(os.environ['BUILD']).read_text())['contracts']
MNEMONIC = 'test test test test test test test test test test test junk'  # Anvil default, public
GWEI = 10**9
ETH = 10**18
OP_TYPE = '(address,uint256,bytes,bytes,bytes32,uint256,bytes32,bytes,bytes)'

def cast(*args):
    return subprocess.check_output([TOOLS['cast'], *map(str, args)], text=True).strip()

def artifact(suffix):
    return next(v for k, v in BUILD.items() if k.endswith(suffix))

with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
URL = f'http://127.0.0.1:{port}'

def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(URL, body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        res = json.load(r)
    if 'error' in res:
        raise RuntimeError(res['error'])
    return res['result']

def send(sender, data, to=None, value=0, gas=15_000_000):
    # Legacy gasPrice keeps the bundler's price fixed at 2 gwei in every block.
    tx = {'from': sender, 'data': data, 'value': hex(value), 'gas': hex(gas), 'gasPrice': hex(2 * GWEI)}
    if to:
        tx['to'] = to
    h = rpc('eth_sendTransaction', tx)
    for _ in range(200):
        r = rpc('eth_getTransactionReceipt', h)
        if r:
            assert int(r['status'], 16) == 1, r
            return r
        time.sleep(0.05)
    raise TimeoutError(h)

def deploy(sender, suffix, *ctor):
    a = artifact(suffix)
    args = cast('abi-encode', 'f(address)', *ctor)[2:] if ctor else ''
    return send(sender, '0x' + a['bin'] + args)['contractAddress']

def call(to, sig, *args):
    return cast('call', '--rpc-url', URL, to, sig, *args)

def balance(addr):
    return int(rpc('eth_getBalance', addr, 'latest'), 16)

def u128x2(hi, lo):  # two uint128 packed into one bytes32
    return '0x' + f'{hi:032x}{lo:032x}'

def op_tuple(op):
    return '(' + ','.join(str(op[k]) for k in (
        'sender', 'nonce', 'initCode', 'callData', 'accountGasLimits',
        'preVerificationGas', 'gasFees', 'paymasterAndData', 'signature')) + ')'

def sign(op, key):
    op['signature'] = '0x'
    h = call(entry_point, f'getUserOpHash({OP_TYPE})(bytes32)', op_tuple(op))
    # SimpleAccount v0.9 recovers the signer from the raw EIP-712 userOpHash.
    op['signature'] = cast('wallet', 'sign', '--no-hash', '--private-key', key, h)
    return h

def handle_ops(op, beneficiary):
    data = cast('calldata', f'handleOps({OP_TYPE}[],address)', f'[{op_tuple(op)}]', beneficiary)
    return data

def frames(txhash):
    """Gas of the call frames that ERC-4337 splits into validation and execution."""
    trace = rpc('debug_traceTransaction', txhash, {'tracer': 'callTracer'})
    names = {cast('sig', s): s.split('(')[0] for s in (
        'createSender(bytes)', 'validateUserOp(' + OP_TYPE + ',bytes32,uint256)',
        'validatePaymasterUserOp(' + OP_TYPE + ',bytes32,uint256)',
        'execute(address,uint256,bytes)')}
    found = {}

    def walk(f):
        name = names.get(f.get('input', '')[:10])
        if name and name not in found:
            found[name] = int(f['gasUsed'], 16)
        for c in f.get('calls', []):
            walk(c)
    walk(trace)
    return found

def user_op_event(receipt):
    topic = cast('sig-event', 'UserOperationEvent(bytes32,address,address,uint256,bool,uint256,uint256)')
    log = next(l for l in receipt['logs'] if l['topics'][0] == topic)
    words = [int(log['data'][2 + i * 64: 2 + (i + 1) * 64], 16) for i in range(4)]
    return {'success': words[1], 'actualGasCost': words[2], 'actualGasUsed': words[3]}

lines = []
log = (OUT / 'node.log').open('w')
node = subprocess.Popen([TOOLS['anvil'], '--host', '127.0.0.1', '--port', str(port),
                         '--chain-id', '31337', '--hardfork', 'prague', '--timestamp', '1700000000',
                         '--accounts', '3', '--quiet'], stdout=log, stderr=log)
try:
    for _ in range(200):
        try:
            bundler, funder, pm_owner = rpc('eth_accounts')[:3]
            break
        except (OSError, RuntimeError):
            time.sleep(0.05)
    else:
        raise TimeoutError('Anvil startup')
    owner_key = cast('wallet', 'private-key', MNEMONIC, 5)    # never funded
    owner = cast('wallet', 'address', '--private-key', owner_key)
    other_key = cast('wallet', 'private-key', MNEMONIC, 6)    # not the owner

    entry_point = deploy(bundler, ':EntryPoint')
    factory = deploy(bundler, ':SimpleAccountFactory', entry_point)
    paymaster = deploy(pm_owner, ':TestPaymasterAcceptAll', entry_point)
    send(pm_owner, cast('calldata', 'deposit()'), paymaster, value=1 * ETH)

    # --- 1. Address before deployment (CREATE2) ---
    salt = 0
    implementation = call(factory, 'accountImplementation()(address)')
    init_args = cast('abi-encode', 'f(address,bytes)', implementation,
                     cast('calldata', 'initialize(address)', owner))
    proxy_init_code = '0x' + artifact(':ERC1967Proxy')['bin'] + init_args[2:]
    by_formula = cast('compute-address', factory, '--salt', f'0x{salt:064x}',
                      '--init-code-hash', cast('keccak', proxy_init_code)).split()[-1]
    by_factory = call(factory, 'getAddress(address,uint256)(address)', owner, salt)
    init_code = factory + cast('calldata', 'createAccount(address,uint256)', owner, salt)[2:]
    try:
        rpc('eth_call', {'to': entry_point, 'data': cast('calldata', 'getSenderAddress(bytes)', init_code)}, 'latest')
        raise AssertionError('getSenderAddress must revert')
    except RuntimeError as e:
        by_entry_point = cast('decode-error', '--sig', 'SenderAddressResult(address)', e.args[0]['data'])
    sender = by_factory
    assert by_formula.lower() == by_factory.lower() == by_entry_point.lower()
    assert rpc('eth_getCode', sender, 'latest') == '0x'
    send(funder, '0x', sender, value=ETH // 10)
    lines += ['# 1. counterfactual address',
              f'CREATE2 formula      : {by_formula}',
              f'factory.getAddress   : {by_factory}',
              f'getSenderAddress     : {by_entry_point}',
              f'code before          : {rpc("eth_getCode", sender, "latest")}  balance: {balance(sender) / ETH} ETH']

    recipients = [cast('wallet', 'address', '--private-key', cast('wallet', 'private-key', MNEMONIC, i)) for i in (7, 8, 9)]

    def user_op(nonce, to, init=b'', pm='0x'):
        return {'sender': sender, 'nonce': nonce, 'initCode': init or '0x',
                'callData': cast('calldata', 'execute(address,uint256,bytes)', to, ETH // 100, '0x'),
                'accountGasLimits': u128x2(400_000, 60_000),   # verificationGasLimit, callGasLimit
                'preVerificationGas': 50_000,
                'gasFees': u128x2(2 * GWEI, 2 * GWEI),          # maxPriorityFeePerGas, maxFeePerGas
                'paymasterAndData': pm, 'signature': '0x'}

    # --- 2. Broken signatures are rejected in validation ---
    lines.append('# 2. validation failures (eth_call to handleOps, nothing is mined)')
    op = user_op(0, recipients[0], init_code)
    sign(op, owner_key)
    tampered = dict(op, callData=cast('calldata', 'execute(address,uint256,bytes)', recipients[0], ETH, '0x'))
    wrong_key = dict(op)
    sign(wrong_key, other_key)
    for label, bad in (('value changed after signing', tampered), ('signed by another key', wrong_key)):
        try:
            rpc('eth_call', {'from': bundler, 'to': entry_point, 'data': handle_ops(bad, bundler)}, 'latest')
            raise AssertionError('must fail')
        except RuntimeError as e:
            err = cast('decode-error', '--sig', 'FailedOp(uint256,string)', e.args[0]['data']).splitlines()
            lines.append(f'{label:28}: FailedOp({err[0]}, {err[1]})')
    assert rpc('eth_getCode', sender, 'latest') == '0x'

    # --- 3. Three UserOperations: deploy + self-paid, self-paid, paymaster ---
    lines.append('# 3. handleOps sent by the bundler EOA (beneficiary = bundler)')
    pm_data = paymaster + f'{100_000:032x}{0:032x}'  # paymaster, verification gas, postOp gas
    cases = [('op1 initCode, self-paid', op),
             ('op2 self-paid', user_op(1, recipients[1])),
             ('op3 paymaster', user_op(2, recipients[2], pm=pm_data))]
    rows, gas_rows = [], []
    for i, (label, o) in enumerate(cases):
        if i:
            sign(o, owner_key)
        before = {'bundler': balance(bundler), 'sender': balance(sender),
                  'sender_deposit': int(call(entry_point, 'balanceOf(address)(uint256)', sender).split()[0]),
                  'pm_deposit': int(call(entry_point, 'balanceOf(address)(uint256)', paymaster).split()[0]),
                  'owner': balance(owner)}
        r = send(bundler, handle_ops(o, bundler), entry_point, gas=3_000_000)
        ev = user_op_event(r)
        assert ev['success'] == 1
        after = {'bundler': balance(bundler), 'sender': balance(sender),
                 'sender_deposit': int(call(entry_point, 'balanceOf(address)(uint256)', sender).split()[0]),
                 'pm_deposit': int(call(entry_point, 'balanceOf(address)(uint256)', paymaster).split()[0]),
                 'owner': balance(owner)}
        d = {k: after[k] - before[k] for k in before}
        tx_fee = int(r['gasUsed'], 16) * int(r['effectiveGasPrice'], 16)
        assert d['owner'] == 0 and balance(owner) == 0
        assert d['bundler'] == ev['actualGasCost'] - tx_fee
        if i == 2:
            assert d['sender'] == -ETH // 100 and d['sender_deposit'] == 0
            assert d['pm_deposit'] == -ev['actualGasCost']
        else:
            assert d['sender'] + d['sender_deposit'] == -ETH // 100 - ev['actualGasCost']
        f = frames(r['transactionHash'])
        g = lambda wei: f'{wei // GWEI:>+10}'  # all values are multiples of 1 gwei here
        rows.append(f"{label:24}| {g(d['sender'] + d['sender_deposit'])} | {g(d['pm_deposit'])} | "
                    f"{g(-tx_fee)} | {g(ev['actualGasCost'])} | {g(d['owner'])}")
        gas_rows.append(f"{label:24}| {int(r['gasUsed'], 16):>8} | {ev['actualGasUsed']:>8} | "
                        f"{f.get('createSender', 0):>8} | {f['validateUserOp']:>8} | "
                        f"{f.get('validatePaymasterUserOp', 0):>8} | {f['execute']:>8}")
        if i == 0:
            code_len = (len(rpc('eth_getCode', sender, 'latest')) - 2) // 2
            lines.append(f'code after op1       : {code_len} bytes at {sender}')
    lines.append('change in gwei          | sender     | paymaster  | bundler    | bundler    | owner')
    lines.append('                        | ETH+deposit| deposit    | tx fee     | received   | EOA')
    lines += rows
    # --- 4. Baseline: plain EOA transfer of the same 0.01 ETH to a fresh address ---
    fresh = cast('wallet', 'address', '--private-key', cast('wallet', 'private-key', MNEMONIC, 10))
    base = send(funder, '0x', fresh, value=ETH // 100, gas=21_000)
    lines.append('# 4. gas (tx = handleOps receipt gasUsed, op = UserOperationEvent.actualGasUsed)')
    lines.append('case                    | tx gas   | op gas   | create   | validate | pm valid | execute')
    lines += gas_rows
    lines.append(f"{'EOA transfer (baseline)':24}| {int(base['gasUsed'], 16):>8} |")
    lines.append('Assertions: PASS')
    summary = '\n'.join(lines) + '\n'
    (OUT / 'summary.txt').write_text(summary)
    (OUT / 'versions.txt').write_text('\n'.join(
        subprocess.check_output([t, '--version'], text=True).splitlines()[0] for t in TOOLS.values()) + '\n')
    print(summary, end='')
finally:
    node.terminate()
    try:
        node.wait(timeout=5)
    except subprocess.TimeoutExpired:
        node.kill()
    log.close()
```

</details>

<br>

```bash
bash content/notes/blockchain-systems/erc-4337/lab/run.sh
```

実行すると、4 段に分かれた[出力](lab/output/summary.txt)が出ます。手順は [lab/README.txt](lab/README.txt) にまとめています。

<br>

<details>
<summary>summary.txt の全体</summary>

```text
# 1. counterfactual address
CREATE2 formula      : 0xD34A413E5659cCDc5f14B5DDb5e8c3C232E4EA21
factory.getAddress   : 0xD34A413E5659cCDc5f14B5DDb5e8c3C232E4EA21
getSenderAddress     : 0xD34A413E5659cCDc5f14B5DDb5e8c3C232E4EA21
code before          : 0x  balance: 0.1 ETH
# 2. validation failures (eth_call to handleOps, nothing is mined)
value changed after signing : FailedOp(0, "AA24 signature error")
signed by another key       : FailedOp(0, "AA24 signature error")
# 3. handleOps sent by the bundler EOA (beneficiary = bundler)
code after op1       : 141 bytes at 0xD34A413E5659cCDc5f14B5DDb5e8c3C232E4EA21
change in gwei          | sender     | paymaster  | bundler    | bundler    | owner
                        | ETH+deposit| deposit    | tx fee     | received   | EOA
op1 initCode, self-paid |  -10597632 |         +0 |    -585516 |    +597632 |         +0
op2 self-paid           |  -10248598 |         +0 |    -234634 |    +248598 |         +0
op3 paymaster           |  -10000000 |    -241398 |    -228528 |    +241398 |         +0
# 4. gas (tx = handleOps receipt gasUsed, op = UserOperationEvent.actualGasUsed)
case                    | tx gas   | op gas   | create   | validate | pm valid | execute
op1 initCode, self-paid |   292758 |   298816 |   141089 |    33547 |        0 |    35768
op2 self-paid           |   117317 |   124299 |        0 |    22929 |        0 |    35768
op3 paymaster           |   114264 |   120699 |        0 |    11425 |      498 |    35768
EOA transfer (baseline) |    21000 |
Assertions: PASS
```

</details>

<br>

1 段目では、作る前のアカウントのアドレスを 3 通りで計算しています。`CREATE2` の式、Factory の `getAddress`、EntryPoint の `getSenderAddress` です。3 つは一致し、そのアドレスはコードが空のまま 0.1 ETH を受け取りました。

```text
CREATE2 formula      : 0xD34A413E5659cCDc5f14B5DDb5e8c3C232E4EA21
factory.getAddress   : 0xD34A413E5659cCDc5f14B5DDb5e8c3C232E4EA21
getSenderAddress     : 0xD34A413E5659cCDc5f14B5DDb5e8c3C232E4EA21
code before          : 0x  balance: 0.1 ETH
```

2 段目は、署名した後に送金額を 0.01 ETH から 1 ETH に書き換えた場合と、所有者以外の鍵で署名した場合です。どちらもチェーンには送らず、`handleOps` を `eth_call`（トランザクションを出さずに実行だけを試す呼び出し）で試しています。どちらも検証で `AA24 signature error` になり、アカウントは作られません。ちなみに、`AA2` で始まるコードはアカウントの検証での失敗を表します。

```text
value changed after signing : FailedOp(0, "AA24 signature error")
signed by another key       : FailedOp(0, "AA24 signature error")
```

<br>

3 段目では、このアカウントから 3 件の UserOperation を順に送ります。op1 は `initCode` 付きでアカウントを作り、手数料を自分で払います。op2 は作成済みのアカウントが自分で払い、op3 は Paymaster に払わせます。どれも 0.01 ETH の送金です。

op1 の後、同じアドレスに 141 バイトのコード（OpenZeppelin の [ERC1967Proxy](https://github.com/OpenZeppelin/openzeppelin-contracts/blob/v5.1.0/contracts/proxy/ERC1967/ERC1967Proxy.sol)）が置かれました。SimpleAccount の本体は Factory が作った別のアドレスにあり、アカウントのアドレスにあるのは、処理を本体に委ねる[プロキシ](../upgradeable-proxy/)です。

3 段目の結果では、所有者の EOA の残高は全ての行で 0 のままです。op1 と op2 では、アカウントの残高と deposit の合計が、送金額に加えて手数料（op1 は、`preVerificationGas` を含めて UserOperation に請求された 298,816 gas × 2 gwei = 597,632 gwei）だけ減りました。op3 では、アカウントは送金額しか減らず、手数料は Paymaster の deposit から引かれています。

以下は、3 段目の UserOperation の手数料と、Bundler 自身が払ったトランザクションのガス代を並べたグラフです。手数料の棒は、払った主体で色を分けています。

{{< figure src="images/erc-4337_fees.webp" alt="op1・op2・op3 の 3 組の横棒。上の棒は UserOperation の手数料で、op1 は 597,632、op2 は 248,598 で青（アカウントが払う）、op3 は 241,398 で黄土色（Paymaster が払う）。下の灰色の棒は Bundler 自身のトランザクションのガス代で、585,516・234,634・228,528。単位は gwei" caption="op1〜op3 の手数料の出どころと Bundler の出費（gwei）" align="center" >}}

上の棒の額は、そのまま EntryPoint が Bundler に払った額です。どの行も、Bundler は自分が送るトランザクションのガス代（図の灰色の棒）を ETH で払い、それより 12,000〜14,000 gwei ほど多い額を受け取っています。差額は、実験で `preVerificationGas` に置いた 50,000 が、EntryPoint の測れない部分より大きかったからです。

以下は、4 段目のガスを処理ごとに分けたグラフです。

{{< figure src="images/erc-4337_gas.webp" alt="トランザクションのガスを横棒で比べた図。op1（作成・自分で払う）は 292,758 で、アカウントの作成が 141,089 を占める。op2（自分で払う）は 117,317、op3（Paymaster）は 114,264 で、どちらも検証・実行・EntryPoint などの残りに分かれる。EOA の送金は 21,000" caption="トランザクション 1 件に掛かるガスの内訳と、EOA の送金との比較" align="center" >}}

作成を含まない op2 でも、EOA の送金の約 5.6 倍、op3 で約 5.4 倍です。実行の 35,768 には、使われていないアドレスに ETH を送る `CALL`（別のアドレスを呼ぶ命令）の追加分 25,000 が含まれます。EOA がトランザクションで同じ送金をする時には、この追加分は掛かりません。op3 の検証が op2 より軽いのは、アカウントが EntryPoint に前払いの ETH を送らないからです。

---

### EIP-7702 との関係

[EIP-7702](https://eips.ethereum.org/EIPS/eip-7702) は、EOA にコントラクトのコードを委任する仕組みです。2025 年 5 月 7 日に、Pectra という名前の Ethereum の[プロトコルの更新](../ethereum-hard-forks/)（[Ethereum Foundation の告知](https://blog.ethereum.org/2025/04/23/pectra-mainnet)）で有効になりました。委任の書き方と nonce の扱いは [Ethereum Account Model](../ethereum-account-model/) で説明しています。ERC-4337 とは競合せず、次のように組み合わせて使います。

| | ERC-4337 だけ | EIP-7702 で委任した EOA |
| --- | --- | --- |
| アドレス | 新しいアカウントのアドレス。資産の移動が必要 | 今の EOA のアドレスのまま |
| 鍵の扱い | 所有者の鍵や承認の条件はアカウントのコードが決め、差し替えもできる | EOA の元の秘密鍵が、委任後もトランザクションに署名でき、委任先も変えられる |
| 変わる層 | コントラクトと別の mempool だけ | プロトコル（新しいトランザクションの型） |

EntryPoint v0.8 以降は、委任済みの EOA を UserOperation の送り主として扱えます。`initCode` の先頭 20 バイトを `0x7702` で始まる目印の値にすると、EntryPoint は委任先のアドレスを `userOpHash` に含めます。

Bundler は、UserOperation に付いた委任の承認（委任を許す EOA の署名、authorization）を EIP-7702 で定めたトランザクションの型で一緒に送ります。EOA でも Paymaster と Bundler の仕組みを使えるようになる一方で、元の鍵が漏れると、委任先のコードに関係なく資産を動かされる点は変わりません。

---

### 利点

- プロトコルを変えずに、署名の方式・複数人の承認・鍵の差し替えをアカウントごとに決められる
- Paymaster で、ETH を持たない利用者の手数料を肩代わりできる
- アドレスを先に配り、最初の操作の時にアカウントを作れる
- 検証の規則を守る限り、誰でも Bundler になれる

---

### 欠点

- 同じ送金でも、EOA より多くのガスを使う（実験では作成なしで約 5.4〜5.6 倍）
- Bundler・mempool・Paymaster という、トランザクションの外にある仕組みに頼る
- 全てのアカウントが EntryPoint を信頼するので、EntryPoint の欠陥が全体に及ぶ
- 検証のコードに ERC-7562 の制限が掛かる。ブロックの時刻は直接読めず、有効期間を EntryPoint に返す形でしか条件にできない（詳細は ERC-7562 のノート）。他のコントラクトの状態を広く読むには、ETH をステーク（stake）として預ける必要がある

---

### 適さないケース

- 1 つの鍵で ETH を送るだけで、承認の方式も手数料の肩代わりも使わない場合。EOA の方が安く済む
- 既存の EOA のアドレスを変えずに機能を足したい場合。EIP-7702 の委任を先に検討する
- 検証に外部の価格など、他のコントラクトの変わりやすい状態を使いたい場合。検証ではなく実行の段階で確認する設計にする

---

### 付録: EntryPoint の版

アカウントは信頼する EntryPoint のアドレスをコードに持つので（SimpleAccount では `immutable`）、EntryPoint の版を変えるにはアカウントの更新が必要です。本記事の実験は v0.9.0 を使っています。

<br>

<details>
<summary>v0.6〜v0.9 の主な変更と Mainnet のアドレス</summary>

以下は、eth-infinitism のリリースノート（2026 年 11 月時点、最新は v0.9.0）を元にした比較です。

| バージョン | リリース | 主な変更 | Mainnet のアドレス |
| --- | --- | --- | --- |
| [v0.6](https://github.com/eth-infinitism/account-abstraction/releases/tag/v0.6.0) | 2023 年 4 月 | nonce を EntryPoint で管理、userOpHash の計算を変更 | `0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789` |
| [v0.7](https://github.com/eth-infinitism/account-abstraction/releases/tag/v0.7.0) | 2024 年 2 月 | チェーン上の形式を PackedUserOperation に変更、未使用ガスへの 10% の罰金、検証の規則を ERC-7562 に分離 | `0x0000000071727De22E5E9d8BAf0edAc6f37da032` |
| [v0.8](https://github.com/eth-infinitism/account-abstraction/releases/tag/v0.8.0) | 2025 年 3 月 | EIP-7702 への対応、userOpHash を EIP-712 の形式に変更 | `0x4337084d9e255ff0702461cf8895ce9e3b5ff108` |
| [v0.9](https://github.com/eth-infinitism/account-abstraction/releases/tag/v0.9.0) | 2025 年 11 月 | Paymaster の署名を後から付けられる、既存のアカウントでは initCode を無視 | `0x433709009B8330FDa32311DF1C2AFA402eD8D009` |

v0.6 と v0.7 では構造体の形が違い、[ABI](../evm/#calldata-と-abi)（Application Binary Interface、関数の呼び出し形式）に互換性がありません。v0.9 は v0.7・v0.8 と ABI の互換があり、既存の関数は変えずに関数やイベントを足しています。ただし、v0.8 で userOpHash の計算が変わったので、署名を作る側は合わせる必要があります。

アドレスはリリースノートに載っている値で、v0.9.0 のリリースノートは使う前に監査報告のアドレスとコードのハッシュを確認するよう警告しています。

</details>

<br>
