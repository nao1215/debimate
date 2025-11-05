---
title: "Golangで無名パイプからデータを受け取る方法【term.IsTerminalによる判定】"
type: post
date: 2021-11-23
categories:
  - "linux"
tags:
  - "golang"
  - "linux"
cover:
  image: images/pipe-g2b0ac93f2_640-min-1.jpg
  alt: "Golangで無名パイプからデータを受け取る方法【term.IsTerminalによる判定】"
  hidden: false
---

## 前書き：os.Args\[1\]にはパイプのデータがない

無名パイプは、Terminal上で用いる"|"の事です。例えば、以下の例ではechoコマンドがパイプで"PIPE test"を渡し、受け取り側のcatコマンドがパイプから受け取ったデータを標準出力しています。

```
$ echo "PIPE test" | cat
PIPE test
```

上記のcatコマンドのようにパイプからデータを受け取るには、「os.Args\[1\]（コマンドライン引数の１つ目）を参照すれば良い」と私は勘違いしていました（正しくは標準入力からデータを受け取ります）。

本記事では、無名パイプ（"|"）からデータを受け取る実装例を紹介します。

## 無名パイプからデータを受け取る実装

以下に実装例と実行結果を示します。実装の詳細は、実行結果の後に後述します。

```
package main

import (
	"fmt"
	"io/ioutil"
	"os"

	"golang.org/x/term"
)

func main() {
	if hasPipeData() {
		data, _ := fromPIPE()
		fmt.Print(data)
	}
}

func fromPIPE() (string, error) {
	if hasPipeData() {
		b, err := ioutil.ReadAll(os.Stdin)
		if err != nil {
			return "", err
		}
		return string(b), nil
	}
	return "", nil
}

func hasPipeData() bool {
	return !term.IsTerminal(syscall.Stdin)
}

```

実行例は以下の通りです。

```
$ go build -o pipe main.go

$ echo "PIPE test" | ./pipe
PIPE test

$ ./pipe not_pipe
（注釈） 何も表示されない

```

## 実装説明：hasPipeData() 部分

golang.org/x/termのterminal.IsTerminal()は、引数で渡されたファイルディスクリプタ（今回は標準入力、fd=0）がターミナルからの入力かどうかを返します。以前は、golang.org/x/crypto/ssh/terminalのterminal.IsTerminal()で確認していたようですが、deprecated（非推奨）となっています。

```
func hasPipeData() bool {
	return !term.IsTerminal(syscall.Stdin)
}

```

標準入力がターミナルかどうかを確認する理由は、下図の通りです。

パイプを用いて実行したかどうかによって、プロセスの標準入力（STDIN）がターミナルもしくはパイプ（他プロセスの標準出力）のどちらに結びつくのかが異なります。標準入力がターミナルと結びついていなければ、パイプからデータがあるとみなせます。

![](images/pipe.jpg)

## 実装説明：fromPIPE() 部分

パイプからのデータは、標準入力を読み込む事によって取得できます。

```
func fromPIPE() (string, error) {
	if hasPipeData() {
		b, err := ioutil.ReadAll(os.Stdin)
		if err != nil {
			return "", err
		}
		return string(b), nil
	}
	return "", nil
}

```

os.Args（プロセス実行時の引数）からパイプのデータが取得できなかった理由は、

1. シェル（例：Bash）は、プロセスの標準入力を別プロセスの標準出力と紐付け
2. シェルは、os.Args（コマンドライン引数）にパイプからのデータを追加しない

という挙動だからでしょう。

昔読んだ「[Xinuオペレーティングシステムデザイン 改訂2版](https://amzn.to/3CPAHY4)」のシェルを思い返すと、シェルがターミナルから渡された文字列をスタックにセットする事によって、プロセスに対してコマンドライン引数を渡していました。この挙動は、上記の1.〜2とほぼ一致します（補足：Xinuにパイプの仕組みはありません）。

## 後書き

Golangで[BusyBox](https://ja.wikipedia.org/wiki/BusyBox)の[パクリ](https://github.com/nao1215/mimixbox)を実装しています。その中で、「パイプからデータを受け取る処理」が登場したわけですが、実装してみて初めてパイプを正しく理解できた気がします。
