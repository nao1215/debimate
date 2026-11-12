---
title: "EVM Opcode History - 更新ごとに増えた命令とプリコンパイル"
date: 2026-11-11
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain-systems", "ethereum", "evm", "eip", "erc", "hard-fork"]
weight: 18
wrapTables: true
topics: ["Smart Contract"]
---

[EVM](../evm/)（Ethereum Virtual Machine）は、[Ethereum](https://ethereum.org/) のノードがコントラクトのコードを実行する仮想マシンです。デプロイしたコントラクトのコードは書き換えられません。では、そのコードを実行する EVM の命令の一覧（命令表）は、2015 年の公開から変わっていないのでしょうか。

実際には、命令表は何度も変わっています。Ethereum は、全てのノードが決めたブロックや時刻に一斉に規則を切り替える更新（ハードフォーク）をこれまでに 20 回ほど行い、そのたびに命令が加わったり、既存の命令の値段（ガス）や意味が変わったりします。ハードフォークの決まり方と、開発者のコードへの影響は [Ethereum Hard Forks](../ethereum-hard-forks/) で説明しています。

<br>

本記事では、[go-ethereum](https://github.com/ethereum/go-ethereum)（geth、Go で書かれた Ethereum のクライアント）の命令表を数えて、EVM の命令表が更新ごとにどう変わったかを示します。続いて、命令ではなく決まったアドレスで呼ぶ組み込みの処理、予定に入って外れた変更、命令を変える文書と変えない文書（EIP と ERC）の違いを扱います。EVM のスタック・ガス・呼び出しの仕組みは [EVM](../evm/) のノートを前提にします。

---

### 本記事に出てくる更新

Ethereum の更新には名前が付いていて、1 回の更新の中身は EIP（Ethereum Improvement Proposal）という番号付きの提案の文書の組で決まります。EIP については「EIP と ERC」の節で説明します。以下は、本記事に出てくる更新を mainnet で有効になった順に並べた表です。

表は覚える必要はなく、後の節で名前が出た時に戻って見るための一覧です。主な変更は代表だけを載せていて、追加された命令の全ては挙げていません。日付は [ethereum.org の更新の一覧](https://ethereum.org/ethereum-forks/)と geth の mainnet の設定に基づきます。

| 名前 | mainnet | EVM に関わる主な変更 |
| --- | --- | --- |
| Frontier | 2015-07 | 最初の版。命令は 129 個 |
| Homestead | 2016-03 | DELEGATECALL の追加 |
| Tangerine Whistle | 2016-10 | 2016 年の DoS 攻撃を受けた、ディスクを読む命令の値上げ |
| Spurious Dragon | 2016-11 | EXP の値上げ、空のアカウントの整理など |
| Byzantium | 2017-10 | REVERT・STATICCALL の追加、楕円曲線の計算の組み込み（後の節のプリコンパイル） |
| Constantinople | 2019-02 | 作成先のアドレスを事前に決められる CREATE2、ビットのシフト命令の追加 |
| Istanbul | 2019-12 | チェーンの番号を読む CHAINID の追加、状態を読む命令（SLOAD・BALANCE・EXTCODEHASH）の値上げ |
| Berlin | 2021-04 | 初めて触る状態（cold）と 2 回目以降（warm）の料金の区別 |
| London | 2021-08 | 手数料の基本料金（base fee）と、それを読む BASEFEE の追加 |
| The Merge | 2022-09 | ブロックを作る権利の決め方が、計算の競争（PoW）から ETH の預け入れ（PoS）に移行 |
| Shanghai | 2023-04 | 0 を積む PUSH0 の追加 |
| Cancun | 2024-03 | トランザクションの間だけ残るストレージ transient storage（TSTORE・TLOAD）と、memory をコピーする MCOPY などの追加 |
| Prague | 2025-05 | EOA がコントラクトのコードに実行を委任できる EIP-7702 |
| Osaka | 2025-12 | 先頭の 0 のビットを数える CLZ の追加、スマートフォンの鍵などで使う曲線 P-256 の署名の検証 |

2022 年の The Merge 以降、更新には実行レイヤー（execution layer、トランザクションを実行する側）とコンセンサス・レイヤー（consensus layer、ブロックの合意を担う側）の 2 つの名前があり、本記事では EVM に関わる実行レイヤーの名前（Shanghai、Cancun など）を使います。

---

### 命令表の変遷

geth は、1 つ前の更新の命令表を受け取って書き換える関数の連鎖で、更新ごとの命令表を作っています（[`jump_table.go`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/jump_table.go#L94-L128)）。例えば Osaka の表は、Prague の表に CLZ 命令を加えたものです。

```go
func newOsakaInstructionSet() JumpTable {
	instructionSet := newPragueInstructionSet()
	enable7939(&instructionSet) // EIP-7939 (CLZ opcode)
	return validate(instructionSet)
}
```

ノードはブロックの高さや時刻から更新を判定し、表を 1 つ選んで実行します。この連鎖をたどって、各更新の表にある命令の数と、前の更新から中身（ガスや振る舞い）が変わった命令を数えました。

無効を表す 0xFE（INVALID）は数えていません。[execution-specs](https://github.com/ethereum/execution-specs)（Python で書かれた仕様）の各更新の命令の数とも一致しました。スクリプトとデータは最後の節にまとめました。

{{< figure src="images/evm-opcode-history_opcodes_by_fork.webp" link="images/evm-opcode-history_opcodes_by_fork.webp" alt="上段は命令の数の階段グラフで、2015 年の Frontier の 129 から、Homestead の DELEGATECALL、Byzantium の REVERT と STATICCALL、Constantinople の CREATE2 と SHL、Istanbul の CHAINID、London の BASEFEE、Shanghai の PUSH0、Cancun の TLOAD と MCOPY を経て、Osaka の CLZ で 149 になる。左上に「geth の Amsterdam は 153（日付未定）」。下段は既存の命令の中身が変わった数（変わった命令）の棒で、Tangerine Whistle 7、Istanbul 4、Berlin 11、Prague 4 が目立ち、The Merge の 1 にもラベルがある。上段の起点に Frontier: 129" caption="更新ごとの命令の数と、中身が変わった命令の数" align="center" >}}

上段の命令の数は、10 年で 129 から 149 に増えただけです（左上の Amsterdam の 153 は、日付が決まっていない次の更新の分で、後の節で触れます）。一方で、下段の変わった命令の数が示すように、既存の命令の値段や振る舞いの変更は何度も入っています。

下段の大きい棒は 4 つです。Tangerine Whistle の 7 個はディスクを読む命令の値上げ（[EIP-150](https://eips.ethereum.org/EIPS/eip-150)）、Istanbul の 4 個は状態を読む命令の値上げと SSTORE の料金の見直しです。

Berlin の 11 個は cold と warm の導入（[EIP-2929](https://eips.ethereum.org/EIPS/eip-2929)）です。Prague の 4 個は、EOA に別のコントラクトのコードを自分のコードとして動かさせる設定（委任、[EIP-7702](https://eips.ethereum.org/EIPS/eip-7702)）が入ったため、CALL 系の命令が委任した EOA を呼ぶ時の扱いを変えたものです。

ラベルの無い小さい棒は 1〜2 個の変更で、払い戻しの縮小や、コントラクトを消す命令 SELFDESTRUCT の意味の変更などです（一覧は [geth_tables.json](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm-opcode-history/lab/output/geth_tables.json) の `changed`）。The Merge の 1 個は次の段落で説明します。値上げで既存のコントラクトが動かなくなった例は [Ethereum Hard Forks](../ethereum-hard-forks/) で実験しています。

<br>

命令の意味だけが変わった例もあります。以下は、0x44 という同じバイトの命令の意味が、The Merge の前後で変わったことを示した図です。

{{< figure src="images/evm-opcode-history_prevrandao.webp" alt="左に青い 0x44 の箱（同じバイト）。上の行は The Merge の前（PoW）で DIFFICULTY、ブロックの計算の難しさ。下の緑の行は The Merge の後（PoS）で PREVRANDAO、PoS で作る乱数" caption="The Merge の前後で意味が変わった 0x44" align="center" >}}

PoW では、ブロックを作るための計算の難しさ（難易度）を 0x44 の DIFFICULTY 命令で読めました。The Merge で PoW をやめると難易度は意味を失うので、同じ 0x44 は、PoS の仕組みで作る[乱数の PREVRANDAO](../commit-reveal/#randao-と最後に明かす人) を返す命令に変わりました（[EIP-4399](https://eips.ethereum.org/EIPS/eip-4399)）。

命令の数は変わらないので、図の上段には The Merge の点が無く、下段に 1 個の変更として現れます。ちなみに、geth の [`opcodes.go`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/opcodes.go#L317) では、0x44 の表示名が今も `DIFFICULTY` のままです。

---

### プリコンパイル

EVM は命令ごとにガスを課金するので、楕円曲線の計算やハッシュを EVM の命令で書くと、命令の数だけガスが積み上がり、大きくなりすぎます。そこで Ethereum は、決まったアドレスへの呼び出しについては、バイトコードではなくクライアントの組み込みの処理で実行する仕組みを持っています。

これをプリコンパイル（precompiled contract）と呼びます。呼ぶ側から見ると CALL や STATICCALL で呼ぶ普通のアドレスで、ガスは入力の大きさなどから決まった式で計算します。

Osaka の時点で 18 個あり、追加された更新ごとに並べると以下の通りです（geth の [`contracts.go`](https://github.com/ethereum/go-ethereum/blob/ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f/core/vm/contracts.go#L150-L172) の表から取り出し、execution-specs の [`mapping.py`](https://github.com/ethereum/execution-specs/blob/f9488c74b3d1f7433a0134b8029a3ae99c994d51/src/ethereum/forks/osaka/vm/precompiled_contracts/mapping.py#L59-L78) と照合しました）。

{{< figure src="images/evm-opcode-history_precompiles.webp" link="images/evm-opcode-history_precompiles.webp" alt="更新ごとの列にプリコンパイルのタイルを並べた図。Frontier に 0x01 ecrecover、0x02 sha256、0x03 ripemd160、0x04 identity。Byzantium に 0x05 modexp と 0x06〜0x08 の bn254 の加算・乗算・ペアリング。Istanbul に 0x09 blake2f。Cancun に 0x0a KZG 検証。Byzantium の下に「0x06〜08 は bn254」。Prague に BLS12-381 の 0x0b〜0x11 の 7 個（加算・MSM・ペアリング・写像）。Osaka に青い 0x100 p256verify" caption="更新ごとに追加されたプリコンパイル" align="center" >}}

上記の図の列ごとのタイルの数を見ると、その時期に Ethereum が必要とした暗号の計算が分かります。タイルの名前（MSM、G1 写像など）は個々の演算の名前で、本文では主な列の用途だけを説明します。Frontier の 0x01 の ecrecover は、署名から署名者のアドレスを復元する処理です。

署名の仕組みは [Digital Signature](../digital-signature/)、ecrecover を使う署名の検証は [EIP-712](../eip-712/) と [ERC-1271](../erc-1271/) で説明しています。

Byzantium の 4 個のうち、modexp は大きな数のべき乗の剰余で、RSA の署名の検証などに使います。bn254（alt_bn128）の 3 個は、計算の中身を明かさずに正しさだけを示す証明（[zkSNARK](../zero-knowledge-proof/)）の検証に使われます（[EIP-196](https://eips.ethereum.org/EIPS/eip-196)、[EIP-197](https://eips.ethereum.org/EIPS/eip-197)）。Istanbul の blake2f は、ハッシュ関数 BLAKE2 の計算の一部です。

Cancun の 0x0a（KZG 検証）は、[rollup](../rollup/) のためのものです。rollup は Ethereum の外でトランザクションをまとめて処理し、そのデータを [blob](../blob/) という大きなデータの欄に載せます。以下は、その時に 0x0a が何を確認するかを示した図です。

{{< figure src="images/evm-opcode-history_kzg.webp" alt="左の灰色の「blob を運ぶトランザクション」の中に、黄土色の blob（128 KiB、EVM からは読めない）と、versioned hash（commitment のハッシュ）。versioned hash から BLOBHASH の矢印で「rollup のコントラクト」へ、そこから青い「0x0a で検証（commitment が versioned hash と合うか、点 z で値 y か）」へ。下に「z・y・commitment・証明は、送る側が blob から計算して渡す」「確認できるのは、その blob のその点の値」" caption="EVM から読めない blob を 0x0a で確認する" align="center" >}}

blob を運ぶトランザクションには、blob の本体と、blob を要約した値（commitment）のハッシュである versioned hash が入ります。EVM からは blob の本体を読めず、コントラクトが BLOBHASH 命令で読めるのは versioned hash だけです。

そこで rollup のコントラクトは、トランザクションを送る側が blob から計算した値（点 z・その点での値 y・commitment・証明）を受け取り、versioned hash と合わせて 0x0a に渡します。0x0a は KZG という方式の証明を使い、commitment が versioned hash と合うことと、blob の中身を多項式とみなした時に点 z で値 y を取ることを確認します。確認できるのは blob 全体ではなく、その blob のその点の値です。

Prague の 7 個は、PoS の投票の署名に使われる BLS12-381 という曲線の演算で、その署名をコントラクトの中でも検証できるようにするためのものです（[EIP-2537](https://eips.ethereum.org/EIPS/eip-2537)）。

Osaka の 0x100 は P-256（secp256r1）の署名を検証します。[EIP-7951](https://eips.ethereum.org/EIPS/eip-7951) は、Apple の [Secure Enclave](https://support.apple.com/guide/security/the-secure-enclave-sec59b0b31ff/web) や [FIDO2](/notes/security/passkey/) / [WebAuthn](https://www.w3.org/TR/webauthn-3/) の鍵がこの曲線を使うことを理由に挙げています。

<br>

#### 3 つのプリコンパイルを呼ぶ

EVM のノートと同じローカルの開発用ノード（[Anvil](https://getfoundry.sh/anvil/overview) を Osaka の規則に固定したもの）で、3 つのプリコンパイルを `eth_call`（トランザクションを作らずにコードを試しに実行し、返り値だけを受け取る API）で呼びました。

0x02 には `abc` を渡して Python の [`hashlib`](https://docs.python.org/3/library/hashlib.html) の [SHA-256](https://csrc.nist.gov/pubs/fips/180-4/upd1/final) と比べ、0x01 の ecrecover には、Anvil のテスト用の鍵で署名したハッシュを渡しました。0x100 には、Python で書いた学習用の P-256 の署名（固定の乱数で作るので実際の鍵には使えません）を渡し、ハッシュを 1 ビット変えた場合とも比べています。

以下は EVM のノートの実験コード [probe.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/probe.py) の抜粋です。`MSG_HASH` と `SIG` は、実験の起動スクリプトが Foundry の cast で作ったハッシュと、テスト用の鍵による署名です。`call(data, to)` は `eth_call` の返り値を 16 進文字列で返す関数、`word` は整数を 32 バイトの 16 進にする関数、`me` は署名したテスト用のアカウントです。

ecrecover には、署名したハッシュと、署名を構成する 3 つの値（v・r・s）を並べて渡します。P-256 の `good` と `bad` は、ハッシュ・r・s・公開鍵の x と y を 32 バイトずつ並べた入力で、`bad` はハッシュの 1 ビットだけを変えたものです（組み立ては probe.py にあります）。

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

ecrecover の返り値は 32 バイトの左側を 0 で埋めたアドレスなので、`out[24:]`（16 進で 24 文字＝12 バイトの 0 を除いた残り）を署名したアカウントと比べています。

```text
== precompiles called with eth_call ==
0x02 sha256("abc") = ba7816bf8f01cfea... matches hashlib: True
0x01 ecrecover(hash, v=28, r, s) = 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266 (the signing test account)
0x100 p256verify(valid signature) = 0x01 (32 bytes), tampered hash = 0x
```

ecrecover は、署名からアドレスを復元し、署名したテスト用のアカウントと一致しました。P-256 の検証は、正しい署名で 1 を返し、ハッシュを変えると空のデータを返しました。失敗を REVERT ではなく空の返り値で伝えるのは、プリコンパイルごとの仕様です。

---

### 予定から外れた変更

予定に入って外れた変更もあります。EOF（EVM Object Format）は、先頭を 0xEF で始めて区別する、コードとデータを分けた新しいコードの形式と、デプロイ時の検証をまとめた提案群です（[EIP-3540](https://eips.ethereum.org/EIPS/eip-3540)、[EIP-7692](https://eips.ethereum.org/EIPS/eip-7692) など）。

Osaka の候補でしたが、2025 年 4 月 28 日のクライアント開発者の会議（[Interop Testing #34](https://github.com/ethereum/pm/issues/1499#issuecomment-2836061807)）で外されました。2021 年の London の [EIP-3541](https://eips.ethereum.org/EIPS/eip-3541) が 0xEF で始まるコードのデプロイを禁止したのは、この形式のための予約で、EOF が有効になったわけではありません。

次の更新は、実行レイヤーが Amsterdam、コンセンサス・レイヤーが Gloas で、2026 年 11 月 10 日時点で mainnet の日付は決まっていません（2 つを合わせた通称は Glamsterdam。[ethereum.org の Glamsterdam](https://ethereum.org/roadmap/glamsterdam/)、予定の詳細は [Ethereum Hard Forks](../ethereum-hard-forks/#今後の予定)）。

本記事で使ったコミットの geth には、図の左上の Amsterdam の命令表（4 個を加えた 153 個）が既にありますが、mainnet の設定に有効化の時刻は無く、現行の EVM の命令ではありません。

---

### EIP と ERC

ここまでの命令の追加は、どれも EIP（Ethereum Improvement Proposal）という文書で提案されました。一方で、[ERC-20](../erc-20/) のようなトークンの規格も、同じ番号の体系の文書です。両者の違いは、ノードの規則を変えるかどうかです。[EIP-1](https://eips.ethereum.org/EIPS/eip-1) は、EIP を以下の種類（type）と分類（category）に分けています。

{{< figure src="images/evm-opcode-history_eip_types.webp" alt="EIP の下に 3 つの種類。灰色の大きな Standards Track の枠の中に 4 つの分類があり、青い Core（命令・ガス・トランザクションの型、原則フォークが要る）、Networking（ノード間通信（devp2p））、Interface（ABI・メソッド名）、ERC（トークン・署名など）。右に Meta（手続き、更新の一覧）と Informational（指針）。Core 以外はフォーク不要" caption="EIP の種類と、ハードフォークが要る範囲" align="center" >}}

上記の図で、原則としてハードフォークが必要なのは、合意の規則（命令・ガス・トランザクションの型など）を変える青い Core だけです。

Networking はノード間の通信（devp2p など）、Interface は言語レベルの規約（メソッド名など）やコントラクトの ABI（関数の呼び出し形式）、ERC はトークン、署名、ウォレットなどアプリケーション層の規格を扱います。Meta は手続きや更新の内容の一覧、Informational は設計上の指針や情報です。

ERC（Ethereum Request for Comments）は、Standards Track の分類の 1 つです。2023 年 10 月 25 日の [ethereum/EIPs の PR #7206](https://github.com/ethereum/EIPs/pull/7206) で ERC の文書は [ethereum/ERCs](https://github.com/ethereum/ERCs) に移りましたが、番号は共通のままで、EIP-1 の分類も変わっていません。

Core の EIP はクライアントのコードを変え、全ノードが同時に切り替える必要があります。ERC は、コントラクトとウォレットが従う約束で、ノードの規則は変えません。例えば ERC-20 に従うトークンは、規格の関数とイベントを持つ普通のコントラクトで、EVM にトークン専用の命令はありません。

なお、図の「Core なら原則ハードフォーク」には例外があります。EIP-1 は合意に必ずしも関わらない変更も Core に含めていて、コードを持つアドレスからのトランザクションを拒む [EIP-3607](https://eips.ethereum.org/EIPS/eip-3607) は、ソフトフォーク（更新前のノードとも互換を保つ更新）として実装できると書かれています。分類だけで、ハードフォークの有無を機械的には判定できません。

<br>

#### 規格の依存関係

規格同士は、文書の先頭の `requires` の欄で依存を表します。以下の図は、debimate の Blockchain Systems のノートで扱う規格から、フォークの要らない規格が、フォークの要る Core の EIP に依存している例だけを選んだものです。コミットを固定した文書から [eip_graph.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm-opcode-history/lab/eip_graph.py) で取り出して描いた図です。矢印が `requires` を表します。

{{< figure src="images/evm-opcode-history_eip_graph.webp" alt="左にフォーク不要（ERC / Interface）の規格が 3 つ（黄土色の ERC-165 対応の問い合わせ、緑の EIP-712 型付きデータの署名、黄土色の ERC-4337 コントラクトのウォレット）、右の青い領域にフォークが要る（Core）の 3 つ（EIP-214 STATICCALL、EIP-155 署名に chain ID、EIP-7702 EOA の委任）。左から右へ 1 本ずつ矢印（requires）がある" caption="フォークの要らない規格が、フォークで入った機能に依存する 3 つの例" align="center" >}}

上記の図の 3 本の矢印は、どれもフォークの要らない規格から Core への依存です。[ERC-165](https://eips.ethereum.org/EIPS/eip-165) は、コントラクトが対応するインターフェースを問い合わせる規格で、問い合わせを書き込みのできない STATICCALL で行うため、Byzantium の [EIP-214](https://eips.ethereum.org/EIPS/eip-214) を前提にしています。

[EIP-712](../eip-712/) は署名に chain ID を含めるので [EIP-155](https://eips.ethereum.org/EIPS/eip-155) に、コントラクトのウォレット（smart account）を扱う [ERC-4337](../erc-4337/) は、EIP-7702 で委任した EOA（EOA delegation）を扱う節があるので EIP-7702 に依存します。つまり、ERC はフォークを必要としませんが、フォークで入った機能の上に乗っている場合があります。

呼び名にも注意が要ります。以下は、よく使う呼び名と、文書に書かれた分類（category）を並べた図です。

{{< figure src="images/evm-opcode-history_names.webp" alt="左によく使う呼び名、右に文書の category。EIP-712 は緑の Interface でフォーク不要。「EIP-1271」は黄土色の ERC でフォーク不要。EIP-1559 は青い Core でフォークが要る" caption="呼び名と分類は一致しない" align="center" >}}

EIP-1 では、ERC の分類の文書は「ERC-番号」、それ以外の分類（Core・Interface など）の文書は「EIP-番号」と呼びます。そのため、署名するデータの形を決める EIP-712 は「EIP」と呼ばれますが、分類は Core ではなく Interface で、フォークは要りません。逆に、「EIP-1271」と書かれることの多いコントラクトの署名の規格は、分類が ERC です。手数料の仕組みを変えた [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559) は Core です。呼び名ではなく、文書の `category` を見る必要があります。

また、EIP の文書には、どこまで確定したかを表す状態（status。Draft・Review・Final など）もあります。Final は文書が確定したことを表すだけで、Core の EIP が mainnet で有効になったことは、別に Meta EIP や更新の一覧で確認します。

---

### データの再現

命令の数とプリコンパイルの表は、geth をコミット ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f に固定して取り出しました。[count_opcodes.sh](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm-opcode-history/lab/count_opcodes.sh) が Go のテスト [zz_count_opcodes_test.go](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm-opcode-history/lab/zz_count_opcodes_test.go) を geth に一時的に置いて実行し、[geth_tables.json](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm-opcode-history/lab/output/geth_tables.json) に保存しました。

規格の依存関係は [eip_graph.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm-opcode-history/lab/eip_graph.py) で [eip_graph.json](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm-opcode-history/lab/output/eip_graph.json) に取り出しています。手順は [README.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm-opcode-history/lab/README.txt)、図の生成元は [figures.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm-opcode-history/figures.py) です。プリコンパイルを呼んだ実験は、EVM のノートの [run.sh](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/evm/lab/run.sh) で再現できます。
