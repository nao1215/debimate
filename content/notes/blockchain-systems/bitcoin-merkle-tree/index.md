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

Bitcoin で支払いを受け取る場合を考えます。送金の取引は、作られてネットワークに流れただけでは、まだどのブロックにも入っていません。どこかのブロックに取り込まれて初めて、共有された履歴に載ります。そのため、代金を受け取る側は、自分宛の取引がブロックに入ったことを確認してから商品を渡します。

厳密には、取引を含むブロック自身と後続のブロックを合わせた確認数（[Bitcoin Block](../bitcoin-block/) で説明）まで見て判断します。ここで扱うのは、その前段の「入ったこと」の確認です。

以下は、代金を受け取る側の携帯端末と、ブロック全体を持つ参加者が持つデータです。

{{< figure src="images/bitcoin-merkle-tree_concept.svg" alt="左の携帯端末はブロックヘッダの列だけを持つ。右の参加者が持つ 8 件の取引の木では、Tx2 からルートハッシュまでの経路が青、経路の兄弟にあたる 3 個のハッシュが黄土色、残りが灰色で、ルートハッシュは端末のヘッダの 1 つに繋がっている" caption="端末に渡るのは、経路の兄弟にあたるハッシュだけ" align="center" >}}

端末がブロック全体を持つ参加者に尋ね、「入っている」という返事を受け取っても、そのままでは証拠になりません。返事の裏を取ろうにも、ブロックチェーン全体は数百 GB あり、携帯端末のウォレットには収まりません。上記の図のように、ヘッダにあるルートハッシュと、その取引のハッシュからルートハッシュを計算するために必要な、少数のハッシュ（包含証明、図の黄土色）を使うと、この返事を手元で検算できます。

<br>

本記事では、Bitcoin が何を葉にして木を組み立てているのか、その木で取引の包含をどう検証するのかを説明します。素朴な方法との比較から入り、次の 5 つを確かめます。

- 全件を連結してハッシュする方法と比べて、何が違うのか。
- 何を葉にして、木を組み立てるのか。
- 段のノード数が奇数の時は、どうするのか。
- 包含証明はどのような形で渡り、実際のブロックではどう検証されるのか。
- ブロックヘッダだけを持つ参加者は、何を確かめられるのか。

前提は 2 つあります。木の作り方と包含証明の仕組みは [Merkle Tree](../merkle-tree/) で、ブロック・ブロックヘッダ・取引の関係は [Bitcoin Block](../bitcoin-block/) で説明しています。

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

上記の図のとおり、ヘッダ側の 32 バイトが本体の数千件を代表します。ブロックと取引を自力で完全に検証する参加者をフルノード、ブロックヘッダだけを保持して取引の有効性の検証をフルノードに任せる参加者を軽量クライアントと呼びます。

---

### 葉になる txid

葉は、各取引の txid です。txid は、取引から witness データ（そのコインを使う資格を示す署名や公開鍵など）を除いた形式に、[SHA-256](/notes/security/sha-256/)（Secure Hash Algorithm 256、出力が 32 バイトのハッシュ関数）を 2 回適用した値です。

葉が並んだら、隣同士を左から順に組にして連結し、その組に SHA-256 を 2 回適用した値を 1 段上のノードにします。1 つになるまで繰り返した結果が、ブロックヘッダに入るルートハッシュです。

取引を並べる順序を決めるのはブロックを作った参加者（マイナー）で、順序が変われば別のルートハッシュになります。

<br>

witness データは、2017 年の Segregated Witness（分離された witness、SegWit）という仕様変更で、取引本体から分離した領域に置かれるようになりました。

署名は、取引の中身を変えないまま第三者が値だけを作り替えられます。署名を txid の計算に含めると、同じ内容の取引の識別子が送金の途中で変わってしまいます。

後続の取引は使うコインを前の取引の txid で指すため、txid が変わると、まだブロックに入っていない後続の取引が使えなくなります。この問題は transaction malleability（取引展性）と呼ばれ、witness を txid の外に出したことが解決策の 1 つでした。

取引と 2 つの識別子の関係は以下の通りです。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart LR
    subgraph Tx["1 つの取引"]
        Base["取引本体<br/>入力（どのコインを使うか）<br/>出力（どこにいくら送るか）"]
        W["witness<br/>署名・公開鍵など"]
    end
    Base -->|"SHA-256 を 2 回"| TXID["txid<br/>ブロックヘッダ側の木の葉"]
    Base --> WTXID["wtxid<br/>witness commitment 側の木の葉"]
    W --> WTXID
    classDef default fill:#eaf1f5,stroke:#9cabb5,color:#28343b;
