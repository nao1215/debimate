---
title: "Gas and EIP-1559 - 計算量の単位と、ブロックの混み具合で動く base fee"
date: 2026-11-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "gas", "eip-1559"]
weight: 13
wrapTables: true
topics: ["Transaction / Wallet"]
---

gas は、[Ethereum](https://ethereum.org/) でトランザクションの実行に掛かる計算量を測る単位です。[EVM](../evm/)（Ethereum Virtual Machine）の命令ごとに gas の量が決まっており、トランザクションは「使ってよい gas の上限」と「1 gas あたりに払う額」を書いて送ります。トランザクションをまとめた単位がブロックで、ネットワークに参加する全てのノード（Ethereum のソフトウェアを動かすコンピューター）がブロックのトランザクションを実行します。ブロック 1 つに入るトランザクションは、gas の合計にも上限があり、これが全ノードが 1 ブロックごとに実行する量の上限になります。

[EIP-1559](https://eips.ethereum.org/EIPS/eip-1559)（EIP は Ethereum の仕様変更の提案書）は、2021 年 8 月 5 日の London の[ハードフォーク](../ethereum-hard-forks/)（全ノードの規則の一斉更新）で入った、1 gas あたりの額の決め方です。この額は、ブロックごとにプロトコルが決める base fee と、送り主が上乗せする priority fee の 2 つに分かれます。base fee は、前のブロックが上限の半分（target）よりどれだけ多く、または少なく gas を使ったかで、1 ブロックごとに最大 12.5% 上下します。以下は、前のブロックの使用量と、次のブロックの base fee の関係を描いた図です。

{{< figure src="images/gas-eip-1559_concept.webp" alt="3 組の図。左の組は gas の上限の箱が青で満杯になっており、次の base fee の黄土色の棒は、今の base fee を示す点線より高い ×1.125。中央の組は箱の半分の破線（target）まで青で、次の棒は点線と同じ高さの ×1。右の組は空の箱で、次の棒は点線より低い ×0.875" caption="前のブロックの使用量と、次のブロックの base fee" align="center" >}}

満杯のブロックが続けば base fee は 1.125 倍ずつ上がり、空のブロックが続けば 0.875 倍ずつ下がります。次のブロックの base fee は今の 1.125 倍を超えないので、払う額の上限を見積もれます。EIP-1559 の本文も、これで[ウォレット](../wallet/)が手数料を自動で設定しやすくなると説明しています。

<br>

本記事では、ローカルのノードで base fee を実測しながら、gas が何を測り、EIP-1559 が 1 gas あたりの額をどう決めるのかを説明します。扱う疑問は次の通りです。

- gas は、なぜ命令ごとに決まっていて、ブロックにも上限があるのか。
- London 以前の手数料の決め方は、何が問題だったのか。
- base fee を焼却し（誰にも渡さずに消し）、priority fee だけをブロックの提案者に渡すのはなぜか。
- base fee はどんな式で上下し、実際のノードは式の通りに動くのか。
- base fee が上がって単価の上限を超えたトランザクションは、どうなるのか。

命令ごとの gas の値は [EVM のノート](../evm/#命令とガス)、トランザクションに書く項目と送り主が払う額の計算例は [Ethereum Transaction](../ethereum-transaction/#使った-gas-と単価による手数料) で説明しています。[rollup](../rollup/) が使う [blob の手数料](../blob/#blob-の手数料)にも target を基準に値段を上下させる仕組みがありますが、その式は扱いません。

---

### gas で計算量を測る理由

Ethereum のトランザクションは、宛先のコントラクトのコードを動かせます。コードはループを書けるので、どれだけの計算になるかをトランザクションのデータから事前に決められません。そこで EVM は、全ての命令に gas の値を付け、送り主がトランザクションに書いた上限（gasLimit）まで使った所で実行を止めます。止まったトランザクションは、状態の変更が取り消されますが、使った gas の分の手数料は払います。

命令の値は、計算の重さだけでなく、ノードのディスクや状態への負担で決まります。例えば、足し算の ADD は 3 gas ですが、storage（コントラクトがチェーン上に持ち続ける領域）の空の場所に初めて値を書く SSTORE は 2 万 gas（その場所にトランザクションの中で初めて触れる cold の時は、さらに 2,100 gas）掛かります。手数料はこの gas の量に 1 gas あたりの額を掛けて決まるので、重い処理を頼むトランザクションほど多く払います。

<br>

1 ブロックに入るトランザクションは、gas の合計にも上限（block gas limit）があります。ブロックを受け取ったノードは、中のトランザクションを全て実行し直して検証します。上限を上げれば 1 ブロックに入るトランザクションは増えますが、全ノードの検証の負担も同じだけ増えます。以下は、トランザクションごとの上限とブロックの上限の関係を描いた図です。

{{< figure src="images/gas-eip-1559_limits.webp" alt="2 段の図。上段はトランザクション 1 件で、ADD 3、SSTORE 22,100、ADD 3、… と命令の gas の箱が左から積み上がり、右端の縦線 gasLimit（送り主がトランザクションに書く上限）に達した所に「使い切ったら実行を止める」。下段はブロック 1 つで、トランザクション 1〜5 の箱が左から並び、右端の縦線が block gas limit（全ノードが実行し直す量の上限）。左下に「箱の幅は gas の量に比例しない」" caption="トランザクションの gasLimit と、ブロックの gas の上限" align="center" >}}

トランザクションの gasLimit は送り主が 1 件ごとに書く上限で、ブロックの上限は、全てのトランザクションを合計した量に掛かる上限です。

上限の値は固定ではありません。Ethereum の仕様を Python で書いた [execution-specs](https://github.com/ethereum/execution-specs) の [`check_gas_limit`](https://github.com/ethereum/execution-specs/blob/v2.20.0/src/ethereum/forks/osaka/fork.py#L1024-L1062) は、親ブロックの上限から 1024 分の 1 未満の幅でしか次の上限を変えられないと定めています。[ethereum.org の gas のページ](https://ethereum.org/en/developers/docs/gas/)には、次のように書かれています。

> The gas limit can fluctuate over time based on validator signalling, as well as via network upgrades.
>
> （gas の上限は、バリデータ（ブロックを提案する参加者）の意思表示や、ネットワークの更新によって時間とともに変わりうる。）

本記事では、時期で変わる上限の値ではなく、上限に対する比率で説明します。

---

### London 以前の手数料

London 以前のトランザクションは、1 gas あたりの額（gasPrice）を 1 つだけ書いていました。マイナー（当時の Proof of Work で、ブロックを作る参加者）は gasPrice の高いトランザクションから選び、取り込まれたトランザクションは書いた額をそのまま払います。高い値を付けた順に、付けた値で買う形で、EIP-1559 の本文はこれを first price auction（第一価格オークション）と呼んでいます。

[EIP-1559 の Motivation](https://github.com/ethereum/EIPs/blob/ba6c342c23164072adb500c3136e3ae6eabff306/EIPS/eip-1559.md#motivation) は、この形の問題を 4 つ挙げています。1 つ目は、ブロックが満杯の時に gasPrice が激しく上下することです。本文は、ブロックに 1 件を足す時のネットワークの負担は 800 万 gas が 802 万 gas になる程度で変わらないのに、値段だけが 10 倍になるのはおかしいと書いています。

2 つ目は、上限が固定されていて、混んだブロックのトランザクションが次へ回されても、空いたブロックの余りを使う仕組みが無いことです。3 つ目は、払う額を自分で入札するので見積もりが難しく、払いすぎが頻繁に起きることです。4 つ目は本記事では扱いません。2 つ目への答えは、後の「base fee を決める式」の節で出てきます。

{{< figure src="images/gas-eip-1559_auction.webp" alt="左は London 以前で、高さの違う 5 本の青い棒がそれぞれの入札額で、全額がマイナーへ渡る。右は EIP-1559 で、5 本とも同じ高さの黄土色の base fee の上に、高さの違う小さな青い tip が乗る。その上の点線の枠は「書いた上限（払わない）」で、払わない部分" caption="London 以前と EIP-1559 の、1 gas あたりの支払い" align="center" >}}

上記の図の右側が EIP-1559 です。同じブロックのトランザクションは全員が同じ base fee を払い、上乗せの priority fee（tip）だけがトランザクションごとに違います。送り主が書くのは、1 gas あたりの額の上限（maxFeePerGas）と、上乗せの上限（maxPriorityFeePerGas）です。点線の枠のうち、base fee と tip を超える部分は払いません。

額は ETH の小さな単位で表し、gwei は 10 億分の 1 ETH、wei は 10^18 分の 1 ETH です。

---

### base fee の焼却と priority fee

EIP-1559 のトランザクションが 1 gas あたりに払う額は、ブロックの base fee と priority fee の和です。priority fee は、maxPriorityFeePerGas と「maxFeePerGas − base fee」のうち小さい方になります。maxFeePerGas が base fee を下回るトランザクションは、そのブロックに入れられません（[execution-specs](https://github.com/ethereum/execution-specs/blob/v2.20.0/src/ethereum/forks/osaka/fork.py#L475-L482) の `InsufficientMaxFeePerGasError`）。

以下は、base fee が 4.11 gwei（後の実験のブロック 16 の値）のブロックで、maxPriorityFeePerGas を 1 gwei にした 3 人が払う額を並べた図です。

{{< figure src="images/gas-eip-1559_split.webp" alt="横の破線が base fee 4.11 gwei。左の maxFeePerGas 10 gwei のトランザクションは、黄土色の base fee の上に青い tip 1.00 が乗り、払う額は 5.11 gwei で、点線の枠の残りは払わない。中央の 5 gwei のトランザクションは tip が 0.89 に減り、払う額は 5.00 gwei。右の 2 gwei のトランザクションは点線の枠が base fee に届かず、ブロックに入れられない。右に、tip はブロックの提案者へ、base fee は焼却（誰にも渡らない）の 2 つの箱。下に tip = min(maxPriorityFeePerGas 1 gwei, maxFeePerGas − base fee)" caption="base fee と priority fee（tip）の分け方と行き先" align="center" >}}

上限に余裕が無いと、tip は書いた額より小さくなります。

base fee の分は誰にも渡らず焼却され、priority fee の分だけがブロックの提案者に渡ります。EIP の本文は受け取る側を miner（マイナー）と書いていますが、2022 年 9 月に [Proof of Stake](../proof-of-stake/) へ移ってからは、ブロックを提案するバリデータが指定したアドレスに渡ります。base fee を提案者に渡さない理由について、本文は次のように書いています。

> Finally, ensuring the miner of a block does not receive the base fee is important because it removes miner incentive to manipulate the fee in order to extract more fees from users.
>
> （最後に、ブロックのマイナーが base fee を受け取らないようにすることは重要である。利用者からより多くの手数料を取るために、マイナーが手数料を操作する動機を取り除くからだ。）

提案者が base fee を受け取れるなら、自分のトランザクションでブロックを満杯にして base fee を吊り上げ、次のブロックから多く取れます。焼却すれば、吊り上げても提案者の取り分は増えません。本文は他にも、手数料を ETH だけで払わせることと、焼却で ETH の新規発行を打ち消すことを理由に挙げています。

<br>

#### priority fee の役割

priority fee について、Proof of Work の時代に書かれた本文は 1 nanoeth（1 gwei）程度の小さな額を想定し、ブロックを作る側が負う、作ったブロックが[孤立して（orphan）チェーンに残らない](../finality/)危険への補償と説明しています。ブロックに空きがあれば、小さな tip でもトランザクションは入ります。満杯のブロックが続いた時に何が起きるかは、後の実験で確かめます。

---

### base fee を決める式

base fee は、親ブロックの gas の上限・使用量・base fee だけから計算します。以下は、execution-specs v2.20.0 の、2025 年 12 月のハードフォーク Osaka の規則の [`calculate_base_fee_per_gas`](https://github.com/ethereum/execution-specs/blob/v2.20.0/src/ethereum/forks/osaka/fork.py#L276-L336) から、上限の検査と型の変換を除いた部分です。

```python
BASE_FEE_MAX_CHANGE_DENOMINATOR = Uint(8)
ELASTICITY_MULTIPLIER = Uint(2)

parent_gas_target = parent_gas_limit // ELASTICITY_MULTIPLIER

if parent_gas_used == parent_gas_target:
    expected_base_fee_per_gas = parent_base_fee_per_gas
elif parent_gas_used > parent_gas_target:
    gas_used_delta = parent_gas_used - parent_gas_target
    parent_fee_gas_delta = parent_base_fee_per_gas * gas_used_delta
    target_fee_gas_delta = parent_fee_gas_delta // parent_gas_target
    base_fee_per_gas_delta = max(
        target_fee_gas_delta // BASE_FEE_MAX_CHANGE_DENOMINATOR,
        Uint(1),
    )
    expected_base_fee_per_gas = parent_base_fee_per_gas + base_fee_per_gas_delta
else:
    gas_used_delta = parent_gas_target - parent_gas_used
    parent_fee_gas_delta = parent_base_fee_per_gas * gas_used_delta
    target_fee_gas_delta = parent_fee_gas_delta // parent_gas_target
    base_fee_per_gas_delta = target_fee_gas_delta // BASE_FEE_MAX_CHANGE_DENOMINATOR
    expected_base_fee_per_gas = parent_base_fee_per_gas - base_fee_per_gas_delta
```

target は上限を ELASTICITY_MULTIPLIER（2）で割った値、つまり上限の半分です。変化の量は「target との差 ÷ target ÷ 8」に親の base fee を掛けたものです。満杯のブロックでは差が target と等しいので 8 分の 1（12.5%）上がり、空のブロックでは 12.5% 下がります。使用率 75% なら差は target の半分なので、上がるのは 6.25% です。

London のフォークのブロックでは、ブロックの上限を 2 倍に引き上げ、base fee を INITIAL_BASE_FEE（10 億 wei、1 gwei）から始めました（[EIP の pseudocode](https://github.com/ethereum/EIPs/blob/ba6c342c23164072adb500c3136e3ae6eabff306/EIPS/eip-1559.md#specification)）。それまでの上限がそのまま target になり、混雑した時だけ、ブロックをその 2 倍まで伸ばせるようにしたわけです。これが、London 以前の問題の 2 つ目（空いたブロックの余りを使えない）への答えです。

<br>

式は整数の切り捨てで計算します。上がる時は最低でも 1 wei 上がりますが、下がる時にはこの最低がありません。base fee が 7 wei 以下だと、空のブロックでも 7 ÷ 8 が切り捨てで 0 になり、それ以上は下がりません。逆に、7 wei から 8 wei への上昇は 14.3% で、極端に小さい base fee では 12.5% を超えて上がります。この下限も、後の実験で確かめます。

---

### Anvil で base fee を実測する

[Foundry](https://github.com/foundry-rs/foundry) のローカルノード [Anvil](https://getfoundry.sh/anvil/overview) 1.7.1 で、ノードの実装が式の通りに base fee を決めているかを確かめました。実行は 2026 年 11 月 11 日で、EVM の規則は 2025 年 12 月のハードフォーク Osaka のものに固定しています（実行環境は [lab/output/environment.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/gas-eip-1559/lab/output/environment.txt)）。

ローカルの Anvil だけを使い、公開のネットワークや実際の資産には接続していません。アカウントは Anvil が既定で作るテスト用のもので、秘密鍵が広く公開されている説明用の無価値な鍵です。

<br>

ブロックを満杯にしやすいように、ブロックの gas の上限を 1,050,000（ETH を送るだけの送金 1 件は 21,000 gas なので、50 件分）に下げ、base fee は 1 gwei から始めました。target は 525,000 で、送金 25 件で使用率がちょうど 50% になります。

`--no-mining` で自動のマイニングを止め、送金を [mempool](../mempool/)（ブロックに入る前のトランザクションを置く場所）に溜めてから、`evm_mine` でブロックを 1 つずつ作ります。並び順は、tip の高いトランザクションを先にする Anvil の既定の設定（`--order fees`）です。

以下は、実験の [lab/run.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/gas-eip-1559/lab/run.py) から、式の計算と、ブロックを作る部分の抜粋です。`transfer` は `eth_sendTransaction` で送金を 1 件送り、`block` は `eth_getBlockByNumber` の結果から gas の使用量と base fee を取り出す関数です。

```python
def expected_base_fee(parent_base_fee, parent_gas_used, parent_gas_limit):
    """EIP-1559 の式で、親ブロックから次のブロックの base fee を計算する。"""
    target = parent_gas_limit // ELASTICITY_MULTIPLIER
    if parent_gas_used == target:
        return parent_base_fee
    if parent_gas_used > target:
        delta = parent_base_fee * (parent_gas_used - target) // target // BASE_FEE_MAX_CHANGE_DENOMINATOR
        return parent_base_fee + max(delta, 1)
    delta = parent_base_fee * (target - parent_gas_used) // target // BASE_FEE_MAX_CHANGE_DENOMINATOR
    return parent_base_fee - delta


def mine_with(filler, to, n_transfers, tip=2 * GWEI, max_fee=1000 * GWEI):
    """filler から n 件の送金を mempool に入れてから、ブロックを 1 つ作る。"""
    for _ in range(n_transfers):
        transfer(filler, to, max_fee, tip)
    rpc('evm_mine')
    return block()
```

手順は次の通りです。まず、target ちょうど（25 件）のブロックを 3 つ作ります。次に、Alice が単価の上限 2 gwei、Carol が 5 gwei で、どちらも tip 1 gwei の送金を 1 件ずつ送ります。その後、混雑を作る役のアカウントが tip 2 gwei の送金を 50 件ずつ送り、満杯のブロックを 12 個作ります。base fee が 2 gwei を超えた直後には、Bob が Alice と同じ上限 2 gwei の送金を送ります。最後に、混雑役が送るのを止めてブロックを 12 個作ります。

{{< figure src="images/gas-eip-1559_measured.webp" alt="上段は横軸がブロック番号、縦軸が base fee（gwei）のグラフ。黒い実測の点が青い式の線と重なる。target の 3 ブロックは 1 gwei のまま、満杯の 12 ブロックで 4.11 gwei まで上がり、混雑が止むと下がって 27 番で 0.95 gwei。2 gwei と 5 gwei に Alice と Carol の上限の破線。16 番で Carol が入り、Alice は赤い×で消える。下段は使用率の棒で、3 ブロックが 50%、12 ブロックが 100%、16 番が 2%、その後は 0%" caption="Anvil で実測した base fee と、EIP-1559 の式で計算した値" align="center" >}}

ブロック 2 から 27 までの base fee は、全て式で計算した値と 1 wei も違いませんでした。満杯のブロックが 12 個続くと、base fee は 1 gwei から 4.11 gwei（1.125 の 12 乗倍）まで上がっています。

ブロック 1 だけは、genesis（使用量 0）から計算すると 0.875 gwei になるはずが、起動時に指定した 1 gwei のままでした。Anvil は、指定した値を最初のブロックにも使うようです。出力の要点は次の通りです（全体は [lab/output/output.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/gas-eip-1559/lab/output/output.txt)）。

```text
phase   block  txs    used  base fee(wei)       EIP-1559  cmp
full        4   50  100.0%     1000000000     1000000000   ok  alice pending, carol pending
full       10   50  100.0%     2027286528     2027286528   ok  alice pending, carol pending
  bob sends the same 2 gwei transaction: rejected (max fee per gas less than block base fee)
full       15   50  100.0%     3653236150     3653236150   ok  alice pending, carol pending
empty      16    1    2.0%     4109890668     4109890668   ok  alice gone, carol included (price 5.000 = base fee + tip 0.890 gwei)
empty      22    0    0.0%     1855039692     1855039692   ok  alice gone
```

<br>

#### 満杯の間は tip の競争になる

Alice と Carol のトランザクションは、満杯の 12 ブロックの間、一度も入りませんでした。ブロック 4〜9 の base fee は Alice の上限 2 gwei を下回っており、base fee の条件は満たしています。それでも入らなかったのは、混雑役の 50 件の tip が 2 gwei で、tip 1 gwei の 2 件より先に並び、ブロックを埋めたからです。

base fee が上がれば需要が減り、ブロックは target に戻る、というのが EIP-1559 の想定です。base fee が需要に追いつくまでの間は、ブロックに入るトランザクションを決めるのは tip の高さで、London 以前に近い入札の形に戻ります。

<br>

#### 上限を超えたトランザクションは入らない

混雑役が止まったブロック 16 で、Carol のトランザクションが入りました。base fee は 4.11 gwei で、Carol の上限 5 gwei までの残りは 0.89 gwei です。tip は 1 gwei と書いていましたが、実際に払ったのは 0.89 gwei で、1 gas あたりの額はちょうど上限の 5 gwei でした。

Alice のトランザクションは、同じブロック 16 で mempool から消えました。`eth_getTransactionByHash` も null を返し、ブロック 22 で base fee が 1.86 gwei まで下がって上限の 2 gwei を下回った後も、戻ってきませんでした。理由は次の節で見ます。

また、base fee が 2 gwei を超えたブロック 10 の直後に、Bob が Alice と同じ 2 gwei の上限で送ったトランザクションは、`max fee per gas less than block base fee` で受け付けられませんでした。

<br>

#### base fee の下限

base fee を 20 wei から始め、空のブロックを続けた結果が以下です（全体は同じ output.txt の (2) にあります）。

```text
empty      10    0    0.0%              8              8   ok
empty      11    0    0.0%              7              7   ok
empty      14    0    0.0%              7              7   ok
full       15   50  100.0%              7              7   ok
full       16   50  100.0%              8              8   ok
```

20、18、16、14、13 と下がった base fee は 7 wei で止まり、空のブロックが続いても下がりませんでした。満杯のブロックを入れると、12.5% なら 0.875 wei のところ、最低の 1 wei が足されて 8、9 と上がっています。

---

### 上限を下回ったトランザクションの行方

Alice のトランザクションが消えたのは、Anvil の実装の振る舞いです。[Anvil v1.7.1 のブロックを作る処理](https://github.com/foundry-rs/foundry/blob/4072e48705af9d93e3c0f6e29e93b5e9a40caed8/crates/anvil/src/eth/backend/executor.rs#L380-L408)は、mempool のトランザクションを順に見て、ブロックの gas が足りなければトランザクションを飛ばし、そのまま mempool に残します。gas が足りてトランザクションを検証した時に失敗すれば、無効なトランザクションとして記録し、[ブロックを作った後に mempool から取り除きます](https://github.com/foundry-rs/foundry/blob/4072e48705af9d93e3c0f6e29e93b5e9a40caed8/crates/anvil/src/eth/pool/mod.rs#L183-L187)。Anvil は受け付ける時にもその時の base fee と比べるので、Bob のトランザクションは最初から拒否されました。

満杯の間の Alice は、受け付けた後に base fee が上限を超え、ブロックの gas が足りずに飛ばされ、mempool に残っていました。ブロック 16 で空きができて検証された時には、maxFeePerGas が base fee を下回っていたので、無効として取り除かれました。

一方で、[go-ethereum](https://github.com/ethereum/go-ethereum)（geth）v1.17.10 の mempool は、受け付ける時に、ノードが決める [tip の最低額は比べます](https://github.com/ethereum/go-ethereum/blob/v1.17.10/core/txpool/validation.go#L159-L162)が、base fee とは比べません。base fee に届かないトランザクションは、ブロックを組み立てる時に [base fee で絞り込んで](https://github.com/ethereum/go-ethereum/blob/v1.17.10/miner/worker.go#L593-L599)外すだけで、[絞り込みは取り出した一覧に対して行います](https://github.com/ethereum/go-ethereum/blob/v1.17.10/core/txpool/legacypool/legacypool.go#L510-L515)。mempool が溢れて追い出されない限り、base fee が上限を下回るまで下がれば、そのトランザクションは改めてブロックの候補になります。

{{< figure src="images/gas-eip-1559_pool.webp" alt="2 段の流れ図。上段の Anvil 1.7.1 は、mempool（受け付けて置く）から、ブロックを作る時に検証（maxFeePerGas < base fee で失敗）へ進み、赤い箱の「無効として取り除く（その後も戻らない）」で終わる。下段の geth v1.17.10 は、mempool から、候補から外す（base fee で絞り込む）へ進み、緑の箱の「mempool に残る」から、破線の矢印が「base fee が下がれば、また候補になる」と mempool に戻る。下に、どちらも maxFeePerGas が base fee 未満のトランザクションをブロックに入れない点は同じ（プロトコルの規則）" caption="maxFeePerGas が base fee を下回ったトランザクションの、Anvil と geth での扱い" align="center" >}}

どちらのノードも、そのトランザクションをブロックに入れない点は同じです。違うのは、入れられないトランザクションをその後も持ち続けるかどうかです。

<br>

base fee を超える上限を書いたトランザクションしかブロックに入れないことは、全ノードが守るプロトコルの規則です。それに対して、上限に届かないトランザクションを受け付けるか、置いておくか、消すかは、[mempool のノート](../mempool/#consensus-rule-と-policy-の違い)で説明した、ノードごとのポリシー（policy）です。送ったトランザクションがしばらく入らない時、待てば入るのか、送り直すべきなのかは、トランザクションを受け取ったノードの実装で変わります。

送り直す時は、同じ [nonce](../ethereum-account-model/)（送り主ごとの通し番号）で上限を上げたトランザクションを送り、前のトランザクションを置き換えます。geth の既定では、置き換えに元のトランザクションより 10% 以上高い額が必要です（[`PriceBump: 10`](https://github.com/ethereum/go-ethereum/blob/v1.17.10/core/txpool/legacypool/legacypool.go#L163)）。

---

### 利点

- 同じブロックのトランザクションは同じ base fee を払い、他人の入札を読んで額を当てる必要が減る
- base fee の変化は 1 ブロックで最大 12.5% なので、数ブロック先までの上限を見積もれる
- 一時的な混雑は、ブロックを target の 2 倍まで伸ばして吸収できる
- base fee が焼却されるので、提案者には base fee を吊り上げる動機が無い

### 欠点

EIP-1559 は、混雑の値段を前のブロックの使用量からプロトコルが決めます。その代わりに、次の制約があります。

- base fee が需要に追いつくまでの数ブロックは、tip の競争に戻る
- 書いた上限を base fee が超えるとトランザクションは入らず、ノードによっては mempool から消えて送り直しが要る
- ノードは、target の 2 倍の大きさのブロックが一時的に来ても処理できるように備える必要がある
- 焼却する量は利用量で決まり、ETH の供給量を固定できなくなる

最後の 2 つは、EIP の [Security Considerations](https://github.com/ethereum/EIPs/blob/ba6c342c23164072adb500c3136e3ae6eabff306/EIPS/eip-1559.md#security-considerations) が挙げているものです。

### EIP-1559 の効果が小さくなりやすいケース

- 需要が上限を長く上回り、満杯のブロックが続く時
- 数ブロックで終わる急な混雑で、base fee が上がりきる前に収まる時
- ブロックの中でトランザクションが並ぶ順番に価値がある時

満杯のブロックが続く間は、実験の Alice と Carol のように、入るトランザクションを決めるのは tip です。また、EIP-1559 が決めるのはブロックに入る額で、ブロックの中の並び順ではありません。並び順を争うトランザクションでは、tip や、[ブロックを組み立てる者](../pbs/)への支払いで順番が決まります。この話は [MEV](../mev/) のノートで扱っています。
