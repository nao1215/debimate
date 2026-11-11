---
title: "Ethereum Transaction - 署名された実行の依頼と手数料の上限"
date: 2026-08-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum"]
weight: 14
topics: ["Transaction / Wallet"]
---

[Ethereum](https://ethereum.org/) の取引（transaction）は、EOA（Externally Owned Account、外部所有アカウント）が秘密鍵で署名した指示のデータです。[公式ドキュメント](https://ethereum.org/en/developers/docs/transactions/)も、取引はアカウントが暗号で署名して出す指示だと定義しています。送金も、コントラクト（コードを持つアカウント）の呼び出しも、コントラクトの作成も、この 1 つの形で表されます。

[ウォレット](../wallet/)の確認画面には、金額のほかに「ガスの上限」や「最大手数料」が表示されます。gas は実行の計算量を測る単位です。また、実行に失敗した取引からも手数料が引かれます。どちらも、取引が送金の指示にとどまらず、宛先のコードを動かす依頼にもなるためです。

手数料は、使った gas の量に 1 gas あたりの額を掛けて決まります。1 gas あたりの額は、[ブロック](../blockchain-basics/)（取引をまとめた記録の単位）ごとにプロトコルが決める最低額（base fee）と、ブロックを作る参加者への上乗せ（priority fee）の和です。以下は、確認画面の「最大手数料」と、実際に払う手数料の関係を面積で示した図です。

{{< figure src="images/ethereum-transaction_concept.webp" alt="横軸が gas の量、縦軸が 1 gas あたりの額の図。gasLimit と maxFeePerGas で囲んだ点線の外枠が最大手数料で、その中の、使った gas の幅で base fee の高さまでが黄土色（焼却）、その上の priority fee の帯が青（参加者へ）に塗られている。使わずに済んだ gas と単価の上限までの余りは塗られていない" caption="最大手数料の枠と、実際に払う手数料" align="center" >}}

上記の図で、送り主が取引に書くのは外枠の 2 辺です。横幅が使って良い gas の上限（gasLimit）、高さが 1 gas あたりの額の上限（maxFeePerGas）です。確認画面の「ガスの上限」は横幅の gasLimit で、「最大手数料」は外枠の面積（gasLimit × maxFeePerGas）に当たります。実際に払うのは塗った部分だけで、詳しくは「使った gas と単価による手数料」で扱います。

取引が作られてから、実行の結果の記録（レシート）が残るまでを以下に示します。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    A["取引を組み立てる<br/>宛先・金額・data<br/>gas の上限"] --> B["秘密鍵で署名する"]
    B --> C["ネットワークに流す"]
    C --> D["ブロックに取り込まれ<br/>実行される"]
    D --> E["レシートに結果が残る"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図で秘密鍵を使うのは、署名の段階だけです。[中継するノード](../mempool/)が中身を書き換えること自体はできます。書き換えた取引がどう扱われるのかは、「署名からの送り主の復元」で扱います。

<br>

本記事では、1 件の取引に何が書かれ、送り主がどう確かめられ、手数料がどう決まるのかを説明します。手掛かりにするのは次の疑問です。

- 取引には、なぜ gas の上限を書くのか。
- 1 件の取引には、どの項目が書かれるのか。
- 送り主は、どのように確かめられるのか。
- 手数料は、どのように決まるのか。
- 中の送金が失敗しても、取引が成功として残るのはなぜか。

アカウントが持つ状態と nonce による順序は [Ethereum Account Model](../ethereum-account-model/) で扱っており、[EVM](../evm/)（Ethereum Virtual Machine）の命令とコントラクトの書き方は本記事では扱いません。

---

### 取引に gas の上限を書く理由

[コントラクト](../smart-contract/)とは、アドレスの下にコードと storage（値を保存する領域）を持つアカウントです。取引の宛先がコードを実行するアカウントであれば、そのコードが EVM で実行されます。

[Bitcoin](https://bitcoin.org/) の取引（[UTXO](../utxo/) を消費して作る形）は、検証に必要な手間が中身からほぼ決まります。Ethereum の取引は宛先のコードを動かせるため、何段階の処理になるのかがデータを見ただけでは分かりません。

Ethereum では、ブロックに入った取引を全てのノードが自分で実行し直し、結果を確かめます。素朴に「実行が終わるまで動かす」形にすると、終わらない処理を含む取引を 1 件流すだけで、全ノードの計算を占有できます。そこで、実行の量を [gas](https://ethereum.org/en/developers/docs/gas/) で測り、上限を設けます。

[公式ドキュメント](https://ethereum.org/en/developers/docs/gas/)は、1 件あたりの上限を課す理由として、コードの中の意図しない、または悪意のある無限ループなど、計算の浪費を防ぐことを挙げています。送り主は、その取引が使って良い gas の上限（gasLimit）を自分で書きます。処理が終わらなくても、実行は gasLimit で止まります。

---

### 取引に書かれる項目

以下は、今のウォレットが送金やコントラクトの呼び出しで作る取引の主な項目です。手数料の上限を 2 つ書く型の取引で、型の違いは後で説明します。

| 項目 | 何を決めるか |
| --- | --- |
| nonce | 送り主のアカウントの通し番号 |
| to | 宛先のアドレス。空のバイト列にすると新しいコントラクトの作成になる |
| value | 宛先に送る ETH（Ethereum の通貨）の量。単位は最小単位の wei で、1 ETH は 10 の 18 乗 wei |
| data | 宛先のコードに渡す任意の長さのデータ |
| gasLimit | この取引が使って良い gas の上限 |
| maxFeePerGas | 1 gas あたりに払う額の上限 |
| maxPriorityFeePerGas | 1 gas あたりで、ブロックを作る参加者に渡す分の上限 |
| accessList | 実行中に触る予定のアドレスと storage key を先に申告する。使わない場合は空のリストにする |
| chainId | どのチェーン向けの取引か |
| 署名 | 送り主が承認した証拠。`r`、`s` と、公開鍵の復元に使う `yParity` |

nonce が何を防ぎ、どの範囲の順序を縛るのかは [Ethereum Account Model](../ethereum-account-model/) で扱っています。value と data は独立していて、`value` が 0 でも `data` を渡してコントラクトを呼べます。

accessList は、後から足された省略できる項目です。足したのは仕様変更の提案書である EIP（Ethereum Improvement Proposal）の 1 つ、[EIP-2930](https://eips.ethereum.org/EIPS/eip-2930) です。申告したアドレスと storage key は、実行中のアクセスが安く済みます。ただし、列挙した分にも gas が掛かるので、実行中に触らない項目まで並べると、申告の分だけ gas が増えます。

<br>

#### 先頭 1 バイトで分かれる取引の型

取引の形は 1 通りではなく、先頭の 1 バイトが中身の読み方を決めます。[EIP-2718](https://eips.ethereum.org/EIPS/eip-2718) は「`TransactionType || TransactionPayload` is a valid transaction」（型の番号と、型ごとの中身を繋いだものが有効な取引になる）と定めています。

上記の表の型は、1 gas あたりの額を base fee と priority fee に分ける今の決め方を入れた [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559) が定めた、番号 0x02 の型で、Type 2 transaction と呼ばれます。

型の番号を持たない古い形の取引（legacy transaction）も、今も使えます。こちらは Ethereum の符号化規則である RLP（Recursive Length Prefix）で項目のリストを符号化したもので、先頭のバイトは 0xc0〜0xfe の範囲に入ります（0xff は将来の拡張用に予約されています）。型の番号はこれと重ならない 0x7f 以下に置かれるので、先頭の 1 バイトを見ればどちらの形かが分かります。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    B["取引の先頭 1 バイト"] --> Q{"値の範囲"}
    Q -->|"0x00〜0x7f"| N["型の番号（TransactionType）<br/>続きは型ごとの中身"]
    Q -->|"0xc0〜0xfe"| L["legacy transaction<br/>RLP で符号化した並び"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図で、型の番号を持つ側の取引を typed transaction と呼び、Type 2 もここに入ります。この分岐があるため、新しい項目を持つ型を足しても、古い形の取引はそのまま検証できます。legacy transaction は、手数料の上限 2 つの代わりに 1 gas あたりの単価 gasPrice を 1 つだけ持ち、chainId を独立した項目としては持ちません。

ほかに、大きなデータ（blob）を伴う 0x03 の型（[Blob のノート](../blob/)で扱います）や、EOA がコントラクトのコードに実行を委ねる 0x04 の型（[EIP-7702](https://eips.ethereum.org/EIPS/eip-7702)）もあります。どちらも本記事では扱わず、手数料も実行に使う gas の分だけを扱います。

---

### 署名からの送り主の復元

上記の表に、送り主のアドレスを書く項目がありません。取引のデータには送り主が入っておらず、署名から復元します。EOA の公開鍵は、楕円曲線を使う署名方式である ECDSA の署名の `r`、`s` と、`yParity`（legacy transaction では `v`）から導けます（[『Mastering Ethereum』第 2 版の第 6 章](https://masteringethereum.xyz/chapter_6.html)）。

復元した公開鍵から[アドレスを計算](../ethereum-address/)すれば送り主が分かり、そのアカウントの nonce と残高で取引を受け付けられるかを照合します。

ここでの復元は、手元の公開鍵で署名を検証する操作とは別です。ECDSA では、署名と対象のデータから公開鍵の候補が求まり、legacy transaction の `v` や typed transaction の `yParity` が、どれを使うのかを指します。署名の計算は [Digital Signature](../digital-signature/) で扱っています。

署名から送り主が決まるまでの流れを図にすると、以下のようになります。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    H["署名の対象になった<br/>取引のデータ"] --> P["公開鍵を復元する"]
    S["署名 r, s と yParity"] --> P
    P --> A["アドレスを計算する"]
    A --> C["そのアカウントの<br/>nonce と残高を照合する"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図で、取引のデータを 1 バイトでも書き換えると、署名の対象が変わります。元の署名をそのまま付けても、復元されるのは元の送り主とは別のアドレスになるか、復元そのものが失敗します。どちらにしても、元の送り主が承認した取引としては成立しません。

同じ鍵とアドレスは、Ethereum 本体とテスト用のネットワークなど、複数のチェーンで使えます。署名済みの取引をそのまま[別のチェーンに流される](../replay-protection/)と、送り主が承認していない送金が成立してしまいます。これを防ぐために、署名の対象に [chain ID](../mainnet-and-testnet/#ethereum-の-chain-id-と-network-id) を入れます。

chain ID が署名の対象に入るかどうかは、取引の形で変わります。typed transaction と、[EIP-155 に従う legacy transaction](https://eips.ethereum.org/EIPS/eip-155) では、署名のためのハッシュを計算する対象に chain ID を含めます。同じ EIP は、chain ID を含めない以前の署名も引き続き有効だと書いており、その形の取引に chain ID は入らず、別のチェーンへ流されることを防げません。

---

### 使った gas と単価による手数料

送り主が払う額は、`使った gas × (base fee + priority fee)` で決まります。base fee はブロックごとに決まる 1 gas あたりの最低額で、priority fee は[ブロックを作る参加者](../proof-of-stake/)に渡す上乗せ分です。

[公式ドキュメント](https://ethereum.org/en/developers/docs/gas/)には、base fee の分が焼却されて流通から取り除かれ、priority fee の分が参加者に渡ると説明されています。

取引に書く 2 つの上限は、この式の別々の箇所を制限します。冒頭の図で言えば、gasLimit が外枠の横幅で、maxFeePerGas が高さです。コードを持たないアカウントに data 無しで ETH を送るだけなら 21,000 gas で、data を付けたりコードが動いたりすると増えます。

実際に渡る priority fee は、maxPriorityFeePerGas と、maxFeePerGas から base fee を引いた残りのうち、小さい方になります。base fee が maxFeePerGas を超えている間、その取引は取り込まれません。

例えば、1 ETH を送る単純な送金に、gasLimit 21,000、maxFeePerGas 30 gwei、maxPriorityFeePerGas 2 gwei を書いたとします。gwei は 10 億 wei です。以下は、ブロックの base fee ごとの支払いです。

| base fee | 渡る priority fee | 1 gas あたりの単価 | 手数料 |
| --- | --- | --- | --- |
| 10 gwei | 2 gwei | 12 gwei | 252,000 gwei（0.000252 ETH） |
| 29 gwei | 1 gwei | 30 gwei | 630,000 gwei（0.00063 ETH） |
| 31 gwei | なし | なし | 取り込まれない |

base fee が 10 gwei なら、0.00021 ETH が焼却され、0.000042 ETH が参加者に渡ります（公式ドキュメントの例と同じ数値です）。base fee が 29 gwei に上がると、上乗せは maxFeePerGas までの残りの 1 gwei に削られます。base fee が 31 gwei の行の取引は、拒否されて消えるのではなく、base fee が 30 gwei 以下に下がるまでブロックに入らないまま待つことになります。待っている取引をノードがどう扱うかは [Gas and EIP-1559](../gas-eip-1559/) で確かめています。

実行が gasLimit に届かずに終われば、使わずに済んだ分は手数料になりません。それでも取引がブロックに入るには、`gasLimit × maxFeePerGas + value` の残高が必要で、上記の例では 1.00063 ETH です。

ウォレットの確認画面に出る「最大手数料」は、実際に引かれる額ではなく、この `gasLimit × maxFeePerGas`（上記の例では 0.00063 ETH）を指します。

送り主が取引に書けるのは上限までで、払う額は、使った gas と、取り込まれたブロックの base fee が分かるまで確定しません。

<br>

#### 混雑で上がる base fee

base fee は、前のブロックの混み具合で上下します。1 ブロックに入る取引の gas の合計にも上限（取引の gasLimit とは別の、ブロックの gas 上限）があり、使った gas がその半分（target）を超えると次の base fee が上がり、下回ると下がります。1 ブロックで動く幅は最大 12.5%（8 分の 1）です。式と、ローカルのノードで実測した推移は [Gas and EIP-1559](../gas-eip-1559/) で扱っています。

上記の例に当てはめると、満杯のブロックが続けば base fee は 1 ブロックごとに 1.125 倍になり、10 gwei からは 10 ブロック目（1 ブロック 12 秒で約 2 分後）に 30 gwei を超えて、表の 3 行目の状態になります。送った時点の base fee の 3 倍を上限に書いても、混雑が 2 分続けば足りなくなる計算です。

---

### 実行が止まった時に消費する gas

取引には、実行を始める前に必ず掛かる intrinsic gas があります。上に挙げた単純な送金なら 21,000 で、data や accessList を付ければ、その内容に応じて増えます。

実行を始めた後は、コードが条件を満たさない時（例えば、送ろうとした[トークン](../erc-20/)の残高が足りない時）に、EVM の `REVERT` 命令で自分から実行を中止し、状態の変更を取り消せます。以下は、gasLimit と実行の進み方によって、消費される gas が分かれる様子です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    T["取引"] --> Q{"gasLimit が<br/>intrinsic gas に届くか"}
    Q -->|"届かない"| X["検証の段階で拒否<br/>ブロックに入らず<br/>gas も消費しない"]
    Q -->|"届く"| E["実行を始める"]
    E -->|"最後まで終わる"| D["使った gas の分だけ払う"]
    E -->|"REVERT で中止"| RV["状態の変更を取り消す<br/>使った分は払い<br/>残った gas は消費しない"]
    E -->|"途中で gas を使い切る"| OG["状態の変更を取り消す<br/>gasLimit の分を全て消費"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図のうち、手数料を払わずに済むのは、検証の段階で拒否される経路だけです。[gas の公式ドキュメント](https://ethereum.org/en/developers/docs/gas/)の例では、単純な送金に 20,000 の gasLimit を付けた取引は、検証の段階で拒否されます。

---

### レシートに残る実行の結果

ブロックに入ったことは、実行が成功したことを意味しません。Ethereum は、取引として有効かどうかの検査と、実行が成功したかどうかを分けて扱います。有効でない取引はブロックに入りませんが、有効であれば、実行に失敗しても手数料を払ってブロックに残ります。

Bitcoin にはこの 2 段の区別が無く、検証を通らない取引はブロックに入らないだけです（[Bitcoin Transaction Lifecycle](../bitcoin-transaction-lifecycle/)）。Ethereum で実行の結果を読み取る先が、取引ごとに作られる取引レシート（receipt）です。

プロトコルが定めるレシートの中身は 4 つです。[EIP-2718 には legacy receipt が `rlp([status, cumulativeGasUsed, logsBloom, logs])` と書かれています](https://eips.ethereum.org/EIPS/eip-2718)。状態コード（status）、そのブロックでこの取引までに使われた gas の累計、logs bloom、ログです。

[ログ](../evm/#イベントとログ)はコントラクトが実行中に残す出来事の記録（例えば、トークンが送られた）で、アプリはこれを読んで結果を知ります。logs bloom は、中身を読まずに、あるアドレスや出来事のログが含まれ得るかを判定するための値です。

typed transaction のレシートには、この 4 つの前に型のバイトが付きます。1 件が使った量はこの中に無く、前の取引の累計との差として求まります。

以下は、プロトコルが記録するレシートと、ノードが API で返すレシートの違いです。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    subgraph P["プロトコルが記録するレシート"]
        P1["status"]
        P2["cumulativeGasUsed<br/>ブロックでの累計"]
        P3["logsBloom"]
        P4["logs"]
    end
    subgraph R["eth_getTransactionReceipt の応答"]
        R1["status や logs など"]
        R2["gasUsed<br/>1 件が使った量"]
        R3["effectiveGasPrice<br/>実際に払った単価"]
    end
    P1 --> R1
    P4 --> R1
    P2 -.->|"前の取引の累計との差"| R2
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

ノードに問い合わせて見るのは、上記の図の右側です。[JSON-RPC のドキュメント](https://ethereum.org/en/developers/docs/apis/json-rpc/)によれば、`eth_getTransactionReceipt` は `gasUsed` と `effectiveGasPrice` も含めて返します。

`REVERT` で中止した取引も、gas を使い切った取引も、成否はレシートの中の status という 1 つの値で表されます。EIP-658 はこの項目を「[a status code, 0 indicating failure ... and 1 indicating success](https://eips.ethereum.org/EIPS/eip-658)」（0 が失敗、1 が成功を示す状態コード）と定めています。

この値が表すのは、取引のトップレベルの実行（取引の宛先として最初に呼ばれた実行）が成功したかどうかです。

2017 年 10 月の更新（Byzantium）で [EIP-140](https://eips.ethereum.org/EIPS/eip-140) が `REVERT` 命令を入れる前は、失敗した取引は必ず gas を使い切るので、使い切らなかった取引は成功したと分かりました。`REVERT` は gas を残して失敗するため、この推測は使えません。[同じ EIP](https://eips.ethereum.org/EIPS/eip-658) は、これを status を入れた理由の 1 つに挙げています。

以下は、実行の結果によって分かれる処理です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    E["ブロックの中で実行する"] --> Q{"トップレベルの実行"}
    Q -->|"成功"| S1["status 1<br/>EVM 実行による<br/>状態変更が残る"]
    Q -->|"失敗<br/>REVERT や gas 切れ"| S0["status 0<br/>EVM 実行による<br/>状態変更を取り消す"]
    S1 --> F["nonce を 1 進め<br/>消費した gas の分を支払う"]
    S0 --> F
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

取り消されるのは、EVM の実行中に生じた状態の変更です。`value` の移動も、コードが storage に書き込んだ分もここに入ります。失敗した取引で送った額は送り主に残り、消えるのは手数料の分だけということです。

一方で、取引の処理として行う nonce の更新と手数料の支払いは、どちらの経路でも残ります（[Ethereum Account Model](../ethereum-account-model/)）。冒頭で挙げた、失敗した取引からも手数料が引かれる理由はここにあります。

<br>

ただし、status が表すのはトップレベルの実行の成否だけです。コントラクトが別のコントラクトを呼び、その中で `REVERT` や gas 切れが起きても、呼び出し元が失敗を受け流して最後まで進めば、取引としては成功になります。以下は、中の呼び出しが失敗した時に、呼び出し元の扱いで status が分かれる様子です。

{{< figure src="images/ethereum-transaction_nested.webp" alt="上下 2 段の図。どちらも灰色の枠がトップレベルの実行で、中に ① 処理を始める、② 別のコントラクトを呼ぶ（赤い点線の箱、× 中で失敗）、③ の 3 つの箱が並ぶ。上段の ③ は「結果を確かめず最後まで進む」で、枠の外の緑の箱 status 1（成功として残る）に矢印が向かう。下段の ③ は「失敗を見て REVERT で中止」で、赤い箱 status 0（状態の変更を取り消す）に矢印が向かう" caption="中の呼び出しの失敗と、レシートの status" align="center" >}}

上記の図の上段では、② の中の変更だけが取り消され、① と ③ の変更は残ります。status が 1 でも、中の処理が失敗していることがあるわけです。下段のように、呼び出し元が失敗を確かめて自分も `REVERT` すれば、status は 0 になります。呼び出しの入れ子と失敗の伝わり方は、[EVM のノート](../evm/#失敗の扱い)で実験しています。

2016 年 2 月のゲーム King of the Ether Throne（新しい王が座を買うと、前の王に補償金が送られる）では、上段の形で[中の送金の失敗が見落とされました](https://www.kingoftheether.com/postmortem.html)。

ETH の受け取り手がコントラクトなら、受け取った時にそのコードが動き、gas を使います。補償金の送り先が、Ethereum のウォレットアプリ [Mist](https://github.com/ethereum/mist) の作るコントラクト型のウォレットだった時、[Solidity](https://soliditylang.org/) の `send`（受け取り側に 2,300 gas だけを渡して ETH を送る関数）では gas が足りず、送金が失敗しています。コントラクトは結果を確かめずに処理を続けたため、取引は成功として進み、補償金は送り元のコントラクトに残りました。

内側の失敗は `REVERT` ではなく gas 切れですが、呼び出し元が受け流せば取引が成功になる点は同じです。当時のレシートに status はありませんでしたが、今の規則なら 1 になります。

---

### この設計で得られる性質

以下は、実行の依頼を署名付きのデータにし、gas の上限を書かせる形から得られる性質です。

- 送り主のアドレスを書かなくても、署名から復元して残高と nonce を照合できる
- 実行の量が事前に決まらない処理でも、1 件あたりの上限を gasLimit で切れる
- 送金、コントラクトの呼び出し、コントラクトの作成が 1 つの形で表される
- 先頭 1 バイトの型により、古い形の取引を残したまま新しい項目を足せる

---

### 利用時に生じる制約

Ethereum は、実行の量が読めないコードを取引から動かせるようにしました。利用時には、次の制約があります。

- 実行に必要な gas を送る前に見積もる必要があり、外すと実行を始められないか、gas 切れで失敗する
- 実行に失敗しても、消費した gas の分の手数料は支払う。gas 切れなら gasLimit の分が消費される
- 実行時の状態によって結果が変わるため、送った時点では成否が決まらない
- 取引のデータだけでは何が起きるか読み取れず、data の中身の解釈が必要

見積もりを外した時の損失を小さくするため、ウォレットはノードに依頼し、ブロックに入れずに同じ取引を試してもらって、使われた gas の量を見積もります。試した時点と実行される時点で状態が違えば、必要な量も変わります。
