---
title: "環境構築：Debianソースコードパッケージをビルドする方法(debソースパッケージ構築ツールのインストール)"
type: post
date: 2019-06-01
categories:
  - "linux"
tags:
  - "debian"
  - "linux"
  - "環境構築"
cover:
  image: "images/tools-498202_640-1.jpg"
  alt: "環境構築：Debianソースコードパッケージをビルドする方法(debソースパッケージ構築ツールのインストール)"
  hidden: false
---

### 前書き

過去の記事で、debソースパッケージの取得方法を示しました。

- [Linuxコマンドのソースコードを取得する方法(Debian環境)：オリジナルコマンド作成前の勉強向け](https://debimate.jp/post/2019-06-01-linux%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89%E3%81%AE%E3%82%BD%E3%83%BC%E3%82%B9%E3%82%B3%E3%83%BC%E3%83%89%E3%82%92%E5%8F%96%E5%BE%97%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95debian%E7%92%B0%E5%A2%83/)

ソースコードを取得したら、自身で改変し、ビルドも試したくなる筈です。そのため、本記事では、debソースパッケージをビルドする方法を示します。debソースパッケージの取得に関する設定は、上記の過去記事を参照して下さい。

本記事の手順

- debパッケージ構築に最低限必要なパッケージをインストール
- debパッケージ作成の補助ツールをインストール
- debソースパッケージのビルド依存パッケージを取得
- debuildコマンドでdebソースパッケージをビルド

### 検証環境

```
$ neofetch
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 9.9 (stretch) x86_64 
 ,$$P'              `$$$.     Kernel: 4.9.0-9-amd64 
',$$P       ,ggs.     `$$b:   Uptime: 2 days, 5 hours, 42 minutes 
`d$$'     ,$P"'   .    $$$    Packages: 2696 
 $$P      d$'     ,    $$P    Shell: bash 4.4.12 
 $$:      $$.   - ,d$$'    Resolution: 2560x1080 
 $$;      Y$b._   _,d$P'      DE: Cinnamon 3.2.7 
 Y$$.    `.`"Y$$$$P"'         WM: Mutter (Muffin) 
 `$$b      "-.__              WM Theme: Cinnamon (Albatross) 
  `Y$$                        Theme: BlackMATE [GTK2/3] 
   `Y$$.                      Icons: Gnome [GTK2/3] 
     `$$b.                    Terminal: gnome-terminal 
       `Y$$b.                 CPU: Intel i3-6100U (4) @ 2.3GHz 
          `"Y$b._             GPU: Intel Integrated Graphics 
              `"""            Memory: 5070MB / 32069MB 

```

### debパッケージ構築に最低限必要なパッケージをインストール

debパッケージを構築するため、最低限必要なパッケージは[build-essentialパッケージ](https://packages.debian.org/ja/stretch/build-essential)です。build-essentialによって、各種コンパイラ、makeコマンド、debパッケージ構築ツールがインストールされます。

```
$ sudo apt install build-essential
```

### debパッケージ作成の補助ツールをインストール

Debianパッケージシステムは、Debian独自のツールによって、パッチ管理やビルド自動化が支えられています。それらのツールをインストールします。実際の所、ビルドするだけであれば、必須パッケージはdevscriptsパッケージ(ビルドに使うdebuildが入ったパッケージ)のみです。

他パッケージは明示的にインストールする必要はありませんが、インストールします。

```
$ sudo apt install dh-make devscripts lintian git-buildpackage quilt pbuilder \
dput debhelper debmake fakeroot equivs cdbs

```

| **パッケージ名** | **説明** |
| --- | --- |
| [dh-make](https://packages.debian.org/ja/stretch/dh-make) | 一時開発元のソースパッケージをdebソースパッケージ形式に変換 |
| [devscripts](https://packages.debian.org/ja/stretch/devscripts) | debパッケージ開発に役立つツール・ラッパー群 |
| [lintian](https://packages.debian.org/ja/stretch/lintian) | debパッケージのバグやポリシー違反を発見するツール |
| [git-buildpackage](https://packages.debian.org/ja/stretch/git-buildpackage) | debソースパッケージをgitリポジトリ内に格納するためのヘルパーツール |
| [quilt](https://packages.debian.org/ja/stretch/quilt) | 複数パッチの管理ツール |
| [pbuilder](https://packages.debian.org/ja/stretch/pbuilder) | chroot環境でパッケージをビルドするツール(ローカルビルド用) |
| [dput](https://packages.debian.org/ja/stretch/dput) | debパッケージのアップロードツール |
| [debhelper](https://packages.debian.org/ja/stretch/debhelper) | debパッケージの自動構築ルール(debian/rules)を実行するためのツール |
| [debmake](https://packages.debian.org/ja/stretch/debmake) | debソースパッケージを作成するためのヘルパースクリプト |
| [fakeroot](https://packages.debian.org/ja/stretch/fakeroot) | 一般ユーザが管理者権限を擬似的に取得するツール |
| [equivs](https://packages.debian.org/ja/stretch/equivs) | 依存関係情報のみが含まれたパッケージを作成するツール(依存関係回避ツール) |
| [cdbs](https://packages.debian.org/ja/stretch/cdbs) | debパッケージ用の共通ビルドシステム |

### debソースパッケージのビルド依存パッケージを取得

debソースパッケージのビルド依存パッケージは、ソースパッケージ毎に異なります。それらのパッケージ名を手入力してインストールする事は面倒なため、"apt build-dep (ソースパッケージ名)"で一括インストールします。今回の例では、coreutilsパッケージのビルド依存パッケージをインストールします。

```
$ sudo apt build-dep coreutils
```

### debuildコマンドでdebソースパッケージをビルド

今回の例では、coreutilsパッケージのソースコードを取得して、ビルドします。取得するソースコードにはパッチも含まれていますが、パッチはソースコード取得のタイミングで適用されています。

ちなみに、ビルド時にdebuildに付与しているオプションに関する説明は、helpに記載されていません。debuildのmanにも書かれておらず、dpkg-buildpackageのmanに書かれています。オプションの意味は、以下の通りです([参考](https://askubuntu.com/questions/754809/whats-the-meaning-of-uc-us-options-in-debuild-uc-us))。

- "uc"=".buildinfo"ファイルと".changes"ファイルに署名をしない(unsigned changes)
- "us"=ソースパッケージに署名をしない(unsigned source)
- "b"=Binaryビルドか、build=any,allと等価

```
$ apt source coreutils
$ ls 　　　　　　　　　 (注釈)　coreutils-8.30がソースコードを格納したディレクトリ
coreutils-8.30        coreutils_8.30-3.debian.tar.xz
coreutils_8.30-3.dsc  coreutils_8.30.orig.tar.xz

$ cd coreutils-8.30

$ debuild -uc -us -b (注釈) ビルド開始

(注釈) 生成物であるバイナリは、srcディレクトリ以下に存在し、
　　　　debパッケージは、一つ上の階層に存在

$ fakeroot debian/rules clean  (注釈) debバイナリパッケージ以外の生成物を削除

```
