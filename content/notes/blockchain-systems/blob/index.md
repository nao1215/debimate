---
title: "Blob - rollup のデータを期限付きで安く置く欄"
date: 2026-11-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "rollup", "blob", "eip-4844"]
weight: 23
wrapTables: true
topics: ["Scaling"]
---

blob は、Ethereum の取引に添付できる 128 KiB のデータの塊です。2024 年 3 月の Ethereum の更新（Cancun）で、仕様の変更提案（EIP、Ethereum Improvement Proposal）の 1 つである [EIP-4844](https://eips.ethereum.org/EIPS/eip-4844) によって入りました。

blob の主な利用者は rollup です。[Rollup](../rollup/) は Ethereum の外のチェーン（L2）で取引を実行し、結果が正しいかを誰でも確認できるように、取引のデータを Ethereum（L1）に公開します。以前は、このデータを L1 の取引の data 欄（calldata）に入れていました。blob は、このデータを calldata より安く置くための欄です。以下は、2 つの置き場所で、データが残る期間を比べた図です。

{{< figure src="images/blob_concept.webp" alt="横軸は取引が入ったブロックからの日数（0〜24 日）。上段の calldata（取引の data 欄）は灰色の棒が右端まで続き、「消す期限は無い　実行中は EVM から読める」「実行と同じ gas で払う」。下段の blob（取引に添付）は青い棒が約 18 日で終わり、その先は点線の「消える」。「中身は読めない」「blob 用の gas で別に払う」" caption="calldata と blob の違い" align="center" >}}

calldata は、取引の実行中に L1 上のプログラム（コントラクト）を動かす [EVM](../evm/) から中身を読めます。プロトコルに消す期限は無く、L1 のノードが保存し続けます（ただし 2025 年 7 月から、The Merge より前の古い履歴は各ノードの判断で削除できるようになりました。[partial history expiry](https://blog.ethereum.org/2025/07/08/partial-history-exp)）。その代わり、L1 の計算と同じ gas（計算量の単位）で、計算を求める他の取引と同じ枠を奪い合って値段が付きます。

blob は約 18 日を過ぎるとノードが消してよくなり、EVM からは中身を読めません。ノードがずっと持ち続ける必要が無く、計算にも使わないため、blob には計算とは別の専用の枠と単価が設けられ、calldata より安く置けます。

rollup が必要とするのは、不正に異議を申し立てられる期間（代表的な rollup の 1 つである OP Mainnet では 7 日）の間だけ、誰でもデータを取得できることです。そのため、消える代わりに安い置き場所でも足ります。

<br>

本記事では、blob の中身をコントラクトがどう確認するか、blob がいつまで残るか、blob の手数料がどう決まるか、batch（rollup が L1 に提出する取引のまとめ）に詰める件数で 1 件あたりのコストがどう変わるかを説明します。

---

### blob の中身の確かめ方

rollup は batch の取引データを blob に置き、L1 上の rollup のコントラクトには、どの blob にデータを置いたかを記録します。後で batch の中身を争う時には、コントラクトが「この blob のこの部分の値はこれである」と確認する必要があります。しかし、コントラクトは blob の中身を読めません。そこで、blob を要約した短い値を使います。

blob は 32 バイトの要素 4096 個、合わせて 131,072 バイト（128 KiB）です。送る側は、blob から commitment（blob 全体を 48 バイトに要約した値）を計算し、そのハッシュである versioned hash（バージョン付きハッシュ）を取引に書きます。blob の本体は取引に添えてノードに渡しますが、ブロックの中の取引に残るのは versioned hash だけで、本体は後述の合意層のノードの間で配られます。

rollup のコントラクトが参照するのは、この versioned hash です。以下の図の「blob を運ぶ取引」は、ノードに渡す時の、本体を添えた形です。図は、[EVM Opcode History](../evm-opcode-history/#プリコンパイル) で使った、確認する流れを示しています。

{{< figure src="/notes/blockchain-systems/evm-opcode-history/images/evm-opcode-history_kzg.webp" alt="左の灰色の「blob を運ぶ取引」の中に、黄土色の blob（128 KiB、EVM からは読めない）と、versioned hash（commitment のハッシュ）。versioned hash から BLOBHASH の矢印で「rollup のコントラクト」へ、そこから青い「0x0a で検証（commitment が versioned hash と合うか、点 z で値 y か）」へ。下に「z・y・commitment・証明は、送る側が blob から計算して渡す」「確認できるのは、その blob のその点の値」" caption="EVM から読めない blob を 0x0a で確認する（EVM Opcode History の図の再掲）" align="center" >}}

コントラクトは、blob を運ぶ取引の実行中に BLOBHASH 命令でその取引の versioned hash を読み、記録しておきます。次に、送る側が blob から計算した値（点 z・その点での値 y・commitment・証明）を 0x0a に渡します。0x0a は、Ethereum に組み込まれた検証処理（プリコンパイル）の 1 つです。

blob の 4096 個の要素は、ある多項式の 4096 点での値とみなせます。0x0a は [KZG](https://dankradfeist.de/ethereum/2020/06/16/kate-polynomial-commitments.html) という方式の証明を使い、commitment が versioned hash と合うことと、blob の中身を多項式とみなした時に点 z で値 y を取ることを確認します。確認できるのは blob 全体ではなく、その blob のその点の値です。

---

### blob の保持期間

ブロックに入った後の blob の本体を保存するのは、Ethereum のノードのうち合意を担う側（consensus layer、合意層）で、実行を担う側（execution layer、実行層）ではありません。Cancun と同時に入った合意層の更新（Deneb）の[仕様](https://github.com/ethereum/consensus-specs/blob/master/specs/deneb/p2p-interface.md)では、ノードが他のノードから求められた時に blob を返す期間を少なくとも 4096 epoch と定めています。[epoch](../proof-of-stake/) は合意層の時間の単位で、1 epoch は 32 slot、1 slot は 12 秒なので、4096 × 32 × 12 秒で約 18 日です。

2025 年 12 月の Fulu 以降は、blob を列（column）に分けて配り、各ノードはその一部だけを持ちますが、配る期間は同じく少なくとも 4096 epoch です（[Fulu の仕様](https://github.com/ethereum/consensus-specs/blob/master/specs/fulu/p2p-interface.md)）。

rollup の出金で待つ期間（rollup の OP Mainnet では 7 日、Arbitrum One では約 6.4 日）は、この 18 日の内側に収まります（[Rollup の取引データの置き場所](../rollup/#取引データの置き場所と保持期間)で図にしています）。L2 のノードを最初から同期し直す時など、18 日より古い blob を後から使う用途では、アーカイブなどの別の保存手段が必要です。

---

### blob の手数料

blob の手数料は、取引の実行に掛かる gas とは別の、blob gas という単位で数えます。blob 1 個は 131,072 blob gas（2 の 17 乗）で、blob の大きさのバイト数と同じなので、1 バイトあたり 1 blob gas です。中身が少なくても 1 個分を払います。

blob gas の単価（blob base fee）は、[EIP-1559](../gas-eip-1559/) の base fee（ブロックの混み具合で自動的に上下する基本料金）と同じ考え方で、ブロックごとに上下します。1 ブロックに入った blob の数が目標（target）を上回ると単価が上がり、下回ると下がります。1 ブロックに入れられる blob の数には、上限（max）もあります。

<br>

上がり方は一定ではありません。目標を超えた分の blob gas は累計され（excess blob gas）、単価はその累計に対して指数関数的に上がります。混んだブロックが続くほど、急に高くなります。

target と max は、Ethereum の更新のたびに引き上げられてきました。以下は、mainnet での 1 ブロックあたりの target と max の推移です。

{{< figure src="images/blob_params.webp" alt="階段状の折れ線グラフ。横軸は 2024 年 3 月から 2026 年 11 月、縦軸は blob の個数。Cancun で目標 3・上限 6、Prague で 6・9、Fusaka の後の BPO1 で 10・15、BPO2 で 14・21 に上がる。黄土色の線が上限、青い線が目標" caption="1 ブロックあたりの blob の目標（target）と上限（max）の推移" align="center" >}}

2025 年 5 月の更新（Prague）で、target 6 個・max 9 個に引き上げられました（[EIP-7691](https://eips.ethereum.org/EIPS/eip-7691)）。2025 年 12 月 3 日の更新（Fusaka。実行層では Osaka、合意層では Fulu と呼ぶ）では、クライアントのコードを変えずに、blob の数などの設定だけを変えるハードフォーク（BPO、Blob Parameter Only。[EIP-7892](https://eips.ethereum.org/EIPS/eip-7892)）が入りました。

この仕組みで、2025 年 12 月 9 日（BPO1）と 2026 年 1 月 7 日（BPO2）に数が引き上げられ、2026 年 11 月時点の値は target 14 個、max 21 個です（[Ethereum Hard Forks](../ethereum-hard-forks/#今後の予定)）。

同じ Fusaka では、blob base fee に、実行の base fee に連動した下限も入りました（[EIP-7918](https://eips.ethereum.org/EIPS/eip-7918)）。blob の手数料が実行の手数料に比べて小さすぎると値段の調整が効かず、blob base fee が最低値の 1 wei まで下がります。そこから需要に見合う値段に戻るには、満杯に近いブロックが 1 時間以上続く必要があったためです。

---

### batch の件数と 1 件あたりのコスト

blob の手数料は 1 個単位で掛かるため、batch に詰める取引の数で、L2 の取引 1 件あたりの負担が変わります。L2 の取引 1 件を圧縮後 150 バイトと仮定し（説明用の仮の値です）、1 件あたりの L1 の gas を計算しました。

batch を出す L1 の取引には、blob gas とは別に、どの取引にも必ず掛かる基本の 21,000 の実行の gas（execution gas）が毎回掛かります（rollup のコントラクトの実行分は含めていません）。2 種類の gas は別々の base fee で値段が付くため、足さずに並べています。グラフの 2 本の線は単価の違う gas なので、線の高さどうしは比べられません。比べるのは、それぞれの下がり方です。

```python
GAS_PER_BLOB = 2**17
BLOB_BYTES = 4096 * 32
TX_GAS = 21_000
TX_BYTES = 150  # 仮定した L2 の取引 1 件の大きさ


def blobs_for(n):
    return -(-n * TX_BYTES // BLOB_BYTES)  # 切り上げ


def per_tx(n):
    """n 件の batch での、1 件あたりの execution gas と blob gas"""
    return TX_GAS / n, GAS_PER_BLOB * blobs_for(n) / n
```

上記は [lab/batch_cost.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/blob/lab/batch_cost.py) からの抜粋です。以下は、件数ごとの値を縦軸・横軸とも対数の目盛りでグラフにしたものです。

{{< figure src="images/blob_batch_cost.webp" alt="両対数の折れ線グラフ。横軸は 1 つの batch に入れる L2 の取引の件数、縦軸は L2 の取引 1 件あたりの L1 の gas。青い blob gas は 1 件の 131,072 から件数に反比例して下がり、blob が 1 個埋まる 873 件で約 150 に達した後は、blob が増えるたびに跳ねながら 150 前後に留まる。赤い execution gas は 21,000 から件数に反比例して下がり続ける" caption="batch の件数と、取引 1 件あたりの L1 の gas" align="center" >}}

blob が 1 個埋まる 873 件までは、1 件あたりの blob gas が件数に反比例して下がり、その先は 1 バイトあたり 1 blob gas、つまり 1 件 150 前後で下げ止まります（実際の符号化では 1 個に詰められる量が少し減るため、件数も少し減ります）。874 件目で 2 個目の blob が要り、一時的に 300 に跳ねます。1 個単位の課金のため、件数が少ない batch ほど 1 件あたりの負担が重くなります。

<br>

<details>
<summary>件数ごとの値（グラフの元）</summary>

```text
   txs blobs  exec gas/tx  blob gas/tx
     1     1      21000.0     131072.0
    10     1       2100.0      13107.2
   100     1        210.0       1310.7
   500     1         42.0        262.1
   873     1         24.1        150.1
   874     2         24.0        299.9
  1000     2         21.0        262.1
  2000     3         10.5        196.6
  5000     6          4.2        157.3
```

</details>

<br>

同じ計算から、全ての rollup を合わせて 1 秒に L1 へ公開できる取引の数も見積もれます。1 ブロックは 12 秒（1 slot）なので、「873 件 × 1 ブロックの blob の数 ÷ 12 秒」です。[出力](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/blob/lab/batch_cost_output.txt)の末尾は以下の通りです。

```text
txs that fill one blob: 873
Cancun 2024-03: target 3 blobs = 218 txs/s, max 6 blobs = 436 txs/s for all rollups together
Prague 2025-05: target 6 blobs = 436 txs/s, max 9 blobs = 655 txs/s for all rollups together
BPO1 2025-12: target 10 blobs = 728 txs/s, max 15 blobs = 1091 txs/s for all rollups together
BPO2 2026-01: target 14 blobs = 1018 txs/s, max 21 blobs = 1528 txs/s for all rollups together
```

1 件 150 バイトの仮定では、2026 年 11 月時点の target の 14 個で、全ての rollup を合わせて毎秒約 1,000 件、max の 21 個でも約 1,500 件です。blob の target と max は、全ての rollup が L1 に公開できるデータ量の枠になっています。

---

### blob が変えないもの

blob が下げるのは、L1 にデータを公開するコストです。シーケンサー（L2 で取引の順序を決めるサーバー）による取引の検閲、rollup のコードの欠陥、利用者が L1 に資産を戻せる時点は、blob を使っても変わりません。

rollup が L1 でどう検証されるか、出金でなぜ待つかは、[Rollup](../rollup/) で説明しています。
