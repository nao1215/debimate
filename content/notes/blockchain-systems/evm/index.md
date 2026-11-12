---
title: "EVM - Ethereum のトランザクションを実行する仮想マシンの全体像"
date: 2026-11-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "evm", "smart-contract", "gas"]
weight: 17
wrapTables: true
topics: ["Smart Contract"]
---

EVM（Ethereum Virtual Machine）は、[Ethereum](https://ethereum.org/) のノードが、トランザクションで呼び出されたコントラクトのコードを実行する仮想マシンです。[Solidity](https://www.soliditylang.org/) などで書いたプログラムはバイトコードにコンパイルされ、EVM がその命令を 1 つずつ実行して、残高やストレージの値を更新します。

EVM の話に入る前に、Ethereum の登場人物を確認します。Ethereum の状態は、アドレスごとのアカウントの集まりで、アカウントには 2 種類あります。

{{< figure src="images/evm_overview.webp" alt="左の EOA の箱に秘密鍵・残高・nonce。そこから「トランザクション」の矢印（宛先・額・入力、ガスの上限）が右のコントラクトに向かう。コントラクトの中には青いコード（不変）と黄土色の storage（キー → 値）があり、コードから storage に読み書きの矢印" caption="EOA が送るトランザクションと、コードと storage を持つコントラクト" align="center" >}}

上記の図の EOA（Externally Owned Account）は、人が秘密鍵で操作する通常のアカウントで、残高と nonce を持ちます。nonce は、そのアカウントが送ったトランザクションを数える番号で、同じトランザクションを 2 回実行させないために使います。

コントラクト（contract）は、デプロイしたプログラムのコードと、そのコードが読み書きするストレージ（storage）を持つアカウントです。コードはデプロイ後に変わらず、storage はキーと値の対応表です。

EOA が署名したトランザクション（transaction）は、宛先（to）、送る ETH の額（value）、コードに渡す入力（data）、使ってよいガスの上限（gas limit）を持ちます。宛先がコントラクトなら、ノードは EVM でそのコードを実行し、storage や残高を書き換えます。

<br>

Ethereum には、計算結果を配る中央のサーバーがありません。全てのノードがブロックに並んだトランザクションを自分で実行し、同じ状態になることを確認します。

{{< figure src="images/evm_nodes.webp" alt="灰色の枠の中で、ノード 1・2・3 がそれぞれ自分の EVM で同じトランザクションを実行し、3 本の矢印が緑の「同じ新しい状態（1 つでも違えば合わない）」に集まる" caption="全ノードが同じトランザクションを実行し、同じ状態になる" align="center" >}}

上記の図のように、1 つのノードでも結果が違えば、そのノードは他と別の状態を持つことになります。そのため EVM は、同じ入力から必ず同じ結果が出るように、命令の意味を細かく決めています。

もう 1 つの前提がガス（gas）です。EVM の全ての命令には、ガスという単位で値段が決まっています。以下は、トランザクション 1 件のガスと手数料の関係を示した図です。

{{< figure src="images/evm_gas_fee.webp" alt="横長の棒がガスの上限（gas limit）で、左の青い部分が使ったガス（gasUsed）、右の白い部分が使わなかった分。使ったガスから黄土色の「手数料 = gasUsed × 単価、ETH（wei）で払う」へ、使わなかった分から点線の「払わない」へ矢印" caption="ガスの上限・使ったガス・手数料" align="center" >}}

トランザクションはガスの上限（gas limit）の範囲でしか実行できず、使い切ると実行は止まります。送り主は、実際に使ったガス（gasUsed）に 1 ガスあたりの単価を掛けた額を ETH で払い、使わなかった分は払いません。額の単位には、ETH の 10 の 18 乗分の 1 にあたる wei も使います。ガスがなぜ必要かは「命令とガス」の節で説明します。

EVM の仕様は 1 つですが、実装（ノードで動くソフトウェアで、クライアントとも呼びます）は複数あります。Go で書かれた [go-ethereum](https://github.com/ethereum/go-ethereum)（geth）や、開発用のローカルノードの [Foundry の Anvil](https://getfoundry.sh/anvil/overview) が使う Rust の [revm](https://github.com/bluealloy/revm) などが、同じブロックから同じ状態を計算します。

{{< figure src="images/evm_clients.webp" alt="左の青い「仕様（execution-specs）」から、geth（Go）・revm（Rust）・他の実装の 3 つに矢印が分かれ、3 つから緑の「同じブロック → 同じ状態」に矢印が集まる。下に「Anvil は revm を使う」" caption="1 つの仕様と複数の実装" align="center" >}}

上記の図の仕様は、[Python](https://www.python.org/) で書かれていてテストとしても動かせる [execution-specs](https://github.com/ethereum/execution-specs) が読みやすいです。本記事は Anvil で実験し、規則の根拠として geth と execution-specs のコードをコミットを固定して参照します。

<br>

本記事では、EVM を初めて学ぶ開発者に向けて、トランザクションが届いてからコードが実行され、結果が残るまでを順に説明します。最初にトランザクションを処理する全体の流れを見て、EVM の中の仕組み（スタック、データ領域、フレーム）、ガス、関数の呼び分け（calldata と ABI）、コントラクト同士の呼び出し、失敗の扱いへ進みます。

Ethereum は、全てのノードが決めた時期に一斉に規則を切り替える更新（ハードフォーク）を重ねていて、命令やガスの値は更新ごとに変わります。本文では、更新を「2021 年 4 月の更新（Berlin）」のように時期と名前で示します。

命令が更新ごとにどう増えてきたかは [EVM Opcode History](../evm-opcode-history/) に分けました。本記事の数値は、2026 年 11 月 10 日時点の [Ethereum mainnet](../mainnet-and-testnet/) の規則（2025 年 12 月の更新 [Osaka](https://eips.ethereum.org/EIPS/eip-7607) の後）によるもので、他のチェーンでは異なる場合があります。

---

### トランザクションからコードの実行まで

ノードが 1 件のトランザクションを処理して状態を次に進める流れ（状態遷移、state transition）は、外側から順に「トランザクションの検査と精算」「メッセージ呼び出し」「命令の実行ループ」の 3 段の入れ子になっています。

{{< figure src="images/evm_pipeline.webp" alt="灰色の外枠がトランザクションの処理（状態遷移）。左の「検査」の箱に署名・nonce・intrinsic gas・前払い、右の「精算」の箱に払い戻し・手数料・レシートがある。中央の青い枠がメッセージ呼び出し（フレーム）で、その中で「読む → ガスを引く → 実行」のループが STOP・RETURN・REVERT・エラーまで回る。下の点線の枠は「CALL → 子のフレーム」" caption="1 件のトランザクションを処理する 3 段の入れ子" align="center" >}}

外側の左では、署名（signature）と nonce を確認し、トランザクション 1 件ごとに決まった基本のガス（intrinsic gas）を引き、gas limit 分の手数料を送り主の残高から前払いさせます。EVM はまだ動いていません。

中央のメッセージ呼び出し（message call）は、呼び出し元・宛先・入力・渡すガス・送る ETH の組です。EVM はこれを 1 つのフレーム（frame）として実行します。

フレームは、1 回の呼び出しの実行に必要なもの（残りのガス、後で説明するスタックや memory）をまとめた単位です。フレームの中では、命令を読み、ガスを引き、実行する、を停止まで繰り返します。コードが CALL 命令で別のコントラクトを呼ぶと、同じループを持つ子のフレームが作られます。

外側の右では、払い戻し（refund。storage の値を 0 に戻した時などに付く割引で、後の節で説明）を計算し、使わなかったガスの分を送り主に返して手数料を払い、レシート（receipt）を作ります。レシートはトランザクションの結果を記録したもので、ノードの API が返すレシートは、成否を表す `status`、使ったガスの `gasUsed`、後で説明するログを持ちます。

<br>

<details>
<summary>3 段に当たる geth と execution-specs の関数</summary>

| 段 | geth（Go） | execution-specs（Python、Osaka） |
| --- | --- | --- |
| トランザクションの検査と精算 | [`ApplyMessage`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/state_transition.go#L396-L404) → [`execute`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/state_transition.go#L716-L817) | [`process_transaction`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/fork.py#L829-L978) |
| メッセージ呼び出し | [`EVM.Call`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/evm.go#L276-L334) | [`process_message_call`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/vm/interpreter.py#L92-L160) |
| 命令の実行ループ | [`EVM.Run`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/interpreter.go#L96-L137) | [`process_message`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/vm/interpreter.py#L221-L302) |

</details>

<br>

EVM が担うのは、上記の図の中央の部分だけです。どのブロックを採用するかの合意は、[Proof of Stake](../proof-of-stake/) を担う別のソフトウェアの仕事で、EVM は関わりません。また、宛先が EOA で ETH を送るだけのトランザクションなら、宛先にコードが無いので、EVM の命令は 1 つも実行されません。

コントラクトは、時間が来ても自分では動きません。コードが動く入口は、ユーザーが送ったトランザクションか、ノード自身がブロックの処理の始めや終わりに決まったコントラクトを呼ぶ場合だけです。後者の例には、合意の仕組みが使う値をコントラクトに書き込む呼び出しがあり、Ethereum の仕様変更の提案（EIP、Ethereum Improvement Proposal）の [EIP-4788](https://eips.ethereum.org/EIPS/eip-4788) で決まっています。

---

### 実行の仕組み

前の節の命令の実行ループが、1 つのフレームの中で何を読み書きするのかを見ます。

#### スタック

EVM はスタックマシン（stack machine）です。命令は、値をスタックから取り出し、計算結果をスタックに積みます。レジスタはありません。以下は、`PUSH1 2` `PUSH1 3` `ADD` を順に実行した時のスタックです。

{{< figure src="images/evm_stack.webp" alt="3 つの段階のスタック。PUSH1 2 の後は 2 だけ、PUSH1 3 の後は 2 の上に 3、ADD の後は 5 だけ。2 段目から 3 段目への矢印の上に「2 と 3 を取り出す」。下に「1 要素は 256 ビットの語、最大 1,024 要素」" caption="PUSH1 2・PUSH1 3・ADD でのスタックの変化" align="center" >}}

スタックの 1 要素（語、word）は 256 ビットで、最大 1,024 要素まで積めます。256 ビットあれば、32 バイトの[ハッシュ値](../hash-function/)も、20 バイトのアドレスも 1 語に収まります。整数の演算は 2 の 256 乗で折り返し、符号付きの命令（SDIV、SLT など）だけが 2 の補数として解釈します。

<br>

#### データ領域と寿命

EVM のコードが読み書きする場所は、スタックの他に複数あります。違いは、寿命と、誰に属するかです。

{{< figure src="images/evm_data_areas.webp" alt="2 つの枠。青い「フレームに属する」に stack（フレームの終わりまで、256 ビットの語）、memory（フレームの終わりまで、バイト列）、calldata（フレームの終わりまで、読むだけ）、returndata（次に子を呼ぶまで）。黄土色の「アカウントに属する」に transient storage（トランザクションの終わりまで）、storage（書き換えるまで）、code（デプロイ後は不変、読むだけ）" caption="EVM が読み書きする場所と、その持ち主" align="center" >}}

左のフレームに属する 4 つは、フレームが終わると消えます。memory は作業用のバイト列で、使った分だけガスが掛かります。calldata は呼び出しの入力のバイト列で、読むだけです。returndata は直近に呼んだ子のフレームが返したバイト列です。

右のアカウントに属する 3 つのうち、storage と transient storage は、どちらも 256 ビットのキーから 256 ビットの値への対応表です。時間軸に並べると、以下のようになります。

{{< figure src="images/evm_lifetimes.webp" alt="1 件のトランザクションの時間軸。フレーム A はトランザクションの開始から終わりまで、フレーム B（CALL）は途中の一部だけ続く。A と B の stack・memory はそれぞれのフレームの間だけ青い帯で続く。transient storage は TSTORE の時点からトランザクションの終わりまで黄土色の帯で続き、終わりに赤い×がある。storage の緑の帯はトランザクションの前から次のトランザクションまで続く" caption="トランザクション 1 件の間に各領域が残る期間" align="center" >}}

memory はフレームごとに新しく作られます。子のフレームに渡すのは、親の memory の一部をコピーした calldata で、子は親の memory を直接は触れません。

storage は、次のトランザクションにも残る唯一の領域です。2 の 256 乗個の場所を確保しているわけではなく、0 以外の値を書いたキーだけを状態に持ちます。Solidity の変数がどのキー（slot）に置かれるかは、EVM ではなくコンパイラの規則で決まります（[Solidity の storage layout](https://docs.soliditylang.org/en/v0.8.28/internals/layout_in_storage.html)）。この配置が問題になる例は [Upgradeable Proxy](../upgradeable-proxy/#storage-の衝突) のノートで説明しています。

transient storage は、2024 年 3 月の更新（Cancun）で [EIP-1153](https://eips.ethereum.org/EIPS/eip-1153) が加えた領域で、TSTORE と TLOAD で読み書きします。同じトランザクションの中なら複数のフレームから見えますが、トランザクションが終わると消えます。「処理の途中である」ことを示す旗のように、トランザクションの間だけ要る値に向いています。

<br>

#### プログラムカウンタと JUMPDEST

コードはバイト列で、プログラムカウンタ（PC）は次に実行するバイトの位置です。通常は 1 進みますが、`PUSH1`〜`PUSH32` は後ろに続く 1〜32 バイトを値（即値）として読み、その分 PC を飛ばします。

分岐には JUMP と JUMPI を使い、飛び先は JUMPDEST（0x5b）でなければなりません。しかし、0x5b のバイトがあればどこでも良いわけではありません。

{{< figure src="images/evm_jumpdest.webp" alt="コード 60 5b 5b 00 の 4 バイト。PC 0 の 60 は PUSH1、PC 1 の 5b は黄土色で PUSH1 の即値、PC 2 の 5b は JUMPDEST、PC 3 の 00 は STOP。PC 0 と 1 は「1 つの命令: PUSH1 0x5b」。「1 へ JUMP」は赤い×、「2 へ JUMP」は緑のチェック" caption="即値の中の 0x5b と、本物の JUMPDEST" align="center" >}}

上記の図の PC 1 の 0x5b は PUSH1 の即値で、命令ではありません。そのため、PC 1 に飛ぶと失敗し、PC 2 に飛ぶと成功します。クライアントは、コードを先頭から読んで実行の前に、即値の範囲を除いた飛び先の一覧を作ります（geth の [`analysis_legacy.go`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/analysis_legacy.go#L75-L118)）。

---

### 命令とガス

冒頭で、命令にはガスの値段が付いていると書きました。EVM のコードはループで任意の回数の計算を書けるので、コードが止まるかどうかを事前に判定できません。そこで EVM は、全ての命令に値段を付け、送り主が gas limit で用意した量を使い切ったら例外として止めます。止まらないコードも、ガスを使い切った時点で終わります。

命令の値段は、計算の重さだけでなく、ノードのディスクや状態の大きさへの負担で決まります。以下は、Osaka の主な命令のガスを対数の目盛りで並べた図です（execution-specs の [`gas.py`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/vm/gas.py#L30-L199)）。

{{< figure src="images/evm_gas_ladder.webp" alt="対数の横軸に命令のガスの横棒を並べた図。青い「計算」は ADD, LT, AND が 3、MUL, DIV が 5、JUMPI が 10。黄土色の「状態・ディスク・レシート」は TLOAD, warm SLOAD が 100、LOG0 が 375、cold SLOAD が 2,100、cold の CALL 先が 2,600、SSTORE 0 → 0 以外が 20,000、CREATE が 32,000" caption="Osaka の主な命令のガス（対数軸）" align="center" >}}

ADD の 3 に比べて、storage やアカウントに触る命令（図の状態・ディスク・レシート）は約 30 倍から 1 万倍です。SLOAD と SSTORE は storage を読む・書く命令、TLOAD は transient storage を読む命令、LOG0 はログを出す命令、CREATE はコントラクトを作る命令です。計算の命令は 3〜10 です。

図の cold と warm は、2021 年 4 月の更新（Berlin）で [EIP-2929](https://eips.ethereum.org/EIPS/eip-2929) が加えた区別です。同じトランザクションの中で初めて触るアカウントや storage の slot（cold）は高く、2 回目から（warm）は安くなります。入力の大きさで変わる式を含めた一覧は、以下に畳みました。`w` はバイト数を 32 で割って切り上げた語数です。

<br>

<details>
<summary>Osaka の主な命令のガス</summary>

| 分類 | 代表的な命令 | ガス |
| --- | --- | --- |
| 算術・比較・ビット | ADD、LT、AND、SHR | 3 |
| | MUL、DIV、CLZ | 5 |
| | EXP | 10 + 指数のバイト数 × 50 |
| ハッシュ | KECCAK256 | 30 + 6w + memory の拡張 |
| memory | MLOAD、MSTORE | 3 + memory の拡張 |
| 分岐 | JUMP / JUMPI | 8 / 10 |
| storage | SLOAD | 初回（cold）2,100、2 回目以降（warm）100 |
| | SSTORE | 0 から 0 以外にすると 20,000、0 以外から別の 0 以外にすると 2,900（どちらも cold なら + 2,100）など |
| transient | TLOAD、TSTORE | 100 |
| ログ | LOG0〜LOG4 | 375 + topic の数 × 375 + データのバイト数 × 8 |
| 呼び出し | CALL など | アカウントの参照 2,600 / 100、ETH を送るなら + 9,000 など |
| 作成 | CREATE | 32,000 + 初期化コードの語数 × 2 など |

</details>

<br>

#### 実験の環境

ここからは、ガスの式を実際のノードで確認します。実験は、手元のコンテナで動かした開発用ノードの Anvil を Osaka の規則に固定して行い、公開のネットワークには繋ぎません。

<br>

<details>
<summary>実験の環境の詳細</summary>

Anvil 1.7.1 を [Docker](https://www.docker.com/) の専用ネットワークで起動し、`--hardfork osaka` で規則を Osaka に固定しました。ホストのポートは公開しません。使う秘密鍵は、Anvil が既定で用意するテスト用の公開された鍵だけです。

Solidity は solc 0.8.28（optimizer 無し、evmVersion は cancun）でコンパイルしています。optimizer はコードを小さく・安くする最適化で、切ると命令がソースの形に近くなります。evmVersion はコンパイラが使う命令の範囲の指定で、cancun 向けのコードは Osaka のノードでもそのまま動きます。

</details>

<br>

ノードへの問い合わせには、2 つの API を使います。`eth_call` は、トランザクションを作らずにノードにコードを試しに実行させ、返り値だけを受け取る API で、状態は変わりません。`debug_traceTransaction` は、送ったトランザクションで実行された命令とそのガスを 1 つずつ返す API です。実験コードは [probe.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/probe.py) で、コントラクトと手で組み立てたバイトコードは学習用で、監査していません。

<br>

#### memory の拡張

memory は使った最大の位置までを語数 `a` で数え、累計で `3a + floor(a² / 512)` のガスが掛かります。命令が memory を広げた時は、広げた後と前の累計の差を払います（execution-specs の [`calculate_memory_gas_cost`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/vm/gas.py#L253-L276)）。

この式を確認するため、残りのガスを積む GAS 命令で MLOAD（memory から 1 語読む命令）の前後を挟んだ短いコードを `eth_call` で実行し、差から拡張の分を求めました。同じ位置を 2 回読み、2 回目には拡張が無いことも見ています。

```text
size_bytes | 1st MLOAD extra | 2nd MLOAD extra | formula 3a + a*a//512
        32 |               3 |               0 | 3
      1024 |              98 |               0 | 98
     32768 |            5120 |               0 | 5120
    131072 |           45056 |               0 | 45056
```

<br>

<details>
<summary>測定に使ったコード（probe.py の抜粋）</summary>

`call(code)` は `eth_call` でコードを実行して返り値の 16 進文字列を返す関数、`words` はそれを 32 バイトずつの整数に分ける関数です。`code` は命令を 16 進で手書きしたバイトコードです。

```python
# GAS, MLOAD(off), POP, GAS, MLOAD(off), POP, GAS.
# Each gap = PUSH3(3) + MLOAD(3) + POP(2) + GAS(2) = 10, plus memory expansion.
def c_mem(size):
    a = (size + 31) // 32
    return 3 * a + a * a // 512

for size in (32, 1024, 32768, 131072):
    off = f'{size - 32:06x}'
    code = ('5a' f'62{off}' '51' '50' '5a' f'62{off}' '51' '50' '5a'
            '604052' '602052' '600052' '60606000f3')
    g0, g1, g2 = words(call(code))
    first, second = g0 - g1 - 10, g1 - g2 - 10
    assert first == c_mem(size) and second == 0
```

</details>

<br>

4 つの大きさの全てで、式と実測が一致しました。2 回目の拡張分は 0 で、確保済みの範囲を読むたびに払うわけではありません。

{{< figure src="images/evm_memory_gas.webp" alt="横軸が memory の大きさ（バイト）、縦軸が 0 から広げるガス。青い破線の直線の項 3a は直線で、黄土色の合計 3a + a²/512 は大きくなるほど上に反る。実測の黒い点 32,768 バイト → 5,120 と 131,072 バイト → 45,056 が曲線に乗っている" caption="memory を広げるガスの式と実測" align="center" >}}

32 KiB までは直線の項（3a）が大半ですが、128 KiB では二次の項（32,768）が直線の項（12,288）の 2.7 倍になります。memory を大きく使うほど 1 バイトあたりが高くなるので、巨大な memory を確保してノードのメモリを使い切らせる攻撃は割に合いません。

<br>

#### トランザクション全体のガス

命令のガスの外側にも、取引ごとに掛かる分があります。最初の節の図の intrinsic gas は、宛先のある取引なら、基本の 21,000 に、取引の `data` の 0 のバイトごとに 4、0 以外のバイトごとに 16 を足した値です。取引でコントラクトを作成（デプロイ）する場合などは、その分も足します（execution-specs の [`calculate_intrinsic_cost`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/transactions.py#L598-L666)）。

2025 年 5 月の更新（Prague）からは、[EIP-7623](https://eips.ethereum.org/EIPS/eip-7623) の下限（floor）もあります。命令をほとんど実行せずに大量の `data` を載せる取引で、ブロックのデータが大きくなりすぎるのを抑えるためのものです。`data` の 0 のバイトは 1、0 以外のバイトは 4 と数え、その合計に 10 を掛けて 21,000 に足した値 `21000 + 10 × (0 のバイト数 + 4 × 0 以外のバイト数)` を下限とし、使ったガスがこれを下回る時は、この値まで引き上げます。

storage の値を 0 に戻すと、払い戻し（refund）が付きます。払い戻しは取引の最後にまとめて行われ、2021 年 8 月の更新（London）の [EIP-3529](https://eips.ethereum.org/EIPS/eip-3529) から、払い戻し前のガスの 5 分の 1 が上限です。実行中に使えるガスは増えません。

<br>

値を 1 つ保存してイベント（後の節で説明するログ）を出すだけの次のコントラクトで、この内訳を確認しました。

```solidity
// SPDX-License-Identifier: CC0-1.0
// Educational example for the EVM note. Not audited.
pragma solidity 0.8.28;

contract Dispatcher {
    uint256 public value;
    event Changed(address indexed sender, uint256 value);

    function set(uint256 x) external {
        value = x;
        emit Changed(msg.sender, x);
    }
}
```

`set(42)`、`set(43)`、`set(0)` を別々の取引で送り、`debug_traceTransaction` で命令ごとのガスを合計しました。以下は、その内訳を横棒にした図で、数値の全体は [summary.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/output/summary.txt) にあります。

{{< figure src="images/evm_tx_gas.webp" alt="3 件の取引のガスの横棒。どれも左の灰色の intrinsic gas が約 21,200 を占める。set(42) は青い SSTORE が 22,100 と長く、gasUsed 45,289。set(43) は SSTORE 5,000 で gasUsed 28,189。set(0) は SSTORE 5,000 の後、緑の払い戻し 4,800 が差し引かれて gasUsed 23,377。赤い縦線の EIP-7623 の下限は約 21,500 で、どの取引も上回っている" caption="set(42)・set(43)・set(0) の gasUsed の内訳" align="center" >}}

`set(42)` は、0 の slot に 0 以外を書くので 20,000 に cold の 2,100 が加わり、SSTORE（storage に書く命令）だけで 22,100 です。`set(43)` は 0 以外から別の 0 以外への書き換えです。SSTORE の値段は、書き換えそのものの 2,900 と、slot に初めて触る cold の 2,100 の和です。

cold と warm の区別は取引ごとにやり直すので、別の取引の `set(43)` でも再び cold になり、2,900 + 2,100 = 5,000 になりました（値は [EIP-2929](https://eips.ethereum.org/EIPS/eip-2929) の Specification）。

`set(0)` は同じ 5,000 を払った後、0 以外の slot を 0 に戻した時の払い戻し 4,800（EIP-3529 の値）を受け、28,177 から 23,377 に下がっています。払い戻しの上限は 28,177 の 5 分の 1（5,635）なので、全額が戻りました。

なお、払い戻し前の 28,177 が `set(43)` の 28,189 より 12 少ないのは、引数の 0 が calldata の 0 のバイトになり、intrinsic gas が 1 バイトあたり 16 から 4 に下がるからです。手数料は、この gasUsed に 1 ガスあたりの単価を掛けた額です。単価の決まり方（[base fee と priority fee](../gas-eip-1559/)）は [Ethereum Transaction](../ethereum-transaction/) で説明しています。

---

### calldata と ABI

前の節では `set(42)` を取引で送りました。しかし、EVM は関数名も引数の型も知りません。コードに渡るのは、取引の `data` 欄のバイト列（calldata）だけです。このバイト列を関数呼び出しとして解釈する取り決めが ABI（Application Binary Interface）です。

[Solidity の ABI 仕様](https://docs.soliditylang.org/en/v0.8.28/abi-spec.html#function-selector)では、`set(uint256)` のような関数のシグネチャ（関数名と引数の型を並べた文字列）から、Ethereum が使うハッシュ関数 Keccak-256 でハッシュ値を求め、その先頭 4 バイトを selector とします。その後ろに引数を 32 バイト単位で並べます。`set(42)` の calldata は、selector の `60fe47b1` と、42（0x2a）を 32 バイトに伸ばした値の 36 バイトです。

```text
calldata of set(42): 60fe47b1 000000000000000000000000000000000000000000000000000000000000002a
```

コンパイルされた `Dispatcher` のコードの先頭には、この selector を見て関数の本体に飛ぶ部分があります。以下は、その流れを図にしたものです。

{{< figure src="images/evm_dispatcher.webp" link="images/evm_dispatcher.webp" alt="上段は calldata（36 バイト）で、青い 4 バイトの 60fe47b1 と黄土色の 32 バイトの 00 … 00 2a (42)。中段は CALLDATALOAD 0 → SHR 224 → 60fe47b1 で、取り出した 60fe47b1 から下段に矢印。下段は EQ 3fa4f245（value()）が「否」、EQ 60fe47b1（set(uint256)）が「一致」で JUMPI → pc 86 に進み、SSTORE、LOG2、STOP の set() の本体に至る。どれとも不一致なら REVERT。左下に「EVM は set という名前を見ない」" caption="calldata の selector から set() の本体に至る分岐" align="center" >}}

CALLDATALOAD で calldata の先頭の 32 バイトを読み、224 ビット右にずらして（SHR）先頭 4 バイトだけを残します。それを `value()` の `3fa4f245`（`uint256 public value` から Solidity が自動で作る読み出し用の関数）、`set(uint256)` の `60fe47b1` と順に比べ（EQ）、一致した所の JUMPDEST に飛びます。

図の pc 86 は飛び先の位置で、16 進では 0x56 です（下に畳んだ抜粋の `PUSH2 0x0056`）。どれにも一致しなければ REVERT します。

`set(42)` の取引を `debug_traceTransaction` でたどると、実行された命令もこの順でした。Foundry の [cast](https://getfoundry.sh/cast/overview) の `cast disassemble` で命令に戻した該当部分は、以下に畳みました。

<br>

<details>
<summary>selector を比べる部分の抜粋（左が PC）</summary>

```text
00000011: PUSH1 0x04
00000013: CALLDATASIZE
00000014: LT
00000015: PUSH2 0x0034
00000018: JUMPI
00000019: PUSH0
0000001a: CALLDATALOAD
0000001b: PUSH1 0xe0
0000001d: SHR
0000001e: DUP1
0000001f: PUSH4 0x3fa4f245
00000024: EQ
00000025: PUSH2 0x0038
00000028: JUMPI
00000029: DUP1
0000002a: PUSH4 0x60fe47b1
0000002f: EQ
00000030: PUSH2 0x0056
00000033: JUMPI
00000034: JUMPDEST
00000035: PUSH0
00000036: PUSH0
00000037: REVERT
```

全体は [dispatcher.disasm.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/output/build/dispatcher.disasm.txt) にあります。

</details>

<br>

この直線の比較は、関数が少なく optimizer を使わない場合の形です。optimizer の設定は、関数を振り分ける部分の二分探索の大きさなどを変えます（[solc の optimizer options](https://docs.soliditylang.org/en/v0.8.28/using-the-compiler.html#optimizer-options)）。

どちらの場合も、EVM が比べているのは 4 バイトの数値だけです。そのため、別のシグネチャから同じ 4 バイトが出る衝突も起こり得ます。呼び出しを別のコントラクトのコードに転送するプロキシ（DELEGATECALL の節で触れます）では、呼び先の関数と管理用の関数の selector が重ならないように設計します（[Upgradeable Proxy](../upgradeable-proxy/#プロキシの型)）。

<br>

#### イベントとログ

`set` の中の `emit Changed(msg.sender, x)` は、LOG2 命令になります。ログはレシートに残る一方通行の出力で、storage とは違い、コントラクトが後から読み返す命令はありません。アプリはノードの API でログを取得し、処理結果を追跡します。

{{< figure src="images/evm_log.webp" alt="set(42) の LOG2: 1,381 ガス = 375 + 2 × 375 + 8 × 32 バイト。青い帯の address（Dispatcher）、topic0（keccak(Changed(...))）、topic1（sender（indexed））と、黄土色の data（value = 42）。address と 2 つの topic から右の灰色の bloom（2048 ビット）に矢印があり、data からは無い。下に「data は bloom に入らない」" caption="set(42) の LOG2 の中身と bloom" align="center" >}}

上記の図の topic0 は、イベントのシグネチャ `Changed(address,uint256)` の Keccak-256 の 32 バイト全体で、関数の selector のように 4 バイトに切りません。`indexed` を付けた引数は topic1 以降に入り、付けていない引数は data に ABI の形で入ります。実験の LOG2 は、図の式どおり 1,381 ガスでした。

```text
topic0 of Changed: 0xb52dda022b6c1a1f40905a85f257f689aa5d69d850e49cf939d688fbe5af5946
```

ブロックのヘッダーとレシートには、2,048 ビットの bloom（bloom filter。値が含まれていないことを素早く判定するためのビット列）があり、ログのアドレスと topic から 3 ビットずつ立てます（geth の [`bloom9.go`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/types/bloom9.go#L107-L160)）。

bloom にビットが無ければ、そのブロックに該当のログが無いと分かり、検索を速くできます。data は bloom に入らないので、値でログを探すなら `indexed` の引数にする必要があります。

---

### 呼び出しの文脈

ここまでは 1 つのコントラクトの中を見ました。コントラクトが別のコントラクトを呼ぶと、最初の節で見た子のフレームが作られます。どの命令でも、子が実行するのは呼び先のコードです。しかし、子の中で `msg.sender`（呼び出し元）・`msg.value`（送られた ETH）・`address(this)`（storage の持ち主）が何になるかは、使う命令で決まります。

| 命令 | storage の持ち主 | `msg.sender` | `msg.value` |
| --- | --- | --- | --- |
| CALL | 呼び先 | 呼び出し元 | 指定した額（送金する） |
| DELEGATECALL | 呼び出し元 | 呼び出し元の `msg.sender` | 呼び出し元の `msg.value` |
| STATICCALL | 呼び先 | 呼び出し元 | 0 |
| CALLCODE（古い命令） | 呼び出し元 | 呼び出し元 | 指定した額（自分宛てなので残高は動かない） |

CALLCODE は最初の版からある古い命令で、今は代わりに DELEGATECALL（[EIP-7](https://eips.ethereum.org/EIPS/eip-7)）を使います。表の 4 つのうち、状態を変更できないのは STATICCALL だけです。

STATICCALL は 2017 年 10 月の更新（Byzantium）の [EIP-214](https://eips.ethereum.org/EIPS/eip-214) で加わり、storage への書き込み、ログ、コントラクトの作成、ETH を送る CALL などを禁止します（TSTORE も EIP-1153 で同じ扱いになりました）。この禁止は孫のフレームにも引き継がれます。

<br>

#### 3 つの命令の比較

同じ `Caller` から同じ `Target` を 3 通りに呼び、`Target` の中で見えた値を記録しました。`Target.record()` は slot 0 の `count` を 1 増やし、自分が見た `msg.sender`・`address(this)`・`msg.value` を返します。EOA は `Caller.run()` を 7 wei 付きで呼び、CALL では 3 wei を送ります。

<br>

<details>
<summary>Context.sol の全体</summary>

```solidity
// SPDX-License-Identifier: CC0-1.0
// Educational example for the EVM note. Not audited.
pragma solidity 0.8.28;

// Target and Caller share the same storage layout (slot 0 = count).
contract Target {
    uint256 public count;

    // Writes storage, then reports what the running code sees.
    function record() external payable returns (address sender, address self, uint256 value) {
        count += 1;
        return (msg.sender, address(this), msg.value);
    }

    // Same report without writing storage.
    function peek() external view returns (address sender, address self, uint256 value) {
        return (msg.sender, address(this), 0);
    }
}

contract Caller {
    uint256 public count;
    event Seen(string mode, bool ok, address sender, address self, uint256 value);

    // Called with msg.value = 7 wei.
    function run(address target) external payable {
        bytes memory rec = abi.encodeCall(Target.record, ());
        (bool ok, bytes memory ret) = target.call{value: 3}(rec);
        _report("CALL record", ok, ret);
        (ok, ret) = target.delegatecall(rec);
        _report("DELEGATECALL record", ok, ret);
        (ok, ret) = target.staticcall(rec);
        _report("STATICCALL record", ok, ret);
        (ok, ret) = target.staticcall(abi.encodeCall(Target.peek, ()));
        _report("STATICCALL peek", ok, ret);
    }

    function _report(string memory mode, bool ok, bytes memory ret) private {
        if (!ok) {
            emit Seen(mode, false, address(0), address(0), 0);
            return;
        }
        (address sender, address self, uint256 value) = abi.decode(ret, (address, address, uint256));
        emit Seen(mode, true, sender, self, value);
    }
}
```

</details>

<br>

```text
== Caller.run(target) sent by the EOA with 7 wei ==
mode                | ok | msg.sender | address(this) | msg.value
CALL record         | 1  | Caller     | Target        | 3
DELEGATECALL record | 1  | EOA        | Caller        | 7
STATICCALL record   | 0  | -          | -             | 0
STATICCALL peek     | 1  | Caller     | Target        | 0
storage slot 0 (count) after: Caller=1, Target=1
balance after (wei): Caller=4, Target=3
```

{{< figure src="images/evm_call_context.webp" link="images/evm_call_context.webp" alt="3 つの枠に CALL・DELEGATECALL・STATICCALL。どの枠でも、上の Caller から下の Target に矢印があり、青く塗られているのは Target のコード。CALL では Target の slot 0 が黄土色で書き込まれ、msg.sender = Caller、msg.value = 3 wei。DELEGATECALL では Caller の slot 0 が黄土色で、msg.sender = EOA、msg.value = 7 wei。STATICCALL では Target の slot 0 が赤で、SSTORE が失敗、ok = 0。下に凡例: 青は動いたコード、黄土色は書き込まれた slot、赤は書き込めず失敗" caption="CALL・DELEGATECALL・STATICCALL の文脈の違い" align="center" >}}

DELEGATECALL では、`Target` のコードが動いたのに、`address(this)` は `Caller` で、増えたのも `Caller` の `count` でした。`msg.sender` と `msg.value` も、`Caller` が受け取った EOA と 7 wei のままです。この性質を使うのがプロキシで、仕組みと storage の衝突は [Upgradeable Proxy](../upgradeable-proxy/) で説明しています。

STATICCALL は、書き込む `record()` では失敗し、読むだけの `peek()` では成功しました。失敗しても `run()` の取引は成功しています。この理由は最後の節で説明します。なお、Solidity が別のコントラクトの `view` 関数を呼ぶ時は STATICCALL を使います（[Solidity の view functions](https://docs.soliditylang.org/en/v0.8.28/contracts.html#view-functions)）。

<br>

#### 子のフレームの終わり方

親は子を呼ぶ時に、自分の残りのガスの一部を子に渡します。子のフレームの終わり方は 4 通りあり、どれで終わったかで、状態の変更と渡したガスの扱いが変わります。

{{< figure src="images/evm_frame_exit.webp" alt="4 行の比較。STOP / RETURN は、子に渡したガスの棒が灰色の「使った分」と青い「返す」に分かれ、状態は「残す」、親へは 1 + データ。REVERT も「使った分」と「返す」で、状態は「取り消す」、親へは 0 + データ。例外は棒の全体が黄土色の「全て失う」で、取り消す、0。始められないは点線の棒で「親に残る」、実行しない、0。下に「『残す』の変更も、親が後で失敗すれば取り消される」" caption="フレームの 4 通りの終わり方と、状態・ガスの扱い" align="center" >}}

STOP と RETURN は成功で、状態の変更を残し、使わなかったガスを親に返します。REVERT は失敗で、そのフレームの中の状態の変更（storage・transient storage への書き込み、ETH の移動、ログなど）を全て取り消します（undone）。ただし、残りのガスは返し、失敗の理由のデータを親に渡せます。

例外は、ガス切れ、無効な命令、JUMPDEST 以外への JUMP などで、変更を取り消したうえで渡されたガスを全て失います。「始められない」は、呼び出しの深さの上限（1,024 段）や残高不足で子を始められない場合で、渡そうとしたガスは親に残ります。

右端の「親へ」の列は、CALL の結果として親のスタックに積まれる値（成功なら 1、失敗なら 0）と、親に返すデータです。最上位のフレーム（取引が直接呼んだフレーム）の場合は、この成否が取引の結果になります。

図の下の注記のとおり、「残す」とした変更も確定ではなく、親が後で失敗すれば、親の変更と一緒に取り消されます。

<br>

#### 63/64 ルール

CALL で子に渡せるガスには上限があります。2016 年 10 月の更新（Tangerine Whistle）の [EIP-150](https://eips.ethereum.org/EIPS/eip-150) から、CALL 自身のコストを引いた残りを `g` として、子に渡せるのは最大で `g - floor(g / 64)` です。

親には少なくとも 64 分の 1 が残り、子が全てのガスを使い切っても、親は後処理を続けられます（execution-specs の [`max_message_call_gas`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/vm/gas.py#L360-L377)）。

`eth_call` に 1,000 万ガスを渡し、入口で残りのガスを返すだけの子コントラクトを CALL して、式どおりの量が渡るかを確認しました。子は初めて触るアカウントなので cold の 2,600 が掛かり、返り値を書く memory の 1 語の拡張で 3 が加わります。

{{< figure src="images/evm_call_split.webp" alt="上に g = 9,946,370（CALL の前）− 2,603（CALL の費用）= 9,943,767。その下の横棒の大部分が青い「子が受け取る 9,788,396（63/64）」で、右端の細い黄土色が「親に残る 155,371（1/64）」。下に「10,000 を要求 → 子は 10,000 を受け取る（上限 9,788,364 より小さい）」" caption="CALL で子に渡るガスの 63/64 の分け方" align="center" >}}

全てを要求した時、子が受け取ったガスは、`g` から 64 分の 1 を引いた値と 1 ガスも違いませんでした。10,000 だけを要求した時は、上限より小さいので要求どおりに渡っています（この時は CALL の前の命令が少し違い、残りのガスが 33 少ないので、上限も 9,788,364 と少し下がります）。

<br>

<details>
<summary>測定に使ったコード（probe.py の抜粋）</summary>

`deploy` は初期化コードを送ってコントラクトを作る関数、`initcode_for` は実行用のコードを返す初期化コードを作る関数です。

```python
callee = deploy(me, initcode_for('5a5f5260205ff3'))  # GAS PUSH0 MSTORE PUSH1 32 PUSH0 RETURN
for label, gas_arg, push_cost in (('all', '5a', 2), ('10000', '612710', 3)):
    # GAS; PUSH1 32; PUSH0 x4; PUSH20 callee; <gas arg>; CALL; POP; MSTORE(32, first GAS); RETURN(0, 64)
    code = '5a' '6020' '5f5f5f5f' '73' + callee[2:].lower() + gas_arg + 'f1' '50' '602052' '60405ff3'
    ret, g0 = words(call(code))
    before = g0 - (3 + 2 * 4 + 3 + push_cost)   # gas available when CALL starts
    costs = 2600 + 3                             # cold account access + 1 word of memory for the return data
    limit = (before - costs) - (before - costs) // 64
    entry = ret + 2
    requested = before - costs if label == 'all' else 10000
    assert entry == min(requested, limit)
```

</details>

<br>

続いて、自分自身を `this.down(depth - 1)` で呼び続ける Solidity のコントラクトで、深さごとに入口のガスを測りました。

```solidity
// Calls itself `depth` times and returns gasleft() at the entry of the deepest frame.
contract Deep {
    function down(uint256 depth) external returns (uint256) {
        if (depth == 0) return gasleft();
        return this.down(depth - 1);
    }
}
```

{{< figure src="images/evm_depth_gas.webp" alt="横軸が呼び出しの深さ 0〜40、縦軸が入口のガス。青い実測の gasleft() の点が約 1,000 万から約 529 万まで下がり、黄土色の g₀ × (63/64)^深さ の線とほぼ重なる。下に「成功する最も深い呼び出しは down(322)（残り 5,487）、深さの上限 1,024 には届かない」" caption="呼び出しの深さと入口のガス（実測と式）" align="center" >}}

1 段深くなるごとに、入口のガスは 0.9843 倍になりました。63/64 は 0.984375 で、残りの差は 1 段ごとの関数呼び出しの準備に使った分です。

1,000 万ガスで成功した最も深い呼び出しは `down(322)` で、そこでの残りは 5,487 でした。0.9843 倍だけで見積もった約 6 万より少ないのは、1 段ごとにほぼ一定の量を準備に使うので、残りが少ない深い所ほどその分の割合が大きくなるからです。EVM には呼び出しの深さを 1,024 までとする上限もあります。しかし、渡せるガスが段ごとに減るので、通常は深さの上限より先にガスが足りなくなります。

<br>

#### 再入

呼び出しの文脈で最も事故が多いのが[再入（reentrancy）](../reentrancy/)です。A が B を CALL すると、A のフレームは B が終わるまで途中で止まっています。その間に B が A を呼び返すと、A のコードが、最初の A がまだ更新していない storage を読んで動きます。以下は、A が「残高を読んで送金し、その後で残高を 0 にする」コードだった場合の時間の流れです。

{{< figure src="images/evm_reentrancy.webp" alt="3 行の時間軸。A（1 回目）は青い「残高 10 を読む」、黄土色の「10 を送る CALL の途中」、青い「残高に 0 を書く」と続く。CALL の途中で B が「A を呼び返す」を実行し、A（2 回目）の青い「また 10 を読み、送る」に矢印が下りる。その右に赤い×。下に「×: 0 になる前の残高で 2 回目の送金が起きる（並列ではなく、フレームの入れ子）」" caption="1 本のスレッドの中で起きる再入" align="center" >}}

上記の図では、1 回目の送金の途中で呼び返された A が、まだ 0 になっていない残高 10 を読み、もう一度 10 を送ってしまいます。並列に動くスレッドは無く、同期的な呼び出しの入れ子だけで起きる問題です（[Solidity の Security Considerations](https://docs.soliditylang.org/en/v0.8.28/security-considerations.html#reentrancy)）。対策は、外部を呼ぶ前に自分の状態を更新しておくことと、前に見た transient storage などに「処理中」の旗を置いて呼び返しを拒むことです。

---

### 失敗の扱い

最後に、ここまでに出てきた失敗が、取引の結果としてどう残るかをまとめます。取引が失敗する場所は、最初の節の 3 段の入れ子のうち 2 つです。

{{< figure src="images/evm_failure_kinds.webp" alt="左から取引、灰色の検査（署名・nonce・前払い）、青いコードの実行（EVM のフレーム）、右端に縦長のブロックの枠。検査から点線で下に降りた先は赤い×の拒否で、ブロックに入らない、nonce も残高も不変。コードの実行から下に降りた黄土色のエラー / REVERT は状態を取り消し、矢印でブロックの中の status 0（nonce + 1、手数料は払う）に入る。成功（矢印のみ）はコードの実行からブロックの status 1（nonce + 1）に入る" caption="取引が失敗する 2 つの場所と、ブロックへの残り方" align="center" >}}

署名が不正、nonce が合わない、最大の手数料（gas limit × 送り主が許す単価の上限）と送る額の合計が残高に足りない取引は、外側の検査で拒否され、ブロックに入りません。nonce も残高も変わりません。

一方で、検査を通った取引がコードの実行中に失敗した場合は、ブロックに入り、レシートの `status` が 0 になります。状態の変更は取り消されますが、nonce は進み、使ったガスの手数料は払います。例えば、`Dispatcher` にどの selector にも一致しない `0xdeadbeef` を送った取引は、REVERT して `status=0` で終わりました。

```text
unknown selector 0xdeadbeef: status=0
```

<br>

ただし、子のフレームの失敗は、そのまま取引の失敗にはなりません。「子のフレームの終わり方」の図のとおり、CALL は子の失敗を 0 としてスタックに積むだけで、親はその値を見て処理を続けられます。前の節の STATICCALL の `record()` が失敗しても `run()` の取引が成功したのは、`Caller` が 0 を受け取って記録しただけだからです。

Solidity の高水準の呼び出し（`target.f()`）が子の失敗を親の失敗として伝えるのは、コンパイラが 0 を見て REVERT するコードを入れているからです。2 種類の失敗の違いは、[Smart Contract](../smart-contract/) の実験でも確認しています。

---

### 実験の再現

実験は、リポジトリのルートで次を実行すると約 5 秒で終わり、コンテナとネットワークを削除します。Anvil の時刻を固定しているので、[summary.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/output/summary.txt) は何度実行しても同じです。

```bash
bash content/notes/blockchain-systems/evm/lab/run.sh
```

起動と後始末は [run.sh](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/run.sh)、測定は [probe.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/probe.py)、コントラクトは [Dispatcher.sol](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/Dispatcher.sol)・[Context.sol](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/Context.sol)・[Deep.sol](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/Deep.sol) にあります。

使ったイメージは ghcr.io/foundry-rs/foundry:v1.7.1、ethereum/solc:0.8.28、python:3.13-slim で、digest は [versions.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/output/versions.txt) に記録しています。図の生成元は [figures.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/figures.py) です。
