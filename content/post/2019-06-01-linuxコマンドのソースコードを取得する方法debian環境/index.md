---
title: "Linuxコマンドのソースコードを取得する方法(Debian環境)：オリジナルコマンド作成前の勉強向け"
type: post
date: 2019-06-01
categories:
  - "linux"
tags:
  - "codereading"
  - "command"
  - "debian"
  - "linux"
cover:
  image: images/code-2434271_640-min.jpg
  alt: "Linuxコマンドのソースコードを取得する方法(Debian環境)：オリジナルコマンド作成前の勉強向け"
  hidden: false
images: ["images/code-2434271_640-min.jpg"]
---

## 前書き

少し古い雑誌ですが、[CQ出版社のInterface誌（2016年10月号）](http://www.kumikomi.net/interface/contents/201610.php)に「レベルアップ！ オリジナル・コマンドを作る」という記事がありました。しかし、この雑誌に書かれている内容は、bashに偏っており、情報が不足していると(当時)感じました。

単純に自作コマンドを作成し、自作コマンドをシステムにインストールするだけであれば、以下の2点が必要な情報ではないかと考えています(本来であれば、メッセージの国際化やmanの作成など、コマンド作成時はすべき事が多いです)。

自作コマンドを作成する上で、最低限必要な情報

- 自作コマンド(実行形式ファイル)の格納先
- 自作コマンド作成時の参考(既存コマンドのソースコード)の取得方法

本記事では、上記2点に関して記載します。なお、本記事は、2016年に書いた内容に加筆したものであり、2019年現在から3年経過しています。その3年の間に、私は他人のコードを読む事が勉強になる事を肌で感じています。そのため、コマンド(パッケージ)のソースコード取得方法は、プログラマであれば覚えておいて損はないと考えています。

## 検証環境

```
$ neofetch 
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 9.9 (stretch) x86_64 
 ,$$P'              `$$$.     Kernel: 4.9.0-9-amd64 
',$$P       ,ggs.     `$$b:   Uptime: 1 day, 23 hours, 47 minutes 
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
              `"""            Memory: 4660MB / 32069MB 
```

## 一般的なコマンドの格納先

Linuxのディレクトリ階層は、Filesystem Hierarchy Standardで(ある程度)定められています。そのため、Linuxコマンドの格納先は、一般的に下表のディレクトリとなります。自作コマンドであれば、格納が推奨されているディレクトリは、/usr/local/bin です。

| ディレクトリ | 役割 |
| --- | --- |
| /bin | シングルユーザモードで必要になるコマンド格納先(cat、rmなど） |
| /sbin | システム管理系コマンド格納先(sudo、ifconfigなど) |
| /usr/bin | 一般ユーザ向けだが、基本的(一般的)ではないコマンド格納先(make、wgetなど） |
| /usr/sbin | 基本的ではないシステムコマンド格納先(各種デーモンなど) |
| /usr/local/bin | 評価版パッケージや自作コマンドの格納先 |

特定のコマンドの格納先が知りたい場合は、下記のコマンドでパスを取得できます。

| コマンド名 | 機能 |
| --- | --- |
| [whereis](http://itpro.nikkeibp.co.jp/article/COLUMN/20140212/536211/) | コマンド格納先、manの格納先を表示 |
| [which](http://itpro.nikkeibp.co.jp/article/COLUMN/20060228/230996/?rt=nocnt) | コマンドの格納先を表示 |

## コマンドのソースコードの取得方法(CUI)

まず、コマンドを提供しているパッケージ名を調査します。今回は、mkdirコマンドを例にします。

```
$ sudo apt-get install dpkg-dev  (注釈) この手順は不要な環境が存在します。
$ which mkdir                    (注釈) mkdirの格納先(絶対パス)を取得。
  /bin/mkdir
$ dpkg --search /bin/mkdir       (注釈) mkdirを提供するパッケージの表示
  coreutils: /bin/mkdir
```

上記のdpkgコマンドにより、mkdirはcoreutilsパッケージで提供される事が分かります。なお、apt-fileコマンドを用いて、パッケージ名を取得する方法もあります。ただし、こちらの方法は、複数のパッケージ名や関係のないディレクトリも表示されます。

```
$ sudo apt-get install apt-file  # この手順は不要な環境が存在します。
$ apt-file update                # データベースの更新。
$ which mkdir                    # mkdir格納先(絶対パス)を取得。
  /bin/mkdir
$ apt-file search /bin/mkdir     # grepコマンド(パイプ)で取捨選択した方が好ましい。
  9base: /usr/lib/plan9/bin/mkdir
  coreutils: /bin/mkdir
  klibc-utils: /usr/lib/klibc/bin/mkdir
  xutils-dev: /usr/bin/mkdirhier
```

次に、aptコマンドでソースコードパッケージを取得する前に、安定版(2019年現在stretch)のソースコードリポジトリを"/etc/apt/sources.list"に設定します。sources.list中で、"deb"から始まる設定はバイナリパッケージリポジトリ、"deb-src"から始まる設定はソースコードパッケージリポジトリに関する設定です。つまり、"deb-src"と記載された設定があれば、以下の手順は不要です。

以下の例でsources.listに記載している"stretch"(=Debian9)という文字列は、"stable(安定版)"に書き換えても良いです。Version名を明確に指定する理由は、システム管理者(ユーザ)がVersion更新に気づかず、意図せずに次Versionのソースコードを取得する事を防ぐためです(バイナリパッケージではないため、"stable"と記載しても影響は殆どありません)。

```
(注釈) 使用するエディタは自由(viでなくても良い)
$ sudo vi /etc/apt/sources.list

```

```
# deb-srcから始まる3行をsources.listに追記。

# ベースリポジトリ
deb-src http://ftp.jp.debian.org/debian/ stretch main contrib non-free

# 安定版更新
deb-src http://ftp.jp.debian.org/debian/ stretch-updates main contrib non-free

# 安定版バックポート
deb-src http://ftp.jp.debian.org/debian/ stretch-backports main contrib non-free

```

最後に、aptコマンドで該当パッケージ(例：coreutils)をソースコードパッケージで取得します。ソースコードと同時に、パッチやdscファイルが付いてきますが、これらはDebian環境下のパッケージ管理に関わるファイルです。ソースコードの大枠を確認する際には、不要な内容なため、今回は無視します。

```
$ sudo apt update
$ sudo apt upgrade
$ apt source coreutils
$ ls 　　　　　　　　　 (注釈)　coreutils-8.30がソースコードを格納したディレクトリ
coreutils-8.30        coreutils_8.30-3.debian.tar.xz
coreutils_8.30-3.dsc  coreutils_8.30.orig.tar.xz

$ cd coreutils-8.30/src
$ ls | grep mkdir    (注釈) mkdir以外のソースコードが格納されているため、grepで検索。
  mkdir.c
```

\[the\_ad id="598"\]

## コマンドのソースコードの取得方法(GUI)

一例ですが、以下のサイトからパッケージ名を検索して、ソースを取得する事ができます。

- [Debian公式サイト](https://packages.debian.org/jessie/coreutils)
- [Ubuntu公式サイト](http://packages.ubuntu.com/ja/)
- [GNUオペレーティング・システム](https://www.gnu.org/)

## おまけ：DebianソースコードをWebブラウザで閲覧

ソースコードをダウンロードして確認する事が面倒であれば、「[Debian Sources](https://sources.debian.org/)」がオススメです。Webブラウザからソースコードパッケージの内容を確認する事が出来ます。

![](images/debian_sources.png)

また、"apt source"コマンドで取得したdebソースパッケージをビルドしたくなった場合、以下の記事にビルド手順をまとめてあります。

https://debimate.jp/2019/06/02/%E7%92%B0%E5%A2%83%E6%A7%8B%E7%AF%89%EF%BC%9Adebian%E3%82%BD%E3%83%BC%E3%82%B9%E3%82%B3%E3%83%BC%E3%83%89%E3%83%91%E3%83%83%E3%82%B1%E3%83%BC%E3%82%B8%E3%82%92%E3%83%93%E3%83%AB%E3%83%89%E3%81%99/
