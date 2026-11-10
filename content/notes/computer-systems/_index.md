---
title: "Computer Systems"
date: 2026-08-04
draft: false
weight: 80
cardLabel: "コンピュータシステム"
cardNote: "OS・カーネル・ハードウェア寄りの技術ノート"

ShowToc: true
TocOpen: true
hidemeta: false
disableShare: true
ShowBreadCrumbs: true
description: ""
topics:
  - name: "Assembly / ARM"
    related:
      - path: "/post/ja/2020-11-21-cortex-a8-armv7-a-e-x-beaglebone-black）のレジスタ情報／アセンブラ命令／"
      - path: "/post/ja/2020-11-21-cortex-a8-armv7-a-e-x-beaglebone-black）におけるコンテキストスイッチ／割"
  - name: "Linux Kernel"
    related:
      - path: "/post/ja/2018-12-31-raspberry-pi3linux-kernelのboot-sequence-step1アーキテクチャ依存部"
      - path: "/post/ja/2019-01-27-環境構築-linux-kernelモジュールの作成準備"
      - path: "/post/ja/2019-02-02-linux-kernel-prinkprint-kernelによるメッセージ出力"
      - path: "/post/ja/2019-02-24-linux-kernel-エラー番号の一覧"
      - path: "/post/ja/2019-03-02-linux-kernel-nullポインタエラーハンドリングerr_ptr-is_err-ptr_err"
      - path: "/post/ja/2019-04-06-linux-kernel-構造体メンバポインタから構造体の先頭ポイ"
      - path: "/post/ja/2019-04-07-linux-kernel-list構造を操作するためのapilistの使い方"
      - path: "/post/ja/2019-04-29-linux-kernel-__initマクロ、__exitマクロの役割メモリの有効利用"
      - path: "/post/ja/2019-06-23-linux-kernelの簡単なcharacter-deviceを作成する方法linked-list-apiの使用方法サ"
      - path: "/post/ja/2019-07-07-linux-kernel-mutex-apiによるロック排他方法"
      - path: "/post/ja/2019-07-15-linux-kernel-tree内で自作kernelモジュールをビルドする方法makefileとkconfi"
  - name: "Linux / Userland"
    related:
      - path: "/post/ja/2019-02-23-linux-command-optionの慣習一般的なoption一覧"
      - path: "/post/ja/2019-03-10-mmdebstrapによるarmhf向けrootfsの作成方法公式最小サイズ27mb"
      - path: "/post/ja/2019-06-01-linuxコマンドのソースコードを取得する方法debian環境"
      - path: "/post/ja/2020-07-04-起動済みプロセス（例：デーモンプロセス）の標"
      - path: "/post/ja/2020-08-19-debian64bitで32bitバイナリを実行もしくは作成する方法（c言"
      - path: "/post/ja/2020-01-17-manコマンドによる「ascii8進数、10進数、16進数の変換表"
      - path: "/post/ja/2020-04-16-etc-passwdに記載された-usr-sbin-nologin-bin-falseとは何か【ログイン禁止"
      - path: "/post/ja/2020-12-16-【visudo-vigr-vipw】システムファイルをsudo-viで編集は駄目【sudoers-g"
      - path: "/post/ja/2020-12-19-【roff形式を手書きは無理ゲー】manページをmarkdown-pandocで作"
      - path: "/post/ja/2019-06-01-環境構築：debianソースコードパッケージをビルドす"
      - path: "/post/ja/2019-03-09-debian-任意のtesting-unstableパッケージのみをinstallする方法システ"
      - path: "/post/ja/2020-12-01-【lpicで見た】-etc-motdの内容を出力しているのは誰？【"
      - path: "/post/ja/2021-08-14-ubuntu-20-04へsshログインした際に表示されるwelcomeメッセージ"
      - path: "/post/ja/2020-04-11-【bash-ruby-python3】オプション解析する方法の比較"
      - path: "/post/ja/2020-04-11-【bash-ruby-python3】root権限を確認する方法の比較"
      - path: "/post/ja/2020-04-12-【bash-ruby-python3】ユーザ名-uid-グループ名-gidを取得する方法"
  - name: "Toolchain / Debugging"
    related:
      - path: "/post/ja/2019-01-26-ccachecompiler-cacheによるビルド高速化"
      - path: "/post/ja/2019-09-14-【vim8-1-xから標準機能】vimからgdbを起動する方法マウス"
  - name: "C / System Programming"
    related:
      - path: "/post/ja/2019-09-07-c言語で非推奨なc標準関数例strcpyをコンパイルエラー"
      - path: "/post/ja/2020-11-01-【苦行】c言語で正規表現を用いる方法【標準cライ"
      - path: "/post/ja/2020-04-26-【c言語】staticprivate関数をユニットテストする3つの方法"
      - path: "/post/ja/2021-05-15-【c言語】_genericc11、gcc4-6以降または__attribute__overloadableによるオーバ"
      - path: "/post/ja/2020-12-19-【コーディングルール】c言語ライブラリのapiを実"
  - name: "Storage / Filesystem"
    related:
      - path: "/post/ja/2019-10-05-autofsを用いてhdd-ssd-usbメモリを起動時に自動マウントする"
      - path: "/post/ja/2019-10-05-gdisk-mkfsコマンドで2tb以上のhddをフォーマットする方法"
      - path: "/post/ja/2020-09-02-raspberry-pi4のimage（データ）をバックアップし、より大容量"
      - path: "/post/ja/2019-03-24-raspberry-pi3をファイルサーバsamba化し、linux-mac-winでファイル共有"
  - name: "Code Reading"
    related:
      - path: "/post/ja/2019-01-20-【コードリーディングc言語】chroot-ischroot"
      - path: "/post/ja/2019-05-03-環境構築：redox向けcoreutilsrustのcode-reading準備およびreading対象コマ"
      - path: "/post/ja/2020-12-12-【静的解析】ソースコード解析補助ツールsourcetrailの導"
  - name: "Hardware / Boot"
    related:
      - path: "/post/ja/2019-01-01-raspberry-pi3-公式ツールおよびhw仕様"
      - path: "/post/ja/2019-09-29-debian10をryzen-3800x環境で動かそうとしてハマった内容グラボ"
      - path: "/post/ja/2020-11-28-【watchdogtimer】raspberry-pi4サーバがフリーズ停止した場合に自動"
  - name: "External Articles"
    related:
      - title: "XINU をソースコードから学習する"
        url: "https://nao1215.github.io/LearningXinuFromSource/html/index.html"
        image: "images/ext-xinu-source.webp"
      - title: "Raspberry Pi3 with Yocto Project：環境構築"
        url: "https://qiita.com/Nao1215/items/399b24bf5d9d81ac087d"
        image: "images/ext-yocto-environment.webp"
      - title: "Raspberry Pi2 Linuxカーネルのクロスコンパイル方法(仮想環境Ubuntu14.04による)"
        url: "https://qiita.com/Nao1215/items/f4cf7988281fd807951c"
        image: "images/ext-rpi2-kernel-cross-compile.webp"
      - title: "ビルド作業と向き合う：Makefile、ccache、Autotools、Yocto Projectについて"
        url: "https://qiita.com/Nao1215/items/06bc77f1002a42adde15"
---

現在は、既存のブログ記事から Computer Systems に関係する記事（組み込みエンジニア時代に書いた記事）を分類してリンクしています。
