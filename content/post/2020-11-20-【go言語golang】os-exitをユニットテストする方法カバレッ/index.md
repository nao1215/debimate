---
title: "【Go言語(Golang)】os.Exit()をユニットテストする方法(カバレッジも取得する方法)"
type: post
date: 2020-11-20
categories:
  - "linux"
tags:
  - "golang"
  - "go言語"
  - "linux"
  - "ユニットテスト"
cover:
  image: "images/exit-44205_640.jpg"
  alt: "【Go言語(Golang)】os.Exit()をユニットテストする方法(カバレッジも取得する方法)"
  hidden: false
---

### 前書き：os.Exit()の結果は親プロセスが受信

Go言語のos.Exit()は以下に示すコードで実装されており、最終的にシステムコールのexit()を呼び出し、プロセスを終了させます。

```
func Exit(code int) {
	if code == 0 {
		// Give race detector a chance to fail the program.
		// Racy programs do not have the right to finish successfully.
		runtime_beforeExit()
	}
	syscall.Exit(code)
}
```

システムコールExit()の引数codeは、そのプロセスの終了状態として親プロセスに伝わる仕様です（他言語のexit()コードも同等の挙動をします）。つまり、テストコードからos.Exit()をコールするメソッドを呼び出しても、その結果を取得できません。

この仕様を踏まえて、GoogleのAndrew Gerrand氏は「テストコード（親プロセス）からサブプロセスを呼び出し、そのサブプロセス内でテスト対象（os.Exit()）を実行し、結果を受け取る方法」を紹介しています（[テスト方法の紹介スライド](https://talks.golang.org/2014/testing.slide#23)）。

以下に、Andrew Gerrand氏が紹介したコードを引用します。

```
func Crasher() {
    fmt.Println("Going down in flames!")
    os.Exit(1)
}
```

```
func TestCrasher(t *testing.T) {
    if os.Getenv("BE_CRASHER") == "1" {
        Crasher()
        return
    }
    cmd := exec.Command(os.Args[0], "-test.run=TestCrasher")
    cmd.Env = append(os.Environ(), "BE_CRASHER=1")
    err := cmd.Run()
    if e, ok := err.(*exec.ExitError); ok && !e.Success() {
        return
    }
    t.Fatalf("process ran with err %v, want exit status 1", err)
}
```

上記のテストコードの初回実行時は、環境変数BE\_CRASHERが定義されていないので、Crasher()は呼び出されません。

テストコードの二回目の実行時、すなわちサブプロセスとしてテストコードを呼び出す時（cmd.Run()部分）では、環境変数BE\_CRASHERが定義されているため、Crasher()が実行され、その結果を変数errで受け取れます。

この解決策は惜しい点があり、「サブプロセスでテストを実行するのでカバレッジを取得できない問題」があります。カバレッジ100%を目指しても品質は上がらないという意見もありますが、100%にできるなら100%にしたい。

そこで、本記事ではカバレッジを取得しつつ、os.Exit()をテストする方法を紹介します。

---


### 別解：os.Exit()のポインタを持つ変数を活用

まず、テスト対象コードに対する修正として、os.Exit()を直接呼ばず、os.Exit()へのポインタを持つ変数（以下の例では、グローバル変数osExit）を用いて、os.Exit()を間接的に実行します。

```
package main

import "os"

var osExit = os.Exit

func Die() {
    osExit(1)
}

```

次にテストコード側では、テストプロセス内でos.Exit()による終了状態を受け取るために、主に3つの処理を実装します。

1. int型の引数を一つ持ち、かつ引数の値を保持する関数を作成（os.Exitの代替）
2. 変数osExitに対して、手順1.で作成した関数へのポインタを代入
3. テスト終了後に、osExitの関数ポインタを復元（os.Exit()へのポインタに戻す）

テストコードの実装例を以下に示します。

```
package foo

import "testing"

func TestDier(t *testing.T) {
    // os.Exit()への関数ポインタをバックアップ
    oldExit := osExit

    // テスト終了後にosExitにバックアップしていた関数ポインタを戻す
    defer func() { osExit = oldExit }()

    // osExit()が実行された場合、終了コードが変数calledに記録される
    var status int
    exit := func(code int) {
        status = code
    }
    osExit = exit

    // テストt対象のメソッド実行および結果確認
    Die()
    if exp := 1; status != exp {
        t.Errorf("Expected exit code: %d, status: %d", exp, status)
    }
}

```

上記のテストコードを実行すると、Die()メソッドの中でos.Exit()の代わりにexit()が呼び出されるため、プロセスが終了しません。

さらに、osExitの引数（=終了状態）が変数statusに代入されるため、statusと期待値を比較すればテストが可能です。

この方法は単一プロセスでテストが完結するため、カバレッジも取得できます。

この方法を初めてみた時、「C言語でstatic関数をテストする方法に似ている」と感じました。C言語では、static関数が別ファイルに定義されたテストコードから呼び出せないので、テスト時だけstatic指定子を消す小技があります。

興味がある方は、以下の記事を参照してください。

[【C言語】static(private)関数をユニットテストする3つの方法【単体テストのバッドノウハウ】](https://debimate.jp/post/2020-04-26-c%E8%A8%80%E8%AA%9Estaticprivate%E9%96%A2%E6%95%B0%E3%82%92%E3%83%A6%E3%83%8B%E3%83%83%E3%83%88%E3%83%86%E3%82%B9%E3%83%88%E3%81%99%E3%82%8B3%E3%81%A4%E3%81%AE%E6%96%B9%E6%B3%95/)

---


### 余談：Goはユニットテストの敷居が低い

2020年11月にGo言語デビューしましたが、Go言語は公式ツールで簡単にユニットテスト環境が出来上がるので、ユニットテストの敷居が低くて好感を持てます。

公式ツールだけで、テストカバレッジをHTMLに出力できる点も感動しました。

<blockquote class="twitter-tweet"><p dir="ltr" lang="ja">Goはテスト後、カバレッジを簡単に表示できるので感動。<br><br>「os.Exit」と「コマンドライン引数」に対するテストは、少し苦労したので記事にする予定（後者は引数パース前にos.Argsを書き換えたけど、正しいのか知らん）<br><br>テストしやすいようにinterfaceが〜という記事を沢山見たが、そこも分かってない <a href="https://t.co/QafOPV6Igr">pic.twitter.com/QafOPV6Igr</a></p>— Nao03 (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1329038461328756736?ref_src=twsrc%5Etfw">November 18, 2020</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
