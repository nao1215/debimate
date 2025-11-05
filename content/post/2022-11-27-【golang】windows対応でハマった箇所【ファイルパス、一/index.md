---
title: "【Golang】Windows対応でハマった箇所【ファイルパス、一時ファイル削除エラー】"
type: post
date: 2022-11-27
categories:
  - "linux"
tags:
  - "golang"
  - "windows"
cover:
  image: images/operating-system-g6fd6f1801_640.png
  alt: "【Golang】Windows対応でハマった箇所【ファイルパス、一時ファイル削除エラー】"
  hidden: false
images: ["post/2022-11-27-【golang】windows対応でハマった箇所【ファイルパス、一/images/operating-system-g6fd6f1801_640.png"]
---

##  前書き：Windows君さぁ......

私は、GolangでCLIツールをよく作ります。CLIツールの品質を担保するために、GitHub Actionsでユニットテスト（Linux、Mac、Windows向け）を継続的に実施しています。

開発作業中、ローカルでパスしたテストがGitHub Actionsでパスしない現象が稀に良く発生します。殆どのケースは、Windowsを意識していない実装のせいでテストに失敗しています。

個人的な備忘録として、Windows環境向けに注意すべき点を本記事に記載します。問題に遭遇次第、適宜加筆します（現段階は数が多くありません）

## GitHub Actions の一例

Windows環境でのユニットテストを実施するGitHub Actionsの例です。

以下の内容を`$PROJECT_ROOT/.github/workflows/windows_test.yml`として配置すると、PushとPull Request時にWindows環境のユニットテストを実行します。

```
name: WindowsUnitTest

on:
  workflow_dispatch:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  unit_test:
    name: Unit test (windows)

    strategy:
      matrix:
        platform: [windows-latest]

    runs-on: ${{ matrix.platform }}

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-go@v3
        with:
          go-version: "1"
          check-latest: true

      - name: Run unit test
        run: |
          go mod download
          go test -race -v ./...
```

## 注意点：ファイルパスの区切り文字

ファイルパスの区切り文字の差異は、クロスプラットフォーム対応で有名な注意点の一つです。LinuxやMacでは区切り文字が"/"ですが、Windowsでは"\\"です。

非常に有名な注意点ですが、正しく実装できていないケースが多いです。外部パッケージを利用したら、この区切り文字問題に遭遇することもあります。

駄目な例は、以下のように区切り文字をハードコーディングしたケースです。LinuxやMacでは動作しますが、Windowsでは区切り文字が異なるため期待通りに動作しません。

```
 fmt.Sprintf("%s/%s", "dir", "example.txt")
```

正しい実装方法は、標準ライブラリの[path/filepathパッケージのJoin()](https://pkg.go.dev/path/filepath#Join)を使用することです。Join()は、実行環境のOSに適した区切り文字を利用したパス（文字列）を返します。

```
filepath.Join("dir", "example.txt")

// 結果
// LinuxやMac：dir/example.txt
// Windows：dir\example.txt

```

## 注意点：一時ディレクトリが削除できない問題の対応

ユニットテスト作成時、[testingパッケージのTempDir()](https://pkg.go.dev/testing#T.TempDir)で一時ディレクトリを作成することがあります。TempDir()はテスト完了時に一時ディレクトリを削除してくれる便利な機能を持ちますが、2022年11月現在ではWindows環境のみディレクトリ削除に失敗することがあります。

削除失敗時のエラーメッセージを以下に示します。

```
TempDir RemoveAll cleanup: remove xxx: The process cannot access the file because it is being used by another process.

```

この現象は、[golang/go Issue#51442](https://github.com/golang/go/issues/51442)で報告されており、将来的には修正されると思います（なお、golang 1.17へのバックポートは難しい、と書かれています）

ユニットテストを作る側（TempDir()を呼び出す側）のワークアラウンドな対応としては、ディレクトリ削除を繰り返す方法があります。

```
func removeDir(dir string) {
	for i := 0; i < 10; i++ {
		if err := os.RemoveAll(dir); err == nil {
			return
		}
		time.Sleep(100 * time.Millisecond)
	}
}

// テストコードでの使用イメージ
// 	dir := t.TempDir()
//	defer removeDir(dir)

```

## 最後に

古の文字コード問題、エスケープシーケンス問題も解決策が決まり次第加筆します。
