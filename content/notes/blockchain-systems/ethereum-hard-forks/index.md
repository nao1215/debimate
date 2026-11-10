---
title: "Ethereum Hard Forks - EVM の規則は全ノードで同時に切り替わる"
date: 2026-11-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain", "ethereum", "evm", "hard-fork", "smart-contract"]
weight: 21
wrapTables: true
topics: ["Smart Contract"]
---

[Solidity](https://soliditylang.org/) のコンパイラ（solc）を 0.8.19 から 0.8.20 に上げると、ソースを 1 行も変えていないのに、一部のチェーンでデプロイが失敗することがあります。0.8.20 から、出力するバイトコードに PUSH0 という命令が入るようになったからです。

PUSH0 は 2023 年 4 月の Shanghai というハードフォークで Ethereum に追加された命令で、このフォークの規則に対応していないチェーンでは無効な命令として扱われます。

ハードフォーク（hard fork）は、決めた高さや時刻を境に、ブロックの有効性を判定する規則を変更するプロトコルの更新です。Ethereum では、[EVM](../evm/)（Ethereum Virtual Machine）の命令の追加、ガスの値の変更、命令の意味の変更がハードフォークで入ります。デプロイ済みのコードは書き換わりませんが、そのコードを実行する規則が変わります。

{{< figure src="images/ethereum-hard-forks_concept.svg" alt="上段は 1 本のブロックの列で、Istanbul・Berlin・Cancun の区間の境目に点線がある。Berlin の境目から、更新しなかったノードが古い規則で伸ばす黄土色の列が分かれている。中段は全区間に渡る「同じバイトコード」の帯。下段は区間ごとの値で、SLOAD は Istanbul で 800、Berlin と Cancun で 2100 / 100、SELFDESTRUCT は Istanbul と Berlin で code を消し、Cancun では code を残す。値が変わった区間の箱だけが青い" caption="フォークの境目で同じバイトコードの値段と意味が変わる" align="center" >}}

上記の図の黄土色の列は、更新しなかったノードがあった場合の分岐です。全員が同じ境目で規則を切り替えれば、列は 1 本のまま続きます。

<br>

本記事では、ハードフォークで EVM の何が変わり、開発者のコードにどう影響するのかを説明します。

- ハードフォークは、チェーンが分裂して新しいコインが生まれることなのか。
- 規則の更新は、誰がどのような手順で決めるのか。
- デプロイ済みのコントラクトの振る舞いは、更新で変わるのか。
- 最新の solc でコンパイルしたコードは、どのチェーンでも動くのか。

後半では、フォークを固定したローカルノードで同じバイトコードを実行し、結果の違いを確かめます。合意層だけの変更（PeerDAS など）と、価格や投資の話は扱いません。

---

### 計画された規則の更新

ハードフォークと聞くと、チェーンが 2 つに割れて、新しいコインが生まれる出来事を想像するかもしれません。しかし、Ethereum のハードフォークのほとんどは、開発者とノードの運用者が事前に合意した計画的な更新で、チェーンは 1 本のままです。[ethereum.org の更新の一覧](https://ethereum.org/ethereum-forks/)に並ぶ更新の多くは、分岐を起こしていません。

規則を変える時は、切り替える境目を先に決め、その規則を実装したクライアントを全ノードが事前に入れておきます。

境目は、Paris より前は、2022 年 6 月の更新までブロックの高さで、2022 年 9 月の Paris（The Merge）は PoW の累積の難易度でした。Shanghai 以降はブロックの時刻（timestamp）を使います。[execution-specs の更新履歴](https://github.com/ethereum/execution-specs/blob/873ecb3e982ad4311a91cea5aaf2bbb83d306db1/docs/specs/protocol_history.md)には、例えば London が「ブロック 12965000」、Cancun が「timestamp 1710338135」と記録されています。

更新前のクライアントは、新しい規則で作られたブロックを無効と判定します。PUSH0 を含む取引は、古い規則では実行に失敗し、状態の計算結果が新しい規則のノードと合いません。そのため、更新しないノードは新しい列についていけません。古い規則のノードとの互換性を保つ更新はソフトフォーク（soft fork）と呼ばれ、ハードフォークと区別されます（[ethereum.org の用語集](https://ethereum.org/glossary/#soft-fork)）。

分岐が残るのは、一部の参加者が意図して古い規則を使い続けた時です。2016 年の The DAO の事件の後、資金を移す規則に切り替えたノードと、切り替えなかったノードに分かれ、後者の列は [Ethereum Classic](https://ethereumclassic.org/) として続いています。経緯は [Blockchain Basics](../blockchain-basics/) で説明しています。

---

### 更新を決める手順

Ethereum には、規則の更新を決める管理者がいません。変更の提案は EIP（Ethereum Improvement Proposal）という文書で出し、[EIP-1](https://eips.ethereum.org/EIPS/eip-1) が書式と状態の遷移を定めています。全ノードが同時に切り替える必要がある変更は、Core という分類の EIP です。

どの EIP をどの更新に入れるかは、クライアントの開発者が集まる All Core Devs という公開の会議で議論します。議事録と議題は [ethereum/pm](https://github.com/ethereum/pm) で公開されています。更新ごとに、対象の EIP を並べた Meta EIP があり、[EIP-7723](https://eips.ethereum.org/EIPS/eip-7723) は、EIP が「提案」「検討」「予定」と段階を進める手順を定めています。

{{< note-steps caption="EIP が mainnet で有効になるまで。" >}}
- title: EIP の提出
  body: 変更の仕様を EIP として公開する。
- title: All Core Devs
  body: 検討・予定の段階に進め、対象の更新を決める。
- title: devnet
  body: 複数のクライアントが同じ結果を出すかを試す。
- title: 公開テストネット
  body: Sepolia・Hoodi などで決めた時刻に有効にする。
- title: mainnet
  body: 時刻を設定したクライアントを全ノードが入れ、その時刻で切り替える。
{{< /note-steps >}}

上記の devnet は、更新ごとに作る短期間のテスト用ネットワークです。Ethereum には実装の異なるクライアントが複数あり、同じブロックから同じ状態を計算できなければ、更新の時点でノードの間に分岐が起きます。mainnet の時刻は、通常は[テストネット](../mainnet-and-testnet/#ハードフォークはテストネットから)で問題が出なかったことを確かめてから決めます。

<br>

Ethereum のノードは、取引を実行する実行層（execution layer）のクライアントと、ブロックの合意を担う合意層（consensus layer）のクライアントを組み合わせて動きます。そのため、The Merge 以降の更新には、実行層と合意層の 2 つの名前があります。実行層は Devcon などの開催都市、合意層は恒星の名前で、2 つを組み合わせた通称で呼ばれます。

| 実行層 | 合意層 | 通称 | mainnet で有効になった日（UTC） |
| --- | --- | --- | --- |
| Shanghai | Capella | Shapella | 2023-04-12 |
| Cancun | Deneb | Dencun | 2024-03-13 |
| Prague | Electra | Pectra | 2025-05-07 |
| Osaka | Fulu | Fusaka | 2025-12-03 |

日付は [ethereum.org の更新の一覧](https://ethereum.org/ethereum-forks/)と execution-specs の更新履歴に基づきます。EVM の規則を決めるのは実行層なので、solc や Anvil の設定では Shanghai・Cancun のような実行層の名前を使います。

---

### デプロイ済みのコントラクトに効く変更

コントラクトのコードは、デプロイした後に書き換えられません。それでも振る舞いが変わることがあるのは、変わらないのがバイト列だけで、各命令のガスの値と意味はハードフォークで変わるからです。

以下は、EVM の振る舞いを変えた主な EIP です。全てではなく、本記事の実験と関係する変更を選んでいます。

| フォーク（mainnet） | 主な EIP | 変わったこと |
| --- | --- | --- |
| Istanbul（2019-12） | [EIP-1884](https://eips.ethereum.org/EIPS/eip-1884) | ストレージの値を読む SLOAD 命令を 200 から 800 ガスに値上げ |
| Berlin（2021-04） | [EIP-2929](https://eips.ethereum.org/EIPS/eip-2929)、[EIP-2930](https://eips.ethereum.org/EIPS/eip-2930) | 状態の初回の参照を cold、2 回目以降を warm として別料金に。取引に参照先の一覧（access list）を付けられる |
| London（2021-08） | [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559)、[EIP-3198](https://eips.ethereum.org/EIPS/eip-3198) | ブロックごとに変わる基本料金（base fee）の導入と、その値を読む BASEFEE 命令 |
| Shanghai（2023-04） | [EIP-3855](https://eips.ethereum.org/EIPS/eip-3855) | 0 を積む PUSH0 命令 |
| Cancun（2024-03） | [EIP-1153](https://eips.ethereum.org/EIPS/eip-1153)、[EIP-5656](https://eips.ethereum.org/EIPS/eip-5656)、[EIP-6780](https://eips.ethereum.org/EIPS/eip-6780)、[EIP-4844](https://eips.ethereum.org/EIPS/eip-4844) | 取引の終わりに消える保存領域の TSTORE と TLOAD、メモリをコピーする MCOPY、SELFDESTRUCT の意味の変更、rollup のデータを載せる blob を運ぶ取引 |
| Prague（2025-05） | [EIP-7702](https://eips.ethereum.org/EIPS/eip-7702)、[EIP-7623](https://eips.ethereum.org/EIPS/eip-7623) | 秘密鍵で操作する通常のアカウント（EOA）が、コントラクトのコードに実行を委任できる。calldata の多い取引の下限料金を値上げ |
| Osaka（2025-12） | [EIP-7939](https://eips.ethereum.org/EIPS/eip-7939)、[EIP-7825](https://eips.ethereum.org/EIPS/eip-7825) | 先頭の 0 のビットを数える CLZ 命令。取引 1 件のガス上限を 2 の 24 乗（16,777,216）に制限 |

新しい命令の追加は、ほとんどの場合、既存のコードの意味を変えません。新しい命令に割り当てたバイト値は、それまで実行すると失敗する無効な命令で、通常のコンパイラの出力には含まれないからです。デプロイ済みのコードに効くのは、ガスの値の変更と、既存の命令の意味の変更です。

<br>

#### warm と cold

EIP-2929 は、取引の中で初めて読むストレージの値（cold）を 2100 ガス、同じ取引の中で既に読んだ値（warm）を 100 ガスにしました。ノードのディスクから初めて読み出す処理が重く、ガスの値と実際の負荷が離れていたからです。アカウントの参照にも同じ区別があり、cold は 2600 ガスです。取引の送り主と宛先のアドレス、事前コンパイル済みのコントラクトは、最初から warm として扱われます。

この変更で、同じコードの同じ SLOAD でも、取引の中で何回目に読むかによってガスが変わるようになりました。EIP-2930 の access list に参照先を書いておくと、取引の開始時点で warm になります。代わりに、access list のアドレス 1 件につき 2400 ガス、ストレージのキー 1 件につき 1900 ガスを取引の開始時に払います。

<br>

#### 2300 ガスの transfer

Solidity の `transfer` は、ETH を送る時に、受け取る側のコードに 2300 ガスだけを渡します。[Solidity のドキュメント](https://docs.soliditylang.org/en/v0.8.28/contracts.html#receive-ether-function)は、2300 ガスでは基本的なログを出す程度の処理しかできないと説明しています。再入（reentrancy、呼び出しの途中で同じコントラクトを呼び返すこと）の対策として、この少なさを当てにしたコードもありました。

しかし、この前提はガスの値が変わらないことに依存しています。2019 年の Istanbul で SLOAD が 800 ガスになった時、EIP-1884 は、ストレージを読む受け取り用の関数が 2300 ガスを超える場合があると互換性の節で警告しました。

値下げで壊れかけた例もあります。ストレージに書く SSTORE 命令を安くする [EIP-1283](https://eips.ethereum.org/EIPS/eip-1283) を含む Constantinople は、既存のコントラクトの一部が再入に弱くなる問題が ChainSecurity から報告され、2019 年 1 月の予定の直前に[延期されました](https://blog.ethereum.org/2019/01/15/security-alert-ethereum-constantinople-postponement)。

Solidity 0.8.31 は、`send` と `transfer` に非推奨の警告を出すようになりました。[リリースのお知らせ](https://www.soliditylang.org/blog/2025/12/03/solidity-0.8.31-release-announcement/)は、2300 ガスの設計が「命令の値段が変わらない」という暗黙の前提に立っていたことを理由に挙げ、空のデータで `call` を使うよう勧めています。

<br>

#### SELFDESTRUCT の意味

SELFDESTRUCT は、コントラクトのコードとストレージを消し、残高を指定先に送る命令でした。Cancun の EIP-6780 から、コードとストレージを消すのは、コントラクトを作成したのと同じ取引の中で実行した場合だけになりました。別の取引で実行すると、残高を送って実行を止めるだけで、コードもストレージも残ります。

この変更で、作成先のアドレスを事前に決められる CREATE2 と SELFDESTRUCT を繰り返し、同じアドレスに別のコードを置き直す手法は使えなくなりました。コントラクトを「消して止める」設計も、Cancun 以降はコードが残ったまま呼び出せる状態になります。

<br>

#### EIP-7702 の委任

Prague の EIP-7702 で、EOA のコードの項目に委任先を指すデータを書けるようになりました。仕組みは [Ethereum Account Model](../ethereum-account-model/)、取引の型は [Ethereum Transaction](../ethereum-transaction/) で説明しています。

EVM の命令から見える影響は 2 つあります。委任した EOA に対する EXTCODESIZE は、委任先のコードではなく、委任を表す 23 バイトの大きさを返します。

また、`require(msg.sender == tx.origin)` で呼び出しが取引の最上位であることを確かめ、再入やサンドイッチ攻撃を防ぐ書き方は、成り立たなくなりました。委任した EOA は、取引の送り主のまま、委任先のコードとして他のコントラクトを呼べるからです（EIP-7702 の Rationale と Security Considerations）。

---

### フォークを切り替えた実験

同じバイトコードを複数のフォークで実行し、ここまでの変更を確かめます。実験では、開発用のローカルノードである [Foundry の Anvil](https://getfoundry.sh/anvil/overview) 1.7.1 を 8 個起動し、`--hardfork` で petersburg（EIP-1283 を外した Constantinople）から osaka までを 1 つずつ固定しました。

ノードは Docker の専用のネットワークの中だけで動かし、公開のネットワークには接続しません。取引には Anvil の既定のテスト用アカウントだけを使っています。

バイトコードは、命令を 1 つずつ確かめるために手で組み立てた学習用のもので、監査していません。新しい命令の確認では、コントラクトを作成する時に実行する初期化用コードとして命令を並べ、[`eth_call`](https://ethereum.org/developers/docs/apis/json-rpc/#eth-call) で実行しました。`eth_call` は結果を状態に保存しないので、取引を送らずに命令の可否を試せます。

以下は [lab/probe.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/probe.py) の抜粋です。`rpc(fork, ...)` は、そのフォークの Anvil に JSON-RPC を送る補助関数です。

```python
RETURN_WORD = '60005260206000f3'  # PUSH1 0 MSTORE PUSH1 32 PUSH1 0 RETURN
PROBES = [
    ('BASEFEE', 'London', '48' + RETURN_WORD),
    ('PUSH0', 'Shanghai', '5f' + RETURN_WORD),
    ('TSTORE', 'Cancun', '6007' '6000' '5d' '6000' '5c' + RETURN_WORD),  # TSTORE(0, 7); TLOAD(0)
    ('MCOPY', 'Cancun', '602a600052' '6020' '6000' '6020' '5e' '60206020f3'),  # copy mem[0:32] to mem[32:64]
    ('CLZ', 'Osaka', '6001' '1e' + RETURN_WORD),  # count leading zeros of 1
]
for fork in FORKS:
    for name, _, code in PROBES:
        try:
            value = int(rpc(fork, 'eth_call', {'data': '0x' + code}, 'latest'), 16)
            cells.append(f'ok={value}')
        except RpcError as e:
            cells.append('error')

# GAS, SLOAD(0), GAS, SLOAD(0), GAS. Each gap = PUSH1(3) + SLOAD + POP(2) + GAS(2).
SLOAD_TWICE = '5a' '600054' '50' '5a' '600054' '50' '5a' '604052' '602052' '600052' '60606000f3'
raw = rpc(fork, 'eth_call', {'data': '0x' + SLOAD_TWICE}, 'latest')[2:]
g0, g1, g2 = (int(raw[i:i + 64], 16) for i in range(0, 192, 64))
lines.append(f'{fork:<10} | {g0 - g1 - 7:>9} | {g1 - g2 - 7:>9}')
```

SLOAD のガスは、GAS 命令で残りのガスを SLOAD の前後に記録し、差から間の PUSH1・POP・GAS の 7 ガスを引いて求めています。同じスロットを 2 回読むので、1 回目が cold、2 回目が warm です。

<details>
<summary>probe.py の全体（transfer・SELFDESTRUCT・evmVersion の検査を含む）</summary>

```python
#!/usr/bin/env python3
"""Run the same EVM bytecode on Anvil nodes pinned to different hard forks.

Local-only. Called by run.sh inside a container on a private Docker network.
The bytecode below is hand-assembled for this experiment and is not audited.
"""
import json
import os
from pathlib import Path
import time
import urllib.request

FORKS = os.environ['FORKS'].split()
OUT = Path('output')
BUILD = OUT / 'build'
lines = []


class RpcError(Exception):
    pass


def rpc(fork, method, *params):
    url = f'http://note-ethereum-hard-forks-{fork}:8545'
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    request = urllib.request.Request(url, body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.load(response)
    if 'error' in result:
        raise RpcError(result['error']['message'])
    return result['result']


def wait_ready(fork):
    for _ in range(200):
        try:
            return rpc(fork, 'eth_accounts')
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(fork)


def status(receipt):
    return int(receipt['status'], 16)


def send(fork, tx):
    tx = {'gas': hex(1_000_000), 'gasPrice': hex(2_000_000_000), **tx}
    txhash = rpc(fork, 'eth_sendTransaction', tx)
    for _ in range(100):
        receipt = rpc(fork, 'eth_getTransactionReceipt', txhash)
        if receipt:
            return receipt
        time.sleep(0.05)
    raise TimeoutError(txhash)


def initcode(runtime):
    """Init code that copies `runtime` (hex) into memory and returns it as the deployed code."""
    n = len(runtime) // 2
    assert n < 256
    return f'60{n:02x}600c600039{"60%02x" % n}6000f3' + runtime


def solc_output(name):
    text = (BUILD / name).read_text()
    sections = {}
    key = None
    for line in text.splitlines():
        if line.endswith(':') and not line.startswith(' '):
            key = line[:-1]
        elif key and line.strip():
            sections.setdefault(key, []).append(line.strip())
    return sections


accounts = {f: wait_ready(f) for f in FORKS}

# 1. New opcodes: run init code with eth_call (no `to` = simulated contract creation).
#    Each snippet leaves one 32-byte word in memory[0:32] and returns it.
RETURN_WORD = '60005260206000f3'  # PUSH1 0 MSTORE PUSH1 32 PUSH1 0 RETURN
PROBES = [
    ('BASEFEE', 'London', '48' + RETURN_WORD),
    ('PUSH0', 'Shanghai', '5f' + RETURN_WORD),
    ('TSTORE', 'Cancun', '6007' '6000' '5d' '6000' '5c' + RETURN_WORD),  # TSTORE(0, 7); TLOAD(0)
    ('MCOPY', 'Cancun', '602a600052' '6020' '6000' '6020' '5e' '60206020f3'),  # copy mem[0:32] to mem[32:64]
    ('CLZ', 'Osaka', '6001' '1e' + RETURN_WORD),  # count leading zeros of 1
]
lines.append('== opcode probes (eth_call of init code) ==')
lines.append('fork       | ' + ' | '.join(name for name, _, _ in PROBES))
errors = set()
for fork in FORKS:
    cells = []
    for name, _, code in PROBES:
        try:
            value = int(rpc(fork, 'eth_call', {'data': '0x' + code}, 'latest'), 16)
            cells.append(f'ok={value}')
        except RpcError as e:
            errors.add(str(e))
            cells.append('error')
    lines.append(f'{fork:<10} | ' + ' | '.join(cells))
lines.append('error messages: ' + '; '.join(sorted(errors)))

# 2. SLOAD gas: GAS, SLOAD(0), GAS, SLOAD(0), GAS. Each gap = PUSH1(3) + SLOAD + POP(2) + GAS(2).
SLOAD_TWICE = '5a' '600054' '50' '5a' '600054' '50' '5a' '604052' '602052' '600052' '60606000f3'
lines.append('')
lines.append('== SLOAD of the same slot twice in one call ==')
lines.append('fork       | 1st SLOAD | 2nd SLOAD')
for fork in FORKS:
    raw = rpc(fork, 'eth_call', {'data': '0x' + SLOAD_TWICE}, 'latest')[2:]
    g0, g1, g2 = (int(raw[i:i + 64], 16) for i in range(0, 192, 64))
    lines.append(f'{fork:<10} | {g0 - g1 - 7:>9} | {g1 - g2 - 7:>9}')

# 3. Solidity transfer() forwards 2300 gas. The receiver reads 3 storage slots on receipt.
RECEIVER = '600054' '50' '600154' '50' '600254' '50' '00'  # SLOAD(0), SLOAD(1), SLOAD(2), STOP
sender = solc_output('Sender.txt')
sender_bin = sender['Binary'][0]
pay = next(h.split(':')[0] for h in sender['Function signatures'] if h.endswith('pay(address)'))
lines.append('')
lines.append('== transfer(1 wei) to a receiver that reads 3 slots ==')
lines.append('fork       | plain tx | with access list')
for fork in FORKS:
    me = accounts[fork][0]
    receiver = send(fork, {'from': me, 'data': '0x' + initcode(RECEIVER)})['contractAddress']
    contract = send(fork, {'from': me, 'data': '0x' + sender_bin})['contractAddress']
    call = {'from': me, 'to': contract, 'value': '0x1', 'data': '0x' + pay + receiver[2:].lower().rjust(64, '0')}
    plain = status(send(fork, call))
    if fork in ('petersburg', 'istanbul'):
        listed = '-'  # access lists (EIP-2930) start at Berlin
    else:
        slots = ['0x' + f'{i:064x}' for i in range(3)]
        listed = status(send(fork, {**call, 'accessList': [{'address': receiver, 'storageKeys': slots}]}))
    lines.append(f'{fork:<10} | {plain:<8} | {listed}')

# 4. SELFDESTRUCT in a later transaction than the one that created the contract.
SELF_DESTRUCT = '33ff'  # CALLER SELFDESTRUCT
lines.append('')
lines.append('== SELFDESTRUCT called in a later transaction ==')
lines.append('fork       | code before | code after | balance after')
for fork in FORKS:
    me = accounts[fork][0]
    target = send(fork, {'from': me, 'value': hex(1000), 'data': '0x' + initcode(SELF_DESTRUCT)})['contractAddress']
    before = rpc(fork, 'eth_getCode', target, 'latest')
    assert status(send(fork, {'from': me, 'to': target})) == 1
    after = rpc(fork, 'eth_getCode', target, 'latest')
    balance = int(rpc(fork, 'eth_getBalance', target, 'latest'), 16)
    lines.append(f'{fork:<10} | {before:<11} | {after:<10} | {balance}')

# 5. The same Solidity source compiled for different evmVersion values.
lines.append('')
lines.append('== Copy.sol compiled with solc --evm-version ==')
lines.append('evmVersion | bytes | PUSH0 | MCOPY | deploy: london | shanghai | cancun')
for version in ('paris', 'shanghai', 'cancun'):
    out = solc_output(f'Copy.{version}.txt')
    code = out['Binary'][0]
    ops = out['Opcodes'][0].split()
    statuses = []
    for fork in ('london', 'shanghai', 'cancun'):
        statuses.append(str(status(send(fork, {'from': accounts[fork][0], 'data': '0x' + code}))))
    lines.append(f'{version:<10} | {len(code) // 2:>5} | {ops.count("PUSH0"):>5} | {ops.count("MCOPY"):>5} | '
                 + ' | '.join(statuses))
for version in ('shanghai', 'cancun'):
    text = (BUILD / f'Guard.{version}.txt').read_text()
    result = 'compiled' if 'Binary:' in text else next(l for l in text.splitlines() if l.strip())
    lines.append(f'Guard.sol (transient) with {version}: {result}')

summary = '\n'.join(lines) + '\n'
(OUT / 'summary.txt').write_text(summary)
print(summary, end='')
```

</details>

コンテナの起動から後始末までは [lab/run.sh](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/run.sh) が行います。リポジトリのルートで次を実行すると、約 10 秒で終わり、全てのコンテナとネットワークを削除します。使ったイメージは ghcr.io/foundry-rs/foundry:v1.7.1、ethereum/solc:0.8.28、python:3.13-slim で、digest は [output/versions.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/output/versions.txt) に残しています。

```bash
bash content/notes/blockchain-systems/ethereum-hard-forks/lab/run.sh
```

フォークごとの命令の可否と、同じスロットを 2 回読んだ SLOAD のガスは、以下の通りです。

{{< figure src="images/ethereum-hard-forks_opcodes.svg" alt="行がフォーク（petersburg から osaka）、列が BASEFEE・PUSH0・TSTORE・MCOPY・CLZ と SLOAD の 1 回目・2 回目。BASEFEE は london から、PUSH0 は shanghai から、TSTORE と MCOPY は cancun から、CLZ は osaka から ok で、それより前は error。SLOAD は petersburg で 200 / 200、istanbul で 800 / 800、berlin 以降は 2100 / 100" caption="同じバイトコードを 8 つのフォークで実行した結果" align="center" >}}

<details>
<summary>命令の可否と SLOAD のガスの出力</summary>

```text
== opcode probes (eth_call of init code) ==
fork       | BASEFEE | PUSH0 | TSTORE | MCOPY | CLZ
petersburg | error | error | error | error | error
istanbul   | error | error | error | error | error
berlin     | error | error | error | error | error
london     | ok=1000000000 | error | error | error | error
shanghai   | ok=1000000000 | ok=0 | error | error | error
cancun     | ok=1000000000 | ok=0 | ok=7 | ok=42 | error
prague     | ok=1000000000 | ok=0 | ok=7 | ok=42 | error
osaka      | ok=1000000000 | ok=0 | ok=7 | ok=42 | ok=255
error messages: EVM error NotActivated

== SLOAD of the same slot twice in one call ==
fork       | 1st SLOAD | 2nd SLOAD
petersburg |       200 |       200
istanbul   |       800 |       800
berlin     |      2100 |       100
london     |      2100 |       100
shanghai   |      2100 |       100
cancun     |      2100 |       100
prague     |      2100 |       100
osaka      |      2100 |       100
```

全体は [summary.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/output/summary.txt) にあります。

</details>

各命令は、追加されたフォークより前では `NotActivated`（上記の図の error）で失敗し、追加されたフォーク以降では同じ値を返しました。SLOAD は Istanbul で 4 倍になり、Berlin から 1 回目と 2 回目で 21 倍の差が付いています。

<br>

次に、受け取る側のコードを変えずに、Solidity の `transfer` で 1 wei を送る取引を各フォークで送りました。受け取る側は、ETH を受け取るとストレージを 3 か所読むだけのコードです。送る側の [Sender.sol](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/Sender.sol) は `payable(to).transfer(msg.value)` を呼ぶだけで、全てのフォークで動くように evmVersion を petersburg にしてコンパイルしています。

受け取る側が 3 か所を読むのに要るガスは、以下の通りです。棒の長さは、上記で測った SLOAD のガスの 3 倍です。

{{< figure src="images/ethereum-hard-forks_transfer.svg" alt="横棒グラフ。受け取る側の SLOAD 3 回のガスは、petersburg が 600 で成功、istanbul が 2,400 で失敗、berlin から osaka が 6,300 で失敗、access list を付けると 300 で成功。2300 の位置に transfer が渡すガスの点線がある" caption="SLOAD 3 回のガスと transfer が渡す 2300 ガス" align="center" >}}

<details>
<summary>transfer の出力（status の 1 は成功、0 は失敗）</summary>

```text
== transfer(1 wei) to a receiver that reads 3 slots ==
fork       | plain tx | with access list
petersburg | 1        | -
istanbul   | 0        | -
berlin     | 0        | 1
london     | 0        | 1
shanghai   | 0        | 1
cancun     | 0        | 1
prague     | 0        | 1
osaka      | 0        | 1
```

</details>

petersburg で成功した送金が、同じバイトコードのまま istanbul 以降で失敗しました。SLOAD の値上げで、3 回の読み出しが 2300 ガスに収まらなくなったからです。Berlin 以降は、3 つのスロットを access list に書くと warm になり、送金が再び成功しました。

<br>

SELFDESTRUCT の結果では、デプロイとは別の取引で `CALLER SELFDESTRUCT`（0x33ff）を実行しています。残高はどのフォークでも送り出されて 0 になりましたが、コードは shanghai まで消え、cancun 以降は残りました。以下は、境目の 2 つのフォークの[出力](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/output/summary.txt)です。

```text
== SELFDESTRUCT called in a later transaction ==
fork       | code before | code after | balance after
shanghai   | 0x33ff      | 0x         | 0
cancun     | 0x33ff      | 0x33ff     | 0
```

---

### solc の evmVersion

最新の solc でコンパイルすれば、どのチェーンでも動くと考えがちです。しかし、solc はどのフォークの命令を使うかを evmVersion という設定で決めており、既定値は solc のバージョンごとに新しいフォークに上がってきました。[Solidity の Changelog](https://github.com/argotorg/solidity/blob/v0.8.38/Changelog.md) によると、既定値は次のように変わっています。

| solc | 既定の evmVersion |
| --- | --- |
| 0.8.20（2023-05） | shanghai |
| 0.8.25（2024-03） | cancun |
| 0.8.30（2025-05） | prague |
| 0.8.31（2025-12） | osaka |

[0.8.20 のリリースのお知らせ](https://soliditylang.org/blog/2023/05/10/solidity-0.8.20-release-announcement/)も、PUSH0 にまだ対応していない L2（[Rollup](../rollup/) など、Ethereum の上で動く別のチェーン）などにデプロイする場合は、適切な EVM のバージョンを選ばないとデプロイが失敗すると注意しています。

対応するフォークはチェーンごとに異なるので、デプロイ先が対応しているフォークを確かめ、solc の `--evm-version`（standard JSON では `settings.evmVersion`）で指定します（[Solidity のドキュメント](https://docs.soliditylang.org/en/v0.8.28/using-the-compiler.html#setting-the-evm-version-to-target)）。

実験では、solc 0.8.28 で 3 つの evmVersion を指定し、`bytes.concat` で 2 つのバイト列を連結するだけの [Copy.sol](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/Copy.sol) をコンパイルしました。できたバイトコードは、それぞれ london・shanghai・cancun の Anvil にデプロイしています。

```text
== Copy.sol compiled with solc --evm-version ==
evmVersion | bytes | PUSH0 | MCOPY | deploy: london | shanghai | cancun
paris      |   900 |     0 |     0 | 1 | 1 | 1
shanghai   |   869 |    38 |     0 | 0 | 1 | 1
cancun     |   843 |    37 |     1 | 0 | 1 | 1
Guard.sol (transient) with shanghai: Error: Transient storage is not supported by EVM versions older than cancun.
Guard.sol (transient) with cancun: compiled
```

同じソースでも、shanghai 向けには PUSH0 が 38 個入り、cancun 向けにはバイト列の連結に MCOPY が使われました。新しい命令を使う分だけバイトコードは小さくなりますが、shanghai 向けと cancun 向けのコードは london のノードでデプロイに失敗します。

一方で、cancun 向けのコードは shanghai のノードでもデプロイに成功しました。MCOPY は実行用のコードにだけあり、デプロイ時の初期化用コードでは実行されないからです。この場合は、`twice` を呼んだ時に初めて失敗します。

ソースに `transient` の変数（TSTORE と TLOAD を使う保存領域）を書いた [Guard.sol](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/Guard.sol) は、cancun より古い evmVersion ではコンパイルの時点でエラーになりました。一方で、`bytes.concat` のように同じ処理を古い命令でも書ける場合は、エラーにならずに命令だけが変わり、デプロイか、関数を呼んだ時に初めて気付くことになります。

---

### 今後の予定

2026 年 11 月 10 日時点で、mainnet で最後に有効になった、名前の付いた更新は Osaka/Fulu（Fusaka、2025-12-03）です。その後の 2025 年 12 月 9 日と 2026 年 1 月 7 日には、blob の数の目標と上限などのパラメータだけを変える BPO（Blob Parameter Only）フォークが有効になりました（[EIP-7607](https://eips.ethereum.org/EIPS/eip-7607)、[EIP-7892](https://eips.ethereum.org/EIPS/eip-7892)）。

次の更新は、実行層が Amsterdam、合意層が Gloas で、通称は Glamsterdam です。Meta EIP の [EIP-7773](https://github.com/ethereum/EIPs/blob/f1ade090fd315895461fc3e249cb1a675aeb55a9/EIPS/eip-7773.md)（2026-10-22 のコミット）には、テストネットの [Sepolia](https://github.com/eth-clients/sepolia) で 2026-10-06、[Hoodi](https://github.com/eth-clients/hoodi) で 2026-10-26 に有効になる時刻が書かれ、mainnet の時刻は空欄です。

ただし Hoodi の予定は、[ACDE #248](https://github.com/ethereum/pm/issues/2267) で議論されたセキュリティ上の懸念を受けて保留になり、クライアントは予定を取り除いたリリースを出しました（例: [Nethermind 2.2.1](https://github.com/NethermindEth/nethermind/releases/tag/2.2.1)、2026-10-22）。2026 年 11 月 10 日時点で、新しい日付は決まっていません。

同じ Meta EIP の予定（Scheduled for Inclusion）には、実行層に関わる次の EIP が含まれています。

- [EIP-8038](https://eips.ethereum.org/EIPS/eip-8038): cold のアカウント参照などの、状態の参照のガスを値上げ
- [EIP-8246](https://eips.ethereum.org/EIPS/eip-8246): SELFDESTRUCT で ETH が消える残りの場合をなくす
- [EIP-7954](https://eips.ethereum.org/EIPS/eip-7954): コントラクトのコードの上限を 24,576 バイトから 65,536 バイトに拡大
- [EIP-7928](https://eips.ethereum.org/EIPS/eip-7928): ブロック単位で参照した状態の一覧を持つ Block-Level Access Lists

内容と時期は Meta EIP の更新で変わります。最新の状態は、Meta EIP と [execution-specs の更新履歴](https://github.com/ethereum/execution-specs/blob/873ecb3e982ad4311a91cea5aaf2bbb83d306db1/docs/specs/protocol_history.md)で確かめてください。

<br>

ガスの値は、ノードの負荷に合わせて今後も見直される対象です。コントラクトの中で特定のガスの値を前提にした分岐や上限を書くと、その前提はハードフォーク 1 回で崩れます。デプロイ先が対応するフォークを確かめて evmVersion を指定し、ガスの値を固定値として扱わないことが、規則が変わり続けるチェーンでコードを長く動かす前提になります。
