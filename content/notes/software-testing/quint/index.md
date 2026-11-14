---
title: "Quint - 仕様に書いた失敗の順番は全部試し、書かなかった失敗は試さない"
date: 2026-11-13
draft: false
series: ["技術ノート", "Software Testing"]
tags: ["software-testing", "quint", "tla-plus", "model-checking", "model-based-testing", "go"]
weight: 5
wrapTables: true
topics: ["Formal Specification"]
---

[Quint](https://quint.sh/) は、システムが持つ状態と、状態を変える操作を書き、操作をどの順番で行っても守られるべき条件に違反しないかを機械に調べさせる仕様記述言語です。[TLA+](https://lamport.azurewebsites.net/tla/tla.html) と同じ Temporal Logic of Actions という論理の上に、プログラマーが読み書きしやすい型付きの文法と、仕様を実行して調べる CLI を載せています。

著者の [sqly](https://github.com/nao1215/sqly) は、CSV などのファイルを取り込み、対話シェルで SQL を実行する CLI です。シェルには、編集した表を元のファイルへ書き戻す `.save` があります。複数のファイルを 1 回で書き戻す時は、途中で失敗したら全てのファイルを元のままにする保証です。この保証を守る実装は、2026 年 7 月 29 日から 8 月 4 日までに 7 本の commit で直されました。どの修正も、前の設計が考えていなかった失敗の順番を塞いだものです。ところが途中の 1 本は、前の修正が塞いだ穴を開け直していました。

では、最初に Quint で手順を書いていれば、この修正の繰り返しと後退は避けられたのでしょうか。下の図は、手元で `.save` の手順を Quint で書き、操作 6 回（6 ステップ）までの全ての実行を調べた結果です。a は people.csv、b は places.csv の 2 つのファイルです。

{{< figure src="images/cover.webp" alt="上から 0ee1d88、3036574、1742eca の設計。どれも保存前、a を一時ファイルに書く、b を一時ファイルに書く、a の上書きが途中で失敗、の 4 つの状態を並べ、各状態に people.csv と places.csv の中身を示す。最後の状態で、中段の 3036574 だけ people.csv が赤い「書き込み途中」のまま残り、上段と下段は元の中身に戻っている" caption="同じ順序で、0ee1d88 と 1742eca は a を戻し、間の 3036574 だけが書き込み途中のファイルを残す" align="center" >}}

sqly は一時ファイルに書いた表を元のファイルへ移し、移せない時は元のファイルを上書きします。上段の 0ee1d88 は、上書きに失敗したファイルをバックアップから戻す修正です。中段の 3036574 は、後のファイルで失敗した時に移し終えたファイルを戻す修正で、この時に 0ee1d88 の戻しが消えました。戻すのは移し終えたファイルだけなので、上書きに失敗した a は戻りません。下段の 1742eca が、6 日後に a を戻す処理を入れ直しています。

Quint は、3036574 の設計で保証が崩れるこの順序を 6 秒ほどで返しました。ただし、それは「上書きが途中で失敗する」場合を著者が仕様に書いた時だけです。

<br>

本記事では、sqly の `.save` を題材に、Quint で何を書き、何が見つかり、何が見つからないかを確認します。後半では、Quint が出した操作の列を Go のテストで本物の `.save` に流し、Go の [rapid](https://github.com/flyingmutant/rapid) と比べます。rapid は、入力や操作の列を乱数で作り、テストが失敗した例を小さく縮める Go のライブラリです。扱う疑問は以下の通りです。

- Quint では何を書き、何を調べるのか。
- sqly の `.save` に当てると、何が見つかり、何が見つからないのか。
- 仕様と Go のコードは、どうつなぐのか。
- Go の rapid や testing/quick と、何が違うのか。
- Go のプロジェクトに入れる時、何が引っかかるのか。

---

### Quint で書くもの

Quint の仕様は、状態を表す変数（`var`）、初期の値（`init`）、変数を変える操作（`action`）、常に成り立つべき条件から成ります。最後の条件を不変条件（invariant）と呼びます。数を 1 ずつ増減させる仕様なら、次のように書きます。

```quint
module counter {
  var n: int
  action init = n' = 0
  action step = any { n' = n + 1, n' = n - 1 }
  val small = n < 3
}
```

`n'` は操作した後に `n` が取る値で、`any` は中の操作のどれか 1 つを選ぶことを表します。`small` は「n は 3 未満」という不変条件です。

Quint の CLI は、この仕様を 2 つの方法で調べます。`quint run` はシミュレーターで、`init` から操作を乱数で選んで進める実行を何千回も繰り返し、不変条件に違反する実行を探します。

`quint verify` では、[Apalache](https://apalache-mc.org/) が、指定したステップ数（既定は 10 ステップ）までの全ての実行を調べます。ステップは操作 1 回のことです。

Apalache は、実行を連立した条件式に直し、条件を満たす値を探す SMT ソルバーの [Z3](https://github.com/Z3Prover/z3) に解かせます。Apalache は Scala で書かれていて、JVM の上で動きます。ステップ数で区切って全部を調べるので、[有界モデル検査](https://quint.sh/docs/model-checkers)（bounded model checking）と呼ばれます。

不変条件に違反した実行は、状態の列として返ります。本記事では、この状態の列をトレースと呼び、不変条件に違反したトレースを反例と呼びます。上の仕様では、`run` は乱数のシード（seed、乱数の列を決める初期値）によって 11 ステップの長いトレースを返し、`verify` は最短の 3 ステップのトレースを返しました。

```console
$ quint run counter.qnt --invariant=small --seed=1
[State 0] { n: 0 }
[State 1] { n: 1 }
[State 2] { n: 0 }
...（中略。n は -1 まで下がってから上がる）
[State 10] { n: 2 }
[State 11] { n: 3 }
[violation] Found an issue (10ms at 100 traces/second).

$ quint verify counter.qnt --invariant=small
[State 0] { n: 0 }
[State 1] { n: 1 }
[State 2] { n: 2 }
[State 3] { n: 3 }
[violation] Found an issue (2951ms).
```

<br>

#### 書くのはコードではなく抽象

Quint で書くのは、システムの振る舞いを抜き出した抽象です。例えば Quint の文字列は、[言語の文書](https://quint.sh/docs/lang)にある通り、等しいかを比べ、集合や辞書に入れることしかできません。文字列をつなぐ演算も無く、著者が仕様に `"stage " + target` と書いた時は、`+` が整数の演算なので型の誤りになりました。後で取り上げる、TSV で引用符が増えるバグのようなバイト列の誤りは、仕様に書けません。

---

### sqly の .save が保証すること

`.save --in-place` は、シェルを起動してから変えた表を取り込み元のファイルへ書き戻します。表が 2 つあれば、2 つのファイルを書きます。今の sqly にある [executeWriteBack](https://github.com/nao1215/sqly/blob/4f67868/shell/save.go#L631) は、次の順に進めます。

1. 全ての表を一時ファイルに書く。一時ファイルは元のファイルと同じディレクトリに置く。
2. 元のファイルを全てバックアップとして写す。
3. 一時ファイルを 1 つずつ元のファイルへ移す。
4. 3 で失敗したら、移し終えたファイルをバックアップから戻す。

3 で移すのは rename で、ファイルの名前を一度に付け替えるので、書き込み途中の状態は生まれません。Windows のように rename を断られた時は、コピーによる上書きで代えます。4 で戻せなかったファイルは、エラーに名前を出して報告します。複数の宛先を全部か無しかで揃えるのは、分散システムで [2PC](/notes/distributed-systems/two-phase-commit/) が扱う問題と同じ形で、sqly は 1 つのプロセスの中でバックアップを使って揃えています。

コピーによる上書きは、元のファイルを空にしてから書くので、途中で失敗すると書き込み途中のファイルが残ります。[commitStagedFile の注釈](https://github.com/nao1215/sqly/blob/4f67868/shell/save.go#L769-L772)は、この書き込み途中のファイルを「コピーの順番をどう変えても避けられない」と書き、4 のバックアップで守っています。

この形になるまでの修正は、以下の 7 本です。最初の 5 本は、7 月 29 日の 1 時間半ほどの間に入りました。

| commit | 日付 | 修正 |
|---|---|---|
| [220a85f](https://github.com/nao1215/sqly/commit/220a85f) | 7/29 | 全部を一時ファイルに書いてから、rename で移す |
| [23dcc5a](https://github.com/nao1215/sqly/commit/23dcc5a) | 7/29 | rename を断られたら、コピーで上書きする |
| [ff97dc2](https://github.com/nao1215/sqly/commit/ff97dc2) | 7/29 | rename を断られた時に、元のファイルを戻す |
| [0ee1d88](https://github.com/nao1215/sqly/commit/0ee1d88) | 7/29 | 上書きの前にバックアップし、失敗したら戻す |
| [3036574](https://github.com/nao1215/sqly/commit/3036574) | 7/29 | 後のファイルで失敗したら、移し終えた分を戻す |
| [663bd7a](https://github.com/nao1215/sqly/commit/663bd7a) | 8/3 | 戻せなかったファイルを報告する |
| [1742eca](https://github.com/nao1215/sqly/commit/1742eca) | 8/4 | 上書きに失敗したファイル自身も戻す |

3036574 は、移し終えたファイルを戻す処理を入れた時に、0ee1d88 で入れた上書き専用の戻しをやめ、戻しの無いただのコピーに置き換えました。上書きに失敗したファイル自身を戻す処理は、ここで一度消えています。

---

### 実験 1: 7 つの設計を仕様に書く

手元では、上記の修正で移り変わった 7 つの設計を 1 つの仕様（[save.qnt](https://github.com/nao1215/debimate/blob/main/content/notes/software-testing/quint/lab/save.qnt)）に書きました。対象は a と b の 2 つのファイルで、中身は「元の中身」「新しい中身」「書き込み途中」の 3 つの値で表し、仕様ではそれぞれ old・new・broken と書きます。中身の文字列は持ちません。

以下は、一時ファイルを 1 つ移す操作の抜粋です。`nondet` は値を 1 つ選ぶ所で、`run` は乱数で選び、`verify` は全ての選び方を調べます。`outcome` は移した結果、`bad` はバックアップから戻すのに失敗するファイルの集合です。`renameFailed` は、sqly では rename の直前に権限を写す所で失敗した場合に当たり、元のファイルは触られません。以下、これを移す前の失敗と呼びます。rename を断られた後の上書きで失敗する場合は、`copyFailed` の方です。

```quint
  action commitStep = {
    // renamed: 移せた / renameFailed: 移せず、先は元のまま / copyFailed: 上書きの途中で失敗し、先は書きかけ
    nondet outcome = (if (COPY_CAN_FAIL) Set("renamed", "renameFailed", "copyFailed")
                      else Set("renamed", "renameFailed")).oneOf()
    nondet bad = (if (RESTORE_CAN_FAIL) TARGETS.indices().map(j => TARGETS[j]).powerset()
                  else Set(Set())).oneOf()
    val t = TARGETS[i]
    val touched = outcome == "copyFailed"
    val d1 = if (touched) disk.set(t, "broken") else disk
    // 戻す範囲: 設計ごとに違う。先頭から k 個か、失敗したファイル自身か
    val k =
      if (DESIGN == "rollback" or DESIGN == "reported") i
      else if (DESIGN == "touched") (if (touched) i + 1 else i)
      else 0
    val restoring =
      if (DESIGN == "selfRestore") (if (touched) Set(t) else Set())
      else TARGETS.indices().filter(j => j < k).map(j => TARGETS[j])
    ...
```

`TARGETS` は a と b のリスト、`i` は今移しているファイルの番号です。`COPY_CAN_FAIL` と `RESTORE_CAN_FAIL` は、上書きの失敗と戻す時の失敗を仕様に入れるかの切り替えで、後の「書かなかった失敗は試さない」で使います。

`DESIGN` は設計の名前で、どの commit に当たるかは後に示す結果の表に書きました。設計ごとに `--main=touched` のように選べるモジュールを用意しました。220a85f にはコピーによる上書きが無いので、その設計には上書きの失敗を入れていません。

設計ごとに主に違うのは、失敗した時に戻すファイル（`restoring`）と、戻せなかったファイルを報告するかどうかです。0ee1d88（`selfRestore`）が戻すのは、失敗したファイル自身だけです。3036574（`rollback`）と 663bd7a（`reported`）が戻すのは、移し終えた先頭の `k` 個だけです。1742eca（`touched`）は、その両方を戻します。

不変条件は「失敗した保存は、全てのファイルを元のままにするか、戻せなかったファイルを報告する」と「成功した保存は、全てのファイルを新しくする」の 2 つです。`phase` は保存の進み具合（失敗なら failed、成功なら ok）、`reported` は報告したファイルの集合です。

```quint
  val failedSaveKeepsOld = phase == "failed" implies
    TARGETS.indices().forall(j => disk.get(TARGETS[j]) == "old" or reported.contains(TARGETS[j]))

  val okSaveWritesAll = phase == "ok" implies
    TARGETS.indices().forall(j => disk.get(TARGETS[j]) == "new")
```

7 つの設計を `quint verify --max-steps=6` で調べた結果は、以下の通りです。1 回は 5〜8 秒でした。

| 設計 | sqly の commit | 6 ステップまで | 最短の反例 |
|---|---|---|---|
| 各ファイルへ直接書く | 220a85f より前 | 違反あり | a の書き込みが途中で失敗（1 ステップ） |
| 一時ファイルから rename で移す | 220a85f | 違反あり | a を移した後、b を移す前に失敗（4 ステップ） |
| コピーで上書きする | 23dcc5a | 違反あり | a の上書きが途中で失敗（3 ステップ） |
| 失敗したファイル自身を戻す | ff97dc2・0ee1d88 | 違反あり | a の上書きに失敗し、戻すのにも失敗（3 ステップ） |
| 移し終えた分を戻す | 3036574 | 違反あり | a の上書きが途中で失敗（3 ステップ） |
| 戻せなければ報告する | 663bd7a | 違反あり | a の上書きが途中で失敗（3 ステップ） |
| 失敗したファイル自身も戻す | 1742eca | 違反なし | なし |

最短の反例は 1 つとは限らず、Apalache が返すのはその 1 つです。表紙の図は、3036574 の反例と同じ順序で、0ee1d88 と 1742eca が a を戻せるかも Quint に探させた結果です。「a の上書きに失敗した直後に a が元の中身である」状態は無い、という条件を `verify` に渡しました。0ee1d88 と 1742eca ではこの条件に違反する実行が見つかり、3036574 と 663bd7a では 6 ステップまでのどの実行でも見つかりませんでした。

<br>

#### 書かなかった失敗は試さない

次に、仕様に書く失敗の種類を減らして調べ直しました。一時ファイルに書く時の失敗と、移す前の失敗は、どの行にも入れています。仕様に書ける失敗は、この 2 つと、戻す時の失敗、上書きの失敗を合わせた 4 種類です。

| 仕様に書いた失敗 | 0ee1d88 | 3036574 | 663bd7a | 1742eca |
|---|---|---|---|---|
| 移す前の失敗だけ | 違反あり | 違反なし | 違反なし | 違反なし |
| 移す前と、戻す時の失敗 | 違反あり | 違反あり | 違反なし | 違反なし |
| 移す前と、上書きの失敗 | 違反あり | 違反あり | 違反あり | 違反なし |
| 移す前と、戻す時と、上書きの失敗 | 違反あり | 違反あり | 違反あり | 違反なし |

663bd7a の設計は、上書きが途中で失敗することを仕様に書かない限り、6 ステップまで全部を調べても違反しません。Quint は、仕様に書いた失敗を全ての組み合わせと順番で調べ、書かなかった失敗は調べません。

この表は、sqly を直した順番とも重なります。0ee1d88 は、移す前の失敗だけでも違反します。a を移した後に b で失敗すると、a は新しい中身のまま残るからです。それを塞いだのが 3036574 です。戻すのに失敗する場合を足すと 3036574 が違反し、それを塞いだのが 663bd7a でした。上書きが途中で失敗する場合を足すと 663bd7a が違反し、それを塞いだのが 1742eca でした。

ただし、表の「違反あり」だけを見ても、3036574 の後退は見えません。0ee1d88 は別の順序で既に違反しているからです。後退が見えるのは、表紙の図のように、同じ順序で設計ごとの最後の状態を並べた時です。

<br>

#### 後退をテストが通した理由

0ee1d88 には、上書きが終わらない時に元のファイルが戻ることを確認するテストがありました。このテストは、コピー元のファイルを消してコピーを失敗させていました。sqly のコピーは、コピー元を開けないと宛先を開く前に止まります。そのため宛先は無傷で、戻す処理が無くてもテストは通ります。3036574 は、このテストを「コピー元が無いことを報告する」テストに書き換えました。

1742eca で足した [partialwrite_test.go の注釈](https://github.com/nao1215/sqly/blob/4f67868/shell/partialwrite_test.go#L29-L31)も、同じことを書いています。宛先を壊さずにエラーを返すだけのスタブでは、バックアップを持たない実装でもテストが通ってしまい、それがこのコードにあったバグだという注釈です。1742eca のテストは、宛先を切り詰めてから失敗するスタブに変わりました。

失敗の種類を思い付くのは、Quint でもテストでも人です。想定していなかった失敗が後から見つかる例は他にもあり、PostgreSQL が fsync で失敗した時の扱いを見直した件は [WAL のノート](/notes/distributed-systems/write-ahead-log/)で扱いました。Quint が引き受けるのは、思い付いた失敗を全ての順番で組み合わせる所です。

---

### 実験 2: 仕様のトレースを本物の .save に流す

実験 1 で調べたのは仕様で、sqly のコードではありません。仕様とコードをつなぐ方法の 1 つに、モデルベースドテスト（model-based testing）があります。訳語は [JSTQB のシラバス](https://www.jstqb.jp/dl/JSTQB-Syllabus.Advanced_MBT_Version1.1.J01.pdf)に合わせました。Quint では、`quint run --out-itf` がトレースを ITF（[Informal Trace Format](https://apalache-mc.org/docs/adr/015adr-trace.html)）という JSON の形式でファイルに書き出します。`--mbt` を足すと、各ステップで選んだ操作と `nondet` の値もトレースに入ります。文書では、`--mbt` は試験的な機能とされています。

テストはそれを読み、本物のコードに同じ操作を流して、各状態が仕様と一致するかを確認します。

```console
$ quint run save.qnt --main=touched --mbt --max-steps=6 --max-samples=500 \
    --n-traces=500 --seed=7 --out-itf='traces/t{seq}.itf.json'
```

1742eca の設計から書き出した 500 本のトレースに含まれていた振る舞いは、12 通りでした。一時ファイルで失敗する順序が 2 通り、a を移す所で失敗する順序が 3 通り、a を移した後の順序が 7 通りで、この仕様が取り得る順序の全部です。

ただし偏りがあり、243 本は最初の一時ファイルで失敗する順序でした。本題の、上書きが途中で失敗する順序は 69 本で、a で失敗するのが 50 本、a を移した後に b で失敗するのが 19 本です。シミュレーターは各ステップの選択肢を同じ確率で選ぶので、長い順序ほど少なくなります。振る舞いごとの本数は [exp2_traces.txt](https://github.com/nao1215/debimate/blob/main/content/notes/software-testing/quint/lab/output/exp2_traces.txt) にあります。

<br>

#### Go でトレースを再生する

Rust には公式の [Quint Connect](https://github.com/quint-co/quint-connect) があり、トレースの読み込みと再生をまとめて引き受けます。Go 向けには、Quint を作り始めた Informal Systems の [itf-go](https://github.com/informalsystems/itf-go) がありますが、v0.0.1 のまま 2023 年 11 月 10 日から更新が無く、README の例は「TODO」のままでした。著者は ITF の読み込みから自分で書き、75 行ほどになりました。

再生には、sqly の [fileOps](https://github.com/nao1215/sqly/blob/4f67868/shell/fileops.go#L9-L23) を使いました。書き戻しの経路が使うファイル操作をまとめた構造体で、テストから 1 つの操作だけを失敗させられます。下のコードで、`plan` はトレースから作ったファイルごとの失敗の指定、`byPath` はファイルのパスから a・b を引く表です。

トレースが「a は上書きの途中で失敗」と言えば、a への rename を断り、続くコピーによる上書きで a を切り詰めてから失敗させます。コードの `.sqly-save-` は一時ファイル、`.sqly-bak` はバックアップの名前に入る文字列です。以下はその抜粋で、全体は [savemodel_test.go](https://github.com/nao1215/debimate/blob/main/content/notes/software-testing/quint/lab/savemodel_test.go) にあります。

```go
	s.files.Rename = func(oldpath, newpath string) error {
		if plan.commit[byPath[newpath]] == "copyFailed" {
			return errors.New("rename refused, as on Windows")
		}
		return ops.Rename(oldpath, newpath)
	}
	s.files.Copy = func(src, dest string) error {
		target, toTarget := byPath[dest]
		base := filepath.Base(src)
		switch {
		case toTarget && strings.Contains(base, ".sqly-save-") && plan.commit[target] == "copyFailed":
			// 上書きの途中で失敗する: 先を切り詰め、頭だけ書いて止まる
			return truncatingCopy(ops.Copy, 1, "id,", errInjected)(src, dest)
		case toTarget && strings.Contains(base, ".sqly-bak") && plan.restoreFail[target]:
			return errors.New("restore refused")
		}
		return ops.Copy(src, dest)
	}
```

保存の後に 2 つのファイルを読み、元の中身・新しい中身・書き込み途中のどれかに分けて、トレースが最後に示す状態と比べます。

<br>

#### 過去の設計に戻した sqly で比べる

今の sqly（4f67868）と、`shell/save.go` の 1 行をわざと過去の設計に戻した 3 つのコードに、同じ 500 本を流しました。本記事では、このコードを [Mutation Testing](/notes/software-testing/mutation-testing/) と同じくミュータントと呼びます。M1 は 3036574・663bd7a の戻す範囲、M2 は 3036574 の戻せなくても黙る形、M3 は 3036574 より前の戻さない形で、どれも今のコードを書き換えて作りました。

同じ失敗を rapid に乱数で選ばせるテストも、乱数のシード（seed）を 5 個変えて 100 回ずつ回しました。表の「N 回目」は、100 回のうち何回目で失敗したかです。テストの結果が正しいかを決める仕組みをテストオラクルと呼び、[Metamorphic Testing のノート](/notes/software-testing/metamorphic-testing/)でも扱いました。rapid のテストオラクルは 2 通り用意しました。厳密なテストオラクルは「元の中身でないファイルは、戻せなかったという報告に名前が出ている」で、報告は sqly が rollback の失敗として返すエラーです。緩いテストオラクルは「エラーの文にそのファイルの名前がある」です。

| sqly |トレースを再生して一致しない本数 | rapid（厳密なテストオラクル） | rapid（緩いテストオラクル） |
|---|---|---|---|
| 今の sqly | 500 本中 0 本 | シード 5 個とも通る | シード 5 個とも通る |
| M1: 書き込み途中のファイルを戻さない | 500 本中 69 本 | 4〜11 回目で失敗する | シード 5 個とも通る |
| M2: 戻せなくても黙る | 500 本中 53 本 | 25 回目までに失敗する | 27 回目までに失敗する |
| M3: 移し終えた分を戻さない | 500 本中 90 本 | 6 回目までに失敗する | 20 回目までに失敗する |

M1 と一致しなかった 69 本は、上書きが途中で失敗する順序の全部です。一方で、緩いテストオラクルの rapid は、シード 5 個×100 回の 500 回とも M1 を通し、バグを見逃しました。下の図は、a の上書きが途中で失敗した 1 回について、今の sqly と M1 を比べたものです。4f67868 は 1742eca の設計のままです。

{{< figure src="images/oracle.webp" alt="左は今の sqly で、people.csv も places.csv も元の中身。右は M1 で、people.csv が赤い書き込み途中、places.csv は元の中身。下に、どちらも同じエラー文 failed to move the saved data onto people.csv: injected failure を返すことを示す" caption="エラー文は全く同じで、M1 だけ people.csv が書き込み途中" align="center" >}}

M1 のエラー文は、今の sqly と全く同じで、people.csv の名前も入っています。そのため「エラーの文に名前があるか」では区別できません。

Quint のトレースは、各ファイルが最後にどの中身であるべきかを状態として持つので、テストは中身そのものを比べられます。rapid でも、テストオラクルを厳密にすれば数回で失敗します。つまり、違いはテストオラクルを誰が書くかです。rapid では人が Go で書き、Quint の再生では仕様の状態がそのままテストオラクルになります。

<br>

#### 一致しない原因はコードとは限らない

再生のテストを最初に書いた時は、今の sqly でも 500 本中 8 本が仕様と一致しませんでした。a も b も戻せない順序で、sqly は 2 つの報告を返していたのに、著者が Go で書いたテストオラクルが 2 つ目を拾えていませんでした。`executeWriteBack` を呼ぶ `writeBack` は、結合したエラーを 1 段包んで返すので、`Unwrap() []error` だけを辿る書き方では、中の報告に届かなかったわけです。

仕様と一致しない時は、コード・仕様・グルーコードの 3 つを疑う必要があります。

---

### Go の似た道具との違い

sqly で最近見つかったバグは、Quint ではなく rapid が見つけています。2026 年 11 月 13 日の [PR #1051](https://github.com/nao1215/sqly/pull/1051) は、編集と保存を乱数で並べ、保存したファイルを別のセッションで読み直して表と比べるテストを足しました。rapid の README が state machine test と呼ぶ形のテストです。

このテストが、TSV の保存で値の `"q"` が `"""q"""` になり、保存の度に引用符が 1 層増えるバグを見つけました。

このテストは「読み直した表が、保存した表と同じ」をテストオラクルに使い、各 SQL 文が何をするかのモデルを持ちません。Quint の仕様は文字列を加工できないので、このバグは書けません。Go の道具と Quint を並べると、以下のようになります。

| 道具 | 人が書くもの | 調べ方 |
|---|---|---|
| [testing/quick](https://pkg.go.dev/testing/quick) | プロパティ（Go の関数） | 乱数の入力。操作の列は作らず、反例を縮めない |
| [rapid](https://github.com/flyingmutant/rapid) | 操作とテストオラクル（Go） | 操作の列を乱数で作る。反例を縮める |
| [gopter の commands](https://github.com/leanovate/gopter/tree/master/commands) | 操作とテストオラクル（Go） | 操作の列を乱数で作る。反例を縮める |
| [porcupine](https://github.com/anishathalye/porcupine) | Go で書いた逐次の仕様と、並行の履歴 | 並行の履歴が、1 つずつ順に実行した結果として説明できるか（線形化可能か）を調べる |
| Quint | 仕様（Quint） | 操作の列を乱数で作るか、ステップ数の中で全ての実行を調べる |

反例を縮めるとは、失敗した入力から関係の無い部分を削り、失敗したままの小さな入力にすることです。testing/quick は Go の標準ライブラリで、文書には新しい機能を受け付けないとあります。

testing/quick と rapid の違いは、[Property-Based Testing のノート](/notes/software-testing/property-based-testing/)で扱いました。Go の道具は、どれも本物のコードを動かします。Quint は仕様を動かすので、コードがまだ無い段階で設計を調べられ、ステップ数の中では全ての実行を調べたと言えます。

しかし、今回の `.save` は失敗の順序が 12 通りしかなく、rapid でも数回で見つかりました。Quint の「全部を調べた」が効くのは、順序の数が乱数では回り切れない時です。例えば、複数のプロセスが同じファイルを書き合う手順や、メッセージが遅れて届く分散システムのプロトコルです。

---

### Go のプロジェクトに入れにくい理由

Quint は TypeScript で書かれた CLI で、モデル検査は JVM の上で動きます。Go のリポジトリから使うと、CLI を動かす Node、`quint run` が使う Rust 製の評価器、`quint verify` が使う JVM の 3 つの実行環境が増えます。

{{< figure src="images/runtime.webp" alt="左の Go のリポジトリに save.qnt と savemodel_test.go がある。save.qnt は中央の quint（npm で Node.js 18 以上、43 MiB・79 パッケージ、または Node 同梱の実行ファイル 128 MiB）へ渡る。quint run は Rust 製の評価器 2.1 MiB、quint verify は Apalache 188 MiB と JDK 21 以上を使う。評価器も Apalache も、初回に GitHub から ~/.quint へダウンロードする。quint run --mbt が書き出す traces/*.itf.json は savemodel_test.go が読む" caption="go test とは別に、Node・Rust 製の評価器・JVM が必要" align="center" >}}

以下の結果は、空の HOME で測ったものです。出力の全体は [exp3_runtime.txt](https://github.com/nao1215/debimate/blob/main/content/notes/software-testing/quint/lab/output/exp3_runtime.txt) にあります。

大きさは図の通りです。Node を同梱した単体の実行ファイルは、PATH から node を外しても `quint run` が動きました。ただし初回に評価器を展開する時に `tar` を呼ぶので、PATH を空にすると失敗しました。`quint verify` が使う Apalache 0.62.4 は JDK 21 以上が必要で、手元で既定にしている JDK 17 では次のエラーで起動しませんでした。

```text
Error: LinkageError occurred while loading main class at.forsyte.apalache.tla.Tool
	java.lang.UnsupportedClassVersionError: at/forsyte/apalache/tla/Tool has been compiled by a more recent version of the Java Runtime (class file version 65.0), this version of the Java Runtime only recognizes class file versions up to 61.0
```

CI では、ジョブごとに評価器と Apalache をダウンロードするか、`~/.quint` をキャッシュすることになります。Go のテストからトレースを使うなら、グルーコードも自分で持ちます。

Go のプロジェクトで形式仕様を持つ例に、[etcd-io/raft の tla ディレクトリ](https://github.com/etcd-io/raft/tree/main/tla)があります。Quint ではなく TLA+ の仕様で、Go の実装に `with_tla` のビルドタグでトレースを書かせ、仕様と照らす手順が README にあります。

検証の script は TLA+ の jar をダウンロードして JVM で動かします。2026 年 11 月 13 日の時点で、このリポジトリの GitHub Actions の workflow には、この検証を走らせるものはありませんでした。

<br>

#### トレースを commit するという逃げ道

実験 2 で書いた Go のテストが読むのは、JSON のファイルだけです。手元でトレースを書き出して commit すれば、CI の `go test` に Node も JVM も必要ありません。代わりに、仕様を変えたらトレースを書き出し直す必要があり、書き出し直しを忘れたことに気づくには、結局どこかで quint を動かすジョブが必要です。500 本のトレースは、手元で 1.7 MiB でした。

---

### Quint を足す前に決めること

Quint を試すかどうかは、次の 3 つで決まります。

まず、失敗の種類を列挙できるかです。実験 1 の通り、Quint は仕様に書かなかった失敗を調べません。sqly の `.save` なら、上書きが途中で失敗する場合を挙げられて初めて、663bd7a で保証が崩れる順序が見えます。

次に、正解を Go で書けるかです。sqly で TSV のバグを見つけた時のように「読み直せば同じ」と書けるなら、rapid で本物のコードを動かす方が安く済みます。正解が手順の設計にあり、コードがまだ無い時や、順序の数が乱数で回り切れない時は、Quint の出番です。

最後に、CI に何を入れるかです。`quint verify` には JVM が、`quint run` には Node か 128 MiB の実行ファイルが必要です。トレースだけを commit して `go test` で再生する形なら、Go の CI はそのままで済みます。

sqly の `.save` のように、失敗の順序が十数通りに収まり、正解を Go で書ける手順なら、rapid のテストで足ります。Quint で 7 本の修正と 1 回の後退を避けられたのは、一時ファイルを書く時・移す前・上書きの途中・戻す時という 4 種類の失敗を最初に挙げられた場合だけでした。

実験のスクリプトと出力は [lab](https://github.com/nao1215/debimate/tree/main/content/notes/software-testing/quint/lab) に、図の生成元は [figures.py](https://github.com/nao1215/debimate/blob/main/content/notes/software-testing/quint/figures.py) にあります。
