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

`bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4` と `tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx` は、同じ公開鍵（後の実験で使う鍵）から作った [Bitcoin](https://bitcoin.org/) のアドレスです。先頭の `bc1` はメインネット、`tb1` はテストネットのアドレスであることを示し、途中の文字列は同じです。

末尾の 6 文字は誤りを見つけるための検査用の文字（チェックサム）で、先頭に合わせて変わります。

メインネット（mainnet）は、市場で価値を持つ通貨が動く本番のネットワークです。テストネット（testnet）は、メインネットとほぼ同じソフトウェアと規則で動く公開のネットワークで、価値を持たない筈の通貨で送金やプログラムを試すために使います。

さらに手元の 1 台だけで動かすローカルのチェーンがあり、Bitcoin のノードのソフトウェアである [Bitcoin Core](https://bitcoincore.org/) の regtest や、[Ethereum](https://ethereum.org/) の開発ツール [Foundry](https://getfoundry.sh/) の [Anvil](https://getfoundry.sh/anvil/overview/)・[Hardhat](https://hardhat.org/) が起動するチェーンが該当します。

例えば、[スマートコントラクト](../smart-contract/)の開発者は、ローカルのチェーンで試した後にテストネットで公開し、最後にメインネットにデプロイします。ウォレットの開発者も、利用者の資産を動かす前にテストネットで送金を確認します。

以下は、Ethereum を例に、3 種類のチェーンがいつから存在し、いつ規則が変わるかを示した図です。横軸は時間で、四角は 1 つのブロックです。テストネットの列は、Ethereum のテストネットの Sepolia です。

{{< figure src="images/mainnet-and-testnet_concept.webp" alt="左にメインネット（chain ID 1）、テストネット（Sepolia、chain ID 11155111）、ローカル（Anvil、chain ID 31337）の 3 行が並び、それぞれ四角を線で繋いだ別々の列を持つ。メインネットの列は最も左から始まり、テストネットはその途中から、ローカルは右端の数個だけ。新しい規則を示す点線はテストネットの列の中ほどにあり、メインネットでは右端の近くにある。ローカルは最初のブロックから、起動時に選んだ規則で始まっている" caption="別々に伸びる 3 種類のチェーンと、新しい規則が有効になる時期（Ethereum の例）" align="center" >}}

上記の図の 3 つの列は、どこにも繋がっていません。テストネットはメインネットより後に作られ、ローカルのチェーンは起動した時に空から始まります。同じ鍵から（Ethereum では）同じアドレスを作れても、残高や記録はチェーンごとに別々です。各列の chain ID は、Ethereum でチェーンを区別する番号で、後の節で説明します。

点線は新しい規則が有効になった時点で、薄い四角は古い規則、濃い四角は新しい規則のブロックです。新しい規則はテストネットで先に有効になり、メインネットでは後から有効になります。ローカルのチェーンは、どの規則で動かすかを起動時に自分で選びます。

<br>

本記事では、[Blockchain Basics](../blockchain-basics/) を読んだ人に向けて、メインネット・テストネット・ローカルのチェーンの違いを Ethereum と Bitcoin の両方で説明します。次の疑問を順に取り上げます。

- 3 種類のネットワークは、何が同じで何が違うのか。
- ノードや署名済みのトランザクションは、どこで自分のネットワークを見分けるのか。
- テストネットで使う鍵は、なぜメインネットでも危ないのか。
- テストネットで動いたことは、メインネットの何を保証しないのか。

テストネットが何度も入れ替わってきた経緯は [Testnet History](../testnet-history/) で説明します。L2（Ethereum の上に作る別のチェーン）のテストネットと、各ネットワークのノードの立て方は扱いません。

---

### 3 種類のネットワークの違い

3 種類のネットワークで同じなのは、トランザクションの形式、署名の方法、鍵からアドレスを計算する手順です。Bitcoin のアドレスにはネットワークの印が入るので、冒頭の例のように文字列は少し違いますが、計算の手順は同じです。そのため、ウォレットや開発ツールは、接続先を切り替えるだけで同じ操作ができます。違うのは、そのネットワークに誰が参加し、どの記録を持っているかです。

整理すると、以下の通りです。テストネットの列は、2026 年 11 月時点の Ethereum の [Sepolia](https://github.com/eth-clients/sepolia) と、Bitcoin の signet（決められた鍵の持ち主だけがブロックを作れるテストネット）を例にしています。

| 項目 | メインネット | テストネット | ローカルのチェーン |
| --- | --- | --- | --- |
| 通貨の価値 | 市場で売買される | 無い筈だが、売買された例がある | 無い |
| 通貨の入手 | 購入、ブロックを作った報酬 | faucet（無料で配る窓口）から受け取る | 起動時に配られる、好きなだけ作る |
| ブロックを作る者 | 誰でも参加できる | 許可された者に限る場合がある | 自分の 1 台 |
| 規則の切り替え | テストネットの後 | メインネットより先 | 起動時に自分で選ぶ |
| 状態 | 長い履歴と、デプロイ済みのコントラクト | 別の履歴。同じコントラクトでもアドレスが違う | 空から始まる |

上記の表の状態の行は、テストネットでの確認がメインネットでの成功を保証しない理由の 1 つです。

例えば、ドル建ての通貨（トークン）の [USDC](https://www.circle.com/usdc) は、チェーン上でアドレスを持つプログラム（コントラクト）として置かれています。このコントラクトは、[発行元の Circle の一覧](https://developers.circle.com/stablecoins/usdc-contract-addresses)によると、Ethereum のメインネットでは `0xA0b8…eB48`、Sepolia では `0x1c7D…7238` にあります。アドレスを直書きしたプログラムは、ネットワークを替えると別の相手を呼びます。

---

### ネットワークの見分け方

ネットワークを取り違えると、テストのつもりの送金がメインネットで成立したり、テストネット用のトランザクションが別のチェーンで実行されたりします。そのため、ノード同士の通信にも署名済みのトランザクションにも、ネットワークを区別する値が入っています。

<br>

#### Ethereum の chain ID と network ID

chain ID は、トランザクションの署名に入れる、チェーンを区別する番号です。2016 年に [EIP-155](https://eips.ethereum.org/EIPS/eip-155)（EIP は Ethereum の仕様の変更提案）で導入され、今のトランザクションは、署名の対象に chain ID を含めます。

Ethereum のトランザクションには送り主の欄が無く、ノードは署名と署名した内容から送り主のアドレスを計算します。そのため、署名の後で chain ID を書き換えると、計算される送り主が別のアドレスになります。そのアドレスには通常、残高も正しい nonce も無いので、トランザクションは成り立ちません。

network ID は、ノード同士の通信で使う番号です。[eth プロトコルの仕様](https://github.com/ethereum/devp2p/blob/88f1c80800d622cc3a542a2125bbe33cc18c9f9c/caps/eth.md)では、ノードは接続した直後に、network ID と genesis（最初のブロック）のハッシュなどを Status というメッセージで伝え合います。以下は、2 つの番号がどこに入っているかを並べた図です。

{{< figure src="images/mainnet-and-testnet_ids.webp" alt="左は署名済みのトランザクションで、chainId・nonce・宛先と金額・手数料と gas・data の欄が並び、その全体に「署名の対象」の括弧が付き、下に署名（v, r, s）がある。chainId の欄は黄土色。右は 2 つのノードが双方向の矢印で繋がり、その間で送る Status メッセージに networkId（黄土色）・genesis のハッシュ・forkId が入っている" caption="chain ID はトランザクションに付ける署名の中に、network ID はノード同士の Status メッセージの中にある" align="center" >}}

上記の図の通り、chain ID はトランザクションごとに署名され、network ID はノードの接続ごとに伝えられます。ノードに問い合わせる RPC（Remote Procedure Call）では、`eth_chainId` が chain ID、`net_version` が network ID を返します。

多くのネットワークでは 2 つの値が同じですが、上記の eth プロトコルの仕様には、一致するとは限らないと書かれています。例えば、[ethereum-lists/chains](https://github.com/ethereum-lists/chains/tree/7306cde75380dc59d2a4124d9711de7c52b210e1/_data/chains) の登録では、2016 年に Ethereum から分かれた [Ethereum Classic](https://ethereumclassic.org/) の chain ID は 61、network ID は Ethereum のメインネットと同じ 1 です。

このように network ID と genesis が同じチェーンでは、ノードは同じメッセージで伝える fork ID（[EIP-2124](https://eips.ethereum.org/EIPS/eip-2124)、どの更新まで有効にしたかを表す値）で相手を見分けます。署名済みのトランザクションを別のチェーンで使わせないのは、chain ID の方です。

以下は、主なネットワークの chain ID です。Hoodi は、ブロックを作るバリデータ（validator）の試験用のテストネットです。

| ネットワーク | chain ID | 2026 年 11 月の状態 |
| --- | --- | --- |
| Ethereum のメインネット | 1 | 稼働中 |
| Sepolia | 11155111 | 稼働中 |
| Hoodi | 560048 | 稼働中 |
| Anvil・Hardhat の既定 | 31337 | ローカル |

chain ID を割り当てる管理者はいません。上記の ethereum-lists/chains は利用者が登録する共有の台帳で、31337 は GoChain Testnet というネットワークの番号として登録されています。Anvil や Hardhat の既定値と重なっており、番号だけではどのネットワークかが決まらない例です。

<br>

#### Bitcoin の magic bytes・アドレス・ポート

Bitcoin Core は、メインネットのほかに、テストネットの testnet3・testnet4・signet と、ローカル用の regtest を選べます。テストネットが 3 つある理由は [Testnet History](../testnet-history/#bitcoin-のテストネット) で説明します。

Bitcoin のノードは、P2P のメッセージの先頭に、ネットワークごとに決まった 4 バイトの magic bytes を付けます。違うネットワークのノードとは、最初のメッセージで食い違うので通信になりません。既定の待ち受けポートも、ネットワークごとに違います。

人が目で見分けるのは、アドレスの接頭辞です。以下は、冒頭の 2 つのアドレスに regtest の 1 つを加えて、区切りごとに並べた図です。

{{< figure src="images/mainnet-and-testnet_bech32.webp" alt="同じ公開鍵の bc1 の形式のアドレスを 3 行に分けて並べた図。メインネットは bc・1・qw508d6qejxtdg4y5r3zarvary0c5xw7k・v8f3t4、テストネットは tb・1・同じ文字列・xpjzsx、regtest は bcrt・1・同じ文字列・ygt080。HRP と末尾の検査用の 6 文字が黄土色で、間の公開鍵から作る部分は 3 行とも同じ灰色" caption="bc1 の形式のアドレスの区切り。変わるのは HRP と検査用の文字だけ" align="center" >}}

`bc1q` で始まる形式のアドレスは [BIP-173](https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki)（BIP は Bitcoin の仕様の変更提案）の形式で、`1` より前の文字列（HRP、human-readable part）がメインネットは `bc`、テストネットは `tb` です。`1` は区切りの文字です。なお、`bc1p` で始まる形式は [BIP-350](https://github.com/bitcoin/bips/blob/master/bip-0350.mediawiki) で決められています。

regtest の `bcrt` は [Bitcoin Core の設定](https://github.com/bitcoin/bitcoin/blob/v32.1/src/kernel/chainparams.cpp)にある値です。末尾の検査用の文字は HRP を含めて計算するので、HRP を書き換えただけのアドレスは誤りとして弾かれます。

---

### 実験: chain ID によるトランザクションの区別

Anvil を chain ID 1（メインネットと同じ番号）と 11155111（Sepolia と同じ番号）の 2 台で起動し、同じトランザクションを両方に送ります。確認するのは、番号を名乗っただけではメインネットの状態は付いてこないこと、署名に入った chain ID が別のチェーンでの実行を止めることの 2 点です。

どちらも外部のネットワークに繋がらない [Docker](https://www.docker.com/) のコンテナで動かし、秘密鍵は Anvil が公開している既定のテスト用の鍵だけを使います。トランザクションは、Foundry の [cast](https://getfoundry.sh/cast/overview/) で chain ID 1 向けに署名します。以下は、手順の中心部分の抜粋です。`--nonce` と `--gas-*` はトランザクションの通し番号と手数料の指定で、本題には関係しません。

```python
a, b = Node(1), Node(11155111)  # two Anvil nodes in containers without network

log('== 1. labels and state')
for n in (a, b):
    log(f'chain {n.chain_id:>8}: eth_chainId={n.rpc("eth_chainId")} net_version={n.rpc("net_version")} '
        f'code at USDC mainnet address={n.rpc("eth_getCode", USDC_ON_MAINNET, "latest")}')

log('== 2. EIP-1559 transfer signed for chain 1')
raw = a.cast('mktx', '--private-key', KEY, '--chain', '1', '--nonce', '0',
             '--gas-limit', '21000', '--gas-price', '2gwei', '--priority-gas-price', '1gwei',
             '--value', '1ether', BOB)
for n in (a, b):
    log(f'send to chain {n.chain_id:>8}: {n.publish(raw)}')
```

`Node` はコンテナの起動と RPC の呼び出しをまとめたクラス、`KEY`・`BOB`・`USDC_ON_MAINNET` は送り主の鍵・宛先・メインネットの USDC のアドレスです。全体は [eth_replay.py](lab/eth_replay.py)、使ったイメージと版は [README](lab/README.txt) にあります。以下が[出力](lab/output/eth_replay.txt)の前半です。

```text
== 1. labels and state
chain        1: eth_chainId=0x1 net_version=1 code at USDC mainnet address=0x
chain 11155111: eth_chainId=0xaa36a7 net_version=11155111 code at USDC mainnet address=0x
== 2. EIP-1559 transfer signed for chain 1
raw tx: 0x02f8720180… (117 bytes, type 0x02)
decoded: chainId=0x1 signer=0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266
send to chain        1: accepted 0x236bb1433eca74dd…
send to chain 11155111: error: Error: server returned an error response: error code -32003: invalid chain id for signer
```

chain ID は、ノードの起動時に誰でも好きな値を名乗れる番号です。手順 1 では、どちらのノードも名乗った番号を返しますが、メインネットで USDC のコードがあるアドレスを `eth_getCode` で問い合わせると、どちらも空（`0x`）です。chain ID は名札で、ネットワークを決めるのは、どの履歴を持ち、どのノードと繋がっているかです。

2 のトランザクション（`type 0x02` は [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559) の形式）は、chain ID 1 のノードだけが受け付け、もう一方は `invalid chain id for signer` で拒否しました。署名に入った chain ID が、別のチェーンでの実行を止めています。

出力の後半では、chain ID を署名に含めない EIP-155 より前の形式でトランザクションを送り、同じバイト列が両方のチェーンで実行されることを確認しています。この使い回し（リプレイ）の仕組みと対策は [Replay Protection](../replay-protection/) で説明しています。

---

### 実験: Bitcoin の 5 つのネットワーク

Bitcoin Core 32.1 を 5 つのネットワークで空の状態から起動し、同じ公開鍵から作ったアドレス、待ち受けのポート、magic bytes を並べます。ノードは外部のネットワークに繋がらないコンテナで動かします。秘密鍵は大きな整数で、ここでは値が 1 の秘密鍵から作った公開鍵を使います。誰でも知っている鍵です。このアドレスに資産を送ってはいけません。

手順の全体は [btc_networks.py](lab/btc_networks.py)、配布物の検証などの環境は [README](lab/README.txt) にあります。以下は、[出力](lab/output/btc_networks.txt)を並べた図です。同じ文字列になったアドレスは、黄土色の 1 つの枠にまとめています。

{{< figure src="images/mainnet-and-testnet_btc_networks.webp" alt="5 行の表のような図。main・testnet3・testnet4・signet・regtest の magic bytes は f9beb4d9・0b110907・1c163f28・0a03cf40・fabfb5da、ポートは 8333・18333・48333・38333・18444 で、全て別々の灰色の枠。古い形式のアドレスは main が 1BgGZ…で、残りの 4 つは 1 つの黄土色の枠の mrCDr…。bc1 の形式のアドレスは main が bc1qw508…、testnet3・testnet4・signet が 1 つの黄土色の枠の tb1qw508…、regtest が bcrt1qw508…" caption="Bitcoin Core 32.1 の 5 つのネットワークと、同じ鍵のアドレス" align="center" >}}

図の「アドレス（bc1 の形式）」は先ほどの区切りの図と同じ形式、「アドレス（古い形式）」は `1` や `m` で始まる形式のアドレスです。main はメインネットを表す Bitcoin Core での名前で、lab の出力の `test` は testnet3 です。magic bytes とポートは 5 つとも違い、ノード同士が取り違えることはありません。

一方で、アドレスで区別できるのは、`bc1` の形式でもメインネット・テストネット・regtest の 3 通り、古い形式ではメインネットとそれ以外の 2 通りだけです。アドレスからはテストネットかどうかまでしか分からず、どのテストネットかは分かりません。同じアドレスでも、どのチェーンの記録かで別の資産です。

<br>

regtest は、ローカルで試しやすいように規則の一部を変えています。出力の続きでは、200 個のブロックをコマンド 1 つで作りました。`coinbase pays` は、そのブロックを作った者が受け取る報酬です。

```text
== regtest: mine 200 blocks to the same key
blocks=200 difficulty=4.66e-10
height   1: coinbase pays 50.0 BTC
height 149: coinbase pays 50.0 BTC
height 150: coinbase pays 25.0 BTC
height 200: coinbase pays 25.0 BTC
```

[採掘の難易度](../proof-of-work/)（メインネットの最低の難易度を 1 とした値）は 4.66e-10 と極めて低く、Bitcoin の報酬は一定のブロック数ごとに半分になり、出力でも 150 個目で 25 BTC に半減しています。メインネットの半減は 210,000 ブロックごとで、Bitcoin Core の設定では regtest だけが 150 です。

---

### 鍵の使い回し

テストネットの通貨には価値が無い筈なので、鍵の扱いも気にしなくてよい、と思うかもしれません。しかし、Ethereum のアカウントのアドレスは、[Ethereum Address](../ethereum-address/) で説明したように、秘密鍵だけから計算され、chain ID は入りません。Bitcoin も、上記の実験の通り、同じ鍵から接頭辞だけが違うアドレスができます。

テストネットで使っている鍵は、そのままメインネットの同じアドレスの鍵です。テストネット用だからと設定ファイルに書いた鍵がリポジトリから漏れると、同じ鍵のメインネットの資産も動かされます。テストネットの通貨そのものも、配る量が足りなくなって[売買された例](../testnet-history/#テストネットの通貨と-faucet)があります。

ローカルのチェーンの既定の鍵は、もっと危険です。Anvil や Hardhat の既定のアカウントの秘密鍵は公開されており、誰でも知っています。Hardhat のノードは起動時に、公開された鍵のアカウントに本番のネットワークで送った資金は失われる、と[警告を出します](https://github.com/NomicFoundation/hardhat/blob/ed85a936f4b5df0fb371ec6127fdebebf7a88b66/packages/hardhat/src/internal/builtin-plugins/node/helpers.ts#L139-L144)。

---

### テストネットで確かめられないこと

テストネットは、メインネットと同じソフトウェアと規則で試せる場所です。しかし、次の点はテストネットでは確認できません。

- 混み具合と手数料: 利用者とトランザクションの量が違うので、手数料の相場や、トランザクションがブロックに入るまでの時間は再現できません。
- ブロックを作る者の振る舞い: Sepolia や signet では、許可された少数がブロックを作ります。トランザクションの並べ替えで利益を得る [MEV](../mev/) や、ブロックに入る前のトランザクションを待たせておく [mempool](../mempool/) の受け入れポリシーの違いは、メインネットの参加者の構成で起きます。
- 他のコントラクトとの組み合わせ: メインネットにあるコントラクトが、テストネットに無いか、違うアドレスや違うバージョンで置かれていることがあります。
- 規則の時期: 新しい規則がテストネットだけで有効な期間は、テストネットで通ったコードがメインネットで動かないことがあります。次の小見出しで説明します。

メインネットの状態で試したい場合は、Anvil の `--fork-url` のように、メインネットのある時点の状態を写したローカルのチェーンを使えます。ただし、写した後は、他の参加者が送ったトランザクションが入りません。

<br>

#### ハードフォークはテストネットから

ブロックチェーンの規則を変える時は、全てのノードが決めた時刻（またはブロックの高さ）で一斉に新しい規則に切り替えます。古い規則のままのノードは新しいブロックを受け入れず、1 本の列が 2 本に分かれてしまう（冒頭の図には描いていません）ので、この種類の更新をハードフォーク（hard fork）と呼びます。

Ethereum では、冒頭の図の「新しい規則」の点線のように、ハードフォークをテストネットで先に有効にし、問題が無いことを確認してからメインネットの時刻を決めます。例えば、2025 年の更新 [Pectra](https://ethereum.org/roadmap/pectra/) は、Sepolia で 3 月 5 日、メインネットで 5 月 7 日に有効になりました（[EIP-7600](https://eips.ethereum.org/EIPS/eip-7600) の表）。

この 2 か月の間は、Sepolia で通ったコードが、メインネットではまだ使えない機能に頼っている可能性があります。

更新を決める手順は [Ethereum Hard Forks](../ethereum-hard-forks/) で、テストネットで先に有効にしたことで見つかった不具合は [Testnet History](../testnet-history/#holesky-の分岐) で説明しています。
