---
title: "Ethereum Address - アドレスの決まり方"
date: 2026-11-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain", "ethereum", "address", "create2", "smart-contract"]
weight: 15
wrapTables: true
topics: ["Transaction / Wallet"]
---

[Ethereum](https://ethereum.org/) のアドレスは、送金の宛先やプログラムの呼び出し先を指す 20 バイトの値で、`0xf39Fd6e5…` のような 16 進の文字列で書きます。銀行の口座番号と違い、誰かに申請して払い出してもらう番号ではありません。手元にある材料から、誰でも同じ計算で求められます。

アドレスを持つアカウントには 2 種類あります。秘密鍵で署名して操作する EOA（Externally Owned Account）と、チェーン上で動くプログラムを持つコントラクト（[スマートコントラクト](../smart-contract/)）です。コントラクトの作り方にも、`CREATE` と、作る前にアドレスを決められる `CREATE2` の 2 つがあります。そのため、アドレスを計算する規則は EOA・`CREATE`・`CREATE2` の 3 つです。

<br>

ここでのチェーンは、トランザクションの記録を多数のコンピュータ（ノード）で共有するブロックチェーンのことです。Ethereum の本体のほかに、テスト用のチェーンや、Ethereum と同じ規則で動く別のチェーンがあり、[chain ID](../mainnet-and-testnet/#ethereum-の-chain-id-と-network-id) という番号で区別します（Ethereum の本体は 1）。

<br>

以下は、3 つの規則の材料と、材料に入らない chain ID の関係を示した図です。図の nonce は送り手がそれまでに出したトランザクションなどの数、salt は作り手が選ぶ 32 バイトの値、initcode はコントラクトを作る時に 1 度だけ動くプログラムで、それぞれの節で説明します。

{{< figure src="images/ethereum-address_concept.webp" alt="EOA は公開鍵 64 バイト、CREATE は送り手と nonce、CREATE2 は ff・送り手・salt・initcode のハッシュを keccak256 に入れ、下位 20 バイトがアドレスになる。アドレスの下にはチェーン A（コード X がある）とチェーン B（空か別のコード）の 2 つの枠が並ぶ。chain ID は署名に入り、keccak256 に向かう点線には赤い × が付いている" caption="3 つの規則の材料と、材料に入らない chain ID" align="center" >}}

どの規則にも chain ID は入りません。そのため、同じ材料からは、どのチェーンでも同じアドレスが計算されます。しかし、そのアドレスにどのコードがあるかは、図のチェーン A と B のように、チェーンごとに別々に記録されます。

<br>

本記事では、3 つの規則を順に説明し、どういう時に同じアドレスになり、どういう時に別のアドレスになるのか、手元で動かした 3 つのチェーンで確認します。最後に、Ethereum では自分のコントラクトだったアドレスが、別のチェーンでは第三者のものになった 2022 年の事故を紹介します。

アカウントが持つ状態と nonce は [Ethereum Account Model](../ethereum-account-model/)、送り手を署名から求める流れは [Ethereum Transaction](../ethereum-transaction/) で説明しています。同じアドレスにあるコードが後から差し替わるかどうかは、[Metamorphic Contract](../metamorphic-contract/) で扱います。

---

### 計算でアドレスを求める理由

誰でも参加できるネットワークには、アドレスを発行する窓口がありません。[Digital Signature](../digital-signature/) で説明したように、鍵ペアは誰の許可も無しに手元で作れ、作った瞬間からそのアドレスで Ethereum の通貨 ETH を受け取れます。コントラクトのアドレスも、トランザクションを実行した全てのノードで一致しなければなりません。

そのため、どの規則も、材料を [keccak256](https://ethereum.github.io/yellowpaper/paper.pdf) という[ハッシュ関数](../hash-function/)に通し、32 バイトの結果の下位 20 バイトを取ります。材料が 1 ビットでも違えば別のアドレスになり、材料が同じなら、いつどこで計算しても同じアドレスになります。つまり、同じアドレスになるかどうかは、材料に何が入っているかで判断できます。

ちなみに、Ethereum の keccak256 は標準化される前の [Keccak](https://keccak.team/keccak.html) で、米国の標準化機関 NIST が定めた [SHA3-256](https://csrc.nist.gov/pubs/fips/202/final) とは詰め物（padding）の 1 バイトが違います。Python の [`hashlib.sha3_256`](https://docs.python.org/3/library/hashlib.html#hashlib.sha3_256) で計算すると別の値になります。

---

### EOA のアドレス

EOA のアドレスは、次の手順で公開鍵から計算します（[ethereum.org のアカウントの説明](https://ethereum.org/en/developers/docs/accounts/)）。

1. 32 バイトの秘密鍵から、楕円曲線 [secp256k1](https://www.secg.org/sec2-v2.pdf) の上の点として公開鍵を求める。
2. 公開鍵の x 座標と y 座標（各 32 バイト、合わせて 64 バイト）を keccak256 に通す。
3. 結果の下位 20 バイトをアドレスにする。

材料は秘密鍵から求まる公開鍵だけで、chain ID は入りません。アドレスはチェーンごとに違うと思われがちですが、EOA については誤りです。同じ秘密鍵は、Ethereum の上に作られた別のチェーンである [L2](../rollup/) でも、コントラクトを動かす仮想マシン [EVM](../evm/)（Ethereum Virtual Machine）を同じ規則で備えたチェーン（EVM 互換チェーン）でも、同じアドレスになります。

chain ID が入るのはトランザクションの署名です。2016 年の [EIP-155](https://eips.ethereum.org/EIPS/eip-155)（EIP は Ethereum の仕様変更の提案）以降の形式で作ったトランザクションは、署名する対象に chain ID を含めます。アドレスはチェーンをまたいで共通で、あるチェーン向けのトランザクションを別のチェーンに流す[リプレイ（replay）](../replay-protection/)は署名で防ぐのです。

[Wallet](../wallet/) で確認した通り、残高はチェーンごとに別です。それでも、どのチェーンでも同じ秘密鍵が操作するので、EOA の持ち主は変わりません。

<br>

#### 大文字と小文字の混ざった表記

`0xf39Fd6e5…` のように大文字と小文字が混ざっているのは、[EIP-55](https://eips.ethereum.org/EIPS/eip-55) のチェックサムです。小文字の 16 進表記を keccak256 に通し、対応するハッシュの桁が 8 以上の英字を大文字にします。打ち間違えると大文字の位置が合わなくなるので、ウォレットが検出できます。表記の違いだけで、全て小文字の `0xf39fd6e5…` も同じ 20 バイトの値です。

---

### CREATE のアドレス

EOA のトランザクションでコントラクトを作る時と、コントラクトが `CREATE` 命令で別のコントラクトを作る時は、送り手のアドレスと nonce から計算します。

```text
address = keccak256(rlp([sender, nonce]))[12:]
```

`[12:]` は、32 バイトのハッシュの 13 バイト目以降、つまり下位 20 バイトを取る意味です。[RLP](https://ethereum.org/en/developers/docs/data-structures-and-encoding/rlp/)（Recursive Length Prefix）は、Ethereum がデータを並べる時の符号化の形式です。`nonce` は作る時点の送り手の nonce で、EOA なら送ったトランザクションの件数です。コントラクトの nonce は [EIP-161](https://eips.ethereum.org/EIPS/eip-161) により 1 から始まり、`CREATE` のたびに 1 増えます。

材料にコードは入っていません。そのため、同じコードをデプロイしても、同じ EOA が先に送金を 1 件済ませていれば nonce が進み、別のアドレスになります。逆に、送り手と nonce が同じなら、中身が全く違うコントラクトでも同じアドレスになります。

---

### CREATE2 のアドレス

`CREATE2` は、2019 年の Ethereum の仕様の更新（[Constantinople](https://ethereum.org/en/history/#constantinople)）で追加された命令です（仕様は [EIP-1014](https://eips.ethereum.org/EIPS/eip-1014)）。nonce の代わりに salt と initcode から計算します。

```text
address = keccak256(0xff ‖ sender ‖ salt ‖ keccak256(initcode))[12:]
```

`‖` はバイト列の連結です。`sender` は `CREATE2` を実行するコントラクトで、本記事ではファクトリ（コントラクトを作るためのコントラクト）と呼びます。`salt` はファクトリが選ぶ 32 バイトの値です。

initcode は、デプロイの時に 1 度だけ実行され、置くコードを返すプログラムで、[Solidity](https://soliditylang.org/) ではコンストラクタの引数も末尾に付きます。先頭の `0xff` は、`CREATE` の RLP が `0xff` で始まらないこと（アドレスと nonce の短いリストなので、先頭は `0xc0`〜`0xf7`）を使って、2 つの規則のアドレスが重ならないようにしています。

nonce が入らないので、デプロイする前にアドレスが分かります。[ERC-4337](../erc-4337/) のスマートアカウント（コントラクトで作るウォレット）は、この性質を使って、作る前のアドレスで ETH を受け取ります。

<br>

#### 同じアドレスになる条件

式の材料のうち、コードに関わるのは initcode のハッシュだけで、ほかに salt とファクトリのアドレスが入ります。そのため、同じコードでも salt が違えば別のアドレスで、コンストラクタの引数が違えば initcode が変わり、やはり別のアドレスです。チェーンをまたいで同じアドレスにするには、ファクトリも両方のチェーンで同じアドレスにある必要があります。

そのために広く使われているのが [deterministic-deployment-proxy](https://github.com/Arachnid/deterministic-deployment-proxy) で、ファクトリは多くのチェーンで `0x4e59b448…` に置かれています。

署名は r・s・v の 3 つの値からなり、署名とトランザクションの中身から送り手の公開鍵を逆算できます（[Ethereum Transaction](../ethereum-transaction/)）。普通は秘密鍵から署名を作りますが、deterministic-deployment-proxy は逆に、r と s に固定の値を置いた署名を先に決め、そこから送り手を逆算しています。そのため、この送り手の秘密鍵は誰も知らず、送り手が出せるのは nonce 0 のこのトランザクション 1 件だけです。

署名は `v` が 27 の、chain ID を含まない古い形式です。そのため、chain ID の無いトランザクションを受け付けるチェーンなら、どこに流しても送り手と nonce 0 が同じになり、ファクトリは同じアドレスにできます。

以下は、その仕組みを 3 つのチェーンに並べた図です。

{{< figure src="images/ethereum-address_ddproxy.webp" alt="左に「署名済みのトランザクション 1 件、chain ID なし（v=27）、送り手の秘密鍵は誰も知らない」の箱。そこから Ethereum・チェーン X・チェーン Y の 3 本に矢印が伸び、どれも送り手の nonce 0 でファクトリ 0x4e59b448… ができ、その先の CREATE2 の作成先もどのチェーンでも同じになる" caption="1 件のトランザクションを各チェーンに流して、ファクトリを同じアドレスに置く" align="center" >}}

計算したアドレスに既にコードがあるか、nonce が 0 でない場合、作成は失敗します。同じ salt と initcode で 2 度はデプロイできません。ただし、2024 年 3 月までは、コントラクトを消してから作り直すことで、同じアドレスに別のコードを置けました。この手法は [Metamorphic Contract](../metamorphic-contract/) で説明しています。

なお、本記事の式は Ethereum のものです。[ZKsync の EraVM](https://docs.zksync.io/zksync-protocol/differences/evm-instructions) のように、EVM 互換をうたうチェーンでも `CREATE` と `CREATE2` を別の式で計算するものがあります。

---

### ローカルでの計算と照合

3 つの規則を外部のライブラリ無しの Python で書き、手元で動かしたチェーンのアドレスと照合しました。チェーンには [Anvil](https://getfoundry.sh/anvil/overview/) を使います。Anvil は、開発用に PC の中だけで動く Ethereum のノードで、起動時の chain ID を指定でき、テスト用のアカウントと秘密鍵を最初から用意しています。

Anvil と Solidity のコンパイラは Docker のコンテナで動かし、コンテナはネットワーク無しで起動します。秘密鍵は Anvil が公開している既定のテスト用の鍵だけを使います。使った版とコンテナのイメージは [README](lab/README.txt) にあります。

以下は [address.py](lab/address.py) の 3 つの規則の抜粋です。`keccak256` と、秘密鍵から公開鍵を求める `public_key` も同じファイルにあります。

```python
def eoa_address(private_key: int) -> bytes:
    x, y = public_key(private_key)
    return keccak256(x.to_bytes(32, 'big') + y.to_bytes(32, 'big'))[-20:]


def _rlp_bytes(b: bytes) -> bytes:
    if len(b) == 1 and b[0] < 0x80:
        return b
    assert len(b) < 56
    return bytes([0x80 + len(b)]) + b


def create_address(sender: bytes, nonce: int) -> bytes:
    # nonce is an RLP integer: 0 is the empty string, no leading zero bytes
    nonce_bytes = nonce.to_bytes((nonce.bit_length() + 7) // 8, 'big')
    payload = _rlp_bytes(sender) + _rlp_bytes(nonce_bytes)
    return keccak256(bytes([0xc0 + len(payload)]) + payload)[-20:]


def create2_address(sender: bytes, salt: bytes, initcode: bytes) -> bytes:
    assert len(sender) == 20 and len(salt) == 32
    return keccak256(b'\xff' + sender + salt + keccak256(initcode))[-20:]
```

<br>

chain ID の違うチェーン A（31337）、B（31338）、C（31339）を起動し、A と C では最初のトランザクションでファクトリを作りました。B では、最初のトランザクションで別のコントラクト（V2）を作り、次のトランザクションでファクトリを作ります。ここでのファクトリは、上記の deterministic-deployment-proxy ではなく、[Address.sol](lab/Address.sol) に書いた自作の `Factory` です。V2 も同じファイルの、ファクトリとは中身の違うコントラクトです。ファクトリは、コンストラクタで値 `v` を受け取る `Child` を `CREATE2` で作ります。

`= python` は、Python の計算と一致したことを示します。`chainId=0x7a69` は 16 進の 31337、`status=0` はトランザクションが失敗したことを示します。手順の全体は [run.py](lab/run.py) にあります。`Address.sol` は学習用に書いたもので、監査していません。以下が[出力](lab/output/summary.txt)の前半です。

```text
== EOA
python      0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
chain 31337 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 (eth_accounts[0])
chain 31338 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 (eth_accounts[0])
chain 31339 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 (eth_accounts[0])
signed for chain A: chainId=0x7a69 tx hash=da4c91867292b5c8…
signed for chain B: chainId=0x7a6a tx hash=4df3855135732adb…
chain B rejects the chain A tx: invalid chain id for signer
== CREATE
chain A nonce 0 Factory 0x5FbDB231… = python
chain B 0x5FbDB231… before: 0 bytes of code
chain B nonce 0 V2      0x5FbDB231… 218 bytes of code
chain B nonce 1 Factory 0xe7f1725E… = python
chain C nonce 0 Factory 0x5FbDB231… = python
== CREATE2 (Child with constructor arg v)
chain A salt=0 v=1 0x66fAc1bd… = python
chain A salt=1 v=1 0x7b80d0f0… = python
chain A salt=0 v=2 0x4a880718… = python
chain B salt=0 v=1 0xbE75Bf11… = python
chain C salt=0 v=1 0x66fAc1bd… = python
chain A salt=0 v=1 again: status=0 (address already used)
```

以下は、出力にあるアドレスをチェーンごとに並べた図です。

{{< figure src="images/ethereum-address_lab.webp" alt="チェーン A（31337）、B（31338）、C（31339）の 3 列。どの列も EOA は 0xf39Fd6e5…。A と C は nonce 0 の作成先 0x5FbDB231… にファクトリがあり、CREATE2 で作った Child（salt=0, v=1）は 0x66fAc1bd…。B は 0x5FbDB231… に V2（別のコード）、nonce 1 の 0xe7f1725E… にファクトリがあり、Child は 0xbE75Bf11… にずれる。A と C の箱は青、B のずれた箱は黄土色" caption="3 つのチェーンでの、同じアドレスとずれたアドレス" align="center" >}}

EOA の段では、3 つのチェーンで同じアドレスが返りました。同じトランザクションでも A 向けと B 向けの署名は別のデータで、A 向けのものを B に流すと拒否されます。

`CREATE` の段では、チェーン B の `0x5FbD…` に最初はコードがありません。そこに nonce 0 で V2 を作ると、チェーン A のファクトリと同じアドレスに、全く別のコードが置かれました。

`CREATE2` の段では、salt を 1 にしても、引数を 2 にしてもアドレスが変わりました。ファクトリの位置が違う B では、salt も引数も同じなのに別のアドレスで、ファクトリが同じ位置にある C では A と同じアドレスです。

---

### チェーンをまたいだアドレスの事故

同じアドレスでも、EOA はどのチェーンでも同じ秘密鍵が操作します。一方、コントラクトの持ち主は、そのチェーンでそのアドレスに誰がコードを置いたかで決まります。

2022 年には、この違いで 2,000 万 OP（[Optimism](https://www.optimism.io/) のトークン）が第三者の手に渡りました。当事者は Optimism と、売買の相手方になって取引を成り立たせる事業者（マーケットメーカー）の Wintermute です。

事故に出てくる Safe は、複数人の署名で資産を動かすコントラクト（[マルチシグ](../safe-multisig/)）です。利用者ごとの Safe は、ProxyFactory というファクトリが作ります。事故の前の状態は次の通りです。

1. 2020 年 11 月、Wintermute は Ethereum で [Safe（当時の Gnosis Safe）](https://github.com/safe-global/safe-contracts/tree/v1.1.1)の ProxyFactory 1.1.1 の `createProxy` を呼び、Safe `0x4f3a120E…cb81` を[作りました](https://etherscan.io/tx/0xd705178d68551a6a6f65ca74363264b32150857a26dd62c27f3f96b8ec69ca01)。`createProxy` は `CREATE` を使うので、このアドレスは ProxyFactory のアドレスと nonce で決まります。
2. 2022 年 5 月、Optimism Foundation は、OP の売買の相手方になること（流動性の提供）を頼んだ Wintermute に 2,000 万 OP を貸し出しました。Wintermute が受け取り先として伝えたのは Ethereum の Safe のアドレスで、Optimism の L2 である OP Mainnet では、そのアドレスに何もありませんでした。

以下は、ここまでの状態と、この後の攻撃を Ethereum と OP Mainnet の 2 本に並べた図です。

{{< figure src="images/ethereum-address_wintermute.webp" alt="上の Ethereum の列では、2019 年に chain ID なしの署名で ProxyFactory を作り、2020 年 11 月にその CREATE で Wintermute の Safe 0x4f3a… ができる。下の OP Mainnet の列では、2022 年 5 月に何も無い 0x4f3a… へ 2,000 万 OP が送られ、6 月 5 日に 2019 年のトランザクションのリプレイで ProxyFactory が同じアドレスにでき、攻撃者が Safe を作り続けて nonce を 2020 年と同じ値へ進め、0x4f3a… に攻撃者の Safe ができる" caption="Ethereum のトランザクションを OP Mainnet でリプレイし、nonce を進めて同じアドレスを取る" align="center" >}}

[Wintermute が Optimism のフォーラムに出した報告](https://gov.optimism.io/t/message-to-optimism-community-from-wintermute/2595)、[rekt.news の解析](https://rekt.news/wintermute-rekt)、チェーン上の記録によると、攻撃は次の 2 段で進みました。

3. 2022 年 6 月 5 日、攻撃者は、2019 年に Ethereum で ProxyFactory を作ったトランザクションを OP Mainnet に流しました。同じ送り手のそれまでのトランザクションも、順に流しています。両方のチェーンに[同じハッシュのトランザクション](https://optimistic.etherscan.io/tx/0x75a42f240d229518979199f56cd7c82e4fc1f1a20ad9a4864c635354b4a34261)が記録されており、chain ID の無い署名だったのでリプレイできたのです。ProxyFactory は Ethereum と同じアドレスにできました。
4. 攻撃者は、自作のコントラクトからこの ProxyFactory を呼び、自分を所有者にした Safe を 1 回のトランザクションで 162 個ずつ作り、nonce を進めました。nonce が 2020 年の時と同じ値に来たところで、`0x4f3a120E…cb81` に[攻撃者の Safe ができ](https://optimistic.etherscan.io/tx/0x00a3da68f0f6a69cb067f09c3f7e741a01636cbc27a84c603b468f65271d415b)、2,000 万 OP を動かせるようになりました。

攻撃者は 100 万 OP を売却した後、6 月 10 日に 1,700 万 OP を Optimism 側に返しました（[The Block の報道](https://www.theblock.co/post/151344/hacker-returns-17-million-op-tokens)）。さらに 100 万 OP は Ethereum の考案者 Vitalik Buterin のアドレスへ送られており、Optimism は回収中としました。売却分を含む 200 万 OP は報奨金として攻撃者に残り、Wintermute が Optimism に補填すると約束しました（[Fortune の報道](https://fortune.com/crypto/2022/06/10/optimism-cryptohacker-returns-majority-funds-vitalik-buterin-ethereum/)）。

<br>

#### 問題と防ぎ方

問題は、Ethereum で自分が管理するコントラクトのアドレスなら、別のチェーンでも自分が管理できる、と扱われたことです。上記の実験のチェーン B で、A のファクトリと同じアドレスに V2 が置けたのは、手順 4 と同じ形です。

<br>

同じ ProxyFactory 1.1.1 には、`CREATE2` を使う `createProxyWithNonce` もあり、所有者を含む初期化の内容のハッシュを salt に入れます。この方法なら、所有者を変えると別のアドレスになるので、攻撃者が自分を所有者にして同じアドレスを作ることはできません。

---

### 利点

アドレスを材料のハッシュで計算する設計から、次の性質が得られます。

- 発行の窓口が無くても、鍵を作った人やトランザクションを実行するノードが、同じアドレスを独立に求められる
- EOA は、同じ秘密鍵でどの EVM 互換チェーンでも同じアドレスを使える
- `CREATE2` では、デプロイする前にアドレスを相手に伝え、資産を受け取れる
- 同じファクトリを使えば、複数のチェーンで同じアドレスにコントラクトを置ける

---

### 欠点

同じ性質から、次の制約があります。

- アドレスが同じでも、何が置かれているか、誰が操作できるかはチェーンごとに違う
- コントラクトのアドレスに送る前に、送る先のチェーンでそのアドレスにコードがあり、自分が管理できるかを確認する必要がある
- `CREATE` のアドレスは nonce で変わるので、デプロイの前に別のトランザクションを挟むと、予定したアドレスがずれる
- 署名に chain ID の無い古い形式のトランザクションは、それを受け付けるチェーンでリプレイでき、同じアドレスにコントラクトを作れる

4 つ目は、EIP-155 より前の形式の署名がプロトコル上は今も有効なことから来ます（ノードの設定やチェーンによっては受け付けません）。deterministic-deployment-proxy はこの性質を使って全てのチェーンで同じアドレスを得ており、Wintermute の件では同じ性質が攻撃に使われました。
