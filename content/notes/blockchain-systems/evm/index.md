---
title: "EVM - Ethereum の取引を実行する仮想マシンの全体像"
date: 2026-11-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "evm", "smart-contract", "eip", "erc", "gas"]
weight: 17
wrapTables: true
topics: ["Smart Contract"]
---

EVM（Ethereum Virtual Machine）は、Ethereum の取引が呼び出したコントラクトのコードについて、全てのノードで同じ結果になるように実行する仮想マシンです。[Solidity](https://www.soliditylang.org/) などで書いたプログラムはバイトコードにコンパイルされ、EVM がその命令を 1 つずつ実行して、残高や保存領域の値を更新します。

EVM の仕様は 1 つですが、実装は複数あります。Go で書かれた [go-ethereum](https://github.com/ethereum/go-ethereum)（geth）や、Rust で書かれ、開発用のローカルノードである Foundry の Anvil が使う [revm](https://github.com/bluealloy/revm) などが、同じブロックから同じ状態を計算します。仕様としては、Python で書かれていてテストとしても動かせる [execution-specs](https://github.com/ethereum/execution-specs) があります。

以下は、EVM が Ethereum のどこにいるかを示した図です。

{{< figure src="images/evm_concept.svg" alt="上段の黄土色の帯は合意層で、ブロックの列から 1 本を選ぶ。点線の矢印で下段の実行層に「有効か」を問い合わせる。青い実行層の中では、前の状態に取引を入れると EVM が実行し、後の状態とレシートができる。EVM の中には frame 1・2・3 が重なって積まれている" caption="合意層と実行層、その中の EVM とフレームの位置" align="center" >}}

上記の図の合意層は、どのブロックを採用するかを決めますが、命令は実行しません。命令を実行するのは実行層の EVM で、呼び出しが入れ子になるたびにフレームが積み重なります。

<br>

本記事では、EVM を初めて学ぶ開発者に向けて、EVM の全体像を大きい部分から順に説明します。最初に EVM が Ethereum のどの部分を担い、どこを担わないのかを確かめ、コードの実行とデータの寿命、ガスの式へ進みます。

後半では、コントラクトが別のコントラクトを呼ぶ時に `msg.sender` と storage が誰のものになるのか、EIP と ERC のどちらがハードフォークを必要とするのか、関数名を知らない EVM がどのように関数を呼び分けるのかを扱います。

数値は、2026 年 11 月 10 日時点の Ethereum mainnet の規則（[Osaka](https://eips.ethereum.org/EIPS/eip-7607)）のものです。L2 などの EVM 互換のチェーンでは、命令やガスが異なる場合があります。途中の実験は、ローカルの開発用ノードだけで行います。

---

### Ethereum の中での位置

Ethereum は、アカウントごとの残高・nonce・コード・storage を状態として持ち、ブロックに並んだ取引をその状態に順に適用して次の状態を作ります。状態の中身は [Ethereum Account Model](../ethereum-account-model/)、取引の中身は [Ethereum Transaction](../ethereum-transaction/) で説明しています。

2022 年の [The Merge](https://ethereum.org/roadmap/merge/) 以降、Ethereum のノードは、実行層（execution layer）のクライアントと合意層（consensus layer）のクライアントを組み合わせて動きます。合意層は [Proof of Stake](../proof-of-stake/) の投票でブロックを選び、[Finality](../finality/) を決めます。

ブロックの中の取引を実行する仕事は、合意層の仕様では実行層に任せています。Fulu の合意層仕様の [`process_execution_payload`](https://github.com/ethereum/consensus-specs/blob/0393013f4e840ae58b3519e1b4e6a50e74a87f90/specs/fulu/beacon-chain.md#L115-L177) は、親のハッシュや時刻を確かめた後、取引の中身の検証を `verify_and_notify_new_payload` で実行層のクライアントに問い合わせます。

EVM は、PoS の投票やブロックの選択にも関わると思うかもしれません。しかし、EVM が担うのは、実行層の中でもコードを実行する部分だけです。取引の署名と nonce の検査、手数料の前払いと精算は、EVM を呼ぶ前後の状態遷移の処理が行います。

EIP-7702 の委任を設定していない EOA（秘密鍵で操作する通常のアカウント）に ETH を送るだけの取引なら、宛先にコードが無いので、EVM の命令は 1 つも実行されません。

<br>

EVM の仕様は、数式で書かれた [Yellow Paper](https://ethereum.github.io/yellowpaper/paper.pdf) から始まりました。しかし、2026 年 11 月時点で公開されている PDF の表紙は「SHANGHAI VERSION（2025-02-04）」で、2024 年の Cancun 以降のハードフォーク（全ノードが同時に規則を切り替える更新）の変更は入っていません。

最近の規則を確かめるなら、フォークごとにディレクトリが分かれた execution-specs が読みやすく、本記事でも geth と execution-specs のコードはコミットを固定して参照します。

なお、コントラクトは時間が来ても自分では動きません。コードが動く入口は、ユーザーが送った取引か、プロトコルが決めたシステムからの呼び出しです。後者には、ブロックの処理の始めに合意層のブロックの root を書き込む [EIP-4788](https://eips.ethereum.org/EIPS/eip-4788) などがあります（execution-specs の [`process_unchecked_system_transaction`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/fork.py#L657-L726)）。

---

### 取引からコードの実行まで

1 件の取引の処理は、外側から順に「取引の検査と精算」「メッセージ呼び出し」「命令の実行ループ」の 3 段の入れ子になっています。

{{< figure src="images/evm_pipeline.svg" alt="灰色の外枠が取引の処理。左に signature・nonce・intrinsic gas・buy gas の検査、右に refund・pay fee・receipt の精算がある。中央の青い枠がメッセージ呼び出しで、その中で read op → charge gas → execute のループが STOP・RETURN・REVERT・エラーまで回る。下の点線の枠は、CALL で子のフレームを作ること" caption="1 件の取引を処理する 3 段の入れ子" align="center" >}}

メッセージ呼び出し（message call）は、呼び出し元・宛先・入力・渡すガス・送る ETH の組で、EVM はこれを 1 つのフレームとして実行します。フレームの中では、命令を読み、ガスを引き、実行する、を停止まで繰り返します。コードが CALL を実行すると、同じループを持つ子のフレームが作られます。

geth と execution-specs で上記の 3 段に当たる関数は、以下に畳みました。どちらも 2026 年 11 月 10 日前後のコミットに固定したリンクです。

<details>
<summary>3 段に当たる geth と execution-specs の関数</summary>

| 段 | geth（Go） | execution-specs（Python、Osaka） |
| --- | --- | --- |
| 取引の検査と精算 | [`ApplyMessage`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/state_transition.go#L396-L404) → [`execute`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/state_transition.go#L716-L817) | [`process_transaction`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/fork.py#L829-L978) |
| メッセージ呼び出し | [`EVM.Call`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/evm.go#L276-L334) | [`process_message_call`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/vm/interpreter.py#L92-L160) |
| 命令の実行ループ | [`EVM.Run`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/interpreter.go#L96-L137) → [`execUntraced`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/interpreter_gen.go#L18) / [`execTraced`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/interpreter.go#L146) | [`process_message`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/vm/interpreter.py#L221-L302) |

</details>

この入れ子を知っておくと、失敗の種類を分けられます。以下は、取引が失敗する 2 つの場所を示した図です。

{{< figure src="images/evm_failure_kinds.svg" alt="左から tx、灰色の checks（sig, nonce, prepay）、青い code runs、右端に縦長の block の枠。checks から点線で下に降りた先は赤い×の rejected で、not in a block、nonce, fee unchanged。code runs から下に降りた黄土色の error / REVERT は state undone で、矢印で block の中の status 0（nonce + 1、fee paid）に入る。成功は code runs から block の status 1 に入る" caption="取引が失敗する 2 つの場所と、ブロックへの残り方" align="center" >}}

署名が不正、nonce が合わない、前払いのガスが足りない取引は、外側の検査で弾かれ、ブロックに入りません。一方で、検査を通った取引がコードの実行中に失敗した場合は、ブロックに入り、レシートの `status` が 0 になります。後者でも nonce は進み、使ったガスの手数料は払います。この違いは [Smart Contract](../smart-contract/) の実験でも確かめています。

---

### 実行モデル

EVM はスタックマシン（stack machine）です。命令は、値をスタックから取り出し、計算結果をスタックに積みます。レジスタはありません。以下は、`PUSH1 2` `PUSH1 3` `ADD` を順に実行した時のスタックです。

{{< figure src="images/evm_stack.svg" alt="3 つの段階のスタック。PUSH1 2 の後は 2 だけ、PUSH1 3 の後は 2 の上に 3、ADD の後は 5 だけ。2 段目から 3 段目への矢印に pops 2, 3。下に 1 slot = one 256-bit word, up to 1,024 slots" caption="PUSH1 2・PUSH1 3・ADD でのスタックの変化" align="center" >}}

スタックの 1 要素（語、word）は 256 ビットで、最大 1,024 要素まで積めます。256 ビットあれば、Keccak-256 のハッシュ値も、20 バイトのアドレスも 1 語に収まります。

geth は語を `uint256.Int` で持ちます。整数演算は 2 の 256 乗を法として折り返し、符号付きの命令（SDIV、SLT など）だけが 2 の補数として解釈します（geth の [`stack.go`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/stack.go#L27-L30)、[`protocol_params.go`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/params/protocol_params.go#L84)）。

<br>

#### データ領域と寿命

EVM のコードが読み書きする場所は、スタックの他に複数あります。違いは、寿命と、誰に属するかです。

{{< figure src="images/evm_data_areas.svg" alt="2 つの枠。青い belongs to the frame に stack（to frame end, 256-bit words）、memory（to frame end, bytes）、calldata（to frame end, read only）、returndata（until the next child call）。黄土色の belongs to the account に transient storage（until the tx ends）、storage（until overwritten）、code（fixed after deploy, read only）" caption="EVM が読み書きする場所と、その持ち主" align="center" >}}

左の 4 つは、フレームが終わると消えます。memory はバイト単位で読み書きし、拡張は 32 バイト単位で課金されます。calldata は読むだけで、範囲外は 0 として読めます。returndata は直近の子フレームが返したバイト列で、次に子を呼ぶまで残ります。右の transient storage と storage は、どちらも 256 ビットのキーと値の組です。

時間軸に並べると、以下のようになります。

{{< figure src="images/evm_lifetimes.svg" alt="1 件の取引の時間軸。frame A は取引の最初から最後まで、frame B は途中の一部だけ続く。stack と memory はそれぞれのフレームの間だけ青い帯で続く。transient storage は TSTORE の時点から取引の終わりまで黄土色の帯で続き、終わりに赤い×がある。storage の緑の帯は取引の前から次の取引まで続く" caption="1 件の取引の中での各領域の寿命" align="center" >}}

memory はフレームごとに新しく作られます。子のフレームに渡すのは、親の memory の一部をコピーした calldata で、子は親の memory を直接は触れません。

storage は、アカウントごとの 256 ビットのキーから 256 ビットの値への対応表です。2 の 256 乗個の場所を確保しているわけではなく、0 以外の値を書いたキーだけを状態に持ちます。

Solidity の変数がどのキー（slot）に置かれるかは、EVM ではなくコンパイラの規則で、mapping の値は「キーと slot 番号を連結した Keccak-256」の位置に置かれます（[Solidity の storage layout](https://docs.soliditylang.org/en/v0.8.28/internals/layout_in_storage.html)）。この配置が問題になる例は [ERC-1967 / ERC-7201](../upgradeable-proxy/) のノートで説明しています。

transient storage は、2024 年の Cancun で [EIP-1153](https://eips.ethereum.org/EIPS/eip-1153) が加えた領域で、TSTORE と TLOAD で読み書きします。storage と同じキーと値の形で、同じ取引の中なら複数のフレームから見えますが、取引が終わると消えます。

transient storage は memory の別名ではなく、フレームが REVERT した時は storage と同じように書き込みが取り消されます。再入の防止に使うロックの旗のように、取引の間だけ必要な値に向いています。

<br>

#### プログラムカウンタと JUMPDEST

コードはバイト列で、プログラムカウンタ（PC）は次に実行するバイトの位置です。通常は 1 進みますが、`PUSH1`〜`PUSH32` は後ろに続く 1〜32 バイトを即値として読み、その分 PC を飛ばします。

分岐には JUMP と JUMPI を使い、飛び先は JUMPDEST（0x5b）でなければなりません。しかし、0x5b のバイトがあればどこでも良いわけではありません。

{{< figure src="images/evm_jumpdest.svg" alt="コード 60 5b 5b 00 の 4 バイト。PC 0 の 60 は PUSH1、PC 1 の 5b は黄土色で PUSH1 の即値（data）、PC 2 の 5b は JUMPDEST、PC 3 の 00 は STOP。PC 0 と 1 は 1 つの命令 PUSH1 0x5b。JUMP to 1 は赤い×、JUMP to 2 は緑のチェック" caption="即値の中の 0x5b と、本物の JUMPDEST" align="center" >}}

上記の図の PC 1 の 0x5b は PUSH1 の即値で、命令ではありません。そのため、PC 1 に飛ぶと失敗し、PC 2 に飛ぶと成功します。クライアントは、コードを先頭から読んで即値の範囲を除いた飛び先の一覧を事前に作ります（geth の [`analysis_legacy.go`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/analysis_legacy.go#L75-L118)、execution-specs の [`get_valid_jump_destinations`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/vm/runtime.py#L22-L69)）。

<br>

#### 停止と巻き戻し

フレームの終わり方は 4 通りあり、どれを選んだかで状態の変更とガスの扱いが変わります。

{{< figure src="images/evm_frame_exit.svg" alt="4 行の比較。STOP / RETURN は、子に渡したガスの棒が灰色の used と青い back に分かれ、state は kept、returns は 1 + data。REVERT も used と back で、state は undone、returns は 0 + data。exception は棒の全体が黄土色の all consumed で、undone、0。cannot start は点線の棒で kept by the parent、not run、0。下に「kept の変更も、親が後で失敗すれば取り消される」" caption="フレームの 4 通りの終わり方と、状態・ガスの扱い" align="center" >}}

上記の図の exception は、ガス切れ、無効な命令、不正な JUMP などです。cannot start は、呼び出しの深さの上限や残高不足で子を始められない場合で、渡そうとしたガスは親に残ります。REVERT は、残りのガスを返すうえに REVERT のデータを親に渡せる点で、例外と違います。

子のフレームが失敗しても、取引全体が失敗するとは限りません。CALL は失敗を 0 としてスタックに積むだけで、親はその値を見て処理を続けられます。Solidity の高水準の呼び出し（`target.f()`）が失敗を親の失敗として伝えるのは、コンパイラが 0 を見て REVERT するコードを入れているからです。

---

### 命令とガス

EVM のコードは、ループで任意の回数の計算を書けます。そのため、コードが止まるかどうかを事前に判定できません。EVM は、全ての命令に値段（ガス）を付け、取引の送り主が先払いした量を使い切ったら実行を止めることで、この問題を避けています。止まらないコードは、ガスを使い切った時点で例外として終わります。

命令の値段は、計算の重さだけでなく、ノードのディスクや状態の大きさへの負担で決まります。以下は、Osaka の主な命令のガスを対数の目盛りで並べた図です（execution-specs の [`gas.py`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/vm/gas.py#L30-L199)）。

{{< figure src="images/evm_gas_ladder.svg" alt="対数の横軸に命令のガスの横棒を並べた図。青い computation は ADD, LT, AND が 3、MUL, DIV が 5、JUMPI が 10。黄土色の state, disk, receipt は TLOAD, warm SLOAD が 100、LOG0 が 375、cold SLOAD が 2,100、cold CALL target が 2,600、SSTORE 0 → non-zero が 20,000、CREATE が 32,000" caption="Osaka の主な命令のガス（対数軸）" align="center" >}}

ADD の 3 に比べて、storage やアカウントに触る命令は約 30 倍から 1 万倍のガスが掛かります。入力の大きさで変わる式を含めた一覧は、以下に畳みました。`w` はバイト数を 32 で割って切り上げた語数です。

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
| | SSTORE | 0 から 0 以外にすると 20,000（cold なら + 2,100）など |
| transient | TLOAD、TSTORE | 100 |
| ログ | LOG0〜LOG4 | 375 + topic の数 × 375 + データのバイト数 × 8 |
| 呼び出し | CALL など | アカウントの参照 2,600 / 100、ETH を送るなら + 9,000 など |
| 作成 | CREATE | 32,000 + 初期化コードの語数 × 2 など |

</details>

cold と warm は、2021 年の Berlin で [EIP-2929](https://eips.ethereum.org/EIPS/eip-2929) が加えた区別です。同じ取引の中で初めて触るアカウントや storage の slot は高く、2 回目からは安くなります。フォークごとに SLOAD を測った実験は [Ethereum Hard Forks](../ethereum-hard-forks/) にあるので、本記事では memory の拡張と取引全体のガスを測ります。

<br>

#### 実験の環境

実験は、[Foundry の Anvil](https://getfoundry.sh/anvil/overview) 1.7.1 を [Docker](https://www.docker.com/) の専用ネットワークで起動し、`--hardfork osaka` で規則を Osaka に固定して行いました。ホストのポートは公開せず、公開のネットワークにも繋ぎません。使う秘密鍵は、Anvil が既定で用意するテスト用の公開された鍵だけです。

Solidity は solc 0.8.28（optimizer 無し、evmVersion は cancun）でコンパイルしています。コントラクトと手で組み立てたバイトコードは学習用で、監査していません。

本文に載せるのは、実験コードの [probe.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/probe.py) の抜粋です。`call(data, to)` は `eth_call` でコードを実行して返り値の 16 進文字列を返す関数、`words` はそれを 32 バイトずつの整数に分ける関数、`send` は取引を送ってレシートを返す関数です。全体と起動用の `run.sh` は本記事の最後に置きました。

<br>

#### memory の拡張

memory は使った分だけ課金され、使った最大の位置までを語数 `a` で数えて、累計で `3a + floor(a² / 512)` のガスが掛かります。命令が memory を広げた時は、広げた後と前の累計の差を払います（geth の [`memoryGasCost`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/gas_table.go#L29-L65)、execution-specs の [`calculate_memory_gas_cost`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/vm/gas.py#L253-L276)）。

この式を確かめるため、残りのガスを返す GAS 命令で MLOAD の前後を挟んだバイトコードを `eth_call` で実行しました。同じ位置を 2 回 MLOAD し、2 回目には拡張が無いことも見ます。

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

<details>
<summary>実行結果（summary.txt の抜粋）</summary>

```text
== memory expansion (MLOAD at the last word of `size` bytes) ==
size_bytes | 1st MLOAD extra | 2nd MLOAD extra | formula 3a + a*a//512
        32 |               3 |               0 | 3
      1024 |              98 |               0 | 98
     32768 |            5120 |               0 | 5120
    131072 |           45056 |               0 | 45056
```

</details>

4 つの大きさの全てで、式と実測が一致しました。2 回目の MLOAD の拡張分は 0 で、確保済みの範囲を読むたびに二次の項を払うわけではありません。

{{< figure src="images/evm_memory_gas.svg" alt="横軸が memory のバイト数、縦軸が 0 から広げるガス。青い破線の 3a は直線で、黄土色の合計 3a + a²/512 は大きくなるほど上に反る。実測の黒い点 32,768 B → 5,120 と 131,072 B → 45,056 が曲線に乗っている" caption="memory を広げるガスの式と実測" align="center" >}}

32 KiB までは直線の項が大半ですが、128 KiB では二次の項（32,768）が直線の項（12,288）の 2.7 倍になります。memory を大きく使うほど 1 バイトあたりが高くなるので、巨大な memory を確保してノードのメモリを使い切らせる攻撃は割に合いません。

<br>

#### 取引全体のガス

命令のガスの外側にも、取引ごとに掛かる分があります。実行を始める前に引かれる intrinsic gas は、宛先のある取引なら、基本の 21,000 に、取引の `data`（calldata）の 0 のバイトごとに 4、0 以外のバイトごとに 16 を足した値です。

コントラクトの作成、access list、EIP-7702 の委任の指定があれば、その分も足します（execution-specs の [`calculate_intrinsic_cost`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/transactions.py#L598-L666)）。

2025 年の Prague からは、[EIP-7623](https://eips.ethereum.org/EIPS/eip-7623) の下限（floor）として `21000 + 10 × (0 のバイト数 + 4 × 0 以外のバイト数)` があり、最終的なガスがこれを下回る時は下限まで引き上げます。

storage の値を 0 に戻すと、払い戻し（refund）が付きます。ただし、払い戻しは取引の最後にまとめて行われ、2021 年の London の [EIP-3529](https://eips.ethereum.org/EIPS/eip-3529) から、払い戻し前のガスの 5 分の 1 が上限です。実行中に使えるガスは増えません。

取引 1 件のガスにも上限があり、2025 年の Osaka の [EIP-7825](https://eips.ethereum.org/EIPS/eip-7825) で 2 の 24 乗（16,777,216）になりました。

<br>

値を 1 つ保存してイベントを出すだけのコントラクト `Dispatcher`（中身は後の ABI の節で説明します）で、この内訳を確かめました。`set(42)`、`set(43)`、`set(0)` を別々の取引で送り、Anvil の `debug_traceTransaction` で命令ごとのガスを合計しています。以下は、その内訳を横棒にした図で、数値の全体は [summary.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/output/summary.txt) にあります。

{{< figure src="images/evm_tx_gas.svg" alt="3 件の取引のガスの横棒。どれも左の灰色の intrinsic が約 21,200 を占める。set(42) は青い SSTORE が 22,100 と長く、gasUsed 45,289。set(43) は SSTORE 5,000 で gasUsed 28,189。set(0) は SSTORE 5,000 の後、緑の refund 4,800 が差し引かれて gasUsed 23,377。赤い縦線の EIP-7623 floor は約 21,500 で、どの取引も上回っている" caption="set(42)・set(43)・set(0) の gasUsed の内訳" align="center" >}}

`set(42)` は、0 の slot に 0 以外を書くので 20,000 に cold の 2,100 が加わり、SSTORE だけで 22,100 です。`set(43)` は 0 以外から別の 0 以外への書き換えで 2,900 + 2,100 = 5,000 になりました。

`set(0)` は同じ 5,000 を払った後に 4,800 が払い戻され（refund は gasUsed と、intrinsic と命令のガスの合計との差から求めました）、28,177 から 23,377 に下がっています。払い戻しの上限は 28,177 の 5 分の 1（5,635）なので、全額が戻りました。

手数料は、この gasUsed に 1 ガスあたりの単価を掛けた額です。単価の決まり方（[EIP-1559](https://eips.ethereum.org/EIPS/eip-1559) の base fee と priority fee）は [Ethereum Transaction](../ethereum-transaction/) で説明しています。

ちなみに、rollup がデータを載せる blob（[EIP-4844](https://eips.ethereum.org/EIPS/eip-4844)）には別の単価の市場があり、EVM の命令から blob の中身は読めません。読めるのは BLOBHASH で得るハッシュだけです（[Rollup](../rollup/)）。

---

### 呼び出しの文脈

コントラクトが別のコントラクトを呼ぶと、子のフレームが作られます。どの命令でも、子が実行するのは呼び先のコードです。しかし、子のフレームの中で `msg.sender`（呼び出し元）・`msg.value`（送られた ETH）・`address(this)`（storage の持ち主）が何になるかは、使う命令で決まります。

| 命令 | storage の持ち主 | `msg.sender` | `msg.value` |
| --- | --- | --- | --- |
| CALL | 呼び先 | 呼び出し元 | 指定した額（送金する） |
| DELEGATECALL | 呼び出し元 | 呼び出し元の `msg.sender` | 呼び出し元の `msg.value` |
| STATICCALL | 呼び先 | 呼び出し元 | 0 |
| CALLCODE | 呼び出し元 | 呼び出し元 | 指定した額（移動しない） |

CALLCODE は Frontier からある古い命令で、`msg.sender` を引き継がない点が使いにくく、2016 年の Homestead で DELEGATECALL（[EIP-7](https://eips.ethereum.org/EIPS/eip-7)）が加わりました。

表の 4 つのうち、状態を変更できないのは STATICCALL だけです。STATICCALL は 2017 年の Byzantium の [EIP-214](https://eips.ethereum.org/EIPS/eip-214) で、SSTORE・LOG・CREATE / CREATE2・SELFDESTRUCT と、ETH を送る CALL を禁止します（TSTORE は Cancun の EIP-1153 で同じ扱いになりました）。この禁止は孫のフレームにも引き継がれます。

表の各列は、geth の [`EVM.Call`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/evm.go#L276-L334)・[`DelegateCall`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/evm.go#L387-L419)・[`StaticCall`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/evm.go#L425-L466) が子のフレームに渡す引数で確かめられます。

<br>

#### 3 つの命令の比較

同じ `Caller` から同じ `Target` を 3 通りに呼び、`Target` の中で見えた値を記録しました。`Target.record()` は slot 0 の `count` を 1 増やし、自分が見た `msg.sender`・`address(this)`・`msg.value` を返します。EOA は `Caller.run()` を 7 wei 付きで呼び、CALL では 3 wei を送ります。

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

{{< figure src="images/evm_call_context.svg" link="images/evm_call_context.svg" alt="3 つの枠に CALL・DELEGATECALL・STATICCALL。どの枠でも、上の Caller から下の Target に矢印があり、青く塗られているのは Target の code。CALL では Target の slot 0 が黄土色で書き込まれ、msg.sender = Caller、msg.value = 3 wei。DELEGATECALL では Caller の slot 0 が黄土色で、msg.sender = EOA、msg.value = 7 wei。STATICCALL では Target の slot 0 が赤で、SSTORE fails、ok = 0" caption="CALL・DELEGATECALL・STATICCALL の文脈の違い" align="center" >}}

DELEGATECALL では、`Target` のコードが動いたのに、`address(this)` は `Caller` で、増えたのも `Caller` の `count` でした。`msg.sender` と `msg.value` も、`Caller` が受け取った EOA と 7 wei のままです。この性質を使うのがプロキシで、仕組みと storage の衝突は [ERC-1967 / ERC-7201](../upgradeable-proxy/) で説明しています。

STATICCALL は、書き込む `record()` では失敗し、読むだけの `peek()` では成功しました。失敗しても `run()` の取引は成功しています。

なお、Solidity が別のコントラクトの `view` 関数を呼ぶ時は STATICCALL を使います（[Solidity の view functions](https://docs.soliditylang.org/en/v0.8.28/contracts.html#view-functions)）。ノードの API の `eth_call` は、取引を作らずに実行を試す別の仕組みで、状態を変える関数も試せます（[Smart Contract](../smart-contract/)）。

<br>

#### 63/64 ルール

CALL で子に渡せるガスには上限があります。2016 年の Tangerine Whistle の [EIP-150](https://eips.ethereum.org/EIPS/eip-150) から、CALL 自身のコストを引いた残りを `g` として、子に渡せるのは最大で `g - floor(g / 64)` です。

親には少なくとも 64 分の 1 が残り、子が全てのガスを使い切っても、親は後処理を続けられます（geth の [`callGas`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/gas.go#L38-L53)、execution-specs の [`max_message_call_gas`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/vm/gas.py#L360-L377)）。

入口で GAS の値を返すだけの子コントラクトを CALL して、式どおりの量が渡るかを確かめました。子は初めて触るアカウントなので cold の 2,600 が掛かり、返り値を書く memory の 1 語の拡張で 3 が加わります。

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

以下は、実行結果を図にしたものです（出力は [summary.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/output/summary.txt)）。

{{< figure src="images/evm_call_split.svg" alt="上に g = 9,946,370 (before CALL) − 2,603 (CALL costs) = 9,943,767。その下の横棒の大部分が青い child gets 9,788,396 (63/64) で、右端の細い黄土色が parent keeps 155,371 (1/64)。下に request 10,000 → child gets 10,000 (below the limit 9,788,364)" caption="CALL で子に渡るガスの 63/64 の分け方" align="center" >}}

全てを要求した時、子が受け取ったガスは、`g` から 64 分の 1 を引いた値と 1 ガスも違いませんでした。10,000 だけを要求した時は、上限より小さいので要求どおりに渡っています。

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

{{< figure src="images/evm_depth_gas.svg" alt="横軸が呼び出しの深さ 0〜40、縦軸が入口のガス。青い実測の点が約 1,000 万から約 529 万まで下がり、黄土色の g₀ × (63/64)^depth の線とほぼ重なる。下に「down(322) が成功する最も深い呼び出しで、残りは 5,487。深さの上限 1024 には届かない」と注記" caption="呼び出しの深さと入口のガス（実測と式）" align="center" >}}

1 段深くなるごとに、入口のガスは 0.9843 倍になりました。63/64 は 0.984375 で、残りの差は 1 段ごとの関数呼び出しの準備に使った分です。

1,000 万ガスで成功した最も深い呼び出しは `down(322)` で、そこでの残りは 5,487 でした。EVM には呼び出しの深さを 1,024 までとする上限もあります。しかし、渡せるガスが段ごとに減るので、通常は深さの上限より先にガスが足りなくなります。

<br>

#### 再入

呼び出しの文脈で最も事故が多いのが再入（reentrancy）です。A が B を CALL すると、A のフレームは B が終わるまで途中で止まっています。その間に B が A を呼び返すと、A のコードが、最初の A がまだ更新していない storage を読んで動きます。以下は、その時間の流れを示した図です。

{{< figure src="images/evm_reentrancy.svg" alt="3 行の時間軸。A (1st) は青い reads value 10、黄土色の paused in CALL、青い writes 0 と続く。paused の間に B が calls A back を実行し、A (2nd) の青い reads 10 again に矢印が下りる。reads 10 again の右に赤い×。下に one thread: nested frames, not parallel ones" caption="1 本のスレッドの中で起きる再入" align="center" >}}

並列に動くスレッドは無く、同期的な呼び出しの入れ子だけで起きる問題です（[Solidity の Security Considerations](https://docs.soliditylang.org/en/v0.8.28/security-considerations.html#reentrancy)）。対策は、外部を呼ぶ前に自分の状態を更新しておくことと、transient storage などで呼び返しを拒むロックを置くことです。

---

### プリコンパイル

プリコンパイル（precompiled contract）は、決まったアドレスへの呼び出しについて、バイトコードではなくクライアントの組み込みの処理で実行する仕組みです。楕円曲線の計算やハッシュを EVM の命令で書くと、ガスが大きくなりすぎるからです。呼ぶ側から見ると、CALL や STATICCALL で呼ぶ普通のアドレスで、ガスは入力の大きさなどから決まった式で計算します。

Osaka の時点で 18 個あり、追加されたフォークごとに並べると以下の通りです（geth の [`contracts.go`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/contracts.go#L150-L172) の表から [count_opcodes.sh](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/count_opcodes.sh) で取り出し、execution-specs の [`mapping.py`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/vm/precompiled_contracts/mapping.py#L59-L78) と照合しました）。

{{< figure src="images/evm_precompiles.svg" link="images/evm_precompiles.svg" alt="フォークごとの列にプリコンパイルのタイルを並べた図。Frontier に 0x01 ecrecover、0x02 sha256、0x03 ripemd160、0x04 identity。Byzantium に 0x05 modexp と 0x06〜0x08 の bn254 の加算・乗算・ペアリング。Istanbul に 0x09 blake2f。Cancun に 0x0a KZG point。Prague に BLS12-381 の 0x0b〜0x11 の 7 個。Osaka に青い 0x100 p256verify" caption="フォークごとに追加されたプリコンパイル" align="center" >}}

上記の図の列の高さは、その時期に Ethereum が必要とした暗号の種類を表しています。Byzantium の bn254（alt_bn128）は zkSNARK の検証に使われ（[EIP-196](https://eips.ethereum.org/EIPS/eip-196)、[EIP-197](https://eips.ethereum.org/EIPS/eip-197)）、Cancun の 0x0a は blob の KZG の証明を確かめます。

Prague の 7 個は BLS12-381 の曲線の演算です（[EIP-2537](https://eips.ethereum.org/EIPS/eip-2537)）。Osaka の 0x100 は P-256（secp256r1）の署名を検証し、[EIP-7951](https://eips.ethereum.org/EIPS/eip-7951) は、Apple の [Secure Enclave](https://support.apple.com/guide/security/the-secure-enclave-sec59b0b31ff/web) や FIDO2 / [WebAuthn](https://www.w3.org/TR/webauthn-3/) の鍵がこの曲線を使うことを理由に挙げています。

<br>

3 つのプリコンパイルを `eth_call` で呼びました。0x02 には `abc` を渡して Python の [`hashlib`](https://docs.python.org/3/library/hashlib.html) の SHA-256 と比べ、0x01 の ecrecover には、Anvil のテスト用の鍵で署名したハッシュを渡しました。

0x100 には、Python で書いた学習用の P-256 の署名（固定の乱数で作るので実際の鍵には使えません）を渡し、ハッシュを 1 ビット変えた場合とも比べています。

```python
msg = b'abc'
out = call(msg.hex(), '0x' + '0' * 38 + '02')
assert out == hashlib.sha256(msg).hexdigest()
h, sig = os.environ['MSG_HASH'][2:], os.environ['SIG'][2:]   # from `cast keccak` and `cast wallet sign`
r, s, v = sig[:64], sig[64:128], int(sig[128:130], 16)
out = call(h + word(v) + r + s, '0x' + '0' * 38 + '01')
assert out[24:] == me[2:].lower()
# good / bad: hash, r, s, public key x, y (bad flips one bit of the hash)
p256 = '0x' + '0' * 37 + '100'
ok_out, bad_out = call(good, p256), call(bad, p256)
assert ok_out == word(1) and bad_out == ''
```

```text
== precompiles called with eth_call ==
0x02 sha256("abc") = ba7816bf8f01cfea... matches hashlib: True
0x01 ecrecover(hash, v=28, r, s) = 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266 (the signing test account)
0x100 p256verify(valid signature) = 0x01 (32 bytes), tampered hash = 0x
```

ecrecover は、署名からアドレスを復元し、署名したテスト用のアカウントと一致しました。署名の仕組みは [Digital Signature](../digital-signature/)、ecrecover を使う署名の検証は [EIP-712 / ERC-1271](../eip-712/) で説明しています。

P-256 の検証は、正しい署名で 1 を返し、ハッシュを変えると空のデータを返しました。失敗を REVERT ではなく空の返り値で伝えるのは、プリコンパイルごとの仕様です。

---

### フォークで変わる命令表

EVM の命令は、デプロイ済みのコードと違って変わります。ハードフォークのたびに命令が加わり、既存の命令のガスや意味も変わります。geth は、1 つ前のフォークの表を受け取って書き換える関数の連鎖で、フォークごとの命令表を作っています（[`jump_table.go`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/jump_table.go#L94-L128)）。

```go
func newOsakaInstructionSet() JumpTable {
	instructionSet := newPragueInstructionSet()
	enable7939(&instructionSet) // EIP-7939 (CLZ opcode)
	return validate(instructionSet)
}

func newPragueInstructionSet() JumpTable {
	instructionSet := newCancunInstructionSet()
	enable7702(&instructionSet) // EIP-7702 Setcode transaction type
	return validate(instructionSet)
}
```

ノードはブロックの高さや時刻からフォークを判定し、表を 1 つ選んで実行します。この連鎖をたどって、各フォークの表にある命令の数と、前のフォークから中身が変わった命令を数えました。

数えたのは [count_opcodes.sh](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/count_opcodes.sh) が geth に一時的に置く Go のテストで、無効を表す 0xFE（INVALID）は除いています。execution-specs の各フォークの `Ops` の数とも一致しました。

{{< figure src="images/evm_opcodes_by_fork.svg" link="images/evm_opcodes_by_fork.svg" alt="上段は命令の数の階段グラフで、2015 年の Frontier の 129 から、Homestead の DELEGATECALL、Byzantium の REVERT と STATICCALL、Constantinople の CREATE2 と SHL、Istanbul の CHAINID、London の BASEFEE、Shanghai の PUSH0、Cancun の TLOAD と MCOPY を経て、Osaka の CLZ で 149 になる。左上に「geth の Amsterdam は 153（日付未定）」。下段は既存の命令の中身が変わった数の棒で、Tangerine Whistle 7、Istanbul 4、Berlin 11、Prague 4 が目立つ" caption="フォークごとの命令の数と、中身が変わった命令の数" align="center" >}}

命令の数は 10 年で 129 から 149 に増えただけです。一方で、下段の棒が示すように、既存の命令の値段や振る舞いの変更は何度も入っています。

Tangerine Whistle の 7 個は IO の値上げ（EIP-150）、Berlin の 11 個は cold と warm の導入、Prague の 4 個は [EIP-7702](https://eips.ethereum.org/EIPS/eip-7702) で委任した EOA を CALL 系の命令が扱うための変更です。

The Merge では、同じ 0x44 の命令が、PoW の難易度（DIFFICULTY）から乱数の PREVRANDAO（[EIP-4399](https://eips.ethereum.org/EIPS/eip-4399)）に意味を変えました。ちなみに、geth の [`opcodes.go`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/opcodes.go#L317) では、0x44 の表示名が今も `DIFFICULTY` のままです。

ガスの変更でデプロイ済みのコードが動かなくなった例、solc の evmVersion とデプロイの失敗は、[Ethereum Hard Forks](../ethereum-hard-forks/) でフォークを切り替えて実験しています。

<br>

予定に入って外れた変更もあります。EOF（EVM Object Format）は、コードとデータを分けた新しいコードの形式と、デプロイ時の検証をまとめた提案群です（[EIP-3540](https://eips.ethereum.org/EIPS/eip-3540)、[EIP-7692](https://eips.ethereum.org/EIPS/eip-7692) など）。Fusaka（Osaka）の候補でしたが、2025 年 4 月 28 日の [Interop Testing #34](https://github.com/ethereum/pm/issues/1499#issuecomment-2836061807) で外されました。

2021 年の London の [EIP-3541](https://eips.ethereum.org/EIPS/eip-3541) が 0xEF で始まるコードのデプロイを禁止したのは、この形式のための予約で、EOF が有効になったわけではありません。

次のフォークの Glamsterdam（実行層は Amsterdam）は、2026 年 11 月 10 日時点で mainnet の日付が決まっていません（[ethereum.org の Glamsterdam](https://ethereum.org/roadmap/glamsterdam/)）。

固定した geth には Amsterdam の命令表（SLOTNUM、DUPN、SWAPN、EXCHANGE を加えた 153 個）が既にありますが、mainnet の設定に有効化の時刻は無く、現行の EVM の命令ではありません。

---

### EIP と ERC の関係

EVM の命令を変える提案も、トークンの規格も、EIP（Ethereum Improvement Proposal）という同じ文書の形式で書かれます。[EIP-1](https://eips.ethereum.org/EIPS/eip-1) は、EIP を以下の種類（type）と分類（category）に分けています。

{{< figure src="images/evm_eip_types.svg" alt="EIP の下に 3 つの種類。灰色の大きな Standards Track の枠の中に 4 つの分類があり、青い Core（opcodes, gas, tx types、hard fork (as a rule)）、Networking（devp2p）、Interface（ABI, method names）、ERC（tokens, wallets, signing）。右に Meta（process, fork lists）と Informational（guidelines）。Core 以外は no hard fork" caption="EIP の種類と、ハードフォークが要る範囲" align="center" >}}

上記の図で、原則としてハードフォークが必要なのは、合意の規則（命令・ガス・取引の型など）を変える青い Core だけです。Networking はノード間の通信、Interface は言語レベルの規約（メソッド名など）やコントラクトの ABI、ERC はトークン、署名、ウォレットなどアプリケーション層の規格を扱います。Meta は手続きやフォークの内容の一覧、Informational は設計上の指針や情報です。

ERC（Ethereum Request for Comments）は、Standards Track の分類の 1 つです。2023 年 10 月 25 日の [ethereum/EIPs の PR #7206](https://github.com/ethereum/EIPs/pull/7206) で ERC の文書は [ethereum/ERCs](https://github.com/ethereum/ERCs) に移りましたが、番号は共通のままで、EIP-1 の分類も変わっていません。

Core の EIP はクライアントのコードを変え、全ノードが同時に切り替える必要があります。ERC は、コントラクトとウォレットが従う約束で、ノードの規則は変えません。例えば [ERC-20](../erc-20/) に従うトークンは、規格の関数とイベントを持つ普通のコントラクトで、EVM にトークン専用の命令はありません。

ただし、EIP-1 は合意に必ずしも関わらない変更も Core に含めていて、[EIP-3607](https://eips.ethereum.org/EIPS/eip-3607) はソフトフォークとして実装できると書かれています。分類だけで、ハードフォークの有無を機械的には判定できません。

<br>

規格同士は、文書の先頭の `requires` の欄で依存を表します。以下は、本記事と関連ノートで扱う規格について、固定したコミットの `requires` を [eip_graph.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/eip_graph.py) で読み取って描いた図です。

{{< figure src="images/evm_eip_graph.svg" link="images/evm_eip_graph.svg" alt="左がフォーク不要の ERC と Interface、右の青い領域がフォークの必要な Core。ERC-721 と ERC-1155 は ERC-165 に、ERC-165 は境界をまたいで EIP-214（STATICCALL）に矢印を出す。ERC-2612 は ERC-20 と EIP-712 に、EIP-712 は ERC-191 と、境界をまたいで EIP-155（chain ID）に依存する。ERC-4337 は EIP-712 と、境界をまたいで EIP-7702 に依存し、EIP-7702 は 9 個の Core EIP（2、161、1052、2718、2929、2930、3541、3607、4844）に依存する。ERC-7562 から ERC-4337、ERC-1271 から EIP-712 には点線の「本文だけの参照」。ERC-7562 は点線の枠で status が Review。左下の凡例は、黄土色が ERC、緑が Interface、青が Core" caption="本記事で扱う規格の依存関係" align="center" >}}

上記の図で、境界をまたぐ矢印は 3 本あります。[ERC-165](https://eips.ethereum.org/EIPS/eip-165) は、コントラクトが対応するインターフェースを問い合わせる規格で、問い合わせを書き込みのできない STATICCALL で行うため、Byzantium の EIP-214 を前提にしています。

[EIP-712](../eip-712/) は署名に chain ID を含めるので [EIP-155](https://eips.ethereum.org/EIPS/eip-155) に、[ERC-4337](../erc-4337/) は 7702 で委任した EOA を扱う節があるので [EIP-7702](https://eips.ethereum.org/EIPS/eip-7702) に依存します。つまり、ERC はフォークを必要としませんが、フォークで入った機能の上に乗っている場合があります。

EIP-712 の分類は、Core ではなく Interface です。EIP-1 は ERC 以外の分類を全て EIP-X と書くので、「EIP」という呼び名だけでは Core かどうか分かりません。逆に、「EIP-1271」と書かれることの多いコントラクトの署名の規格は、分類が ERC です。呼び名ではなく、文書の `category` を見る必要があります。

[ERC-7562](../erc-7562/) は、ERC-4337 の Bundler が検証の段階で課す規則で、本文は ERC-4337 を参照しています。しかし、どちらの `requires` にも相手の番号はありません。上記の図では、この関係を `requires` と区別して点線で描きました。

また、図の全ての規格の状態（status）は Final で、ERC-7562 だけが Review です（2026-11-10 の ERCs のコミット [f94e400](https://github.com/ethereum/ERCs/blob/f94e400afdddaa2625c291f71646bde0ef44df9d/ERCS/erc-7562.md#L1-L11)）。Final は文書が確定したことを表し、Core の EIP が mainnet で有効になったことは、別に Meta EIP や更新の一覧で確かめます。

ERC-721 と ERC-1155 の違いは [ERC-721](../erc-721/)、ERC-2612 の permit は [EIP-712 / ERC-1271](../eip-712/) のノートで説明しています。

---

### コントラクトからの見え方（ABI）

EVM は、関数名も引数の型も知りません。コードに渡るのは calldata というバイト列だけで、それを関数呼び出しとして解釈する取り決めが ABI（Application Binary Interface）です。

[Solidity の ABI 仕様](https://docs.soliditylang.org/en/v0.8.28/abi-spec.html#function-selector)では、`set(uint256)` のような関数の署名の Keccak-256 の先頭 4 バイトを selector とし、その後ろに引数を 32 バイト単位で並べます。返り値の型と引数名は署名に含めません。

例として、次のコントラクトを solc 0.8.28 でコンパイルしました（optimizer 無し、evmVersion は cancun、metadata のハッシュ無し）。

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

`set(42)` の calldata は、selector の `60fe47b1` と、42（0x2a）を 32 バイトに伸ばした値の 36 バイトです。

```text
calldata of set(42): 60fe47b1 000000000000000000000000000000000000000000000000000000000000002a
```

コンパイル結果を `cast disassemble` で命令に戻すと、先頭に selector を比べるコードがあります。その部分の抜粋は以下に畳み、全体は [dispatcher.disasm.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/output/build/dispatcher.disasm.txt) に置きました。

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

</details>

calldata が 4 バイト未満なら 0x34 の REVERT に飛びます。CALLDATALOAD で先頭の 32 バイトを読み、224 ビット右にずらして先頭 4 バイトを取り出し、`value()` の `3fa4f245`、`set(uint256)` の `60fe47b1` と順に比べます。

{{< figure src="images/evm_dispatcher.svg" link="images/evm_dispatcher.svg" alt="上段は 36 バイトの calldata で、青い 4 バイトの 60fe47b1 と黄土色の 32 バイトの 00 … 00 2a (42)。中段は CALLDATALOAD 0 → SHR 224 → 60fe47b1。下段は EQ 3fa4f245（value()）が no、EQ 60fe47b1（set(uint256)）が yes で JUMPI → pc 86 に進み、SSTORE、LOG2、STOP の set() の本体に至る。どちらにも一致しなければ REVERT。左下に「EVM は set という名前を見ない」" caption="calldata の selector から set() の本体に至る分岐" align="center" >}}

`set(42)` の取引を `debug_traceTransaction` でたどると、実行された命令もこの通りでした。先頭から 30 命令の PC・命令・ガスは、以下に畳みました。

<details>
<summary>実行された先頭 30 命令（PC・命令・ガス）</summary>

```text
    0 PUSH1        3
    2 PUSH1        3
    4 MSTORE       12
    5 CALLVALUE    2
    6 DUP1         3
    7 ISZERO       3
    8 PUSH2        3
   11 JUMPI        10
   15 JUMPDEST     1
   16 POP          2
   17 PUSH1        3
   19 CALLDATASIZE 2
   20 LT           3
   21 PUSH2        3
   24 JUMPI        10
   25 PUSH0        2
   26 CALLDATALOAD 3
   27 PUSH1        3
   29 SHR          3
   30 DUP1         3
   31 PUSH4        3
   36 EQ           3
   37 PUSH2        3
   40 JUMPI        10
   41 DUP1         3
   42 PUSH4        3
   47 EQ           3
   48 PUSH2        3
   51 JUMPI        10
   86 JUMPDEST     1
```

</details>

PC 4 の MSTORE が 12 ガスなのは、Solidity が memory の 0x40 に空き領域の先頭（0x80）を書く時に、0x60 バイトまで memory を広げるからです。命令の 3 に、3 語分の拡張の 9 が加わっています。

`set` は `payable` ではないので、PC 5〜11 で ETH が付いていないことを確かめています。PC 51 の JUMPI で 86（0x56）に飛んだ後が `set` の本体です。

どの selector にも一致しない `0xdeadbeef` を送った取引は、`status=0` で失敗しました。

```text
unknown selector 0xdeadbeef: status=0
```

この直線の比較は、関数が少なく optimizer を使わない場合の形です。optimizer の設定は、関数を振り分ける部分の二分探索の大きさなどを変えます（[solc の optimizer options](https://docs.soliditylang.org/en/v0.8.28/using-the-compiler.html#optimizer-options)）。

どちらの場合も、EVM が比べているのは 4 バイトの数値だけです。そのため、別の署名から同じ 4 バイトが出る衝突も起こり得て、プロキシでは呼び先の関数と管理用の関数の selector が重ならないように設計します（[ERC-1967 / ERC-7201](../upgradeable-proxy/)）。

<br>

#### イベントとログ

`emit Changed(msg.sender, x)` は LOG2 命令になります。ログは、レシートに残る一方通行の出力で、storage とは違い、コントラクトが後から読み返す命令はありません。アプリはノードの API でログを取得し、処理結果を追跡します。

{{< figure src="images/evm_log.svg" alt=`LOG2 in set(42): 1381 gas = 375 + 2 × 375 + 8 × 32 bytes。青い帯の address（Dispatcher）、topic0（keccak("Changed(...)")）、topic1（sender (indexed)）と、黄土色の data（value = 42）。address と 2 つの topic から右の灰色の bloom（2048 bits）に矢印があり、data からは無い` caption="set(42) の LOG2 の中身と bloom" align="center" >}}

topic0 は、イベントの署名 `Changed(address,uint256)` の Keccak-256 の 32 バイト全体で、関数の selector のように 4 バイトに切りません。`indexed` を付けた引数は topic1 以降に入り、付けていない引数は data に ABI の形で入ります。実験の LOG2 は、上記の図の式どおり 1,381 ガスでした。

```text
topic0 of Changed: 0xb52dda022b6c1a1f40905a85f257f689aa5d69d850e49cf939d688fbe5af5946
```

ブロックのヘッダーとレシートには、2,048 ビットの bloom があり、ログのアドレスと topic から 3 ビットずつ立てます（geth の [`bloom9.go`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/types/bloom9.go#L107-L160)）。bloom にビットが無ければ、そのブロックに該当のログが無いと分かり、検索を速くできます。data は bloom に入らないので、値でログを探すなら `indexed` の引数にする必要があります。

---

### 実験の再現

実験は、リポジトリのルートで次を実行すると約 5 秒で終わり、コンテナとネットワークを削除します。

使ったイメージは ghcr.io/foundry-rs/foundry:v1.7.1、ethereum/solc:0.8.28、python:3.13-slim で、digest は [versions.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/output/versions.txt) に記録しています。Anvil の時刻を固定しているので、[summary.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/output/summary.txt) は何度実行しても同じです。

```bash
bash content/notes/blockchain-systems/evm/lab/run.sh
```

<details>
<summary>run.sh の全体</summary>

```bash
#!/usr/bin/env bash
# Local-only EVM experiment. One Anvil node pinned to Osaka runs on a private
# Docker network and publishes no host port. Only Anvil's default test
# accounts and key are used. No public network is contacted.
set -euo pipefail

LAB="$(cd "$(dirname "$0")" && pwd)"
OUT="$LAB/output"
FOUNDRY=ghcr.io/foundry-rs/foundry:v1.7.1
SOLC=ethereum/solc:0.8.28
PY=python:3.13-slim
NET=note-evm-net
NODE=note-evm-anvil
# Anvil's well-known default test key for account 0 (public, never use with real funds).
TEST_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

cleanup() {
  docker rm -f "$NODE" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT

rm -rf "$OUT/build" "$OUT/summary.txt" "$OUT/probe.json" "$OUT/versions.txt"
mkdir -p "$OUT/build"

# 1. Compile. Optimizer off, metadata hash off, evmVersion cancun.
docker run --rm -v "$LAB:/lab:ro" "$SOLC" --evm-version cancun --metadata-hash none \
  --combined-json abi,bin,bin-runtime,hashes /lab/Dispatcher.sol /lab/Context.sol /lab/Deep.sol \
  > "$OUT/build/combined.json"

# 2. Start Anvil (Osaka rules, fixed timestamp so gas and addresses repeat).
docker network create "$NET" >/dev/null
docker run -d --name "$NODE" --network "$NET" "$FOUNDRY" \
  "anvil --host 0.0.0.0 --hardfork osaka --chain-id 31337 --timestamp 1700000000 --accounts 2 --steps-tracing --quiet" >/dev/null

# 3. Values that need Keccak-256 or secp256k1: computed with cast in the node container.
runtime=$(python3 -c "import json,sys;c=json.load(open(sys.argv[1]))['contracts'];print([v for k,v in c.items() if k.endswith(':Dispatcher')][0]['bin-runtime'])" "$OUT/build/combined.json")
docker exec "$NODE" cast disassemble "0x$runtime" > "$OUT/build/dispatcher.disasm.txt"
MSG_HASH=$(docker exec "$NODE" cast keccak "evm note")
SIG=$(docker exec "$NODE" cast wallet sign --no-hash --private-key "$TEST_KEY" "$MSG_HASH")
TOPIC0=$(docker exec "$NODE" cast keccak "Changed(address,uint256)")

# 4. Probes from a Python container on the same network.
docker run --rm --network "$NET" --user "$(id -u):$(id -g)" -v "$LAB:/lab" -w /lab \
  -e NODE="$NODE" -e MSG_HASH="$MSG_HASH" -e SIG="$SIG" -e TOPIC0="$TOPIC0" \
  "$PY" python -I probe.py

{
  for img in "$FOUNDRY" "$SOLC" "$PY"; do
    echo "$img $(docker image inspect --format '{{index .RepoDigests 0}}' "$img")"
  done
  docker exec "$NODE" anvil --version | head -1
  docker run --rm "$SOLC" --version | tail -1
} > "$OUT/versions.txt"
```

</details>

<details>
<summary>probe.py の全体</summary>

```python
#!/usr/bin/env python3
"""Probe the EVM on a local Anvil node pinned to Osaka.

Local-only. Called by run.sh inside a container on a private Docker network.
Hand-assembled bytecode and the Solidity files are educational and not audited.
"""
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request

NODE = os.environ['NODE']
OUT = Path('output')
BUILD = json.loads((OUT / 'build' / 'combined.json').read_text())['contracts']
lines = []
record = {}


class RpcError(Exception):
    pass


def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    request = urllib.request.Request(f'http://{NODE}:8545', body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.load(response)
    if 'error' in result:
        raise RpcError(result['error']['message'])
    return result['result']


def wait_ready():
    for _ in range(200):
        try:
            return rpc('eth_accounts')
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(NODE)


def send(tx):
    tx = {'gas': hex(3_000_000), **tx}
    txhash = rpc('eth_sendTransaction', tx)
    for _ in range(100):
        receipt = rpc('eth_getTransactionReceipt', txhash)
        if receipt:
            return receipt
        time.sleep(0.05)
    raise TimeoutError(txhash)


def call(data, to=None, gas=10_000_000):
    tx = {'data': '0x' + data, 'gas': hex(gas)}
    if to:
        tx['to'] = to
    return rpc('eth_call', tx, 'latest')[2:]


def words(raw):
    return [int(raw[i:i + 64], 16) for i in range(0, len(raw), 64)]


def contract(name):
    return next(v for k, v in BUILD.items() if k.endswith(':' + name))


def deploy(me, initcode):
    receipt = send({'from': me, 'data': '0x' + initcode})
    assert int(receipt['status'], 16) == 1
    return receipt['contractAddress']


def initcode_for(runtime):
    """Init code that copies `runtime` (hex) into memory and returns it as the deployed code."""
    n = len(runtime) // 2
    assert n < 256
    return f'60{n:02x}600c600039{"60%02x" % n}6000f3' + runtime


def word(x):
    return f'{x:064x}'


def addr_word(a):
    return a[2:].lower().rjust(64, '0')


me, other = wait_ready()

# 1. Memory expansion: GAS, MLOAD(off), POP, GAS, MLOAD(off), POP, GAS.
#    Each gap = PUSH3(3) + MLOAD(3) + POP(2) + GAS(2) = 10, plus memory expansion.
def c_mem(size):
    a = (size + 31) // 32
    return 3 * a + a * a // 512


lines.append('== memory expansion (MLOAD at the last word of `size` bytes) ==')
lines.append('size_bytes | 1st MLOAD extra | 2nd MLOAD extra | formula 3a + a*a//512')
record['memory'] = []
for size in (32, 1024, 32768, 131072):
    off = f'{size - 32:06x}'
    code = ('5a' f'62{off}' '51' '50' '5a' f'62{off}' '51' '50' '5a'
            '604052' '602052' '600052' '60606000f3')
    g0, g1, g2 = words(call(code))
    first, second = g0 - g1 - 10, g1 - g2 - 10
    assert first == c_mem(size) and second == 0
    record['memory'].append({'size': size, 'measured': first, 'formula': c_mem(size)})
    lines.append(f'{size:>10} | {first:>15} | {second:>15} | {c_mem(size)}')

# 2. The 63/64 rule. The callee returns GAS at its entry (GAS costs 2, so entry = value + 2).
callee = deploy(me, initcode_for('5a5f5260205ff3'))  # GAS PUSH0 MSTORE PUSH1 32 PUSH0 RETURN
lines.append('')
lines.append('== CALL forwards at most g - floor(g/64) (g = gas left after the CALL costs) ==')
lines.append('request  | gas before CALL | CALL costs | callee entry | 63/64 limit')
record['call_gas'] = []
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
    record['call_gas'].append({'request': label, 'before': before, 'entry': entry, 'limit': limit})
    lines.append(f'{label:<8} | {before:>15} | {costs:>10} | {entry:>12} | {limit}')

# 3. Gas left at the entry of the deepest frame of down(d) (Solidity, this.down(d - 1)).
deep = deploy(me, contract('Deep')['bin'])
sel = contract('Deep')['hashes']['down(uint256)']
g = [words(call(sel + word(d), deep))[0] for d in range(0, 41)]
record['depth'] = g
lines.append('')
lines.append('== gasleft() at the entry of the deepest frame (eth_call gas 10,000,000) ==')
lines.append('depth | gasleft  | ratio to one level up')
for d in (0, 1, 2, 3, 10, 20, 30, 40):
    ratio = '' if d == 0 else f'{g[d] / g[d - 1]:.4f}'
    lines.append(f'{d:>5} | {g[d]:>8} | {ratio}')
lo, hi = 0, 1024
while lo < hi:  # deepest d for which down(d) still succeeds with 10M gas
    mid = (lo + hi + 1) // 2
    try:
        call(sel + word(mid), deep)
        lo = mid
    except RpcError:
        hi = mid - 1
record['max_depth'] = lo
record['max_depth_gas'] = words(call(sel + word(lo), deep))[0]
lines.append(f'deepest down() that succeeds with 10,000,000 gas: {lo} (gasleft there: {record["max_depth_gas"]})')

# 4. CALL / DELEGATECALL / STATICCALL from the same Caller to the same Target.
target = deploy(me, contract('Target')['bin'])
caller = deploy(me, contract('Caller')['bin'])
receipt = send({'from': me, 'to': caller, 'value': hex(7),
                'data': '0x' + contract('Caller')['hashes']['run(address)'] + addr_word(target)})
assert int(receipt['status'], 16) == 1
names = {me.lower(): 'EOA', caller.lower(): 'Caller', target.lower(): 'Target',
         '0x' + '0' * 40: '-'}
lines.append('')
lines.append('== Caller.run(target) sent by the EOA with 7 wei ==')
lines.append('mode                | ok | msg.sender | address(this) | msg.value')
record['context'] = []
for log in receipt['logs']:
    w = words(log['data'][2:])
    off, ok, sender, self_, value = w[0], w[1], w[2], w[3], w[4]
    n = w[off // 32]
    mode = bytes.fromhex(log['data'][2:][(off + 32) * 2:(off + 32 + n) * 2]).decode()
    s, t = names['0x' + f'{sender:040x}'], names['0x' + f'{self_:040x}']
    record['context'].append({'mode': mode, 'ok': ok, 'sender': s, 'self': t, 'value': value})
    lines.append(f'{mode:<19} | {ok:<2} | {s:<10} | {t:<13} | {value}')
count = contract('Target')['hashes']['count()']
counts = {n: words(call(count, a))[0] for n, a in (('Caller', caller), ('Target', target))}
balances = {n: int(rpc('eth_getBalance', a, 'latest'), 16) for n, a in (('Caller', caller), ('Target', target))}
record['counts'], record['balances'] = counts, balances
lines.append('storage slot 0 (count) after: ' + ', '.join(f'{k}={v}' for k, v in counts.items()))
lines.append('balance after (wei): ' + ', '.join(f'{k}={v}' for k, v in balances.items()))

# 5. The dispatcher: calldata, executed opcodes, and the gas of each transaction.
disp = deploy(me, contract('Dispatcher')['bin'])
set_sel = contract('Dispatcher')['hashes']['set(uint256)']
record['getter_selector'] = contract('Dispatcher')['hashes']['value()']


def intrinsic(data_hex):
    b = bytes.fromhex(data_hex)
    zeros = b.count(0)
    nonzero = len(b) - zeros
    return 21000 + 4 * zeros + 16 * nonzero, 21000 + 10 * (zeros + 4 * nonzero)


lines.append('')
lines.append('== Dispatcher.set(x): calldata and the gas of each transaction ==')
record['dispatcher'] = []
for x in (42, 43, 0):
    data = set_sel + word(x)
    receipt = send({'from': me, 'to': disp, 'data': '0x' + data})
    trace = rpc('debug_traceTransaction', receipt['transactionHash'], {'disableStorage': True})
    steps = trace['structLogs']
    execution = sum(s['gasCost'] for s in steps)
    by_op = {}
    for s in steps:
        by_op[s['op']] = by_op.get(s['op'], 0) + s['gasCost']
    base, floor = intrinsic(data)
    used = int(receipt['gasUsed'], 16)
    refund = base + execution - used
    item = {'x': x, 'calldata': data, 'intrinsic': base, 'floor': floor, 'execution': execution,
            'sstore': by_op.get('SSTORE', 0), 'log': by_op.get('LOG2', 0), 'gas_used': used,
            'refund': refund, 'steps': len(steps)}
    record['dispatcher'].append(item)
    if x == 42:
        lines.append('calldata of set(42): ' + data[:8] + ' ' + data[8:])
        assert receipt['logs'][0]['topics'][0] == os.environ['TOPIC0']
        lines.append('topic0 of Changed: ' + receipt['logs'][0]['topics'][0])
        lines.append('first executed opcodes (pc op gasCost):')
        for s in steps[:30]:
            lines.append(f'  {s["pc"]:>3} {s["op"]:<12} {s["gasCost"]}')
        record['trace_head'] = [[s['pc'], s['op'], s['gasCost']] for s in steps[:30]]
    lines.append(f'set({x}): intrinsic={base} floor={floor} execution={execution} '
                 f'(SSTORE={item["sstore"]} LOG2={item["log"]}) refund={refund} gasUsed={used}')
bad = send({'from': me, 'to': disp, 'data': '0xdeadbeef'})
record['unknown_selector_status'] = int(bad['status'], 16)
lines.append(f'unknown selector 0xdeadbeef: status={int(bad["status"], 16)}')

# 6. Precompiles: SHA-256 (0x02), ecrecover (0x01) and P-256 verification (0x100, Osaka).
lines.append('')
lines.append('== precompiles called with eth_call ==')
msg = b'abc'
out = call(msg.hex(), '0x' + '0' * 38 + '02')
assert out == hashlib.sha256(msg).hexdigest()
lines.append(f'0x02 sha256("abc") = {out[:16]}... matches hashlib: True')
h, sig = os.environ['MSG_HASH'][2:], os.environ['SIG'][2:]
r, s, v = sig[:64], sig[64:128], int(sig[128:130], 16)
out = call(h + word(v) + r + s, '0x' + '0' * 38 + '01')
assert out[24:] == me[2:].lower()
lines.append(f'0x01 ecrecover(hash, v={v}, r, s) = 0x{out[24:]} (the signing test account)')

# Minimal ECDSA over P-256 for the 0x100 input (educational, fixed k, never use for real keys).
P = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
N = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
A = P - 3
G = (0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296,
     0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5)


def add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    if p1[0] == p2[0] and (p1[1] + p2[1]) % P == 0:
        return None
    if p1 == p2:
        m = (3 * p1[0] * p1[0] + A) * pow(2 * p1[1], -1, P) % P
    else:
        m = (p2[1] - p1[1]) * pow(p2[0] - p1[0], -1, P) % P
    x = (m * m - p1[0] - p2[0]) % P
    return x, (m * (p1[0] - x) - p1[1]) % P


def mul(k, pt):
    acc = None
    while k:
        if k & 1:
            acc = add(acc, pt)
        pt, k = add(pt, pt), k >> 1
    return acc


d, k = 0x1234567, 0x7654321
qx, qy = mul(d, G)
z = int(hashlib.sha256(b'evm note').hexdigest(), 16)
r256 = mul(k, G)[0] % N
s256 = pow(k, -1, N) * (z + r256 * d) % N
good = f'{z:064x}{r256:064x}{s256:064x}{qx:064x}{qy:064x}'
bad = f'{z ^ 1:064x}{r256:064x}{s256:064x}{qx:064x}{qy:064x}'
p256 = '0x' + '0' * 37 + '100'
ok_out, bad_out = call(good, p256), call(bad, p256)
assert ok_out == word(1) and bad_out == ''
record['p256'] = {'valid': ok_out, 'tampered': bad_out}
lines.append(f'0x100 p256verify(valid signature) = 0x{ok_out[-2:]} (32 bytes), tampered hash = 0x{bad_out}')

summary = '\n'.join(lines) + '\n'
(OUT / 'summary.txt').write_text(summary)
(OUT / 'probe.json').write_text(json.dumps(record, indent=2) + '\n')
print(summary, end='')
```

</details>

命令表とプリコンパイルの数え上げ（[count_opcodes.sh](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/count_opcodes.sh)）は go-ethereum の [ddaa6957](https://github.com/ethereum/go-ethereum/tree/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f)、依存の図（[eip_graph.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/eip_graph.py)）は ethereum/EIPs の [542e62eb](https://github.com/ethereum/EIPs/tree/542e62eb129517130b7facc52bbb9a1f333c711e) と ethereum/ERCs の [f94e400a](https://github.com/ethereum/ERCs/tree/f94e400afdddaa2625c291f71646bde0ef44df9d) を手元に置いて実行します。図は全て [figures.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/figures.py) が、これらの出力から描いています。
