---
title: "Ethereum Hard Forks - EVM の規則は全ノードで同時に切り替わる"
date: 2026-11-10
draft: false
series: ["技術ノート", "Blockchain Systems"]
tags: ["blockchain", "ethereum", "evm", "hard-fork", "smart-contract"]
weight: 21
wrapTables: true
topics: ["Smart Contract"]
---

[Ethereum](https://ethereum.org/) では、ネットワークに参加する多数のコンピュータ（ノード）が、利用者の送った取引を同じ規則で実行し、結果が一致したものだけをブロック（取引をまとめた記録の単位）として受け入れます。

この規則には、コントラクト（チェーンに置いたプログラム）を実行する仮想マシン [EVM](../evm/)（Ethereum Virtual Machine）の命令の一覧と、命令ごとの手数料が含まれます。手数料はガス（gas）という単位で数え、命令の重さに合わせて決まっています。

ハードフォーク（hard fork）は、決めたブロックや時刻を境に、この規則を全てのノードで一斉に切り替える更新です。Ethereum は 2015 年からハードフォークを 20 回ほど行い、更新ごとに Istanbul・Berlin・Cancun のような名前を付けています。

<br>

開発者には、この切り替えが 2 つの形で効きます。1 つ目は、コンパイラが新しい規則の命令を使い始めることです。

例えば [Solidity](https://soliditylang.org/) のコンパイラ（solc）は 0.8.20 から、2023 年 4 月の更新 Shanghai で加わった PUSH0（スタックに 0 を積む命令）を出力します。そのため、solc を上げただけで、Shanghai の規則をまだ取り込んでいない、EVM を動かす別のチェーン（後の節で説明する L2 など）へのデプロイが失敗することがあります。

2 つ目は、デプロイ済みのコードの値段と意味が変わることです。次の図は、3 回の更新をまたいで同じバイトコード（コンパイル済みのコード）を実行した時の様子です。

{{< figure src="images/ethereum-hard-forks_concept.webp" alt="上段は 1 本のブロックの列で、Istanbul・Berlin・Cancun の区間の境目に点線がある。Berlin の境目から、更新しなかったノードが古い規則で伸ばす黄土色の列が分かれている。中段は全区間に渡る「デプロイ済みの同じバイトコード」の帯。下段は区間ごとの値で、SLOAD は Istanbul で 800、Berlin と Cancun で 2100 / 100、SELFDESTRUCT は Istanbul と Berlin でコードを消し、Cancun ではコードを残す。直前の区間から値が変わった箱だけが青い（左端の Istanbul は基準）" caption="フォークの境目で、同じバイトコードの値段と意味が変わる" align="center" >}}

ストレージ（コントラクトが持つ永続的な保存領域）を読む SLOAD 命令は、Istanbul では 800 ガスでしたが、Berlin からは、同じ取引の中で 1 回目に読む時が 2100、2 回目が 100 ガスになりました。コントラクトを消す SELFDESTRUCT 命令は、Cancun からコードを残すようになりました。

黄土色の点線の列は、仮に更新しなかったノードがあった場合に、そのノードが古い規則で伸ばす別の列です。実際の更新では全てのノードが切り替えるので、列は 1 本のままです（次の節で説明します）。

<br>

本記事では、ハードフォークで EVM の何が変わり、開発者のコードにどう影響するのかを説明します。

- ハードフォークは、チェーンが分裂して新しいコインが生まれることなのか。
- デプロイ済みのコントラクトの振る舞いは、更新で変わるのか。
- 最新の solc でコンパイルしたコードは、どのチェーンでも動くのか。
- 規則の更新は、誰がどのような手順で決めるのか。

前半で答えを示し、後半では、フォークを固定したローカルのノードで同じバイトコードを実行して確かめます。ブロックの合意の仕組みだけを変える更新と、価格や投資の話は扱いません。

---

### 計画された規則の更新

ハードフォークと聞くと、チェーンが 2 つに割れて新しいコインが生まれる出来事を想像するかもしれません。しかし、Ethereum のハードフォークのほとんどは、開発者とノードの運用者が事前に合意した計画的な更新で、チェーンは 1 本のままです。[ethereum.org の更新の一覧](https://ethereum.org/ethereum-forks/)に並ぶ更新の多くは、分岐を起こしていません。

規則を変える時は、切り替える境目を先に決め、全てのノードが、新しい規則を実装したノードのソフトウェア（クライアント）を事前に入れておきます。境目の決め方は、時期によって次のように変わってきました。

| 時期 | 境目の決め方 | 例（[execution-specs の更新履歴](https://github.com/ethereum/execution-specs/blob/873ecb3e982ad4311a91cea5aaf2bbb83d306db1/docs/specs/protocol_history.md)） |
| --- | --- | --- |
| 2022 年 6 月の更新まで | ブロックの高さ（先頭から数えた番号） | 2021 年 8 月の London は「ブロック 12965000」 |
| 2022 年 9 月の Paris | [PoW](../proof-of-work/)（計算の競争でブロックを作る方式）の累積の難易度 | 1 回だけの例外 |
| 2023 年 4 月の Shanghai 以降 | ブロックの時刻（timestamp） | 2024 年 3 月の Cancun は「timestamp 1710338135」 |

Paris は The Merge と呼ばれる更新で、ブロックを作る権利の決め方を PoW から [PoS](../proof-of-stake/)（通貨の預け入れの量で決める方式）に変えました。

<br>

各ノードはブロックの取引を自分で実行し、結果の状態がブロックに記録された値と合うかを確かめます。そのため、境目で切り替えなかったノードは、新しいブロックを受け入れられません。古い規則では PUSH0 は無効な命令なので、PUSH0 を使う取引を含むブロックは、取引の結果として変わる残高やストレージ（まとめて状態と呼びます）が古い規則での計算と合わず、無効なブロックと判定されるからです。

{{< figure src="images/ethereum-hard-forks_rules.webp" alt="左はソフトフォーク。灰色の「古い規則で有効」の枠の中に、青い「新しい規則で有効」の枠が収まっていて、古いノードも新しいブロックを受け入れ、ブロックの列は 1 本。右はハードフォーク。青い枠が灰色の枠からはみ出し、はみ出した所に PUSH0 がある。古いノードは新しいブロックを拒み、ブロックの列が黄土色の列に分かれる" caption="ソフトフォークとハードフォークの違い" align="center" >}}

上記の図の左のように、新しい規則が有効なブロックの範囲を狭めるだけなら、古いノードも新しいブロックを受け入れられます。この、古いノードとの互換性を保つ更新はソフトフォーク（soft fork）と呼ばれ、ハードフォークと区別されます（[ethereum.org の用語集](https://ethereum.org/glossary/#soft-fork)）。右のハードフォークでは、古い規則では無効だったブロックが有効になるので、古いノードはついていけません。

分岐が残るのは、一部の参加者が意図して古い規則を使い続けた時です。2016 年、Ethereum の通貨 ETH を集めて使い道を投票で決めるコントラクト The DAO から、不具合を突かれて 360 万 ETH 以上が流出しました。

その後のハードフォークで、資金を回収用のコントラクトへ移す規則に切り替えたノードと、切り替えなかったノードに分かれ、後者の列は今も [Ethereum Classic](https://ethereumclassic.org/) として続いています。

分かれた直後は、片方のチェーンに送った署名済みの取引が、もう片方でもそのまま実行できました。この問題と対策は [Replay Protection](../replay-protection/#eth-と-etc-の分岐) で扱っています。規則の切り替えで履歴が 2 本に分かれる仕組みは [Blockchain Basics](../blockchain-basics/) で、The DAO の資金が流出した経緯は [Reentrancy](../reentrancy/) で説明しています。

---

### デプロイ済みのコントラクトに効く変更

[コントラクト](../smart-contract/)のコードは、デプロイした後に書き換えられません。それでも振る舞いが変わることがあるのは、変わらないのがバイト列だけで、各命令のガスの値と意味はハードフォークで変わるからです。

ハードフォークで EVM に入る変更は、命令の追加、ガスの値の変更、既存の命令の意味の変更の 3 種類で、影響を受けるコードが違います。

{{< note-panels caption="ハードフォークで EVM に入る変更と、影響を受けるコード。" >}}
- title: 命令の追加
  body: "例: PUSH0（Shanghai）、メモリをコピーする MCOPY（Cancun）。"
  items:
  - デプロイ済みのコードは変わらない
  - 新しくコンパイルしたコードが、古い規則のチェーンで動かない
- title: ガスの値の変更
  body: "例: SLOAD の値上げ（Istanbul、Berlin）。"
  items:
  - デプロイ済みのコードの値段が変わる
  - ガスの量を前提にしたコードが失敗する
- title: 命令の意味の変更
  body: "例: SELFDESTRUCT（Cancun）、秘密鍵で操作するアカウントへのコードの委任（Prague）。"
  items:
  - デプロイ済みのコードの結果が変わる
{{< /note-panels >}}

バイトコードは、1 バイトの命令番号（オペコード）を並べた列です。命令の追加がデプロイ済みのコードに効かないのは、新しい命令に割り当てた番号が、それまでは実行すると失敗する無効な命令で、通常のコンパイラの出力に含まれないからです。デプロイ済みのコードに効くのは、残りの 2 つです。以下では、実際に問題になった例を取り上げます。全ての更新で命令がどう増えたかは [EVM Opcode History](../evm-opcode-history/) で数えています。

<br>

#### warm と cold

2019 年 12 月の Istanbul は、SLOAD を 200 から 800 ガスに値上げしました（[EIP-1884](https://eips.ethereum.org/EIPS/eip-1884)）。EIP（Ethereum Improvement Proposal）は規則の変更を提案する文書で、更新ごとに採用する EIP の組が決まります。決まり方は後の「更新を決める手順」の節で説明します。

2021 年 4 月の Berlin は、さらに、取引の中で初めて読むストレージの値（cold）を 2100 ガス、同じ取引の中で既に読んだ値（warm）を 100 ガスに分けました（[EIP-2929](https://eips.ethereum.org/EIPS/eip-2929)）。別のコントラクトを呼ぶ時のアドレスの参照にも同じ区別があり、初回は 2600、2 回目以降は 100 ガスです。ノードのディスクから初めて読み出す処理が重く、ガスの値と実際の負荷が離れていたからです。

冒頭の図の「2100 / 100」は、この 1 回目と 2 回目の値です。

同時に入った [EIP-2930](https://eips.ethereum.org/EIPS/eip-2930) で、取引に参照先の一覧（access list）を付けられるようになりました。一覧に書いたストレージの値は、取引の開始時点から warm になります。代わりに、一覧のアドレス 1 件につき 2400 ガス、ストレージのキー 1 件につき 1900 ガスを取引の開始時に払います。

{{< figure src="images/ethereum-hard-forks_warm.webp" alt="横棒が 2 本。access list なしは、呼び出し先のアドレスの初回 2,600、ストレージの値の初回 2,100、2 回目 100 で計 4,800。access list ありは、開始時にアドレス 1 件の 2,400 とキー 1 件の 1,900 の計 4,300 を先払いし、呼び出しと 2 回の読み出しは warm で 100 ずつ、計 4,600" caption="別のコントラクトを呼び、その中で同じ値を 2 回読む時のガス（Berlin 以降）" align="center" >}}

上記の図のように、access list はガスを先払いして、呼び出しの中の参照を全て warm にする仕組みです。合計はあまり変わりませんが（この例では 4,800 と 4,600）、呼び出しと読み出しのガスは 100 ずつで済みます。

これは、次の `transfer` のように、使えるガスに上限がある呼び出しの中で効きます。後の実験では、この性質で、Berlin 以降に失敗するようになった送金を再び通します。

<br>

#### 2300 ガスの transfer

ETH をコントラクトに送ると、受け取る側のコントラクトのコードが動きます。呼び出す側は、そのコードが使ってよいガスの量に上限を付けて呼び出せます。

Solidity の `transfer` は、ETH を送る時に、受け取る側のコードに 2300 ガスだけを渡します。[Solidity のドキュメント](https://docs.soliditylang.org/en/v0.8.28/contracts.html#receive-ether-function)は、2300 ガスでは基本的なログを出す程度の処理しかできないと説明しています。[再入](../reentrancy/)（reentrancy、呼び出しの途中で同じコントラクトを呼び返すこと）の対策として、受け取る側が何もできないこの少なさを当てにしたコードもありました。

しかし、この前提はガスの値が変わらないことに依存しています。Istanbul で SLOAD が 800 ガスになった時、EIP-1884 は、受け取る時にストレージを読むコントラクトが 2300 ガスを超える場合があると、互換性の節で警告しました。後の実験では、ストレージを 3 か所読むだけの受け取り側への送金が、Istanbul から失敗します。

<br>

#### 延期された Constantinople

値上げだけでなく、値下げで壊れかけた例もあります。2019 年の Constantinople は、ストレージに書く SSTORE 命令を安くする [EIP-1283](https://eips.ethereum.org/EIPS/eip-1283) を含んでいました。同じ取引の中で既に書き換えたスロット（ストレージの 1 か所）への再書き込みが 200 ガスになるので、2300 ガスの中でも、受け取る側が送金元を呼び返してそのストレージを書き換えられるようになり、`transfer` なら再入されないと考えていた既存のコントラクトの一部が攻撃できる状態になります。

スマートコントラクトの監査会社 ChainSecurity がこの問題を報告し、更新は 2019 年 1 月の予定の直前に[延期されました](https://blog.ethereum.org/2019/01/15/security-alert-ethereum-constantinople-postponement)。Constantinople は、EIP-1283 を外す Petersburg という更新と同時に、2019 年 2 月に出し直されています。

この件の後も、2300 ガスを当てにする書き方は残りました。Solidity 0.8.31 は、`send` と `transfer` に非推奨の警告を出すようになりました。[リリースのお知らせ](https://www.soliditylang.org/blog/2025/12/03/solidity-0.8.31-release-announcement/)は、2300 ガスの設計が「命令の値段が変わらない」という暗黙の前提に立っていたことを理由に挙げ、渡すガスを制限しない低レベルの呼び出し `call` に空のデータを渡して使うよう勧めています。

<br>

#### SELFDESTRUCT の意味

SELFDESTRUCT は、コントラクトのコードとストレージを消し、残高を指定先に送る命令でした。2024 年 3 月の Cancun の [EIP-6780](https://eips.ethereum.org/EIPS/eip-6780) から、コードとストレージを消すのは、コントラクトを作成したのと同じ取引の中で実行した場合だけになりました。別の取引で実行すると、残高を送って実行を止めるだけで、コードもストレージも残ります。

この変更で、作成先のアドレスを事前に決められる [CREATE2](../ethereum-address/) と SELFDESTRUCT を繰り返し、同じアドレスに別のコードを置き直す手法（[metamorphic contract](../metamorphic-contract/)）は使えなくなりました。

コントラクトを「消して止める」設計も、Cancun 以降はコードが残ったまま呼び出せる状態になります。処理を別のコントラクトに転送するプロキシで、転送先のコードを SELFDESTRUCT で消された事故があり、この変更がその種の事故にどう効くかは [Upgradeable Proxy](../upgradeable-proxy/#初期化関数と初期化を忘れた事故) で扱っています。

<br>

#### EOA の委任

Ethereum のアカウントには、秘密鍵で操作する通常のアカウント（EOA、Externally Owned Account）と、コードを持つコントラクトの 2 種類があります。

2025 年 5 月の Prague の [EIP-7702](https://eips.ethereum.org/EIPS/eip-7702) で、EOA のアドレスに、指定したコントラクトのコードを指す印を書き込めるようになりました。印を書いた EOA を呼ぶと、そのコードが EOA 自身のアドレスで動きます。これを委任と呼びます。仕組みは [Ethereum Account Model](../ethereum-account-model/)、取引の型は [Ethereum Transaction](../ethereum-transaction/) で説明しています。

この変更で、既存のコントラクトが使っていた 2 つの判定の意味が変わりました。1 つは、相手のコードの大きさを返す EXTCODESIZE 命令です。大きさが 0 なら相手は EOA だと判定するコードがありましたが、委任した EOA に対しては、委任先のアドレスを示す 23 バイトのデータの大きさを返します。

もう 1 つは `require(msg.sender == tx.origin)` です。`msg.sender` は直接の呼び出し元、`tx.origin` は取引に署名した EOA で、2 つが等しければ、間に別のコントラクトを挟まずに EOA から呼ばれたと判断できました。

{{< figure src="images/ethereum-hard-forks_delegation.webp" alt="上段の以前は、EOA が署名した取引がコントラクト B を経てコントラクト A を呼び、A では msg.sender = B ≠ tx.origin なので拒否できた。下段の Prague 以降は、委任先のコードを持つ EOA が自分のアドレスのまま A を呼び、msg.sender = EOA = tx.origin となって通ってしまう。委任先のコードは 1 つの取引の中で A を何度でも呼べる" caption="msg.sender と tx.origin の判定が通ってしまう流れ" align="center" >}}

この判定は、コントラクトを経由して 1 つの取引の中に複数の操作をまとめることを禁じ、再入や[サンドイッチ攻撃](../mev/)（他人の取引の前後に自分の取引を挟んで価格差を取る攻撃）を防ぐために使われてきました。

この目的では、この書き方は成り立たなくなりました（呼び出し元が EOA かどうかの確認には影響しないと、EIP は書いています）。委任した EOA は、取引の送り主のまま、委任先のコードとして他のコントラクトを 1 つの取引の中で何度でも呼べるからです（EIP-7702 の設計の理由とセキュリティの節）。

---

### solc の evmVersion

最新の solc でコンパイルすれば、どのチェーンでも動くと考えがちです。しかし、solc はどのフォークの命令を使うかを evmVersion という設定で決めていて、その既定値は、Ethereum の mainnet（本番のネットワーク）で新しいフォークが有効になる度に上がってきました。

{{< figure src="images/ethereum-hard-forks_solc.webp" alt="2023 年から 2026 年の時間軸に 2 本の線。上の Ethereum mainnet には Shanghai 2023-04、Cancun 2024-03、Prague 2025-05、Osaka 2025-12。下の solc の既定の evmVersion には shanghai（0.8.20）、cancun（0.8.25）、prague（0.8.30）、osaka（0.8.31）が、それぞれ mainnet の更新とほぼ同じ位置に並ぶ。下の黄土色の帯に、L2 などの別の EVM のチェーンは、どのフォークまで取り込むかを各自で決める、とある" caption="mainnet の更新と solc の既定の evmVersion" align="center" >}}

上記の図は、[Solidity の Changelog](https://github.com/argotorg/solidity/blob/v0.8.38/Changelog.md) に基づく既定値の変化です。0.8.20 で shanghai、0.8.25 で cancun、0.8.30 で prague、0.8.31 で osaka になり、いずれも mainnet の更新と同じ月か翌月です。

一方で、Ethereum の上で動く L2（[Rollup](../rollup/) など、Ethereum に記録を預けて動く別のチェーン）や、EVM を採用した別のチェーンは、どのフォークの規則まで取り込むかを各自で決めます。[0.8.20 のリリースのお知らせ](https://soliditylang.org/blog/2023/05/10/solidity-0.8.20-release-announcement/)も、PUSH0 にまだ対応していない L2 などにデプロイする場合は、適切な EVM のバージョンを選ばないとデプロイが失敗すると注意しています。

そのため、デプロイ先が対応しているフォークを確かめ、solc の `--evm-version`（standard JSON では `settings.evmVersion`）で指定します（[Solidity のドキュメント](https://docs.soliditylang.org/en/v0.8.28/using-the-compiler.html#setting-the-evm-version-to-target)）。

<br>

指定を誤った時に失敗する場所は、新しい命令がバイトコードのどこに入ったかで変わります。コントラクトのバイトコードは、デプロイの時に 1 回だけ動く部分と、保存されて呼び出しの度に動く部分に分かれているからです。

{{< note-steps caption="コントラクトをデプロイしてから呼ぶまで。" >}}
- title: デプロイの取引
  body: 初期化用コード（init code）を送る。
- title: 初期化用コードを実行
  body: 1 回だけ実行され、実行用コードを返す。
- title: 実行用コードを保存
  body: 実行用コード（runtime code）がアドレスに置かれる。
- title: 関数の呼び出し
  body: 呼ぶ度に実行用コードを実行する。
{{< /note-steps >}}

初期化用コードに未対応の命令があればデプロイが失敗し、実行用コードだけにあればデプロイは成功して、関数を呼んだ時に失敗します。

ソースに、新しい命令でしか書けない機能を使った場合は、もっと早く気付けます。例えば、取引の終わりに消える保存領域（transient storage）の変数は、cancun より古い evmVersion を指定するとコンパイルの時点でエラーになります。一方で、同じ処理を古い命令でも書ける場合は、エラーにならずに使う命令だけが変わります。

後の実験で、デプロイで失敗する場合、デプロイが通ってしまう場合、コンパイルでエラーになる場合の 3 つを確かめます。

---

### 更新を決める手順

Ethereum には、規則の更新を決める管理者がいません。変更の提案は前の節で触れた EIP という文書で出し、[EIP-1](https://eips.ethereum.org/EIPS/eip-1) が書式と状態の遷移を定めています。全ノードが同時に切り替える必要がある変更は、Core（ノードの規則を変える分類）の EIP です（トークンの規格を決める ERC などの他の分類との違いは [EVM Opcode History](../evm-opcode-history/#eip-と-erc)）。

どの EIP をどの更新に入れるかは、クライアントの開発者が集まる All Core Devs という公開の会議で議論します。議事録と議題は [ethereum/pm](https://github.com/ethereum/pm) で公開されています。更新ごとに、対象の EIP を並べた Meta EIP という一覧の文書があり、[EIP-7723](https://eips.ethereum.org/EIPS/eip-7723) は、個々の EIP がその一覧の中で「提案」「検討」「予定」と段階を進める手順を定めています。

{{< note-steps caption="EIP が mainnet で有効になるまで。" >}}
- title: EIP の提出
  body: 変更の仕様を EIP として公開する。
- title: All Core Devs の会議
  body: 提案・検討・予定と段階を進め、対象の更新を決める。
- title: devnet
  body: 開発者向けの短期間のネットワークで、複数のクライアントが同じ結果を出すかを試す。
- title: 公開テストネット
  body: 試験用のネットワーク（Sepolia・Hoodi など）で決めた時刻に有効にする。
- title: mainnet
  body: 時刻を設定したクライアントを全ノードが入れ、その時刻で切り替える。
{{< /note-steps >}}

devnet で試すのは、Ethereum には実装の異なるクライアントが複数あるからです。同じブロックから同じ状態を計算できなければ、更新の時点でノードの間に分岐が起きます。mainnet の時刻は、通常は[テストネット](../mainnet-and-testnet/#ハードフォークはテストネットから)（本番と同じソフトウェアで動く試験用のネットワーク）で問題が出なかったことを確かめてから決めます。

<br>

Ethereum のノードは、取引を実行する実行層（execution layer）のクライアントと、ブロックの合意を担う合意層（consensus layer）のクライアントを組み合わせて動きます。そのため、The Merge 以降の更新には、実行層と合意層の 2 つの名前があります。実行層は開発者会議の Devcon などの開催都市、合意層は恒星の名前で、2 つを組み合わせた通称で呼ばれます。

| 実行層 | 合意層 | 通称 | mainnet で有効になった日（UTC） |
| --- | --- | --- | --- |
| Shanghai | Capella | Shapella | 2023-04-12 |
| Cancun | Deneb | Dencun | 2024-03-13 |
| Prague | Electra | Pectra | 2025-05-07 |
| Osaka | Fulu | Fusaka | 2025-12-03 |

日付は [ethereum.org の更新の一覧](https://ethereum.org/ethereum-forks/)と execution-specs の更新履歴に基づきます。EVM の規則を決めるのは実行層なので、solc の evmVersion などの設定では Shanghai・Cancun のような実行層の名前を使います。

---

### フォークを切り替えた実験

同じバイトコードを複数のフォークで実行して、ここまでの変更を確かめます。

開発用のローカルノードである [Foundry の Anvil](https://getfoundry.sh/anvil/overview) を 8 個起動し、`--hardfork` オプションで petersburg（EIP-1283 を外した Constantinople）から osaka までを 1 つずつ固定しました（The Merge の paris は、本記事で確かめる命令とガスに変化が無いので省いています）。

Anvil と solc の設定ではフォーク名を小文字で書くので、以下の図と出力も小文字です。

ノードは [Docker](https://www.docker.com/) の専用のネットワークの中だけで動かし、公開のネットワークには接続しません。取引には Anvil の既定のテスト用アカウントだけを使っています。コンテナの起動から後始末までは [lab/run.sh](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/run.sh) が行い、リポジトリのルートで次を実行すると約 10 秒で終わります。使ったイメージの版は [lab/README.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/README.txt) に記録しています。

```bash
bash content/notes/blockchain-systems/ethereum-hard-forks/lab/run.sh
```

<br>

#### 新しい命令

確かめたのは、次の 5 つの命令です。

| 命令 | 何をするか | 追加された更新 |
| --- | --- | --- |
| BASEFEE | ブロックの[基本料金（base fee）](../gas-eip-1559/#base-fee-の焼却と-priority-fee)を読む | London（[EIP-3198](https://eips.ethereum.org/EIPS/eip-3198)） |
| PUSH0 | スタックに 0 を積む | Shanghai（[EIP-3855](https://eips.ethereum.org/EIPS/eip-3855)） |
| TSTORE・TLOAD | 取引の終わりに消える保存領域に書く・読む | Cancun（[EIP-1153](https://eips.ethereum.org/EIPS/eip-1153)） |
| MCOPY | メモリの中で値をコピーする | Cancun（[EIP-5656](https://eips.ethereum.org/EIPS/eip-5656)） |
| CLZ | 先頭の 0 のビットを数える | Osaka（[EIP-7939](https://eips.ethereum.org/EIPS/eip-7939)） |

各命令を初期化用コードとして並べ、宛先を付けずに [`eth_call`](https://ethereum.org/developers/docs/apis/json-rpc/#eth-call)（ノードを操作する HTTP の API である JSON-RPC のメソッドの 1 つ）で送りました。宛先の無い `eth_call` は、[JSON-RPC の仕様](https://github.com/ethereum/execution-apis/blob/main/src/schemas/transaction.yaml)の通りコントラクトの作成を模擬して初期化用コードを実行し、結果を状態に保存しないので、取引を送らずに命令の可否を試せます。バイトコードは、命令を 1 つずつ確かめるために手で組み立てた学習用のもので、監査していません。

{{< figure src="images/ethereum-hard-forks_opcodes.webp" alt="行がフォーク（petersburg から osaka）、列が BASEFEE・PUSH0・TSTORE・MCOPY・CLZ と SLOAD のガスの 1 回目・2 回目。BASEFEE は london から、PUSH0 は shanghai から、TSTORE と MCOPY は cancun から、CLZ は osaka から「動く」で、それより前は「失敗」。SLOAD は petersburg で 200 / 200、istanbul で 800 / 800、berlin 以降は 2100 / 100" caption="同じバイトコードを 8 つのフォークで実行した結果" align="center" >}}

図の TSTORE の列は、TSTORE で書いた値を TLOAD で読み戻した結果です。各命令は、追加されたフォークより前では `NotActivated`（上記の図の「失敗」）というエラーで失敗し、追加されたフォーク以降では同じ値を返しました。

右の 2 列は、同じスロットを 1 回の `eth_call` の中で（同じ取引の中と同じ扱いで）2 回読んだ SLOAD のガスです。Istanbul で 4 倍になり、Berlin からは 1 回目と 2 回目で 21 倍の差が付いています。

SLOAD のガスは、残りのガスを返す GAS 命令を SLOAD の前後に置き、差から間の PUSH1・POP・GAS の 7 ガスを引いて求めています。以下は [lab/probe.py](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/probe.py) の抜粋です。`rpc(fork, ...)` は、そのフォークの Anvil に JSON-RPC で要求を送る補助関数です。

```python
RETURN_WORD = '60005260206000f3'  # PUSH1 0 MSTORE PUSH1 32 PUSH1 0 RETURN
PROBES = [
    ('BASEFEE', 'London', '48' + RETURN_WORD),
    ('PUSH0', 'Shanghai', '5f' + RETURN_WORD),
    ('TSTORE', 'Cancun', '6007' '6000' '5d' '6000' '5c' + RETURN_WORD),  # TSTORE(0, 7); TLOAD(0)
    ('MCOPY', 'Cancun', '602a600052' '6020' '6000' '6020' '5e' '60206020f3'),  # copy mem[0:32] to mem[32:64]
    ('CLZ', 'Osaka', '6001' '1e' + RETURN_WORD),  # count leading zeros of 1
]
for fork in FORKS:
    for name, _, code in PROBES:
        try:
            value = int(rpc(fork, 'eth_call', {'data': '0x' + code}, 'latest'), 16)
            cells.append(f'ok={value}')
        except RpcError as e:
            cells.append('error')

# GAS, SLOAD(0), GAS, SLOAD(0), GAS. Each gap = PUSH1(3) + SLOAD + POP(2) + GAS(2).
SLOAD_TWICE = '5a' '600054' '50' '5a' '600054' '50' '5a' '604052' '602052' '600052' '60606000f3'
raw = rpc(fork, 'eth_call', {'data': '0x' + SLOAD_TWICE}, 'latest')[2:]
g0, g1, g2 = (int(raw[i:i + 64], 16) for i in range(0, 192, 64))
lines.append(f'{fork:<10} | {g0 - g1 - 7:>9} | {g1 - g2 - 7:>9}')
```

<details>
<summary>probe.py の全体（transfer・SELFDESTRUCT・evmVersion の検査を含む）</summary>

```python
#!/usr/bin/env python3
"""Run the same EVM bytecode on Anvil nodes pinned to different hard forks.

Local-only. Called by run.sh inside a container on a private Docker network.
The bytecode below is hand-assembled for this experiment and is not audited.
"""
import json
import os
from pathlib import Path
import time
import urllib.request

FORKS = os.environ['FORKS'].split()
OUT = Path('output')
BUILD = OUT / 'build'
lines = []


class RpcError(Exception):
    pass


def rpc(fork, method, *params):
    url = f'http://note-ethereum-hard-forks-{fork}:8545'
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    request = urllib.request.Request(url, body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.load(response)
    if 'error' in result:
        raise RpcError(result['error']['message'])
    return result['result']


def wait_ready(fork):
    for _ in range(200):
        try:
            return rpc(fork, 'eth_accounts')
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(fork)


def status(receipt):
    return int(receipt['status'], 16)


def send(fork, tx):
    tx = {'gas': hex(1_000_000), 'gasPrice': hex(2_000_000_000), **tx}
    txhash = rpc(fork, 'eth_sendTransaction', tx)
    for _ in range(100):
        receipt = rpc(fork, 'eth_getTransactionReceipt', txhash)
        if receipt:
            return receipt
        time.sleep(0.05)
    raise TimeoutError(txhash)


def initcode(runtime):
    """Init code that copies `runtime` (hex) into memory and returns it as the deployed code."""
    n = len(runtime) // 2
    assert n < 256
    return f'60{n:02x}600c600039{"60%02x" % n}6000f3' + runtime


def solc_output(name):
    text = (BUILD / name).read_text()
    sections = {}
    key = None
    for line in text.splitlines():
        if line.endswith(':') and not line.startswith(' '):
            key = line[:-1]
        elif key and line.strip():
            sections.setdefault(key, []).append(line.strip())
    return sections


accounts = {f: wait_ready(f) for f in FORKS}

# 1. New opcodes: run init code with eth_call (no `to` = simulated contract creation).
#    Each snippet leaves one 32-byte word in memory[0:32] and returns it.
RETURN_WORD = '60005260206000f3'  # PUSH1 0 MSTORE PUSH1 32 PUSH1 0 RETURN
PROBES = [
    ('BASEFEE', 'London', '48' + RETURN_WORD),
    ('PUSH0', 'Shanghai', '5f' + RETURN_WORD),
    ('TSTORE', 'Cancun', '6007' '6000' '5d' '6000' '5c' + RETURN_WORD),  # TSTORE(0, 7); TLOAD(0)
    ('MCOPY', 'Cancun', '602a600052' '6020' '6000' '6020' '5e' '60206020f3'),  # copy mem[0:32] to mem[32:64]
    ('CLZ', 'Osaka', '6001' '1e' + RETURN_WORD),  # count leading zeros of 1
]
lines.append('== opcode probes (eth_call of init code) ==')
lines.append('fork       | ' + ' | '.join(name for name, _, _ in PROBES))
errors = set()
for fork in FORKS:
    cells = []
    for name, _, code in PROBES:
        try:
            value = int(rpc(fork, 'eth_call', {'data': '0x' + code}, 'latest'), 16)
            cells.append(f'ok={value}')
        except RpcError as e:
            errors.add(str(e))
            cells.append('error')
    lines.append(f'{fork:<10} | ' + ' | '.join(cells))
lines.append('error messages: ' + '; '.join(sorted(errors)))

# 2. SLOAD gas: GAS, SLOAD(0), GAS, SLOAD(0), GAS. Each gap = PUSH1(3) + SLOAD + POP(2) + GAS(2).
SLOAD_TWICE = '5a' '600054' '50' '5a' '600054' '50' '5a' '604052' '602052' '600052' '60606000f3'
lines.append('')
lines.append('== SLOAD of the same slot twice in one call ==')
lines.append('fork       | 1st SLOAD | 2nd SLOAD')
for fork in FORKS:
    raw = rpc(fork, 'eth_call', {'data': '0x' + SLOAD_TWICE}, 'latest')[2:]
    g0, g1, g2 = (int(raw[i:i + 64], 16) for i in range(0, 192, 64))
    lines.append(f'{fork:<10} | {g0 - g1 - 7:>9} | {g1 - g2 - 7:>9}')

# 3. Solidity transfer() forwards 2300 gas. The receiver reads 3 storage slots on receipt.
RECEIVER = '600054' '50' '600154' '50' '600254' '50' '00'  # SLOAD(0), SLOAD(1), SLOAD(2), STOP
sender = solc_output('Sender.txt')
sender_bin = sender['Binary'][0]
pay = next(h.split(':')[0] for h in sender['Function signatures'] if h.endswith('pay(address)'))
lines.append('')
lines.append('== transfer(1 wei) to a receiver that reads 3 slots ==')
lines.append('fork       | plain tx | with access list')
for fork in FORKS:
    me = accounts[fork][0]
    receiver = send(fork, {'from': me, 'data': '0x' + initcode(RECEIVER)})['contractAddress']
    contract = send(fork, {'from': me, 'data': '0x' + sender_bin})['contractAddress']
    call = {'from': me, 'to': contract, 'value': '0x1', 'data': '0x' + pay + receiver[2:].lower().rjust(64, '0')}
    plain = status(send(fork, call))
    if fork in ('petersburg', 'istanbul'):
        listed = '-'  # access lists (EIP-2930) start at Berlin
    else:
        slots = ['0x' + f'{i:064x}' for i in range(3)]
        listed = status(send(fork, {**call, 'accessList': [{'address': receiver, 'storageKeys': slots}]}))
    lines.append(f'{fork:<10} | {plain:<8} | {listed}')

# 4. SELFDESTRUCT in a later transaction than the one that created the contract.
SELF_DESTRUCT = '33ff'  # CALLER SELFDESTRUCT
lines.append('')
lines.append('== SELFDESTRUCT called in a later transaction ==')
lines.append('fork       | code before | code after | balance after')
for fork in FORKS:
    me = accounts[fork][0]
    target = send(fork, {'from': me, 'value': hex(1000), 'data': '0x' + initcode(SELF_DESTRUCT)})['contractAddress']
    before = rpc(fork, 'eth_getCode', target, 'latest')
    assert status(send(fork, {'from': me, 'to': target})) == 1
    after = rpc(fork, 'eth_getCode', target, 'latest')
    balance = int(rpc(fork, 'eth_getBalance', target, 'latest'), 16)
    lines.append(f'{fork:<10} | {before:<11} | {after:<10} | {balance}')

# 5. The same Solidity source compiled for different evmVersion values.
lines.append('')
lines.append('== Copy.sol compiled with solc --evm-version ==')
lines.append('evmVersion | bytes | PUSH0 | MCOPY | deploy: london | shanghai | cancun')
for version in ('paris', 'shanghai', 'cancun'):
    out = solc_output(f'Copy.{version}.txt')
    code = out['Binary'][0]
    ops = out['Opcodes'][0].split()
    statuses = []
    for fork in ('london', 'shanghai', 'cancun'):
        statuses.append(str(status(send(fork, {'from': accounts[fork][0], 'data': '0x' + code}))))
    lines.append(f'{version:<10} | {len(code) // 2:>5} | {ops.count("PUSH0"):>5} | {ops.count("MCOPY"):>5} | '
                 + ' | '.join(statuses))
for version in ('shanghai', 'cancun'):
    text = (BUILD / f'Guard.{version}.txt').read_text()
    result = 'compiled' if 'Binary:' in text else next(l for l in text.splitlines() if l.strip())
    lines.append(f'Guard.sol (transient) with {version}: {result}')

summary = '\n'.join(lines) + '\n'
(OUT / 'summary.txt').write_text(summary)
print(summary, end='')
```

</details>

<details>
<summary>命令の可否と SLOAD のガスの出力</summary>

```text
== opcode probes (eth_call of init code) ==
fork       | BASEFEE | PUSH0 | TSTORE | MCOPY | CLZ
petersburg | error | error | error | error | error
istanbul   | error | error | error | error | error
berlin     | error | error | error | error | error
london     | ok=1000000000 | error | error | error | error
shanghai   | ok=1000000000 | ok=0 | error | error | error
cancun     | ok=1000000000 | ok=0 | ok=7 | ok=42 | error
prague     | ok=1000000000 | ok=0 | ok=7 | ok=42 | error
osaka      | ok=1000000000 | ok=0 | ok=7 | ok=42 | ok=255
error messages: EVM error NotActivated

== SLOAD of the same slot twice in one call ==
fork       | 1st SLOAD | 2nd SLOAD
petersburg |       200 |       200
istanbul   |       800 |       800
berlin     |      2100 |       100
london     |      2100 |       100
shanghai   |      2100 |       100
cancun     |      2100 |       100
prague     |      2100 |       100
osaka      |      2100 |       100
```

全体は [summary.txt](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/output/summary.txt) にあります。

</details>

<br>

#### 2300 ガスの送金

次に、受け取る側のコードを変えずに、Solidity の `transfer` で 1 wei（ETH の最小単位）を送る取引を各フォークで送りました。受け取る側は、ETH を受け取るとストレージを 3 か所読むだけのコードです。

送る側の [Sender.sol](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/Sender.sol) は `payable(to).transfer(msg.value)` を呼ぶだけで、全てのフォークで動くように evmVersion を petersburg にしてコンパイルしています。受け取る側が 3 か所を読むのに要るガスは、以下の通りです。

{{< figure src="images/ethereum-hard-forks_transfer.webp" alt="横棒グラフ。受け取る側の SLOAD 3 回のガスは、petersburg が 600 で成功、istanbul が 2,400 で失敗、berlin から osaka が 6,300 で失敗、access list を付けると 300 で成功。2300 の位置に transfer が渡すガスの点線がある" caption="SLOAD 3 回のガスと transfer が渡す 2300 ガス" align="center" >}}

棒の長さは、上記で測った SLOAD のガスの 3 倍です。

petersburg で成功した送金が、同じバイトコードのまま istanbul 以降で失敗しました。SLOAD の値上げで、3 回の読み出しが 2300 ガスに収まらなくなったからです。Berlin 以降は、3 つのスロットを access list に書くと warm になり、送金が再び成功しました。access list の先払いは取引の開始時に送り主が払うので、`transfer` が渡す 2300 ガスの枠からは引かれず、枠の中の SLOAD は warm の 100 × 3 = 300 ガスで済みます。

<details>
<summary>transfer の出力（status の 1 は成功、0 は失敗）</summary>

```text
== transfer(1 wei) to a receiver that reads 3 slots ==
fork       | plain tx | with access list
petersburg | 1        | -
istanbul   | 0        | -
berlin     | 0        | 1
london     | 0        | 1
shanghai   | 0        | 1
cancun     | 0        | 1
prague     | 0        | 1
osaka      | 0        | 1
```

</details>

<br>

#### 別の取引での SELFDESTRUCT

デプロイとは別の取引で `CALLER SELFDESTRUCT`（0x33ff、呼び出し元へ残高を送る）を実行しました。残高はどのフォークでも送り出されて 0 になりましたが、コードは shanghai まで消え（出力の `0x` は空のコード）、cancun 以降は残りました。以下は、境目の 2 つのフォークの[出力](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/output/summary.txt)です。

```text
== SELFDESTRUCT called in a later transaction ==
fork       | code before | code after | balance after
shanghai   | 0x33ff      | 0x         | 0
cancun     | 0x33ff      | 0x33ff     | 0
```

<br>

#### evmVersion を変えたコンパイル

最後に、solc 0.8.28 で 3 つの evmVersion（PUSH0 より前の paris、shanghai、cancun）を指定し、[Copy.sol](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/Copy.sol) をコンパイルしました。Copy.sol は、受け取ったバイト列を `bytes.concat` で 2 回つなげて返す関数 `twice` だけを持つコントラクトです。できたバイトコードは、それぞれ london・shanghai・cancun の Anvil にデプロイしています。

{{< figure src="images/ethereum-hard-forks_evmversion.webp" alt="行が evmVersion の paris・shanghai・cancun、列がデプロイ先の london・shanghai・cancun の 3 行 3 列。paris は PUSH0 0 個・MCOPY 0 個で全て成功。shanghai は PUSH0 38 個・MCOPY 0 個で london だけ失敗。cancun は PUSH0 37 個・MCOPY 1 個で london だけ失敗。下に、cancun 向けの MCOPY は呼び出し時に実行され、デプロイ時には実行されないとある" caption="同じ Copy.sol を 3 つの evmVersion でコンパイルし、3 つのフォークにデプロイした結果" align="center" >}}

同じソースでも、shanghai 向けには PUSH0 が 38 個入り、cancun 向けには実行用コードに MCOPY が 1 個入りました。PUSH0 は初期化用コードにも入るので、shanghai 向けと cancun 向けのコードは、london のノードではデプロイに失敗します。

一方で、cancun 向けのコードは shanghai のノードでもデプロイに成功しました。MCOPY は実行用コードにだけあり、デプロイの時には実行されないからです。このコードは、`twice` を呼んだ時に初めて失敗するはずです（実験では呼び出しまでは試していません）。

transient storage の変数を書いた [Guard.sol](https://github.com/nao1215/debimate/blob/main/content/notes/blockchain-systems/ethereum-hard-forks/lab/Guard.sol) は、shanghai を指定するとコンパイルの時点でエラーになり、cancun では通りました。

<details>
<summary>evmVersion を変えたコンパイルの出力（deploy の 1 は成功、0 は失敗）</summary>

```text
== Copy.sol compiled with solc --evm-version ==
evmVersion | bytes | PUSH0 | MCOPY | deploy: london | shanghai | cancun
paris      |   900 |     0 |     0 | 1 | 1 | 1
shanghai   |   869 |    38 |     0 | 0 | 1 | 1
cancun     |   843 |    37 |     1 | 0 | 1 | 1
Guard.sol (transient) with shanghai: Error: Transient storage is not supported by EVM versions older than cancun.
Guard.sol (transient) with cancun: compiled
```

</details>

---

### 今後の予定

2026 年 11 月 11 日時点で、mainnet で最後に有効になった、名前の付いた更新は Osaka/Fulu（Fusaka、2025-12-03）です。その後は、blob に関わる値だけを変える小さな更新が 2 回ありました。

blob は、L2 がデータを安く載せるために取引に添える、一時的なデータです。2025 年 12 月 9 日と 2026 年 1 月 7 日に、ブロックに載せる blob の数の目標・上限と、blob の手数料の変わり方だけを変える BPO（Blob Parameter Only）フォークが有効になりました（[EIP-7607](https://eips.ethereum.org/EIPS/eip-7607)、[EIP-7892](https://eips.ethereum.org/EIPS/eip-7892)。値の推移は [Blob](../blob/#blob-の手数料) で扱っています）。

次の名前の付いた更新は、実行層が Amsterdam、合意層が Gloas で、通称は Glamsterdam です。下の図は、Fusaka 以降の動きと Glamsterdam の予定です。

{{< figure src="images/ethereum-hard-forks_schedule.webp" alt="2025 年 12 月から 2026 年 12 月の時間軸に mainnet・Sepolia・Hoodi の 3 行。mainnet には Fusaka（2025-12-03）、BPO1（2025-12-09）、BPO2（2026-01-07）の青い点があり、Glamsterdam の日付は未定と書かれている。Sepolia には Glamsterdam（2026-10-06）の青い点。Hoodi には 2026-10-26 の予定を保留した黄土色の点線の点。2026-11-11 に本記事の時点を示す縦の点線" caption="Fusaka 以降の更新と、Glamsterdam の予定（2026 年 11 月 11 日時点）" align="center" >}}

Glamsterdam の Meta EIP の [EIP-7773](https://github.com/ethereum/EIPs/blob/f1ade090fd315895461fc3e249cb1a675aeb55a9/EIPS/eip-7773.md)（2026-10-22 のコミット）には、テストネットの [Sepolia](https://github.com/eth-clients/sepolia) で 2026-10-06、[Hoodi](https://github.com/eth-clients/hoodi) で 2026-10-26 に有効になる時刻が書かれ、mainnet の時刻は空欄です。

ただし Hoodi の予定は、実行層を扱う All Core Devs の会議（ACDE、All Core Devs Execution）の[第 248 回](https://github.com/ethereum/pm/issues/2267)で、ガスの値を変える EIP-8037 と EIP-8038 へのセキュリティ上の懸念が議論され、保留になりました。

会議の issue には、ChainSecurity の調査として、残りのガス（Solidity の `gasleft()`）が実行の途中で増える場合があるなど、ガスの値を前提にしたコントラクトが壊れる例が寄せられています。Constantinople を止めたのと同じ会社が、同じ種類の問題を指摘した形です。クライアントは、予定を取り除いたリリースを出しています（例: 実行層のクライアントの 1 つ [Nethermind 2.2.1](https://github.com/NethermindEth/nethermind/releases/tag/2.2.1)、2026-10-22）。2026 年 11 月 11 日時点で、新しい日付は決まっていません。

<br>

同じ Meta EIP の予定（Scheduled for Inclusion）には、本記事で扱ったガスや SELFDESTRUCT に関わる次の EIP が含まれています。

| EIP | 変わること |
| --- | --- |
| [EIP-8038](https://eips.ethereum.org/EIPS/eip-8038) | アカウントを初めて触る cold の参照（2,600 → 3,000）や、状態への書き込みのガスを値上げ（cold の SLOAD の 2,100 は据え置き） |
| [EIP-8246](https://eips.ethereum.org/EIPS/eip-8246) | SELFDESTRUCT で ETH が消える残りの場合をなくす |
| [EIP-7954](https://eips.ethereum.org/EIPS/eip-7954) | コントラクトのコードの上限を 24,576 バイトから 65,536 バイトに拡大 |
| [EIP-7928](https://eips.ethereum.org/EIPS/eip-7928) | ブロックの中の取引が読み書きした状態の一覧（Block-Level Access Lists）をブロックに付ける |

内容と時期は Meta EIP の更新で変わります。その後の変更は、Meta EIP と [execution-specs の更新履歴](https://github.com/ethereum/execution-specs/blob/873ecb3e982ad4311a91cea5aaf2bbb83d306db1/docs/specs/protocol_history.md)で確かめてください。

<br>

ガスの値は、ノードの負荷に合わせて今後も見直される対象です。コントラクトの中で特定のガスの値を前提にした分岐や上限を書くと、その前提はハードフォーク 1 回で崩れます。デプロイ先が対応するフォークを確かめて evmVersion を指定し、ガスの値を固定値として扱わないことが、規則が変わり続けるチェーンでコードを長く動かす前提になります。
