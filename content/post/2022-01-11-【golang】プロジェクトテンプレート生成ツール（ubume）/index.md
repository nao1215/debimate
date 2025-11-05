---
title: "【Golang】プロジェクトテンプレート生成ツール（ubume）を試作【改善案を募集】"
type: post
date: 2022-01-11
categories:
  - "linux"
  - "体験談"
tags:
  - "golang"
  - "linux"
  - "oss"
cover:
  image: images/cooking-g7a7f01727_640-min.jpg
  alt: "【Golang】プロジェクトテンプレート生成ツール（ubume）を試作【改善案を募集】"
  hidden: false
images: ["post/2022-01-11-【golang】プロジェクトテンプレート生成ツール（ubume）/images/cooking-g7a7f01727_640-min.jpg"]
---

## 前書き：プロジェクトを新規で作るのはダルい

Golangの勉強中に、「サンプルコードを試すためのプロジェクト」や「検証用プロジェクト」を手動で作るのは、面倒だなと感じてきました。また、どこかのプロジェクトをコピーして流用すると、名称の変更忘れ（誤記、typo）が発生しがちです。

Javaのgradleのような「Golangプロジェクトテンプレートのジェネレータ」を探しましたが、パッと見つかりませんでした。そこで、Golangプロジェクトテンプレートを生成する[ubumeコマンド](https://github.com/nao1215/mkgoprj)を作ってみました。

機能が少ないので、改善案があれば[Issue（日本語もOK）](https://github.com/nao1215/mkgoprj/issues)や[問い合わせフォーム](https://debimate.jp/%e3%81%8a%e5%95%8f%e3%81%84%e5%90%88%e3%82%8f%e3%81%9b/)からご連絡いただけると嬉しいです。

**2022年4月19日追記**：ubumeからmkgoprjにリネームしました。そして本記事に書かれている内容とは別仕様に変更（破壊的な変更）をしたので、[日本語版README](https://github.com/nao1215/mkgoprj/blob/main/doc/README.ja.md)を参照してください。

## インストール方法

go installでインストールしてください。

```
$ go install github.com/nao1215/mkgoprj/v2@latest
```

Golang開発環境が未構築の場合は、ubumeコマンドのインストール前に[Golang公式サイト](https://go.dev/doc/install)を参考にしてGolang開発環境を構築してください。

## 使い方

前提ですが、Version 0.5.1の段階ではアプリケーションプロジェクトしか生成できません。ライブラリプロジェクトも対応する予定ですが、現在はプロジェクトレイアウトを検討中です。

ubumeコマンドは、"$ go mod init"と同様にインポートパスを引数として取ります。例えば、バージョン管理システム（VCS）にGitHubを使用し、ユーザー名がnao1215であり、新規作製プロジェクト名がsampleの場合は、以下のようにコマンドを実行します。

```
$ ubume github.com/nao1215/sample
```

上記のコマンド実行後に生成されるsampleディレクトリ内は、以下のツリー構成となります。

```
$ tree sample/
sample/
├── Changelog.md
├── Makefile
├── cmd
│     └── sample
│             ├── main.go
│             └── main_test.go
└── go.mod
```

sample/cmd以下には、mainパッケージとそのテストファイルが格納されています。コードをビルド、テスト、フォーマットするためのMakefileも生成します。" $ go mod init github.com/nao1215/sample" も実行済みの状態です。

## Makefileの仕様

[Makefileは自己文書化](https://debimate.jp/2020/10/29/%E3%80%90tips%E3%80%91%E4%BD%95%E5%BA%A6%E3%82%82%E7%B9%B0%E3%82%8A%E8%BF%94%E3%81%99%E9%96%8B%E7%99%BA%E7%92%B0%E5%A2%83%E6%A7%8B%E7%AF%89%E3%82%92makefile%E3%81%A8%E3%82%B7%E3%82%A7%E3%83%AB/)されています。makeコマンドを引数なしで叩いた場合はビルドが始まらず、Makefileがどのようなターゲットを持ち、そのターゲットが何をするのかの説明文（helpメッセージ）が表示されます。 

```
$ make
build           Build binary 
clean           Clean project
deps            Dependency resolution for build
fmt             Format go source code 
test            Start test
vet             Start go vet

```

デフォルトで登録されているターゲットは、以下の処理を行います。

- make build：バイナリを生成する
- make clean：プロジェクト内の中間ファイルやゴミを削除する
- make deps：ビルド時に必要な外部ファイルを取得する
- make fmt：コードに対してフォーマッタを適用する
- make test：単体テストを実行し、カバレッジファイル（cover.html）を生成する
- make vet：静的解析を行う

新しいターゲットをMakefileに追加する場合、target:の横に##でコメントを追加してください。その##コメントが抽出されて、helpメッセージとして表示されます。以下、記載例（Makefileの抜粋）です。

```
build: deps ## Build binary 
	env GO111MODULE=on GOOS=$(GOOS) $(GO_BUILD) $(GO_LDFLAGS) -o $(APP) cmd/sample/main.go

clean: ## Clean project
	-rm -rf ./vendor $(APP) cover.out cover.html

```

## ビルド方法

"make build"でプロジェクトルートディレクトリに、バイナリが生成されます（今回はsampleバイナリが生成されます）。

```
$ ls
Changelog.md  Makefile  cmd  go.mod

$ make build
$ ls
Changelog.md  Makefile  cmd  go.mod  sample

$ ./sample 
Hello, World

```

## 最後に（追記含む）

類似のプログラムは存在しそうですが、自分好みのプロジェクトがコマンド一発で作れるので、車輪の再発明（？）も悪くないかなと考えています。実装時間も数時間であり、そこまで労力かかっていません（あと、作った次の日に会社で使うタイミングがあった）

**以下、追記**

2022年2月現在は、オプションが増えて、作れるプロジェクト種類も増えました。本記事の内容も古くなってしまったので、興味がある方は[GitHub](https://github.com/nao1215/ubume)を覗いてみてください。READMEにスクショ付きで説明を書いています。

## おまけ：2022年に作成したGolang製コマンド一覧

https://debimate.jp/2022/02/05/%e3%80%90golang%e3%80%912022%e5%b9%b4%e3%81%ab%e9%96%8b%e7%99%ba%e3%81%97%e3%81%9f%e8%87%aa%e4%bd%9ccli%e3%82%b3%e3%83%9e%e3%83%b3%e3%83%89%ef%bc%8f%e3%83%a9%e3%82%a4%e3%83%96%e3%83%a9%e3%83%aa/
