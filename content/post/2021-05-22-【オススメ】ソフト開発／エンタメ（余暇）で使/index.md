---
title: "【オススメ】ソフト開発／エンタメ（余暇）で使用するLinuxアプリ【Debian／elementary OS】"
type: post
date: 2021-05-22
categories:
  - "linux"
tags:
  - "linux"
  - "アプリ"
  - "開発"
cover:
  image: images/icon-1328421_640.jpg
  alt: "【オススメ】ソフト開発／エンタメ（余暇）で使用するLinuxアプリ【Debian／elementary OS】"
  hidden: false
---

## 前書き：オススメ？当たり前？

本記事は、読者の皆様にLinuxアプリをオススメするように見せかけた備忘録記事です。

私は、2018年から開発環境（≒普段使いのPC）をMacからLinuxに移行しました。Linux環境に移行した後もDebian → elementary OSと移行を続けていて、開発や余暇で使用するアプリを記録しておく必要性が出てきました。

そこで、本記事では私が頻繁に使用するLinuxアプリをリストアップします。Linuxアプリと言っても、最近はクロスプラットホーム対応アプリやWebアプリの数が増えました。そのため、Windows／Macユーザの方にとっても馴染みのあるアプリが登場します。

## リストから除外するアプリ

ターミナルで使用するCLIコマンド（基本的なコマンド）は、除外します。例えば、[git(構成管理)](https://git-scm.com/)、[gcc(コンパイラ)](https://gcc.gnu.org/)、[ssh(他PCへのログイン)](http://www.openssh.com/)、[tmux(ターミナル画面分割)](https://github.com/tmux/tmux/wiki)、[fish(shell)](https://fishshell.com/)、[sdkman(環境構築ツール)](https://sdkman.io/)、[ag(高速版grep)](https://github.com/ggreer/the_silver_searcher)、[bat（カラフルなcat）](https://github.com/sharkdp/bat)等です。

この辺りのコマンドは、書いても書いてもキリがありません。また、私は上記のような基本的なコマンドを[Makefileとインストーラスクリプトを組み合わせて環境構築（インストール）](https://debimate.jp/2020/10/29/%e3%80%90tips%e3%80%91%e4%bd%95%e5%ba%a6%e3%82%82%e7%b9%b0%e3%82%8a%e8%bf%94%e3%81%99%e9%96%8b%e7%99%ba%e7%92%b0%e5%a2%83%e6%a7%8b%e7%af%89%e3%82%92makefile%e3%81%a8%e3%82%b7%e3%82%a7%e3%83%ab/)しています。つまり、備忘録が不要です（個人的な理由）。

さらに言えば、昔は[Linux Kernel開発者のようにターミナルに引きこもる硬派なエンジニア](https://cpplover.blogspot.com/2013/06/linux.html)に憧れていましたが、最近はGUIアプリを抵抗なく使うようになりました。「皆さんも使いやすいGUIアプリを知りたい筈」という前提で、アプリをリストアップします。

\[the\_ad id="598"\]

## エディタ／IDE

エディタは、Visual Studio Codeさえあれば十分な印象。

一昔前は、[Sublime Text](https://www.sublimetext.com/)や[Atom](https://atom.io/)では痒いところに手が届かなくてNeovimを選択していました。組み込みソフト屋時代は「Neovim最強！」でしたが、最近はVisual Studio Codeの使いやすさに負けて浮気しました。Neovimで多言語対応は辛かった。

| **アプリ名** | **説明／所感** |
| --- | --- |
| [Neovim](https://neovim.io/) | 日本人大好きvim一族。過去4年ほど愛用。私が使うプログラミング言語が増えてからはプラグイン管理の負荷が大きく、使用頻度が低下。 |
| [Visual Studio Code](https://azure.microsoft.com/ja-jp/products/visual-studio-code/) | 天下のMicrosoft製エディタ。プラグイン管理が楽であり、操作も直感的。ネットでの情報量が多く、動作が軽いのもポイント。稀に、Visual Studio Code内のターミナルでNeovimが顔を出す。 |
| [micro](https://micro-editor.github.io/) | シンプルなCLIエディタ。Windowsのメモ帳ポジション。日本語を書く場合とGitのコミットメッセージには、microを使う。 |
| [Android Studio](https://developer.android.com/studio?hl=ja) | Androidアプリ開発向け統合開発環境。 |
| [IntelliJ IDEA](https://www.jetbrains.com/ja-jp/idea/) | JVM（Java）系開発向け統合開発環境。有償版か無料版かでSpring FrameやDB周りの機能差あり。個人的にはVisual Studio Codeで十分。 |

## 調査／コード設計／GUI設計／静的解析

基本的には、静的解析、作図、仮想環境、GUI構築ツールをリストアップしています。

コード調査をシステマチックに行いたい気持ちが強いのですが、現状はSourcetrail + コードリーディングで実装を把握しています。そして、GUI設計ではモックアップツールが登場しません。

| **アプリ名** | **説明／所感** |
| --- | --- |
| [cloc](https://github.com/AlDanial/cloc) | コード行数カウンタ(CLI)。類似アプリの[VS Code Counter](https://marketplace.visualstudio.com/items?itemName=uctakeoff.vscode-counter)よりも気軽に叩きやすい。コード調査時はgit clone → clocがワンセット。  |
| [valgrind](https://valgrind.org/) | メモリ系の静的解析ツール。C/C++でメモリリークしない限り使わない。 |
| [cppcheck](http://cppcheck.sourceforge.net/) | 冗長な代入やnullチェック等を行う静的解析ツール。C/C++しかチェックできないため、[Coverity](https://www.synopsys.com/ja-jp/software-integrity/security-testing/static-analysis-sast.html)の代替ツールポジション。 |
| [lizard](https://github.com/terryyin/lizard) | 循環的複雑度を計測する静的解析ツール。複雑度やメソッドの長さに対して警告が出せるため、冗長なコードの検出に役立つ。[使用方法の記事はコチラ。](https://debimate.jp/2021/05/19/%e3%80%90c-c-c-java%e5%af%be%e5%bf%9c%e3%80%91%e5%be%aa%e7%92%b0%e7%9a%84%e8%a4%87%e9%9b%91%e5%ba%a6%e3%81%ae%e8%a8%88%e6%b8%ac%e3%83%84%e3%83%bc%e3%83%ab-lizard%e3%81%ae%e5%b0%8e%e5%85%a5%e6%96%b9/) |
| [Sourcetrail](https://www.sourcetrail.com/) | ソースコード（クラス）の関連性をビジュアライズする静的解析ツール。環境構築がやや面倒な点を除けば、コードを直接読むより処理を把握しやすい。[導入方法の記事はコチラ](https://debimate.jp/2020/12/12/%e3%80%90%e9%9d%99%e7%9a%84%e8%a7%a3%e6%9e%90%e3%80%91%e3%82%bd%e3%83%bc%e3%82%b9%e3%82%b3%e3%83%bc%e3%83%89%e8%a7%a3%e6%9e%90%e8%a3%9c%e5%8a%a9%e3%83%84%e3%83%bc%e3%83%absourcetrail%e3%81%ae%e5%b0%8e/)。 |
| [drawio](https://app.diagrams.net/) | UML等の作図ツール。図の種類が豊富かつ無料。類似ツール（[Visio](https://www.microsoft.com/ja-jp/microsoft-365/visio/flowchart-software)、[plantuml](https://plantuml.com/ja/)、[dia](https://gitlab.gnome.org/GNOME/dia/)）と比較して、一歩踏み込んだ使いやすさ。 |
| [Docker](https://www.docker.com/) | コンテナ仮想化ツール。Linuxがお手軽に立ち上げられる便利さと引き換えに、管理が面倒。コンテナ管理を楽にするはずの[コンテナ管理基盤Kubernetes](https://kubernetes.io/ja/)は、私のスキルでは理解が追いつかない。 |
| [Virtual Box](https://www.virtualbox.org/) | 仮想化環境。主に仮想化環境でWindowsを立ち上げ、非常識なフォーマットドキュメントを読むために使用。それか[ランス](https://www.alicesoft.com/rance10/)のため。 |
| [VNC Viewer](https://www.realvnc.com/en/) | リモートデスクトップ。ラズパイ環境にssh接続できないヤラカシ（主に設定ミス）をした時に使用。サーバ持ちの人が使う印象。 |
| [Scene Builder](https://gluonhq.com/products/scene-builder/) | JavaFXを使用したGUIアプリの画面構築で使用。 |
| [Glade](https://glade.gnome.org/) | GTKを使用したGUIアプリの画面構築で使用。 |
| [Inkscape](https://inkscape.org/ja/) | ベクター画像エディタ。アイコン作成で使用。 |

## オフィス／ドキュメント系

「Linuxはオフィスツールが弱い」

多くの方が上記の認識だと思いますが、Exactly(その通りでございます)。Microsoft Ofiiceに飼いならされた私達が、同じクオリティ／操作性のアプリをLinuxで見つけるのは至難の業です。似ているアプリはありますが、似て非なるアプリです。

| **アプリ名** | **説明／所感** |
| --- | --- |
| [LibreOffice](https://ja.libreoffice.org/) | Microsoft Word／Excel／PowerPoint等に相当するオフィスツール。体裁の整えづらいWord、マクロのないExcel、配色が気になるPowerPointといった印象。文字化けや細かい挙動の差に苦しむが、他のLinuxアプリよりマシ。 |
| [Google Docs](https://www.google.com/intl/ja_jp/docs/about/) | Google版オフィスツール（Webアプリ）。LibreOfficeよりネットの情報量が多い印象。 |
| [メール](https://github.com/elementary/mail) | elementary OSデフォルトメーラー。[Thunderbird](https://www.thunderbird.net/ja/)も使用しましたが、どちらも使いやすさはイマイチ（Outlookに慣れすぎているだけ？） |
| [Slack](https://slack.com/intl/ja-jp/) | 人気のあるチャットツール。 |
| [Joplin](https://joplinapp.org/) | マークダウン形式でToDo、ノートを残せるアプリ。コート調査メモやブログネタを整理するために使用。類似アプリは[evernote](https://evernote.com/intl/jp)。 |
| [Evince](https://wiki.gnome.org/action/show/Apps/Evince) | PDFビューワー。 |

## エンターテイメント（マルチメディア、SNS）

Linuxは、意外とエンタメが弱くないです。

Linux上でGoogle ChromeやFireFoxが動作するため、Webアプリは何でも動きます。例えば、[Twitter](https://twitter.com/home)や[Instagram](https://www.instagram.com/?hl=ja)、[Amazon Prime](https://www.amazon.co.jp/Prime-Video/b?ie=UTF8&node=3535604051)や[Netflix](https://www.netflix.com/jp/)や[YouTube](https://www.youtube.com/)、[Reddit](https://www.reddit.com/)や[Komiflo](https://komiflo.com/)が使えます。

これらに加えて、Linuxネイティブアプリを併用すれば余暇を十分楽しめます。強いて弱みを挙げるとすれば、電子書籍とゲーム。間違いなく弱い。

| **アプリ名** | **説明／所感** |
| --- | --- |
| [Lollypop](https://wiki.gnome.org/Apps/Lollypop) | ミュージックプレイヤー。数百GBの音楽を取り扱っても落ちず、アーティスト情報や歌詞情報を表示する機能あり。アートワークもDL可能。 |
| [Plex Media Server](https://www.plex.tv/ja/media-server-downloads/) | 音楽、動画、写真を配信するためのメディアサーバー。自分の管理するメディアを一元管理できるため便利（最近、有料会員となった）。[導入記事はコチラ](https://debimate.jp/2020/10/31/%e3%80%90%e7%92%b0%e5%a2%83%e6%a7%8b%e7%af%89%e3%80%91raspberry-pi%e3%81%abplex-media-server%e3%82%92%e3%82%a4%e3%83%b3%e3%82%b9%e3%83%88%e3%83%bc%e3%83%ab%e3%80%90kodi%e3%80%81emby%e3%81%a8%e3%81%ae/)。 |
| [Cinema](https://appcenter.elementary.io/com.github.artemanufrij.playmyvideos/) | ムービープレイヤー（elementary OSフォルトアプリ）。オススメするほど多機能ではないが、シンプルで分かりやすい。 |
| [Photo](https://github.com/elementary/photos) | 写真管理アプリ（elementary OSフォルトアプリ）。雰囲気は、Macの写真アプリに類似。 |
| [Steam](https://store.steampowered.com/?l=japanese) | ゲーム配信プラットフォーム。Linux環境で動作するゲームの配信に力を入れているため、今後に期待。[Helltaker](https://store.steampowered.com/app/1289310/Helltaker/?l=japanese)が最近面白かった。 |

## 最後に：メインPCがLinuxでも結構大丈夫

「デスクトップPCをLinuxに変更しようかな」と気の迷いを起こしている方は、以下の記事も参考にしてみてください。Linuxデスクトップ環境の強みと弱みがまとめてあります。

https://debimate.jp/2020/08/26/%e5%85%83win%ef%bc%8fmac%e3%83%a6%e3%83%bc%e3%82%b6%e3%81%8c%e3%83%a1%e3%82%a4%e3%83%b3pc%e3%82%92linuxdebian%e3%81%ab%e3%81%97%e3%81%9f%e6%84%9f%e6%83%b3/
