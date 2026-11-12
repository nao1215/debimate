---
title: "Bridge の事故 - 預け入れの確認が破られた 4 件"
date: 2026-11-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "bridge", "security"]
weight: 26
wrapTables: true
topics: ["Interoperability"]
---

[Cross-Chain Bridge](../cross-chain-bridge/)（以下、bridge）は、あるブロックチェーン（以下、チェーン）で資産が金庫に預けられたことを確認して、別のチェーンで同じ量のラップドトークン（wrapped token）を発行する仕組みです。ラップドトークンを焼却（消すこと）すると、元のチェーンの金庫から資産が払い出されます。預ける側を source chain、ラップドトークンを受け取る側を destination chain と呼びます。

bridge の安全性は、destination chain が「source chain で預け入れがあった」という主張をどう確認するかで決まります。2022 年には、この確認する部分が破られる事故が続きました。

{{< figure src="images/bridge-incidents_concept.webp" alt="左に source chain の金庫、右に destination chain のラップドトークンがあり、間の「確認する部分」に 4 つの穴が開いている。Ronin は署名者の鍵と残っていた署名の代行の許可、Wormhole は署名を確認するコード、Nomad は確認済みの初期値、BSC Token Hub は Merkle proof を確認するコード。どの穴を通っても、預け入れや焼却の無いメッセージが本物として扱われる" caption="4 件の事故が破った場所。どれも金庫ではなく、間の確認する部分" align="center" >}}

上記の図のように、4 件とも金庫やトークンのコントラクト（チェーン上で動くプログラム）自体は壊れていません。偽の預け入れが本物として扱われてラップドトークンが発行されたか、偽の焼却が本物として扱われて金庫から払い出されました。

<br>

