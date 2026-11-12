---
title: "Replay Protection - 署名済みのデータを別の場所や時点で使い回させない仕組み"
date: 2026-11-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "replay-attack", "eip-155", "eip-712", "security"]
weight: 16
wrapTables: true
topics: ["Transaction / Wallet"]
---

リプレイ攻撃（replay attack）は、署名した人が意図していない場所や時点で、正しく署名されたデータをもう一度使わせる攻撃です。[デジタル署名](../digital-signature/)が示すのは、誰が署名したかと、署名の後に中身が変わっていないことです。どこで何回使ってよいかは、署名した中身に書いていない限り示しません。

[Ethereum](https://ethereum.org/) のトランザクションは、送り主が秘密鍵で署名したバイト列で、[mempool](../mempool/) やブロックを通じて誰でも読めます。読めたバイト列は、誰でも別のノードへそのまま送り直せます。

送り直す先は、同じチェーン、分岐した別のチェーン、[テストネットとメインネット](../mainnet-and-testnet/)、[L2](../rollup/)（Ethereum の上で動く別のチェーン）と複数あります。それぞれの先で同じ署名が通らないように、署名する中身に「どこで」「何回目か」「いつまで」を表す値を入れて防ぎます。チェーンを表す番号（chain ID）を署名に入れる規則は、[EIP-155](https://github.com/ethereum/EIPs/blob/bd93d240b72702450920eeeadc2ce593626bfd8a/EIPS/eip-155.md) という提案で入りました。以下は、手元で分岐させた 2 本のチェーンに、同じトランザクションを流した結果です。

{{< figure src="images/replay-protection_fork.webp" alt="左の 3 つの灰色のブロックが共通の列で、分岐の前は残高も nonce も共通。右で chain A（chain ID 31337）と chain B（chain ID 31338）の 2 本に分かれる。chain ID なしの署名（黄土色の古い形式）は A と B の両方のブロックに入り、chain ID 31337 入りの署名（青の EIP-155）は A だけに入って、B では赤い破線の × で外される" caption="分岐した 2 本のチェーンに同じ署名済みのトランザクションを流した結果" align="center" >}}

chain ID を含めない古い形式のトランザクションは、両方のチェーンで実行されました。chain ID 31337 を署名に含めたトランザクションは、chain ID 31338 のチェーンでは実行されていません。

<br>

本記事では、Ethereum のトランザクションとコントラクトの署名を例に、リプレイ攻撃を防ぐ仕組みを説明します。扱う疑問は次の通りです。

- 署名済みのトランザクションは、なぜ別のチェーンでも通るのか。
- nonce は何を防ぎ、分岐したチェーンでは何を防げないのか。
- 2016 年の ETH と ETC の分岐では何が起き、EIP-155 は chain ID をどう署名に入れたのか。
- コントラクトに渡す署名は、domain と nonce・期限でどう縛るのか。

[Cross-Chain Bridge](../cross-chain-bridge/) のメッセージの検証と、Bitcoin 系のチェーンの分岐での対策は扱いません。

---

### 署名済みのトランザクションが使い回せる理由

署名は、署名したデータに対して何度検証しても同じ結果を返します。[Digital Signature](../digital-signature/) のノートの実験でも、同じメッセージを送り直した場合の検証は `VALID` でした。署名の仕組みだけでは、1 回目と 2 回目を区別できません。

同じチェーンでの再送を止めるのは、[Ethereum Account Model](../ethereum-account-model/) で説明した nonce です。トランザクションには送り主の通し番号が入り、アカウントの nonce と一致するトランザクションだけが実行されます。実行されると nonce が 1 進むので、同じトランザクションの 2 回目は古い番号として拒否されます。

ただし、nonce を数えているのはチェーンごとの状態です。チェーンが分岐すると、分岐の時点の残高と nonce は両方のチェーンにそのまま残ります。片方で実行したトランザクションの nonce は、もう片方でもまだ使われていません。テストネットとメインネットや L2 でも、同じ鍵のアカウントの nonce がたまたま同じなら、同じことが起きます。

<br>

そこで、署名する中身に「どこで使う署名か」と「何回目か」「いつまでか」を入れます。署名には、トランザクションそのものの署名のほかに、トランザクションを送らずにメッセージへ署名し、受け取った相手がそれをコントラクトに渡すもの（トークンの使用許可など）があり、後者はコントラクトが検査します。以下は、使い回す先ごとに、それを防ぐ部品を並べた表です。

| 使い回す先 | 防ぐ部品 | 署名に入る値 |
| --- | --- | --- |
| 同じチェーンでもう一度 | トランザクションの nonce | 送り主の通し番号 |
| 別のチェーン | EIP-155 と型付きのトランザクション | chain ID |
| 同じチェーンの別のコントラクト | EIP-712 の domain | 検証するコントラクトのアドレス |
| 同じコントラクトでもう一度 | [アプリの nonce](/notes/security/nonce/) | 使い終わった番号 |
| 後の時点 | アプリの期限 | 期限の時刻 |

上の 2 行はトランザクションの規則で、プロトコルが検査します。下の 3 行は、コントラクトが自分で検査する必要があります。型付きのトランザクションと EIP-712 の domain は、後の節で説明します。

---

### ETH と ETC の分岐

署名に chain ID を入れる規則は、2016 年のチェーンの分岐をきっかけに作られました。[The DAO の事件](../reentrancy/)の後、Ethereum はブロック 1,920,000 で資金を移す規則に切り替え、切り替えなかったノードの列は Ethereum Classic（ETC）として続きました。経緯は [Blockchain Basics](../blockchain-basics/) と [Ethereum Hard Forks](../ethereum-hard-forks/) で説明しています。

分岐の前に ETH を持っていた人は、両方のチェーンに同じ残高を持つことになりました。当時のトランザクションは、署名にチェーンを区別する値が無いので、片方のチェーンに送ったトランザクションは、もう片方のチェーンでも有効です。ETH を送ったつもりのトランザクションが ETC のチェーンにも流されれば、同じ額の ETC も同じ宛先へ移ります。以下は、分岐から、両方のチェーンが chain ID を署名に入れるまでの流れです。

{{< figure src="images/replay-protection_timeline.webp" alt="左の 1 本の線が、2016-07 のブロック 1,920,000 で上の ETH と下の ETC の 2 本に分かれる。ETH 側には分岐から 2016-11 の Spurious Dragon（EIP-155、chain ID 1）まで「ETC でも通る」黄土色の帯、ETC 側には分岐から 2017-01 の Die Hard（EIP-155、chain ID 61）まで「ETH でも通る」帯がある。下に、帯はそのチェーンで署名したトランザクションがもう片方でも通った期間（EIP-155 の形式で署名した場合）で、chain ID を含めない形式で署名したトランザクションはその後も両方で有効、という注記" caption="ETH と ETC の分岐と、両方が chain ID を署名に入れるまで" align="center" >}}

帯の長さは、それぞれのチェーンが EIP-155 を入れるまでの期間です。ただし、EIP-155 は chain ID を含めない形式も有効なまま残したので、その形式で署名したトランザクションは帯が終わった後も使い回せます（この節の最後で説明します）。

Ethereum Foundation は分岐の 6 日後の[ブログ](https://blog.ethereum.org/2016/07/26/onward-from-the-hard-fork)で、ETC を動かす前に splitter のコントラクトを使い、新しく作ったアカウントへ移すよう勧めました。

[Etherscan に載っている関数の一覧（ABI）](https://etherscan.io/address/0xaBbb6bEbFA05aA13e908EaA492Bd7a8343760477#code) では、このコントラクトの名前は ReplaySafeSplit、関数は `split(targetFork, targetNoFork)` です。同じトランザクションが両方のチェーンで実行されても、分岐した側と分岐しなかった側で別の宛先に送るので、その後は 2 つのチェーンの資金が別のアカウントに分かれます。片方だけに残高があるアカウントから出したトランザクションは、もう片方では残高が足りず実行されません。同じブログは、ETC 側にもトランザクションの形式を変える分岐を検討するよう求めています。

<br>

#### EIP-155 の導入

プロトコル側の対策が [EIP-155](https://github.com/ethereum/EIPs/blob/bd93d240b72702450920eeeadc2ce593626bfd8a/EIPS/eip-155.md) です。2016 年 10 月 14 日に作られ、ブロック 2,675,000 の [Spurious Dragon](https://eips.ethereum.org/EIPS/eip-607) で有効になりました。[告知](https://blog.ethereum.org/2016/11/18/hard-fork-no-4-spurious-dragon)では、2016 年 11 月 22 日に到達する見込みとされています。

EIP-155 の Rationale は、目的を「a way to send transactions that work on Ethereum without working on ETC or the Morden testnet」（ETC やテストネットの Morden では通らず、Ethereum でだけ通るトランザクションを送る方法）と書き、ETC にも別の chain ID で採用するよう勧めています。

ただし、chain ID を含めない古い形式も、引き続き有効です。上記の告知も、この互換性のために EIP-155 を採用していないチェーン（ETC など）で作ったトランザクションは、まだ Ethereum でリプレイできると注意しています。ETC は 2017 年 1 月 13 日のブロック 3,000,000 の Die Hard で EIP-155 を採用し、chain ID 61 を使っています（[ECIP-1066](https://github.com/ethereumclassic/ECIPs/blob/cad0aecc6978e5fa0cdff66b99f79e6dc4978d86/_specs/ecip-1066.md)）。

---

### 分岐したチェーンでの再送

この状況を手元で再現しました。[Foundry](https://github.com/foundry-rs/foundry) のローカルノード [Anvil](https://getfoundry.sh/anvil/overview) 1.7.1 を 2 つ使います。chain ID 31337 のチェーン A で送り主の Alice に資金を送り、後の節で使う引換券のコントラクトを置いた後、Anvil の `--fork-url` で A のブロック 7 から chain ID 31338 のチェーン B を作りました。B は分岐の時点の A の残高・nonce・コントラクトを引き継ぎます。

実行は 2026 年 11 月 11 日で、Solidity のコンパイラは solc 0.8.28 です（実行環境は [environment.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/replay-protection/lab/output/environment.txt)）。

Anvil は `127.0.0.1` だけで待ち受け、公開のネットワークや実際の資産には接続していません。鍵は Anvil の既定のテスト用の鍵（広く公開されていて無価値）と、固定の文字列のハッシュから作った説明用の鍵だけです。

<br>

署名は、Python だけで書いた secp256k1 の署名と復元（[secp256k1.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/replay-protection/lab/secp256k1.py)）で行います。[cast](https://getfoundry.sh/cast/overview/) の `wallet sign` と同じ署名になること、EIP-155 の仕様にある例のトランザクションを同じバイト列で作れることを確かめています。以下が、トランザクションに署名する部分です。

```python
def sighash(fields, chain_id=None):
    """EIP-155 より前は 6 項目、EIP-155 では chainId, 0, 0 を足した 9 項目をハッシュする。"""
    if chain_id is None:
        return keccak256(rlp(fields))
    return keccak256(rlp(fields + [num(chain_id), b'', b'']))


def sign_legacy(key, nonce, to, value, chain_id=None, gas_price=10 * GWEI):
    fields = legacy_fields(nonce, to, value, gas_price)  # nonce, gasPrice, gas, to, value, data
    parity, r, s = secp256k1.sign(key, sighash(fields, chain_id))
    v = 27 + parity if chain_id is None else chain_id * 2 + 35 + parity
    return '0x' + rlp(fields + [num(v), num(r), num(s)]).hex(), (v, r, s)
```

`rlp` はトランザクションの符号化（[RLP](https://ethereum.org/developers/docs/data-structures-and-encoding/rlp/)）、`keccak256` は [EIP-712 のノート](../eip-712/)の実験で使った Python だけの Keccak-256 です。実験の全体は [lab/run.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/replay-protection/lab/run.py)、出力の全体は [lab/output/output.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/replay-protection/lab/output/output.txt) にあります。

まず、chain ID を渡さずに、Alice の nonce 0 で 1 ETH を Bob に送るトランザクションを作り、同じバイト列を A、B、もう一度 A の順に送りました。

```text
== 1. pre-EIP-155 transfer (alice nonce 0, 1 ETH to bob, signed without chain ID)
  raw 0xf86c808502540be400… v=28; recovered sender (None, '0x691f244c770a9d3dda5a97a4cc278afe51c19391')
  send to A: included 0x60ac026ee2d38b11… status 1
  send to B: included 0x60ac026ee2d38b11… status 1
  send to A again: rejected: nonce too low
  bob balance: A 1 ETH, B 1 ETH; alice nonce: A 1, B 1
```

同じトランザクションが、同じハッシュのまま両方のチェーンで実行されました。A への 2 回目は nonce で拒否されています。nonce は同じチェーンの 2 回目を止めますが、分岐した B の 1 回目は止めません。

---

### EIP-155 の chain ID

Ethereum の署名は、r、s、v の 3 つの値です。r と s が署名の本体で、v は署名とハッシュから公開鍵（つまり送り主のアドレス）を計算する時に、候補の 2 つのうちどちらかを選ぶ値です。前述のコードの `parity` がその 0 か 1 で、EIP-155 より前は 27 か 28 を足した値を v にしていました。

EIP-155 では、署名する前にハッシュする項目に chain ID と 0 を 2 つ足し、6 項目から 9 項目に変えます。前述のコードの `sighash` の 2 つの分岐が、その違いです。署名の `v` も、27 か 28 の代わりに `chain ID × 2 + 35` か `+ 36` にします。

トランザクションのデータには送り主のアドレスが入っていません。[Ethereum Transaction](../ethereum-transaction/) で説明した通り、ノードは署名から送り主を復元します。`v` が 35 以上なら、ノードは `v` から chain ID を読み、9 項目のハッシュで復元します。

<br>

Alice の nonce 1 で、chain ID 31337 を含めた取引を作りました。B に送った後、`v` だけを B の chain ID 31338 の値に書き換えた取引も B に送っています。

```text
== 2. EIP-155 transfer for chain 31337 (alice nonce 1)
  raw 0xf86e018502540be400… v=62710 = 31337*2+35+1; recovered (chain, sender) (31337, '0x691f244c770a9d3dda5a97a4cc278afe51c19391')
  send to A: included 0xf782f056affe8dd1… status 1
  send to B: hash 0xf782f056affe8dd1… returned, but not included (receipt null)
  v rewritten to 62712: recovered (chain, sender) (31338, '0x7d0a685db592d3104a37aa1590d878ecae3f54ca')
  send rewritten to B: rejected: Insufficient funds for gas * price + value
  bob balance: A 2 ETH, B 1 ETH; alice nonce: A 2, B 1
```

B は取引を受け取ってハッシュを返しましたが、ブロックには入れませんでした。レシート（取り込まれた取引の結果）は返らず、B の Alice の nonce も 1 のままです。[Anvil 1.7.1 の取引の受け付けの検査](https://github.com/foundry-rs/foundry/blob/v1.7.1/crates/anvil/src/eth/backend/mem/mod.rs#L4326-L4340)は、型付きの取引（後述）の chain ID の食い違いは拒否しますが、古い形式（legacy）の取引は通します。B がこの取引をブロックに入れなかった理由までは確かめていませんが、直後のブロックには入らなかったので、RPC がハッシュを返したことは、取り込まれたことを意味しません。

`v` を書き換えると、ハッシュする 9 項目の chain ID が変わり、復元される送り主は Alice とは無関係な `0x7d0a…` になりました。このアドレスには残高が無いので、B は残高不足で拒否しています。chain ID は署名の外に付けた札ではなく、署名した中身の一部なので、書き換えれば別人の署名になるわけです。

{{< figure src="images/replay-protection_recover.webp" alt="2 段の流れ図。上段は、署名の v 62710（31337×2+35+1）から、chainId 31337 を含む 9 項目をハッシュし、同じ r, s で復元すると青い箱の Alice 0x691f…（署名した本人）になる。下段は、v を 62712 に書き換えると chainId 31338 の 9 項目をハッシュすることになり、赤い箱の別のアドレス 0x7d0a…（残高が無く、残高不足で拒否）が復元される" caption="v を書き換えると、復元される送り主が変わる" align="center" >}}

送り主は署名から復元するので、ハッシュが変われば別のアドレスが出てくるだけで、ノードには署名が壊れたようには見えません。

<br>

#### 型付きの取引と L2

先頭に型を表すバイトを持つ取引（[EIP-1559](https://eips.ethereum.org/EIPS/eip-1559) など）は、`chainId` を独立した項目として持ち、署名の対象に含めます。[Mainnet and Testnet](../mainnet-and-testnet/) の実験では、chain ID 1 向けの EIP-1559 の取引を chain ID 11155111 のノードに送り、`invalid chain id for signer` で拒否されています。

L2 も、それぞれ別の chain ID を持ちます。2026 年 11 月 11 日時点の [chainid.network](https://chainid.network/) の一覧（[ethereum-lists/chains](https://github.com/ethereum-lists/chains/tree/8443a02df0503b02b54eb7b6db47720feb87b148/_data/chains) が元）は 2,858 件で、OP Mainnet は 10、Arbitrum One は 42161、Base は 8453 です。

chain ID を割り当てる管理者はいないので、一覧に登録されていない番号もあります。実験の 31338 は未登録で、31337 は同じ時点の一覧で GoChain Testnet の番号として登録されており、Anvil の既定値と重なっています。

<br>

#### chain ID を含めない取引の受け付け

Ethereum のノードの実装である [Geth](https://geth.ethereum.org/) は [1.10.0](https://github.com/ethereum/go-ethereum/releases/tag/v1.10.0) から、chain ID を含めない取引を RPC で既定では拒否します（`--rpc.allow-unprotected-txs` で解除）。

これはノードの受け付けの方針で、プロトコルの規則は変わっていません。誰かがブロックに入れれば、chain ID を含めない取引は今も実行されます。2022 年の [Optimism](https://www.optimism.io/) で、Ethereum の古い取引を L2 に流してコントラクトを同じアドレスに作られた事故は、[Ethereum Address](../ethereum-address/) で説明しています。

---

### EIP-712 の domain と分岐

取引を送らずにメッセージに署名し、相手がその署名をコントラクトに渡す場面でも、同じ問題が起きます。例えば、トークンの使用許可を署名で渡す ERC-2612 の permit がこの形です。[EIP-712](https://github.com/ethereum/EIPs/blob/bd93d240b72702450920eeeadc2ce593626bfd8a/EIPS/eip-712.md) では、署名するハッシュに domain separator（署名の領域を表すハッシュ）を入れ、`chainId` と `verifyingContract`（検証するコントラクトのアドレス）で、どのチェーンのどのコントラクト向けの署名かを区別します。

ハッシュの組み立ては [EIP-712 のノート](../eip-712/)で説明しています。以下のコードの `ecrecover` は、署名とハッシュから署名者のアドレスを復元する EVM の組み込み関数です。

domain の項目は、アプリが選びます。`chainId` を入れない domain も規格の上では作れますし、`chainId` を入れても、その値をいつ計算するかで結果が変わります。そこで、発行者が署名した引換券を出すと 1 ETH を払うコントラクトで、domain の作り方を 3 通りに変えて比べました。以下は、検証の部分の抜粋です。

```solidity
// mode 0: name と version だけ / mode 1: chainId と自分のアドレスを入れ、デプロイ時に計算して固定 / mode 2: 同じ項目を検証のたびに計算
function domainSeparator() public view returns (bytes32) {
    return mode == 2 ? _separator() : cachedSeparator;
}

function claim(address to, uint256 amount, uint256 nonce, uint256 deadline, uint8 v, bytes32 r, bytes32 s) external {
    require(block.timestamp <= deadline, "expired");
    require(!used[nonce], "nonce used");
    bytes32 structHash = keccak256(abi.encode(CLAIM_TYPEHASH, to, amount, nonce, deadline));
    bytes32 digest = keccak256(abi.encodePacked("\x19\x01", domainSeparator(), structHash));
    require(ecrecover(digest, v, r, s) == issuer, "bad signature");
    used[nonce] = true;
    payable(to).transfer(amount);
}
```

`_separator()` は、mode 0 なら `name` と `version` だけ、それ以外なら `block.chainid` と `address(this)` も入れて domain separator を計算します。全体は [lab/Voucher.sol](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/replay-protection/lab/Voucher.sol) で、説明用の実装です。監査は受けていません。

<br>

分岐の前の A に、各 mode のコントラクトを 2 個ずつ置きました。分岐した B にも、同じアドレスで 1 個目と 2 個目が残ります。発行者は、A の 1 個目向けに Bob への引換券（nonce 0）を 1 枚署名し、同じ署名を 4 か所に出しました。以下は、その結果です。

{{< figure src="images/replay-protection_voucher.webp" alt="3 行 4 列の結果の表。列は、署名した先（A の 1 個目）、分岐した B（同じアドレス）、A の 2 個目（別のアドレス）、同じ先に 2 回目。mode 0（chainId も verifyingContract も無し）は、通る、通る、通る、使用済み。mode 1（両方あり、デプロイ時に固定）は、通る、通る、署名が不一致、使用済み。mode 2（両方あり、検証のたびに計算）は、通る、署名が不一致、署名が不一致、使用済み。1 列目の通るは青、2 列目と 3 列目の通るは黄土色" caption="1 枚の引換券の署名を 4 か所に出した結果（lab/output/output.txt の 3）" align="center" >}}

mode 0 は、分岐した B でも、同じチェーンの別のコントラクトでも払いました。1 枚の署名で 3 ETH が出ています。

mode 1 は、別のコントラクトでは署名が一致しませんが、B では払いました。domain separator をデプロイ時に計算して固定したので、B のコントラクトも分岐の前の chain ID 31337 で検証するからです。

[ERC-2612](https://github.com/ethereum/ERCs/blob/6504eb9dbd3f42c685f057fd2a7e7cd20b5bc391/ERCS/erc-2612.md) の Security Considerations も、`chainId` を含む `DOMAIN_SEPARATOR` を署名ごとに作り直さずデプロイ時に決めると、将来のチェーンの分岐でチェーンをまたいだ再生の恐れがあると書いています。

mode 2 だけが、B と別のコントラクトの両方で署名の不一致になりました。[OpenZeppelin Contracts v5.1.0 の EIP712](https://github.com/OpenZeppelin/openzeppelin-contracts/blob/v5.1.0/contracts/utils/cryptography/EIP712.sol#L80-L86) は、デプロイ時の値を持ちつつ、`block.chainid` か自分のアドレスが変わっていれば計算し直します。固定の値で gas を節約しながら、mode 2 と同じ結果になる作りです。

---

### アプリの nonce と期限

前節の結果の 4 列目では、3 つの mode とも同じコントラクトへの 2 回目が `nonce used` で拒否されました。domain が防ぐのは別の場所での使い回しで、同じ場所での 2 回目は防ぎません。

EIP-712 の仕様の冒頭も「It does not include replay protection.」（再生の防止は含まない）と書き、Security Considerations で、同じ署名を 2 回見た時に拒否するか、[何度実行しても結果が変わらない処理](/notes/distributed-systems/idempotency/)にするのはアプリの責任だとしています。

実験の引換券は、使った番号を `used` に覚えるだけの nonce です。[EIP-712 のノート](../eip-712/)で扱った ERC-2612 の permit は、所有者ごとに番号を 1 ずつ進め、次の番号の署名だけを受け付けます。所有者が自分で permit を送って番号を進めれば、まだ使われていない署名を無効にできると、ERC-2612 の Security Considerations は書いています。

<br>

もう 1 つの軸が時間です。Ethereum の取引には、期限の項目がありません。署名した取引は、その nonce が使われるまでいつまでも有効です。A の時計を 365 日進めて、1 年前に署名した取引と引換券を出しました。

```text
== 4. a year later on chain A
  block time 1794367721 -> 1825903721 (+365 days)
  transfer signed a year ago (nonce 2) -> included 0x61ee9ef1e81f9e90… status 1
  voucher signed a year ago (deadline +1 h) -> revert execution reverted: expired
```

取引は 1 年後でも実行され、期限を 1 時間後にした引換券は `expired` で拒否されました。送らずに手元に残した取引を無効にするには、同じ nonce の別の取引を先に実行させるしかありません。署名をサービスに渡す場面では、期限を短くすることが、相手の手元に残った署名の寿命を決めます。

---

### 意図した使い回し

chain ID を含めない署名は、使い回せることを利用されてもいます。[deterministic-deployment-proxy](https://github.com/Arachnid/deterministic-deployment-proxy/tree/be3c5974db5028d502537209329ff2e730ed336c) は、秘密鍵を誰も知らない使い捨てのアカウントが署名した、chain ID を含めない取引（`v` が 27）でファクトリ（コントラクトを作るためのコントラクト）を作ります。署名の値を先に決め、そこから送り主のアドレスを逆に計算するので、そのアドレスの秘密鍵は誰も知りません。同じ取引を各チェーンに流せるので、どのチェーンでも同じアドレスにファクトリが置かれます。仕組みは [Ethereum Address](../ethereum-address/) で説明しています。

[EIP-7702](https://github.com/ethereum/EIPs/blob/bd93d240b72702450920eeeadc2ce593626bfd8a/EIPS/eip-7702.md) で、秘密鍵で動く普通のアカウント（EOA）が、自分の代わりに動くコントラクトのコードを指定（委任）する署名も、chain ID を 0 にすると全てのチェーンで有効になります。仕様は、委任先のアドレスに別のチェーンで何が置かれているかを考え、必要なら chain ID で範囲を絞るよう書き、全てのチェーンで使いたい場合は 0 にするとしています。使い回せることは、それ自体が欠陥なのではありません。問題は、どこまで使い回せるかを署名する人が分かっているかどうかです。

---

### 利点

- 取引の nonce と chain ID は、ウォレットとノードが扱うので、利用者は意識せずに守られる
- 署名する中身に値を足すだけで、新しい鍵や仕組みを用意せずに使い回せる範囲を狭められる
- chain ID や domain が違うと署名者が別のアドレスとして復元され、残高も権限も持たないので取引や検証が通らない
- 期限と nonce をアプリが選べるので、署名の寿命と回数を用途に合わせて決められる

### 欠点

これらの仕組みは、署名する中身に場所・回数・期限を入れることで使い回しを防ぎます。その代わりに、次の制約があります。

- chain ID を含めない古い署名も有効なままで、受け付けるかどうかはノードの設定に任される
- chain ID は登録制ではなく、別のチェーンが同じ番号を名乗ることを規則では止められない
- EIP-712 の domain や nonce・期限はコントラクトごとの実装で、入れ忘れや計算の時点の誤りは規格では防げない
- 取引に期限が無いので、送らずに残した署名済みの取引は、同じ nonce を使うまで有効なまま残る

### これらの仕組みで防げないケース

- 同じ chain ID のまま分岐し、どちらのチェーンも番号を変えない場合
- 署名した人が、domain や期限の意味を確かめずに、正規のサイトを装った相手に署名する場合
- コントラクトが、署名したメッセージに chain ID や自分のアドレスを含めずに検証する場合
- chain ID が 0 の委任のように、全てのチェーンで有効にした署名が、意図しないチェーンで使われる場合

分岐の後に chain ID を変えるかどうかは、そのチェーンの参加者が決めることです。署名する側が確かめられるのは、自分の署名にどの chain ID とどのコントラクトが入っているかまでです。

図の生成コードは [figures.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/replay-protection/figures.py) にあります。
