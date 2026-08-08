---
title: "Computer Systems"
date: 2026-08-04
draft: false
weight: 10
cardLabel: "コンピュータシステム"
cardNote: "OS・カーネル・ハードウェア寄りの技術ノート"

ShowToc: true
TocOpen: true
hidemeta: false
disableShare: true
ShowBreadCrumbs: true
description: ""
---

現在は、既存のブログ記事から Computer Systems に関係する記事（組み込みエンジニア時代に書いた記事）を分類してリンクしています。

---

### コンテンツ一覧

#### Assembly / ARM

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Cortex-A8 (ARMv7-A, e.x. BeagleBone Black）のレジスタ情報／アセンブラ命令／インラインアセンブラの書き方](/post/ja/2020-11-21-cortex-a8-armv7-a-e-x-beaglebone-blackのレジスタ情報アセンブラ命令/) | ARM / アセンブラ |
| 2 | [Cortex-A8 (ARMv7-A, e.x. BeagleBone Black）におけるコンテキストスイッチ／割り込み操作／Halt](/post/ja/2020-11-21-cortex-a8-armv7-a-e-x-beaglebone-blackにおけるコンテキストスイッチ割/) | ARM / OS |

---

#### Linux Kernel

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Raspberry Pi3(Linux Kernel)のBoot Sequence Step1:アーキテクチャ依存部](/post/ja/2018-12-31-raspberry-pi3linux-kernelのboot-sequence-step1アーキテクチャ依存部/) | Boot Sequence |
| 2 | [環境構築: Linux Kernelモジュールの作成準備](/post/ja/2019-01-27-環境構築-linux-kernelモジュールの作成準備/) | 開発環境 |
| 3 | [Linux Kernel: prink(print kernel)によるメッセージ出力](/post/ja/2019-02-02-linux-kernel-prinkprint-kernelによるメッセージ出力/) | ログ出力 |
| 4 | [Linux Kernel: エラー番号の一覧](/post/ja/2019-02-24-linux-kernel-エラー番号の一覧/) | エラー処理 |
| 5 | [Linux Kernel: NULLポインタエラーハンドリング(ERR_PTR, IS_ERR, PTR_ERR)](/post/ja/2019-03-02-linux-kernel-nullポインタエラーハンドリングerr_ptr-is_err-ptr_err/) | エラー処理 |
| 6 | [Linux Kernel: 構造体メンバポインタから構造体の先頭ポインタを得るcontainer_ofマクロ](/post/ja/2019-04-06-linux-kernel-構造体メンバポインタから構造体の先頭ポイ/) | マクロ |
| 7 | [Linux Kernel: List構造を操作するためのAPI(Listの使い方)](/post/ja/2019-04-07-linux-kernel-list構造を操作するためのapilistの使い方/) | データ構造 |
| 8 | [Linux Kernel: __initマクロ、__exitマクロの役割(メモリの有効利用)](/post/ja/2019-04-29-linux-kernel-__initマクロ__exitマクロの役割メモリの有効利用/) | メモリ |
| 9 | [Linux Kernelの簡単なCharacter Deviceを作成する方法(Linked List APIの使用方法サンプル)](/post/ja/2019-06-23-linux-kernelの簡単なcharacter-deviceを作成する方法linked-list-apiの使用方法サ/) | Device Driver |
| 10 | [Linux Kernel: mutex APIによるロック(排他)方法](/post/ja/2019-07-07-linux-kernel-mutex-apiによるロック排他方法/) | 排他制御 |
| 11 | [Linux Kernel Tree内で自作Kernelモジュールをビルドする方法(MakefileとKconfigの書き方)](/post/ja/2019-07-15-linux-kernel-tree内で自作kernelモジュールをビルドする方法makefileとkconfi/) | ビルド |

---