本記事では、4 件を表の順に説明します。鍵を奪われた Ronin から始め、確認するコードの欠陥を突かれた 3 件へ進みます。外部の署名者、ライト・クライアント、異議の受付期間といった確かめ方の違いは [Cross-Chain Bridge](../cross-chain-bridge/#預け入れを確かめる方法) を前提にします。金額は当時の公式発表と報道によるもので、ドル換算は当時の価格です。

| 事故 | 時期 | 確かめ方 | 破られた所 |
| --- | --- | --- | --- |
| Ronin | 2022 年 3 月 | 外部の署名者 | 署名者の鍵 4 本と、残っていた署名の代行の許可（計 9 人中 5 人分） |
| Wormhole | 2022 年 2 月 | 外部の署名者 | 署名を確認するコード |
| Nomad | 2022 年 8 月 | 異議の受付期間 | 確認済みの扱いにする初期値 |
| BSC Token Hub | 2022 年 10 月 | ライト・クライアント | Merkle proof を確認するコード |

---

### Ronin

[Ronin](https://roninchain.com/) は、ゲームの [Axie Infinity](https://axieinfinity.com/) のために作られたチェーンです。Ethereum との bridge は、9 人の署名者（Ronin では validator と呼びます）のうち [5 人の署名](../multisig/)で、Ethereum 側の金庫からの払い出しを受け入れていました。鍵を 5 本集めれば、焼却の無い払い出しに署名できる構造です。

9 人のうち 4 人は、ゲームを運営する [Sky Mavis](https://www.skymavis.com/) の鍵でした。残りの 5 人のうちの 1 人が Axie DAO（DAO は Decentralized Autonomous Organization の略で、ここでは Axie Infinity の利用者が運営の判断に参加する組織）です。

{{< figure src="images/bridge-incidents_ronin.webp" alt="横の時間軸。2021 年 11 月に Axie DAO が Sky Mavis に署名の代行を許可する。12 月に代行は終わるが、許可は取り消されないまま残る。2022 年 3 月 23 日に攻撃者が Sky Mavis の鍵 4 本と代行の経路で 5 本目の署名を得て、偽の払い出しを通す。6 日後の 3 月 29 日に、利用者が払い出せないことで発覚する" caption="Ronin で 5 本目の署名が得られるまでの経緯" align="center" >}}

[Halborn の分析](https://www.halborn.com/blog/post/explained-the-ronin-hack-march-2022)によると、事故は次の順序で起きました。

1. 2021 年 11 月、利用者の急増による負荷への対策として、Axie DAO が Sky Mavis に署名の代行を許可した。12 月に代行は終わったが、許可は取り消されていなかった。
2. 攻撃者は、Sky Mavis の鍵 4 本を手に入れた。さらに残っていた代行の経路から Axie DAO の署名も得て、5 本目にした。
3. 2022 年 3 月 23 日、焼却の無い偽の払い出しで、Ethereum 側の金庫から 173,600 ETH と 2,550 万 USDC を引き出した。発覚したのは 6 日後で、利用者が 5,000 ETH を払い出せなかったことがきっかけだった。

[Cross-Chain Bridge の実験](../cross-chain-bridge/#署名鍵を奪われた-bridge-の実験)で、5 本目の鍵で偽の払い出しが通った場面にあたります。金庫が空になっても destination chain 側で、ラップドトークンの表示は変わらず、金庫の残高を見張る仕組みも無かったため、発覚まで 6 日かかりました。

---

### Wormhole

[Wormhole](https://wormhole.com/) は、[19 の guardian（署名者）のうち 13 の署名](https://wormhole.com/docs/protocol/infrastructure/guardians/)でメッセージを受け入れる bridge です。Ronin と同じ外部の署名者のタイプですが、鍵は奪われていません。2022 年 2 月 2 日、[Solana](https://solana.com/) 側のコントラクトで、署名を確認する処理そのものが回避されました。

この欠陥を読むには、Solana のプログラムの呼び出し方を知る必要があります。Solana のプログラム（コントラクト）は、呼び出し側から、読み書きするデータを入れたアカウントを引数の一覧として受け取ります。その中には、ランタイムが用意する特別なアカウント（sysvar）も含まれます。アカウントはそれぞれアドレス（識別子）を持ち、sysvar のアドレスは決まっています。

Solana では、署名の検証を組み込みのプログラム（secp256k1 program。secp256k1 は署名方式の名前）の命令としてトランザクションに入れ、同じトランザクションの中で先に実行させます。後から呼ばれるプログラムは、その命令がトランザクションに入っていたかを [Instructions sysvar](https://docs.anza.xyz/runtime/sysvars#instructions)（同じトランザクションの中で実行される命令の一覧を持つ sysvar）から読んで確認します。

{{< figure src="images/bridge-incidents_wormhole.webp" alt="左右 2 段の比較。上の正しい呼び出しでは、呼び出し側が本物の Instructions sysvar を渡し、命令の一覧に署名の検証の命令がある。下の攻撃では、呼び出し側が自分で作った偽のアカウントを渡し、命令の一覧に署名の検証の命令があるように書いておく。Wormhole のプログラムは渡されたアカウントのアドレスを確認しなかったため、どちらも検証済みと判断した" caption="渡されたアカウントが本物の sysvar かを確認しなかった" align="center" >}}

[Halborn の分析](https://www.halborn.com/blog/post/explained-the-wormhole-hack-february-2022)によると、流れは次の通りです。

1. Wormhole の `verify_signatures` は、渡された Instructions sysvar を読んで、guardian の署名を検証する secp256k1 program の命令が同じトランザクションに入っているかを確認していた。
2. 渡されたアカウントのアドレスが本物の sysvar のものかを確認していなかったため、攻撃者は検証の命令が入っているように見える偽のアカウントを渡した。
3. guardian の署名が揃ったと扱われたメッセージで、Ethereum に預け入れの無い 120,000 wETH（Wormhole の wrapped ETH）を Solana 上で発行した。

本物の sysvar かを確認する [`load_instruction_at_checked`](https://docs.rs/solana-program/latest/solana_program/sysvar/instructions/index.html) へ置き換える[変更の提案（pull request）](https://github.com/wormhole-foundation/wormhole/pull/751)は、事故の 3 週間前の 2022 年 1 月 13 日に公開リポジトリへ出ていました。しかし、main への取り込みは事故当日の 2 月 2 日で、Solana 上で動いていたプログラムは古いままでした。裏付けの無いまま発行された 120,000 wETH の分の ETH は、Wormhole の開発に関わる [Jump Crypto](https://jumpcrypto.com/) が[補填しました](https://www.theblock.co/post/132909/wormhole-replenishes-its-blockchain-bridge-after-325-million-exploit)。

---

### Nomad

[Nomad](https://www.nomad.xyz/) は、異議の受付期間を使う optimistic な bridge でした。source chain のメッセージは [Merkle Tree](../merkle-tree/) にまとめられ、その根のハッシュ（root）に [updater](https://docs.nomad.xyz/the-nomad-protocol/off-chain-agents/updater)（root に署名する役）が署名します。[relayer](https://docs.nomad.xyz/the-nomad-protocol/off-chain-agents/relayer)（届ける役）が署名済みの root を destination chain へ届け、一定期間に [watcher](https://docs.nomad.xyz/the-nomad-protocol/off-chain-agents/watchers)（監視する役）が止めなければ、その root は確認済みになります。root に含まれることを証明したメッセージだけが処理されます。

2022 年 8 月 1 日の事故は、[Halborn の分析](https://www.halborn.com/blog/post/the-nomad-bridge-hack-a-deeper-dive)によると次の順序で起きました。

1. [コントラクトの更新時の初期化](../upgradeable-proxy/#初期化関数と初期化を忘れた事故)で、0x00 を確認済みの root として登録してしまった。
2. [Solidity の mapping](https://docs.soliditylang.org/en/latest/types.html#mapping-types)（Ethereum のコントラクトの言語での連想配列）は、登録されていないキーに 0 を返す。証明されていないメッセージの root を引くと 0x00 になり、それが確認済みとして扱われた。
3. どんなメッセージも証明済みとして処理されるようになり、最初の攻撃で使ったトランザクションをコピーして宛先だけ変えたトランザクションが数百のアドレスから送られた。損失は約 1.9 億ドル。

この初期値の誤りは、辞書 2 つで再現できます（[lab/nomad_sim.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/bridge-incidents/lab/nomad_sim.py)）。

```python
def message(kind, nonce, to, amount):
    return f"{kind}|{nonce}|{to}|{amount}".encode()


ZERO = "00" * 32
proven = {ZERO: True}  # the mistake: the initial root 0x00 is marked as proved
root_of = {}  # message -> root it belongs to; unknown messages give ZERO


def accept(msg):
    return proven.get(root_of.get(msg, ZERO), False)


forged = message("deposit", 99, "mallory", 1000)
print(f"unproved message accepted: {accept(forged)}")
proven = {}  # without the mistake
print(f"unproved message accepted after fix: {accept(forged)}")
```

```text
unproved message accepted: True
unproved message accepted after fix: False
```

異議の受付期間は、届いた root を watcher が期間内に止める仕組みです。証明されていないメッセージが期間を経ずに受け入れられる状態では、watcher が止める機会もありませんでした。

---

### BSC Token Hub

[BNB Chain](https://www.bnbchain.org/)（通貨は BNB）は、2022 年当時、ステーキングや投票を扱う BNB Beacon Chain と、コントラクトを動かす [BNB Smart Chain](https://docs.bnbchain.org/)（BSC）の 2 本のチェーンで構成されていました。Beacon Chain を source chain、BSC を destination chain とする bridge が BSC Token Hub（[TokenHub.sol](https://github.com/bnb-chain/bsc-genesis-contract/blob/master/contracts/TokenHub.sol)）です。

BSC Token Hub はライト・クライアントのタイプで、Beacon Chain の状態を Merkle proof（Merkle Tree の葉から根までの経路のハッシュ）で確認していました。木の形式は [IAVL](https://github.com/cosmos/iavl) という、Cosmos 系のチェーンが使う Merkle Tree の一種です。

[Nansen の分析](https://www.nansen.ai/post/bnb-chains-cross-chain-bridge-exploit-explained)によると、攻撃者は前日に BSC Token Hub の relayer として登録し、2022 年 10 月 6 日に存在しない預け入れの proof を提出して、1,000,000 BNB の発行を 2 回通しました。BNB Chain は validator（BNB Smart Chain でブロックを承認する参加者）と調整してチェーンを止めたため、外のチェーンへ持ち出されたのは一部に留まりました。

{{< figure src="images/bridge-incidents_bsc.webp" alt="左の BNB Beacon Chain（source chain）には預け入れが無い。中央の攻撃者は relayer に登録し、偽の Merkle proof を 2 回提出する。右の BNB Smart Chain（destination chain）の BSC Token Hub は proof を確認して発行し、1,000,000 BNB の発行が 2 回通った" caption="預け入れの無い proof で、BSC Token Hub が発行した" align="center" >}}

[Verichains の分析](https://blog.verichains.io/p/binance-bridge-exploitation-preliminary)によると、原因は IAVL の範囲の proof（1 つの proof で複数の葉が木に含まれることを示す形式）を検証するコード（[iavl の修正](https://github.com/cosmos/iavl/pull/582)）にありました。検証コードは、次の 2 つが両方成り立てば、proof に並んだ葉が木の中にあると判定していました。

1. 1 枚目の葉から経路をたどって計算した root が、チェーンに記録された root と一致する。
2. 2 枚目以降の葉から計算したハッシュが、経路の要素が持つ右の子の値と一致する。

経路の要素は、通常は左右の子のどちらか一方のハッシュだけを持ちます。左右の子を両方持つ要素を渡された時、検証コードは 1. の計算で右の子の値を使っていませんでした。

{{< figure src="images/bridge-incidents_iavl.webp" alt="Merkle Tree の経路の図。正しい証明では、経路の要素は兄弟のハッシュを 1 つだけ持ち、本物の葉から計算した値が root と一致する。攻撃の証明では、経路の要素に左の子と右の子を両方入れ、右の子に偽の葉のハッシュを入れる。確認 1 では右の子が使われないので root は一致し、確認 2 では偽の葉のハッシュと右の子が一致するので、偽の葉も木の中にあると判定される" caption="root の計算に使われない右の子に、偽の葉のハッシュを入れた" align="center" >}}

上記の図のように、攻撃者は本物の葉と経路で 1. を通し、右の子に偽の葉のハッシュを入れて 2. を通しました。右の子は 1. の計算に使われないため、何を入れても root は変わりません。ライト・クライアントのタイプは source chain の合意を信頼する方式ですが、その前提は、証明を確認するコードが正しい場合に限ります。証明の形式を曖昧にしない木の設計は [Merkle Tree Design](../merkle-tree-design/) で扱っています。
