---
title: "Fuzzing - 機械に入力を作らせて、壊れる入力を探す"
date: 2026-11-12
draft: false
series: ["技術ノート", "Software Testing"]
tags: ["software-testing", "fuzzing", "go", "parquet"]
weight: 3
wrapTables: true
topics: ["Input Generation"]
---

Fuzzing（ファジング）は、テスト対象に渡す入力を機械に大量に作らせ、プログラムが落ちる入力や止まらない入力を探すテスト手法です。人が思い付く入力ではなく、壊れたファイルや意味の無いバイト列を 1 秒に数万回の速さで渡し続けます。

著者のデスクトップは、2026 年の 9 月ごろ、月に 1 回ほど GUI が固まっていました。Ubuntu 26.04 が不安定なのだろうと思っていましたが、調べると原因はメモリ不足で、メモリを使っていたのは著者が書いた fuzz のテストでした。fuzz のテストは、止めるか異常が見つかるまで入力を作り続けるので、手元で何時間も回すことがあります。

例えば 2026-09-10 には、[jsonize](https://github.com/nao1215/jsonize) の fuzz のテストのプロセスが、システムに割り当てた 64 GB のほぼ全てに当たる 58 GB までメモリを使い、[OOM Killer](/notes/computer-systems/oom-killer/) に止められています。OOM Killer は、メモリが尽きた時に Linux がプロセスを選んで止める仕組みです。jsonize は、コマンドの出力を JSON に変換する著者の CLI です。

原因は、jsonize が表を読む処理にありました。jsonize は、`ps` や `df` のように見出しの行と値の行が並ぶ出力を表として読みます。表の列の数には 256 の上限がありましたが、行の数には上限が無く、入力の大きさの 1 万倍を超えるメモリを保持する作りでした。

fuzz のテストは 1 MiB までの入力を受け付けるので、1 つの入力で十数 GB を保持します。Go の fuzz は複数のプロセスで並列に入力を試すので、合計はさらに増えます。

{{< figure src="images/retain.webp" alt="修正前の jsonize の表の読み取りに、256 列の見出しと x だけの行 160,000 行を渡した結果。入力 321.2 KB は左下の小さな点で、保持したメモリ 4.63 GB は大きな赤い正方形。面積が大きさに比例し、入力の約 14,419 倍" caption="321.2 KB の入力で 4.63 GB を保持した（修正前の jsonize で測り直した値）" align="center" >}}

この時、fuzz のテストは失敗していません。テストが検査していたのは「panic しないこと」だけで、メモリの量は検査していなかったからです。異常はテストの失敗としてではなく、マシンが固まる形で現れました。

<br>

本記事では、手元の実験と、著者の OSS で fuzz が見つけたバグで、Fuzzing の仕組みと使い方を説明します。扱う疑問は以下の通りです。

- 乱数で入力を作るのと何が違うのか。
- Go ではどう書き、どれくらいで見つかるのか。
- panic しない異常（メモリや時間の使い過ぎ）は、どうすれば見つかるのか。
- 回しているつもりの fuzz が、回っていないことはあるのか。

---

### 乱数の入力から、カバレッジで導く入力へ

Fuzzing の始まりは、1988 年の雷雨の夜です。[Barton Miller 氏の回想](https://pages.cs.wisc.edu/~bart/fuzz/Foreword1.html)によると、同氏は自宅から電話回線で大学の UNIX にログインしていて、雷雨の雑音が入力に混ざると、普段使っているコマンドが落ちることに気付きました。

同氏はこれを大学院の授業の課題にし、ランダムな文字列を UNIX のコマンドに渡す実験に学生が取り組みました。[1990 年の報告](https://pages.cs.wisc.edu/~bart/fuzz/)では、どの UNIX でも、テストしたコマンドの 25〜33% が落ちるか、止まらなくなりました。判定は「落ちたか、止まらなくなったか」だけです。出力の正解が不要なので、どのコマンドにも同じ方法で掛けられます。

同氏らは [2020 年に同じ方法で調べ直し](https://arxiv.org/abs/2008.06537)、Rust で書き直した coreutils である [uutils](https://github.com/uutils/coreutils) の 14 個のコマンドも試しました。そのうち `comm`、`fold`、`ptx` の 3 つが止まらなくなりました。

例えば `ptx` は、行の長さの 2 乗に比例する処理を持っていて、9300 万バイトの 1 行を 34 時間掛けても 22% しか処理できませんでした。Rust はメモリの誤った操作を防ぎますが、遅すぎる処理は防ぎません。uutils と GNU coreutils の違いは、[Differential Testing のノート](/notes/software-testing/differential-testing/)でも扱っています。

<br>

#### カバレッジを手掛かりにする

ランダムな入力は、入力の形式を確認する処理の手前で弾かれやすいです。例えば、後で取り上げる Parquet というファイル形式は先頭の 4 バイトが `PAR1` で、これを確認する処理があると、ランダムな 4 バイトが一致する確率は約 43 億分の 1 なので、その先の処理には届きません。

カバレッジは、実行中にプログラムのどの分岐を通ったかの記録です。現在の主な fuzz の道具は、カバレッジを記録し、新しい分岐を通った入力を残して、それを少しずつ変えます。[AFL](https://lcamtuf.coredump.cx/afl/) や [libFuzzer](https://llvm.org/docs/LibFuzzer.html) が広めた方法で、Go は 1.18 から [`go test` に組み込んでいます](https://go.dev/doc/security/fuzz/)。

残した入力の集まりを corpus、最初に人が渡す入力を seed と呼びます。入力を少し変えることを変異（mutation）と呼びます。

{{< figure src="images/loop.webp" alt="カバレッジで導く fuzz の繰り返し。corpus（seed と、新しい分岐に届いた入力）から 1 つ選び、変異（バイトを足す・消す・変える）を加え、対象の関数に渡して実行し、前に通っていない分岐を通ったかを見る。通ったら corpus に足し、通らなければ捨てる。実行中に検査に失敗（panic、t.Fatal、10 秒を超える）したら、入力を testdata/fuzz/ に保存して止まる" caption="新しい分岐を通った入力を残し、それを元に次の入力を作る" align="center" >}}

新しい分岐に届いた入力が残るので、次の変異はそこから始まり、少しずつ奥の分岐へ進みます。

---

### 実験 1: 1 バイトずつの比較が、段を作る

先頭が `FUZZ` の入力だけで panic する 2 つの関数で、カバレッジが入力をどう導くかを試しました。2 つの違いは、同じ条件を 1 バイトずつ比べるか、4 バイトをまとめて 1 回で比べるかだけです。

```go
// ByteByByte は先頭の 4 バイトを 1 バイトずつ比べる。
func ByteByByte(b []byte) {
	if len(b) >= 4 && b[0] == 'F' {
		if b[1] == 'U' {
			if b[2] == 'Z' {
				if b[3] == 'Z' {
					panic("FUZZ")
				}
			}
		}
	}
}

// AtOnce は先頭の 4 バイトを 1 回の比較で比べる。
func AtOnce(b []byte) {
	// 0x5a5a5546 は、"FUZZ" の 4 バイトを 1 つの整数として読んだ値。
	if len(b) >= 4 && uint32(b[0])|uint32(b[1])<<8|uint32(b[2])<<16|uint32(b[3])<<24 == 0x5a5a5546 {
		panic("FUZZ")
	}
}
```

Go の fuzz のテストは、名前が `Fuzz` で始まり `*testing.F` を受け取る関数です。`f.Add` で seed を渡し、`f.Fuzz` に渡した関数が、変異させた入力ごとに呼ばれます。

```go
func FuzzByteByByte(f *testing.F) {
	f.Add([]byte("seed"))
	f.Fuzz(func(t *testing.T, b []byte) { ByteByByte(b) })
}
```

`go test -run '^$' -fuzz '^FuzzByteByByte$'` で fuzz を始めます。`-run '^$'` は、普段のテストを走らせない指定です。比較のため、カバレッジを見ずに乱数で 4 バイトを作り、`ByteByByte` に 1 億回渡すテストも走らせました。条件と結果は以下の通りです。見つかるまでの回数は、ワーカーを 1 つにして（`-parallel 1`）数えました。

| 条件 | 実行した回数 | 結果 |
|---|---|---|
| `ByteByByte` に fuzz | 36,709〜116,814 回 | 5 回とも見つかった |
| `ByteByByte` に乱数の 4 バイト | 1 億回 | 見つからない |
| `AtOnce` に fuzz | 2 分で約 1 億回を 3 回 | 見つからない |

{{< figure src="images/steps.webp" alt="左は ByteByByte。seed、F...、FU..、FUZ.、FUZZ と 1 段ずつ上がる階段で、1 段上がるたびに新しい分岐を通るので、その入力が corpus に残る。見つかるまで 36,709〜116,814 回。右は AtOnce。seed から FUZZ まで途中の段が無く、4 バイト全てを一度に当てる必要がある。当たる確率は 4,294,967,296 分の 1 で、2 分で約 1 億回実行しても見つからない" caption="1 バイトずつ比べると、途中まで一致した入力が corpus に残る" align="center" >}}

同じ `ByteByByte` でも、fuzz は 12 万回以内で見つけ、乱数は 1 億回でも見つけられませんでした。違いは、途中まで一致した入力が残るかどうかです。`ByteByByte` では、先頭が `F` の入力は `b[1] == 'U'` の分岐に初めて届くので、corpus に残ります。次の変異はその入力から始まるので、残りの 3 バイトを 1 バイトずつ当てれば済みます。

`AtOnce` は fuzz でも見つかりませんでした。4 バイトを 1 回で比べるので、途中まで一致しても通る分岐が変わらず、手掛かりが残りません。

<br>

#### 比べる値を手掛かりにする道具もある

libFuzzer には、比較の命令に渡された値を記録し、その値を入力に入れてみる [Tracing CMP instructions](https://llvm.org/docs/LibFuzzer.html#tracing-cmp-instructions) という機能があります。この機能があれば、`AtOnce` の `0x5a5a5546` のような定数も入力に入ります。手元の Go 1.26 の `go test -fuzz` では、`AtOnce` は見つかりませんでした。

Go で、ファイル形式の先頭の識別子やチェックサムを確認する処理を fuzz する時は、正しいファイルを `f.Add` で seed に渡します。正しいファイルから始めれば、確認の処理を通った後の分岐から変異が始まります。後の実験 2 の filesql も、本物の Parquet のファイルを seed に渡しています。

<br>

#### 見つかった入力はテストとして残る

fuzz が失敗した入力は、`testdata/fuzz/<関数名>/` の下にファイルとして保存されます。中身は以下の形です。

```text
go test fuzz v1
[]byte("FUZZ")
```

`-fuzz` を付けない普段の `go test` は、`f.Add` の seed と、このディレクトリのファイルを 1 回ずつ実行するだけです。新しい入力は探しません。見つかった入力を修正と一緒にコミットすると、以後は普段の `go test` が同じ入力で確認します。

---

### panic しない異常

前の loop の図の通り、Go の fuzz が失敗とみなすのは、panic した時、`t.Fatal` などでテストが失敗した時、1 つの入力の実行が長すぎる時です。[公式の文書](https://go.dev/doc/security/fuzz/)は 1 秒と書いていますが、手元の Go 1.26.9 で試すと、8 秒眠る入力は通り、12 秒眠る入力は 10 秒で失敗になりました。試したスクリプトは [exp3_hang.sh](https://github.com/nao1215/debimate/blob/main/content/notes/software-testing/fuzzing/lab/exp3_hang.sh) です。

メモリの使い過ぎは検査しないので、冒頭の jsonize のように、OS がプロセスを止めるまで動き続けます。

jsonize の問題は、1 行の入力が小さくても、読み取りが列の数だけ値を作る所にありました。256 列の見出しの下に `x` だけの行を並べると、各行は `x` と改行の 2 バイトですが、読み取りは 1 行ごとに 256 個の値を持つ JSON のオブジェクトを作ります。

{{< figure src="images/row.webp" alt="左は入力で、1 行目は c0 c1 c2 … c255 の見出し、2 行目以降は x だけの行。1 行は x と改行の 2 バイト。右は読み取りが保持する 1 行分で、256 個の値の細い帯。c0 だけが x で、c1 から c255 は null。列の数は 256 で止めていたが、行の数は止めていなかったので、1 行 2 バイトの入力が 1 行約 29 KB のメモリになる" caption="1 行 2 バイトの入力が、256 個の値になる" align="center" >}}

修正では、読み取りが作った値の数を数え、4,194,304 個を超えたら入力を拒否するようにしました。修正後の jsonize に同じ入力を渡すと、16,386 行目で `the input yields more than 4194304 values` というエラーで止まります。入力の大きさではなく、読み取りが作るものの量に上限を置いたわけです。

---

### 実験 2: 確保の上限を検査に足す

jsonize の件は、マシンが固まって初めて分かりました。メモリの使い過ぎをテストの失敗として見つけるには、fuzz の関数の中で検査する必要があります。

[filesql](https://github.com/nao1215/filesql) は、CSV などのファイルを SQLite に読み込んで SQL で問い合わせる著者の Go のライブラリです。[Parquet](https://parquet.apache.org/) という列指向のファイル形式も読めます。

filesql の `FuzzParseBinary` は、壊れたファイルで panic しないかと、行のセルの数が見出しの数と合うかを検査する fuzz で、Parquet の読み取りの中で panic が起きる入力を 3 秒未満で見つけています（[Issue #413](https://github.com/nao1215/filesql/issues/413)）。

この関数を元に、Parquet の読み取りが 16 MiB を超えて確保したら失敗にする fuzz を書き、確保を制限する修正の前のコードに掛けました。全体は [lab の exp2_parquet.sh](https://github.com/nao1215/debimate/blob/main/content/notes/software-testing/fuzzing/lab/exp2_parquet.sh) と [ceiling_test.go.txt](https://github.com/nao1215/debimate/blob/main/content/notes/software-testing/fuzzing/lab/parquet/ceiling_test.go.txt) にあります。

```go
f.Fuzz(func(t *testing.T, data []byte) {
	if len(data) > 1<<16 {
		t.Skip()
	}
	var before, after runtime.MemStats
	runtime.ReadMemStats(&before)
	_, _ = Parse(bytes.NewReader(data), Parquet)
	runtime.ReadMemStats(&after)
	if got, limit := after.TotalAlloc-before.TotalAlloc, uint64(16<<20); got > limit {
		t.Fatalf("%d bytes allocated %d MiB", len(data), got>>20)
	}
})
```

`runtime.MemStats` の `TotalAlloc` は、プロセスがそれまでにヒープに確保したメモリの累計で、解放しても減りません。`Parse` の前後の差が、1 回の読み取りで確保した量になります。64 KiB を超える入力は飛ばすので、16 MiB は入力の 256 倍以上です。

5 分ずつ 3 回走らせると、2 回で見つかりました。57 秒で見つけた 472 バイトのファイルは、16 MiB 余りを確保しました。1 分 48 秒で見つけた 471 バイトのファイルは、44 MiB を確保しました。3 回目は 5 分で見つかりませんでした。修正後のコードには 5 分で約 1,370 万回の入力を渡し、上限を超える入力は見つかりませんでした。

<br>

filesql の修正（[Issue #526](https://github.com/nao1215/filesql/issues/526)）のきっかけになった 473 バイトのファイルも、`FuzzParseBinary` に確保の上限を足して見つけたものです。Go の fuzz は、失敗する入力を見つけると、失敗したまま小さくできるだけ小さくしてから保存します。473 バイトは、そうして縮めた後の大きさです。

修正前（8cf4dda）と修正後（bd2f9e9）で、このファイルを 1 回ずつ読んだ出力が以下です。

```text
== filesql 8cf4dda (bd2f9e9^)
473 bytes allocated 100456.2 KiB, err=failed to read table: decoding thrift payload: ... unexpected EOF
== filesql bd2f9e9 (bd2f9e9)
473 bytes allocated 40.1 KiB, err=parquet column chunk 0 of row group 0 claims 3113 bytes at offset 42 in a file of 473
```

修正前も、エラーを返すという結果は正しいです。問題は、エラーを返すまでに 98.1 MiB を確保した点にあります。

Parquet のファイルは、列ごとのデータの塊を持ちます。この塊を列のチャンクと呼び、その位置と大きさをファイルの中で宣言しています。チャンクの中はページに分かれていて、各ページの見出しも、続くデータの大きさを宣言しています。

{{< figure src="images/parquet.webp" alt="473 バイトの Parquet のファイルの帯と、列のチャンク 0 が 42 バイト目から 3113 バイトと宣言する赤い点線の帯。宣言はファイルの終わりを大きく越えている。修正前は、中のページの見出しが宣言する大きさを先に確保してから読み、ファイルの終わりで失敗して 98.1 MiB を確保した。修正後は、読む前にチャンクとページの宣言がファイルに収まるかを見て拒否し、40.1 KiB で済んだ" caption="473 バイトのファイルが、ファイルに無い 3113 バイトを宣言していた" align="center" >}}

読み取りに使っている [parquet-go](https://github.com/parquet-go/parquet-go) は、ページの見出しが宣言した大きさのメモリを確保してから、その分のバイトがあるかを確認していました。そのため、同じファイルを何度も開く常駐のプロセスでは、開くたびに 98 MiB を確保します。

修正後の filesql は、ライブラリに渡す前に、各チャンクとページの宣言がファイルの大きさに収まるかを確認します。

---

### fuzz の関数に書く検査

fuzz が見つけられるのは、fuzz の関数が検査している異常だけです。著者の OSS では、以下の検査で fuzz がバグを見つけました。

| 検査 | 失敗にする条件 | 見つけたもの |
|---|---|---|
| panic しない | panic した | filesql: Parquet の読み取りの中の panic |
| 確保の上限 | 決めた量を超えて確保した | filesql: 473 バイトのファイルで 98 MiB |
| 2 つの読み方の一致 | 全体を読んだ結果と、1 行ずつ読んだ結果が違う | jsonize: `"\x1b\n"` で 2 行が 1 行につながる |
| 別の実装との一致 | Go の `encoding/json` が読める入力を拒否した | jsonize: `"\uD800"`（検査の誤り） |

3 行目の `\x1b` は、端末の色付けの指定（エスケープ列）の始まりを表す ESC という制御文字です。全体を読む経路では、色付けを取り除く処理が、ESC の直後の改行をエスケープ列の終わりとみなして消し、2 行を 1 行につなげていました。1 行ずつ読む経路は先に行を切るので、つながりません。

この検査は、同じ入力を 2 つの経路で読んで結果を比べるもので、[Metamorphic Testing のノート](/notes/software-testing/metamorphic-testing/)で扱った関係の 1 つです。4 行目は、別の実装と結果を比べる Differential Testing です。

例えば uutils の [uufuzz](https://github.com/uutils/coreutils/tree/main/fuzz/uufuzz) も、ランダムな入力を GNU と uutils の両方に渡して比べています。fuzz は入力を作り、その入力で何を確認するかは、これらの手法から選べます。

<br>

4 行目は、fuzz が失敗した原因がプログラムではなく検査にあった例です。`"\uD800"` は、UTF-16 で 2 つ組で使う値の片方だけを書いたエスケープで、1 つの文字を表しません。Go の `encoding/json` は、これを U+FFFD（置換文字）に置き換えて読みます。jsonize は入力を黙って変えないことを方針にしていて、置き換えずに拒否するとテストで決めていました。

そこで、検査に「2 つ組の片方だけのエスケープは、拒否して良い」という例外を足し、見つかった入力を `lone-surrogate` という名前で seed に入れました。fuzz が失敗した時は、プログラムを直す前に、検査がプログラムの仕様と合っているかを確認します。

---

### 回しているつもりの fuzz

実験 1 の節で書いたように、`-fuzz` を付けない `go test` は seed を実行するだけです。そのため、新しい入力を探すには、fuzz の関数ごとに `go test -fuzz` を走らせる仕組みが別に必要です。filesql と jsonize は、GitHub Actions のスケジュールで毎晩動くジョブで、fuzz の関数ごとに 5〜10 分ずつ回しています。

ジョブは、パッケージのパスと関数名の組の一覧（matrix）から作ります。filesql では、v0.55.0 でパッケージを `internal/` の下に移した時、この一覧を直し忘れました。

{{< figure src="images/matrix.webp" alt="左は filesql の夜間の fuzz の matrix の 7 行、右はリポジトリにある Fuzz 関数の 7 個。5 組は線でつながる。左の ./parser FuzzParseFormats と ./parser FuzzParseBinary は赤で directory not found。右の internal/parser FuzzParseFormats と internal/parser FuzzParseBinary は黄色で、どのジョブも回していなかった" caption="filesql v0.56.0 の時点で、2 つの fuzz の関数を誰も回していなかった" align="center" >}}

一覧の `./parser` が存在しないので、2 つのジョブは毎晩 `directory not found` で失敗していました。一覧には `fail-fast: false` を指定していたので、1 つのジョブが失敗しても他の 5 つは最後まで走ります。また、スケジュールで動くジョブの失敗は、プルリクエストの画面には出ません。そのため、誰も失敗を見ていませんでした。

回っていなかった 2 つは、外部から受け取ったファイルを読む関数の fuzz で、filesql の中で最も fuzz が必要な所でした。v0.56.0 の時点でジョブの失敗に気付き、[Issue #1051](https://github.com/nao1215/filesql/issues/1051) で直しました。

jsonize でも、新しく書いた 2 つの fuzz の関数を一覧に足し忘れました。一覧とリポジトリの fuzz の関数を比べるジョブはありましたが、1 日 1 回の定期実行でしか動かなかったので、関数を書いたプルリクエストではなく、翌日の定期実行で報告されました。

どちらも、一覧とリポジトリの fuzz の関数を比べる確認が、プルリクエストごとに走るように直しました。リポジトリの fuzz の関数は `grep '^func Fuzz'` で列挙できます。fuzz を CI に入れたら、緑であることだけでなく、全ての関数が実際に回っていることを確認する必要があります。

---

### fuzz を足す時に決めること

fuzz の関数を書くこと自体は、数行で済みます。著者の OSS で fuzz が役に立ったか、役に立たなかったかを分けたのは、以下の 4 つでした。

| 決めること | 確かめること |
|---|---|
| 対象 | ファイル、ネットワーク、コマンドの出力など、外から受け取るバイト列を読む関数か |
| 検査 | panic に加えて、メモリと時間の上限や、別の読み方・別の実装との一致を見るか |
| seed | 形式の確認を通る正しい入力を渡したか |
| 実行 | 全ての関数が、実際に毎晩回っているか |

fuzz はバイト列を作るので、形式の確認で弾かれやすく、作った入力の意味を知りません。構造のある値（日付、木、SQL の式など）を作って性質を確認する方法は、次の Property-Based Testing のノートで扱います。

実験のスクリプトと出力は [lab](https://github.com/nao1215/debimate/tree/main/content/notes/software-testing/fuzzing/lab) に、図の生成元は [figures.py](https://github.com/nao1215/debimate/blob/main/content/notes/software-testing/fuzzing/figures.py) にあります。
