---
title: "MEV - トランザクションの並び順から生まれる価値と利用者の損失"
date: 2026-11-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "mev", "defi"]
weight: 25
wrapTables: true
topics: ["Node Policy"]
---

ブロックチェーンでは、利用者が送ったトランザクションはすぐには実行されません。いったんトランザクションの置き場に集められ、ブロックを作る者がその中からトランザクションを選び、順番に並べて[ブロック](../blockchain-basics/)（トランザクションをまとめた記録の単位）にした時に、上から順に実行されます。

MEV（Maximal Extractable Value）は、ブロックを作る者がトランザクションを入れる・外す・並べ替えることで得られる価値のうち、通常のブロック報酬と手数料を超える分です。送り主が決められるのはトランザクションの中身までで、並び順に値段を付けられるのはブロックを作る者です。

<br>

チェーンの上でプログラムとして動く取引所（後の節で説明する AMM）の例で、並び順だけで結果が変わる様子を見ます。ETH は Ethereum の通貨で、USDC は米ドルとの連動を目指すトークン（Ethereum の上でプログラムが発行する通貨、[ERC-20](../erc-20/)）です。

取引所のプログラムに、10,000 USDC で ETH を買うトランザクション A が送られたとします。そのトランザクション A を見た別の参加者が、約 15,161 USDC（額の決め方は後の節で説明します）で ETH を買うトランザクション B と、B で得た ETH を全て売るトランザクション C を送りました。

この参加者は、後で説明する searcher と呼ばれる参加者で、この例では利用者から価値を取る攻撃者です。3 件のトランザクションは、指示は同じまま、ブロックに並べる順番を変えるだけで、A の送り主が受け取る ETH の量が変わります。

| ブロック内の順番 | A の送り主が受け取る ETH | B と C の送り主の損益 |
| --- | --- | --- |
| A → B → C | 3.312325 ETH | −90.38 USDC |
| B → A → C | 3.279202 ETH | +9.35 USDC |

上記の表は、後半の実験で計算した値です。損益には、gas 代（トランザクションの実行に払う手数料）とブロックを作る者への支払いを含めていません。A の送り主は「受取が見積もりより 1% 以上減ったら取り消す」という下限を付けています。2 つ目の順番では、A の受取がちょうどこの下限まで 0.033 ETH（1 ETH = 3,000 USDC の換算で約 99 USDC）減り、B と C の送り主が利益を得ています。

変えたのは並び順だけです。ただし、C が売る ETH の量は B で得た量なので、順番に合わせて変わります（A → B → C では約 4.980 ETH、B → A → C では約 5.013 ETH）。

以下は、同じ 2 通りの順で 3 件を実行した時に、取引所が示す ETH の価格（1 ETH あたりの USDC）がどう上下するかを描いた図です。

{{< figure src="images/mev_concept.webp" alt="上段は A → B → C、下段は B → A → C の順にトランザクションを並べ、その上に取引所が示す ETH 価格の動きを重ねた図。下段では B の買いで価格が上がった後に A が買うため、A の受取は 3.312 ETH から 3.279 ETH に減る。どちらの順でも、C の売りで価格は下がる。" caption="3 件のトランザクションを 2 通りの順で並べた時の、取引所の ETH 価格" align="center" >}}

下段では、A は B が押し上げた価格から買い始めます。価格がなぜ買いで上がるのかは、後の節「定数積 AMM の価格」で説明します。

<br>