```

上記の図のとおり、ブロックヘッダ側の木に witness は入りません。

仕様変更の提案文書である BIP（Bitcoin Improvement Proposal）の [141 番](https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki)は、witness まで含めた識別子である wtxid で別の木を作り、そのルートをコインベース取引（ブロックの先頭に置かれる、ブロック作成者が報酬を受け取る取引）の出力に埋め込む witness commitment を定めています。witness が改竄されていないことは、wtxid の木で保証します。

---

### 奇数の葉の複製

Bitcoin は、段の中のノード数が奇数になると最後のノードを複製してから組を作ります。[Bitcoin Core の実装](https://github.com/bitcoin/bitcoin/blob/master/src/consensus/merkle.cpp)のコメントは、この複製を「which is unusual in Merkle trees」（Merkle Tree では異例）と断っています。

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

上記の図の Hash22 は、Hash2 を 2 つ連結した組のハッシュです。この木は、4 件目の取引として Tx2 をもう一度並べた場合と同じ形になります。

複製規則の副作用として、異なる取引の並びが同じルートハッシュになる場合があります。SHA-256 の衝突ではなく、木の構築規則に由来する一致です。以下は、取引 3 件のブロックと、Tx2 を実際に 2 回並べた 4 件のブロックです。

{{< figure src="images/bitcoin-merkle-tree_duplicate.svg" alt="左は取引 3 件の正当なブロックの木で、Tx2 の隣に点線の Tx2 の複製がある。右は Tx0・Tx1・Tx2・Tx2 の 4 件を並べた無効なブロックの木。左右の木は同じ形で、ルートは同じ値になる。右の木の Tx2 と Tx2 の組を赤い点線で囲み、組の 2 つが同じなので棄却すると書いている" caption="3 件の並びと、Tx2 を 2 回並べた 4 件の並び" align="center" >}}

左の点線は計算の上だけの複製で、右の 2 つ目の Tx2 はブロックに実際に入っている取引です。どちらも同じルートになるため、ヘッダだけでは区別できません。

この一致を放置すると、[CVE-2012-2459](https://en.bitcoin.it/wiki/Common_Vulnerabilities_and_Exposures#CVE-2012-2459) の攻撃が成り立ちます。ノードは無効と判定したブロックをハッシュで覚え、同じハッシュのブロックを以後受け取りません。攻撃者が取引を複製した無効なブロックを先に送ると、同じヘッダを持つ正当なブロックまで拒まれます。

そのため Bitcoin Core は、各段で組にする 2 つのハッシュが同じになる箇所を探し、見つかったブロックはヘッダとデータが一致しないものとして棄却します。ヘッダ自体を無効として覚えないため、後から届く正当なブロックは受け入れられます。

複製しない流儀もあります。Certificate Transparency の [RFC 9162](https://www.rfc-editor.org/rfc/rfc9162.html#section-2.1) は、葉の件数から木の形を決める分割規則を使っており、奇数の扱いを含む構築規則の違いは [Merkle Tree Design](../merkle-tree-design/) で扱います。

---

### 包含証明の形式と検証

以下は、取引 4 件のブロックで Tx2 の包含を示す時に渡る値です。木と証明の読み方は [Merkle Tree](../merkle-tree/) の包含証明と同じです。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f7f1e5","noteBorderColor":"#c5b99b","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
flowchart BT
    H2["Hash2<br/>検証者が計算する"] --> H23["Hash23<br/>検証者が計算する"]
    H3["Hash3<br/>証明に含まれる"] --> H23
    H01["Hash01<br/>証明に含まれる"] --> R["ルートハッシュ<br/>検証者が計算する"]
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

[BIP 37](https://github.com/bitcoin/bips/blob/master/bip-0037.mediawiki) が定める `merkleblock` メッセージは、partial Merkle tree と呼ばれる形式で、`total_transactions`・`hashes`・`flags` の 3 つを送ります。受け取った側は取引の総数から木の形を復元し、どのノードで下に降りるかを表す `flags` のビットを深さ優先で読みながら `hashes` を消費して、ルートまで計算します。

---

### SPV - ヘッダだけによる取引の確認

軽量クライアントが持っているのは、ブロックヘッダの列だけです。ヘッダはルートハッシュを含むため、包含証明を受け取れば、その取引がヘッダの指すブロックに入っていたことを自力で確かめられます。Bitcoin の白書はこの手順を Simplified Payment Verification（簡易支払い検証）と呼んでおり、一般には SPV と略されます。

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

上記の図の最後で一致した時に確かめられたのは、Tx2 がそのブロックに入っていたことだけです。Tx2 が有効な取引であることまでは確かめていません。署名が正しいか、使おうとしている残高が既に使われていないかについては、そのブロックを受け入れたノードの判断と、後ろにブロックが積み上がった事実だけが間接的な裏付けになります。

<br>

包含の確認そのものにも、木の構造に由来する弱点があります。Bitcoin は葉と内部ノードに同じ二重 SHA-256 を使い、入力の長さでも区別していません。

- 葉の入力：取引をシリアライズしたバイト列
- 内部ノードの入力：左右の 32 バイトのハッシュを連結した 64 バイトのバイト列

witness を除いた大きさがちょうど 64 バイトの取引は、葉としても内部ノードとしても読めます。

{{< figure src="images/bitcoin-merkle-tree_64byte.svg" alt="左は葉として読む場合で、64 バイトの取引 T を二重 SHA-256 して txid になる。右は内部ノードとして読む場合で、同じ 64 バイトを左 32 バイトと右 32 バイトに分け、二重 SHA-256 して内部ノードのハッシュになる。2 つの値は同じ。右 32 バイトの下には、ハッシュが一致する点線の偽の取引がぶら下がっている" caption="同じ 64 バイトの 2 通りの読み方" align="center" >}}

ブロックに入った 64 バイトの取引を内部ノードと偽り、その下にもう 1 段の証明を付け足すと、ブロックに入っていない取引が入っているように見せかけた包含証明を作れる場合があります。木の段数は取引の総数で決まりますが、BIP 37 の総数は相手が送る値で、ヘッダには入っていません。

[BIP 54](https://github.com/bitcoin/bips/blob/master/bip-0054.md) は、witness を除いた大きさが 64 バイトの取引を無効にする規則で、この脆弱性を防ぐ案を示しています。

<br>

注意点として、包含証明だけでは、そのルートハッシュを含むブロックヘッダが正しいチェーンに属することまでは証明できません。

ヘッダの列のどれを正しいチェーンとして採用するかは、各ヘッダが満たす [proof of work](../proof-of-work/)（計算作業）の量と、どの列を選ぶかの規則で決まります。白書も、この検証が信頼できるのは、正直な（規則どおりに動く）ノードの計算能力が攻撃者を上回っている間だけだとしています。Merkle Tree の外側にある話なので、本記事では扱いません。

---

### 利点

- ブロック全体を持たない参加者が、取引 1 件の包含を自力で検証できる
- 証明のサイズが件数の対数で、数千件のブロックでも数百バイトに収まる
- witness を別の木に分けたことで、txid の木は署名の作り替えの影響を受けない
- 使い終わった取引の枝をハッシュ 1 つに置き換え、古いブロックの保存量を減らせる

4 番目について、Bitcoin の白書は、使い終わった取引を木から外し、代わりにその枝をまとめたハッシュを残すことで古いブロックを圧縮する案を挙げています。なお Bitcoin Core の枝刈りはブロックファイルごと消す別の方式で、白書のこの案は実装されていません。

---

### 欠点

Bitcoin の Merkle Tree は、証明を小さく保つ代わりに、渡す情報をブロックへの包含に絞っています。その分、次の制約が残ります。

- 素朴に証明を要求すると、どの取引に関心があるかが相手のノードに伝わる
- SPV が確かめるのはブロックへの包含だけで、取引の有効性までは確かめない
- 複製規則の副作用として、同じルートハッシュになる別の取引の並びが存在する（検出して棄却する）
- 葉と内部ノードを入力の長さで区別しないため、64 バイトの取引を使って包含証明を偽れる余地がある

どの取引に関心があるかが伝わる問題に対して、BIP 37 は、誤検出を許す集合の判定である Bloom filter を使い、関係の無い取引もいくらか混ぜて受け取る仕組みを定めました。同じ文書の説明では、絞り込みの精度を上げれば自分のウォレットに関係する取引だけが届く一方で、相手のノードに取引と IP アドレスを結び付けられる場合があります。通信量と匿名性のどちらを取るかの選択になります。

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

なお [Bitcoin Core 0.19.0.1](https://github.com/bitcoin/bitcoin/blob/master/doc/release-notes/release-notes-0.19.0.1.md) は、サービス拒否攻撃の経路を断つ目的で、この絞り込みを受け付ける設定を既定で無効にしました。代わりの仕組みとして、ブロックごとに作った要約をクライアントが取得し、手元で照合する compact block filters（形式は [BIP 158](https://github.com/bitcoin/bips/blob/master/bip-0158.mediawiki)、取得の手順は [BIP 157](https://github.com/bitcoin/bips/blob/master/bip-0157.mediawiki)）があります。