#### Linux / Userland

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Linux Command Optionの慣習(一般的なOption一覧)](/post/ja/2019-02-23-linux-command-optionの慣習一般的なoption一覧/) | CLI |
| 2 | [mmdebstrapによるarmhf向けrootfsの作成方法(公式最小サイズ27MB)](/post/ja/2019-03-10-mmdebstrapによるarmhf向けrootfsの作成方法公式最小サイズ27mb/) | rootfs |
| 3 | [Linuxコマンドのソースコードを取得する方法(Debian環境)：オリジナルコマンド作成前の勉強向け](/post/ja/2019-06-01-linuxコマンドのソースコードを取得する方法debian環境/) | ソースコード取得 |
| 4 | [起動済みプロセス（例：デーモンプロセス）の標準出力を確認する方法](/post/ja/2020-07-04-起動済みプロセス（例：デーモンプロセス）の標/) | プロセス |
| 5 | [Debian(64bit)で32bitバイナリを実行もしくは作成する方法（C言語）](/post/ja/2020-08-19-debian64bitで32bitバイナリを実行もしくは作成する方法（c言/) | バイナリ |
| 6 | [manコマンドによる「ASCII ⇔ 8進数、10進数、16進数の変換表」](/post/ja/2020-01-17-manコマンドによる「ascii8進数、10進数、16進数の変換表/) | 文字コード |
| 7 | [/etc/passwdに記載された/usr/sbin/nologin, /bin/falseとは何か【ログイン禁止】](/post/ja/2020-04-16-etc-passwdに記載された-usr-sbin-nologin-bin-falseとは何か【ログイン禁止/) | ユーザ管理 |
| 8 | [【visudo / vigr / vipw】システムファイルをsudo viで編集は駄目【sudoers / group / passwd】](/post/ja/2020-12-16-【visudo-vigr-vipw】システムファイルをsudo-viで編集は駄目【sudoers-g/) | システムファイル |
| 9 | [【roff形式を手書きは無理ゲー】manページをMarkdown + Pandocで作成【with manページお作法】](/post/ja/2020-12-19-【roff形式を手書きは無理ゲー】manページをmarkdown-pandocで作/) | man page |
| 10 | [環境構築：Debianソースコードパッケージをビルドする方法(debソースパッケージ構築ツールのインストール)](/post/ja/2019-06-01-環境構築：debianソースコードパッケージをビルドす/) | パッケージ |
| 11 | [Debian: 任意のtesting/unstableパッケージのみをinstallする方法(システム全体はstableを維持)](/post/ja/2019-03-09-debian-任意のtesting-unstableパッケージのみをinstallする方法システ/) | パッケージ |
| 12 | [【LPICで見た】/etc/motdの内容を出力しているのは誰？【答え:sshd】](/post/ja/2020-12-01-【lpicで見た】-etc-motdの内容を出力しているのは誰/) | ログイン |
| 13 | [Ubuntu (20.04)へsshログインした際に表示されるWelcomeメッセージの仕組みと表示しない方法](/post/ja/2021-08-14-ubuntu-20-04へsshログインした際に表示されるwelcomeメッセージ/) | ログイン |
| 14 | [【Bash / Ruby / Python3】オプション解析する方法の比較](/post/ja/2020-04-11-【bash-ruby-python3】オプション解析する方法の比較/) | CLI |
| 15 | [【Bash / Ruby / Python3】root権限を確認する方法の比較](/post/ja/2020-04-11-【bash-ruby-python3】root権限を確認する方法の比較/) | 権限 |
| 16 | [【Bash / Ruby / Python3】ユーザ名 / UID / グループ名 / GIDを取得する方法の比較](/post/ja/2020-04-12-【bash-ruby-python3】ユーザ名-uid-グループ名-gidを取得する方法/) | ユーザ管理 |

---

#### Toolchain / Debugging

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [ccache(compiler cache)によるビルド高速化](/post/ja/2019-01-26-ccachecompiler-cacheによるビルド高速化/) | ビルド |
| 2 | [【Vim8.1.xから標準機能】VimからGDBを起動する方法(マウスでGDBを操作可能)](/post/ja/2019-09-14-【vim8-1-xから標準機能】vimからgdbを起動する方法マウス/) | デバッグ |

---

