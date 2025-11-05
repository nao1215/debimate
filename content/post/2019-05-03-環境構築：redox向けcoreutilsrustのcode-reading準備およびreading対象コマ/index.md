---
title: "環境構築：Redox向けcoreutils(Rust)のCode Reading準備およびReading対象コマンド一覧"
type: post
date: 2019-05-03
categories:
  - "linux"
tags:
  - "codereading"
  - "coreutils"
  - "debian"
  - "rust"
  - "環境構築"
cover:
  image: images/Code_Reading.jpg
  alt: "環境構築：Redox向けcoreutils(Rust)のCode Reading準備およびReading対象コマンド一覧"
  hidden: false
---

## 前書き：Redox版coreutilsを読む理由

[Redoxプロジェクトが開発しているcoreutils](https://github.com/redox-os/coreutils)を読む理由は、「(Rust初心者の私が)**Rustを学習する**」ためです。Redoxプロジェクトに関わるコードは、基本的にRustで書かれています。何故、Redox(Kernel)ではなくて、coreutilsを読むのかと言えば、

- Kernelを読めるほど、私がRustに慣れていない
- RedoxプロジェクトのCoreutilsは小規模
- CoreutilsはUnix/Linuxコマンドのため、私が機能を把握済み

という理由です。

Rustは登場してから日が浅い言語のため、日本語情報が少ないです。そのため、私がCode Readingした結果を全て残したいと思います。その第一歩として、本記事では、Redox coreutilsを読むために、「必要な環境構築手順」を説明し、Reading結果へのリンクを残します。

本記事で説明する内容

- Redoxサイドプロジェクト一覧
- Reading対象のCoreutilsコマンド一覧(Reading結果一覧)
- 開発環境
- Rust(nightly)のインストール
- Redox版coreutilsのビルド

## Redoxのサイドプロジェクト一覧

前提として、[Redox](https://www.redox-os.org/jp/)は、Rust言語で書かれたUNIXライクのOSです。Redox(Kernel)を開発するプロジェクトだけでなく、ユーザランド向けアプリケーションを対象としたサイドプロジェクトが多数存在します。現段階で、Redox(再度プロジェクト含む)は下図のように、一般的なディストリビューションのような見た目をしています。

![](images/Redox-destop.jpg)

下表(一部抜粋)が、Redoxサイドプロジェクト一覧です。なお、coreutilsは2種類存在しますが、BSDライクをReading対象とします。GNUライク版(uutils)は、[BusyBox](https://ja.wikipedia.org/wiki/BusyBox)に似ていたため、Reading対象としませんでした。

1. 「BSDライク」かつ「1コマンド＝1バイナリ」(coreutils、Reading対象)
2. 「GNUライク」かつ「全コマンド＝1バイナリ」(uutils)　　

| **サイドプロジェクト名** | **説明** |
| --- | --- |
| [TFS](https://gitlab.redox-os.org/redox-os/tfs) | [ZFS](https://wiki.archlinux.jp/index.php/ZFS)にインスパイアされたFile System |
| [Ion](https://gitlab.redox-os.org/redox-os/ion) | Redox用のShell |
| [Orbital](https://gitlab.redox-os.org/redox-os/orbital) | Redox用のディスプレイサーバ(GUI機能) |
| [OrbTK](https://gitlab.redox-os.org/redox-os/orbtk) | Widgetツールキット(GUI機能) |
| [pkgutils](https://gitlab.redox-os.org/redox-os/pkgutils) | RedoxパッケージマネージメントライブラリおよびCLIフロントエンド |
| [Sodium](https://gitlab.redox-os.org/redox-os/sodium) | Viコマンド風のエディタ |
| [ralloc](https://gitlab.redox-os.org/redox-os/ralloc) | メモリアロケータ |
| [libextra](https://gitlab.redox-os.org/redox-os/libextra) | libstdの補足となる機能(例：Hash、Map、乱数) |
| [games-for-redox](https://gitlab.redox-os.org/redox-os/games) | Redox向けのゲーム |
| [Coreutils](https://gitlab.redox-os.org/redox-os/coreutils) |   Unix系OSで中心的(core)なユーティリティコマンドセット(BSD ベース)   |
| [Extrautils](https://gitlab.redox-os.org/redox-os/extrautils) | リマインダ、カレンダ➖、スペルチェックなどのユーティリティセット |
| [Binutils](https://gitlab.redox-os.org/redox-os/binutils) | バイナリファイル操作用ユーティリティ |
| [uutils/coreutils](https://github.com/uutils/coreutils) | GNU coreutilsをクロスプラットフォーム向けにRustで書き直したコマンドセット |
| [m-labs/smoltcp](https://github.com/m-labs/smoltcp) | Redoxで用いられるネットワークスタック |

## Reading対象のCoreutilsコマンド一覧(Reading結果一覧)

[Redox版Coreutils](https://github.com/redox-os/coreutils)コマンド全てをReading対象とします。コマンド名称にリンクが貼ってある場合、そのリンク先はReading結果(本サイト内の記事)です。2019年5月3日段階で、まだ未着手です。

Redox版Coreutilsは、数が少なく、低機能(小規模)である事が特徴です。

| **Coreutilsコマンド** | **Step数** | **機能説明** |
| --- | --- | --- |
| [cat](https://debimate.jp/2019/05/06/code-reading%EF%BC%9Aredoxrust%E7%89%88coreutils%E3%81%AEcat%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89-%E3%81%9D%E3%81%AE1%E5%85%A82%E5%9B%9E/?preview=true&_thumbnail_id=2055) | 269 | ファイル閲覧や文字列の連結 |
| chown | 91 | ファイル・ディレクトリの所有権やグループ変更 |
| clear | 34 | 端末(画面上の文字)をクリア |
| dd | 199 | ブロック単位でファイルコピーや変換 |
| df | 92 | File Systemのディスク容量を表示 |
| du | 87 | ファイル・ディレクトリの使用量を表示 |
| free | 79 | メモリ使用量を表示 |
| kill | 59 | プロセスを終了 |
| ln | 66 | ファイルのハードリンク・シンボリックリンクを作成 |
| mkdir | 51 | ディレクトリを作成 |
| ps | 36 | 実行中のプロセス一覧を表示 |
| reset | 34 | 端末を初期化(端末起動直後の状態に変更) |
| shutdown | 44 | システムを終了 |
| sort | 115 | 文字列の並べ替え |
| tail | 305 | ファイルの最終行から数行表示 |
| test | 336 | 条件式の真偽を判定 |
| time | 46 | コマンド実行時間の計測 |
| touch | 53 | タイムスタンプ変更やファイル作成 |
| uname | 91 | OSまたはHWの情報を表示 |
| uptime | 65 | システム稼働時間を表示 |
| which | 53 | 実行コマンドの絶対PATHを表示 |

## 開発環境

開発環境は、Debianを想定しています。

```
$ neofetch 
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 9.9 (stretch) x86_64 
 ,$$P'              `$$$.     Kernel: 4.9.0-9-amd64 
',$$P       ,ggs.     `$$b:   Uptime: 4 hours, 43 minutes 
`d$$'     ,$P"'   .    $$$    Packages: 2709 
 $$P      d$'     ,    $$P    Shell: bash 4.4.12 
 $$:      $$.   - ,d$$'    Resolution: 1920x1080 
 $$;      Y$b._   _,d$P'      DE: Cinnamon 3.2.7 
 Y$$.    `.`"Y$$$$P"'         WM: Mutter (Muffin) 
 `$$b      "-.__              WM Theme: Cinnamon (Albatross) 
  `Y$$                        Theme: BlackMATE [GTK2/3] 
   `Y$$.                      Icons: Gnome [GTK2/3] 
     `$$b.                    Terminal: gnome-terminal 
       `Y$$b.                 CPU: Intel i3-6100U (4) @ 2.3GHz 
          `"Y$b._             GPU: Intel Integrated Graphics 
              `"""            Memory: 3157MB / 32069MB 
```

## Rust(nightly)のインストール

Rustは、3種類のバージョンが同時期に提供されます。

- Nightly(2019/5/3時点で、Coreutilsのビルドに必須)
- Beta
- Stable

Nightlyリリースは、毎日作成されます。6週間周期で、最新のnightlyリリースが"Beta"に移行します。さらに6週間後、betaは”stable”に移行します。Nightlyリリースは新機能が使えますが、stableまでにその機能が残っている保証がありません。

Redox版coreutilsは、nightlyリリースでのみ提供される機能を使用しているため、stableリリースではビルドが通りません(2019/5/3時点)。そのため、今回の環境構築では、stableリリースを導入後、nightlyリリースに変更します。私のサイトは参考情報として、公式サイト手順を信用して下さい。

まず、stableリリースをインストールします。

```
$ curl https://sh.rustup.rs -sSf | sh
info: downloading installer

Welcome to Rust!

This will download and install the official compiler for the Rust programming 
language, and its package manager, Cargo.

It will add the cargo, rustc, rustup and other commands to Cargo's bin 
directory, located at:

  /home/nao/.cargo/bin

This path will then be added to your PATH environment variable by modifying the
profile file located at:

  /home/nao/.profile

You can uninstall at any time with rustup self uninstall and these changes will
be reverted.

Current installation options:

   default host triple: x86_64-unknown-linux-gnu
     default toolchain: stable
  modify PATH variable: yes

1) Proceed with installation (default)
2) Customize installation
3) Cancel installation
>1　　　　　　　　　　(注釈)：1を選択し、Enter

info: syncing channel updates for 'stable-x86_64-unknown-linux-gnu'
info: latest update on 2019-04-25, rust version 1.34.1 (fc50f328b 2019-04-24)
info: downloading component 'rustc'
 85.4 MiB /  85.4 MiB (100 %)   3.3 MiB/s ETA:   0 s

(省略)

Rust is installed now. Great!

To get started you need Cargo's bin directory ($HOME/.cargo/bin) in your PATH 
environment variable. Next time you log in this will be done automatically.

To configure your current shell run source $HOME/.cargo/env

```

次に、Rustのビルドシステムであるcargo向け環境変数を端末起動時に自動で読み込むため、.bashrcに追記をします。

```
(注釈)：ビルドシステムcargoの環境変数を.bashrcに書き込む。
　　　　echoコマンドではなく、エディタを使っても大丈夫です。
$ echo "source \$HOME/.cargo/env" >> ~/.bashrc 

$ source $HOME/.cargo/env  (注釈)：初回時のみ、手動で環境変数を設定

```

```
(注釈)：ビルドシステムcargoの環境変数を.bashrcに書き込む。
　　　　echoコマンドではなく、エディタを使っても大丈夫です。
$ echo "source \$HOME/.cargo/env" >> ~/.bashrc 

$ source $HOME/.cargo/env  (注釈)：初回時のみ、手動で環境変数を設定

```

最後に、nightlyリリースのToolchainをインストールし、デフォルトで使用するコンパイラをnightlyにします。その後、Rust開発環境を最新版にアップデートします。

```
$ rustup --version　　　　　(注釈)：現在のバージョン確認
rustup 1.18.2 (a0bf3c9cb 2019-05-02)

$ rustup install nightly
info: syncing channel updates for 'nightly-x86_64-unknown-linux-gnu'
info: latest update on 2019-05-03, rust version 1.36.0-nightly (08bfe1612 2019-05-02)
(省略)
  nightly-x86_64-unknown-linux-gnu installed - rustc 1.36.0-nightly (08bfe1612 2019-05-02)

info: checking for self-updates

$ rustup default nightly　(注釈)：デフォルトコンパイラをnightlyに変更

$ rustup update　(注釈)：Rust環境をアップデート
info: syncing channel updates for 'stable-x86_64-unknown-linux-gnu'
info: syncing channel updates for 'nightly-x86_64-unknown-linux-gnu'
info: checking for self-updates

   stable-x86_64-unknown-linux-gnu unchanged - rustc 1.34.1 (fc50f328b 2019-04-24)
  nightly-x86_64-unknown-linux-gnu unchanged - rustc 1.36.0-nightly (08bfe1612 2019-05-02)

```

## Redox版coreutilsのビルド

まず、[Redox版coreutilsのGitHub](_wp_link_placeholder)からRepositoryをクローン(複製)します。

```
$ git clone https://github.com/redox-os/coreutils.git
$ cd coreutils

$ tree　　(注釈)：coreutilsのファイル内容
.
├── Cargo.lock
├── Cargo.toml
├── LICENSE
├── README.md
├── proptest-regressions
│   └── bin
│       └── dd.txt
├── src
│   ├── bin
│   │   ├── cat.rs
│   │   ├── chown.rs
│   │   ├── clear.rs
│   │   ├── dd.rs
│   │   ├── df.rs
│   │   ├── du.rs
│   │   ├── free.rs
│   │   ├── kill.rs
│   │   ├── ln.rs
│   │   ├── mkdir.rs
│   │   ├── ps.rs
│   │   ├── reset.rs
│   │   ├── shutdown.rs
│   │   ├── sort.rs
│   │   ├── stat.rs
│   │   ├── tail.rs
│   │   ├── test.rs
│   │   ├── time.rs
│   │   ├── touch.rs
│   │   ├── uname.rs
│   │   ├── uptime.rs
│   │   └── which.rs
│   └── lib.rs
└── testing
    ├── empty_file
    ├── executable_file
    ├── file_with_text
    ├── multi_line_lang_file
    └── symlink -> empty_file

5 directories, 33 files

```

Redox版Coreutilsをビルドします。初回ビルド時に、依存している[crate](https://doc.rust-jp.rs/the-rust-programming-language-ja/1.6/book/crates-and-modules.html)をFetchするため、時間がかかります。

```
$ cargo build

$ ls target/debug/　(注釈)：ビルド後の生成物
build    dd    examples        libcoreutils.rlib  ps.d        tail    touch.d
cat      dd.d  free            ln                 reset       tail.d  uname
cat.d    deps  free.d          ln.d               reset.d     test    uname.d
chown    df    incremental     mkdir              shutdown    test.d  uptime
chown.d  df.d  kill            mkdir.d            shutdown.d  time    uptime.d
clear    du    kill.d          native             sort        time.d  which
clear.d  du.d  libcoreutils.d  ps                 sort.d      touch   which.d

```
