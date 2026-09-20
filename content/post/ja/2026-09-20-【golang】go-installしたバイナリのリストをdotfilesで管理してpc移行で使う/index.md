---
title: 【Golang】go installしたバイナリのリストをdotfilesとして管理してPC移行で使う
type: post
date: 2026-09-20
draft: false
categories:
- Go
tags:
- golang
- dotfiles
cover:
  image: images/gup-export-import.webp
  fit: contain
  alt: gup exportとgup importの実行例
  hidden: false
---

### go install したバイナリを PC 間で揃える

業務で使う PC、私物 PC、新しい PC などの様々な環境で、go install したバイナリを一致させたいことがあります。私であれば、[jesseduffield/lazygit](https://github.com/jesseduffield/lazygit)、[x-motemen/ghq](https://github.com/x-motemen/ghq)、[junegunn/fzf](https://github.com/junegunn/fzf) あたりは直ぐにインストールしたくなります。

しかし、一つずつツールのインストール方法を調べ直すのは、かなり面倒です。シェルスクリプトで `go install github.com/...`と、インストール処理を列挙する案もありますが、これもまた面倒です。

この面倒な作業を簡単にする方法として、本記事では [nao1215/gup](https://github.com/nao1215/gup) の export・import 機能を紹介します。export 機能では `go install` したバイナリリストを `gup.json` に書き出し、import 機能では `gup.json`に基づいてインストールを行います。

---

### gup のインストール方法

```shell
go install github.com/nao1215/gup@latest
```

他のインストール方法は、[公式ドキュメント](https://nao1215.github.io/gup/)に記載しています。Homebrew、winget、mise、nix、aqua、AUR、prebuilt packages（rpm, deb, apk, tar.gz, zip）に対応しています。

---

### gup export で go install したバイナリのリストを生成

`gup export` は $GOBIN 以下に存在するバイナリの名前、インポートパス、バージョン、チャネル（latest、master、main のいずれか）を `gup.json` に書き込みます。

デフォルトでは、`$XDG_CONFIG_HOME/gup/gup.json` として出力しています。`gup.json` を dotfiles として GitHub Repository などに保管すると、別 PC に `gup.json` を持ち運ぶのが楽になります。


```shell
$ gup export 
Export /home/nao/.config/gup/gup.json
```

保存先を指定することもできます。

```shell
gup export --file ./foo/gup.json
```

`gup.json` の例：

```json
{
  "schema_version": 1,
  "packages": [
    {
      "name": "actionlint",
      "import_path": "github.com/rhysd/actionlint/cmd/actionlint",
      "version": "v1.7.12",
      "channel": "latest"
    },
    {
      "name": "fzf",
      "import_path": "github.com/junegunn/fzf",
      "version": "v0.74.4",
      "channel": "latest"
    },
    {
      "name": "ghq",
      "import_path": "github.com/x-motemen/ghq",
      "version": "v1.10.1",
      "channel": "latest"
    },
    {
      "name": "gitleaks",
      "import_path": "github.com/zricethezav/gitleaks/v8",
      "version": "v8.30.1",
      "channel": "latest"
    },
    {
      "name": "go-arch-lint",
      "import_path": "github.com/fe3dback/go-arch-lint",
      "version": "v1.19.0",
      "channel": "latest"
    },
    {
      "name": "gocyclo",
      "import_path": "github.com/fzipp/gocyclo/cmd/gocyclo",
      "version": "v0.6.0",
      "channel": "latest"
    },
    {
      "name": "goimports",
      "import_path": "golang.org/x/tools/cmd/goimports",
      "version": "v0.50.0",
      "channel": "latest"
    },
    {
      "name": "golangci-lint",
      "import_path": "github.com/golangci/golangci-lint/v2/cmd/golangci-lint",
      "version": "v2.13.2",
      "channel": "latest"
    },
    {
      "name": "gopls",
      "import_path": "golang.org/x/tools/gopls",
      "version": "v0.23.0",
      "channel": "latest"
    },
    {
      "name": "gorelease",
      "import_path": "golang.org/x/exp/cmd/gorelease",
      "version": "v0.0.0-20260908205506-85c1c2202aba",
      "channel": "latest"
    },
    {
      "name": "goreleaser",
      "import_path": "github.com/goreleaser/goreleaser/v2",
      "version": "v2.18.2",
      "channel": "latest"
    },
    {
      "name": "goveralls",
      "import_path": "github.com/mattn/goveralls",
      "version": "v0.0.12",
      "channel": "latest"
    },
    {
      "name": "govulncheck",
      "import_path": "golang.org/x/vuln/cmd/govulncheck",
      "version": "v1.8.0",
      "channel": "latest"
    },
    {
      "name": "gup",
      "import_path": "github.com/nao1215/gup",
      "version": "v1.9.3",
      "channel": "latest"
    },
    {
      "name": "lazygit",
      "import_path": "github.com/jesseduffield/lazygit",
      "version": "v0.65.1",
      "channel": "latest"
    }
  ]
}
```

---

### gup import で gup.json に書かれたバイナリをインストール

`gup import` で `gup.json` に書かれたバイナリを全て import（インストール）できます。`--file`で明示的にファイルパスを指定するか、以下に置かれたファイルを自動的に利用します。

1. `$XDG_CONFIG_HOME/gup/gup.json`
2. `./gup.json`

import 時は、最新バージョンに追従するのではなく、`gup.json` に書かれたバージョンと同一のものを利用します。

```shell
$ gup import --file gup.json 
start import based on gup.json
[ 1/15] github.com/fzipp/gocyclo/cmd/gocyclo@v0.6.0
[ 2/15] github.com/nao1215/gup@v1.9.3
[ 3/15] github.com/mattn/goveralls@v0.0.12
[ 4/15] golang.org/x/tools/cmd/goimports@v0.50.0
[ 5/15] github.com/x-motemen/ghq@v1.10.1
[ 6/15] github.com/junegunn/fzf@v0.74.4
[ 7/15] golang.org/x/exp/cmd/gorelease@v0.0.0-20260908205506-85c1c2202aba
[ 8/15] github.com/rhysd/actionlint/cmd/actionlint@v1.7.12
[ 9/15] golang.org/x/vuln/cmd/govulncheck@v1.8.0
[10/15] github.com/zricethezav/gitleaks/v8@v8.30.1
[11/15] github.com/fe3dback/go-arch-lint@v1.19.0
[12/15] github.com/golangci/golangci-lint/v2/cmd/golangci-lint@v2.13.2
[13/15] github.com/jesseduffield/lazygit@v0.65.1
[14/15] golang.org/x/tools/gopls@v0.23.0
[15/15] github.com/goreleaser/goreleaser/v2@v2.18.2
```

---

### 最後に

`gup export`、`gup import` は初期から存在する便利機能でしたが、あまり認知されていませんでした。紹介記事を書いて、少しでも広めようかと考えた次第です。
