---
title: "【Golang】go installで取得した$GOPATH/bin以下のバイナリを一括更新するgupコマンドを試作"
type: post
date: 2022-02-20
categories:
  - "linux"
  - "体験談"
tags:
  - "golang"
  - "linux"
  - "oss"
cover:
  image: "images/Screenshot-from-2022-02-20-13-02-09.png"
  alt: "【Golang】go installで取得した$GOPATH/bin以下のバイナリを一括更新するgupコマンドを試作"
  hidden: false
---

### 前書き：バイナリの更新が面倒

Golangでは、MacやLinuxのパッケージマネージャ（brew, apt, dnf, snap, etc）を利用せずに、"$ go install"でバイナリをインストールできます。"$ go install"は、開発者がパッケージのスペックファイルを作成せずにバイナリを配布できるメリットがあります。

しかし、"$ go install"には、インストールしたバイナリを一括アップデートするための仕組みが用意されていません（例：apt update --> apt upgradeのような仕組み）。バイナリを一つずつアップデートするしか方法がありません。

そこで試作したのが[gupコマンド](https://github.com/nao1215/gup)です。gupコマンドを叩くと、$GOPATH/bin以下にあるバイナリの一括更新を開始します（便利に聞こえますが、イマイチな部分があります）。本記事では、gupコマンドの仕様に関して説明します。

![](images/Screenshot-from-2022-02-20-13-02-09.png)

2022/2/21追記：本記事の最下部に別仕様を記載しています。この別仕様によって、gupコマンドのイマイチな仕様が改善されました。ヒントは[@shogo82148](https://twitter.com/shogo82148)氏からいただきました。感謝！

2022/3/14追記：最新の仕様は、[Zenn](https://zenn.dev/nao1215/articles/aef3fe318848d6)で公開しています。

---


### 課題：パッケージパスをどのように取得するか

"$ go install"でパッケージをインストールするには、以下のようにコマンドパッケージのパス情報を入力する必要があります。

```
$ go install github.com/nao1215/gup@latest
```

gupの試作中に困った部分は、go installの引数（パッケージパス情報）を自動取得する方法でした。前書きで示したスクショで"WARN"と出ている部分は、パス情報の取得に失敗しています（つまり、バイナリを更新できていない）。

コマンドパッケージパス情報は、コマンドごとに異なります。以下、一例です（${...}部分は変数）

- github.com/${user\_name}/${cmd\_name}
    
- github.com/${user\_name}/${cmd\_name}/cmd/${cmd\_name}
    
- github.com/${user\_name}/${cmd\_name}/${cmd\_name}
    

パッケージが存在するリポジトリが"github.com"ではない場合もあり、このパス情報をどのように取得するかが設計のキモでした。

例えば、[他の方](https://github.com/pborzenkov/goupdate)は同じ仕様のコマンドを実現するために、バイナリの中身を解析していました。しかし、バイナリを解析しても正しいパス情報を習得できない場合があります。

---


### 解決案：パス情報を自動取得／手動設定

gupコマンドでは、若干妥協する形でコマンドパッケージパスを取得する設計としました。具体的には、自動取得と手動取得（手動設定）を併用する形としました。

- 自動取得：シェルのコマンド実行履歴ファイルをパース
    
- 手動設定："$ go install"の代わりに、"$ gup install"でコマンドをインストール
    
- 手動設定：$HOME/.config/gup/gup.confを編集
    

シェルのコマンド履歴は、通常であればユーザーホームディレクトリ以下のヒストリーファイルに記録されています（例：~/.bash\_history）。このファイルには、過去に実行したコマンド情報がテキストで記録されているので、"$ go install"の実行履歴（= パス情報）が抽出できます。

抽出した情報は、次回以降のgupコマンド実行時も使用します。そこで、gup.confに"コマンド名 = パス情報"という形式で書き出します。以下に例を示します。

```
$ cat ~/.config/gup/gup.conf 
cheat = github.com/cheat/cheat/cmd/cheat
fyne_demo = fyne.io/fyne/v2/cmd/fyne_demo
gal = github.com/nao1215/gal/cmd/gal
ginkgo = github.com/onsi/ginkgo/ginkgo
git-chglog = 
go-licenses = 
go-outline = 
```

上記のgup.confを見れば分かる通り、パス情報が取得できていないケースがあります。この理由は、シェルのコマンド履歴が万能ではないからです。一般的なシェルでは、履歴の数に上限値があり、古い履歴から失われていきます。

つまり、数年前に"$ go install"したコマンドのインストール履歴を取得できないのです。この課題を解決するために、ユーザーに"$ gup install"（"$ go install"のラッパー）経由でコマンドをインストールしてもらいます。"$ gup install"経由で取得したコマンドのパス情報は、gup.confに記録されます。

一つ一つ"$ gup install"するのが面倒な場合は、gup.confを直接編集することも可能です。が、「gup.confの手動編集自体が面倒」だと私は思っています（なので、仕様がイマイチだと思っています）

---


### 複数環境で" $ go install"対象コマンドを共有

ここまでの説明を要約すると、gupコマンドは$HOME/.config/gup/gup.confに従って、$GOPATH/bin以下のバイナリをアップデートする仕様です。

そのため、gup.confを別環境に配置してからgupを実行すれば、複数の環境間で$GOPATH/bin以下に同じバイナリをインストールできます。この辺りは「設定ファイル（gup.conf）の同期機能を作りたいな」とは考えています。

（その前にバグ出しが先かな、とも思いつつ）

---


### 別仕様：go version -mでパス情報が取得可能

会社で「$ go version -m"の情報だと不十分ですか？」とコメントをいただきました。実は、このコメントの前にも一言ヒントを頂いていました。

<blockquote class="twitter-tweet" data-conversation="none"><p dir="ltr" lang="ja">‘go version 実行ファイル名’ でモジュール名分かるので、割と簡単にできそうな気もしますね🤔</p>— f96fd3a0-bdb9-4f10-b69f-8f765c1d341c IchinoseShogo (@shogo82148) <a href="https://twitter.com/shogo82148/status/1494306347046748166?ref_src=twsrc%5Etfw">February 17, 2022</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

Twitter上でのヒントを試した時、「バイナリ名しか取得できないから、この方法だと厳しいな」と早とちりしていました。ヘルプを読むと、-m オプションを付与するとバイナリの詳細情報が出力される事が記載されています。

以下、go version -mの結果です。

```
$ go version -m gup
gup: go1.17
	path	github.com/nao1215/gup
	mod	github.com/nao1215/gup	v0.1.1	h1:63/l6/W7wERE65AZv3H+jJUusShf8rUXNOq1vMqfX0M=
	dep	github.com/fatih/color	v1.13.0	h1:8LOYc1KYPPmyKMuN8QV2DNRWNbLo6LZ0iLs8+mlH53w=
	dep	github.com/mattn/go-colorable	v0.1.12	h1:jF+Du6AlPIjs2BiUiQlKOX0rt3SujHxPnksPKZbaA40=
	dep	github.com/mattn/go-isatty	v0.0.14	h1:yVuAays6BHfxijgZPzw+3Zlu5yQgKGP2/hcQbHb7S9Y=
	dep	github.com/spf13/cobra	v1.3.0	h1:R7cSvGu+Vv+qX0gW5R/85dx2kmmJT5z5NM8ifdYjdn0=
	dep	github.com/spf13/pflag	v1.0.5	h1:iy+VFUOCP1a+8yFto/drg2CJ5u0yRoB7fZw3DKv/JXA=
	dep	golang.org/x/sys	v0.0.0-20211205182925-97ca703d548d	h1:FjkYO/PPp4Wi0EAUOVLxePm7qVW4r4ctbWpURyuOD0E=

```

上記の"path github.com/nao1215/gup"の部分が、コマンドパス情報です。ここからパスを取得するようにコードを書き換えたら、$GOPATH/bin以下のバイナリを全て更新できました。手動設定も不要です！嬉しい！

![](images/Screenshot-from-2022-02-21-19-31-58.png)
