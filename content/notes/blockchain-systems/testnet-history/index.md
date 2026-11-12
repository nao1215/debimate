---
title: "Testnet History - テストネットが入れ替わってきた理由"
date: 2026-11-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "bitcoin", "testnet"]
weight: 4
wrapTables: true
topics: ["Introduction"]
---

テストネット（testnet）は、メインネットとほぼ同じソフトウェアと規則で動く、試験用の公開のネットワークです。メインネット・テストネット・ローカルのチェーンの違いは [Mainnet and Testnet](../mainnet-and-testnet/) で説明しました。

テストネットは一度作れば使い続けられそうに見えますが、実際には何度も作り直されています。以下は、[Ethereum](https://ethereum.org/) の主なテストネットが動いていた期間を年単位で示した図です。

{{< figure src="images/testnet-history_lifespans.webp" alt="横棒のグラフ。Ropsten 2016–2022、Rinkeby 2017–2023、Goerli 2019–2024、Holesky 2023–2025 は灰色で終了済み。Sepolia 2021– と Hoodi 2025– は青で、2026 年 11 月の点線まで続いている" caption="Ethereum の主なテストネットの稼働期間（年単位で、終了は年の中ほどに描いている。2026 年 11 月時点）" align="center" >}}

上記の図の 6 つのうち、2026 年 11 月に動いているのは青の 2 つだけです。[Bitcoin](https://bitcoin.org/) にも、作り直されたテストネットと、作り方の違うテストネットが並んでいます。

<br>

本記事では、Ethereum と Bitcoin の実例から、テストネットが入れ替わる理由を説明します。次の疑問を順に取り上げます。

- Ethereum のテストネットは、なぜ数年ごとに作り直されるのか。
- テストネットだけで起きた不具合は、何を止めたのか。
- 新しい規則は、どの順にネットワークへ広がるのか。
- Bitcoin には、なぜテストネットが 3 つあるのか。
- 価値が無い筈のテストネットの通貨は、なぜ売買されるのか。

---

### Ethereum のテストネットの入れ替わり

2022 年の [The Merge](https://ethereum.org/roadmap/merge/) で、Ethereum は採掘をやめ、預けた ETH を担保にする [PoS（Proof of Stake）](../proof-of-stake/)に移りました。PoS でブロックを提案・承認する参加者を validator と呼びます。以下は、図の 6 つのテストネットの経緯です。

| テストネット | 経緯 | 2026 年 11 月時点 |
| --- | --- | --- |
| Ropsten | 2022 年 6 月に[終了を予告](https://blog.ethereum.org/2022/06/21/testnet-deprecation)。PoS に移行済みで、2022 年の第 4 四半期に終了の予定 | 終了 |
| Rinkeby | 同じ告知で、PoS に移行せず 2023 年に終了の予定 | 終了 |
| Goerli | 2024-01-17 に Goerli で有効にした更新 [Dencun](https://eips.ethereum.org/EIPS/eip-7569) を最後とし、メインネットの Dencun の後にクライアントの開発チームが[対応を終了](https://blog.ethereum.org/2023/11/30/goerli-lts-update) | 終了 |
| [Sepolia](https://github.com/eth-clients/sepolia) | 2021 年に開始。アプリとコントラクトの試験用で、ブロックを作る validator は許可制 | 稼働中 |
| [Holesky](https://github.com/eth-clients/holesky) | 2023-09-28 に開始。validator の試験用。2025 年 9 月に、翌月の更新 Fusaka の後に大部分の validator を止めると[告知](https://blog.ethereum.org/2025/09/01/holesky-shutdown-announcement) | 終了 |
| [Hoodi](https://github.com/eth-clients/hoodi) | 2025-03-17 に開始。validator とインフラの試験用で、誰でも validator になれる | 稼働中 |

上記の表の終わり方には、主に 3 つの理由があります。

1 つ目は維持の負担です。Ropsten と Rinkeby を終える 2022 年の告知は、履歴が増え続けるとノードを動かすのが難しくなること、クライアントの開発チームが長く支えるテストネットを 2 つに絞りたいことを挙げています。

2 つ目は、Goerli のように通貨を配れなくなること（[後の節](#テストネットの通貨と-faucet)）、3 つ目は、Holesky のように不具合の後で試したい操作ができなくなることです（次の節）。

[ethereum.org のネットワークのページ](https://ethereum.org/en/developers/docs/networks/)（2026-09-23 更新）は、アプリの開発には Sepolia、validator の試験には Hoodi を勧めています。

Sepolia も、後継を立てて 2027 年に終える案が [2026 年 5 月に Ethereum Magicians で提案](https://ethereum-magicians.org/t/sepolia-testnet-replacement-sunsetting/28647)されています。2026 年 11 月時点で、後継の名前と終了日は決まっていません。

---

### Holesky の分岐

Holesky は、当初の予定より 3 年早く終わりました。Holesky の README には、当初の予定として「LTS（長期の支援）は 2027 年 12 月まで、終了は 2028 年 12 月」と書かれています。きっかけは、テストネットで先に有効にした更新で起きた不具合です。

PoS の Ethereum のノードは、2 つのソフトウェアを組み合わせて動きます。取引を実行して状態を計算する実行層のクライアント（[EVM](../evm/) を動かす側）と、どのブロックを正しいとするかを validator の間で決める合意層のクライアントです。

validator になる人は、預け入れ（deposit）用のコントラクトに ETH を送って登録します。ブロックが取り消されないことを保証する[確定（finality）](../finality/)には、validator の 2/3 の票が同じ列に集まる必要があります。

2025 年 2 月 24 日、Holesky で更新 [Pectra](https://ethereum.org/roadmap/pectra/) が有効になった直後に、ネットワークが 2 つに分かれました。以下は、分かれた 2 本の列と、確定が止まった期間を示した図です。

{{< figure src="images/testnet-history_holesky.webp" alt="左に灰色の共通の列があり、2/24 Pectra が有効になった点線の所で 2 本に分かれる。上の赤い列は誤った列で、Geth・Nethermind・Besu が受け入れ、ノードの多くが従った。下の青い列は正しい列で、Erigon・Reth は預け入れを含むブロックを拒否した。正しい列の最初の 6 個は点線の枠で、票が集まらない期間を表す。間に「確定が止まる（約 2 週間）」の矢印があり、3/10 の点線で正しい列で確定が戻る。誤った列はそこで途切れている" caption="2025 年 2 月の Holesky の分岐と、確定が止まった期間" align="center" >}}

[事後報告](https://github.com/ethereum/pm/blob/6f1d4cb01d68e07c02ed61e48a9a335f9fb787db/Network-Upgrade-Archive/Pectra/holesky-postmortem.md)によると、経緯は次の通りです。

1. Pectra で、validator の登録を処理するため、実行層のクライアントが預け入れのコントラクトの出す記録（イベント）を読むようになりました。
2. このコントラクトのアドレスは、メインネットと Holesky で違います。Holesky は `0x4242…4242` です。
3. 実行層のクライアントの [Geth](https://geth.ethereum.org/)・[Nethermind](https://github.com/NethermindEth/nethermind)・[Besu](https://github.com/besu-eth/besu) は Holesky のアドレスを正しく設定しておらず、預け入れを含むブロックで、本来は無効なブロックを有効と判定しました。
4. 同じブロックから違う結果を出したソフトウェアの間で、列が 2 本に分かれました。

図の誤った列は、Geth・Nethermind・Besu が受け入れた方です。この 3 つを使うノードが多く、事後報告によると、ノードの多くがこちらに従いました。もう一方の [Erigon](https://github.com/erigontech/erigon)・[Reth](https://github.com/paradigmxyz/reth) は、預け入れを含むブロックを拒否して正しい列に残りました。

誤った列に一度票を入れた validator は、正しい列に票を入れ直すと、矛盾する票として罰（slashing）を受けるおそれがありました。そのため正しい列へ移る調整が手間取り、確定に必要な 2/3 の票が集まらず、確定は約 2 週間止まりました。回復したのは 3 月 10 日です。

メインネットには無い、テストネットの設定だけで起きた不具合です。テストネットで先に試す手順が、メインネットの前に問題を見つけたとも言えます。

<br>

#### Hoodi への移行

validator が参加をやめる（退出する）手続きは、一度に処理できる数に上限があり、待ち行列に並んで順に処理されます。事後報告は、確定が戻った後に validator に関する処理が進み始め、退出の待ち行列が約 1.5 年分埋まったと書いています。これほど多くの退出が並んだ理由は、公開された事後報告では説明されていません。

これでは登録から退出までの [validator の一連の操作を試せない](https://blog.ethereum.org/2025/03/18/hoodi-holesky)ので、代わりに Hoodi を立ち上げました。

---

### 更新はテストネットから順に

全てのノードが同じ時刻に規則を切り替える更新（ハードフォーク）は、テストネットで先に有効にし、問題が無いことを確認してからメインネットの時刻を決めます。手順は [Ethereum Hard Forks](../ethereum-hard-forks/) で説明しています。以下は、2025 年の 2 回の更新が各ネットワークで有効になった日（UTC）です。

{{< figure src="images/testnet-history_activation.webp" alt="縦に Holesky・Sepolia・Hoodi・メインネットの 4 行、横に 2025 年の時間。Pectra は Holesky 02-24、Sepolia 03-05、Hoodi 03-26、メインネット 05-07。Fusaka は Holesky 10-01、Sepolia 10-14、Hoodi 10-28、メインネット 12-03。どちらも上の行から下の行へ順に右へずれる" caption="Pectra と Fusaka が有効になった日（2025 年、UTC）" align="center" >}}

日付は、更新ごとに対象の EIP（Ethereum Improvement Proposal、仕様の変更提案）を並べた [EIP-7600](https://eips.ethereum.org/EIPS/eip-7600)（Pectra）と [EIP-7607](https://eips.ethereum.org/EIPS/eip-7607)（Fusaka）の表に基づきます。

どちらの更新も、テストネットで 3 回有効にし、3 回目から 5〜6 週間後にメインネットで有効になっています。Pectra の Holesky と Hoodi の間が、上記の分岐と Hoodi の立ち上げの時期です。

次の更新 Glamsterdam は、Sepolia で 2026-10-06 に有効になり、Hoodi で予定していた日付は保留になりました。その経緯は [Ethereum Hard Forks](../ethereum-hard-forks/#今後の予定) で説明しています。

---

### Bitcoin のテストネット

Bitcoin のノードのソフトウェアである [Bitcoin Core](https://bitcoincore.org/) の 32.1 が選べるネットワークは、メインネットのほかに 4 つあります。BIP は Bitcoin の仕様の変更提案です。

| 名前 | 仕様 | ブロックを作る者 | 特徴 |
| --- | --- | --- | --- |
| testnet3 | — | 採掘する者 | BIP-94 が引用した 2024 年の投稿の時点で 13 年続いていた。前のブロックから 20 分空くと、最低の[難易度](../proof-of-work/)のブロックを作ってよい |
| testnet4 | [BIP-94](https://github.com/bitcoin/bips/blob/master/bip-0094.mediawiki) | 採掘する者 | Bitcoin Core [28.0](https://bitcoincore.org/en/releases/28.0/) で追加。testnet3 の難易度の不具合を直した |
| signet | [BIP-325](https://github.com/bitcoin/bips/blob/master/bip-0325.mediawiki) | 決められた鍵で署名できる者 | [0.21.0](https://bitcoincore.org/en/releases/0.21.0/) で追加。採掘に加えて署名が必要 |
| regtest | — | 自分の 1 台 | ローカル用。難易度が最低で、コマンドでブロックを作れる |

<br>

#### testnet3 の block storm

testnet3 の「20 分」の規則は、BIP-94 によると、テストネットを CPU でも採掘できるようにするためのものです。

しかし、難易度は 2016 ブロックごとに直前の値を基準に計算し直すので、区切りの最後のブロックが最低の難易度だと、次の区切りの難易度は最低の難易度を基準に計算され、最大でもその 4 倍にしかなりません。

そのため、実際の計算力に比べて難易度が低いままになり、ブロックが一気に作られます。この不具合で、短い期間に大量のブロックが作られる block storm が繰り返し起きました。

その結果、testnet3 はメインネットよりずっと長い列になっています。Bitcoin Core 32.1 のソースコードに書かれた 2026 年 9 月頃のブロックの高さ（新しいノードが同期する時の目安として埋め込まれた値）は、2009 年から続くメインネットが 966,143、testnet3 が 5,128,859 です。

Bitcoin の報酬は 210,000 ブロックごとに半分になり、この規則は testnet3 も同じなので、ブロックの多い testnet3 では報酬も小さくなります。Bitcoin Core 32.1 の `-testnet` の説明には、testnet3 の支援は非推奨で今後のバージョンで削除する、と書かれています。

<br>

#### signet

signet は、別の方向から問題を解きました。signet のブロックには、決められた[スクリプト（challenge）](../bitcoin-script/)を満たす署名が必要です。既定の signet の challenge は 2 つの鍵のどちらかの署名を求めるもので、鍵を持たない者はブロックを作れません。BIP-325 は、testnet3 の大きな巻き戻しや長い停止を避け、予測できる試験環境を作ることを目的に挙げています。

---

### テストネットの通貨と faucet

#### Ethereum の faucet

テストネットの通貨は、faucet（無料で配る窓口）から受け取ります。PoS の Ethereum のテストネットには採掘が無く、通貨は最初のブロックで割り当てた分などから配ります。faucet の運営者が配れる量には限りがあるので、1 人あたりの量を絞ります。

例えば、2026 年 11 月時点で、[Alchemy の Sepolia 向けの faucet](https://www.alchemy.com/faucets/ethereum-sepolia) は 24 時間に 0.1 ETH までで、メインネットに 0.001 ETH 以上の残高と利用の履歴があるアドレスにだけ配ります。[pk910 の faucet](https://sepolia-faucet.pk910.de/) は、受け取る代わりに計算の作業を求めます。

配る量が需要に追いつかないと、テストネットの通貨に値段が付きます。

2023 年 2 月、[LayerZero](https://layerzero.network/) は ETH で Goerli の ETH を買える [bridge](../cross-chain-bridge/)（チェーンの間で資産を移す仕組み）を公開し、[開発者から批判を受けました](https://www.theblock.co/post/213868/layerzero-sparks-controversy-by-making-it-possible-to-buy-testnet-ether)。

合意層のクライアント [Lodestar](https://github.com/ChainSafe/lodestar) を開発する [ChainSafe](https://chainsafe.io/) は、2023 年 4 月に[市場を開いても Goerli の供給の問題は解決せず、終了予定のテストネットを使い続ける動機になる](https://blog.chainsafe.io/ethereum-testnets-goerli-eth-and-a-way-forward/)と反対しました。

<br>

#### Bitcoin の tBTC

Bitcoin でも同じことが起きました。BIP-94 は testnet4 を作る理由として、Jameson Lopp 氏のメーリングリストへの投稿を引用し、2024 年の投稿の時点で testnet3 の 1 ブロックの報酬が約 0.014 tBTC まで減って、採掘では通貨が配れなくなったことを挙げています。0.014 は投稿のままの値で、規則の報酬だけを計算した値（0.0122 tBTC）とは一致しません。

さらに、tBTC（testnet3 の BTC）が売買され、「テストネットの通貨は価値を持たない」という前提が崩れたことも挙げています。

以下は、ブロックの高さごとの 1 ブロックの報酬に、2026 年 9 月頃の 2 つの高さの印を付けたグラフです。

{{< figure src="images/testnet-history_reward.webp" alt="横軸がブロックの高さ（百万）、縦軸が対数の 1 ブロックの報酬（BTC）の階段状のグラフ。50 BTC から 21 万ブロックごとに半分になる。メインネットの点は高さ 966,143 で 3.125 BTC、testnet3 の点は高さ 5,128,859 で約 0.000003 BTC" caption="ブロックの高さと 1 ブロックの報酬（手数料を除く）。規則はメインネットと testnet3 で同じ" align="center" >}}

上記のグラフの通り、[Bitcoin のテストネット](#bitcoin-のテストネット)の節で見た高さの差のために、testnet3 の報酬はその後さらに減り、メインネットの約 100 万分の 1 になっています。

通貨が配れなくなることも、テストネットを作り直す理由の 1 つです。新しいテストネットでは、最初のブロックから通貨の配り方を決め直せます。
