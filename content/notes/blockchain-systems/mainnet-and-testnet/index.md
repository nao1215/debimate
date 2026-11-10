---
title: "Mainnet and Testnet - 本番のネットワークと試験用のネットワーク"
date: 2026-11-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "bitcoin", "testnet"]
weight: 2
wrapTables: true
topics: ["Introduction"]
---

`bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4` と `tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx` は、同じ公開鍵から作った Bitcoin のアドレスです。先頭の `bc1` はメインネット、`tb1` はテストネットのアドレスであることを示し、途中の文字列は同じです。

メインネット（mainnet）は、市場で価値を持つ通貨が動く本番のネットワークです。テストネット（testnet）は、メインネットとほぼ同じソフトウェアと規則で動く公開のネットワークで、価値を持たない筈の通貨で送金やプログラムを試すために使います。

さらに手元の 1 台だけで動かすローカルのチェーンがあり、Bitcoin のノードのソフトウェアである [Bitcoin Core](https://bitcoincore.org/) の regtest や、Ethereum の開発ツール [Foundry](https://getfoundry.sh/) の [Anvil](https://getfoundry.sh/anvil/overview/)・[Hardhat](https://hardhat.org/) が起動するチェーンが該当します。

例えば、スマートコントラクトの開発者は、ローカルのチェーンで試した後にテストネットで公開し、最後にメインネットにデプロイします。ウォレットの開発者も、利用者の資産を動かす前にテストネットで送金を確かめます。以下は、3 種類のネットワークの関係を時間の流れで示した図です。

{{< figure src="images/mainnet-and-testnet_concept.svg" alt="左に Mainnet（chain ID 1）、Testnet（chain ID 11155111）、Local（chain ID 31337）の 3 行が並び、それぞれ四角を線で繋いだ別々の列を持つ。Mainnet の列は最も左から始まり、Testnet はその途中から、Local は右端の数個だけ。新しい規則を示す点線は Testnet の列の中ほどにあり、Mainnet では右端の近くにある。Local は最初のブロックから自分で選んだ規則で始まっている" caption="別々に伸びる 3 種類のチェーンと、新しい規則が有効になる時期" align="center" >}}

上記の図の 3 つの列は、どこにも繋がっていません。同じ鍵から同じアドレスを作れても、残高や記録はチェーンごとに別々です。また、新しい規則はテストネットで先に有効になり、メインネットでは後から有効になります。

<br>

本記事では、[Blockchain Basics](../blockchain-basics/) を読んだ人に向けて、メインネット・テストネット・ローカルのチェーンの違いを Ethereum と Bitcoin の両方で説明します。次の疑問を順に取り上げます。

- 3 種類のネットワークは、何が同じで何が違うのか。
- ノードや署名済みの取引は、どこで自分のネットワークを見分けるのか。
- テストネットは、なぜ何度も入れ替わってきたのか。
- 価値が無い筈のテストネットの通貨は、なぜ問題を起こすのか。

L2（Ethereum の上に作る別のチェーン）のテストネットと、各ネットワークのノードの立て方は説明しません。

---

### 3 種類のネットワークの違い

3 種類のネットワークで同じなのは、取引の形式、署名の方法、アドレスの計算の規則です。そのため、ウォレットや開発ツールは、接続先を切り替えるだけで同じ操作ができます。違うのは、そのネットワークに誰が参加し、どの記録を持っているかです。

整理すると、以下の通りです。テストネットの列は、2026 年 11 月時点の Ethereum の Sepolia と Bitcoin の signet を例にしています。

| 項目 | メインネット | テストネット | ローカルのチェーン |
| --- | --- | --- | --- |
| 通貨の価値 | 市場で売買される | 無い筈だが、売買された例がある | 無い |
| 通貨の入手 | 購入、採掘、報酬 | faucet（無料で配る窓口）から受け取る | 起動時に配られる、好きなだけ作る |
| ブロックを作る者 | 誰でも参加できる | 許可された者に限る場合がある | 自分の 1 台 |
| 規則の切り替え | テストネットの後 | メインネットより先 | 起動時に自分で選ぶ |
| 状態 | 長い履歴と、デプロイ済みのコントラクト | 別の履歴。同じコントラクトでもアドレスが違う | 空から始まる |

上記の表の状態の行は、テストネットでの確認がメインネットでの成功を保証しない理由の 1 つです。例えば、[USDC](https://www.circle.com/usdc) というトークンのコントラクトは、[発行元の Circle の一覧](https://developers.circle.com/stablecoins/usdc-contract-addresses)によると、Ethereum のメインネットでは `0xA0b8…eB48`、Sepolia では `0x1c7D…7238` にあります。アドレスを直書きしたプログラムは、ネットワークを替えると別の相手を呼びます。

<br>

ネットワークごとの設定の違いは、ノードのソフトウェアの不具合も生みます。2025 年 2 月 24 日、Ethereum のテストネットの Holesky で更新 [Pectra](https://ethereum.org/roadmap/pectra/) が有効になった直後に、ネットワークが 2 つに分かれました。[事後報告](https://github.com/ethereum/pm/blob/6f1d4cb01d68e07c02ed61e48a9a335f9fb787db/Network-Upgrade-Archive/Pectra/holesky-postmortem.md)によると、経緯は次の通りです。

1. Pectra で、預け入れ（deposit）を記録するコントラクトのイベントは、取引を実行する側のソフトウェア（実行層のクライアント）が読むようになりました。
2. このコントラクトのアドレスは、メインネットと Holesky で違います。Holesky は `0x4242…4242` です。
3. 実行層のクライアントの Geth・Nethermind・[Besu](https://github.com/besu-eth/besu) は Holesky のアドレスを正しく設定しておらず、預け入れを含むブロックで他のソフトウェアと違う結果を出しました。
4. 確定（finality）が約 2 週間止まり、3 月 10 日に回復しました。

メインネットに無い不具合がテストネットだけで起きた例です。逆に、メインネットにだけある設定や状態で失敗することもあります。テストネットで動いたことは、同じ規則・同じソフトウェアで動いたことの確認であって、メインネットの状態と混み具合で動いたことの確認ではありません。

---

### ネットワークの見分け方

ネットワークを取り違えると、テストのつもりの送金がメインネットで成立したり、テストネット用の取引が別のチェーンで実行されたりします。そのため、ノード同士の通信と、署名済みの取引の両方に、ネットワークを区別する値が入っています。

<br>

#### Ethereum の chain ID と network ID

chain ID は、取引の署名に入れる、チェーンを区別する番号です。[EIP-155](https://eips.ethereum.org/EIPS/eip-155)（2016 年の [Spurious Dragon](https://eips.ethereum.org/EIPS/eip-607) で有効）が導入しました。EIP-155 の取引と、型を持つ取引（typed transaction）は、署名の対象に chain ID を含めます。署名の後で chain ID を書き換えると、署名から復元される送り主が別のアドレスになり、取引は成り立ちません。

network ID は、ノード同士の通信で使う番号です。[eth プロトコルの仕様](https://github.com/ethereum/devp2p/blob/88f1c80800d622cc3a542a2125bbe33cc18c9f9c/caps/eth.md)では、接続した直後に送る Status メッセージに network ID・genesis（最初のブロック）のハッシュ・[EIP-2124](https://eips.ethereum.org/EIPS/eip-2124) の fork ID を入れ、相手が同じネットワークかを判断します。ノードに問い合わせる RPC（Remote Procedure Call）では、`eth_chainId` が chain ID、`net_version` が network ID を返します。

多くのネットワークでは 2 つの値が同じです。しかし、同じ仕様には、network ID が chain ID と一致するとは限らないと書かれています。例えば、[ethereum-lists/chains](https://github.com/ethereum-lists/chains/tree/7306cde75380dc59d2a4124d9711de7c52b210e1/_data/chains) の登録では、[Ethereum Classic](https://ethereumclassic.org/) の chain ID は 61、network ID は 1 です。以下は、主なネットワークの chain ID です。

| ネットワーク | chain ID | 2026 年 11 月の状態 |
| --- | --- | --- |
| Ethereum のメインネット | 1 | 稼働中 |
| Sepolia | 11155111 | 稼働中 |
| Hoodi | 560048 | 稼働中 |
| Holesky | 17000 | 支援終了 |
| Goerli | 5 | 支援終了 |
| Anvil・Hardhat の既定 | 31337 | ローカル |

chain ID を割り当てる管理者はいません。上記の一覧は利用者が登録する共有の台帳で、31337 は GoChain Testnet というネットワークの番号として登録されています。Anvil や Hardhat の既定値と重なっているのです。

<br>

#### Bitcoin の magic bytes・アドレス・ポート

Bitcoin のノードは、P2P のメッセージの先頭に、ネットワークごとに決まった 4 バイトの magic bytes を付けます。ブロックをディスクに保存する時も、ブロックごとに同じ 4 バイトを付けます。ただし、Bitcoin Core 28.0 以降は保存するファイルに既定で XOR をかけるので、後の実験では `-blocksxor=0` で外して読みます。違うネットワークのノードとは、最初のメッセージで食い違うので通信になりません。

人が目で見分けるのは、アドレスの接頭辞です。`bc1` で始まる形式のアドレスは [BIP-173](https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki) の形式で、先頭の文字列（HRP、human-readable part）がメインネットは `bc`、テストネットは `tb` です。regtest の `bcrt` は [Bitcoin Core の設定](https://github.com/bitcoin/bitcoin/blob/v32.1/src/kernel/chainparams.cpp)にある値です。末尾の検査用の文字は HRP を含めて計算するので、HRP を書き換えただけのアドレスは誤りとして弾かれます。

既定の待ち受けポートも、ネットワークごとに違います。値は、後の実験で確かめます。

---

### Ethereum のテストネットの移り変わり

Ethereum のテストネットは、数年ごとに入れ替わってきました。履歴と状態が増え続けてノードを動かす負担が大きくなり、通貨の配り方やブロックを作る者の集め方にも問題が出るからです。2022 年の [The Merge](https://ethereum.org/roadmap/merge/) 以降の Ethereum は、預けた ETH を担保にする PoS（Proof of Stake）で動き、ブロックを提案・承認する参加者を validator と呼びます。

| テストネット | 経緯 | 2026 年 11 月時点 |
| --- | --- | --- |
| Ropsten | 2022 年 6 月に[終了を予告](https://blog.ethereum.org/2022/06/21/testnet-deprecation)。PoS に移行済みで、2022 年の第 4 四半期に終了の予定 | 終了 |
| Rinkeby | 同じ告知で、PoS に移行せず 2023 年に終了の予定 | 終了 |
| Goerli | [Dencun](https://eips.ethereum.org/EIPS/eip-7569)（2024-01-17）を最後の更新とし、メインネットの Dencun の後に[支援を終了](https://blog.ethereum.org/2023/11/30/goerli-lts-update) | 終了 |
| [Sepolia](https://github.com/eth-clients/sepolia) | 2021 年に開始。アプリとコントラクトの試験用で、ブロックを作る validator は許可制 | 稼働中 |
| [Holesky](https://github.com/eth-clients/holesky) | 2023-09-28 に開始。validator の試験用。2025 年 9 月に[終了を告知](https://blog.ethereum.org/2025/09/01/holesky-shutdown-announcement) | 終了 |
| [Hoodi](https://github.com/eth-clients/hoodi) | 2025-03-17 に開始。validator とインフラの試験用で、誰でも validator になれる | 稼働中 |

[ethereum.org のネットワークのページ](https://ethereum.org/en/developers/docs/networks/)（2026-09-23 更新）は、アプリの開発には Sepolia、validator の試験には Hoodi を勧めています。

Holesky の README には、当初の予定として「LTS（長期の支援）は 2027 年 12 月まで、終了は 2028 年 12 月」と書かれています。予定より 3 年早く終わったのは、Pectra の事故の後に validator の退出の待ち行列が大きく伸び、[validator の一連の操作を試せなくなった](https://blog.ethereum.org/2025/03/18/hoodi-holesky)からです。代わりに立ち上げたのが Hoodi です。

Sepolia も、後継を立てて 2027 年に終える案が [2026 年 5 月に Ethereum Magicians で提案](https://ethereum-magicians.org/t/sepolia-testnet-replacement-sunsetting/28647)されています。2026 年 11 月時点で、後継の名前と終了日は決まっていません。

<br>

#### ハードフォークはテストネットから

全ノードが同時に規則を切り替える更新（ハードフォーク）は、テストネットで先に有効にし、問題が無いことを確かめてからメインネットの時刻を決めます。手順は [Ethereum Hard Forks](../ethereum-hard-forks/) で説明しています。以下は、直近の 3 回の更新が有効になった日（UTC）です。

| 更新 | Holesky | Sepolia | Hoodi | メインネット |
| --- | --- | --- | --- | --- |
| Pectra | 2025-02-24 | 2025-03-05 | 2025-03-26 | 2025-05-07 |
| Fusaka | 2025-10-01 | 2025-10-14 | 2025-10-28 | 2025-12-03 |
| Glamsterdam | — | 2026-10-06 | 延期（予定の 2026-10-26 を取り消し） | 未定 |

日付は、更新ごとに対象の EIP（Ethereum Improvement Proposal）を並べた Meta EIP の [EIP-7600](https://eips.ethereum.org/EIPS/eip-7600)・[EIP-7607](https://eips.ethereum.org/EIPS/eip-7607)・[EIP-7773](https://github.com/ethereum/EIPs/blob/f1ade090fd315895461fc3e249cb1a675aeb55a9/EIPS/eip-7773.md)（2026-10-22 のコミット）の表に基づきます。

Hoodi の Glamsterdam は、[ACDE #248](https://github.com/ethereum/pm/issues/2267) で議論されたセキュリティ上の懸念を受けて、予定の 4 日前に保留になりました。クライアントは予定を取り除いたリリースを出しています（例: [Nethermind 2.2.1](https://github.com/NethermindEth/nethermind/releases/tag/2.2.1)、2026-10-22）。

2026 年 11 月 10 日時点では、Glamsterdam が有効なのはテストネットの Sepolia だけです。この期間にテストネットで動いたコントラクトが、メインネットではまだ使えない命令やガスの値に頼っていることがあります。

---

### Bitcoin のテストネット

Bitcoin Core 32.1 が選べるネットワークは、メインネットのほかに 4 つあります。

| 名前 | 仕様 | ブロックを作る者 | 特徴 |
| --- | --- | --- | --- |
| testnet3 | — | 採掘する者 | BIP-94 の時点（2024 年）で 13 年続いていた。前のブロックから 20 分空くと難易度を最低に戻せる |
| testnet4 | [BIP-94](https://github.com/bitcoin/bips/blob/master/bip-0094.mediawiki) | 採掘する者 | Bitcoin Core [28.0](https://bitcoincore.org/en/releases/28.0/) で追加。testnet3 の難易度の不具合を直した |
| signet | [BIP-325](https://github.com/bitcoin/bips/blob/master/bip-0325.mediawiki) | 決められた鍵で署名できる者 | [0.21.0](https://bitcoincore.org/en/releases/0.21.0/) で追加。採掘に加えて署名が必要 |
| regtest | — | 自分の 1 台 | 難易度が最低で、コマンドでブロックを作れる |

testnet3 の「20 分」の規則は、採掘する者が少ない時にブロックが止まらないようにするためのものです。しかし、難易度を戻す計算の不具合で、短い期間に大量のブロックが作られる block storm が繰り返し起きました。

Bitcoin Core 32.1 が既定値として持つ、2026 年 9 月頃のブロックの高さ（assumevalid）は、2009 年から続くメインネットが 966,143、testnet3 が 5,128,859 です。Bitcoin Core 32.1 の `-testnet` の説明には、testnet3 の支援は非推奨で今後のバージョンで削除する、と書かれています。

signet のブロックには、決められたスクリプト（challenge）を満たす署名が必要です。既定の signet の challenge は 2 つの鍵のどちらかの署名を求めるもので、鍵を持たない者はブロックを作れません。BIP-325 は、testnet3 の大きな巻き戻しや長い停止を避け、予測できる試験環境を作ることを目的に挙げています。

---

### テストネットの通貨と faucet

テストネットの通貨は、faucet から無料で受け取ります。PoS の Ethereum のテストネットには採掘が無く、faucet の運営者が配れる量には限りがあるので、1 人あたりの量を絞ります。例えば、[Alchemy の Sepolia 向けの faucet](https://www.alchemy.com/faucets/ethereum-sepolia) は 24 時間に 0.1 ETH までで、メインネットに 0.001 ETH 以上の残高と利用の履歴があるアドレスにだけ配ります。[pk910 の faucet](https://sepolia-faucet.pk910.de/) は、受け取る代わりに計算の作業を求めます。

配る量が需要に追いつかないと、テストネットの通貨に値段が付きます。

- 2023 年 2 月、[LayerZero](https://layerzero.network/) は ETH で Goerli の ETH を買える bridge を公開し、[開発者から批判を受けました](https://www.theblock.co/post/213868/layerzero-sparks-controversy-by-making-it-possible-to-buy-testnet-ether)。合意層のクライアント [Lodestar](https://github.com/ChainSafe/lodestar) を開発する [ChainSafe](https://chainsafe.io/) は、2023 年 4 月に[市場を開いても Goerli の供給の問題は解決せず、終了予定のテストネットを使い続ける動機になる](https://blog.chainsafe.io/ethereum-testnets-goerli-eth-and-a-way-forward/)と反対しました。
- BIP-94 は testnet4 を作る理由として、Jameson Lopp 氏のメーリングリストへの投稿を引用し、testnet3 の 1 ブロックの報酬が約 0.014 tBTC まで減って採掘では通貨が配れなくなったことと、tBTC が売買され「テストネットの通貨は価値を持たない」という前提が崩れたことを挙げています。

<br>

価値が無いので扱いを気にしなくてよい、と思うかもしれません。しかし、Ethereum の EOA（秘密鍵で操作するアカウント）のアドレスは、[Ethereum Address](../ethereum-address/) で説明したように、秘密鍵だけから計算され、chain ID は入りません。テストネットで使っている鍵は、そのままメインネットの同じアドレスの鍵です。テストネット用だからと設定ファイルに書いた鍵がリポジトリから漏れると、同じ鍵のメインネットの資産も動かされます。

ローカルのチェーンの既定の鍵は、もっと危険です。Anvil や Hardhat の既定のアカウントの秘密鍵は公開されており、誰でも知っています。Hardhat のノードは起動時に、公開された鍵のアカウントに本番のネットワークで送った資金は失われる、と[警告を出します](https://github.com/NomicFoundation/hardhat/blob/ed85a936f4b5df0fb371ec6127fdebebf7a88b66/packages/hardhat/src/internal/builtin-plugins/node/helpers.ts#L139-L144)。

---

### 実験: chain ID による取引の区別

Anvil を chain ID 1（メインネットと同じ番号）と 11155111（Sepolia と同じ番号）の 2 台で起動し、取引を送り分けます。Anvil と、取引を作る [cast](https://getfoundry.sh/cast/overview/) は Foundry 1.7.1 の[公式イメージ](https://github.com/foundry-rs/foundry/pkgs/container/foundry)で、ネットワークを持たない [Docker](https://www.docker.com/) のコンテナで動かすので、公開のネットワークには繋がりません。秘密鍵は Anvil が公開している既定のテスト用の鍵だけを使います。

送る取引は 2 種類です。1 つは chain ID 1 向けに署名した [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559) の取引です。もう 1 つは、EIP-155 より前の形式の取引です。この形式は 6 つの項目だけを署名し、`v` は 27 か 28 で、chain ID がどこにも入りません。以下は、その署名を作る部分の抜粋です。

```python
def pre_eip155_transfer(node, nonce, value_wei):
    """Legacy transaction signed over 6 fields only: no chain ID anywhere."""
    fields = [num(nonce), num(10**9 * 2), num(21000), bytes.fromhex(BOB[2:]), num(value_wei), b'']
    sighash = node.cast('keccak', '0x' + rlp(fields).hex())
    sig = bytes.fromhex(node.cast('wallet', 'sign', '--no-hash', '--private-key', KEY, sighash)[2:])
    r, s, v = sig[:32], sig[32:64], sig[64]  # v is 27 or 28
    return '0x' + rlp(fields + [num(v), r.lstrip(b'\0'), s.lstrip(b'\0')]).hex(), v
```

全体は [eth_replay.py](lab/eth_replay.py)、環境は [README](lab/README.txt) にあります。以下が[出力](lab/output/eth_replay.txt)です。

```text
== 1. labels and state
chain        1: eth_chainId=0x1 net_version=1 code at USDC mainnet address=0x
chain 11155111: eth_chainId=0xaa36a7 net_version=11155111 code at USDC mainnet address=0x
== 2. EIP-1559 transfer signed for chain 1
raw tx: 0x02f8720180… (117 bytes, type 0x02)
decoded: chainId=0x1 signer=0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266
send to chain        1: accepted 0x236bb1433eca74dd…
send to chain 11155111: error: Error: server returned an error response: error code -32003: invalid chain id for signer
== 3. pre-EIP-155 legacy transfer (signed without chain ID)
raw tx: 0xf86b808477… (109 bytes, v=27)
send to chain 11155111: accepted 0x49dabd9cf3a78266…
send to chain        1: error: Error: server returned an error response: error code -32003: nonce too low
second raw tx (nonce 1): 0xf86b018477…, v=28
send to chain 11155111: accepted 0xb10284370368f5ef…
send to chain        1: accepted 0xb10284370368f5ef…
chain        1: Bob balance 10002.000000000000000000 ETH
chain 11155111: Bob balance 10002.000000000000000000 ETH
```

1 の結果は、chain ID 1 を名乗るノードがメインネットではないことを示します。メインネットで USDC のコードがあるアドレスに、どちらのノードもコードを持っていません。chain ID は名札で、ネットワークを決めるのは、どの履歴を持ち、どのノードと繋がっているかです。

2 の EIP-1559 の取引は、chain ID 1 のノードだけが受け付けました。3 の EIP-155 より前の取引は、同じバイト列が両方のチェーンで実行され、取引のハッシュも同じです。nonce 0 の取引が chain ID 1 で拒否されたのは、2 で nonce 0 を使った後だからで、chain ID とは関係がありません。つまり、chain ID の無い署名を規則の上で止めるのは、主に送り主の nonce が一致しないことです。

Anvil 1.7.1 はこの取引を RPC で受け付けました。一方で、Geth は [1.10.0](https://github.com/ethereum/go-ethereum/releases/tag/v1.10.0) から、EIP-155 より前の取引を RPC で既定で拒否しています。ただし、EIP-155 はこの形式の取引も引き続き有効だとしているので、ブロックに入れば実行されます。

2022 年に L2 の [Optimism](https://www.optimism.io/)（現在の OP Mainnet）で、この形式の古い取引を流してコントラクトを同じアドレスに作られた事故は、[Ethereum Address](../ethereum-address/) で説明しています。

---

### 実験: Bitcoin の 5 つのネットワーク

Bitcoin Core 32.1 を 5 つのネットワークで空の状態から起動し、同じ公開鍵から作ったアドレス、待ち受けのポート、ブロックを保存したファイルの先頭 4 バイトを並べます。Bitcoin Core は公式の Docker イメージを出していないので、[配布物](https://bitcoincore.org/bin/bitcoin-core-32.1/)を `SHA256SUMS` で確かめてから、ネットワークを持たないコンテナで動かします。

公開鍵は、秘密鍵 1 から作ったもので、誰でも知っている鍵です。このアドレスに資産を送ってはいけません。手順の全体は [btc_networks.py](lab/btc_networks.py) にあります。以下は、[出力](lab/output/btc_networks.txt)のネットワークごとの magic bytes・ポート・アドレスの先頭を並べた図です。同じ文字列になったアドレスは、黄土色の 1 つの枠にまとめています。

{{< figure src="images/mainnet-and-testnet_btc_networks.svg" alt="5 行の表のような図。main・testnet3・testnet4・signet・regtest の magic bytes は f9beb4d9・0b110907・1c163f28・0a03cf40・fabfb5da、ポートは 8333・18333・48333・38333・18444 で、全て別々の灰色の枠。pkh のアドレスは main が 1BgGZ…で、残りの 4 つは 1 つの黄土色の枠の mrCDr…。wpkh のアドレスは main が bc1qw508…、testnet3・testnet4・signet が 1 つの黄土色の枠の tb1qw508…、regtest が bcrt1qw508…" caption="Bitcoin Core 32.1 の 5 つのネットワークと、同じ鍵のアドレス" align="center" >}}

magic bytes、ポート、最初のブロックのハッシュは 5 つとも違います。signet の `0a03cf40` は、BIP-325 の通り challenge のハッシュの先頭 4 バイトを [Python](https://www.python.org/) で計算した値と一致しました。

一方で、アドレスで区別できるのは、`bc1` の形式でもメインネット・テストネット・regtest の 3 通り、古い形式（pkh）ではメインネットとそれ以外の 2 通りだけです。この鍵の pkh は 3 つのテストネットと regtest で同じ `m` で始まる文字列で、`tb1` のアドレスも testnet3・testnet4・signet で同じです。

アドレスからはテストネットかどうかまでしか分からず、どのテストネットかは分かりません。同じアドレスでも、どのチェーンの記録かで別の資産です。

```text
== regtest: mine 200 blocks to the same key
blocks=200 difficulty=4.66e-10
height   1: coinbase pays 50.0 BTC
height 149: coinbase pays 50.0 BTC
height 150: coinbase pays 25.0 BTC
height 200: coinbase pays 25.0 BTC
```

regtest では、200 個のブロックがコマンド 1 つで作られ、難易度は 4.66e-10 でした。ブロックの報酬は 150 個目で 25 BTC に半減しています。メインネットの半減は 210,000 ブロックごとで、[Bitcoin Core の設定](https://github.com/bitcoin/bitcoin/blob/v32.1/src/kernel/chainparams.cpp)では regtest だけが 150 です。ローカルのチェーンは、試験しやすいように規則の一部を変えているのです。

---

### テストネットで確かめられないこと

テストネットは、メインネットと同じソフトウェアと規則で試せる場所です。しかし、次の点はテストネットでは確かめられません。

- 混み具合と手数料: 利用者と取引の量が違うので、手数料の相場や、取引がブロックに入るまでの時間は再現できません。
- ブロックを作る者の振る舞い: Sepolia や signet では、許可された少数がブロックを作ります。取引の並べ替えで利益を得る [MEV](../mev/) や、[mempool](../mempool/) の受け入れ方針の違いは、メインネットの参加者の構成で起きます。
- 他のコントラクトとの組み合わせ: メインネットにあるコントラクトが、テストネットに無いか、違うアドレスや違うバージョンで置かれていることがあります。
- 規則の時期: 新しい規則がテストネットだけで有効な期間は、テストネットで通ったコードがメインネットで動かないことがあります。

メインネットの状態で試したい場合は、Anvil の `--fork-url` のように、メインネットのある時点の状態を写したローカルのチェーンを使えます。ただし、写した後は他の参加者の取引が入りません。
