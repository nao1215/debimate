---
title: "Ethereum Transaction - 送信元は署名から決まり、priority fee は base fee との和が maxFeePerGas 以下の間、書いた値のまま払われる"
date: 2026-08-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum"]
weight: 14
topics: ["Transaction / Wallet"]
---

Ethereum のトランザクション（[transaction](https://ethereum.org/developers/docs/transactions/)）は、ETH の送金、[スマートコントラクト](../smart-contract/)の呼び出しと作成を[ブロックチェーン](../blockchain-basics/)のネットワークに依頼する、署名済みのデータです。[ウォレット](../wallet/)の確認画面で承認した時や、アプリが [ethers](https://docs.ethers.org/) などのライブラリで送った時に作られます。

手数料の欄には、上限という名前の値が 2 つあります。ところが、片方は条件を満たす間、上限ではなく書いた値がそのまま払われます。

2021 年 9 月 27 日、暗号資産取引所の Bitfinex から分かれた DeversiFi の画面で、ドルと価値を連動させた [ERC-20](../erc-20/) トークンの USDT を約 10 万ドル分動かす 1 件のトランザクションが送られ、7,676 ETH の手数料が払われました。手数料を払った送信元は、Bitfinex が持つウォレットの 1 つです。[The Block の報道](https://www.theblock.co/post/118753/bitfinex-just-spent-23-7-million-in-fees-to-make-one-ethereum-transaction)によると、当時の価値で約 2,370 万ドルです。

{{< figure src="images/ethereum-transaction_deversifi.webp" alt="対数の横軸に 3 本の横棒。灰色の base fee は 58.9 gwei、黄土色の maxPriorityFeePerGas は 53,243,611 gwei、青い maxFeePerGas は 115,773,962 gwei。上に、ブロック 13,307,440 で手数料 7,676.6 ETH、うち焼却 0.0085 ETH。下に、払った単価は base fee と priority fee の和の 53,243,670 gwei で、maxFeePerGas には届いていない" caption="7,676 ETH を払ったトランザクションに書かれた値と、その時の base fee" align="center" >}}

上の図に並べたのは、公開のノードから読んだ[そのトランザクション](https://etherscan.io/tx/0x2c9931793876db33b1a9aad123ad4921dfb9cd5e59dbb78ce78f277759587115)に書かれた上限 2 つと、当時のブロックで決まっていた最低単価（base fee）です。Ethereum の手数料は、[gas](https://ethereum.org/developers/docs/gas/) という単位で数える処理量に、gwei という単位の単価を掛けて決まります。図の gasUsed は使った gas の量です。

払った単価は、単価の上限を書く maxFeePerGas の半分ほどでした。払った額を決めたのは、ブロックを作る側への上乗せを書く maxPriorityFeePerGas の方です。ただし、maxFeePerGas も base fee の約 200 万倍でした。誰の手にも渡らず消える焼却の分はわずかで、手数料のほぼ全部が当時ブロックを作っていたマイナーへ渡りました。報道の追記によると、そのうち約 2,210 万ドル分は Bitfinex のウォレットへ返されています。

<br>

本記事では、手数料の欄に書く値をコードで決める人や、確認画面で承認する人に向けて、手元のチェーンで試した結果から次の順に説明します。

- トランザクションには何が書かれ、送信元はどこにあるのか。
- 署名後のバイト列を書き換えると、何が起きるのか。
- 手数料の上限 2 つのうち、どちらが書いた値のまま払われるのか。
- 送るには、残高がいくら必要なのか。
- 中の処理が失敗した時、手数料と nonce はどうなるのか。
- Bitcoin のトランザクションや、型の番号ごとに何が違うのか。

単価が上下する仕組みは [Gas and EIP-1559](../gas-eip-1559/)、nonce の順序は [Ethereum Account Model](../ethereum-account-model/) に任せ、本記事では使う所だけを説明します。

---

### 欄と署名

まず、署名済みのトランザクションがどんなバイト列かを見ます。実験には [Foundry](https://getfoundry.sh/) の [Anvil](https://getfoundry.sh/anvil/overview/) を使いました。Anvil は、手元の PC だけで動く Ethereum 互換のチェーンを作る、開発用のノードです。公開ネットワークと実資産は使いません。

Anvil は開発用のアカウントを 10 個用意し、その秘密鍵を誰でも見られる形で配っています。そのうちアカウント 0 の鍵で、アカウント 1 へ 1 ETH を送るトランザクションを [cast](https://getfoundry.sh/cast/overview/) の `mktx` で署名しました。`mktx` は署名したバイト列を作るだけで、ノードには送りません。

```shell
# KEY0 は Anvil のアカウント 0 の秘密鍵（開発用に公開されている値）
cast mktx --private-key "$KEY0" 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 \
  --value 1ether --nonce 0 --gas-limit 21000 \
  --gas-price 2gwei --priority-gas-price 1gwei --chain 31337
```

`--gas-price` に書いた値は下の表にある maxFeePerGas に、`--priority-gas-price` は maxPriorityFeePerGas に入ります。

出てきたのは 119 バイトの 16 進数です。先頭の 1 バイトが型、残りが欄を並べた [RLP](https://ethereum.org/developers/docs/data-structures-and-encoding/rlp/)（Recursive Length Prefix）という形式のバイト列です。区切ると次のようになります。

{{< figure src="images/ethereum-transaction_bytes.webp" alt="119 バイトを欄ごとに区切った 2 段の帯。上の段は灰色の型 02（1 バイト）と長さ（2 バイト）の後に、青い chainId 3・nonce 1・maxPriorityFeePerGas 5・maxFeePerGas 5・gasLimit 3・to 21・value 9・data 1・accessList 1 バイトが並び、青い欄の上に「署名する欄（49 バイト。リストにまとめ直し、前に型 02 を付けてハッシュする）」の括弧。下の段は黄土色の yParity 1・r 33・s 33 バイトで「署名（67 バイト）」の括弧。一番上に「送信元（from）の欄は無い」" caption="署名済みのトランザクション（type 2）を欄ごとに区切った 119 バイト" align="center" >}}

青い欄の意味は次の通りです。表の wei は ETH を数える最小の単位で、1 gwei は 10 億 wei、1 ETH は 10 の 18 乗 wei です。

| 欄 | 役割 | 実験の値 |
| --- | --- | --- |
| chainId | どのチェーン宛ての依頼か | [31337](../mainnet-and-testnet/#ethereum-の-chain-id-と-network-id)（Anvil） |
| [nonce](../../security/nonce/) | 送信元の通し番号。同じ番号は 1 回しか通らない | 0 |
| maxPriorityFeePerGas | gas 1 単位ごとに上乗せする額の上限 | 1 gwei |
| maxFeePerGas | gas 1 単位ごとに払う額の上限 | 2 gwei |
| gasLimit | この依頼で使って良い gas の量 | 21,000 |
| to | 宛先のアドレス。空ならコントラクトの作成 | アカウント 1 |
| value | 送る ETH の額。単位は wei | 10 の 18 乗 |
| data | コントラクトに渡す入力。送金だけなら空 | 空 |
| accessList | 先に読むと宣言するアドレスとストレージ | 空 |

gasLimit を書くのは、全ノードが同じ処理を実行し直すからです。終わらない処理でネットワークを占有されないよう、1 件ごとに使って良い量を先に決めます。単純な送金でも 21,000 の gas が必ず掛かり、これを intrinsic gas と呼びます。data と accessList を足すと増えます。

value と data は別の欄なので、value が 0 のまま data でコントラクトを呼べます。data の中身は、呼ぶ関数と引数を決まった形に並べたバイト列で、[ABI](../evm/#calldata-と-abi) を知らないと何をする依頼か読めません。accessList は [EIP-2930](https://eips.ethereum.org/EIPS/eip-2930) で加わった欄で、触るアドレスとストレージを先に申告すると実行中の読み書きが安くなります。ただし、列挙した分にも gas が掛かります。

<br>

黄土色の 67 バイトが署名です。r と s は [ECDSA](../digital-signature/) で作った署名の値で、yParity は公開鍵の候補 2 つのどちらかを示す 0 か 1 です。

<br>

欄を全部並べても、送信元（from）はありません。ノードは青い欄を RLP のリストにまとめ直し、前に型の 02 を付けて [Keccak-256](../hash-function/) でハッシュします。

そのハッシュと r・s・yParity から公開鍵を計算します。この計算を公開鍵の復元と呼び、公開鍵から決まる[アドレス](../ethereum-address/)が送信元です。ブロックエクスプローラーの From も、記録された値ではなくこの計算の結果です。復元の手順は [Mastering Ethereum の第 6 章](https://masteringethereum.xyz/chapter_6.html)で説明されています。

同じ計算は `cast decode-transaction` でもできます。出力の `signer` が復元した送信元です（抜粋）。

```json
{
  "signer": "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266",
  "type": "0x2",
  "nonce": "0x0",
  "hash": "0x7d4c13ed95c0cee830d7457ec5a5976db1fc301cfa7a23fef0039a7ccf6aea87"
}
```

`hash` は、署名まで含めた 119 バイト全体を Keccak-256 でハッシュした値で、トランザクションハッシュと呼びます。ノードに送る前から決まっており、後でノードに送ると、実行結果の記録であるレシート（receipt）にも同じ `0x7d4c…ea87` が載りました。

---

### 署名した後の書き換え

送信元が欄に無いなら、署名した後のバイト列を書き換えると何が起きるのかを試します。上記の 119 バイトで、value・to・chainId という 3 つの欄だけ、長さを変えずに値を置き換えました。署名の 67 バイトには触れていません。次のコードは、Python から cast を呼ぶ [run.py](lab/run.py) の抜粋です。

```python
# sign・decode・publish は cast の mktx・decode-transaction・publish を呼ぶだけの関数
raw = sign(KEY0, nonce=0, value_wei=1 * ETH, max_fee=2 * GWEI, prio=1 * GWEI)
cases = {
    # 88 は「続く 8 バイト」を表す長さ、0de0b6b3a7640000 が 1 ETH（10 の 18 乗 wei）
    "value を 1 → 2 ETH": raw.replace("880de0b6b3a7640000", "881bc16d674ec80000"),
    # to のアドレスの末尾 3 バイト
    "to の末尾 c8 → c9": raw.replace("dc79c8", "dc79c9"),
    # 82 は長さ、7a69 が chainId の 31337、続く 80 は nonce の 0
    "chainId を 31337 → 31338": raw.replace("827a6980", "827a6a80"),
}
for name, r in cases.items():
    print(name, decode(r)["signer"], publish(r))
```

結果は次の通りです。

| 書き換えた欄 | 復元した送信元 | ノードの返事 |
| --- | --- | --- |
| 無し | `0xf39f…2266`（アカウント 0） | 受け付けた |
| value を 1 → 2 ETH | `0x6eb0…d268` | Insufficient funds |
| to の末尾 c8 → c9 | `0x1bdd…14f4` | Insufficient funds |
| chainId を 31337 → 31338 | `0xcdab…fafd` | invalid chain id for signer |

どの書き換えでも、署名が不正というエラーは出ませんでした。value と to を書き換えたバイト列は、知らないアドレスが送信元の依頼として読まれ、そのアドレスの残高が 0 なので拒否されています。表の Insufficient funds は、Anvil の返事 `Insufficient funds for gas * price + value` の先頭です。chainId を書き換えたものは、残高より先に、Anvil の chainId と合わないことで拒否されました。

chainId を署名する欄に含めるのは、別のチェーンに同じバイト列を送らせないためです。この防ぎ方は [Replay Protection](../replay-protection/) で扱っています。

{{< figure src="images/ethereum-transaction_recover.webp" alt="2 段の流れ図。見出しは、署名の 67 バイトに触れずに試した 3 件の書き換えでは、どれも公開鍵の復元は失敗せず、別の送信元が復元された。上段は元のバイト列（value = 1 ETH）から、署名する欄をハッシュし、同じ r, s, yParity から公開鍵を復元すると、緑の送信元 0xf39f…2266（Anvil のアカウント 0、署名した鍵）になり、受け付けて実行される。下段は value を 2 ETH に書き換えたバイト列で、同じ手順から赤い送信元 0x6eb0…d268（鍵の持ち主はいない、残高 0）が出て、残高不足で拒否、残高を入れると実行された" caption="試した書き換えでは、ハッシュが変わり同じ署名から別の送信元が復元された" align="center" >}}

上の図のように、試した 3 件では公開鍵の復元は失敗せず、計算した結果がそのまま送信元になりました。

<br>

では、書き換えで出てきた `0x6eb0…d268` に残高があればどうなるかです。Anvil が開発用に持つ命令 `anvil_setBalance` でこのアドレスに 10 ETH を入れ、value を書き換えたバイト列をもう一度送りました。

```text
資金を入れた後: status 0x1 from 0x6eb0fa363dc12d7675fe88009c284d270620d268
```

レシートの status は成功を表す 1 で、秘密鍵を知る人がいない `0x6eb0…d268` から 2 ETH が送られました。ノードから見ると、署名と送信元の対応に矛盾は無いためです。

公開のチェーンでこれが攻撃にならないのは、復元される送信元を書き換える側が選べないからです。出てくるのは残高の無い、事実上ランダムなアドレスです。特定の誰かを送信元にするには、その人の秘密鍵で署名し直すしかありません。

ただし、ネットワークにつながない端末で署名したバイト列を別の端末から送る時や、送信を他のサービスに任せる時は、途中の書き換えが署名エラーではなく残高不足や chainId の不一致として返ってきます。送る前に `cast decode-transaction` などで欄と送信元を読み直すか、署名した時に控えたトランザクションハッシュと照らすと気付けます。

---

### 手数料の上限 2 つ {#使った-gas-と単価による手数料}

次に、冒頭で DeversiFi に起きたことを手元で再現します。手数料に関わるのは、ブロックごとに決まる base fee と、トランザクションに書く 2 つの上限です。

base fee（基本料金）は、ブロックの混み具合からプロトコルが決める gas 1 単位の最低額で、払った分は焼却され誰の手にも渡りません。[EIP-1559](https://eips.ethereum.org/EIPS/eip-1559) の規則では、gas 1 単位に実際に払う単価は、次のどちらか小さい方です。

- maxFeePerGas
- base fee + maxPriorityFeePerGas

maxPriorityFeePerGas は略して priority fee と呼ばれ、本記事の図もこの呼び名を使います。単価のうち base fee を超えた分は tip と呼ばれ、ブロックを作った側に渡ります。

<br>

<details>
<summary>tip の受け取り先</summary>

2022 年 9 月の [The Merge](https://ethereum.org/roadmap/merge/) より前はマイナーでした。今はブロックごとに指定されたアドレスに入り、多くはブロックを提案した[バリデーター](../proof-of-stake/)、外部のビルダーが組んだブロックではビルダーのアドレスのこともあります。

</details>

<br>

Anvil の `anvil_setNextBlockBaseFeePerGas` で、次に作るブロックの base fee を 10 gwei に固定し、maxFeePerGas を 100 gwei にそろえて、maxPriorityFeePerGas だけを 1・50・100 gwei と変えた送金を 1 件ずつ送りました。gas はどれも 21,000 です。次のコードは [run.py](lab/run.py) から、レシートを読む行を省いた抜粋です。

```python
for prio in [1, 50, 100]:
    raw = sign(KEY0, nonce, 0, max_fee=100 * GWEI, prio=prio * GWEI)
    nonce += 1
    set_base_fee(10)  # anvil_setNextBlockBaseFeePerGas
    publish(raw)
```

{{< figure src="images/ethereum-transaction_fee_split.webp" alt="3 本の横棒。横軸は gas 1 単位あたりの gwei で、100 に maxFeePerGas の点線。priority fee 1 gwei は灰色の base fee 10、黄土色の tip 1、斜線の払わない 89 で、手数料 0.000231 ETH。50 gwei は 10、50、払わない 40 で 0.001260 ETH。100 gwei は 10 と 90 で上限の 100 に届き、0.002100 ETH" caption="maxFeePerGas を 100 gwei にそろえ、priority fee だけを変えた 3 件の単価" align="center" >}}

上の図のように、maxPriorityFeePerGas を 1 から 50 gwei に上げると、手数料は 0.000231 ETH から 0.00126 ETH まで 5 倍以上になりました。maxFeePerGas はどちらも 100 gwei のままです。

maxFeePerGas が単価を抑えたのは、base fee と priority fee の和が 110 gwei になった 3 件目だけで、tip は 100 ではなく 90 gwei に削られています。

maxPriorityFeePerGas を 20 gwei、maxFeePerGas を 10 gwei と、priority fee の方を大きくしたトランザクションは、ノードが受け付けませんでした。

```text
priority fee 20 > maxFee 10 -> max priority fee per gas higher than max fee per gas
```

<br>

maxFeePerGas は、送った後に base fee が上がった時に払いすぎないための上限です。base fee はブロックが混んでいると上がり、1 ブロックで最大 12.5% 動きます。満杯のブロックが続いた時に、10 gwei から上がる様子を EIP-1559 の式で計算しました。

{{< figure src="images/ethereum-transaction_basefee_rise.webp" alt="横軸が満杯のブロックが続いた数 0〜12（1 ブロック 12 秒）、縦軸が base fee の棒グラフ。10.0 gwei から 1 ブロックごとに 1.125 倍になり、9 ブロック目の 28.9 gwei までは灰色、10 ブロック目の 32.5 gwei から赤で、maxFeePerGas 30 gwei の点線を超える" caption="満杯のブロックが続いた時の base fee（計算値）" align="center" >}}

送った時の base fee の 3 倍を上限に書いても、満杯のブロックが 10 個、約 2 分続けば超える計算です。

base fee が maxFeePerGas を超えている間、トランザクションはすぐには消えず、ブロックに入る前のトランザクションを置く [mempool](../mempool/) で下がるのを待ちます。待つ時間が長いと、ノードの方針で mempool から外されることもあります。この扱いは [Gas and EIP-1559](../gas-eip-1559/#上限を下回ったトランザクションの行方) で実験しています。

<br>

冒頭の図に戻ると、DeversiFi のトランザクションは maxPriorityFeePerGas が 53,243,611 gwei で、その時の base fee 58.9 gwei の約 90 万倍でした。maxFeePerGas は 115,773,962 gwei で、base fee と priority fee の和はこれに届いていません。

払った単価は base fee と priority fee の和で、gas 144,179 を掛けて 7,676.6 ETH になりました。焼却された base fee の分は 0.0085 ETH だけです。gasLimit の 169,595 に maxFeePerGas を掛けた、払う可能性があった最大の額は 19,634.7 ETH です。

maxPriorityFeePerGas は上限という名前でも、base fee との和が maxFeePerGas に届かない限り、書いた値がそのまま払われる入札額として働きます。

なお、DeversiFi は原因としてハードウェアウォレットからの入金に「誤って高い gas の手数料」が付いたと説明しています。なぜその値になったかは、上記の報道からは分かりません。

---

### 送るのに必要な残高

手数料の上限は、払う額だけでなく、送れるかどうかにも効きます。上限まで払うことになった場合に備えて、ノードはトランザクションを受け付ける前に、送信元の残高が次の額以上あるかを調べるからです。

- value + gasLimit × maxFeePerGas

アカウント 2 の残高を 1.001 ETH にして、1 ETH を送るトランザクションを 3 通りの上限で署名しました。base fee は 10 gwei に固定し、priority fee は 1 gwei です。1 ETH を送った残りは 0.001 ETH なので、gasLimit × maxFeePerGas がこれを超えると拒否されるはずです。

{{< figure src="images/ethereum-transaction_reserve.webp" alt="対数の横軸に 3 本の横棒と、1 ETH を送った残り 0.001 ETH の点線。gasLimit 21,000 × maxFeePerGas 100 gwei は 0.00210 ETH で赤、Insufficient funds で拒否。gasLimit 1,000,000 × maxFeePerGas 40 gwei は 0.04000 ETH で赤、拒否。gasLimit 21,000 × maxFeePerGas 40 gwei は 0.00084 ETH で緑、受け付けた、実際の手数料 0.000231 ETH" caption="残高 1.001 ETH から 1 ETH を送る時に必要な上限分の額と結果" align="center" >}}

1 件目は、実際に掛かる手数料が 21,000 × 11 gwei = 0.000231 ETH で、残りの 0.001 ETH に収まります。それでも、maxFeePerGas を 100 gwei と書いたため、上限分の 0.0021 ETH が足りずに拒否されました。

2 件目は単価の上限を 40 gwei に下げても、gasLimit を 1,000,000 と多めに書いたために拒否されています。3 件目だけが通り、払ったのは 1 件目と同じ 0.000231 ETH でした。

この条件は、ノードごとに決める受け付けの方針ではなく、プロトコルの規則です。参照実装の [execution-specs](https://github.com/ethereum/execution-specs/blob/7b8124a77280edaaad877128937b71a1e3a7ebc5/src/ethereum/forks/prague/fork.py) では `check_transaction` にあり、満たさないトランザクションを含むブロックは無効になります。

上限を多めに書くほど安全に見えますが、残高に余裕が無い時は送れなくなります。残高をちょうど使い切るには、maxFeePerGas を実際に払う単価に、gasLimit を使う gas の量に、それぞれ合わせる必要があります。上限に余裕を持たせた分は、使わなかった分として送信元の残高に残ります。

ウォレットでも同じ欄を変えられます。[MetaMask のガス設定](https://support.metamask.io/configure/transactions/how-to-customize-gas-settings/)では、gasLimit は「Gas limit」（gas の上限）、maxPriorityFeePerGas は「Max priority fee」（priority fee の上限）という名前です。確認画面に出る手数料がこの式の額か、見込みの額かはウォレットで違うので、承認する前に欄の値から計算して比べます。

---

### 中の処理が失敗した時 {#実行が止まった時に消費する-gas}

ここまでの拒否は、どれもブロックに入る前の話でした。gasLimit が intrinsic gas に届かないトランザクションも、この段階で拒否されて手数料が掛かりません。手数料を払わずに済むのは、ブロックに入る前に拒否された時だけです。トランザクションがブロックに入った後、宛先のコントラクトで処理が失敗した時は扱いが変わります。

`REVERT` は、処理を取り消して終える命令です。呼ばれると必ず `REVERT` するだけのコントラクトを置き、gasLimit 100,000 で呼び出しました。結果は次の通りです。

```text
status 0x0  gasUsed 21,006 / gasLimit 100,000  手数料 0.000231066 ETH  nonce 5 → 6  ブロック 8
```

トランザクションはブロック 8 に入り、レシートの status は失敗を表す 0 でした。コントラクトで行った変更は取り消され、value で送るはずだった ETH も送信元に残ります。ただし、使った gas 21,006 に掛かる手数料は引かれ、nonce も 1 つ進みます。21,006 は、送金でも掛かる 21,000 に、`REVERT` までに実行した命令の 6 を足した値です。

ブロックエクスプローラーで「失敗」なのに手数料が引かれているのは、このようにブロックに入った後で処理が止まった状態です。払う額は止まり方で変わり、`REVERT` で止まった時は使った分だけ、gas を使い切って止まった時は gasLimit の分を全て払います。

gasLimit を指定しないと、[cast は送る前にノードの `eth_estimateGas` を呼び](https://github.com/foundry-rs/foundry/blob/v1.7.1/crates/cast/src/tx.rs#L684-L695)、ブロックへ入れずに試させた結果で gasLimit を決めます。試した時と実行する時でコントラクトの状態が違えば必要な gas も変わり、gas 切れで失敗することがあります。

ノードに [JSON-RPC](https://ethereum.org/developers/docs/apis/json-rpc/) で問い合わせる `eth_getTransactionReceipt` で、この失敗したトランザクションのレシートを読みました（抜粋）。

```json
{
  "status": "0x0",
  "cumulativeGasUsed": "0x520e",
  "logs": [],
  "blockNumber": "0x8",
  "gasUsed": "0x520e",
  "effectiveGasPrice": "0x28fa6ae00"
}
```

`gasUsed` の 0x520e は 21,006、`effectiveGasPrice` の 0x28fa6ae00 は 11 gwei で、掛けると上記の手数料になります。`cumulativeGasUsed` はブロックの中で使った gas の累計で、このブロックには 1 件しか無いので gasUsed と同じです。`logs` はコントラクトが残した[ログ](../evm/#イベントとログ)で、取り消されたので空です。

ただし、status 1 も、中の処理が全て成功したことまでは示しません。コントラクトが別のコントラクトを呼ぶ入れ子の処理では、呼んだ先が失敗しても、呼んだ側がその失敗を受け止めて処理を続ければ status は 1 になり、呼んだ先の変更だけが取り消されます。

{{< figure src="images/ethereum-transaction_nested.webp" alt="上下 2 段の模式図。どちらも灰色の枠がトップレベルの実行で、中に ① 処理を始める、② 別のコントラクトを呼ぶ（赤い点線の箱、× 中で失敗）、③ の 3 つの箱が並ぶ。上段の ③ は「戻り値を見ず最後まで進む」で、枠の外の緑の箱 status 1（成功として残る）に矢印が向かう。下段の ③ は「失敗を見て REVERT で中止」で、赤い箱 status 0（状態の変更を取り消す）に矢印が向かう" caption="中の呼び出しの失敗と、レシートの status" align="center" >}}

図の上段では、② の中の変更だけが取り消され、① と ③ の変更は残ります。下段のように、呼んだ側が失敗を見て自分も `REVERT` すれば、status は 0 になります。

例えば、2016 年 2 月のゲーム [King of the Ether Throne](https://www.kingoftheether.com/postmortem.html) では、ゲームのコントラクトが [Solidity](https://soliditylang.org/) の `send` で補償金を払いました。`send` は受け取る側に 2,300 gas だけを渡すので、送り先が [Mist](https://github.com/ethereum/mist) の作るコントラクト型ウォレットだった時は gas が足りずに失敗しました。

ゲームのコントラクトは `send` の戻り値を見ていなかったため、上段の形でトランザクション全体は成功し、補償金はゲームのコントラクトに残りました。補償金は後に手作業で返されています。

当時のレシートには、まだ status がありませんでした。status は [EIP-658](https://eips.ethereum.org/EIPS/eip-658) で 2017 年 10 月の Byzantium から入りました。足されたのは、同じ時に [EIP-140](https://eips.ethereum.org/EIPS/eip-140) の `REVERT` も入り、gas を残して止まる失敗ができたので、gas を使い切ったかどうかでは失敗を見分けられなくなったからです。この事故は今の規則で送っても、status は 1 になります。

失敗の種類ごとに gas と状態がどう扱われるかは、[EVM](../evm/#失敗の扱い)（Ethereum Virtual Machine）のノートに図があります。

---

### 型の番号と Bitcoin との違い

冒頭に示したバイト列の先頭 1 バイト `02` は、トランザクションの型を表す番号です。[EIP-2718](https://eips.ethereum.org/EIPS/eip-2718) で、先頭の 1 バイトで形式を区別する決まりができ、欄の組み合わせは、全ノードが同時に規則を切り替える更新（ハードフォーク）のたびに増えてきました。

| 型 | 導入 | 加わったもの |
| --- | --- | --- |
| 0 | 最初から | 単価の欄は gasPrice だけ |
| 1 | Berlin（2021 年 4 月） | accessList（EIP-2930） |
| 2 | London（2021 年 8 月） | 上限 2 つの手数料（EIP-1559） |
| 3 | Dencun（2024 年 3 月） | blob の手数料と参照（[EIP-4844](https://eips.ethereum.org/EIPS/eip-4844)） |
| 4 | Pectra（2025 年 5 月） | 秘密鍵で動くアカウントにコードを委任（[EIP-7702](https://eips.ethereum.org/EIPS/eip-7702)） |

型 0 は gasPrice に書いた単価をそのまま払う形式で、今も送れます。型 3 の blob は [Blob](../blob/)、ハードフォークの流れは [Ethereum Hard Forks](../ethereum-hard-forks/) で扱っています。

<br>

<details>
<summary>型 0 の署名と先頭のバイト</summary>

型 0 には chainId の欄が無く、yParity の代わりに v という値を使います。[EIP-155](https://eips.ethereum.org/EIPS/eip-155) に従って署名した時だけ、v に chainId を埋め込みます。chainId を含めない古い形の署名もプロトコルでは今も有効なので、受け付けるノードがあれば別のチェーンでも通ります。ただし [geth](https://geth.ethereum.org/docs/fundamentals/command-line-options) は既定で、この形のトランザクションを RPC から受け付けません。

型 0 のバイト列は RLP のリストなので先頭が 0xc0 以上になり、0x7f 以下を使う型の番号とは先頭 1 バイトで見分けられます。

</details>

<br>

同じ「トランザクション」でも、[Bitcoin のトランザクション](../bitcoin-transaction-lifecycle/)とは作りが違います。Bitcoin は、まだ使われていない過去の出力を入力として指す [UTXO](../utxo/) のモデルで、送信元の欄が無い点は同じですが、理由が異なります。

| | Bitcoin | Ethereum |
| --- | --- | --- |
| 送信元 | 入力が指す出力の条件を満たした人 | 署名から復元したアドレス |
| 手数料 | 入力の合計 − 出力の合計 | gasUsed × 単価 |
| 二重の使用を防ぐもの | 使った出力は消える | 送信元の nonce |
| 中で処理が失敗した時 | ブロックに入らない | 入り、status 0 で手数料を払う |

Bitcoin の手数料には欄が無く、出力に書かなかった差額がそのまま手数料になります。検証の手間もデータからほぼ決まります。Ethereum は宛先のコードを動かすので、データだけでは処理量が分からず、gasLimit と単価の上限を書く必要があります。

入力の条件を書く [Bitcoin Script](../bitcoin-script/) が通らないトランザクションは無効で、ブロックに入りません。Ethereum では、署名・nonce・残高の条件を満たせば、中で処理が成功したかに関わらずブロックに入り、gas の分を払います。

---

### 送る前に見る所

DeversiFi の画面から送られたトランザクションは、正しく署名され、status 1 の成功としてブロックに入っていました。違っていたのは手数料の欄に書いた値で、払った額を決めたのは上限という名前の maxPriorityFeePerGas でした。トランザクションを組み立てるコードや、承認する画面では、次の 4 つを見ます。どれも本記事の実験と冒頭の事例で起きたことに対応しています。

1. 上限 2 つをその時の base fee と桁で比べる。
2. value + gasLimit × maxFeePerGas が残高に収まるかを見る。
3. 受け渡した署名済みのバイト列は、送る前にデコードする。
4. 送った後はハッシュでなく status を見る。入れ子の失敗は出ない。

1 つ目で maxPriorityFeePerGas も見るのは、maxFeePerGas に届かない限り、書いた値のまま払われるからです。冒頭の DeversiFi では maxFeePerGas も base fee の約 200 万倍で、どちらを見ても桁違いに気付けました。2 つ目は、gas 切れを避けようと gasLimit に余裕を持たせるほど、必要な残高も増えるためです。

実験のコードと出力は [lab](lab/README.txt) にあります。
