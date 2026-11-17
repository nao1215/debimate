---
title: "UTXO - 送金の手数料は、残高ではなく使う UTXO の数で決まる"
date: 2026-08-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "bitcoin"]
weight: 5
wrapTables: true
topics: ["Transaction / Wallet"]
---

[Bitcoin](https://bitcoin.org/) には、口座ごとの残高を書いた欄がありません。送金 1 回分の記録であるトランザクションは「誰に、いくら」を出力として残し、まだ使われていない出力を UTXO（Unspent Transaction Output、未使用のトランザクション出力）と呼びます。[ウォレット](../wallet/)に表示される残高は、自分の鍵で使える UTXO の額を足した値です。

ここで 1 つ予想してみてください。Alice と Carol のウォレットは、どちらも残高が 1 BTC です。Alice は 1 BTC を 1 回で受け取り、Carol は 0.005 BTC を 200 回受け取りました。2 人が同じ手数料率で 0.9 BTC を送ると、手数料はどれだけ違うでしょうか。手数料率は、トランザクションの大きさ 1 vB（virtual byte）あたりに払う額で、単位の sat（satoshi）は 1 億分の 1 BTC です。

{{< figure src="images/utxo_fee_same_balance.webp" alt="残高 1 BTC の 2 つのウォレットから 0.9 BTC を手数料率 10 sat/vB で送った時の手数料。UTXO 1 個のウォレットは入力 1 個・見積もり 141 vB で 1,410 sat、UTXO 200 個のウォレットは入力 181 個・見積もり 12,381 vB で 123,810 sat" caption="同じ残高・同じ送金額でも、手数料は 88 倍に開く" align="center" >}}

手元で実際のトランザクションを組み立て、大きさから手数料を見積もって署名すると、Alice の手数料は 1,410 sat、Carol は 123,810 sat で、88 倍の差が出ました。Carol は 0.9 BTC に届くまで UTXO を 181 個並べる必要があり、手数料はその分だけ大きくなります。

小額の入金を多く受け取るサービス、例えば投げ銭や EC の決済、取引所の入金用アドレスでは、Carol と同じ状態が自然にできます。残高は十分なのに出金の手数料が見積もりより大きい、残高があるのに送金を作れない、といった問題は、残高ではなく UTXO の並びを見ると説明できます。

<br>

本記事では、Bitcoin のウォレットや入出金の処理を扱う開発者に向けて、UTXO が手数料と送金の可否をどう決めるか説明します。材料は手元の実験と、実際に払われた手数料率のデータです。次の疑問を順に扱います。

- 残高はどこに記録され、送金で何が消えて何が増えるのか。
- 同じ残高でも、手数料が 88 倍に開くのはなぜか。
- 残高があるのに送れなくなるのは、どんな時か。
- 同じ UTXO を 2 回使う送金は、何が止めるのか。
- Ethereum の残高と比べて、何が違うのか。
- 小さな UTXO が溜まるサービスは、何を決めておくべきか。

---

### 出力を丸ごと使う送金

まず、送金でデータがどう変わるかを見ます。トランザクションは入力と出力を持ちます。出力は「額」と「次に使える条件」の組で、条件には通常、受取人の鍵による署名が必要なことが書かれます。支払いの宛先に使うアドレスは、この条件を組み立てるための情報を符号化した文字列です。条件の書き方は [Bitcoin Script](../bitcoin-script/) で扱っています。

入力は、使う UTXO を「どのトランザクションが作った何番目の出力か」の組で指し、その条件を満たす[デジタル署名](../digital-signature/)を添えます。この組を outpoint と呼び、トランザクションは txid という識別子で指します。txid の計算は [Bitcoin Merkle Tree](../bitcoin-merkle-tree/) で説明しています。入力に指した UTXO は額の一部だけを使うことができず、丸ごと使います。送る額との差は、自分宛ての出力としてお釣りに戻します。

{{< figure src="images/utxo_tx_shape.webp" alt="Alice が受け取った 1 BTC の出力を入力 0 で丸ごと使うトランザクション。出力 0 は Bob 宛ての 90,000,000 sat、出力 1 は Alice へのお釣り 9,998,590 sat。入力と出力の差 1,410 sat が手数料" caption="冒頭で Alice が送ったトランザクション。使った出力は消え、新しい出力 2 つが UTXO になる" align="center" >}}

上記の図は、冒頭の実験で Alice が送ったトランザクションです。1 億 sat の UTXO を使い、Bob へ 9,000 万 sat、自分へ 9,998,590 sat を出力しました。トランザクションを集めてブロックを作る参加者をマイナーと呼びます。トランザクションに手数料の欄は無く、入力の合計から出力の合計を引いた差の 1,410 sat が、そのトランザクションをブロックに取り込んだマイナーの報酬になります。お釣りの出力を書き忘れると、差額の全部が手数料になります。

ネットワークに参加するノードは、全ての UTXO を集めた UTXO セットを持ちます。新しいトランザクションを受け取ると、入力が指す UTXO がセットにあるか、署名が条件を満たすか、出力の合計が入力の合計を超えていないかを調べます。

ブロックに入ったトランザクションの入力はセットから消え、出力が加わります。トランザクションがノードに届いてからブロックに入るまでの流れは [Bitcoin Transaction Lifecycle](../bitcoin-transaction-lifecycle/) で説明しています。

<br>

入力が指す出力をさかのぼると、ブロックの報酬を新しく発行するコインベーストランザクションに行き着きます。コインベースは [Bitcoin Block](../bitcoin-block/) で扱っています。

前の持ち主の署名で次の持ち主宛ての出力を作る連なりなので、[Bitcoin のホワイトペーパー](https://bitcoin.org/bitcoin.pdf)はコインを「a chain of digital signatures」（デジタル署名の連鎖）と定義しています。実際のトランザクションは入力と出力を複数持てるので、連なりは 1 本の鎖ではなく、合流と分岐を持つグラフになります。

<br>

#### 2010 年の桁あふれ

手数料の欄が無いので、出力の合計が入力の合計を超えないかという比較が、コインの水増しを防ぐ検査も兼ねています。2010 年 8 月 15 日、この検査をすり抜けたトランザクションがブロック 74638 に入りました。[当時フォーラムに投稿された報告](https://bitcointalk.org/index.php?topic=822.0)には、約 922 億 BTC の出力を 2 つ持つトランザクションと、50.51 BTC を受け取ったコインベースが載っています。

[当時の実装](https://github.com/bitcoin/bitcoin/blob/4bd188c4383d6e614e18f79dc337fbabe8464c82/main.cpp)は、出力ごとの額が負でないことと、手数料が負でないことは調べていましたが、出力の額を足す時に 64 ビットの符号付き整数があふれることを考えていませんでした。報告に入力の額は無いので、コインベースの額と合う 0.5 BTC を入力に置いて、当時の計算を再現します。

```python
import ctypes

def int64(x):  # C++ の int64_t と同じく、64 ビットに収まらない桁を捨てる
    return ctypes.c_int64(x).value

value_in = 50_000_000                     # 入力 0.5 BTC（sat 単位）
vout = [9_223_372_036_854_275_808] * 2    # 出力 2 つ（約 922 億 BTC ずつ。sat 単位の int64 の上限付近）
value_out = int64(sum(vout))              # 出力の合計
fee = value_in - value_out                # 手数料 = 入力 - 出力
print(value_out, fee, fee < 0)
```

```text
-1000000 51000000 False
```

出力の合計は負の値に回り込んで -0.01 BTC になり、手数料は正の 0.51 BTC になるので、検査を通ります。報告にあるコインベースの 50.51 BTC は、新規発行の 50 BTC にこの手数料 0.51 BTC を足した額と一致します。

[修正](https://github.com/bitcoin/bitcoin/commit/d4c6b90ca3f9b47adb1b2724a0c3514f80635c84)は、1 つの出力にも出力の合計にも 2,100 万 BTC の上限を設けました。同じ検査は、今の Bitcoin Core の [tx_check.cpp](https://github.com/bitcoin/bitcoin/blob/v30.0/src/consensus/tx_check.cpp) に残っています。

Bitcoin では、チェーンが 2 つに分かれた時、より多くの計算を積んだ長い方が残ります。修正したノードが伸ばしたチェーンがやがて元のチェーンを追い越し、このトランザクションは履歴から消えました。今のチェーンで高さ 74638 にあるのは別のブロックで、コインベースは 50 BTC です。

---

### 手数料を決める入力の数

手数料をいくら残すかは、トランザクションを作る人が決めます。ただし、マイナーは 1 vB あたりの手数料、つまり手数料率が高いトランザクションから順にブロックへ取り込みます。取り込む順番は [Mempool](../mempool/) で説明しています。

同じ速さで取り込まれたいなら、トランザクションの大きさ（vB）に手数料率を掛けた額を払う必要があります。手数料は送る額ではなく大きさで決まり、入力が増えると、大きさの大半を入力が占めます。

Bitcoin には、署名をトランザクションの本体と別の witness という領域に置く SegWit（Segregated Witness）という改良があります。冒頭の実験は、SegWit で加わった P2WPKH（Pay to Witness Public Key Hash）という形の出力を使い、Python の標準ライブラリだけでトランザクションを組み立てて署名しました。Alice と Carol が受け取った UTXO は、受け取りのトランザクションを省いて UTXO セットに直接置いています。

P2WPKH の入力 1 個は 68 vB、出力 1 個は 31 vB で、残りはバージョン番号やロックタイムなどの固定の部分です。vB は、Bitcoin の改良提案である BIP（Bitcoin Improvement Proposal）の 1 つ、[BIP 141](https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki) が定める大きさで、witness の部分は 4 分の 1 に割り引いて数えます。

次のコードは実験の抜粋です。`serialize` はトランザクションをバイト列にする関数、`build` は入力と出力からトランザクションを組み立てて署名する関数で、どちらも [utxo_lab.py](lab/utxo_lab.py) にあります。

```python
def vsize(tx):
    weight = len(serialize(tx, False)) * 3 + len(serialize(tx))
    return math.ceil(weight / 4)


def pay(coins, key, amount, to_script, rate):
    """Largest-first selection until inputs cover amount + fee; change back to `key`."""
    coins = sorted(coins, key=lambda c: -c[2])
    for count in range(1, len(coins) + 1):
        chosen = coins[:count]
        total = sum(c[2] for c in chosen)
        draft = build(chosen, key, [(amount, to_script), (0, key.script)], signed=False)
        fee = vsize(draft) * rate
        if total >= amount + fee:
            tx = build(chosen, key, [(amount, to_script), (total - amount - fee, key.script)])
            return tx, fee
    raise ValueError('insufficient funds')
```

`pay` は、額の大きい UTXO から順に入力へ加え、送る額と手数料に届いた所で止めます。手数料は、署名の代わりに 72 バイトの仮置きを入れた時の大きさから決めます。ウォレットも同じように、仮の署名で大きさを見積もってから署名します。結果は次の通りで、`one` は Alice、`many` は Carol のウォレットです。

```text
one: balance=100000000 sat in 1 coins -> send 90000000 sat at 10 sat/vB: inputs=1 vsize=141 vB fee=1410 sat
many: balance=100000000 sat in 200 coins -> send 90000000 sat at 10 sat/vB: inputs=181 vsize=12357 vB fee=123810 sat
```

出力の `vsize` は署名後に測った大きさで、`fee` は見積もりから決めた額です。Carol の見積もりは 12,381 vB で、123,810 sat はこれに 10 sat/vB を掛けた額です。実際の署名には仮の 72 バイトより短いものがあるので、署名後は 24 vB 小さい 12,357 vB になりました。

Carol のトランザクションは 12,357 vB のうち 99.4% が 181 個の入力で、入力以外は 73 vB ほどです。0.005 BTC の UTXO だけで 0.9 BTC と手数料を払うには 181 個が必要で、どの順に選んでも入力の数は減りません。送る額が 0.9 BTC でも 0.0001 BTC でも、手数料は「何個の UTXO を使うか」でほぼ決まります。

<br>

UTXO の額がばらばらな時は、どれを組み合わせるかで入力の数が変わります。この選び方をコイン選択（coin selection）と呼びます。[Bitcoin Core](https://bitcoincore.org/) のウォレットは、それまでの選び方では必要以上に多くの入力を使うことがあり、手数料率が高い時ほど損が大きくなっていました。[27.0](https://bitcoincore.org/en/releases/27.0/) で加わった CoinGrinder は、手数料率が高い時だけ働き、足りる組み合わせのうちトランザクションが最も小さくなるものを探します。経緯は [Bitcoin Optech の日本語版ニュースレター](https://bitcoinops.org/ja/newsletters/2024/01/03/)に載っています。

---

### 残高があるのに送れない UTXO

入力 1 個に 68 vB 掛かるので、UTXO 1 個を使うだけで「68 × 手数料率」の手数料が要ります。額がそれより小さい UTXO は、使うと赤字になります。実験では、1,000 sat を 100 回受け取ったお店のウォレットで、全部を 1 つの出力にまとめて送ると、送り先がいくら受け取れるかを手数料率ごとに測りました。

{{< figure src="images/utxo_small_coins.webp" alt="1,000 sat の UTXO 100 個をまとめて送った時に送り先が受け取る額。手数料率 1 sat/vB で 93,158 sat、10 sat/vB で 31,580 sat、14 sat/vB で 4,212 sat。14.7 sat/vB を超えると、全部を入力にすると額がマイナスになり、赤字の UTXO を外すと使える UTXO が無くなる" caption="表示上の残高は 100,000 sat のまま、送れる額は手数料率で 0 まで減る" align="center" >}}

1,000 ÷ 68 = 14.7 sat/vB を超えると、UTXO 1 個の額より 1 個を使う手数料が大きくなります。手数料率 15 sat/vB では、100 個を全部使うと手数料が残高を 2,630 sat 上回り、トランザクションを作れません。表示上の残高は 100,000 sat のままで、送れる額は 0 です。

```python
def sweep(coins, key, to_script, rate, send_max):
    """Like Bitcoin Core sendall: one output; send_max drops coins that cannot pay for themselves."""
    spend = [c for c in coins if not send_max or c[2] - rate * INPUT_VB > 0]
    if not spend:
        return None
    draft = build(spend, key, [(0, to_script)], signed=False)
    fee = vsize(draft) * rate
    total = sum(c[2] for c in spend)
    return {'inputs': len(spend), 'vsize': vsize(draft), 'fee': fee, 'received': total - fee}
```

`sweep` の `send_max` は、Bitcoin Core の [`sendall`](https://github.com/bitcoin/bitcoin/blob/v30.0/src/wallet/rpc/spend.cpp) にある同じ名前のオプションに合わせました。オプションの説明は「自分の手数料を払える UTXO だけを使う」で、残りは使わずに残します。UTXO の額から使う手数料を引いた値を effective value と呼び、Bitcoin Core のコイン選択も、この値が正の UTXO を分けて扱います。

<br>

#### 実際の手数料率と 14.7 sat/vB

14.7 sat/vB が高いか低いかは、時期で大きく変わります。[mempool.space の API](https://mempool.space/docs/api/rest) から、2023 年 11 月から 2026 年 11 月までのブロックの手数料率（ブロックごとの[中央値](/ml/math/median/)を約 12 時間ずつ平均した値）を取得しました。API の値は整数に切り捨てられているので、14.7 sat/vB 以上の判定は、実際には 15 sat/vB 以上の期間を数えています。

{{< figure src="images/utxo_fee_history.webp" alt="2023 年 11 月から 2026 年 11 月までの手数料率の推移。2024 年は 44% の期間で 14.7 sat/vB を上回り、2024 年 4 月 20 日に 1,192 sat/vB に達した。2025 年以降は最大 13 sat/vB で、14.7 sat/vB を一度も超えていない" caption="1,000 sat の UTXO は、2024 年の 44% の期間で赤字、2025 年以降は一度も赤字にならない" align="center" >}}

2024 年は、期間の 44% で中央値が 14.7 sat/vB 以上でした。最も高かったのは 2024 年 4 月 20 日の 1,192 sat/vB で、ブロックの報酬が半分になる半減期（halving）の日です。一方で、2025 年の最大は 13 sat/vB、2026 年は 5 sat/vB で、1,000 sat の UTXO は一度も赤字になっていません。同じ UTXO が、使える時期と使えない時期を行き来します。取得と集計のコードは [fee_history.py](lab/fee_history.py) にあります。

<br>

#### ノードが中継しない小さな出力

小さすぎる出力は、作る段階でも止められます。Bitcoin Core は、3 sat/vB で使う時の手数料が額を上回る出力をダスト（dust）と呼び、ダストの出力を含むトランザクションを原則として中継せず、ブロックの候補にも入れません。v30.0 の既定にも例外があります。手数料 0 の親が持つダストが 1 個だけで、一緒に送る子のトランザクションがそれを使う場合で、ephemeral dust と呼ばれます。

ダストの境目は [policy.cpp の `GetDustThreshold`](https://github.com/bitcoin/bitcoin/blob/v30.0/src/policy/policy.cpp) が、出力と、それを使う入力の大きさに 3 sat/vB を掛けて決めます。

| 出力の形 | ダストになる額（v30.0 の既定） |
| --- | --- |
| P2WPKH | 294 sat 未満 |
| P2TR | 330 sat 未満 |
| P2PKH | 546 sat 未満 |

この境目は 3 sat/vB で計算した値なので、1,000 sat の出力は作れます。作れることと、後で黒字で使えることは別です。ダストの判定はノードごとの受け入れの規則（policy）で、ブロックの有効性を決める規則ではありません。違いも Mempool のノートで扱っています。

---

### 二重支出を止める UTXO セット

同じ UTXO を 2 つの送金に使うことは二重支出（double spending）と呼ばれます。UTXO のモデルでは、二重支出の判定は「入力が指す UTXO がセットにあるか」だけで済みます。実験では、ノードが持つ UTXO セットを辞書で表し、トランザクションを適用する処理を書きました。次のコードは抜粋で、署名を検査する数行を省いています。

```python
class UtxoSet:
    """Outpoint (txid, vout) -> (value, script). Applies transactions like a node would."""

    def __init__(self):
        self.coins = {}

    def apply(self, tx):
        spent = 0
        for index, txin in enumerate(tx['vin']):
            outpoint = (txin['txid'], txin['vout'])
            if outpoint not in self.coins:
                return f'rejected: input {index} is not in the UTXO set'
            value, script = self.coins[outpoint]
            # ここで署名が script の条件を満たすかを検査する（省略）
            spent += value
        created = sum(o['value'] for o in tx['vout'])
        if created > spent:
            return 'rejected: outputs exceed inputs'
        for txin in tx['vin']:
            del self.coins[(txin['txid'], txin['vout'])]
        new_id = txid(tx)
        for n, o in enumerate(tx['vout']):
            self.coins[(new_id, n)] = (o['value'], o['script'])
        return f'accepted: fee {spent - created} sat'
```

Alice の送金を適用した後、同じ 1 BTC の UTXO をお店宛てに使うトランザクションを作り、正しく署名して適用しました。

```text
spend alice's 1 BTC coin again: rejected: input 0 is not in the UTXO set
spend alice's change coin: accepted: fee 2000 sat
```

次の図にある one:0 は、Alice が受け取ったトランザクション one の 0 番目の出力を指す outpoint で、many:0〜199 は Carol が受け取った 200 個の UTXO です。tx1 は Alice の送金、tx2 は 2 回目の送金です。

{{< figure src="images/utxo_double_spend.webp" alt="UTXO セットの変化。使う前は one:0（Alice の 1 BTC）と many:0〜199 がある。tx1 を当てはめると one:0 が削除され、tx1:0（Bob 0.9 BTC）と tx1:1（Alice のお釣り）が加わる。one:0 を入力に指す tx2 は、入力が UTXO セットに無いので拒否される" caption="2 回目の送金は、署名が正しくても入力が見つからずに拒否される" align="center" >}}

2 回目の送金は、署名も額も正しいのに、入力の UTXO がセットから消えているので拒否されました。お釣りの UTXO は新しくセットに加わっているので使えます。

ただし、これはブロックに入った後の話です。2 つのトランザクションがまだどちらもブロックに入っていない間は、ノードごとに先に届いた方を持ち、どちらが残るかは [Proof of Work](../proof-of-work/) で作られる次のブロックで決まります。手数料の高い方へ置き換える RBF（Replace-By-Fee）という規則もあります。RBF も Mempool のノートで扱っています。受け取る側が、ブロックに入る前の入金を確定と扱わないのはこのためです。

ブロックに入った後でも、チェーンの末尾が分かれて片方のブロックが捨てられると、そこで使われた出力はセットに戻り、作られた出力は消えます。分岐の解消は、コインベースと同じく Bitcoin Block のノートで扱っています。

---

### Ethereum と比べた違い

[Ethereum](https://ethereum.org/) は、アドレスごとに残高と通し番号（nonce）を状態として持つアカウントモデルです。仕組みは [Ethereum Account Model](../ethereum-account-model/) で説明しています。同じ「1 BTC を 200 回に分けて受け取った」状況を当てはめると、違いがはっきりします。

| 観点 | Bitcoin（UTXO） | Ethereum（アカウント） |
| --- | --- | --- |
| 残高の持ち方 | UTXO の合計をウォレットが計算 | アドレスの残高をノードが保持 |
| 送金の手数料 | 使う UTXO の数でほぼ決まる | ETH の送金は 21,000 gas で一定 |
| 二重支出の防ぎ方 | 使った UTXO をセットから消す | nonce を 1 つずつ進める |
| 同じ送り手の送金 | 別の UTXO なら互いに独立 | nonce の順にしか取り込まれない |
| お釣り | 毎回、自分宛ての出力を作る | 残高から引くだけで不要 |

Ethereum では、ETH を 200 回受け取っても 1 回受け取っても、ETH を送る手数料は [21,000 gas](https://ethereum.org/en/developers/docs/gas/) で変わりません。入金の回数が手数料に響くのは UTXO モデルの特徴です。

一方で、UTXO は互いに独立しているので、別々の UTXO を使えば、同じウォレットから出る 2 つの送金を同時に作れます。Ethereum では nonce が 1 つ飛ぶと、番号が後の送金は前の番号が取り込まれるまで待たされます。どちらが良いというより、入金の回数と送金の並び方のどちらに制約が掛かるかが違います。

---

### 小さな UTXO が溜まる時に決めること

小額の入金を受け取るサービスで UTXO を扱う時は、冒頭の Carol のような手数料や、送れない残高を避けるために、次の 3 つを決めておきます。どれも、手元にある UTXO の数と額を知っていることが前提で、Bitcoin Core なら `listunspent` で一覧を取れます。表の「統合（consolidation）」は、複数の UTXO を自分宛ての 1 つの出力に移すトランザクションです。

| 決めること | 判断の材料 |
| --- | --- |
| 統合する時期 | 100 個の統合は 1 sat/vB で 6,842 sat、14 sat/vB で 95,788 sat |
| 受け付ける入金の最小額 | 想定する最も高い手数料率 × 68 vB を上回る額 |
| 小額の支払いに使う経路 | チェーンの外でやり取りする [Lightning Network](../lightning-network/) |

最小額は、2024 年のように数百 sat/vB の時期を想定に入れるかで大きく変わります。400 sat/vB を想定すれば、P2WPKH の UTXO 1 個を使う手数料は 27,200 sat で、それより小さい入金は混雑した時期には使えません。

統合には注意点もあります。1 つのトランザクションの入力に並べた UTXO は、同じ持ち主のものだと外から推測されます。この推測は [common-input-ownership heuristic](https://en.bitcoin.it/wiki/Common-input-ownership_heuristic) と呼ばれ、別々のアドレスで受け取った入金が結び付けられます。入金の出どころを分けておきたい用途では、まとめる範囲を考えます。

<br>

冒頭の 88 倍の差は、残高ではなく Carol が受け取った回数で決まっていました。Bitcoin を扱うシステムでは、残高の数字に加えて、UTXO の数・額・その時の手数料率を並べて見ると、出金の手数料と、送れるかどうかが分かります。

実験のコードと実行の手順は [lab の README](lab/README.txt) にあり、Python の標準ライブラリだけで動きます。ネットワークには接続せず、鍵は固定の文字列から作った使い捨てのものです。
