---
title: "Lending - 担保を預けて暗号資産を借りる仕組みと清算"
date: 2026-11-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "defi", "lending"]
weight: 28
wrapTables: true
topics: ["DeFi"]
---

レンディングプロトコル（lending protocol）は、ブロックチェーンの上で暗号資産を貸し借りする仕組みです。貸し手（以下、預け手）が預けた資産を 1 か所に集め（以下、プール）、そこから借り手に貸し出します。銀行の窓口の代わりに、チェーン上で動くプログラムである[スマートコントラクト](../smart-contract/)が、預け入れ・貸し出し・返済を受け付けます。代表例は [Aave](https://aave.com/docs/aave-v3/overview) と [Compound](https://docs.compound.xyz/) です。

借り手は、借りる前に別の暗号資産を担保として預けます。例えば、Alice が 10 ETH（[Ethereum](https://ethereum.org/) の暗号資産）を担保に預け、12,000 [USDC](https://www.circle.com/usdc) を借りたとします。USDC は、1 USDC が 1 米ドルの価値を保つように発行されているトークン（[ERC-20](../erc-20/) の規格で作られた資産）です。Alice は ETH を売らずに、ドル建ての資金を手にできます。

ETH の価格が下がると、担保の価値が借入に近づきます。担保の価値の 80%（この割合は資産ごとに決められています）が借入を下回ると、誰でも Alice の借入を代わりに返済し、その分の担保を割引価格で受け取れます。この処理を清算（liquidation）と言います。

{{< figure src="images/lending_concept.webp" alt="3 つの価格での担保と借入の棒。1 ETH が 2,000 ドルの時は担保 20,000 ドルの 80% の点線が借入 12,000 USDC より上にあり HF 1.33。1,600 ドルでは点線が借入に近づき HF 1.07。1,400 ドルでは点線が借入の棒を下回り、赤い × が付いて HF 0.93" caption="ETH の価格が下がり、担保の 80% の線が借入を下回ると清算される" align="center" >}}

上記の図の 3 つ目では、担保の価値（14,000 ドル）はまだ借入（12,000 USDC）を上回っています。それでも清算されるのは、担保が借入を割り込む前に回収を始めるためです。図の下の HF は、点線と借入の比を表す値で、後の節で説明します。

<br>

本記事では、[Aave v3](https://github.com/aave-dao/aave-v3-origin) の実装を例に、担保と清算の仕組みを説明します。コードへのリンクは、Aave v3 の実装のリポジトリ（aave-v3-origin）の v3.6.0（2026 年 1 月公開）を指します。2026 年 11 月時点の最新は v3.7.0 ですが、本記事で扱う処理は同じです。扱う疑問は次の通りです。

- 審査も裁判所も無いのに、なぜ貸し倒れを防げるのか。
- 清算はいつ・誰が・どれだけ行うのか。
- 価格が一気に動いた時、なぜ預け手に損失が残るのか。
- 金利は誰が決めているのか。

担保の価格をチェーンに届ける仕組みは [Oracle](../oracle/)、担保なしで 1 つの取引の中だけ借りる仕組みは [Flash Loan](../flash-loan/) で扱っています。

---

### 身元を確かめずに貸す方法

銀行の融資では、借り手の収入や信用を審査し、返済が滞れば契約と裁判所を通じて回収します。レンディングプロトコルは、借り手について何も確認していません。借り手はアドレス（口座番号にあたる識別子）でしか識別できず、返済しないまま別のアドレスに移っても、追いかける手段が無いからです。

そこで、借りる額より価値の大きい担保を先に預けてもらいます。この形を過剰担保（over-collateralization）と言います。返済されなくても担保を売れば回収できるため、借り手が誰であっても構いません。担保はコントラクトが保管し、借り手は返済するまで引き出せません。

<br>

Aave v3 では、[技術資料](https://github.com/aave/aave-v3-core/blob/master/techpaper/Aave_V3_Technical_Paper.pdf)の通り、担保にする資産ごとに 2 つの割合を設定しています。

- LTV（Loan to Value）: 担保の価値に対して、新しく借りられる上限の割合。
- 清算閾値（liquidation threshold）: 借入が担保の価値のこの割合を超えると、清算できるようになる線。

LTV は清算閾値より低く設定します。借りた直後に清算されないよう、2 つの割合の間に余裕を持たせるためです。

本記事では説明のために LTV を 75%、清算閾値を 80% とします。10 ETH（1 ETH = 2,000 ドルで 20,000 ドル）を預けると 15,000 USDC まで借りられ、借入が担保の価値の 80% を超えると清算の対象になります。冒頭の図の点線が、この 80% の線です。実際の値は資産ごとに異なり、Aave の運営方針を決める投票（ガバナンス）か、その権限を受けたリスク管理の役が変更します。

---

### health factor（HF）

Aave v3 は、借り手の状態を health factor（以下、HF）という 1 つの数値で表します。担保が複数ある場合は、資産ごとの価値に清算閾値を掛けて合計し、借入の合計で割ります。

```text
HF = Σ（担保 i の価値 × 担保 i の清算閾値） / 借入の合計の価値
```

価値は、オラクル（チェーンの外の価格をコントラクトへ届ける仕組み）の価格で、市場の基準の通貨（Aave の主な市場では米ドル）に換算した値です。HF が 1 以上なら安全で、1 を下回ると清算できます。Aave v3 の実装でも、[HF を計算する部分](https://github.com/aave-dao/aave-v3-origin/blob/v3.6.0/src/contracts/protocol/libraries/logic/GenericLogic.sol#L156-L164)と、清算の前に [HF が 1 未満かを確認する部分](https://github.com/aave-dao/aave-v3-origin/blob/v3.6.0/src/contracts/protocol/libraries/logic/ValidationLogic.sol#L336-L339)は、この式の通りに書かれています。

冒頭の Alice の例では、1 ETH = 2,000 ドルなら HF = 20,000 × 0.8 / 12,000 = 1.33 です。価格が 1,500 ドルまで下がると HF はちょうど 1 になり、それより下がると清算の対象になります。借入は USDC のまま変わらないので、HF を動かすのは主に担保の価格です。ただし、借りている間の利息も借入に加わります。担保に付く利率より借入の利率が高いと、価格が動かなくても HF は少しずつ下がります。

HF は「担保が借入の何倍あるか」ではありません。担保の価値が借入を上回っていても、清算閾値を掛けた値が借入を下回れば HF は 1 未満です。

---

### 清算

清算者（liquidator）は、HF が 1 を下回った借り手の借入の一部を代わりに返済し、返済額に清算ボーナス（liquidation bonus）を上乗せした価値の担保を受け取ります。以下は、ETH が 1,455 ドルに下がって HF が 0.97 になった Alice に対し、清算者が 1 回清算する例です。ボーナスは 5% とします。

{{< figure src="images/lending_liquidation_call.webp" alt="左が清算の前で、担保 10.00 ETH、借入 12,000 USDC、HF 0.97。中央の清算者から左の借入へ 6,000 USDC を返済する矢印と、左の担保から清算者へ 4.33 ETH（6,300 ドル分）が渡る矢印がある。右が清算の後で、担保 5.67 ETH、借入 6,000 USDC、HF 1.10。どちらも担保の 80% の点線が描かれている" caption="1 回の清算で動く借入と担保（1 ETH = 1,455 ドル、ボーナス 5%）" align="center" >}}

清算者は 6,000 USDC を返済し、6,300 ドル分（約 4.33 ETH）の ETH を受け取ります。Alice は返済額より 300 ドル分多く担保を失い、清算者はその差から取引の手数料（[gas 代](../gas-eip-1559/)）を引いた分を得ます。借入が半分になったので、清算の後の HF は 1.10 に戻ります。Aave v3 では、ボーナスの一部をプロトコルが手数料として取る設定もあります。

<br>

1 回の清算で返済できる量の上限を close factor と言います。Aave v3 では、[借入の 50% まで](https://github.com/aave-dao/aave-v3-origin/blob/v3.6.0/src/contracts/protocol/libraries/logic/LiquidationLogic.sol#L256-L274)が原則です。ただし、HF が 0.95 以下まで下がった時や、対象の資産の担保か借入のどちらかが 2,000 ドル未満の時は、一度に全額を清算できます。HF が深く下がった借入や少額の残りを一度に片付けるためです。

<br>

#### 誰が清算するのか

清算は運営者が行うと思うかもしれませんが、Aave v3 の清算の入口（`liquidationCall` という関数）には、呼び出せるアドレスの制限がありません。回収を運営者だけが担う設計では、その運営者が止まると誰も回収できません。Aave は、ボーナスという利益を示して、回収の作業を誰でも引き受けられる形にしています。

実際には、HF が 1 に近い借入を監視する bot が同じ機会を取り合います。取引の手数料を高く払うほど先にブロックに入れてもらえるので、bot は手数料を上乗せして先に清算しようとします。この競争は、取引の並び順から生まれる利益である [MEV](../mev/) の代表例の 1 つです。清算者は返済に使う USDC を持っていなくても構いません。flash loan で借りて返済し、受け取った ETH を売って同じ取引の中で返せるからです。

[Compound v2](https://docs.compound.xyz/v2/comptroller/#close-factor) も、close factor と liquidation incentive（清算ボーナスにあたる値）で清算者に報酬を与えます。[Compound III](https://docs.compound.xyz/liquidation/) のように、プロトコル自身が担保を引き取って借入を消し、引き取った担保を後で割引価格で売る設計もあります。

---

### 価格の急落と清算の実験

清算者に任せる設計は、価格が少しずつ動く間はうまく働きます。価格の下がり方で清算の結果がどう変わるか、[Python](https://www.python.org/) で確認しました。3 人の借り手 A・B・C が 10 ETH ずつ預け、8,000・12,000・15,000 USDC を借ります。1 ETH = 2,000 ドルの時点で、担保の 40%・60%・75% です。清算閾値 80%、ボーナス 5%、close factor 50%（2,000 ドル未満の規則は省きます）で、HF が 1 を下回った借り手は、清算者が価格の 1 段ごとに 1 回清算します。

価格の動きは 2 通りです。1 つは 2,000 から 1,200 まで 10 ずつ下がる場合（smooth）、もう 1 つは 1,950 から 1,300 へ一気に飛ぶ場合（gap）です。後者は、オラクルの更新が遅れた後に価格が一度に動く場面や、ネットワークの混雑で清算の取引がしばらく[ブロックに入らない](../mempool/)場面に当たります。実際のネットワークや資産は使いません。

```python
LT = 0.80  # liquidation threshold
BONUS = 1.05  # liquidator receives 105% of the repaid debt in collateral
CLOSE_FACTOR = 0.5  # share of the debt repayable per call while HF > 0.95


def health_factor(p, price):
    if p["debt"] == 0:
        return float("inf")
    return p["eth"] * price * LT / p["debt"]


def liquidate(p, price):
    """One liquidation call. Returns the debt left without collateral."""
    hf = health_factor(p, price)
    repay = p["debt"] * (CLOSE_FACTOR if hf > 0.95 else 1.0)
    seize = repay * BONUS / price  # ETH sent to the liquidator
    if seize > p["eth"]:  # not enough collateral: take all of it
        seize = p["eth"]
        repay = seize * price / BONUS
    p["eth"] -= seize
    p["debt"] -= repay
    if p["eth"] == 0 and p["debt"] > 0:
        bad, p["debt"] = p["debt"], 0.0
        return bad
    return 0.0


def run(prices):
    positions = {name: {"eth": 10.0, "debt": debt}
                 for name, debt in (("A", 8000.0), ("B", 12000.0), ("C", 15000.0))}
    bad_debt, calls, history = 0.0, 0, []
    for price in prices:
        for p in positions.values():
            if health_factor(p, price) < 1:
                bad_debt += liquidate(p, price)
                calls += 1
        history.append((price, [health_factor(p, price) for p in positions.values()]))
    return positions, bad_debt, calls, history


smooth = [2000 - 10 * i for i in range(81)]
gap = smooth[:6] + [p for p in smooth if p <= 1300]

for label, prices in (("smooth", smooth), ("gap", gap)):
    positions, bad_debt, calls, history = run(prices)
    print(f"[{label}] {prices[0]} -> {prices[-1]} USDC, {calls} liquidation calls")
    for name, p in positions.items():
        print(f"  {name}: eth={p['eth']:6.3f} debt={p['debt']:9.2f}")
    print(f"  bad debt: {bad_debt:.2f} USDC")
    for price, hfs in history:  # health factors after the liquidations
        print(f"  hf {label} {price} " + " ".join(f"{h:.3f}" for h in hfs))
```

上記は [lab/lending_sim.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/lending/lab/lending_sim.py) から先頭のコメントを除いたものです。以下は出力のうち、各段の HF（`hf` で始まる行）を除いた部分です。全体は [lab/lending_sim_output.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/lending/lab/lending_sim_output.txt) にあります。

```text
[smooth] 2000 -> 1200 USDC, 6 liquidation calls
  A: eth=10.000 debt=  8000.00
  B: eth= 3.330 debt=  3000.00
  C: eth= 1.123 debt=   937.50
  bad debt: 0.00 USDC
[gap] 2000 -> 1200 USDC, 2 liquidation calls
  A: eth=10.000 debt=  8000.00
  B: eth= 0.308 debt=     0.00
  C: eth= 0.000 debt=     0.00
  bad debt: 2619.05 USDC
```

{{< figure src="images/lending_liquidation.webp" alt="横軸が右に向かって下がる ETH の価格、縦軸が清算の後の HF の折れ線グラフ。価格が 10 ずつ下がる場合、B と C の HF は 1 に触れる度に清算されて 1.15 前後に跳ね戻るのこぎり型になる。価格が 1,950 から 1,300 に飛ぶ場合は、1,950 の黄土色の点から下の横向きの矢印で価格が飛んだことを示し、1,300 の赤い × が清算の直前の C の HF 0.69 を示す。担保が借入を下回り 2,619 USDC が不良債権になったと注記がある" caption="ETH の価格と清算の後の HF（シミュレーション）" align="center" >}}

10 ずつ下がる場合は、C の HF が 1 を割る度に借入の半分が返済され、HF は 1.15 前後に戻りました。B も 1,500 を下回った所で同じように清算されています。担保は減りましたが、借入は全て担保で返済されており、損失は残っていません。

一気に飛ぶ場合は、1,300 の時点で C の担保は 13,000 ドルしかなく、借入の 15,000 USDC を下回っています。HF が 0.95 を下回っているので借入の全額が清算の対象になりますが、担保が足りません。清算者は担保を全て受け取る代わりに、ボーナス分を引いた 12,380.95 USDC だけを返済し、残りの 2,619.05 USDC は誰も返済しない借入になりました。これが不良債権（bad debt）です。この不足を埋める仕組みが無ければ、損をするのは借り手ではなく、プールに資産を預けた預け手です。

gap では B も HF 0.87 まで飛びましたが（図には描いていません）、担保が借入を上回っていたので全額を清算でき、損失は出ていません。

<br>

Aave v3 では、v3.3 から、こうして残った不足を資産ごとに[記録](https://github.com/aave-dao/aave-v3-origin/blob/v3.6.0/src/contracts/protocol/libraries/logic/LiquidationLogic.sol#L514-L518)しています。記録した不足は、Umbrella の対象に設定した資産では、[Umbrella](https://github.com/aave-dao/aave-umbrella) という仕組みに預けられた資金を差し押さえて埋めます。Umbrella に資金を預けるのは、損失を肩代わりする代わりに報酬を受け取る人たちです。不足をまず引き受けた人の資金で埋め、預け手全員にかぶせないための設計です。

---

### 清算が間に合わなかった日

実験の gap に近いことが、2020 年 3 月 12〜13 日に [MakerDAO](https://github.com/makerdao/dss) で起きました。MakerDAO も過剰担保で貸す仕組みですが、呼び名と清算の形が Aave と異なります。

- 担保を預けて借りる単位を Vault、借りるトークンを DAI と呼びます。DAI は MakerDAO 自身が発行する、米ドル連動のトークンです。MakerDAO は預け手から集めた資産を貸すのではなく、借り手のために DAI を新しく発行して貸します。
- 清算では、担保をオークションに掛けます。keeper と呼ばれる bot が DAI で入札し、最後の入札から一定時間より良い入札が無いと（またはオークション全体の期限が来ると）その入札が落札し、落札額の DAI で借入を埋めます。

<br>

#### 事故の経過

[Maker Foundation の報告](https://web.archive.org/web/20201205172925/https://blog.makerdao.com/the-market-collapse-of-march-12-2020-how-it-impacted-makerdao/)によると、事故は次の順序で起きました。

1. 36 時間の間に ETH などの暗号資産が 50% 以上値下がりし、Ethereum の取引が急増して gas 代が跳ね上がった。
2. Vault の所有者は、混雑のために担保の追加や返済を間に合わせにくくなった。MakerDAO のオラクルは、価格を 1 時間遅らせて反映する仕組み（[OSM](https://github.com/sky-ecosystem/osm/blob/master/src/osm.sol)、Oracle Security Module）を通している。本来はその 1 時間が対応の猶予になるが、混雑の中では足りなかった。
3. 多数のオークションが一斉に始まった。清算に参加していた keeper は約 4 者で、1 者は技術的な問題で、1 者は DAI が尽きて、それぞれ数時間入札できなかった。残る 2 者の bot はほぼ 0 DAI の入札を出し、競う入札が無いまま時間が過ぎた一部のオークションでは、その入札で担保が落札された。
4. 担保を売っても借入を埋められず、約 540 万 DAI が不足した。

{{< figure src="images/lending_maker_auction.webp" alt="上の段は通常の日で、複数の keeper が競って入札し、落札額の棒が借入の棒と同じ長さまで伸びて借入を回収できる。下の段は 2020 年 3 月 12〜13 日で、落札額の棒はほぼ 0 で、残りは赤い点線の枠で埋まらない借入と示される" caption="MakerDAO の担保のオークション（模式図）" align="center" >}}

上記の図の上の段が通常の日のオークション、下の段が手順 3〜4 です。埋まらない借入が不良債権です。手順 4 の約 540 万 DAI は、この不足を全ての Vault で合計した額です。MakerDAO は、運営の投票に使うトークン MKR を新しく発行して DAI と交換する debt auction を行い、3 月 29 日までに 20,980 MKR を 530 万 DAI と交換して、不足の大半を埋めました。MKR が増えた分、既存の MKR の保有者の持ち分が薄まります。

<br>

清算は誰でも参加できますが、参加者がその時に取引をチェーンに入れられることを前提にしています。入札が届かなければ競争が起きず、担保は安値で売られ、不足は貸した側が負います。MakerDAO で負ったのは、DAI を発行して貸した仕組みを支える MKR の保有者でした。

---

### 金利と利用率

残る疑問は金利です。預け手の利息と借り手の金利は、運営者が日々決めているのではありません。プールの利用率（utilization）から式で計算します。利用率は、プールの資産のうち貸し出されている割合です。

以下は、[Aave v3 の金利モデル](https://github.com/aave-dao/aave-v3-origin/blob/v3.6.0/src/contracts/misc/DefaultReserveInterestRateStrategyV2.sol#L150-L168)と同じ形の式に、説明用の値を入れた図です。金利の上がり方が変わる利用率（最適利用率、optimal usage ratio）を 80% とし、そこまでに金利が 0% から 4% まで上がり、80% から 100% までにさらに 75% 上がるとします。プロトコルの取り分（reserve factor、利息のうちプロトコルが取る割合）は 15% です。実在する市場の値ではありません。

{{< figure src="images/lending_rate.webp" alt="横軸が利用率、縦軸が年利の折れ線グラフ。借り手の金利は利用率 80% までは 0% から 4% までゆっくり上がり、80% を超えると急に上がって 100% で 79% に達する。預け手の利率はその下を同じ形でたどる" caption="利用率と金利（説明用の値）" align="center" >}}

借り手の金利（borrow rate）は、利用率が最適利用率に達するまではゆっくり上がり、それを超えると急に上がります。この折れ曲がる点は、[Compound v2 の JumpRateModel](https://github.com/compound-finance/compound-protocol/blob/master/contracts/JumpRateModel.sol) では kink と呼ばれています。

急に上げる理由は、預け手の引き出しです。プールの資産が全て貸し出されると、預け手は自分の預けた資産を引き出せません。利用率が高い時に金利を大きく上げると、借り手は返済を急ぎ、新しい預け手も集まるので、プールに空きが戻ります。

預け手の利率（supply rate）は、借り手の金利に利用率を掛け、プロトコルの取り分を引いた値です。借り手が払った利息を預け手全員で分け合う形です。HF の節で触れた通り、借り手の側ではこの利息が借入に加わり、HF を少しずつ下げます。