#### External Articles

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [XINU をソースコードから学習する](https://nao1215.github.io/LearningXinuFromSource/html/index.html) | OS / Code Reading |
| 2 | [Raspberry Pi3 with Yocto Project：環境構築](https://qiita.com/Nao1215/items/399b24bf5d9d81ac087d) | Yocto / 組み込みLinux |
| 3 | [Raspberry Pi2 Linuxカーネルのクロスコンパイル方法(仮想環境Ubuntu14.04による)](https://qiita.com/Nao1215/items/f4cf7988281fd807951c) | Linux Kernel / Cross Compile |
| 4 | [ビルド作業と向き合う：Makefile、ccache、Autotools、Yocto Projectについて](https://qiita.com/Nao1215/items/06bc77f1002a42adde15) | Build System |

---

#### C / System Programming

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [C言語で非推奨なC標準関数(例:strcpy)をコンパイルエラーにする方法](/post/ja/2019-09-07-c言語で非推奨なc標準関数例strcpyをコンパイルエラー/) | C / Toolchain |
| 2 | [【苦行】C言語で正規表現を用いる方法【標準Cライブラリ(glibc)使用】](/post/ja/2020-11-01-【苦行】c言語で正規表現を用いる方法【標準cライ/) | glibc |
| 3 | [【C言語】static(private)関数をユニットテストする3つの方法](/post/ja/2020-04-26-【c言語】staticprivate関数をユニットテストする3つの方法/) | C |
| 4 | [【C言語】\_Generic(C11)、GCC4.6以降または\_\_attribute\_\_((overloadable))によるオーバーロード](/post/ja/2021-05-15-【c言語】_genericc11gcc4-6以降または__attribute__overloadableによるオーバ/) | C / GCC |
| 5 | [【コーディングルール】C言語ライブラリのAPIを実装する際に注意すべき事柄](/post/ja/2020-12-19-【コーディングルール】c言語ライブラリのapiを実/) | API設計 |

---

#### Storage / Filesystem

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [autofsを用いてHDD/SSD/USBメモリを起動時に自動マウントする方法(Debian)](/post/ja/2019-10-05-autofsを用いてhdd-ssd-usbメモリを起動時に自動マウントする/) | mount |
| 2 | [gdisk/mkfsコマンドで2TB以上の大容量HDDをフォーマットする方法](/post/ja/2019-10-05-gdisk-mkfsコマンドで2tb以上のhddをフォーマットする方法/) | filesystem |
| 3 | [Raspberry Pi4のimage（データ）をバックアップし、より大容量のSDカードへ移行する方法](/post/ja/2020-09-02-raspberry-pi4のimage（データ）をバックアップしより大容量/) | backup |
| 4 | [Raspberry Pi3をsambaファイルサーバ化し、Linux/Mac/Winでファイル共有(外付けSSDを使用)](/post/ja/2019-03-24-raspberry-pi3をファイルサーバsamba化しlinux-mac-winでファイル共有/) | file server |

---

#### Code Reading

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [コードリーディング(C言語)：chroot / ischroot](/post/ja/2019-01-20-【コードリーディングc言語】chroot-ischroot/) | Linux Userland |
| 2 | [環境構築：Redox向けcoreutils(Rust)のCode Reading準備およびReading対象コマンド一覧](/post/ja/2019-05-03-環境構築：redox向けcoreutilsrustのcode-reading準備およびreading対象コマ/) | coreutils |
| 3 | [【静的解析】ソースコード解析補助ツールSourcetrailの導入方法【例：systemd(C言語)】](/post/ja/2020-12-12-【静的解析】ソースコード解析補助ツールsourcetrailの導/) | systemd |

---

#### Hardware / Boot

| No. | 項目 | カテゴリ |
| --- | --- | --- |
| 1 | [Raspberry Pi3: 公式ツールおよびHW仕様](/post/ja/2019-01-01-raspberry-pi3-公式ツールおよびhw仕様/) | Raspberry Pi |
| 2 | [Debian10をRyzen 3800X環境で動かそうとしてハマった内容(グラボ必須、BIOS設定、Kernel設定)](/post/ja/2019-09-29-debian10をryzen-3800x環境で動かそうとしてハマった内容グラボ/) | Kernel設定 |
| 3 | [【WatchDogTimer】Raspberry Pi4サーバがフリーズ(停止)した場合に自動再起動する方法【HeartBeat】](/post/ja/2020-11-28-【watchdogtimer】raspberry-pi4サーバがフリーズ停止した場合に自動/) | Watchdog |

---

### 参考文献（手元にある書籍）

- [詳解 Linuxカーネル 第3版](https://www.oreilly.co.jp/books/9784873113135/)
- [Linuxカーネル2.6解読室](https://www.sbcr.jp/product/4797338261/)
- [Linuxプログラミングインターフェース](https://www.oreilly.co.jp/books/9784873115856/)
- [新装改訂版 Linuxのブートプロセスをみる](https://tatsu-zine.com/books/linux-bootprocess?srsltid=AfmBOopyZZOSAMX3BfHBzoZK5nYonZ_3qrTvwXG3_-S3pN5Q9-y8IOwc)
- [Linux Device Driver Development](https://www.packtpub.com/en-us/product/linux-device-driver-development-9781803235943)
- [Linuxデバイスドライバプログラミング](https://www.sbcr.jp/product/4797346428/)
- [Xinuオペレーティングシステムデザイン 改訂2版](https://tatsu-zine.com/books/xinu-os-design/samplepage?srsltid=AfmBOop5s-yE7_3Z7L1opVjA6909NsZOLd8oyCfjC4fc_jZEk2QsKOA1)
- [ゼロからのOS自作入門](https://book.mynavi.jp/ec/products/detail/id=121220)
- [UNIXという考え方](https://www.ohmsha.co.jp/book/9784274064067.html)
- [Linuxネットワーク プログラミングバイブル](https://www.shuwasystem.co.jp/book/9784798028620.html)
- [超例解Linuxカーネルプログラミング～最先端Linuxカーネルの修正コードから学ぶソフトウェア品質～](https://book.mynavi.jp/manatee/books/detail/id=105523)
- [［改訂新版］プロのためのLinuxシステム構築・運用技術](https://gihyo.jp/book/2016/978-4-7741-8426-5)
- [動くメカニズムを図解&実験! Linux超入門](https://shop.cqpub.co.jp/detail/1832/)
- [最新コンパイラ構成技法](https://www.shoeisha.co.jp/book/detail/9784798114682)
- [flex & bison](https://www.oreilly.com/library/view/flex-bison/9780596805418/)
- [APIデザインの極意 Java/NetBeansアーキテクト探究ノート](https://book.impress.co.jp/books/1113101014)
- [C/C++ セキュアコーディング 第2版](https://www.jpcert.or.jp/securecoding_book_2nd.html)
- [C言語によるオブジェクト指向プログラミング入門](https://www.shoeisha.co.jp/book/detail/9784798121130)
- [モダンC言語プログラミング 統合開発環境、デザインパターン、エクストリーム・プログラミング、テスト駆動開発、リファクタリング、継続的インテグレーションの活用](https://tatsu-zine.com/books/modern-cprogramming?srsltid=AfmBOoqr4Wt2hZLbu3ON6omQohBmCxipDqSfz1Uirj6ZnkzXptQDUfPk)
- [詳説 Cポインタ](https://www.oreilly.co.jp/books/9784873116563/)
- [lsを読まずにプログラマを名乗るな！](https://www.shuwasystem.co.jp/book/9784798039435.html)
- [Autotools, 2nd Edition: A Practitioner's Guide to GNU Autoconf, Automake, and Libtool](https://www.amazon.co.jp/Autotools-2nd-John-Calcote/dp/1593279728)
- [Embedded Linux Development Using Yocto Project Cookbook](https://www.oreilly.com/library/view/embedded-linux-development/9781788399210/ae722662-967a-48a6-a89d-e35190c65f99.xhtml)
- [Inside Linux Software　～オープンソースソフトウェアのからくりとしくみ～](https://www.shoeisha.co.jp/book/detail/9784798112831)
- [入門Debianパッケージ](https://gihyo.jp/book/2006/4-7741-2768-X)
