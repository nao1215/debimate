---
title: "【Golang】go:embedを用いて格言表示コマンド（subaru）を開発"
type: post
date: 2022-02-05
categories:
  - "linux"
  - "体験談"
tags:
  - "golang"
  - "oss"
  - "体験談"
cover:
  image: images/constellations-ge1bcb2718_640.jpg
  alt: "【Golang】go:embedを用いて格言表示コマンド（subaru）を開発"
  hidden: false
---

## 前書き：go:embedを試したかった

Golangでは、[go:embed](https://pkg.go.dev/embed)がVersion1.16から組み込まれています。

go:embedの利点は、「バイナリインストール（設定ファイルや関連ファイル含む）がより簡単になる事」でしょうか。go:embedを用いる事によって、バイナリの中に設定ファイルやスクリプトなどを埋め込めます。そのため、バイナリをシステムに置くだけで、インストール作業が完了となります。

この手法は、他言語でも一般的です。例えば、[シェルスクリプトにバイナリを埋め込んで、インストーラを作る手法](https://debimate.jp/2021/08/29/shell-script%e3%81%ab%e3%83%90%e3%82%a4%e3%83%8a%e3%83%aa%ef%bc%88%e4%be%8b%ef%bc%9atarball%ef%bc%89%e3%82%92%e5%9f%8b%e3%82%81%e8%be%bc%e3%81%bf%e3%80%81%e5%ae%9f%e8%a1%8c%e6%99%82%e3%81%ab%e3%83%90/)があります。

馴染み深いがゆえに、「go:embedを使ったコマンドを作ってみたいな」と2021年から考えていました。2022年の2月に重い腰を上げて、go:embedの勉強用コマンド（subaru）を作ることにしました。

## subaru：格言を出力するfortuneライクコマンド

[subaruコマンド](https://github.com/nao1215/subaru)は、[fortuneコマンド](https://ja.wikipedia.org/wiki/Fortune_\(UNIX\)#:~:text=fortune%E3%81%A8%E3%81%AF%E3%80%81Unix%E7%B3%BB,%E7%84%A1%E4%BD%9C%E7%82%BA%E3%81%AB%E8%A1%A8%E7%A4%BA%E3%81%99%E3%82%8B%E3%80%82)をインスパイアしています。

> **fortune**とは、[Unix系](https://ja.wikipedia.org/wiki/Unix%E7%B3%BB "Unix系")OSのコマンドの一つ。[フォーチュン・クッキー](https://ja.wikipedia.org/wiki/%E3%83%95%E3%82%A9%E3%83%BC%E3%83%81%E3%83%A5%E3%83%B3%E3%83%BB%E3%82%AF%E3%83%83%E3%82%AD%E3%83%BC "フォーチュン・クッキー")を模したプログラムであり、歴史上の偉人の名言や有名人の発言などを一部引用したメッセージを無作為に表示する。

subaruコマンドをそのまま実行すると、ランダムで格言（および格言に関係する人、会社、ツールの名前）が表示されます。

```
$ subaru
[atari]
Business is a good game. Lots of competition and a minimum of rules.
You keep score with money.
```

サブコマンドが用意されており、特定の格言を出力できます。例えば、以下の例ではUnix哲学を出力します。

```
$ subaru unix
[unix]
1. Small is beautiful.
2. Make each program do one thing well.
3. Build a prototype as soon as possible.
4. Choose portability over efficiency.
5. Store data in flat text files.
6. Use software leverage to your advantage.
7. Use shell scripts to increase leverage and portability.
8. Avoid captive user interfaces.
9. Make every program a Filter.。
```

## 設計：格言追加時にコードを修正しない

subaruコマンドを開発する時、避けたかった設計が一つあります。それは、subaruコマンドのコード内部に格言（テキスト）をベタ書きする方法です。コードはなるべく触りたくありません。

そのため、subaruコマンドは以下の設計となっています。

- 格言は外部ファイル（拡張子".subaru"）に定義する
- 全ての\*.subaruファイルをgo:embedでバイナリに組み込む
- \*.subaruファイルからサブコマンドを実行時に定義する
- \*.subaruファイルのファイル名をサブコマンド名とする

これらの仕様をどのように実装したかを後述します。

## \*.subaruファイルの埋め込み

subaruコマンドのディレクトリ構成（大事な部分）は、以下の構成です。

```
subaruプロジェクトルートディレクトリ
├── cmd
│   ├── root.go　　　★ 動的にサブコマンドを定義する処理が存在
│   └── version.go
├── fortune　　　　  ★ 格言を保存するディレクトリ
│   ├── atari.subaru
│   ├── nietzsche.subaru
│   ├── python.subaru
│   └── unix.subaru
└── main.go　　　　★ここにgo:emdedの定義が存在
```

fortune/\*以下に存在するファイルを全てバイナリに埋め込みます。そのため、プロジェクトルートディレクトリに存在するmain.goに、go:embedの処理を書いています。

```
package main

import (
	"embed"

	"github.com/nao1215/subaru/cmd"
)

//go:embed fortune/*.subaru         (注釈：埋め込み処理)
var fortune embed.FS

func main() {
	cmd.AddCommands(fortune)
	cmd.Execute()
}
```

埋め込みでは、初期化前の変数（上記の例ではfortune）の上に"//go:embed"を記載します。変数の型には、string、\[\]byte、embed.FSが使用できます。

"//go:embed    "の後に、埋め込み対象のファイル名を書きます。ファイル名はスペース区切りで複数記載でき、上記の例のようにワイルドカード指定もできます。

注意点は、「"//"と"go:embed"の間にスペースは不要」および「埋め込めないファイルが存在する事」です。後者の具体例ですが、"go:embed"を記載したファイルより上の階層のファイル」は埋め込めません。つまり、"//go:embed ../sample.txt"のような記載はビルドエラーとなります。

## サブコマンドを実行時に定義

この方法は、[エキスパートたちのGo言語](https://amzn.to/3rpcZPM)の1.2章（[依存関係のある処理を並行して実行できるタスクランナー](https://github.com/morikuni/ran)）を真似して実装しました。

subaruコマンドは[spf13/cobra](https://github.com/spf13/cobra)を利用しています。サブコマンド定義は、cobraのAPI " (\*cobra.Command).AddCommand()"を呼び出せば終わります。

subaruコマンドの場合、上記のAddCommandに渡す引数は、サブコマンド名、サブコマンドの説明、サブコマンドのエントリーポイント関数の3つです。

- サブコマンド名は、\*.subaruのファイル名と同一
- サブコマンドの説明は、"Print phrase related to $(サブコマンド名)"
- エントリーポイント関数は、\*.subaruの内容を標準出力に表示

```
func AddCommands(fs embed.FS) {
	// fortune/*.subaruの内容がバイナリに埋め込まれているので、
	// fortuneディレクトリ以下のエントリを取得
	entries, err := fs.ReadDir("fortune")
	if err != nil {
		exitError(err)
	}

	// エントリ（ファイル）単位でサブコマンドを追加
	for _, entry := range entries {
		// エントリ名（= ファイル名）から拡張子を除外
		cmdName := removerExt(entry.Name())

		// 格言を定義したファイルの内容を読み込み
		b, err := fs.ReadFile(filepath.Join("fortune", entry.Name()))
		if err != nil {
			exitError(err)
		}

		// サブコマンドの追加
		rootCmd.AddCommand(&cobra.Command{
			Use:   cmdName,
			Short: "Print phrase related to " + cmdName,
			Run: func(cmd *cobra.Command, args []string) {
				os.Exit(printPhrase(cmd.Name(), string(b)))
			},
		})
	}
}
}
```

上記の処理があるおかげで\*.subaruファイルが増えても、自動でサブコマンドが定義されます（再ビルドは必須）。そのため、ファイル追加だけでドンドン格言が増やせます。[コントリビュートしたい方、募集中！](https://github.com/nao1215/subaru)

## 最後に：subaruの由来

subaru（昴）は、子供に付けようと思った名前です。

昴は意味も良いし、車のSUBARUは技術大好きな人が多いし、名字との合わせも良くて「完璧だ」と思っていました。が、諸事情でNGとなりました。

一度気に入った名前なので「コマンドの名前にでもするか」と考え、今回subaruを実装しました。subaruは、集団（何かが集まるイメージ）の意味があるので「格言"集"」となっています。

##  おまけ：2022年に作成したGolang製コマンド一覧

https://debimate.jp/2022/02/05/%e3%80%90golang%e3%80%912022%e5%b9%b4%e3%81%ab%e9%96%8b%e7%99%ba%e3%81%97%e3%81%9f%e8%87%aa%e4%bd%9ccli%e3%82%b3%e3%83%9e%e3%83%b3%e3%83%89%ef%bc%8f%e3%83%a9%e3%82%a4%e3%83%96%e3%83%a9%e3%83%aa/
