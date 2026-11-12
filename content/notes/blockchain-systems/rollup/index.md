---
title: "Rollup - 実行を外へ出し、結果をチェーンで確定する"
date: 2026-11-08
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "rollup", "layer-2"]
weight: 23
wrapTables: true
topics: ["Scaling"]
---

[Ethereum](https://ethereum.org/) では、ネットワークに参加する多数のノード（トランザクションを検証するコンピュータ）が、全てのトランザクションを同じ順に実行して結果を照合します。誰でも結果を確認できる代わりに、1 秒に処理できるトランザクションの数が限られ、混み合うと手数料が上がります。

[Rollup](https://ethereum.org/developers/docs/scaling/#rollups) は、この制約を緩める仕組みです。トランザクションの実行を Ethereum の外にある別のチェーンで行い、Ethereum には実行の結果と、結果を確認するのに要るデータだけを書き込みます。土台になる Ethereum を Layer 1（L1）、外のチェーンを Layer 2（L2）と呼びます。L2 では、シーケンサー（sequencer）と呼ばれるサーバーが利用者のトランザクションを受け取り、順に実行し、多数のトランザクションを 1 つの batch（まとめ）にして L1 に提出します。

例えば、Alice が L1 と L2 の間で資産を移す L1 上のプログラム（bridge）を通じて、1 ETH（Ethereum の通貨）を L2 の 1 つである [OP Mainnet](https://docs.optimism.io/) に預け、L2 上で Bob に 0.3 ETH を送ったとします。L2 の送金は数秒で残高に反映され、手数料も L1 より安くなります。

しかし、Bob が受け取った ETH を Ethereum に戻す時は、[OP Mainnet の出金手順](https://docs.optimism.io/op-stack/bridging/withdrawal-flow)に従い、L1 で出金を証明してから 7 日間待ちます。L2 では数秒で済んだ送金が、L1 に戻す時は 1 週間かかります。以下は、L2 で実行した多数のトランザクションのうち、L1 に何が届くかを示した図です。

{{< figure src="images/rollup_concept.webp" alt="上の L2 では、利用者の多数のトランザクションをシーケンサーが順に実行し、1 つの batch に詰める。batch から下の L1 へ矢印が 2 本出て、rollup のコントラクトには state root、L1 のブロックにはトランザクションデータが届く。左の黄土色の「異議 または validity proof」がコントラクトの更新を確認する" caption="L2 で生まれる多数のトランザクションのうち、L1 に届くもの" align="center" >}}

L1 に届くのは、L2 の残高などを短い値に要約した state root（状態の要約）と、batch に入れたトランザクションのデータです。state root は L1 上のプログラム（rollup のコントラクト）に記録され、トランザクションデータは L1 のブロックに置かれます。

L1 は state root を提出する者を無条件には信用せず、誰かが異議（challenge）を出せる期間を待つか、計算が正しいことの証明（validity proof）を検証して、state root が正しいかを確認します。OP Mainnet は前者の方式で、冒頭の 7 日間は、異議が出るのを待つために設けた期間です。

<br>

本記事では、rollup が L1 に何を残し、L1 がそれをどう確認するかを次の順に説明します。

- L2 はどの処理を L1 の外へ出し、L1 には何を残すのか。
- state root だけでは、なぜ利用者が L2 の状態を再計算できないのか。
- 異議と validity proof では、L1 は何を確認し、いつ出金を確定できるのか。
- トランザクションデータは L1 のどこに置かれ、いつまで残るのか。

L1 にトランザクションを入れるまでの流れは [Ethereum Transaction](../ethereum-transaction/) で説明しています。

---

### L1 と L2 の分担

Ethereum では、トランザクションをブロックに入れる時に[全ての検証ノードが同じ順序で実行し](../evm/)、状態の更新を確認します。ここでいう状態は、各アカウントの残高やコントラクトが保存している値の全体で、DB でいえばテーブルの全行にあたります。全てのノードが計算とデータを処理するため、トランザクションの処理量には限りがあります。

rollup は、利用者のトランザクションを L2 で実行してから、複数のトランザクションを batch にまとめます。L1 は L2 の各トランザクションを通常は一件ずつ再実行しません。L1 上の [Smart Contract](../smart-contract/)（rollup のコントラクト）が、batch を実行した後の state root と、異議または validity proof を受け取ります。トランザクションを L2 内でまとめることで、L1 に載せる処理を減らせます。

シーケンサーは 1 つの事業者が運用する構成が多くあります。ただし、順序を決める主体がいることと、その主体が状態を自由に改竄できることは同じではありません。検証者（公開されたデータから L2 の状態を自分で計算し直す人）は、計算した状態と L1 に記録された state root を照合できます。

{{< note-panels caption="L1 と L2 は、同じトランザクションを別々に処理するのではなく、検証の仕事を分けます。">}}
- title: L2
  body: 利用者のトランザクションを受け取り、順序を決めて実行し、batch と新しい状態を作ります。シーケンサーがこの役割を担う構成が多くあります。
- title: L1
  body: コントラクトが state root と、異議または validity proof を受け取り、rollup の規則に従って更新を受け入れます。トランザクションデータはブロックに置かれます。
- title: 利用者・検証者
  body: 公開されたデータから L2 の状態を復元・検証します。不正を発見した時に誰が異議を提出できるかは実装ごとに確認が必要です。
{{< /note-panels >}}

冒頭の Bob の例のように、L2 がトランザクションを受け付けた時点、batch を L1 に提出した時点、L1 の規則で出金を認める時点は一致しません。ウォレットに表示された「完了」だけから、L1 に戻す資産が既に引き出せるとは判断できません。

---

### state root とトランザクションデータ

state root は、アカウントの残高やコントラクトの保存状態を Merkle tree（マークル木）などで要約した値です。状態の一部と Merkle proof（その一部が木に含まれることを示す経路）があれば、その一部が特定の state root に含まれることを検証できます。[Merkle Tree](../merkle-tree/) で扱ったように、木の内容が変われば root も変わります。

冒頭の OP Mainnet の「出金の証明」は、L1 に提出された L2 の状態の要約に自分の出金の記録が含まれることを Merkle proof で L1 のコントラクトに示す手順です。

OP では、この要約を output root と呼び、state root などをまとめてハッシュにした値を使います（[出金の仕様](https://github.com/ethereum-optimism/specs/blob/main/specs/protocol/withdrawals.md)）。

ただし、state root から分かるのは、ある値が含まれるかどうかまでです。root は状態の要約であり、全てのトランザクションや状態そのものではありません。新しい root と古い root だけが L1 にあっても、検証者はどの送金をどの順序で実行してその root になったかを再計算できません。

以下は、シーケンサーが自分の残高に 50 を足した状態の root を提出した場合に、検証者が公開されたトランザクションから root を再計算して照合する例です。説明を短くするため、Merkle tree ではなく残高の表全体の [SHA-256](../../security/sha-256/) を root にしています。

```python
import hashlib
import json


def state_root(state):
    # 説明用に、残高の表全体の SHA-256 を root とする（実際の rollup は Merkle 木などを使う）
    data = json.dumps(state, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()[:16]


def apply(state, txs):
    state = dict(state)
    for sender, to, amount in txs:
        if state.get(sender, 0) < amount:
            continue  # 残高不足のトランザクションは無視する
        state[sender] -= amount
        state[to] = state.get(to, 0) + amount
    return state


before = {"alice": 100, "bob": 0, "sequencer": 0}
txs = [("alice", "bob", 30), ("bob", "alice", 5)]

honest = apply(before, txs)
forged = dict(honest, sequencer=honest["sequencer"] + 50)  # 自分に 50 を足した状態

print("提出された root:", state_root(forged))
print("再計算した root:", state_root(apply(before, txs)))
print("一致するか:", state_root(forged) == state_root(apply(before, txs)))
```

```text
提出された root: c3ce5aa78617464f
再計算した root: 8a5804b9396dccb7
一致するか: False
```

検証者が不正に気付けたのは、`before` と `txs` を入手できたからです。`txs` が無ければ、`c3ce5aa78617464f` が正しい root かどうかを確認する手段はありません。

<br>

この「検証者が必要なトランザクションデータを取得できる」性質は、data availability（データ可用性）と呼ばれます。rollup がトランザクションデータを L1 に公開する場合、シーケンサーがデータの配布を止めても、L1 のデータから別の参加者が状態を再計算できます。冒頭の図で、state root とトランザクションデータの 2 つが L1 に届くのはこのためです。state root は照合する値で、トランザクションデータは再計算の入力です。

一方で、シーケンサーや、データを預かる少数の組織（委員会）だけがトランザクションデータを持ち、state root だけを L1 に送る構成は validium などと呼ばれ、rollup とは区別されます。例えば、L2 を比較するサイトの [ETHBEAT（旧 L2BEAT）](https://ethbeat.org/layer2s/summary)は、state root を証明の仕組み付きで提出し、トランザクションデータも Ethereum に公開するものを Rollups とし、データを外に置く validium などとは別の一覧に載せています。

---

### Optimistic Rollup の challenge

Optimistic Rollup は、L1 に提出された state root を直ちに検証するのではなく、決められた期間（challenge 期間）に誰も異議を出さなければ受け入れる方式です。提出された batch は正しいと楽観的に（optimistic）扱い、不正を見つけた人が期間内に異議を出した時だけ L1 が判定します。

異議を出す人は、トランザクションの実行に関する fault proof（不正を示す証明）を使って争います。OP Mainnet の [fault proof の仕様](https://specs.optimism.io/fault-proof/index.html)では、この争いを L1 上の dispute game（異議を争う手続き）として定めています。

L1 のコントラクトは、batch の全ての計算を再実行して判定するわけではありません。提出者と異議を出した人に途中の状態を示させ、2 人の主張が最初に食い違う 1 ステップまで範囲を半分ずつ絞り、最後にその 1 ステップだけを L1 で実行します。ここでのステップは計算の 1 段で、トランザクション 1 件ではありません。実装では、L2 のトランザクションを実行するプログラムの命令 1 つの単位まで絞ります。以下は、16 ステップの計算でこの絞り込みを示した説明用の図です。

{{< figure src="images/rollup_bisection.webp" alt="上に、提出者の主張と異議を出した人の主張を 16 マスずつ並べ、10 ステップ目までは同じ青、提出者の 11 ステップ目以降だけが黄土色。下に、最初の範囲 0〜16 から、8 で一致・12 で不一致・10 で一致・11 で不一致と比べるごとに範囲が半分になる棒を並べ、最後は 11 ステップ目の 1 マスだけが赤く残る。L1 は 11 ステップ目だけを実行して判定する" caption="食い違う 1 ステップまで絞り、L1 はそこだけを実行する（説明用の 16 ステップの例）" align="center" >}}

上記の図では、8 ステップ目の後の状態は一致し、12 ステップ目の後は食い違うので、食い違いの始まりは 9〜12 ステップ目のどこかにあると分かります。これを繰り返すと 11 ステップ目だけが残り、L1 は 10 ステップ目の後の状態から 1 ステップだけ実行して、どちらの 11 ステップ目の状態が正しいかを決めます。前節の例でいえば、検証者が `txs` を再実行して得た root と、提出された root の食い違いを L1 が判定できる大きさまで小さくする処理です。

<br>

この方式では、通常の batch は証明を伴わずに先へ進められますが、L1 に戻す出金は challenge 期間を待ちます。2026 年 11 月時点の公式ドキュメントでは、OP Mainnet は 7 日、[Arbitrum One](https://docs.arbitrum.io/arbitrum-bridge/troubleshooting) は L1 の 45818 ブロック（1 ブロック 12 秒として約 6.4 日）で、どちらも出金には約 1 週間かかります。

なお、OP Mainnet でも、2024 年 6 月までは fault proof が無く、許可された 1 つのアカウントだけが L2 の状態の要約を提出していました。

[誰でも提出・異議申し立てできる fault proof へ移行](https://gov.optimism.io/t/final-protocol-upgrade-7-fault-proofs/8161)した時は、証明済みで 7 日の待ちが終わっていない出金が全て無効になり、利用者は出金を証明し直す必要がありました。

---

### ZK Rollup の validity proof

ZK Rollup は、batch の実行が規則に従ったことを示す validity proof（有効性証明）を作り、L1 の verifier contract（証明を検証するコントラクト）に提出します。L1 は証明を検証し、受け入れた batch の state root を更新します。証明には [Zero-Knowledge Proof](../zero-knowledge-proof/)（ゼロ知識証明）の技術を使います。

名称に ZK とありますが、rollup で使う証明が常にトランザクション内容を隠すためのものとは限りません。ここで重要なのは、L1 が短い証明を検証するだけで、batch の全ての計算が正しかったと確認できる点です。Optimistic Rollup が異議の出た時だけ 1 ステップを判定するのに対し、ZK Rollup では全ての batch が validity proof で確認できます（複数の batch をまとめて 1 つの証明にする実装もあります）。

validity proof が検証されてから L1 上の出金を受け付ける構成では、不正を待ち受ける challenge 期間は必要ありません。以下は、L1 に戻す出金の手順を 2 つの方式で並べた図です。

{{< figure src="images/rollup_withdraw.webp" alt="上段の Optimistic Rollup（OP Mainnet の例）は、L2 で出金を送る、batch を L1 に提出、L1 で出金を証明、黄土色の challenge 期間（7 日）、L1 で受け取る、の 5 つの箱。下段の ZK Rollup は、L2 で出金を送る、batch を L1 に提出、青の「validity proof を作り、L1 が検証」、L1 で受け取る、の 4 つの箱。箱の幅は時間の長さを表していない" caption="L1 に戻す出金の手順（Optimistic Rollup と ZK Rollup）" align="center" >}}

ZK Rollup でも、証明を作る時間、batch の提出間隔、L1 のブロックへの取り込み、L1 のブロックが巻き戻らなくなるまでの時間（[Finality](../finality/)）は残ります。「ZK Rollup なら即時に出金できる」とは限りません。

本記事でいう出金の確定は、batch が rollup の規則を満たして L1 のコントラクトに受け入れられた状態を指し、L1 自体の finality とは分けて扱っています。

安全性は、誤った計算に対して正しい証明を作れないという証明の仕組みの性質だけでなく、その実装に欠陥が無いこと、証明を作る主体が止まらないこと、トランザクションデータが公開されていることにも依存します。証明が正しい遷移を示しても、利用者が必要なデータを得られなければ、自分の資産を扱う手順を実行できません。

| 検証方法 | L1 が受け取る主な材料 | L1 が確認すること |
| --- | --- | --- |
| Optimistic Rollup | state root、トランザクションデータ、異議が出た時の fault proof | 異議が出た時だけ、食い違う 1 ステップ |
| ZK Rollup | state root、トランザクションデータ、validity proof | 全ての batch が、証明で正しいか |

この表は検証の違いを示したものです。手数料、シーケンサーが止まった時の挙動、[bridge の管理者権限](../cross-chain-bridge/)は、個別の L2 と bridge の仕様で確認する必要があります。

---

### トランザクションデータの置き場所と保持期間

どちらの方式でも、利用者や異議を出す人が状態を計算し直すには、公開されたトランザクションデータが要ります。

rollup は以前、L1 に送るトランザクションの data 欄（calldata）にトランザクションデータを入れていました。calldata はブロックの一部として、blob のような期限を決めずに保存され（2025 年 7 月から、The Merge より前の古い履歴はノードが削除できるようになりました）、トランザクションの実行中はコントラクトから読めます。その代わり、実行と同じ [gas](../gas-eip-1559/)（L1 の計算量の単位）で値段が付くため高くつきます。

<br>

2024 年 3 月の Ethereum の更新（Dencun）で、トランザクションに大きなデータを添付する blob という欄が入りました（[EIP-4844](https://eips.ethereum.org/EIPS/eip-4844)）。blob はコントラクトから中身を読めず、一定の期間が過ぎると消える代わりに、calldata より安く置けます。

L1 のトランザクションに残るのは blob を識別するハッシュ（versioned hash）だけで、コントラクトはそのハッシュを参照できます。中身はコンセンサス・レイヤーのノードが一定期間保存します。多くの rollup は、batch のトランザクションデータを blob に置いています。

blob を保存するのは、Ethereum のノードのうち合意を担う側（consensus layer、コンセンサス・レイヤー）で、仕様上の保持期間は少なくとも 4096 epoch です。[epoch](../proof-of-stake/) はコンセンサス・レイヤーで使う時間の単位で、1 epoch は 32 slot、1 slot は 2026 年 11 月時点で 12 秒なので、4096 × 32 × 12 秒で約 18 日です。

{{< figure src="images/rollup_retention.webp" alt="横棒グラフ。blob の保持は約 18 日以上（4096 epoch）、OP Mainnet の challenge 期間は 7 日、Arbitrum One は約 6.4 日で、2 本の黄土色の棒は青い棒の半分にも届かない" caption="blob の保持期間と、出金の challenge 期間" align="center" >}}

2025 年 12 月の Fulu 以降は、各ノードが blob を列に分けた一部だけを持ちますが、期間は同じ 4096 epoch です（[Fulu の仕様](https://github.com/ethereum/consensus-specs/blob/master/specs/fulu/p2p-interface.md)）。

上記の図の通り、OP Mainnet と Arbitrum One の challenge 期間は、blob の保持期間の内側に収まります。異議を出す人は、期間中なら blob からトランザクションデータを取り出して再計算できます。18 日より古い blob を後から使う用途では、アーカイブなどの別の保存手段が必要です。blob の大きさ、手数料の仕組み、batch に詰める件数と 1 件あたりのコストは [Blob](../blob/) で説明しています。

---

### rollup を比べる時に見る所

blob が下げるのは、L1 にデータを公開するコストです。シーケンサーによるトランザクションの検閲、rollup のコードの欠陥、利用者が出金できる時点は、blob を使っても変わりません。データの置き場所が calldata から blob に変わっても、Optimistic Rollup では challenge の条件、ZK Rollup では証明の条件を満たす必要があります。

L1 にデータがあっても、状態を復元するには、データを取得・実行するソフトウェアと、L1 に資産を戻す手順の実装も要ります。rollup を比較する時は「L2 の手数料が安いか」だけでなく、トランザクションデータをどこで得るか、状態の更新をどう検証するか、シーケンサーが止まった時と L1 に資産を戻す時にどの経路を使うかを分けて確認する必要があります。
