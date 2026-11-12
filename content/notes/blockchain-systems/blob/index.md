---
title: "Blob - 大きなデータなら calldata より安く、コントラクトからは読めないデータ置き場"
date: 2026-11-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "rollup", "blob", "eip-4844"]
weight: 23
wrapTables: true
topics: ["Scaling"]
---

blob は、Ethereum のトランザクションに添えて送る、1 個 131,072 バイト（128 KiB）のデータです。2024 年 3 月 13 日の Dencun アップグレードで、[EIP-4844](https://eips.ethereum.org/EIPS/eip-4844) として入りました。blob を添えたトランザクションは型の番号が 0x03 で、型の一覧は [Ethereum Transaction](../ethereum-transaction/) で説明しています。

blob を主に使うのは [rollup](../rollup/) です。rollup は Ethereum とは別のチェーン（L2）で多くのトランザクションを実行し、その中身をまとめて Ethereum（L1）に書き込みます。以前の書き込み先は、コントラクトに渡す入力のデータである calldata でした。

Dencun の後は書き込み先が blob に移りました。[Vitalik Buterin の振り返り](https://vitalik.eth.limo/general/2024/03/28/blobs.html)には、rollup の手数料が当初 100 分の 1 以下になったと書かれています。

{{< figure src="images/blob_overview.webp" alt="左に blob を添えたトランザクションがあり、calldata・versioned hash・blob の 3 つの部分に分かれる。calldata の中身と versioned hash は、右上の実行レイヤー（EVM が動き、ブロックに残り続ける）へ入り、calldata は CALLDATALOAD、versioned hash は BLOBHASH で読める。blob は右下のコンセンサス・レイヤーへ入り、beacon node が 4096 epoch（約 18 日）は提供する義務を負い、その先は保証されない" caption="ブロックに入った後の calldata と blob の行き先" align="center" >}}

送る時は本体を添えて実行クライアントに渡しますが、上記の図のように、ブロックに入った後の中身は、コントラクトを実行する EVM と同じ実行レイヤー（execution layer）に残りません。中身を保持して提供するのは、ブロックの合意を担うコンセンサス・レイヤー（consensus layer）のノードで、beacon node と呼ばれます。

コントラクトから見えるのは、blob の中身から計算した 32 バイトの要約値である versioned hash だけです。beacon node が blob を提供する義務も、約 18 日で終わります。その代わり、大きなデータなら calldata より安く置けます。

<br>

本記事では、rollup を作る人や、blob を添えたトランザクションをエクスプローラーやノードで見かけた人に向けて、次の疑問を扱います。

- blob の中身について、コントラクトからは何が見えるのか。
- 18 日を過ぎた blob は、どこから取り出せるのか。
- blob の手数料はどう決まり、なぜ 1 wei から急に上がったのか。
- 使用量が少ないのに、今の手数料が 1 wei まで下がらないのはなぜか。
- 小さなデータでも、calldata より blob の方が安いのか。

手元の実験は [Foundry](https://getfoundry.sh/) の anvil と cast で行います。anvil は開発用のチェーンを手元で動かすツールで、cast はそのチェーンへトランザクションを送るコマンドです。手数料は mainnet のブロックヘッダーから計算し、実資産は送りません。手数料に使う wei は ETH の最小単位で、1 gwei は 10 億 wei、1 ETH は 10 の 18 乗 wei です。

---

### calldata と blob

calldata と blob は、どちらもトランザクションと一緒にデータを Ethereum に載せる手段です。違いは、データを誰が持ち続け、誰が読めるかにあります。表に出てくる epoch は、[Proof of Stake](../proof-of-stake/) で使う時間の単位です。1 epoch は 32 slot（1 slot は 12 秒）で 6.4 分なので、4096 epoch は約 18.2 日になります。

| 項目 | calldata | blob |
| --- | --- | --- |
| 置き場所 | 実行レイヤーのブロック | コンセンサス・レイヤーの beacon node |
| 残る期間 | ブロックと一緒に残る（[古い履歴](https://blog.ethereum.org/2025/07/08/partial-history-exp)はノードが消せる） | 4096 epoch（約 18 日）は提供する義務がある |
| コントラクトから | `CALLDATALOAD` で中身を読める | `BLOBHASH` で versioned hash だけ読める |
| 課金の単位 | 1 バイトごとの gas | blob 1 個ごとに 131,072 blob gas |
| 値段の決まり方 | 実行の base fee（[EIP-1559](../gas-eip-1559/)） | blob 専用の base fee |

calldata は、実行と同じ gas で値段が付き、計算を求める他のトランザクションと同じ枠を取り合います。gas の単価である base fee は、ブロックの混み具合で上下します。コントラクトが calldata を読む仕組みは [EVM のノート](../evm/#calldata-と-abi)で扱っています。blob には、実行の gas とは別に blob gas という単位と、専用の base fee があります。

<br>

rollup がデータを Ethereum に載せるのは、誰でも後から rollup の状態を再計算でき、不正があれば指摘できるようにするためです。この性質をデータ可用性（data availability）と呼びます。

再計算に必要なのはデータそのもので、EVM の中で読めなくても構いません。不正を指摘できる期間が過ぎた後に、全てのノードが持ち続ける必要もありません。blob は、この用途に合わせて、EVM から読めない代わりに安く、期限付きで提供するデータとして作られました。rollup がデータを何に使うかは [rollup のノート](../rollup/)で扱っています。

---

### コントラクトから見えるもの

実験では、今の mainnet と同じ規則で anvil を起動し、5 バイトの `hello` を blob に入れてコントラクトへ送りました。コントラクトは、1 個目と 2 個目の versioned hash（`BLOBHASH(0)`・`BLOBHASH(1)`）と、calldata の長さ（`CALLDATASIZE`）をストレージに書くだけです。Solidity を使わず、[EVM](../evm/) の命令を並べたバイトコードを直接置いています。

```shell
# BLOBHASH(0)・BLOBHASH(1)・CALLDATASIZE をスロット 0・1・2 に書くだけのコントラクト
#   runtime: PUSH1 0 BLOBHASH PUSH1 0 SSTORE  PUSH1 1 BLOBHASH PUSH1 1 SSTORE
#            CALLDATASIZE PUSH1 2 SSTORE  STOP
runtime=6000496000556001496001553660025500
initcode=0x6011600c60003960116000f3$runtime
probe=$(cast send --from "$from" --unlocked --rpc-url "$rpc" --json --create "$initcode" | jq -r .contractAddress)

# 5 バイトの "hello" を blob に入れて、コントラクトへ送る（calldata は空）
printf 'hello' > "$out/hello.bin"
cast send "$probe" --blob --path "$out/hello.bin" \
  --from "$from" --unlocked --rpc-url "$rpc" --json > "$out/blob_receipt.json"
```

上記は抜粋で、anvil の起動・終了と結果の書き出しを含む全体は [basics.sh](lab/basics.sh) にあります。結果は次の通りです。

```text
receipt.type        0x3
receipt.gasUsed     47523
receipt.blobGasUsed 131072
tx.input            0x
tx.blobVersionedHashes[0] 0x01ff8e9b72e2fc56d17f411e4eeecafb8c2c62130d1032145753fa173630f951
slot0 BLOBHASH(0)   0x01ff8e9b72e2fc56d17f411e4eeecafb8c2c62130d1032145753fa173630f951
slot1 BLOBHASH(1)   0x0000000000000000000000000000000000000000000000000000000000000000
slot2 CALLDATASIZE  0
0x01 + sha256(commitment)[1:] 0x01ff8e9b72e2fc56d17f411e4eeecafb8c2c62130d1032145753fa173630f951
```

コントラクトに届いたのは、32 バイトの versioned hash と、長さ 0 の calldata です。`hello` の 5 バイトは、どの命令を使っても EVM から読めません。blob は 1 個だけなので、`BLOBHASH(1)` は 0 を返しました。

{{< figure src="images/blob_contract_view.webp" alt="左に blob を 64 × 64 のマスで描き、1 マスが 32 バイト、全体で 4096 個 × 32 バイト = 131,072 バイト。左上の 2 マス（64 バイト）にデータの長さと hello の 5 バイトが入り、残りは 0 でも blob gas は 131,072 を払う。blob から KZG commitment（48 バイト）を作り、SHA-256 の先頭 1 バイトを 0x01 に替えて versioned hash 0x01ff8e9b…30f951 にする。右のコントラクトの中では BLOBHASH(0) がこの値を返し、CALLDATASIZE は 0、blob の中身を読む命令は無い" caption="5 バイトの blob と、コントラクトから見える値" align="center" >}}

上記の図で、versioned hash は blob から直接は作りません。先に blob から 48 バイトの KZG commitment を計算し、その [SHA-256](../../security/sha-256/) の先頭 1 バイトを 0x01 に替えた値です。

実験の出力でも、commitment から計算した最終行の値が `BLOBHASH(0)` と一致しています。先頭の 0x01 は、将来 commitment の方式を替えた時に区別するためのバージョン番号です。

<br>

#### 中身を使いたい時

コントラクトが blob の中身を使いたい時は、中身を渡すのではなく、中身についての主張を証明付きで渡します。[KZG commitment](https://dankradfeist.de/ethereum/2020/06/16/kate-polynomial-commitments.html) は、blob を 4096 個の値を通る多項式として扱う方式です。「この blob の多項式は点 z で値 y を取る」という主張は、短い証明で検証できます。検証できるのは blob 全体ではなく、その点の値だけです。

ただし、`BLOBHASH` が返すのは、実行中のトランザクションに添えた blob の versioned hash だけです。後のトランザクションからは読めないので、rollup のコントラクトは、L2 のトランザクションを束ねた batch を受け取る時にこの値を記録します。

この検証は、EVM に組み込まれた関数であるプリコンパイルの 1 つで、アドレス 0x0a の point evaluation precompile が 50,000 gas で行います。0x0a には、記録した versioned hash と、点 z・値 y・commitment・証明を渡します。0x0a は、commitment から作った versioned hash が渡された値と一致するかも確認するので、証明が記録した blob についての主張だと結び付きます。

<br>

計算の正しさを証明で示す zk rollup は、この検証で、証明に使ったデータと blob が同じだと示します。不正の指摘を待つ optimistic rollup は、指摘する時に必要な箇所だけをコントラクトに見せます。0x0a を含むプリコンパイルの一覧は [EVM Opcode History](../evm-opcode-history/#プリコンパイル)、証明の考え方は [Zero-Knowledge Proof](../zero-knowledge-proof/) で扱っています。

<br>

#### 131,072 バイト全部は使えない

KZG commitment の計算では、blob を 32 バイトずつ区切り、それぞれをある素数より小さい整数として扱います。そのため、各 32 バイトの先頭を 0 にして 31 バイトずつ詰める符号化がよく使われます。

cast の符号化では、最初の 32 バイトをデータの長さに使います。実験の blob でも、先頭の 32 バイトに長さの 5 が入り、`hello` は次の 32 バイトから始まっていました。残る 4095 個に 31 バイトずつ詰めるので、1 個の blob に入るのは 4095 × 31 = 126,945 バイトです。一方で、課金は blob の個数で決まります。今回の 5 バイトでも `blobGasUsed` は 131,072 で、1 個を満たした時と同じ額を払っています。

<br>

#### ノードの RPC から取れるもの

anvil は、トランザクションの照会（`eth_getTransactionByHash`）で blob の中身も返します。これは開発用の anvil が手元に持っているからです。mainnet の実行クライアントに同じ照会をしても、返るのは versioned hash だけです。

中身は beacon node の [Beacon API](https://ethereum.github.io/beacon-APIs/) にある `/eth/v1/beacon/blobs/{block_id}` から、ブロックやスロットを指定して取ります。

---

### 18 日を過ぎた blob

beacon node が blob を提供する義務は、コンセンサス・レイヤーの[仕様](https://github.com/ethereum/consensus-specs/blob/master/specs/deneb/p2p-interface.md)にある `MIN_EPOCHS_FOR_BLOB_SIDECARS_REQUESTS` で 4096 epoch と決まっています。4096 epoch は消す期限ではなく、提供する義務がある最短の期間です。2026-11-12 に、公開の beacon node（publicnode）へ約 45 日前に作られたスロットについて blob を問い合わせました。

```text
GET https://ethereum-beacon-api.publicnode.com/eth/v1/beacon/blobs/15315356
  slot 15315356  (2026-09-28 15:11:35 UTC, 324,010 slots = 45.0 days before head)
  HTTP 200, 5,505,185 bytes, 21 blobs of 131,072 bytes each
```

45 日前の blob も 21 個返りました。ただし、これはそのノードの設定です。60 日前のスロットを問い合わせた時は HTTP 403 が返り、その記録も [beacon_old_blobs.txt](lab/output/beacon_old_blobs.txt) に残しています。期間を過ぎた blob は、[Blobscan](https://blobscan.com/) のように blob を集めて保存するサービスか、自分で保存した写しから取ります。

<br>

<details>
<summary>Fusaka 以降は普通の beacon node から返らないことがある</summary>

2025 年 12 月の Fusaka アップグレード以降は、各ノードが blob を列に分けた一部だけを持つ方式（[PeerDAS](https://eips.ethereum.org/EIPS/eip-7594)）に変わりました。提供の期間は Fusaka 後の[仕様](https://github.com/ethereum/consensus-specs/blob/master/specs/fulu/p2p-interface.md)でも同じ 4096 epoch です。一方で [Beacon API の仕様](https://github.com/ethereum/beacon-APIs/blob/6bc8c7bde19d0499f88e67417419eb12331438f4/apis/beacon/blobs/blobs.yaml#L11)では、先の API が blob を返す義務を負うのは、全ての列を持つ supernode だけになりました。

</details>

<br>

optimistic rollup で不正を指摘できる challenge 期間は、OP Mainnet で 7 日、Arbitrum One で約 6.4 日です。どちらも 18 日の内側に収まり、その関係は [rollup のノート](../rollup/#トランザクションデータの置き場所と保持期間)に図があります。一方で、L2 のノードを最初から同期し直す時や、エクスプローラーやインデクサーのように過去の blob を読み直す時は、18 日に縛られない保存先が必要です。

---

### blob の手数料 {#blob-の手数料}

blob の値段は、ブロックごとに 1 つ決まる blob 専用の base fee で決まります。これは blob gas 1 あたりの単価で、1 個の blob は 131,072 blob gas なので、blob 1 個の手数料は 131,072 × 単価です。

単価の上下は、[EIP-1559](../gas-eip-1559/) の base fee と同じく、ブロックに載った量が、1 ブロックで目指す blob の量である target より多いか少ないかで決まります。target と上限（max）は、次のように変わってきました。

| 有効になった日 | アップグレード | target | max |
| --- | --- | --- | --- |
| 2024-03-13 | Dencun | 3 | 6 |
| 2025-05-07 | Pectra（[EIP-7691](https://eips.ethereum.org/EIPS/eip-7691)） | 6 | 9 |
| 2025-12-03 | Fusaka | 6 | 9 |
| 2025-12-09 | Fusaka の BPO1 | 10 | 15 |
| 2026-01-07 | Fusaka の BPO2 | 14 | 21 |

BPO（Blob Parameter Only）は、Fusaka で入った [EIP-7892](https://eips.ethereum.org/EIPS/eip-7892) の仕組みで、blob の個数と単価の変わり方だけを変える小さなアップグレードです。この先の予定は [Ethereum Hard Forks](../ethereum-hard-forks/#今後の予定) で扱っています。2026-11-12 に mainnet のノードへ `eth_config` を問い合わせると、有効な設定は BPO2 で、次の変更は予定されていませんでした。

<br>

#### 溜まった超過分で単価が決まる

各ブロックのヘッダーには、target を超えて使われた blob gas の累計である `excessBlobGas` があります。target より多く載ったブロックの後は増え、少ないブロックの後は減り、0 より下には下がりません。単価は、この累計を指数関数に通した値です。仕様の擬似コードを Python に写すと次のようになります。

```python
GAS_PER_BLOB = 2**17          # 131,072
MIN_BASE_FEE_PER_BLOB_GAS = 1

CANCUN = (3, 6, 3338477, False)       # (target, max, update fraction, EIP-7918 の有無)
BPO2 = (14, 21, 11684671, True)


def fake_exponential(factor, numerator, denominator):
    i, output, acc = 1, 0, factor * denominator
    while acc > 0:
        output += acc
        acc = (acc * numerator) // (denominator * i)
        i += 1
    return output // denominator


def blob_base_fee(excess, params):
    return fake_exponential(MIN_BASE_FEE_PER_BLOB_GAS, excess, params[2])
```

`fake_exponential` は、整数だけで e の excess / fraction 乗を近似する関数です。単価は最低 1 wei で、上限の個数を載せたブロックが続くと、1 ブロックごとに Dencun では 12.5%、Pectra 以降は約 8.2% ずつ上がります。全体は [blobfee.py](lab/blobfee.py) にあり、後で使う EIP-7918 の分岐も入っています。

<br>

この式で前のブロックから次の `excessBlobGas` を計算し、mainnet のヘッダーと照らしました。2024-03-27 の 800 ブロック（Cancun の式）と、2026-11-12 の 300 ブロック（BPO2 の式）で、全ての組が一致しています。Cancun は、Dencun のうち実行レイヤー側の呼び名です。

```text
Cancun の式: 次のブロックの excessBlobGas が一致 799/799
BPO2 の式: 次のブロックの excessBlobGas が一致 299/299
BPO2 から EIP-7918 を外した式: 次のブロックの excessBlobGas が一致 100/299
```

手元の anvil（Foundry 1.7.1）でも上限の 9 個を 3 ブロック続けて載せましたが、`excessBlobGas` は 0 のまま動きませんでした（[anvil_excess.txt](lab/output/anvil_excess.txt)）。既定の設定で動かした anvil では値上がりを再現できなかったので、以降は mainnet のヘッダーを使います。

<br>

#### 1 wei から 2 時間で 737 gwei

Dencun から 2 週間ほど、blob の単価は 1 wei のままでした。rollup が載せる blob が target の 3 個に届かず、`excessBlobGas` が 0 に張り付いていたからです。2024 年 3 月 27 日に、[Ethscriptions](https://docs.ethscriptions.com/) が blob に画像などを書き込む「blobscriptions」を始めると、上限の 6 個を載せたブロックが続きました。

{{< figure src="images/blob_fee_spike.webp" alt="2024-03-27 の mainnet の動画。上の段は blob gas 1 あたりの単価を対数の縦軸で描き、下の段はブロックごとの blob の数を棒で描く。16:12 まで単価は 1 wei のまま。その後は上限の 6 個のブロックが続き、単価は 16:58 に 100 万 wei、17:11 に 1 gwei を超え、18:13 に 737 gwei で最も高くなり、18:31 には 57.4 gwei まで下がる。実際のブロックの時刻を 1000 倍速で再生し、最後の状態で 3.5 秒止まる" caption="2024-03-27 に blob の単価が上がる様子（ヘッダーから計算、実時間の 1000 倍速で再生）" align="center" >}}

ヘッダーから計算すると、最後に 1 wei だったのは 16:12:47 UTC のブロック 19,526,747 です。そこから 18:13:23 のブロック 19,527,315 までの 568 ブロックのうち、316 ブロックが上限の 6 個を載せました。

最も高いブロックの単価は 736,862,660,297 wei（約 737 gwei）で、2 時間で約 7,400 億倍です。[CoinDesk](https://www.coindesk.com/tech/2024/03/28/ethereum-hit-by-blobscriptions-in-first-stress-test-of-blockchains-new-data-system)も翌日の報道で、Dune の集計から「少なくとも 582 gwei」まで上がったと伝えています。

<br>

最も高いブロックで 1 個の blob を満たした時、1 バイトあたりの値段は、同じブロックで calldata に書いた時（0 でないバイト 1 つで 16 gas）の 0.93 倍でした。数時間だけですが、blob は calldata とほぼ同じ値段まで上がったことになります。

この後、単価は数十 gwei の辺りで上下しました。Vitalik Buterin は先の振り返りで、blob の値段が初めて需要で決まる段階に入ったと書いています。

<br>

#### 使用量が少なくても下限で止まる

1 wei まで下がる仕組みには、問題もありました。使用量が target を下回る間は単価が 1 wei まで下がり続け、blob の手数料は実行の手数料に比べて無視できるほど小さくなります。その状態から需要が戻ると、上限に近いブロックが 1 時間以上続かないと、需要に見合う値段まで戻りません。上の動画でも、1 gwei に届くまで約 1 時間かかりました。[EIP-7918](https://eips.ethereum.org/EIPS/eip-7918) は、この点を理由に Fusaka で下限を入れました。

下限の目安は、blob 1 個の手数料が実行の 8,192 gas 分（base fee × 8,192）になる値で、blob gas 1 あたりにすると base fee × 8,192 / 131,072 です。単価がこれより安い間は `excessBlobGas` が減らなくなり、blob が載る度に、載った blob gas × (max − target) / max だけ増えます。単価そのものを止めるのではないので、下回ることはありますが、下限の辺りへ押し戻されます。

先の照合で EIP-7918 を外した式が 299 組のうち 100 組しか一致しなかったのは、この分岐を通った組が多かったからです。

{{< figure src="images/blob_fee_reserve.webp" alt="2026-11-12 12:56〜13:56 UTC の mainnet（BPO2: target 14、max 21）。上の段は対数の縦軸で、実際の単価（赤）が下限 base fee × 8192 / 131072（灰色の破線）にほぼ重なって 500 万から 5,000 万 wei の間を動く。同じ使われ方を EIP-7918 なしの式に通した場合（青）は下がり続け、約 48 分で 1 wei になる。下の段はブロックごとの blob の数で、多くのブロックが target 14 の破線より下にある" caption="2026-11-12 の単価と下限（ヘッダーから計算）" align="center" >}}

2026-11-12 の 1 時間（300 ブロック）では、1 ブロックに載った blob は平均 8.5 個、[中央値](/ml/math/median/)で 7 個で、target の 14 個を下回っています。それでも単価の中央値は 22,253,942 wei で、下限の中央値 23,579,818 wei とほぼ同じでした。300 ブロックのうち 213 ブロックは下限を下回り、そこから押し戻されています。

同じ使われ方を EIP-7918 なしの式に通すと、単価は約 48 分で 1 wei まで下がります。少なくともこの 1 時間の単価は、blob の需要よりも、実行の base fee に連動して決まっていました。

---

### calldata の方が安いデータ

blob が安いのは、大きなデータを送る時です。calldata は 1 バイトごとに gas がかかり、blob は 1 個単位でかかります。どこで逆転するかを知るため、anvil で calldata の大きさを変えて送り、使った gas を測りました。

```text
bytes gasUsed
5 21200
100 25000
1000 61000
10000 421000
100000 4021000
```

どの大きさでも、gasUsed は 21,000 + 40 × バイト数でした。Pectra で入った [EIP-7623](https://eips.ethereum.org/EIPS/eip-7623) は、実行に使う gas が少ないトランザクションに、calldata の最低額として 0 でないバイト 1 つあたり 40 gas、0 のバイトは 10 gas を課します。実験のデータは全て 0 でないバイトで、送り先はコントラクトの無いアドレスなので、この最低額がそのまま gasUsed に出ています。

{{< figure src="images/blob_cost_crossover.webp" alt="横軸は送るデータの大きさ（1 バイトから blob 6 個分の 761,670 バイト、対数）、縦軸は手数料（ETH、対数）。2026-11-12 の中央値（base fee 0.377 gwei、blob gas の単価 0.0223 gwei）で計算した。calldata（黒、21,000 + 40 × バイト数 gas）は右上がりで、anvil で測った 5・100・1,000・1 万・10 万バイトの点が線に乗る。blob（赤、21,000 gas + blob の数 × 131,072 blob gas）は 126,945 バイトごとに一段上がる階段で、1 トランザクションの上限の 6 個で終わる。calldata の線は 1 トランザクションの gas 上限に届く 418,905 バイトで終わる。194 バイトで 2 本の線が交わり、それより小さいデータでは calldata の方が安い" caption="データの大きさと手数料（2026-11-12 の中央値で計算）" align="center" >}}

この日の中央値では、194 バイトより小さいデータは calldata の方が安くなりました。図の右端で 2 本の線が途中で終わるのは、1 つのトランザクションに載る量に上限があるからです。Fusaka から、blob は [EIP-7594](https://eips.ethereum.org/EIPS/eip-7594) で 6 個まで、calldata は [EIP-7825](https://eips.ethereum.org/EIPS/eip-7825) が定めた gas の上限で 418,905 バイトまでです。

<br>

図からは、blob を 1 個送る手数料のうち大きいのはトランザクション自体の 21,000 gas だと分かります。中央値で計算すると、21,000 gas 分が約 0.0000079 ETH、blob 1 個分が約 0.0000029 ETH でした。1 つのトランザクションに blob を複数添えれば 21,000 gas を分け合えるので、データを溜めてから送る方が 1 バイトあたりは安くなります。

rollup にとって、この 21,000 gas は、1 つの batch に何件分詰めるかの判断に関わります。

冒頭で挙げた Vitalik Buterin の振り返りは、圧縮しない 1 件をおよそ 180 バイトと見積もっています。この見積もりなら、1 個の blob に 705 件が入ります。2026-11-12 の中央値で、21,000 gas を含めた 1 件あたりの手数料を計算すると次の通りです。rollup のコントラクトを動かす分の gas は含めていません。

| batch の件数 | blob の数 | 1 件あたりの手数料 |
| ---: | ---: | ---: |
| 100 | 1 | 108.4 gwei |
| 352 | 1 | 30.8 gwei |
| 705 | 1 | 15.4 gwei |
| 706 | 2 | 19.5 gwei |
| 1,410 | 2 | 9.8 gwei |
| 4,230 | 6 | 6.0 gwei |

blob が埋まる 705 件までは、件数を増やすほど 1 件あたりは安くなります。706 件目で 2 個目の blob が必要になり、一度高くなります。上限の 6 個まで添えると 21,000 gas の割合が小さくなり、1 件あたりは blob 1 個分を 705 件で割った約 4.1 gwei に近づきます。

<br>

同じ見積もりで、1 ブロック（12 秒）に target の 14 個が載ると、全ての rollup を合わせて毎秒約 820 件、max の 21 個で約 1,230 件です。target と max は、全ての rollup が L1 に公開できるデータ量の枠になっています。blob が下げるのは、この枠にデータを公開するコストです。シーケンサーによる検閲、rollup のコードに潜む欠陥、L1 に資産を戻せるまでの待ち時間は、blob を使っても変わりません。

---

### blob を使う前に見ること

blob に何かを載せる前に、次の 4 つを見ます。

1. データが数百バイト以下なら、calldata と比べる。
2. コントラクトが中身を使うなら、証明を渡す形にする。
3. 18 日より後に読むなら、自分で保存先を用意する。
4. 手数料の見積もりは、mainnet か testnet で測る。

1 つ目は、上記の逆転を描いた図の通りです。単価が下限に張り付いている間は、blob 1 個の手数料が base fee × 8,192、calldata が base fee × 40 × バイト数なので、逆転は 8,192 / 40 = 約 205 バイトの辺りにあり、base fee が上下してもこの位置は動きません。

単価が下限より高い時は、逆転の位置も大きい方へ動きます。この日の 194 バイトが少し小さいのは、単価の中央値が下限をわずかに下回っていたからです。

2 つ目は、コントラクトから見える値が versioned hash だけだからで、中身の一部を使うなら point evaluation precompile に証明を渡します。

<br>

3 つ目は、beacon node が blob を提供するのが最短 4096 epoch で、その先はノードの設定次第だからです。

4 つ目は、手元の anvil（Foundry 1.7.1、既定の設定）では `excessBlobGas` が動かず、値上がりを再現できなかったからです。本記事の [blobfee.py](lab/blobfee.py) のように、仕様の式とヘッダーの値から計算する方法もあります。式の上では、上限の個数が 1 時間（300 ブロック）続くと仮定すると、今の設定でも単価は約 170 億倍になります。
