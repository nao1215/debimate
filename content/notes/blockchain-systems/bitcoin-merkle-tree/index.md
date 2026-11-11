---
title: "Bitcoin Merkle Tree - txid の木と SPV による検証"
date: 2026-08-09
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "bitcoin"]
weight: 9
topics: ["Data Structure"]
---

Bitcoin は、ブロックに入った取引（transaction、以下の図では Tx と略します）の並びを Merkle Tree で 1 つのルートハッシュに畳み込み、80 バイトのブロックヘッダに収めています。[Bitcoin の白書](https://bitcoin.org/bitcoin.pdf)も、取引を Merkle Tree でハッシュ化し、ブロックのハッシュに入れるのはルートだけとしています。

Bitcoin で支払いを受け取る場合を考えます。送金の取引は、作られて[ネットワークに流れた](../bitcoin-transaction-lifecycle/)だけでは、まだどのブロックにも入っていません。どこかのブロックに取り込まれて初めて、共有された履歴に載ります。そのため、代金を受け取る側は、自分宛の取引がブロックに入ったことを確認してから商品を渡します。

厳密には、取引を含むブロック自身と後続のブロックを合わせた確認数（[Bitcoin Block](../bitcoin-block/) で説明）まで見て判断します。ここで扱うのは、その前段の「入ったこと」の確認です。

以下は、代金を受け取る側の携帯端末と、ブロック全体を持つ参加者が持つデータです。

{{< figure src="images/bitcoin-merkle-tree_concept.webp" alt="左の携帯端末はブロックヘッダの列だけを持つ。右の参加者が持つ 8 件の取引の木では、Tx2 からルートハッシュまでの経路が青、経路の兄弟にあたる 3 個のハッシュが黄土色、残りが灰色で、ルートハッシュは端末のヘッダの 1 つに繋がっている" caption="端末に渡るのは、経路の兄弟にあたるハッシュだけ" align="center" >}}

端末がブロック全体を持つ参加者に尋ね、「入っている」という返事を受け取っても、そのままでは証拠になりません。返事の裏を取ろうにも、ブロックチェーン全体は数百 GB（2026 年時点）あり、携帯端末の[ウォレット](../wallet/)には収まりません。上記の図のように、ヘッダにあるルートハッシュと、その取引のハッシュからルートハッシュを計算するために必要な、少数のハッシュ（包含証明、図の黄土色）を使うと、この返事を手元で検算できます。

<br>

本記事では、Bitcoin が何を葉にして木を組み立てているのか、その木で取引の包含をどう検証するのかを説明します。素朴な方法との比較から入り、次の 5 つを確かめます。

- 全件を連結してハッシュする方法と比べて、何が違うのか。
- 何を葉にして、木を組み立てるのか。
- 段のノード数が奇数の時は、どうするのか。
- 包含証明はどのような形で渡り、実際のブロックではどう検証されるのか。
- ブロックヘッダだけを持つ参加者は、何を確かめられるのか。

前提は 2 つあります。木の作り方と包含証明の仕組みは [Merkle Tree](../merkle-tree/) で、ブロック・ブロックヘッダ・取引の関係は [Bitcoin Block](../bitcoin-block/) で説明しています。木の作り方に由来する 2 つの弱点（取引の複製と 64 バイトの取引）は、[Bitcoin Merkle Tree の弱点](../bitcoin-merkle-tree-attacks/) で扱います。

---

### 全件を渡す検証との違い

取引の並びを 1 つの値で代表するだけなら、全件を順に連結してハッシュを 1 回計算すれば足ります。この方法では、ある取引の包含を確かめるたびに、数千件・数 MB のブロック全体を受け取って計算し直す必要があります。Merkle Tree の包含証明なら、受け取るのは件数の対数、数千件でもハッシュ十数個です（[Merkle Tree](../merkle-tree/) の「葉の件数と証明のサイズ」）。

以下は、ヘッダとブロック本体の大きさの関係です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    subgraph Body["ブロック本体（数 MB）"]
        TX["取引 数千件<br/>Tx0, Tx1, Tx2, ..."]
    end
    subgraph Header["ブロックヘッダ（80 バイト）"]
        R["ルートハッシュ<br/>32 バイト"]
        O["バージョン・直前のブロックのハッシュ<br/>時刻・bits・nonce"]
    end
    TX -->|"全件から計算"| R
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図のとおり、ヘッダ側の 32 バイトが本体の数千件を代表します。

---

### 葉になる txid

葉は、各取引の txid です。txid は、取引から witness データ（そのコインを使う資格を示す署名や公開鍵など。Bitcoin のコインは前の取引の出力で、[UTXO](../utxo/) で説明）を除いた形式に、[SHA-256](/notes/security/sha-256/)（Secure Hash Algorithm 256、出力が 32 バイトのハッシュ関数）を 2 回適用した値です。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    subgraph Tx["1 つの取引"]
        Base["取引本体<br/>入力（どのコインを使うか）<br/>出力（どこにいくら送るか）"]
        W["witness<br/>署名・公開鍵など"]
    end
    Base -->|"SHA-256 を 2 回"| TXID["txid<br/>本記事の木の葉"]
    W -.->|"txid には入れない"| Other["witness 用の別の木"]
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図のとおり、txid の計算に witness は入りません。

葉が並んだら、隣同士を左から順に組にして連結し、その組に SHA-256 を 2 回適用した値を 1 段上のノードにします。1 つになるまで繰り返した結果が、ブロックヘッダに入るルートハッシュです。

取引を並べる順序を決めるのはブロックを作った参加者（マイナー）で、順序が変われば別のルートハッシュになります。

<br>

witness データは、2017 年の Segregated Witness（分離された witness、SegWit）という仕様変更で、取引本体から分離した領域に置かれるようになりました。それまでは、署名も txid の計算に含まれていました（SegWit を使わない従来形式の取引では、今も含まれます）。

txid から witness を外したのは、第三者が取引の中身を変えないまま、[署名](../digital-signature/)の値だけを検証に通る別の値へ書き換えられるためです（理由は Digital Signature で説明）。

署名を txid の計算に含めると、同じ内容の取引の識別子が送金の途中で変わってしまいます。後続の取引は使うコインを前の取引の txid で指すため、まだブロックに入っていない後続の取引が使えなくなります。この問題は transaction malleability（取引展性）と呼ばれ、witness を txid の外に出したことが解決策の 1 つでした。witness は[別の木](https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki)でブロックに結び付けられており（[Bitcoin Block](../bitcoin-block/) で説明）、本記事では扱いません。

---

### 奇数の葉の複製

Bitcoin は、段の中のノード数が奇数になると最後のノードを複製してから組を作ります。代表的なノードのソフトウェアである [Bitcoin Core](https://bitcoincore.org/) の[実装](https://github.com/bitcoin/bitcoin/blob/master/src/consensus/merkle.cpp)のコメントは、この複製を「which is unusual in Merkle trees」（Merkle Tree では異例）と断っています。

例えば、取引 3 件のブロックでは、次のように複製します。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart BT
    H0["Hash0"] --> H01["Hash01"]
    H1["Hash1"] --> H01
    H2["Hash2"] --> H22["Hash22"]
    H2d["Hash2 の複製"] --> H22
    H01 --> R["ルートハッシュ"]
    H22 --> R
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図の Hash0〜Hash2 は Tx0〜Tx2 の txid で、Hash22 は Hash2 を 2 つ連結した組のハッシュです。この木は、4 件目の取引として Tx2 をもう一度並べた場合と同じ形になります。

この規則には副作用があります。3 件の並びと、Tx2 を実際に 2 回並べた 4 件の並びが、同じルートハッシュになります。SHA-256 の[衝突](../hash-function/)ではなく、木の構築規則に由来する一致です。Bitcoin Core はこの一致を検出して棄却しています。放置した場合に成り立つ攻撃と検出の方法は、[Bitcoin Merkle Tree の弱点](../bitcoin-merkle-tree-attacks/) で説明します。

複製しない規則（Certificate Transparency の仕様 [RFC 9162](https://www.rfc-editor.org/rfc/rfc9162.html#section-2.1)）を使う仕組みもあり、奇数の扱いを含む構築規則の違いは [Merkle Tree Design](../merkle-tree-design/) で扱います。

---

### 包含証明の形式と検証

以下は、取引 4 件のブロックで Tx2 の包含を示す時に渡る値です。以下では、包含を確かめる側（冒頭の携帯端末）を検証者と呼びます。各ハッシュに添えた番号は、その段の中で左から 0 始まりで数えた位置です。木と証明の読み方は [Merkle Tree](../merkle-tree/) の包含証明と同じです。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart BT
    H2["Hash2（段の中で 2）<br/>検証者が計算する"] --> H23["Hash23（段の中で 1）<br/>検証者が計算する"]
    H3["Hash3（段の中で 3）<br/>証明に含まれる"] --> H23
    H01["Hash01（段の中で 0）<br/>証明に含まれる"] --> R["ルートハッシュ<br/>検証者が計算する"]
    H23 --> R
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図で証明として渡るのは Hash3 と Hash01 の 2 個で、検証者は Tx2 から Hash2 を求め、ルートまで再計算して手元のルートハッシュと照合します。

左右の知り方は証明の形式によって異なり、Bitcoin では各段での番号から判断します。0 から数えると Hash2 は番号 2 で、偶数なので相手は右の Hash3 です。1 つ上の段で Hash23 は番号 1 になり、奇数なので相手は左の Hash01 です。

取引 4 件の実際のブロック（[ブロック 100000](https://mempool.space/block/000000000003ba27aa200b1cecaad478d2b00432346c3f1f3986da1afd33e506)）で、この情報を受け取って検証する関数を動かすプログラムが以下です。チェーンの中身を表示する Web サービス（ブロックエクスプローラ）に表示される 4 つの txid とルートハッシュを使い、図と同じ形で Tx2 の包含を確かめます。

ハッシュは内部のバイト順で渡す必要があります。ブロックエクスプローラの txid は慣習で逆順の 16 進表記になっているため、`fromHex` で反転してから渡します。

```go
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"slices"
)

// verifyMerkleProof は、葉のハッシュと包含証明からルートハッシュを再計算し、
// 期待するルートハッシュと一致するかを返します。
// path は葉に近い段から並べ、siblingIsRight[i] は path[i] が右側にあったことを表します。
func verifyMerkleProof(leaf [32]byte, path [][32]byte, siblingIsRight []bool, root [32]byte) bool {
	if len(path) != len(siblingIsRight) {
		return false
	}

	h := leaf
	for i, sibling := range path {
		if siblingIsRight[i] {
			h = doubleSHA256(h[:], sibling[:])
		} else {
			h = doubleSHA256(sibling[:], h[:])
		}
	}
	return h == root
}

// doubleSHA256 は、2 つのハッシュを連結して SHA-256 を 2 回適用します。
func doubleSHA256(left, right []byte) [32]byte {
	buf := make([]byte, 0, len(left)+len(right))
	buf = append(buf, left...)
	buf = append(buf, right...)

	first := sha256.Sum256(buf)
	return sha256.Sum256(first[:])
}

// fromHex は 16 進表記を 32 バイトに変換します。reverse が true なら
// ブロックエクスプローラの表記（逆順）を内部のバイト順に戻します。
func fromHex(s string, reverse bool) [32]byte {
	b, err := hex.DecodeString(s)
	if err != nil || len(b) != 32 {
		panic("bad hash: " + s)
	}
	if reverse {
		slices.Reverse(b)
	}
	return [32]byte(b)
}

func main() {
	// ブロック 100000 の txid とルートハッシュ（ブロックエクスプローラの表記）
	txids := []string{
		"8c14f0db3df150123e6f3dbbf30f8b955a8249b62ac1d1ff16284aefa3d06d87",
		"fff2525b8931402dd09222c50775608f75787bd2b87e56995a7bdd30f79702c4",
		"6359f0868171b1d194cbee1af2f16ea598ae8fad666d9b012c8ed2b79a236ec4",
		"e9a66845e05d5abc0ad04ec80f774a7e585c6e8db975962d069a522137b80c1d",
	}
	root := "f3e94742aca4b5ef85488dc37c06c3282295ffec960994b2c0d5ac2a25a95766"

	for _, reverse := range []bool{true, false} {
		tx0, tx1 := fromHex(txids[0], reverse), fromHex(txids[1], reverse)
		// Hash01 は本来フルノードが証明として渡す値で、ここでは手元で用意する
		hash01 := doubleSHA256(tx0[:], tx1[:])
		path := [][32]byte{fromHex(txids[3], reverse), hash01}
		ok := verifyMerkleProof(fromHex(txids[2], reverse), path, []bool{true, false}, fromHex(root, reverse))
		if reverse {
			fmt.Println("内部のバイト順に戻した場合:", ok)
		} else {
			fmt.Println("表記のまま渡した場合:", ok)
		}
	}
}
```

Go 1.26 で実行した結果が以下です。

```text
内部のバイト順に戻した場合: true
表記のまま渡した場合: false
```

1 行目のとおり、渡したハッシュ 2 個でヘッダのルートハッシュに辿り着きました。2 行目は、同じ計算を表記のまま行った場合です。手順が正しくても、バイト順を取り違えると検証は通りません。

`verifyMerkleProof` で繰り返す回数は `path` の長さです。奇数のノードを複製する Bitcoin の作り方では、葉の件数を 2 の冪に切り上げた木と同じ深さになるため、葉が n 件なら段数は `ceil(log2 n)` です。

例えば、取引が 3000 件のブロックなら段数は 12 で、32 バイトのハッシュを 12 個、合わせて 384 バイトです。そのブロック本体が 1 MB だとすると、384 バイトは 1/2000 以下に収まります。

<br>

`verifyMerkleProof` は、左右のハッシュを連結する、SHA-256 を 2 回適用する、ルートまで再計算する、の 3 つだけを抜き出したもので、Bitcoin が実際に送る証明の形式ではありません。

実際の形式は、Bitcoin の仕様変更の提案文書である BIP（Bitcoin Improvement Proposal）の [37 番](https://github.com/bitcoin/bips/blob/master/bip-0037.mediawiki)（以下 BIP 37）が定めています。ハッシュの列と一緒に取引の総数も送り、受け取った側は総数から木の形を復元します。

---

### SPV - ヘッダだけによる取引の確認

ブロックと取引を自力で完全に検証する参加者をフルノード、ブロックヘッダだけを保持して取引の有効性の検証をフルノードに任せる参加者を軽量クライアントと呼びます。冒頭の携帯端末は軽量クライアントです。軽量クライアントが持っているのは、ブロックヘッダの列だけです。ヘッダはルートハッシュを含むため、包含証明を受け取れば、その取引がヘッダの指すブロックに入っていたことを自力で確かめられます。Bitcoin の白書はこの手順を Simplified Payment Verification（簡易支払い検証）と呼んでおり、一般には SPV と略されます。

軽量クライアントとフルノードのやり取りは以下の通りです。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant C as 軽量クライアント
    participant F as フルノード
    Note over C,F: ヘッダの列は<br/>取得済み
    C->>F: Tx2 の包含証明を要求
    F-->>C: Hash3 と Hash01
    C->>C: 2 個のハッシュで<br/>ルートを再計算
    C->>C: ヘッダのルートと照合
    Note over C,F: 一致すれば Tx2 は<br/>そのブロックに<br/>入っていた
```

上記の図の最後で一致した時に確かめられたのは、Tx2 がそのブロックに入っていたことだけです。Tx2 が有効な取引であることまでは確かめていません。署名が正しいか、使おうとしているコインが既に使われていないかについては、そのブロックを受け入れたノードの判断と、後ろにブロックが積み上がった事実だけが間接的な裏付けになります。

<br>

包含の確認そのものにも、木の作り方に由来する弱点があり、特定の取引を使うと包含証明を偽れる場合があります。手順と対策は [Bitcoin Merkle Tree の弱点](../bitcoin-merkle-tree-attacks/) で説明します。

<br>

注意点として、包含証明だけでは、そのルートハッシュを含むブロックヘッダが正しいチェーンに属することまでは証明できません。

ヘッダの列のどれを正しいチェーンとして採用するかは、各ヘッダが満たす [proof of work](../proof-of-work/)（計算作業）の量と、どの列を選ぶかの規則で決まります。白書も、この検証が信頼できるのは、正直な（規則どおりに動く）ノードの計算能力が攻撃者を上回っている間だけだとしています。Merkle Tree の外側にある話なので、本記事では扱いません。

---

### 利点

- ブロック全体を持たない参加者が、取引 1 件の包含を自力で検証できる
- 証明のサイズが件数の対数で、数千件のブロックでも数百バイトに収まる
- witness を別の木に分けたことで、SegWit の取引の txid は署名の作り替えの影響を受けない

---

### 欠点

Bitcoin の Merkle Tree は、証明を小さく保つ代わりに、渡す情報をブロックへの包含に絞っています。その分、次の制約が残ります。

- 素朴に証明を要求すると、どの取引に関心があるかが相手のノードに伝わる
- SPV が確かめるのはブロックへの包含だけで、取引の有効性までは確かめない
- 複製規則の副作用として、同じルートハッシュになる別の取引の並びが存在する（検出して棄却する）
- 葉と内部ノードを区別しないため、64 バイトの取引を使って包含証明を偽れる余地がある

後ろの 2 つは [Bitcoin Merkle Tree の弱点](../bitcoin-merkle-tree-attacks/) で扱っています。

どの取引に関心があるかが伝わる問題に対して、BIP 37 は、誤検出を許す集合の判定である Bloom filter を使い、関係の無い取引もいくらか混ぜて受け取る仕組みを定めました。同じ文書によれば、絞り込みの精度を上げると自分のウォレットに関係する取引だけが届く一方で、相手のノードに取引と IP アドレスを結び付けられる場合があります。通信量と匿名性のどちらを取るかの選択になります。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant C as 軽量クライアント
    participant F as フルノード
    C->>F: 関心のある取引の絞り込み条件<br/>（わざと粗くできる）
    F-->>C: 条件に合った取引の包含証明
    Note over F: 条件が細かいほど、どの取引に<br/>関心があるかを推測しやすい
    Note over C: 条件が粗いほど、無関係の取引まで<br/>受け取り通信量が増える
```

なお Bitcoin Core は、サービス拒否攻撃の経路を断つ目的で、[0.19.0.1](https://github.com/bitcoin/bitcoin/blob/master/doc/release-notes/release-notes-0.19.0.1.md) からこの絞り込みを既定で受け付けていません。代わりに、ブロックごとの要約を配り、軽量クライアントが手元で照合する仕組み（形式は [BIP 158](https://github.com/bitcoin/bips/blob/master/bip-0158.mediawiki)、取得の手順は [BIP 157](https://github.com/bitcoin/bips/blob/master/bip-0157.mediawiki)）があり、関心のある取引を相手に伝えずに済みます。