MEV の M は、最初は Miner の頭文字でした。[Proof of Work](../proof-of-work/) では、計算の競争に勝ったマイナー（miner）がブロックを作っていたからです。この呼び名は、取引所の bot を計測した [Flash Boys 2.0](https://arxiv.org/abs/1904.05234)（Daian らの 2019 年の論文）が付けました。

[ethereum.org の MEV のページ](https://ethereum.org/en/developers/docs/mev/)によると、Ethereum が [Proof of Stake](../proof-of-stake/) に移ってブロックを作る者がマイナーでなくなったことに合わせて、Maximal と呼ぶようになりました。

<br>

本記事では、取引所の計算をローカルで再現しながら、並び順が価値に変わる仕組みを説明します。扱う疑問は次の通りです。

- 並び順を変えるだけで、なぜ価値が生まれるのか。
- 利用者のトランザクションを前後から挟む sandwich attack では、誰がいくら得て、誰がいくら失うのか。
- 利用者が払う手数料と、MEV で受ける不利益は何が違うのか。
- 利用者は何をすれば、取られる額を減らせるのか。

トランザクションと手数料の基本は [Ethereum Transaction](../ethereum-transaction/) を前提にします。実験は Python の計算だけで行い、実際のネットワークや資産は使いません。現在の Ethereum で「ブロックを作る者」が proposer・builder・relay という役割に分かれている話は、[PBS](../pbs/) で扱います。

---

### 並び順が価値になる理由

冒頭の例のように、他人のトランザクションを挟むように前後に割り込んで価値を取るには、2 つの条件が揃う必要があります。以下の図の左が 1 つ目、右が 2 つ目の条件です。

{{< figure src="images/mev_conditions.webp" alt="左の灰色の枠は公開 mempool で、利用者のトランザクション A を searcher が読み、トランザクション B と C を作る。右の枠はブロックを作る者で、B 買い、A 利用者、C 売りの順に並べる。下に、プロトコルが決めるのは同じ送り主のトランザクションを nonce の順に並べることだけで、2 つが揃うと他人のトランザクションを挟むように前後に自分のトランザクションを差し込める、と書いてある" caption="並び順が価値になる 2 つの条件" align="center" >}}

1 つ目は、トランザクションが実行される前に他人から見えることです。送られたトランザクションは、[mempool](../mempool/)（ブロックに入る前のトランザクションを置く場所）を通じてネットワークに広まります。誰でも読める置き場を公開 mempool と呼びます。そのため、利用者が「この値段で買う」と署名したトランザクションは、ブロックに入る前に誰でも読めます。

2 つ目は、ブロックを作る者が、取り込むトランザクションとその順番を選べることです。Ethereum のプロトコルは、ブロックに入れたトランザクションが有効であることは検証します。一方で、同じ送り主のトランザクションを [nonce（通し番号）](../ethereum-account-model/)の順に並べること以外に、並び順の規則を定めていません。

<br>

この 2 つが揃うと、他人のトランザクションを挟むように前後に自分のトランザクションを差し込む余地が生まれます。[スマートコントラクト](../smart-contract/)（チェーンの上で動くプログラム）は実行時点の状態を読んで動くので、取引所なら直前のトランザクションで動いた価格を次のトランザクションがそのまま使います。

上記の図でトランザクション B と C を作っているのは、searcher と呼ばれる参加者です。searcher は、公開 mempool のトランザクションを読んで、このような機会を探します。見つけたトランザクションの組をブロックを作る者に渡し、自分のトランザクションを入れたい位置に入れてもらいます。

ブロックを作る者が searcher の望む位置に入れるのは、その分の支払いを受けるからです。トランザクションの手数料（gas 代、後の節で説明）を上乗せするか、ブロックを作る者へ直接送金して、順番を買います。支払いの仕組みは、後の節「MEV の種類」と PBS のノートで扱います。

---

### 定数積 AMM の価格

冒頭の取引所は、DEX（Decentralized Exchange、スマートコントラクトで動く取引所）の一種である [AMM（Automated Market Maker）](../amm/)です。株の取引所のように売り注文と買い注文を突き合わせる板（オーダーブック）は無く、2 種類のトークンを預けたプール（pool）と、交換比率を計算する式だけで売買が成立します。

代表的な AMM の 1 つである [Uniswap v2](https://app.uniswap.org/whitepaper.pdf) は、プールの残高 `x`（USDC）と `y`（ETH）の積 `x × y` が交換の前後で減らないように受取量を計算します。これを定数積（constant product）と呼びます。

入力の 0.3% は手数料としてプールに残り、流動性提供者（プールにトークンを預けた人）の取り分になります。受取量の計算は、Uniswap v2 の [`getAmountOut`](https://github.com/Uniswap/v2-periphery/blob/master/contracts/libraries/UniswapV2Library.sol) と同じ次の式です。

```text
受取量 = (入力 × 997 × 出力側の残高) / (入力側の残高 × 1000 + 入力 × 997)
```

プールが示す価格は、残高の比 `x / y` です。3,000,000 USDC と 1,000 ETH のプールなら、1 ETH が 3,000 USDC です。ETH を買うと、USDC がプールに入って `x` が増え、ETH が出ていって `y` が減ります。そのため、買いの後は 1 ETH あたりの USDC、つまり価格が上がります。

1 件の買いの中でも、この値上がりは少しずつ進みます。上記のプールで 10,000 USDC を入れても、受け取れるのは 3.333 ETH ではなく約 3.312 ETH です。手数料に加えて、買うほど 1 ETH あたりの値段が上がるからです。これを価格インパクト（price impact）と呼びます。式の導き方は、[AMM](../amm/) のノートで詳しく扱っています。

<br>

ウォレットや取引所の画面は、送信する時点のプールの残高から受取量を見積もります。ところが、自分のトランザクションより前に誰かが同じ向きに買うと、価格が上がった状態から買い始めることになり、受取量は見積もりより減ります。そこで利用者は、受取量が見積もりより一定以上減ったらトランザクションを取り消す下限を付けます。この許容幅を slippage tolerance と呼びます。

Uniswap v2 では、利用者の交換を受け付けるコントラクト（[Router](https://github.com/Uniswap/v2-periphery/blob/master/contracts/UniswapV2Router02.sol)）に、この下限を `amountOutMin` という引数で渡します。受取量がこれを下回ると、トランザクション全体が `INSUFFICIENT_OUTPUT_AMOUNT` というエラーで取り消されます。この下限はトランザクションの中身に書かれるので、公開 mempool に送った時点で誰でも読めます。

---

### sandwich attack の計算

sandwich attack は、利用者の買いの直前に同じ向きの買い（front-run）、直後に売り（back-run）を入れる手口です。利用者は値上がり後の価格で買わされ、攻撃者はさらに上がった価格で売り抜けます。冒頭のトランザクション B が front-run、C が back-run です。

[計算用のコード](lab/sandwich.py)は、前節の式を整数で再現し、同じ指示の 3 件を 2 通りの順で実行します。C は B で得た ETH を全て売るので、C が売る量は順番で変わります。

攻撃者は、mempool で読んだ利用者の下限（`amountOutMin`）を使い、利用者のトランザクションが取り消されない範囲で最も大きい front-run を二分探索で選びます。許容幅を広げると、使える front-run も攻撃者の利益も大きくなります（後半の表）。トランザクションの実行に掛かる手数料（gas 代）は含めていません。

以下は抜粋です。`amount_out` が前節の式、`largest_front` が front-run の大きさを決める二分探索です。

```python
def amount_out(amount_in, reserve_in, reserve_out):
    """UniswapV2Library.getAmountOut と同じ式。入力の 0.3% が手数料になる。"""
    amount_in_with_fee = amount_in * 997
    return amount_in_with_fee * reserve_out // (reserve_in * 1000 + amount_in_with_fee)


def largest_front(victim_usdc, min_eth):
    """利用者のトランザクションが取り消されない範囲で、最も大きい先回りの買いを二分探索する。"""
    lo, hi = 0, 3_000_000 * USDC
    while lo < hi:
        mid = (lo + hi + 1) // 2
        pool = Pool()
        pool.buy_eth(mid)
        if amount_out(victim_usdc, pool.usdc, pool.eth) >= min_eth:
            lo = mid
        else:
            hi = mid - 1
    return lo
```

<br>

<details>
<summary>sandwich.py の全体</summary>

```python
"""Uniswap v2 型の定数積プールで、同じ指示の 3 件のトランザクションを並べ替えて結果を比べる。

C は「B で得た ETH を全て売る」トランザクションなので、C が売る量は順番で変わる。

ネットワークには接続せず、整数の計算だけを行う。gas 代は含めない。
"""

USDC = 10**6   # USDC は小数 6 桁
ETH = 10**18   # ETH は小数 18 桁（wei）


def amount_out(amount_in, reserve_in, reserve_out):
    """UniswapV2Library.getAmountOut と同じ式。入力の 0.3% が手数料になる。"""
    amount_in_with_fee = amount_in * 997
    return amount_in_with_fee * reserve_out // (reserve_in * 1000 + amount_in_with_fee)


class Pool:
    def __init__(self, usdc=3_000_000 * USDC, eth=1_000 * ETH):
        self.usdc = usdc
        self.eth = eth

    def buy_eth(self, usdc_in):
        out = amount_out(usdc_in, self.usdc, self.eth)
        self.usdc += usdc_in
        self.eth -= out
        return out

    def sell_eth(self, eth_in):
        out = amount_out(eth_in, self.eth, self.usdc)
        self.eth += eth_in
        self.usdc -= out
        return out


def run(order, victim_usdc, min_eth, front_usdc):
    """A: 利用者の買い、B: 攻撃者の買い、C: 攻撃者の売り（B で得た ETH を全て売る）。"""
    pool = Pool()
    result = {}
    attacker_eth = 0
    for tx in order:
        if tx == "A":
            # Router は受取量が amountOutMin を下回るとトランザクション全体を取り消す
            if amount_out(victim_usdc, pool.usdc, pool.eth) < min_eth:
                result["A"] = None
                continue
            result["A"] = pool.buy_eth(victim_usdc)
        elif tx == "B":
            attacker_eth = pool.buy_eth(front_usdc)
        elif tx == "C":
            result["C"] = pool.sell_eth(attacker_eth)
    result["profit"] = result["C"] - front_usdc
    return result


def min_out(victim_usdc, tolerance_bps):
    """画面で見積もった受取量から、許容する下落分を引いた最低受取量。"""
    quote = amount_out(victim_usdc, Pool().usdc, Pool().eth)
    return quote * (10_000 - tolerance_bps) // 10_000


def largest_front(victim_usdc, min_eth):
    """利用者のトランザクションが取り消されない範囲で、最も大きい先回りの買いを二分探索する。"""
    lo, hi = 0, 3_000_000 * USDC
    while lo < hi:
        mid = (lo + hi + 1) // 2
        pool = Pool()
        pool.buy_eth(mid)
        if amount_out(victim_usdc, pool.usdc, pool.eth) >= min_eth:
            lo = mid
        else:
            hi = mid - 1
    return lo


def sweep_point(victim_usdc, tolerance_bps):
    """許容幅ごとに、取り消されない最大の先回りで sandwich を組む。"""
    floor = min_out(victim_usdc, tolerance_bps)
    front = largest_front(victim_usdc, floor)
    r = run("BAC", victim_usdc, floor, front)
    r["front"] = front
    return r


def fmt_eth(v):
    return "revert" if v is None else f"{v / ETH:.6f} ETH"


def fmt_usdc(v):
    return f"{v / USDC:+,.2f} USDC"


if __name__ == "__main__":
    victim = 10_000 * USDC
    tol = 100  # 1.00%
    floor = min_out(victim, tol)
    front = largest_front(victim, floor)
    print("pool: 3,000,000 USDC / 1,000 ETH, victim buys with 10,000 USDC")
    print(f"quote {fmt_eth(min_out(victim, 0))}, amountOutMin (1%) {fmt_eth(floor)}")
    print(f"attacker front-run: {front / USDC:,.2f} USDC")
    print()
    for order in ("ABC", "BAC"):
        r = run(order, victim, floor, front)
        print(f"order {'->'.join(order)}: victim gets {fmt_eth(r['A'])}, "
              f"attacker {fmt_usdc(r['profit'])}")
    print()
    print("tolerance  front-run  victim loss        attacker profit")
    quote = min_out(victim, 0)
    for bps in (10, 50, 100, 200, 300, 500):
        r = sweep_point(victim, bps)
        loss = quote - r["A"]
        print(f"{bps / 100:>8.2f}%  {r['front'] / USDC:>9,.0f}  "
              f"{loss / ETH:.6f} ETH ({loss * 3_000 // ETH:>3} USDC)  "
              f"{r['profit'] / USDC:>8.2f} USDC")
```

</details>

<br>

以下が[実行結果](lab/output.txt)の前半です。`quote` はトランザクション前の見積もり、`victim` は利用者、`attacker` は攻撃者です。

```text
pool: 3,000,000 USDC / 1,000 ETH, victim buys with 10,000 USDC
quote 3.312325 ETH, amountOutMin (1%) 3.279202 ETH
attacker front-run: 15,161.30 USDC

order A->B->C: victim gets 3.312325 ETH, attacker -90.38 USDC
order B->A->C: victim gets 3.279202 ETH, attacker +9.35 USDC
```

slippage tolerance が 1% の時、B → A → C の順での利用者の受取は、下限の `amountOutMin` と同じ 3.279202 ETH です。攻撃者が取り消しの直前まで front-run を大きくしたので、損失は許容幅の上限に達しています。つまり、slippage tolerance は「この額までなら取られてもよい」という上限としても働きます。

A → B → C の順では、攻撃者は 90.38 USDC を失っています。約 15,000 USDC の 0.3% ずつを 2 回払うので、利用者の買いが間に入らない限り赤字です。B → A → C では、B で買った後に A の買いが価格をさらに押し上げるので、C は高い価格で売れます。この手数料を払った上で 9.35 USDC が残ります。

<br>

許容幅を 0.1% から 5% まで動かすと、利用者の損失（victim loss）と攻撃者の利益（attacker profit）は次のように変わります。以下は実行結果の後半です。

```text
tolerance  front-run  victim loss        attacker profit
    0.10%      1,506  0.003312 ETH (  9 USDC)      0.96 USDC
    0.50%      7,552  0.016562 ETH ( 49 USDC)      4.73 USDC
    1.00%     15,161  0.033123 ETH ( 99 USDC)      9.35 USDC
    2.00%     30,554  0.066247 ETH (198 USDC)     18.25 USDC
    3.00%     46,184  0.099370 ETH (298 USDC)     26.68 USDC
    5.00%     78,182  0.165616 ETH (496 USDC)     42.11 USDC
```

同じ計算を 0.1% 刻みで描くと、次の図になります。

{{< figure src="images/mev_slippage.webp" alt="横軸が slippage tolerance（0.1% から 5%）、縦軸が USDC のグラフ。利用者の損失（赤い破線）と攻撃者の利益（青い実線）は、どちらも許容幅にほぼ比例して増える。1% で損失は約 99 USDC、利益は 9.35 USDC。2 本の線の間は灰色で、その差の大半は攻撃者の 2 回の交換の手数料" caption="slippage tolerance ごとの利用者の損失と攻撃者の利益" align="center" >}}

上記の図の 2 本の線の間は、主に攻撃者が 2 回の交換で払うプールの手数料です。この条件では、利用者が失った額のうち攻撃者に残るのは 1 割未満で、残りの大半は流動性提供者に渡ります。実際の攻撃者は、さらに gas 代と、ブロックを作る者への支払いも負担します。本記事の額は仕組みを見るための小さな例で、gas 代と支払いを差し引いても利益が残るのは、より大きなトランザクションや、許容幅の大きいトランザクションを挟める時です。図の生成コードは [figures.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/mev/figures.py) です。

---

### MEV の種類

全ての MEV が利用者から直接奪う形をとるわけではありません。ethereum.org が挙げる例のうち 3 つを並べると、誰が損をするかが分かれます。

{{< note-panels caption="MEV の代表例。いずれも、狙ったトランザクションの直前・直後の位置を競合より先に取った者が有利になります。" >}}
- title: DEX の裁定取引
  body: 同じトークンの価格が 2 つの取引所でずれた時に、安い方で買って高い方で売ります。
  items:
  - 結果として、取引所の間の価格が揃う
  - 損をするのは、ずれた価格で取引を受けた側（AMM なら流動性提供者）
- title: 清算
  body: "貸付のサービスでは、借り手は担保を預けて借ります。[担保の価値が下がった借り手](../lending/)から、第三者が規定の割引で担保を買い取って返済に充てます。担保の価格は[オラクル](../oracle/)（外部の価格をチェーンに届ける仕組み）から読みます。"
  items:
  - 清算が早いと、貸し手側の資産が守られる
  - 清算された借り手は、割引の分を失う
- title: sandwich attack
  body: 利用者のトランザクションを前後から挟み、悪い価格で約定させます。
  items:
  - 価格を揃える働きは無い
  - 損をするのは、挟まれた利用者
{{< /note-panels >}}

同じ機会は複数の searcher が狙います。ブロックを作る者は、受け取る手数料が多いトランザクションほど前に並べるのが普通です。そのため、トランザクションの組を直接渡す仕組みが広まる前は、searcher 同士が公開 mempool で手数料を競り上げて順番を取り合っていました。Flash Boys 2.0 はこの競り合いを priority gas auction と呼んでいます。

DB のトランザクションと違い、途中で取り消された（revert した）トランザクションもブロックに記録され、そこまでに使った gas の代金を払います。競りに負けたトランザクションは、勝者が先に機会を使い切った後に実行されるので条件を満たせず、多くは失敗したままブロックに入り、ブロックの空きを埋めます。そのため、MEV と無関係な利用者も混雑の影響を受けます。現在は、searcher がトランザクションの組を builder（ブロックの中身を組み立てる参加者）に直接渡す形が主になっています。

---

### 利用者が払う手数料と受ける損失

ウォレットが「手数料」として表示するのは、gas の代金です。gas はトランザクションの計算量を測る単位で、手数料は `使った gas × 1 gas あたりの額` です。

1 gas あたりの額は、混み具合でプロトコルが決めて焼却される（誰にも渡らず消える） base fee と、ブロックを作る者に渡る上乗せの priority fee の和です（詳しくは [Gas and EIP-1559](../gas-eip-1559/)）。sandwich で失う額はここに含まれず、受け取るトークンが少ない形で現れます。

以下は、10,000 USDC の買いで利用者が負担する額を分けた表です。

| 項目 | 渡る先 | 利用者がトランザクション前に分かること | 実験の例 |
| --- | --- | --- | --- |
| base fee | 焼却され、誰にも渡らない | 単価の上限をトランザクションに書ける | 含めていない |
| priority fee | ブロックを作る者 | 単価の上限をトランザクションに書ける | 含めていない |
| プールの手数料 | 流動性提供者 | 入力の 0.3% と分かっている | 30 USDC |
| 価格インパクト | プール（自分の買いで価格が動く分） | 見積もりの受取量に含まれる | 見積もりに反映済み |
| sandwich による損失 | 攻撃者と、攻撃者の手数料を受けるプール | 上限だけが slippage tolerance で分かる | 0.033123 ETH（約 99 USDC） |

上の 4 行は、見積もりや確認画面で、トランザクション前に額か上限が分かります。最後の行だけは、トランザクションが終わって受取量を見るまで額が分からず、手数料の明細にも失敗の表示にも出てきません。

---

### 利用者ができる対策と限界

利用者ができる対策は 3 つあります。比較の前に、2 つの語を説明します。

RPC（Remote Procedure Call）は、ウォレットがトランザクションを送るノードの窓口です。private RPC は、受け取ったトランザクションを公開 mempool に流さず、builder に直接渡す送信先です。builder は、現在の Ethereum でブロックの中身を組み立てる仕事を担う参加者です。

batch auction は、一定の時間に集まった注文をまとめて（バッチにして）約定させる方式です。

{{< note-panels caption="利用者ができる 3 つの対策と、その限界。" >}}
- title: slippage tolerance を小さくする
  body: sandwich で取られる額の上限を下げます。
  items:
  - 小さすぎると、価格の変動だけで取り消される
  - 取り消されても gas は掛かる
- title: private RPC に送る
  body: 公開 mempool に流さずにトランザクションを受け付ける送信先に送ります（例：[Flashbots Protect](https://docs.flashbots.net/flashbots-protect/overview)）。公開 mempool を監視する bot は、トランザクションを事前に読めません。
  items:
  - 送り先の運営者と、トランザクションを受け取る builder を信頼する
  - トランザクションの流れが特定の builder に集まる
- title: batch auction で約定する
  body: 同じバッチで同じトークンの組を同じ向きに交換する注文に同じ価格を付け、バッチ内の順番を無意味にします（例：[CoW Protocol](https://docs.cow.fi/cow-protocol/concepts/introduction/fair-combinatorial-auction)。同プロトコルでは fair combinatorial batch auction と呼ぶ）。
  items:
  - 対応する取引所でしか使えない
  - 約定を組み立てる別の参加者（solver）に頼る
{{< /note-panels >}}

slippage tolerance を小さくする対策は、取られる額の上限を下げます。一方で private RPC と batch auction は MEV を消すわけではなく、誰が並び順を決め、誰がその価値を受け取るかを変えます。

上記の 2 つ目の private RPC で「トランザクションの流れが特定の builder に集まる」と、その builder だけが組める並び順が増え、ブロックの入札で勝ちやすくなります。トランザクションを private に送るほど、ブロック作りが少数に集まる原因になります。この集中は [PBS](../pbs/#private-order-flow-と-builder-の集中) で扱います。

<br>

トランザクションの中身を締め切りまで隠し、読まれても先回りできないようにするアプリ側の設計もあります。入札やくじのように中身を後から明かせる用途では、[Commit-Reveal](../commit-reveal/) が使われます。
