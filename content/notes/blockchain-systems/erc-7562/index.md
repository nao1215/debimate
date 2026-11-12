---
title: "ERC-7562 - アカウント抽象化の検証に Bundler が課す規則"
date: 2026-11-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain", "ethereum", "erc-7562", "erc-4337", "account-abstraction"]
weight: 20
wrapTables: true
topics: ["Transaction / Wallet"]
---

[ERC-7562](https://eips.ethereum.org/EIPS/eip-7562) は、Ethereum のアカウント抽象化（account abstraction）の仕組みである [ERC-4337](../erc-4337/) で、Bundler がアカウントの検証のコードに課す規則です。検証のコードが使って良い命令と、読み書きして良い storage（コントラクトが持つ永続的な記憶領域で、32 バイトの番号＝slot ごとに値を置く）を決めています。

本記事で必要な ERC-4337 の前提は、次の流れだけです。ERC-4337 では、利用者のアカウントをコントラクト（スマートアカウント）で作ります。利用者は取引の代わりに UserOperation という依頼を作り、Bundler に送ります。Bundler は集めた UserOperation を 1 件の取引にまとめ、自分の EOA（秘密鍵で署名して取引を送る通常のアカウント）から EntryPoint というコントラクトへ送ります。

EntryPoint は UserOperation ごとに、アカウントの `validateUserOp`（検証）を呼び、通れば中身を実行します。検証の中身はアカウントのコードが決めるので、署名の確かめ方などを自由に書けます。

{{< figure src="images/erc-7562_roles.webp" alt="左から利用者、Bundler、EntryPoint、スマートアカウントの箱が矢印でつながる。利用者から Bundler へ UserOperation、Bundler から EntryPoint へ handleOps（ガス代は Bundler）、EntryPoint からアカウントへ検証から実行。EntryPoint から Bundler へ破線の矢印が戻り、アカウントか Paymaster の deposit から払い戻す（検証を通った分だけ）とある。下に、チェーンの外は利用者と Bundler、チェーンの上は EntryPoint とアカウントとある" caption="ERC-4337 の登場人物と、手数料の流れ" align="center" >}}

上記の図で、利用者と Bundler はチェーンの外、EntryPoint とアカウントはチェーンの上にいます。`handleOps` の取引のガス代はネットワークに払うもので、送った Bundler の EOA から出ます。

ここで、[取引の手数料](../gas-eip-1559/)を先に払うのは、送り主ではなく Bundler です。Ethereum では、途中で失敗して取り消された取引でも、使った分の手数料は取引を送った側が払います。

EntryPoint は、検証を通った UserOperation についてだけ、アカウント（または、手数料を肩代わりするコントラクトの Paymaster）が EntryPoint に預けた ETH（deposit）から手数料を Bundler へ払い戻します。参照実装の EntryPoint では、チェーン上で 1 件でも検証が失敗するとバンドル全体が取り消され、その手数料は全て Bundler の損になります。そのため Bundler は、送る前に手元で検証をシミュレーションします。

{{< figure src="images/erc-7562_flow.webp" alt="左の灰色の箱は送り主の UserOperation。中央の破線の枠は Bundler の手元のシミュレーションで、青い箱が 3 つ並ぶ。1 つ目は受け取った時に 1 件だけ検証して規則に合うかを見る。2 つ目はバンドルの前に 1 件ずつ検証して状態の変化を見る。3 つ目は送る直前にバンドル全体を検証して組み合わせを見る。枠の下に、ERC-7562 の規則でここの結果をチェーンでも保つとある。右の黄土色の箱はチェーンの EntryPoint で、検証から実行へ進む。下に、ここで検証が失敗すると手数料は Bundler が払うとある" caption="Bundler が 1 件の UserOperation を送るまでの 3 回の検証" align="center" >}}

上記の図の 3 回の検証は、どれもチェーンに取引を出さずに、ノードに実行だけをさせる呼び出し（`eth_call` など）で行います。1 回目は受け取った時に 1 件だけを検証し、規則に合うかを確認します。

2 回目は、バンドル（bundle、複数の UserOperation をまとめた 1 件の `handleOps` の呼び出し）に入れる前に 1 件ずつ検証し直し、受け取った後の他の取引で結果が変わっていないかを見ます。3 回目は送る直前にバンドル全体を検証し、同じバンドルの UserOperation どうしが邪魔し合わないかを見ます（ERC-4337 の「Bundler behavior upon receiving a UserOperation」）。

シミュレーションで通っても、右端のチェーン上で検証が失敗すれば、手数料を払うのは Bundler です。ERC-7562 の規則で検証から読めるのは、原則として、1 回書き換えても影響がそのアカウントの UserOperation だけに留まる値です。多数の UserOperation をまとめて無効にするには件数分の書き換えが要るので、シミュレーションの結果をチェーンの上で覆す攻撃が割に合わなくなります。

{{< figure src="images/erc-7562_one_write.webp" alt="左右の比較。左は全員が同じ slot を読む場合で、Gate.isOpen の箱を 1 回書き換える（赤い ×）と、そこから線が伸びた 10 個の UserOperation が全て赤（無効）になる。右は各自の slot だけを読む場合で、10 個の slot がそれぞれ 1 つの UserOperation とつながり、1 つの slot を 1 回書き換えると 1 件だけが赤になる" caption="1 回の書き換えで無効にできる UserOperation の数" align="center" >}}

上記の図の左は、多数のアカウントが 1 つのコントラクトの開閉スイッチ（後の実験の `Gate.isOpen`）を読む場合です。右のように、各自の slot だけを読ませれば、全員を止めるには件数分の書き換えが要ります。

<br>

本記事では、ローカルの実験で確認しながら、次の疑問を順に扱います。

- 検証に制限が無いと、誰がどう損をするのか。
- 検証では、どの命令と storage が使えるのか。
- stake（担保）と reputation（評判）は、何を防ぐのか。
- Bundler は、規則に従っているかどうかをどう確認するのか。

UserOperation の中身、手数料を肩代わりする Paymaster、アカウントを作る Factory を含む全体は [ERC-4337](../erc-4337/) のノートで説明しています。仕様の引用は、2026 年 10 月 23 日時点の内容（[ethereum/ERCs のコミット cab9f75](https://github.com/ethereum/ERCs/blob/cab9f75eaf10ffb30d4aa4b4f712e8324a24f4db/ERCS/erc-7562.md)、状態は Review）に基づきます。

---

### 検証の規則が必要な理由

通常の取引では、ノードは受け取った取引を [mempool](../mempool/)（ブロックに入る前の取引を溜めておく場所）に入れます。EOA の取引が有効かどうかは、署名・nonce（取引の通し番号）・残高の 3 つで判定できます。取引を無効にする方向にこの 3 つを変えられるのは、同じ EOA の別の取引だけです。無効になった取引でノードが失うのは検証の計算だけで、お金は失いません。

Bundler も、受け取った UserOperation を自分の mempool に溜めます。しかし、Bundler は無効になった UserOperation の検証に払われない計算を使い、チェーン上で失敗すれば自分の ETH も失います。

さらに、UserOperation の検証はアカウントのコードが決めます。コードがブロックの時刻や他のコントラクトの storage を読むと、無関係な取引や時間の経過で結果が変わります。以下は、検証が `block.timestamp`（ブロックの時刻）を読み、期限を過ぎていたら失敗するアカウントで起きる流れです。t+46 は後の実験の値で、期限を過ぎたブロックを表します。

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#eaf1f5","primaryTextColor":"#28343b","primaryBorderColor":"#9cabb5","lineColor":"#596b76","textColor":"#28343b","actorBkg":"#eaf1f5","actorBorder":"#9cabb5","actorTextColor":"#28343b","actorLineColor":"#9cabb5","signalColor":"#596b76","signalTextColor":"#28343b","noteBkgColor":"#f8eed8","noteBorderColor":"#d4a24c","noteTextColor":"#403c32","activationBkgColor":"#edf3ef","activationBorderColor":"#9aafa1"}}}%%
sequenceDiagram
    participant U as 送り主
    participant B as Bundler
    participant E as EntryPoint（ブロックの中）
    U->>B: UserOperation
    B->>B: 時刻 t でシミュレーション（成功）
    B->>E: handleOps（Bundler の EOA が送る）
    E->>E: 時刻 t+46 で検証（AA23 で revert）
    Note over B,E: 手数料は Bundler の EOA が払う<br/>送り主の負担は 0
```

上記の図の `AA23` は、アカウントの検証が revert（処理を取り消して失敗）した時に EntryPoint が返すエラーです。送り主の deposit から手数料を受け取る処理は、検証を通った後にしか動きません。検証は、Web のアプリで言えば認可に当たり、通るまではアカウントの資金を使ってよいと言えないからです。検証で revert した取引は、Bundler が手数料を払っただけで終わります。

<br>

ERC-7562 の Rationale は、これを大量無効化攻撃（mass invalidation attack）と呼び、方法を 3 つ挙げています。

1. 受け取った時の検証は通り、バンドルを作る時の検証で失敗する UserOperation を送る（冒頭の図の 2 回目で見つかる）
2. 1 件ずつなら有効で、同じバンドルに入ると無効になる UserOperation を送る（3 回目で見つかる）
3. 有効な UserOperation の前に、それを無効にする状態の変更を割り込ませる（3 回の検証の後に起きるので、検証では見つからない）

{{< figure src="images/erc-7562_attacks.webp" alt="上に、受け取った時、バンドルの前、送る直前の 3 回の検証と、ブロックの中の箱が左から並ぶ。下の 3 行で、方法 1（後で失敗する）はバンドルの前の検証で丸が付き見つかる。方法 2（一緒だと失敗する）は送る直前の検証で見つかる。方法 3（前に割り込む）はブロックの中まで線が伸びて赤い × があり、検証の後なので見つからないとある" caption="大量無効化の 3 つの方法が見つかる場所" align="center" >}}

3 つ目の割り込みは、ブロックの中の取引の順序はブロックを作る側が手数料の単価などで決める、という性質を使います。Bundler の取引を見てから、より高い単価の取引を[前に入れる](../mev/)わけです。

どれも、攻撃者の少ないコストで、Bundler に多数の UserOperation の手数料や検証の手間を負わせる経路です。1 つ目と 2 つ目は検証で見つけて捨てられますが、何度も繰り返されると手間だけが残ります。

ERC-7562 は検証のコードを砂場（sandbox）に閉じ込め、他の UserOperation、外部の storage の変更、ブロックの時刻のような環境から切り離します。この制限があれば、3 つ目の割り込みでも1 回の変更で無効にできるのは 1 つのアカウントの分だけになります。

ERC-7562 はプロトコルの規則だと思うかもしれません。しかし、仕様の Abstract が述べる通り、規則を守らせるのはブロックビルダー（取引を選んでブロックを組み立てるノード）と Bundler で、確認する場所はオフチェーンです。

EntryPoint のコントラクトは、時刻を読む検証もそのまま実行します。Mempool のノートの言葉では、consensus rule（全ノードが守るブロックの規則）ではなく policy（各ノードが受け付けを決める方針）に入る規則です。

---

### 検証が読める値

ERC-7562 の規則は、命令の規則と storage の規則に大きく分かれます。どちらも、シミュレーションした時とブロックに入った時で変わり得る値を検証から締め出す規則です。

{{< figure src="images/erc-7562_concept.webp" alt="左に黄土色の箱が 3 つ（TIMESTAMP、NUMBER、関連しない storage）並び、上にブロックまでに変わる値とある。3 本の線は中央の青い枠（検証、ERC-7562 の規則（原則））の手前で赤い × に止められる。青い枠の中には自分の storage と自分に関連する他の slot の白い箱があり、下に書き換えの影響はそのアカウントだけとある。青い枠から右の破線の灰色の箱（実行、任意のコード）に矢印が伸びる" caption="検証が読める値と、柵の外に置かれる値" align="center" >}}

上記の図の左の値は、時刻の経過や他人の取引で、ブロックに入るまでに変わり得るので、検証からは読めません。中央の 2 つは、書き換えて影響を受けるのがそのアカウントの UserOperation だけの値です。「自分に関連する他の slot」の決まり方は、次の次の節で説明します。制限が掛かるのは検証だけで、右の実行では任意のコードが動きます。

仕様は個々の規則に、命令なら OP-011、storage なら STO-021 のような番号を振っています。後の実験の出力も、この番号で違反を示します。

---

### 禁止される命令

ERC-7562 は、storage とコード以外の情報を読む命令を「環境」と呼び、検証での使用を禁じています（OP-011）。ブロックの時刻（`TIMESTAMP`）や番号（`NUMBER`）、手数料の単価（`GASPRICE`・`BASEFEE`）など、値がブロックや取引ごとに変わる命令です。

残高を読む `BALANCE` と `SELFBALANCE` も、原則として使えません（後述の stake をした主体だけが使えます。OP-080）。他人の送金で残高が変わるからです。コントラクトを作る `CREATE` も、アカウントを作る時の例外（OP-032）を除いて禁止です。

<br>

<details>
<summary>禁止・制限される命令の一覧</summary>

| 区分 | 禁止される命令 |
| --- | --- |
| ブロックの情報 | `TIMESTAMP`・`NUMBER`・`BLOCKHASH`・`PREVRANDAO`・`COINBASE`・`GASLIMIT`・`BASEFEE`・`BLOBBASEFEE` |
| 取引の情報 | `GASPRICE`・`ORIGIN`・`BLOBHASH` |
| 作成と削除 | `CREATE`（アカウントを作る時の例外あり）・`SELFDESTRUCT` |
| 未有効化の命令 | `SETCODEFROM`・`SLOTNUM`（有効化したネットワークのみ） |
| その他 | `INVALID`・割り当てのない命令（OP-013） |

上記に加えて、次の制限があります。

- `GAS` は、直後に `CALL` などの呼び出しが続く場合だけ使える（OP-012）。残りのガスをそのまま呼び出し先に渡す定型で、値をほかの命令が読めないから
- `BALANCE` と `SELFBALANCE` は、stake をした主体だけが使える（OP-080）
- 値を付けた `CALL` は、EntryPoint への支払いを除いて禁止（OP-061）
- コードの無いアドレスへの `CALL` や `EXTCODESIZE` などは禁止（OP-041）。例外は、デプロイ中の Factory が送り主のアドレスに触れる場合だけ（OP-042）
- precompile（チェーンに組み込まれた計算用のコントラクト）は、状態を読まない `0x1`〜`0x11` と `P256VERIFY` だけ使える（OP-062）

</details>

<br>

時刻で期限を付けたい場合は、`validationData` という戻り値の `validUntil` と `validAfter` を用います。EntryPoint がブロックの時刻と比べ、範囲外なら `AA22 expired or not due` で失敗させます。

Bundler はシミュレーションの結果から期限を読めるので、期限の近い UserOperation をバンドルに入れずに済みます（[ERC-4337](https://eips.ethereum.org/EIPS/eip-4337) は、すぐに期限が切れる UserOperation を落とすよう求めています）。コードの中で `TIMESTAMP` を読む場合との違いは、期限が Bundler に見えるかどうかです。

---

### 触って良い storage

命令の制限だけでは、他のコントラクトの storage を読む検証を止められません。冒頭の 1 回の書き換えの図の左のように、多数のアカウントが 1 つのコントラクトの開閉スイッチを読むと、スイッチを 1 回切り替えるだけで、全ての UserOperation が無効になります。そのため、ERC-7562 は検証で触れる storage を原則としてそのアカウントに紐づくものに限ります。

アカウントに関連する storage（associated storage）は、どのコントラクトにある [slot](../evm/#データ領域と寿命) でも、次のどちらかを満たすものです。A はアカウントのアドレスです。

- slot の番号が A に等しい
- slot の番号が `keccak(A || x) + n`（x は 32 バイトの値、n は 0〜128）

`keccak` は Ethereum が使うハッシュ関数、`||` はバイト列の連結です。

例えば、[Solidity](https://soliditylang.org/) の `mapping(address => uint256) balanceOf` は、`balanceOf[A]` を `keccak(A || p)` の slot に置きます（p は mapping 自体の slot 番号）。そのため、[ERC-20](../erc-20/) のトークンにある自分の残高は、アカウントに関連する storage です。n の幅があるので、mapping の値が複数の slot を占める構造体でも含まれます。

{{< figure src="images/erc-7562_associated.webp" alt="トークンのコントラクトの storage の表。mapping balanceOf の slot 番号を p とする。slot の番号 keccak(A || p) の値は balanceOf[A] で、A に関連する slot（青）。keccak(B || p) の値は balanceOf[B]、p 以外の固定の番号の値は totalSupply などで、どちらも A には関連しない（灰色）。下に、A の検証は他人のコントラクトの中でも A に関連する slot なら読めるとある" caption="トークンの storage の中の、A に関連する slot" align="center" >}}

アカウントの検証が触れるのは、自分の storage と、他のコントラクトにある関連する slot です（STO-010・STO-021）。次の節の stake をした主体には、もう少し広い範囲が認められます。`TLOAD`・`TSTORE` で扱う一時的な storage（[EIP-1153](https://eips.ethereum.org/EIPS/eip-1153)）も、同じ規則で判定します（OP-070）。

<br>

<details>
<summary>誰がどの storage を触れるか（仕様の Storage Rules の整理）</summary>

| 触れる storage | 許される条件 |
| --- | --- |
| アカウント自身の storage | 常に（STO-010） |
| 他のコントラクトにある、アカウントに関連する slot | アカウントが作成済み、または Factory が stake している（STO-021・STO-022） |
| stake した Paymaster・Factory 自身の storage | 常に（STO-031） |
| 他のコントラクトにある、stake した Paymaster・Factory に関連する slot | 読み書きできる（STO-032） |
| 主体でないコントラクトの任意の slot | stake した Paymaster・Factory だけ、読むことができる（STO-033） |

</details>

<br>

この制限で、1 回の storage の変更で無効にできる UserOperation は、原則として 1 つのアカウントの分に限られます。

仕様の試算では、無効化に必要な最小の変更は storage の書き換え 1 回の 5,000 gas です。取引 1 件ごとの基本料（21,000 gas）は別で、1 件の取引で多数の slot を書き換えると、1 UserOperation あたりの費用はこの値に近づきます。

ノードが 1 ブロックで 2,000 件の不正な UserOperation を処理できると仮定すると、その全てを無効にし続けるには 1 ブロックあたり 10,000,000 gas が要ります。この量は、2026 年 11 月時点のメインネットのブロックのガスの上限（6,000 万）の 6 分の 1 に当たり、これを毎ブロック払い続けることになります。

---

### stake と reputation

UserOperation は、アカウントのほかに、手数料を肩代わりする Paymaster や、まだ無いアカウントを作る Factory を指定できます。Paymaster や Factory は多くのアカウントから共通に使われ、利用者ごとの残高の管理のように、自分の storage を読みたい場面があります。

ERC-7562 は、stake した主体（entity）にだけ広い storage を認め、その代わりに失敗の多い主体を止めます。主体は、UserOperation に関わる Factory・Paymaster・Aggregator（複数の署名をまとめて検証するコントラクト）と、stake したアカウントです。

{{< figure src="images/erc-7562_entities.webp" alt="左の UserOperation に関わる主体の箱から、送り主のアカウント（検証する本人）、Factory（アカウントを作る）、Paymaster（手数料を肩代わり）、Aggregator（署名をまとめて検証）の 4 つの箱へ矢印が伸びる。右の黄土色の箱は stake した場合で、EntryPoint に ETH を預け 1 日以上ロック、広い storage を読めるとある。箱の下に、失敗の多さ（reputation）は stake の有無に関わらず数えるとある" caption="UserOperation に関わる主体と、stake した場合" align="center" >}}

stake は、EntryPoint の `addStake` で ETH を預け、引き出しに待ち時間を設ける仕組みです。標準の mempool は、`MIN_STAKE_VALUE`（チェーンごとに決める値で、仕様の目安は 1,000 ドル相当）以上の ETH を 1 日（`MIN_UNSTAKE_DELAY` = 86,400 秒）以上の待ち時間で預けた主体を staked と見なします。

stake は没収されません。検知はオフチェーンなので没収はせず、資金を 1 日以上ロックさせることで、主体を作り直して攻撃を続けるコストを上げています。

<br>

reputation は、Bundler が主体ごとに数える成功率です。`opsSeen` は受け取った有効な UserOperation のうちその主体を参照した数、`opsIncluded` はそのうちチェーンに載った数です。

どちらも 1 時間ごとに 23/24 倍され、仕様は 4 日でおよそ 1% に減るとしています（23/24 を 96 回掛けると約 1.7%）。`max_seen = opsSeen // 10` として、状態は次の通りです。

| 状態 | 条件 | 扱い |
| --- | --- | --- |
| BANNED | `max_seen > opsIncluded + 50` | mempool に入れず、参照する UserOperation も外す |
| THROTTLED | `max_seen > opsIncluded + 10` | mempool に 4 件、1 つのバンドルに 4 件、mempool に 10 ブロックまで |
| OK | それ以外 | stake した主体は件数の制限なし |

例えば、`opsSeen` が 1,000 なら `max_seen` は 100 で、載った数が 89 件以下で THROTTLED、49 件以下で BANNED です。受け付けた UserOperation の 1 割ほどがチェーンに載っていれば、OK のままです。

冒頭の図の 2 回目の検証を通った後で、バンドルを作る段階（3 回目の検証）で失敗させた主体は、数に関係なく BANNED になります。1 件ずつの検証を通しながらバンドルの中だけで失敗するのは偶然では起きにくいので、即座に止めます（検知の方法は「規則を確認する仕組み」の節）。

stake しない主体には、件数の上限があります。ERC-4337 は mempool に溜める UserOperation を送り主ごとに 1 件を基本とし（stake した送り主は例外）、複数を受け付ける Bundler に判断を任せています。

ERC-7562 の標準の mempool は、これを stake しない送り主で同時に 4 件まで広げています。stake しない Paymaster を参照する UserOperation は、新しい Paymaster なら 10 件までです。

---

### 同じ送り主の扱い

前節の件数の上限は mempool に溜める数でした。それとは別に、[ERC-4337](https://eips.ethereum.org/EIPS/eip-4337) は、1 つのバンドルに入れる UserOperation を送り主ごとに 1 件までとしています（stake した送り主は例外）。

ERC-7562 の Rationale も、同じアカウントの UserOperation を複数入れるなら、先に一緒に検証するよう求めています。1 件ずつなら有効でも、一緒になると無効になる組み合わせがあり、大量無効化の 2 つ目の方法になるからです。

EntryPoint は検証の時に、手数料の上限額（prefund）を前払いで確保します。deposit で足りない分は、アカウントが検証の中で自分の ETH から EntryPoint へ送ります。この ETH が 1 件分しか無いと、2 件目の検証で前払いが足りなくなります。

nonce の key（並列に使える nonce の系列）を分ければ、同じ送り主でも順序に縛られずに 2 件を出せるので、残高だけが衝突します。この例は後の実験で確認します。

同じ理由で、バンドルを作る Bundler は、別の UserOperation の送り主のアドレスに触れる UserOperation と、同じバンドルで作られるアカウントに触れる UserOperation を除きます（ERC-4337 の Bundling）。送り主の storage は、その送り主自身の検証が書き換えられるので、後ろの検証の前提が崩れ得ます。

---

### EIP-7702 で変わったこと

[EIP-7702](https://eips.ethereum.org/EIPS/eip-7702) は、EOA がコントラクトのコードに実行を委任する仕組みです。2025 年 5 月 7 日に、Ethereum のプロトコルの更新（[ハードフォーク](../ethereum-hard-forks/)）である Pectra で有効になりました。委任の書き方は [Ethereum Account Model](../ethereum-account-model/) で説明しています。

委任した EOA のコードは誰からでも呼べるので、他人の取引の中でその EOA の残高が動くことがあります。委任先も、新しい承認（authorization、委任先を指定する署名）で変わります。EOA の取引は他人の取引に左右されない、という前提が崩れたわけです。

EIP-7702 の Security Considerations は、委任した EOA の保留中の取引を 1 件までに抑えるよう勧めています。

UserOperation の送り主にも委任した EOA を使えるので、ERC-7562 にも承認を扱う規則が足されました。

- 1 つの UserOperation に載せられる承認は 1 つまで
- 委任した EOA は送り主としてだけ使え、Paymaster や Factory にはなれない
- 委任した EOA のコードに触れて良いのは、その EOA が送り主の UserOperation だけ
- 同じ送り主の承認付き UserOperation は、全て同じ委任先を指す

EntryPoint が委任した EOA を送り主として扱えるのは v0.8 以降で、詳細は [ERC-4337](../erc-4337/) のノートにあります。

---

### 規則を確かめる仕組み

冒頭の図で 3 回目の検証が必要なのは、悪意のある stake した主体が、バンドルの検証の中で動いていることを検知して revert できるからです（仕様の Validation Rules）。stake した主体は広い storage を読めるので、1 件ずつの検証では通り、バンドルの中でだけ失敗するように書けます。仕様は検知の方法を挙げていませんが、例えば、同じバンドルで先に動いた UserOperation が書いた値を読めば、1 件だけのシミュレーションとの違いを見分けられます。

3 回目で見つかった主体は、前節の reputation で BANNED になります。

`eth_call` で `handleOps` を呼ぶだけでは、成否と戻り値しか分かりません。規則を当てるには、検証で使われた命令、触れた storage の slot、`keccak` の入力（関連する slot の判定に必要）が必要です。Bundler は、実行の途中経過を記録して返す [`debug_traceCall`](https://geth.ethereum.org/docs/interacting-with-geth/rpc/ns-debug#debugtracecall) と、その記録の形を決める tracer で、これを集めます。

{{< figure src="images/erc-7562_tracer.webp" alt="左から、UserOperation の検証、debug_traceCall と erc7562Tracer（ノードが記録）、使った命令・触れた slot・keccak の入力の箱、規則と照合（ERC7562Parser、受け付けか拒否）の箱が矢印でつながる。下に、eth_call だけでは成否と戻り値しか分からないとある" caption="Bundler が規則を確認する流れ" align="center" >}}

参照実装の [eth-infinitism/bundler](https://github.com/eth-infinitism/bundler/tree/aae77140e5c2b1386d04eaeba2d23fc17a62bd87)（2026 年 11 月時点の最新のコミット `aae7714`）は、既定では [go-ethereum](https://github.com/ethereum/go-ethereum) の native tracer `erc7562Tracer` の出力を [ERC7562Parser](https://github.com/eth-infinitism/bundler/blob/aae77140e5c2b1386d04eaeba2d23fc17a62bd87/packages/validation-manager/src/ERC7562Parser.ts) で規則と照合します。

[erc7562Tracer](https://github.com/ethereum/go-ethereum/blob/v1.17.10/eth/tracers/native/erc7562.go) は go-ethereum v1.16.0 で入った tracer で（[PR #31006](https://github.com/ethereum/go-ethereum/pull/31006)）、呼び出しごとに使った命令（`usedOpcodes`）と触れた slot（`accessedSlots`）、取引全体の `keccak` の入力を返します。

<br>

禁止の一覧は、プロトコルに命令が増えると伸びます。2026 年 10 月には、まだメインネットで有効になっていない `SETCODEFROM` と `SLOTNUM` が一覧に足されました（[ERCs の変更履歴](https://github.com/ethereum/ERCs/commits/master/ERCS/erc-7562.md)）。

実装は仕様より遅れることがあります。2026 年 11 月時点で、上記の参照実装の禁止命令の一覧（[ERC7562BannedOpcodes.ts](https://github.com/eth-infinitism/bundler/blob/aae77140e5c2b1386d04eaeba2d23fc17a62bd87/packages/validation-manager/src/ERC7562BannedOpcodes.ts)）には、この 2 つがありません。Bundler を選ぶ時は、仕様と実装のバージョンを揃えて確認する必要があります。

---

### ローカルでの検証の実験

実験では、[Foundry](https://github.com/foundry-rs/foundry) のローカルのノード [Anvil](https://getfoundry.sh/anvil/overview) に、ERC-4337 のノートと同じ [eth-infinitism/account-abstraction](https://github.com/eth-infinitism/account-abstraction/tree/v0.9.0) v0.9.0 の EntryPoint と [SimpleAccount](https://github.com/eth-infinitism/account-abstraction/blob/v0.9.0/contracts/accounts/SimpleAccount.sol)・Factory をデプロイします。Bundler のソフトウェアは使わず、スクリプトが Bundler の役を代わります。

<br>

<details>
<summary>使ったソフトウェアの版とライセンス</summary>

- Anvil・cast 1.7.1（実行規則は Prague、チェーン ID 31337）
- eth-infinitism/account-abstraction v0.9.0（コミット `b36a1ed`）。EntryPoint は GPL-3.0、SimpleAccount と Factory は MIT
- [OpenZeppelin Contracts](https://github.com/OpenZeppelin/openzeppelin-contracts/tree/v5.1.0) v5.1.0（MIT）
- コンパイラ [solc 0.8.28](https://github.com/argotorg/solidity/releases/tag/v0.8.28)

ソースは本記事のリポジトリに複製せず、実行時に固定したコミットを取得します。手順は [lab/README.txt](lab/README.txt) にまとめています。

</details>

<br>

比べるアカウントは次の 6 つです。SimpleAccount 以外は本記事のために書いた学習用のコントラクト（[Lab.sol](lab/Lab.sol)）で、監査しておらず、署名の検証も省いています。鍵は Anvil の公開されたテスト用のニーモニックから作ったものだけです。

| アカウント | 検証で確認すること |
| --- | --- |
| SimpleAccount v0.9.0 | 所有者の署名（自分の storage にある所有者と照合） |
| TokenAccount | LabToken の `balanceOf[自分]` が 1 以上 |
| DeadlineAccount | 何も読まず、`validUntil` を返す |
| TimeAccount | `block.timestamp` が期限より前 |
| BalanceAccount | 自分の ETH の残高が 0 より多い |
| GateAccount | Gate というコントラクトの `isOpen` が true |

実験の出力は 4 段で、それぞれ次を確認します。

1. 6 つのアカウントの検証を `eth_call` と検査器に掛け、EntryPoint が通すものと規則が落とすものを比べる
2. 時刻を読む TimeAccount が、シミュレーションでは通り、期限を過ぎたブロックで失敗した時に誰が払うか
3. 10 個の GateAccount が読む Gate を攻撃者が同じブロックで閉じる割り込み（大量無効化の 3 つ目）
4. 前払い 1 件分の ETH しか持たない同じ送り主が、2 件の UserOperation を出す組み合わせ（大量無効化の 2 つ目）

時刻を扱う 2 つのアカウントの違いは、次の部分だけです。

```solidity
// TimeAccount: TIMESTAMP を読む（OP-011 の違反）
function _check() internal view override returns (uint256) {
    require(block.timestamp < deadline, "too late");
    return 0;
}

// DeadlineAccount: validUntil を返し、比較は EntryPoint に任せる
function _check() internal view override returns (uint256) {
    return uint256(deadline - 1) << 160; // validUntil, inclusive
}
```

使った Anvil は `erc7562Tracer` に対応していない（`unsupported tracer type` を返す）ので、スクリプトは `debug_traceCall` の既定の tracer（命令ごとの記録）から規則を判定します。

以下は、その小さな検査器から規則を当てる部分の抜粋です。呼び出しの深さを追ってアカウントの frame（呼び出しの単位）だけを選ぶ処理は、後の run.py の全体にあります。

対応する規則は OP-011・OP-012・OP-070・OP-080・STO-010・STO-021 だけで、stake や Factory・Paymaster の規則は判定しません。`keccak` の入力も、アカウントの frame の中で計算したものだけを見ます。

```python
# Inside check7562(): one struct log `log` of the account's frames.
# st = stack (top last), store = storage address of the current frame.
        if op in BANNED:                       # TIMESTAMP, NUMBER, ...
            violations.append(f'OP-011 {op} in {where}')
        if op in STAKED_ONLY:                  # BALANCE, SELFBALANCE
            violations.append(f'OP-080 {op} in {where} (unstaked)')
        if op == 'KECCAK256':                  # remember result -> preimage
            pre = mem(log, st[-1], st[-2])
            hashes[int(struct_logs[i + 1]['stack'][-1], 16)] = pre
        if op in STORAGE:                      # SLOAD, SSTORE, TLOAD, TSTORE
            slot = st[-1]
            if store == sender:
                rule, ok = 'own storage (STO-010)', True
            elif associated(slot, sender, hashes):
                rule, ok = 'associated (STO-021)', True
            else:
                rule, ok = 'not associated', False
                violations.append(f'STO-021 {op} slot {slot:#x} of {label(store)}')


def associated(slot, addr, hashes):
    """ERC-7562 'associated storage': slot == A, or slot == keccak(A || x) + n, 0 <= n <= 128."""
    if slot == addr:
        return True
    for n in range(129):
        pre = hashes.get(slot - n)
        if pre is not None and len(pre) == 64 and int.from_bytes(pre[:32], 'big') == addr:
            return True
    return False
```

`KECCAK256` の入力と結果を記録しておき、`SLOAD` の slot がその結果と一致すれば、関連する storage と判定します。

trace を取る時は、検証の対象の後ろに、コードの無い送り主の UserOperation を足して `handleOps` を呼びます。2 件目が `AA20 account not deployed` で失敗するので、バンドルは実行の前に revert し、trace には検証だけが残ります。ERC-4337 の Simulation の節が挙げている手法です。

<br>

<details>
<summary>run.py の全体（376 行）</summary>

```python
#!/usr/bin/env python3
"""Local-only ERC-7562 experiment (EntryPoint v0.9.0). Run through run.sh.

The script plays a bundler itself. It simulates UserOperations with eth_call,
traces their validation with debug_traceCall, and checks the trace against a
subset of the ERC-7562 rules (check7562 below). No bundler software, no
external RPC. Keys are Anvil's public test mnemonic only.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import urllib.request

HERE = Path(__file__).resolve().parent
OUT = HERE / 'output'
OUT.mkdir(exist_ok=True)
TOOLS = {n: os.environ.get(n.upper(), shutil.which(n)) for n in ('anvil', 'cast')}
if not all(TOOLS.values()):
    raise SystemExit('Put anvil and cast on PATH (or set ANVIL, CAST).')
BUILD = json.loads(Path(os.environ['BUILD']).read_text())['contracts']
MNEMONIC = 'test test test test test test test test test test test junk'  # Anvil default, public
GWEI = 10**9
ETH = 10**18
OP_TYPE = '(address,uint256,bytes,bytes,bytes32,uint256,bytes32,bytes,bytes)'


def cast(*args):
    return subprocess.check_output([TOOLS['cast'], *map(str, args)], text=True,
                                   stderr=subprocess.DEVNULL).strip()


def artifact(suffix):
    return next(v for k, v in BUILD.items() if k.endswith(suffix))


with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
URL = f'http://127.0.0.1:{port}'


def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(URL, body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.load(r)
    if 'error' in res:
        raise RuntimeError(res['error'])
    return res['result']


def submit(sender, data, to=None, value=0, gas=15_000_000, price=2 * GWEI):
    # Legacy gasPrice keeps the price fixed, as in the erc-4337 note.
    tx = {'from': sender, 'data': data, 'value': hex(value), 'gas': hex(gas), 'gasPrice': hex(price)}
    if to:
        tx['to'] = to
    return rpc('eth_sendTransaction', tx)


def receipt(h):
    for _ in range(400):
        r = rpc('eth_getTransactionReceipt', h)
        if r:
            return r
        time.sleep(0.05)
    raise TimeoutError(h)


def send(*args, **kw):
    r = receipt(submit(*args, **kw))
    assert int(r['status'], 16) == 1, r
    return r


def deploy(sender, suffix, sig='', *ctor):
    a = artifact(suffix)
    args = cast('abi-encode', f'f({sig})', *ctor)[2:] if ctor else ''
    return send(sender, '0x' + a['bin'] + args)['contractAddress']


def call(to, sig, *args):
    return cast('call', '--rpc-url', URL, to, sig, *args)


def balance(addr):
    return int(rpc('eth_getBalance', addr, 'latest'), 16)


def deposit_of(addr):
    return int(call(entry_point, 'balanceOf(address)(uint256)', addr).split()[0])


def u128x2(hi, lo):
    return '0x' + f'{hi:032x}{lo:032x}'


def op_tuple(op):
    return '(' + ','.join(str(op[k]) for k in (
        'sender', 'nonce', 'initCode', 'callData', 'accountGasLimits',
        'preVerificationGas', 'gasFees', 'paymasterAndData', 'signature')) + ')'


def user_op(sender, to):
    return {'sender': sender, 'nonce': 0, 'initCode': '0x',
            'callData': cast('calldata', 'execute(address,uint256,bytes)', to, 0, '0x'),
            'accountGasLimits': u128x2(200_000, 50_000),   # verificationGasLimit, callGasLimit
            'preVerificationGas': 50_000,
            'gasFees': u128x2(2 * GWEI, 2 * GWEI),          # maxPriorityFeePerGas, maxFeePerGas
            'paymasterAndData': '0x', 'signature': '0x'}


def handle_ops(ops):
    return cast('calldata', f'handleOps({OP_TYPE}[],address)',
                '[' + ','.join(op_tuple(o) for o in ops) + ']', bundler)


def simulate(ops):
    """First validation of a naive bundler: eth_call handleOps. Returns 'ok' or the FailedOp text."""
    try:
        rpc('eth_call', {'from': bundler, 'to': entry_point, 'data': handle_ops(ops), 'gas': hex(3_000_000)}, 'latest')
        return 'ok'
    except RuntimeError as e:
        data = e.args[0].get('data', '')
        for sig in ('FailedOpWithRevert(uint256,string,bytes)', 'FailedOp(uint256,string)'):
            try:
                idx, msg = cast('decode-error', '--sig', sig, data).splitlines()[:2]
                return f'op {idx}: {msg}'
            except subprocess.CalledProcessError:
                pass
        return str(e.args[0])


# ---------------------------------------------------------------------------
# A small ERC-7562 checker over the default (struct log) tracer of debug_traceCall.
# It covers OP-011, OP-012, OP-080 and the storage rules for an existing,
# unstaked account without paymaster or factory (STO-010, STO-021).
BANNED = {'ORIGIN', 'GASPRICE', 'BLOCKHASH', 'COINBASE', 'TIMESTAMP', 'NUMBER', 'PREVRANDAO',
          'DIFFICULTY', 'GASLIMIT', 'BASEFEE', 'BLOBHASH', 'BLOBBASEFEE', 'CREATE', 'INVALID',
          'SELFDESTRUCT'}                                   # OP-011 (CREATE: no factory here)
STAKED_ONLY = {'BALANCE', 'SELFBALANCE'}                    # OP-080
CALLS = {'CALL', 'STATICCALL', 'DELEGATECALL', 'CALLCODE'}
STORAGE = {'SLOAD', 'SSTORE', 'TLOAD', 'TSTORE'}


def mem(log, off, size):
    blob = bytes.fromhex(''.join(w.removeprefix('0x') for w in log.get('memory') or []))
    return blob[off:off + size].ljust(size, b'\0')


NAMES = {}  # address (int) -> short name, for printing only


def label(a):
    return NAMES.get(a, f'{a:#x}'[:10])


def check7562(sender, struct_logs):
    """Return (opcodes, slots, violations, validUntil) for the frames of `sender` and below."""
    sender = int(sender, 16)
    stack = []            # [(depth, code_addr, storage_addr)] of frames under the sender
    pending = None        # call seen at depth d; resolved by the next log
    hashes = {}           # keccak result -> preimage, as seen in the trace
    opcodes, slots, violations, valid_until = {}, [], [], None
    for i, log in enumerate(struct_logs):
        d, op, st = log['depth'], log['op'], [int(x, 16) for x in log['stack']]
        if pending:
            pd, code, store = pending
            pending = None
            if d == pd + 1 and (stack or code == sender):
                stack.append((d, code, store))
        while stack and d < stack[-1][0]:
            stack.pop()
        if op in CALLS:
            target = st[-2]
            store = stack[-1][2] if op in ('DELEGATECALL', 'CALLCODE') and stack else target
            pending = (d, target, store)
        if not stack or d != stack[-1][0]:
            continue
        code, store = stack[-1][1], stack[-1][2]
        opcodes[op] = opcodes.get(op, 0) + 1
        where = label(code)
        if op in BANNED:
            violations.append(f'OP-011 {op} in {where}')
        if op in STAKED_ONLY:
            violations.append(f'OP-080 {op} in {where} (unstaked)')
        if op == 'GAS' and struct_logs[i + 1]['op'] not in CALLS:
            violations.append(f'OP-012 GAS not followed by CALL in {where}')
        if op == 'KECCAK256':
            pre = mem(log, st[-1], st[-2])
            hashes[int(struct_logs[i + 1]['stack'][-1], 16)] = pre
        if op in STORAGE:
            slot = st[-1]
            if store == sender:
                rule, ok = 'own storage (STO-010)', True
            elif associated(slot, sender, hashes):
                rule, ok = 'associated (STO-021)', True
            else:
                rule, ok = 'not associated', False
                violations.append(f'STO-021 {op} slot {slot:#x} of {label(store)}')
            short = f'{slot:#x}' if slot < 2**32 else f'{slot:#x}'[:12] + '..'
            slots.append(f'{op} {label(store)} slot {short}: {rule}')
        if op == 'RETURN' and len(stack) == 1 and st[-2] == 32:
            valid_until = int.from_bytes(mem(log, st[-1], 32), 'big') >> 160 & (2**48 - 1)
    return opcodes, slots, violations, valid_until


def associated(slot, addr, hashes):
    """ERC-7562 'associated storage': slot == A, or slot == keccak(A || x) + n, 0 <= n <= 128."""
    if slot == addr:
        return True
    for n in range(129):
        pre = hashes.get(slot - n)
        if pre is not None and len(pre) == 64 and int.from_bytes(pre[:32], 'big') == addr:
            return True
    return False


def trace_validation(op):
    """debug_traceCall of handleOps([op, stopper]): the stopper fails with AA20,
    so the bundle reverts before any execution and the trace holds validation only."""
    stopper = dict(op, sender=cast('wallet', 'address', '--private-key', cast('wallet', 'private-key', MNEMONIC, 19)))
    tx = {'from': bundler, 'to': entry_point, 'data': handle_ops([op, stopper]), 'gas': hex(3_000_000)}
    res = rpc('debug_traceCall', tx, 'latest', {'enableMemory': True, 'disableStorage': True})
    return res['structLogs']


lines = []
log = (OUT / 'node.log').open('w')
node = subprocess.Popen([TOOLS['anvil'], '--host', '127.0.0.1', '--port', str(port),
                         '--chain-id', '31337', '--hardfork', 'prague', '--timestamp', '1700000000',
                         '--accounts', '4', '--quiet'], stdout=log, stderr=log)
try:
    for _ in range(200):
        try:
            bundler, deployer, attacker = rpc('eth_accounts')[:3]
            break
        except (OSError, RuntimeError):
            time.sleep(0.05)
    else:
        raise TimeoutError('Anvil startup')
    rpc('anvil_setBlockTimestampInterval', 1)                 # +1 s per block: reproducible times
    owner_key = cast('wallet', 'private-key', MNEMONIC, 5)    # never funded
    owner = cast('wallet', 'address', '--private-key', owner_key)
    recipient = cast('wallet', 'address', '--private-key', cast('wallet', 'private-key', MNEMONIC, 7))

    entry_point = deploy(deployer, ':EntryPoint')
    factory = deploy(deployer, ':SimpleAccountFactory', 'address', entry_point)
    token = deploy(deployer, ':LabToken')
    gate = deploy(attacker, ':Gate')                          # the attacker owns the switch
    t0 = int(rpc('eth_getBlockByNumber', 'latest', False)['timestamp'], 16)
    deadline = t0 + 60
    acct = {
        'SimpleAccount v0.9.0': None,
        'TokenAccount': deploy(deployer, ':TokenAccount', 'address,address', entry_point, token),
        'DeadlineAccount': deploy(deployer, ':DeadlineAccount', 'address,uint48', entry_point, deadline),
        'TimeAccount': deploy(deployer, ':TimeAccount', 'address,uint256', entry_point, deadline),
        'BalanceAccount': deploy(deployer, ':BalanceAccount', 'address', entry_point),
        'GateAccount': deploy(deployer, ':GateAccount', 'address,address', entry_point, gate),
    }
    acct['SimpleAccount v0.9.0'] = call(factory, 'getAddress(address,uint256)(address)', owner, 0)
    NAMES.update({int(v, 16): k.split()[0] for k, v in acct.items()})
    NAMES.update({int(token, 16): 'LabToken', int(gate, 16): 'Gate'})
    send(deployer, cast('calldata', 'mint(address,uint256)', acct['TokenAccount'], 1), token)
    send(deployer, '0x', acct['BalanceAccount'], value=ETH // 100)
    for a in acct.values():   # prepaid deposit, so validation never sends ETH (missingAccountFunds = 0)
        send(deployer, cast('calldata', 'depositTo(address)', a), entry_point, value=ETH // 10)

    def op_for(name, init='0x'):
        o = user_op(acct[name], recipient)
        o['nonce'] = int(call(entry_point, 'getNonce(address,uint192)(uint256)', acct[name], 0).split()[0])
        o['initCode'] = init
        if name.startswith('SimpleAccount'):
            h = call(entry_point, f'getUserOpHash({OP_TYPE})(bytes32)', op_tuple(o))
            o['signature'] = cast('wallet', 'sign', '--no-hash', '--private-key', owner_key, h)
        return o

    # SimpleAccount is created by its first UserOperation (initCode = factory + createAccount).
    init = factory + cast('calldata', 'createAccount(address,uint256)', owner, 0)[2:]
    send(bundler, handle_ops([op_for('SimpleAccount v0.9.0', init)]), entry_point, gas=3_000_000)

    # --- 1. trace each validation and check it ---
    now = int(rpc('eth_getBlockByNumber', 'latest', False)['timestamp'], 16)
    lines.append(f'# 1. validation traced with debug_traceCall (block time {now}, deadline {deadline})')
    lines.append(f'{"account":21}| eth_call | ERC-7562 check')
    details = []
    for name in acct:
        o = op_for(name)
        sim = simulate([o])
        opcodes, slots, bad, vu = check7562(acct[name], trace_validation(o))
        verdict = 'accept' if not bad else 'reject: ' + bad[0].split(' in ')[0].split(' slot')[0]
        lines.append(f'{name:21}| {sim:8} | {verdict}')
        details.append(f'[{name}] {sum(opcodes.values())} opcodes executed in the account frames'
                       + (f', validUntil {vu}' if vu else ''))
        details += [f'  {s}' for s in slots]
        details += [f'  violation: {v}' for v in bad]
    lines += details
    expected = {'SimpleAccount v0.9.0': [], 'TokenAccount': [], 'DeadlineAccount': []}
    for name in expected:
        assert not check7562(acct[name], trace_validation(op_for(name)))[2], name

    # --- 2. TIMESTAMP: passes the simulation, fails in the block, the bundler pays ---
    lines.append('# 2. TimeAccount: simulated now, mined at the deadline')
    o = op_for('TimeAccount')
    b0, d0 = balance(bundler), deposit_of(acct['TimeAccount'])
    now = int(rpc('eth_getBlockByNumber', 'latest', False)['timestamp'], 16)
    lines.append(f'simulation at {now}  : {simulate([o])}')
    rpc('evm_setNextBlockTimestamp', hex(deadline))
    r = receipt(submit(bundler, handle_ops([o]), entry_point, gas=1_000_000))
    gas_used, price = int(r['gasUsed'], 16), int(r['effectiveGasPrice'], 16)
    assert int(r['status'], 16) == 0
    lines.append(f'mined at {deadline}       : status {int(r["status"], 16)} (reverted), gasUsed {gas_used}')
    lines.append(f'bundler balance change : {(balance(bundler) - b0) / GWEI:+.0f} gwei'
                 f' (= {gas_used} gas x {price // GWEI} gwei)')
    lines.append(f'account deposit change : {(deposit_of(acct["TimeAccount"]) - d0) / GWEI:+.0f} gwei')
    assert balance(bundler) - b0 == -gas_used * price and deposit_of(acct['TimeAccount']) == d0
    lines.append(f'DeadlineAccount now    : {simulate([op_for("DeadlineAccount")])}'
                 f' (validUntil {deadline - 1} was visible in the trace)')

    # --- 3. one storage write invalidates many UserOperations ---
    lines.append('# 3. ten GateAccounts and one Gate.close() from the attacker')
    gates = [deploy(deployer, ':GateAccount', 'address,address', entry_point, gate) for _ in range(10)]
    for a in gates:
        send(deployer, cast('calldata', 'depositTo(address)', a), entry_point, value=ETH // 10)
    ops = [user_op(a, recipient) for a in gates]
    lines.append(f'first validation  : {sum(simulate([x]) == "ok" for x in ops)}/10 ok, '
                 f'bundle of 10: {simulate(ops)}')
    b0, a0 = balance(bundler), balance(attacker)
    g0 = sum(deposit_of(a) + balance(a) for a in gates)
    rpc('evm_setAutomine', False)
    hb = submit(bundler, handle_ops(ops), entry_point, gas=3_000_000, price=2 * GWEI)
    ha = submit(attacker, cast('calldata', 'close()'), gate, gas=100_000, price=3 * GWEI)  # front-runs
    rpc('evm_mine')
    rpc('evm_setAutomine', True)
    rb, ra = receipt(hb), receipt(ha)
    assert rb['blockNumber'] == ra['blockNumber'] and int(ra['transactionIndex'], 16) < int(rb['transactionIndex'], 16)
    assert int(ra['status'], 16) == 1 and int(rb['status'], 16) == 0
    cost = lambda x: int(x['gasUsed'], 16) * int(x['effectiveGasPrice'], 16)
    lines.append(f'same block        : close() index {int(ra["transactionIndex"], 16)} status 1, '
                 f'handleOps index {int(rb["transactionIndex"], 16)} status 0')
    lines.append(f'attacker paid     : {cost(ra) // GWEI} gwei ({int(ra["gasUsed"], 16)} gas x 3 gwei)')
    paid = g0 - sum(deposit_of(a) + balance(a) for a in gates)
    lines.append(f'bundler paid      : {cost(rb) // GWEI} gwei ({int(rb["gasUsed"], 16)} gas x 2 gwei)')
    lines.append(f'10 GateAccounts   : {paid // GWEI} gwei (deposit + balance change)')
    assert b0 - balance(bundler) == cost(rb) and a0 - balance(attacker) == cost(ra) and paid == 0
    after = [simulate([x]) for x in ops]
    lines.append(f'second validation : {sum(x == "ok" for x in after)}/10 ok ({after[0]})')

    # --- 4. same sender twice in one bundle (two nonce keys, ETH for one prefund) ---
    lines.append('# 4. one sender, two UserOperations, ETH for one prefund only')
    solo = deploy(deployer, ':TokenAccount', 'address,address', entry_point, token)
    send(deployer, cast('calldata', 'mint(address,uint256)', solo, 1), token)
    prefund = (200_000 + 50_000 + 50_000) * 2 * GWEI
    send(deployer, '0x', solo, value=prefund * 3 // 2)
    pair = [dict(user_op(solo, recipient), nonce=k << 64) for k in (0, 1)]  # nonce keys 0 and 1
    lines.append(f'prefund per op    : {prefund // GWEI} gwei, account balance {balance(solo) // GWEI} gwei')
    lines.append(f'op(key 0) alone   : {simulate(pair[:1])}')
    lines.append(f'op(key 1) alone   : {simulate(pair[1:])}')
    lines.append(f'both in one bundle: {simulate(pair)}')
    assert simulate(pair[:1]) == simulate(pair[1:]) == 'ok' and simulate(pair) != 'ok'
    lines.append('Assertions: PASS')
    summary = '\n'.join(lines) + '\n'
    (OUT / 'summary.txt').write_text(summary)
    (OUT / 'versions.txt').write_text('\n'.join(
        subprocess.check_output([t, '--version'], text=True).splitlines()[0] for t in TOOLS.values()) + '\n')
    print(summary, end='')
finally:
    node.terminate()
    try:
        node.wait(timeout=5)
    except subprocess.TimeoutExpired:
        node.kill()
    log.close()
```

</details>

<br>

<details>
<summary>Lab.sol の全体（120 行）</summary>

```solidity
// SPDX-License-Identifier: MIT
// Learning contracts for the ERC-7562 note. Not audited. Do not deploy.
// Signature checks are left out on purpose: anyone could use these accounts.
pragma solidity 0.8.28;

import {PackedUserOperation} from "contracts/interfaces/PackedUserOperation.sol";

abstract contract LabAccount {
    address public immutable entryPoint;

    constructor(address ep) {
        entryPoint = ep;
    }

    function validateUserOp(PackedUserOperation calldata, bytes32, uint256 missingAccountFunds)
        external
        returns (uint256 validationData)
    {
        require(msg.sender == entryPoint, "not EntryPoint");
        validationData = _check();
        if (missingAccountFunds > 0) {
            (bool ok,) = payable(msg.sender).call{value: missingAccountFunds}("");
            ok;
        }
    }

    function _check() internal view virtual returns (uint256);

    function execute(address to, uint256 value, bytes calldata data) external {
        require(msg.sender == entryPoint, "not EntryPoint");
        (bool ok,) = to.call{value: value}(data);
        require(ok, "call failed");
    }

    receive() external payable {}
}

// Reads TIMESTAMP inside validation (OP-011).
contract TimeAccount is LabAccount {
    uint256 public immutable deadline;

    constructor(address ep, uint256 d) LabAccount(ep) {
        deadline = d;
    }

    function _check() internal view override returns (uint256) {
        require(block.timestamp < deadline, "too late");
        return 0;
    }
}

// Same intent, but returns validUntil and lets the EntryPoint compare it.
contract DeadlineAccount is LabAccount {
    uint48 public immutable deadline;

    constructor(address ep, uint48 d) LabAccount(ep) {
        deadline = d;
    }

    function _check() internal view override returns (uint256) {
        return uint256(deadline - 1) << 160; // validUntil, inclusive
    }
}

// A switch in another contract that anyone's account may depend on.
contract Gate {
    address public immutable owner = msg.sender;
    bool public isOpen = true;

    function close() external {
        require(msg.sender == owner, "not owner");
        isOpen = false;
    }
}

// Reads a slot of Gate that is not associated with the account (STO-021 fails).
contract GateAccount is LabAccount {
    Gate public immutable gate;

    constructor(address ep, Gate g) LabAccount(ep) {
        gate = g;
    }

    function _check() internal view override returns (uint256) {
        require(gate.isOpen(), "gate closed");
        return 0;
    }
}

contract LabToken {
    mapping(address => uint256) public balanceOf; // slot 0

    function mint(address to, uint256 v) external {
        balanceOf[to] += v;
    }
}

// Reads balanceOf[this] in a token: keccak(this || 0), associated storage (STO-021 allows).
contract TokenAccount is LabAccount {
    LabToken public immutable token;

    constructor(address ep, LabToken t) LabAccount(ep) {
        token = t;
    }

    function _check() internal view override returns (uint256) {
        require(token.balanceOf(address(this)) > 0, "no token");
        return 0;
    }
}

// Reads its own ETH balance with SELFBALANCE (OP-080: staked entities only).
contract BalanceAccount is LabAccount {
    constructor(address ep) LabAccount(ep) {}

    function _check() internal view override returns (uint256) {
        require(address(this).balance > 0, "empty");
        return 0;
    }
}
```

</details>

<br>

```bash
bash content/notes/blockchain-systems/erc-7562/lab/run.sh
```

以下は、[出力](lab/output/summary.txt)の 1 段目です。2〜4 段目を含む全体は、その下に畳んでいます。

```text
# 1. validation traced with debug_traceCall (block time 1700000018, deadline 1700000064)
account              | eth_call | ERC-7562 check
SimpleAccount v0.9.0 | ok       | accept
TokenAccount         | ok       | accept
DeadlineAccount      | ok       | accept
TimeAccount          | ok       | reject: OP-011 TIMESTAMP
BalanceAccount       | ok       | reject: OP-080 SELFBALANCE
GateAccount          | ok       | reject: STO-021 SLOAD
```

<br>

<details>
<summary>出力の全体（4 段、Assertions: PASS まで）</summary>

```text
# 1. validation traced with debug_traceCall (block time 1700000018, deadline 1700000064)
account              | eth_call | ERC-7562 check
SimpleAccount v0.9.0 | ok       | accept
TokenAccount         | ok       | accept
DeadlineAccount      | ok       | accept
TimeAccount          | ok       | reject: OP-011 TIMESTAMP
BalanceAccount       | ok       | reject: OP-080 SELFBALANCE
GateAccount          | ok       | reject: STO-021 SLOAD
[SimpleAccount v0.9.0] 385 opcodes executed in the account frames
  SLOAD SimpleAccount slot 0x360894a13b..: own storage (STO-010)
  SLOAD SimpleAccount slot 0x0: own storage (STO-010)
[TokenAccount] 224 opcodes executed in the account frames
  SLOAD LabToken slot 0x2bdc1ac19b..: associated (STO-021)
[DeadlineAccount] 89 opcodes executed in the account frames, validUntil 1700000063
[TimeAccount] 79 opcodes executed in the account frames
  violation: OP-011 TIMESTAMP in TimeAccount
[BalanceAccount] 77 opcodes executed in the account frames
  violation: OP-080 SELFBALANCE in BalanceAccount (unstaked)
[GateAccount] 209 opcodes executed in the account frames
  SLOAD Gate slot 0x0: not associated
  violation: STO-021 SLOAD slot 0x0 of Gate
# 2. TimeAccount: simulated now, mined at the deadline
simulation at 1700000018  : ok
mined at 1700000064       : status 0 (reverted), gasUsed 36926
bundler balance change : -73852 gwei (= 36926 gas x 2 gwei)
account deposit change : +0 gwei
DeadlineAccount now    : op 0: "AA22 expired or not due" (validUntil 1700000063 was visible in the trace)
# 3. ten GateAccounts and one Gate.close() from the attacker
first validation  : 10/10 ok, bundle of 10: ok
same block        : close() index 0 status 1, handleOps index 1 status 0
attacker paid     : 64287 gwei (21429 gas x 3 gwei)
bundler paid      : 207780 gwei (103890 gas x 2 gwei)
10 GateAccounts   : 0 gwei (deposit + balance change)
second validation : 0/10 ok (op 0: "AA23 reverted")
# 4. one sender, two UserOperations, ETH for one prefund only
prefund per op    : 600000 gwei, account balance 900000 gwei
op(key 0) alone   : ok
op(key 1) alone   : ok
both in one bundle: op 1: "AA21 didn't pay prefund"
Assertions: PASS
```

</details>

<br>

---

### 実験の結果

1 段目の `eth_call` の列は、6 つとも `ok` です。`TIMESTAMP` を読むアカウントも、他のコントラクトの storage を読むアカウントも、EntryPoint は普通に検証を通しています。

規則で落としたのは検査器の列の 3 つで、ERC-7562 は EntryPoint ではなく Bundler が当てる規則だと分かります。TokenAccount が読んだ LabToken の slot は、trace の中の `keccak(TokenAccount || 0)` の結果と一致したので、関連する storage と判定されました。

2 段目では、期限の 46 秒前のブロックでシミュレーションが通り、期限ちょうどのブロックで `handleOps` が revert しました。Bundler の EOA は 36,926 gas × 2 gwei = 73,852 gwei（1 gwei は 10 億分の 1 ETH）を払い、アカウントの deposit は 1 gwei も減っていません。

一方で、DeadlineAccount では trace から `validUntil` が読めるので、Bundler は期限を過ぎる前にバンドルから外せます。期限の後に送れば EntryPoint が `AA22` で拒否するので、期限を守らせる仕組みはチェーンの上にも残ります。

<br>

3 段目は、大量無効化の 3 つ目の方法です。10 件の UserOperation は、1 件ずつでもバンドルでもシミュレーションを通りました。攻撃者が同じブロックで `Gate.close()` を Bundler の取引より高い単価で割り込ませると、`handleOps` は revert しました。

{{< figure src="images/erc-7562_paid.webp" alt="横棒グラフ。無効になったバンドル 1 件で払った額は、Bundler が 207,780 gwei、攻撃者が 64,287 gwei、10 個の GateAccount が 0 gwei" caption="割り込みの実験（出力の 3 段目）で、誰がいくら払ったか" align="center" >}}

Bundler が払ったのは 207,780 gwei（103,890 gas × 2 gwei）、攻撃者が払ったのは 64,287 gwei（21,429 gas × 3 gwei）で、10 個の GateAccount の deposit と残高は 1 gwei も減っていません。

10 件の UserOperation は全て、次の検証で無効になっています。GateAccount は Gate の slot 0 を読む時点で検査器に落とされるので、ERC-7562 に従う Bundler はこのバンドルを作りません。

4 段目では、1 件分の前払い（600,000 gwei）に対して 900,000 gwei しか持たないアカウントが、nonce の key を変えて 2 件を出しています。1 件ずつなら通り、バンドルにすると 2 件目（op 1）が `AA21 didn't pay prefund` で失敗しました。送り主ごとに 1 件、または一緒に検証する、という規則が必要な理由です。

---

### 利点

- Bundler が、他人の取引や時間の経過でただ働きさせられる経路を塞げる
- 規則を共有するので、どの Bundler も同じ UserOperation を有効と判定し、P2P の mempool で配れる
- stake すれば、Paymaster や Factory も自分の storage を使った検証を書ける

---

### 欠点

ERC-7562 は、検証を他の UserOperation から切り離す代わりに、検証で書けるコードを狭めています。

- 外部の価格や他のコントラクトの状態に頼る検証は、標準の mempool では受け付けられない
- 規則を当てるには `debug_traceCall` と専用の tracer が必要で、Bundler を動かすノードを選ぶ
- 命令が増えるたびに一覧の更新が必要で、仕様と実装の間に遅れが出る
- reputation は Bundler ごとの数え方なので、同じ主体の扱いが Bundler で一時的にずれ得る

---

### 適さないケース

- 検証の段階で、[オラクル](../oracle/)の価格や他のアカウントの状態を読みたい場合。読むのは実行の段階に移す
- 規則を緩めた検証が必要で、標準の mempool に載せられない場合。仕様は alternative mempool（規則を合意し直した別の mempool）を用意しているが、参加する Bundler に限られる
- Bundler を経由せず、自分の EOA から `handleOps` を直接送る運用。この場合は自分で手数料のリスクを負うので、ERC-7562 は守る相手がいない
