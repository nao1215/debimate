---
title: "qhqで管理しているリポジトリをVS Codeで開くシェル関数"
type: post
date: 2025-03-17
categories:
  - "linux"
cover:
  image: images/vscode.png
  alt: "qhqで管理しているリポジトリをVS Codeで開くシェル関数"
  hidden: false
images: ["images/vscode.png"]
---

## 前書き

複数のリポジトリを用いて開発している人は、[x-motemen/ghq](https://github.com/x-motemen/ghq)でリポジトリを管理するケースが多いでしょう。本記事では、ターミナルからghqで管理しているリポジトリをVS Codeで開く方法を紹介します。

## ツールインストール

[x-motemen/ghq](https://github.com/x-motemen/ghq) および [peco/peco](https://github.com/peco/peco) を利用します。以下はgoコマンドを利用したインストール方法です。他のインストール方法を利用する場合は、公式サイトを確認してください。

```
go install github.com/x-motemen/ghq@latest
go install github.com/peco/peco/cmd/peco@latest
```

## ~/.bashrc もしくは ~/.zshrc に関数を定義

bashを利用している場合は \`~/.bashrc\` に、zshを利用している場合は`~/.zshrc`に以下の関数を定義してください。なお、fishシェルでは利用できません。定義後は、sourceコマンドなどで \`~/.bashrc\`や`~/.zshrc`を再読込してください。

```
function vscode() {
    if [ -n "$1" ]; then
        repo=$(ghq list | grep "$1" | head -n 1)
    else
        repo=$(ghq list | peco)
    fi

    if [ -n "${repo}" ]; then
        code "$(ghq root)/${repo}"
    fi
}
```

上記のvscode関数は、`ghq list`でリポジトリ一覧を表示し、その一覧をパイプで受け取ったpecoコマンドがインタラクティブにリポジトリをフィルタリング（リポジトリの選択）できるようにします。

codeコマンドは、VS Codeを起動するコマンドであり、\`$(ghq root)/${repo}\`はユーザーが選択したリポジトリの絶対パスを表します。引数にリポジトリ名を指定した場合は、pecoコマンドを使用せずに直接リポジトリを　VS Codeで開きます。

以下、vscode関数の実行例です。選択したリポジトリをVS Codeで開きます。

![](images/vscode_result.png)

## codeコマンドへのPATHが通っていない場合

macOSでは、VS Code（GUI）を利用しているのにも関わらず、codeコマンドのPATHが通っていない場合があります。[公式手順の方法](https://code.visualstudio.com/docs/setup/mac#_configure-the-path-with-vs-code)でPATHを通します。

1. VS Codeを起動
2. コマンドパレット（Cmd+Shift+P）を開く
3. "shell command"と入力
4. 選択肢"Shell Command: Install 'code' command in PATH" を実行

## 最後に

本来であれば記事にするような内容ではないです。が、私はdotfilesをGitHubで管理していないので、vscode関数をコピペできるように記事を書きました。
