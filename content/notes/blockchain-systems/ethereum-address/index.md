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

`0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` は、開発用のローカルノードである [Anvil](https://getfoundry.sh/anvil/overview/) が最初に用意するテスト用アカウントのアドレスです。chain ID（チェーンを区別する番号）を 31337 にしても 31338 にしても、このアカウントは同じアドレスで現れます。

Ethereum のアドレスは、アカウントを指す 20 バイトの値です。誰かに申請して払い出してもらう番号ではなく、秘密鍵や作り手の情報から、誰でも同じ計算で求められます。計算の規則は、秘密鍵で操作する EOA（Externally Owned Account）、コントラクトを作る `CREATE`、作る前にアドレスを指定できる `CREATE2` の 3 つです。

以下は、3 つの規則の材料と、材料に入らない chain ID の関係を示した図です。

{{< figure src="images/ethereum-address_concept.svg" alt="EOA は公開鍵 64 バイト、CREATE は送り手と nonce、CREATE2 は ff・送り手・salt・initcode のハッシュを keccak256 に入れ、下位 20 バイトがアドレスになる。アドレスの下にはチェーン A（コード X がある）とチェーン B（空か別のコード）の 2 つの枠が並ぶ。chain ID は署名に入り、keccak256 に向かう点線には赤い × が付いている" caption="3 つの規則の材料と、材料に入らない chain ID" align="center" >}}

上記の図のどの規則にも chain ID は入りません。そのため、同じ材料からは、どのチェーンでも同じアドレスが計算されます。しかし、そのアドレスにどのコードがあるかは、チェーンごとに別々に記録されます。

<br>

本記事では、同じ鍵やコードからどういう時に同じアドレスになり、どういう時に別のアドレスになるのかを説明します。よく見かける次の理解は、どれも条件付きでしか成り立ちません。仕様とローカルの実験で確かめ直します。

- アドレスはチェーンごとに違う。
- 同じコードをデプロイすれば、同じアドレスになる。
- コントラクトのアドレスにあるコードは、後から変わらない。

アカウントが持つ状態と nonce は [Ethereum Account Model](../ethereum-account-model/)、送り主を署名から復元する流れは [Ethereum Transaction](../ethereum-transaction/) で説明しました。仕様変更の提案（EIP、Ethereum Improvement Proposal）の [EIP-7702](https://eips.ethereum.org/EIPS/eip-7702) による委任と [ERC-4337](../erc-4337/) のスマートアカウントのアドレスは、それぞれのノートで扱っています。

---

### 計算でアドレスを求める理由

誰でも参加できるネットワークには、アドレスを発行する窓口がありません。[Digital Signature](../digital-signature/) で説明したように、鍵ペアは誰の許可も無しに手元で作れ、作った瞬間からそのアドレスで ETH を受け取れます。コントラクトのアドレスも、取引を実行した全てのノードで一致しなければなりません。

そのため、どの規則も、材料を [keccak256](https://ethereum.github.io/yellowpaper/paper.pdf) というハッシュ関数に通し、32 バイトの結果の下位 20 バイトを取ります。材料が 1 ビットでも違えば別のアドレスになり、材料が同じなら、いつどこで計算しても同じアドレスになります。つまり、同じアドレスになるかどうかは、材料に何が入っているかで判断できます。

ちなみに、Ethereum の keccak256 は標準化前の [Keccak](https://keccak.team/keccak.html) で、米国の NIST が定めた [SHA3-256](https://csrc.nist.gov/pubs/fips/202/final) とは詰め物（padding）の 1 バイトが違います。Python の [`hashlib.sha3_256`](https://docs.python.org/3/library/hashlib.html#hashlib.sha3_256) で計算すると別の値になります。

---

### EOA のアドレス

EOA のアドレスは、次の手順で公開鍵から計算します（[ethereum.org のアカウントの説明](https://ethereum.org/en/developers/docs/accounts/)）。

1. 32 バイトの秘密鍵から、楕円曲線 [secp256k1](https://www.secg.org/sec2-v2.pdf) の上の点として公開鍵を求める。
2. 公開鍵の x 座標と y 座標（各 32 バイト、合わせて 64 バイト）を keccak256 に通す。
3. 結果の下位 20 バイトをアドレスにする。

材料は秘密鍵から求まる公開鍵だけで、chain ID は入りません。アドレスはチェーンごとに違う、という説明は EOA については誤りです。同じ秘密鍵は、Ethereum でも [L2](https://ethereum.org/en/layer-2/) でも、同じ規則でアドレスを計算する EVM（Ethereum Virtual Machine）互換チェーンなら同じアドレスになります。

chain ID が入るのは取引の署名です。[EIP-155](https://eips.ethereum.org/EIPS/eip-155) に従う legacy transaction と、型を持つ取引（typed transaction）は、署名の対象に chain ID を含めます。アドレスはチェーンをまたいで共通で、チェーンをまたいだ取引の再生は署名で防ぐのです。

[Wallet](../wallet/) で確かめた通り残高はチェーンごとに別ですが、どのチェーンでも同じ秘密鍵が操作するので、EOA の持ち主は変わりません。

<br>

#### 大文字と小文字の混ざった表記

`0xf39Fd6e5…` のように大文字と小文字が混ざっているのは、[EIP-55](https://eips.ethereum.org/EIPS/eip-55) のチェックサムです。小文字の 16 進表記を keccak256 に通し、対応するハッシュの桁が 8 以上の英字を大文字にします。打ち間違えると大文字の位置が合わなくなるので、ウォレットが検出できます。表記の違いだけで、全て小文字の `0xf39fd6e5…` も同じ 20 バイトの値です。

---

### CREATE のアドレス

EOA の取引でコントラクトを作る時と、コントラクトが `CREATE` 命令で別のコントラクトを作る時は、送り手のアドレスと nonce から計算します。

```text
address = keccak256(rlp([sender, nonce]))[12:]
```

[RLP](https://ethereum.org/en/developers/docs/data-structures-and-encoding/rlp/)（Recursive Length Prefix）は、Ethereum がデータを並べる時の符号化の形式です。`nonce` は作る時点の送り手の nonce で、EOA なら送った取引の件数です。コントラクトの nonce は [EIP-161](https://eips.ethereum.org/EIPS/eip-161) により 1 から始まり、`CREATE` のたびに 1 増えます。

材料にコードは入っていません。そのため、同じコードをデプロイしても、同じ EOA が先に送金を 1 件済ませていれば nonce が進み、別のアドレスになります。逆に、送り手と nonce が同じなら、中身が全く違うコントラクトでも同じアドレスになります。

---

### CREATE2 のアドレス

`CREATE2` は、[EIP-1014](https://eips.ethereum.org/EIPS/eip-1014) で、[2019 年のハードフォーク](https://ethereum.org/en/history/#constantinople)（全ノードが同時に規則を切り替える更新）Constantinople から使えるようになった命令で、nonce の代わりに salt と initcode から計算します。

```text
address = keccak256(0xff ‖ sender ‖ salt ‖ keccak256(initcode))[12:]
```

`sender` は `CREATE2` を実行するコントラクト（以下、ファクトリ）、`salt` はファクトリが選ぶ 32 バイトの値です。

initcode は、デプロイの時に 1 度だけ実行され、置くコードを返すプログラムで、[Solidity](https://soliditylang.org/) ではコンストラクタの引数も末尾に付きます。先頭の `0xff` は、`CREATE` の RLP が `0xff` で始まらないことを使って、2 つの規則のアドレスが重ならないようにしています。

nonce が入らないので、デプロイする前にアドレスが分かります。ERC-4337 のスマートアカウントは、この性質を使って作る前のアドレスで ETH を受け取ります（[ERC-4337](../erc-4337/)）。

<br>

式の材料のうち、コードに関わるのは initcode のハッシュだけで、ほかに salt とファクトリのアドレスが入ります。そのため、同じコードでも salt が違えば別のアドレスで、コンストラクタの引数が違えば initcode が変わり、やはり別のアドレスです。チェーンをまたいで同じアドレスにするには、ファクトリも両方のチェーンで同じアドレスにある必要があります。

そのために広く使われているのが [deterministic-deployment-proxy](https://github.com/Arachnid/deterministic-deployment-proxy) です。`r` と `s` を固定値にした署名で、ファクトリを作る取引を公開しています。送り手は署名から逆算されるアカウントで、秘密鍵は誰も知らず、1 度しか使えません。

署名は `v` が 27 の、chain ID を含まない形式です。そのため、chain ID の無い取引を受け付けるチェーンなら、どこに流しても送り手と nonce 0 が同じになり、ファクトリは同じアドレスにできます。

計算したアドレスに既にコードがあるか、nonce が 0 でない場合、作成は失敗します。同じ salt と initcode で 2 度はデプロイできません。

なお、本記事の式は Ethereum のものです。[ZKsync の EraVM](https://docs.zksync.io/zksync-protocol/differences/evm-instructions) のように、EVM 互換をうたうチェーンでも `CREATE` と `CREATE2` を別の式で計算するものがあります。

---

### ローカルでの計算と照合

3 つの規則を外部のライブラリ無しの Python で書き、Anvil のデプロイ結果と照合しました。Anvil 1.7.1 と Solidity コンパイラ 0.8.28 は、Docker の公式イメージ（[ghcr.io/foundry-rs/foundry](https://github.com/foundry-rs/foundry/pkgs/container/foundry) の v1.7.1、[ethereum/solc](https://hub.docker.com/r/ethereum/solc) の 0.8.28）で動かします。コンテナはネットワーク無しで起動し、秘密鍵は Anvil が公開している既定のテスト用の鍵だけを使います。

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

chain ID の違うチェーン A（31337）、B（31338）、C（31339）を起動し、A と C では最初の取引でファクトリを作りました。B では、最初の取引で別のコントラクト（V2）を作り、次の取引でファクトリを作ります。ファクトリは、コンストラクタで値 `v` を受け取る `Child` を `CREATE2` で作ります。

`= python` は、Python の計算と一致したことを示します。手順の全体は [run.py](lab/run.py)、コントラクトは [Address.sol](lab/Address.sol)、環境は [README](lab/README.txt) にあります。`Address.sol` は学習用に書いたもので、監査していません。以下が[出力](lab/output/summary.txt)の前半です。

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

EOA の段では、3 つのチェーンで同じアドレスが返りました。同じ取引でも A 向けと B 向けの署名は別のデータで、A 向けのものを B に流すと拒否されます。

`CREATE` の段では、チェーン B の `0x5FbD…` に最初はコードがありません。そこに nonce 0 で V2 を作ると、チェーン A のファクトリと同じアドレスに、全く別のコードが置かれました。

`CREATE2` の段では、salt を 1 にしても、引数を 2 にしてもアドレスが変わりました。ファクトリの位置が違う B では、salt も引数も同じなのに別のアドレスで、ファクトリが同じ位置にある C では A と同じアドレスです。

---

### チェーンをまたいだアドレスの事故

同じアドレスでも、別のチェーンで誰が操作できるかは、EOA とコントラクトで違います。EOA は同じ秘密鍵がどのチェーンでも操作します。コントラクトは、そのチェーンでそのアドレスに誰がコードを置いたかで持ち主が変わります。2022 年の Optimism と、暗号資産の売買で流動性を提供する事業者 Wintermute の件では、この違いで 2,000 万 OP が第三者の手に渡りました。

[Wintermute が Optimism のフォーラムに出した報告](https://gov.optimism.io/t/message-to-optimism-community-from-wintermute/2595)、[rekt.news の解析](https://rekt.news/wintermute-rekt)、チェーン上の記録から、経緯は次の通りです。

1. 2020 年 11 月、Wintermute は Ethereum で [Safe（当時の Gnosis Safe）](https://github.com/safe-global/safe-contracts/tree/v1.1.1)の ProxyFactory 1.1.1 の `createProxy` を呼び、マルチシグ `0x4f3a120E…cb81` を[作りました](https://etherscan.io/tx/0xd705178d68551a6a6f65ca74363264b32150857a26dd62c27f3f96b8ec69ca01)。`createProxy` は `CREATE` を使うので、このアドレスは ProxyFactory のアドレスと nonce から計算されたものです。
2. 2022 年 5 月、[Optimism Foundation](https://www.optimism.io/) は流動性の提供を頼んだ Wintermute に 2,000 万 OP を貸し出しました。Wintermute が受け取り先として伝えたのは Ethereum の Safe のアドレスで、OP Mainnet（Optimism の L2）のそのアドレスには何もありませんでした。
3. 2022 年 6 月 5 日、攻撃者は、2019 年に Ethereum で ProxyFactory を作った取引を OP Mainnet に流しました。両方のチェーンに[同じハッシュの取引](https://optimistic.etherscan.io/tx/0x75a42f240d229518979199f56cd7c82e4fc1f1a20ad9a4864c635354b4a34261)が記録されており、chain ID の無い署名だったので再生できたのです。ProxyFactory は Ethereum と同じアドレスにできました。
4. 攻撃者は、自分を所有者にした Safe をこの ProxyFactory で 162 個ずつ作り、nonce を進めました。nonce が 2020 年の時と同じ値に来たところで、`0x4f3a120E…cb81` に[攻撃者の Safe ができ](https://optimistic.etherscan.io/tx/0x00a3da68f0f6a69cb067f09c3f7e741a01636cbc27a84c603b468f65271d415b)、2,000 万 OP を動かせるようになりました。

問題は、Ethereum で自分が管理するコントラクトのアドレスなら、別のチェーンでも自分が管理できる、と扱われたことです。上記の実験のチェーン B で、A のファクトリと同じアドレスに V2 が置けたのは、手順 4 と同じ形です。攻撃者は 100 万 OP を売却した後、6 月 10 日に 1,700 万 OP を Optimism 側に返しました（[The Block の報道](https://www.theblock.co/post/151344/hacker-returns-17-million-op-tokens)）。

同じ ProxyFactory 1.1.1 には、`CREATE2` を使う `createProxyWithNonce` もあり、所有者を含む初期化の内容のハッシュを salt に入れます。この方法なら、所有者を変えると別のアドレスになるので、攻撃者が自分を所有者にして同じアドレスを作ることはできません。

---

### 同じアドレスでのコードの置き直し

コントラクトのアドレスにあるコードは、後から差し替えられるのでしょうか。2024 年 3 月 13 日のハードフォーク Cancun より前は、差し替えられました。`CREATE2`、`CREATE`、コントラクトを消す `SELFDESTRUCT` を組み合わせると、同じアドレスに別のコードを置き直せたからです。この手法は metamorphic contract と呼ばれます。手順は以下の通りです。

1. ファクトリが `CREATE2` で、固定の salt と initcode から Deployer を作る。Deployer のアドレスは毎回同じになる。
2. Deployer が `CREATE` で V1 を作る。アドレスは Deployer と nonce 1 で計算される。
3. V1 と Deployer を `SELFDESTRUCT` で消す。アカウントごと消えるので、Deployer の nonce も無くなる。
4. 1 と同じ `CREATE2` で Deployer を作り直す。nonce は再び 1 から始まる。
5. Deployer が `CREATE` で V2 を作る。材料が 2 と同じなので、V1 と同じアドレスに V2 が置かれる。

2023 年 5 月の Tornado Cash のガバナンスの乗っ取りでは、この手順が使われました（[rekt.news の解析](https://rekt.news/tornado-gov-rekt)）。攻撃者は、以前の提案と同じ処理だとうたう提案のコントラクトを出し、投票で可決させました。その後でコントラクトを消し、[同じアドレスに別のコードを置き直して](https://etherscan.io/address/0xC503893b3e3c0C6b909222b45f2a3a259a52752D)、ガバナンスの票を自分に集めました。投票者が確かめたのは、投票の時点でそのアドレスにあったコードです。

<br>

Cancun で有効になった [EIP-6780](https://eips.ethereum.org/EIPS/eip-6780) により、`SELFDESTRUCT` でアカウントが消えるのは、コントラクトを作ったのと同じ取引の中で呼んだ場合だけになりました。別の取引で呼ばれた `SELFDESTRUCT` は残高を送るだけで、コードも nonce も消しません。そのため、手順 4 の `CREATE2` は、消えずに残った Deployer に当たって失敗します。

1〜5 の各段を別の取引にして、Anvil の `--hardfork` を変えて実行しました。以下は [run.py](lab/run.py) の 3〜5 の抜粋で、`dd` は Deployer を作る呼び出しです。

```python
assert ok(n.send(target, selector('kill()'))) == 1    # V1 SELFDESTRUCT
assert ok(n.send(deployer, selector('kill()'))) == 1  # Deployer SELFDESTRUCT
sizes = f'{n.code_size(target)}/{n.code_size(deployer)} bytes'
redeploy = ok(n.send(factory, dd))                     # CREATE2 the Deployer again
target2 = returned_address(n, deployer, deploy + abi_bytes(bins['V2']))
assert ok(n.send(deployer, deploy + abi_bytes(bins['V2']))) == 1
```

V1 の `version()` は 1、V2 は 2 を返します。コンパイルは、比べる全てのフォークで動くように、Cancun の 1 つ前の Shanghai 向けにしました。結果は以下の通りです。

```text
fork     | 1st target | v | code after kill | redeploy Deployer | 2nd target | v | v at 1st
shanghai | 0xCB8956e6 | 1 | 0/0 bytes       | status=1          | 0xCB8956e6 | 2 | 2
cancun   | 0xCB8956e6 | 1 | 218/930 bytes   | status=0          | 0x673a327D | 2 | 1
prague   | 0xCB8956e6 | 1 | 218/930 bytes   | status=0          | 0x673a327D | 2 | 1
```

以下は、手順の段ごとに、最初のアドレス `0xCB8956e6…` にあるコードを並べた図です。

{{< figure src="images/ethereum-address_redeploy.svg" alt="上の段の Shanghai では、0xCB8956e6… のコードが V1 から、消した後の空（0 bytes）を経て V2 に変わる。下の段の Cancun 以降では、消した後も V1 が 218 bytes のまま残り、作り直しの後も V1 のまま。下に赤い × と「Deployer を作り直せない」「V2 は 0x673a327D… へ」" caption="1 つのアドレスにあるコードの移り変わり" align="center" >}}

Shanghai では、`SELFDESTRUCT` の後に V1 も Deployer も 0 バイトになり、同じ `0xCB8956e6…` に V2 が置かれました。Cancun と、次の Prague では、コードが残ったまま Deployer の作り直しが失敗し、V2 は nonce 2 で別のアドレスに作られました。元のアドレスは 1 を返し続けます。

フォークごとの `SELFDESTRUCT` の違いは、[Ethereum Hard Forks](../ethereum-hard-forks/) でも確かめています。

<br>

Cancun 以降も、同じ取引の中で作って消したアドレスには、後の取引で別のコードを作れます。しかし、そのコードは 1 つの取引の中にしか無かったので、取引をまたいで誰かが確かめたコードが差し替わることはありません。

ただし、コードが変わらなくても振る舞いが変わる仕組みは残っています。実装の参照先を記憶領域に持つプロキシは、参照先を差し替えると別の処理を行います。EIP-7702 で委任した EOA も、委任先を書き換えられます（[Ethereum Account Model](../ethereum-account-model/)）。

---

### 利点

アドレスを材料のハッシュで計算する設計から、次の性質が得られます。

- 発行の窓口が無くても、鍵を作った人や取引を実行するノードが、同じアドレスを独立に求められる
- EOA は、同じ秘密鍵でどの EVM 互換チェーンでも同じアドレスを使える
- `CREATE2` では、デプロイする前にアドレスを相手に伝え、資産を受け取れる
- 同じファクトリを使えば、複数のチェーンで同じアドレスにコントラクトを置ける

---

### 欠点

同じ性質から、次の制約があります。

- アドレスが同じでも、何が置かれているか、誰が操作できるかはチェーンごとに違う
- コントラクトのアドレスに送る前に、送る先のチェーンでそのアドレスにコードがあり、自分が管理できるかを確かめる必要がある
- `CREATE` のアドレスは nonce で変わるので、デプロイの前に別の取引を挟むと、予定したアドレスがずれる
- 署名に chain ID の無い古い形式の取引は、それを受け付けるチェーンで再生でき、同じアドレスにコントラクトを作れる

4 つ目は、EIP-155 より前の形式の署名がプロトコル上は今も有効なことから来ます（ノードの設定やチェーンによっては受け付けません）。deterministic-deployment-proxy はこの性質を使って全てのチェーンで同じアドレスを得ており、Wintermute の件では同じ性質が攻撃に使われました。
