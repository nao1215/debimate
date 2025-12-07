---
title: "ccache(compiler cache)によるビルド高速化"
type: post
date: 2019-01-26
categories:
  - "linux"
tags:
  - "build"
  - "command"
  - "debian"
  - "linux"
  - "環境構築"
cover:
  image: "images/ccache-1.png"
  alt: "ccache(compiler cache)によるビルド高速化"
  hidden: false
---

### 前書き

大規模なプログラムをビルドする場合、数十分〜数時間かかる事があります。ビルド時間が長いと、それだけ開発者の待ち時間が増えるわけですから、短いに越したことはありません。そんなビルド時間を短縮するツールとして、[ccache](https://ccache.samba.org/)があります。

[![](images/ccache-1.png)](https://ccache.samba.org/)

ccacheはgcc向けのビルド高速化ツールで、対応言語は C/C++/Objective-C/Objective-C++です。ビルド時のキャッシュを残し、二回目のビルド以降にキャッシュを再利用できる場合は、キャッシュを用いる事によりビルド速度を改善します。

押さえておきたいポイントは、以下の4点です。

ccacheのPOINT

- gcc専用のビルド高速化ツール(キャッシュ利用)
- C/C++/Objective-C/Objective-C++向け
- 一度環境を構築すれば、簡単に利用可能
- キャッシュ作成のため、初回ビルドに時間がかかるデメリットあり

以降では、導入を記載します。環境はDebian系を想定しています。

---


### ccacheのinstallおよび環境変数設定

まず、パッケージマネージャ(apt)を用いてccacheをinstallします。その後、ログイン時にccacheの設定が自動で反映されるように、~/.bashrcファイルを編集します。

```
$ sudo apt-get install ccache

$ echo "export USE_CCACHE=1" >> ~/.bash_profile         # ccacheの使用宣言
$ echo "export CCACHE_DIR=~/.ccache" >> ~/.bashrc # キャッシュの格納先(任意)
$ echo "export set CC='ccache gcc'" >> ~/.bashrc  # gccコマンド時にccacheを使用。
$ echo "export set CXX='ccache g++'" >> ~/.bashrc # g++コマンド時にccacheを使用。

$ source ~/.bashrc  # ログインし直す代わりに、手動で変更した設定の反映(初回時のみ)
```

---


### makeコマンドでビルドする際の対応

Linuxでc言語開発をする場合、Makefileを使用します。ccacheを利用する場合は、以下のいずれかを行う必要があります。

- Makefile内のCC、CXX変数を変更(例：CC="ccache gcc")
- makeコマンド実行時にオプションを付ける事(例：make CC="ccache gcc")
- コンパイラ指定変数(例：CC)の前に、"ccache"を付与

ccacheを有効にする場合は、gccコマンドの前に"ccache "文字列を付与しなければいけない制約があります。そのため、上記のように、Makefileを直接編集するか、makeのオプションでccacheの使用を明示します。簡単なMakefileの修正例を以下に示します。

```
CC     := gcc                                                                                  
CFLAGS := -g -Wall                                                                             
CCACHE := $(shell which ccache)                                                                
                                                                                                 
hello:test.c                                                                                   
    $(CCACHE) $(CC) -o hello test.c    
```

---


### ccacheの設定変更

```
Usage:
    ccache [options]
```

| オプション | 説明 |
| --- | --- |
| \-c, --cleanup | 古いファイルを削除し、サイズカウンタを再計算します。 |
| \-C, --clear | 完全にキャッシュを削除します。 |
| \-F, --max-files=N | キャッシュ内に格納できる最大ファイル数を設定します。通常は0(制限なし)。 |
| \-M, --max-size=SIZE | キャッシュの最大サイズを設定します(◯G、◯M、◯Kという記述方法で指定。例：`ccache -M 10G` ) |
| \-s, --show-stats | 統計情報(キャッシュヒット率、キャッシュ内のファイル数など)を表示します。 |
| \-z, --zero-stats | 統計情報のカウンターをゼロクリア(初期化)します。 |

---


### 参考：ccache利用時のビルド時間

最後に、参考として、Linuxカーネルのビルド時間(ccache有り、無し)を比較します。使用したカーネルはVersion4.8.9(stable)、コンフィグはx86\_64\_defconfigです。計測時に使用したコマンドは、通常ビルド時が`time make -j8`、ccache使用時が`time make CXX="ccache g++" CC="ccache gcc" -j8`です。

各実行時間を以下の表に示します。  
ccacheを利用した場合、二回目以降のビルドが劇的に早くなります。ちなみに、[ccache公式のパフォーマンス測定](https://ccache.samba.org/performance.html)では、約37倍の実行速度が示されています。

| キャッシュの有無 | 実行時間 | 倍率 |
| --- | --- | --- |
| ccache無し(通常ビルド時) | 6分28秒 | 1.00x |
| ccache有り(初回ビルド時、キャッシュ無し) | 7分20秒 | 0.88x |
| ccache有り(二回目ビルド時、キャッシュ有り) | 29秒 | 13.38x |
