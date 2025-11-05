---
title: "shc（Shell Script Compiler）でスクリプトをバイナリ化（暗号化）する方法"
type: post
date: 2021-08-29
categories:
  - "linux"
tags:
  - "bash"
  - "linux"
  - "shell"
  - "shellscript"
cover:
  image: images/cyber-security-3400657_640-min.jpg
  alt: "shc（Shell Script Compiler）でスクリプトをバイナリ化（暗号化）する方法"
  hidden: false
images: ["post/2021-08-29-shc（shell-script-compiler）でスクリプトをバイナリ化（暗号化）/images/cyber-security-3400657_640-min.jpg"]
---

## 前書き：Shell Scriptの中身を見せたくない

通常の開発業務では、Shell Scriptをバイナリ化（かつ暗号化）する利点はありません。自分しか解読できないShell Scriptは、他のチームメンバにとっては迷惑な存在（負債）になります。

が、Shell Scriptのバイナリ化に全く利点が無い訳ではありません。Shell Scriptのリリース後に発生する面倒事を避けるために、バイナリ化を検討する事もあります。

Shell Scriptをバイナリ化する利点

- 機密保持（顧客にShell Scriptを解読をさせない）
- Shell Scriptの改変防止

本記事では、shc（Shell Script Compiler）を用いてShell Scriptをバイナリ化する方法を紹介します。

## 検証環境

Ubuntu 21.04、Bash 5.1.4、shc 4.0.3を使用します。

```
           ./oydmMMMMMMmdyo/.              nao@nao 
        :smMMMMMMMMMMMhs+:++yhs:           ------- 
     `omMMMMMMMMMMMN+`        `odo`        OS: Ubuntu Budgie 21.04 x86_64 
    /NMMMMMMMMMMMMN- `sN/       Host: B450 I AORUS PRO WIFI 
  `hMMMMmhhmMMMMMMh               sMh`     Kernel: 5.11.0-31-generic 
 .mMmo- /yMMMMm`              `MMm.    Uptime: 12 hours, 45 mins 
 mN/       yMMMMMMMd- MMMm    Packages: 2830 (dpkg), 11 (snap) 
oN- oMMMMMMMMMms+//+o+:    :MMMMo   Shell: bash 5.1.4 
m/          +NMMMMMMMMMMMMMMMMm. :NMMMMm   Resolution: 2560x1080 
M`           .NMMMMMMMMMMMMMMMNodMMMMMMM   DE: Budgie 10.5.2 
M- sMMMMMMMMMMMMMMMMMMMMMMMMM   WM: Mutter(Budgie) 
mm`           mMMMMMMMMMNdhhdNMMMMMMMMMm   Theme: Yaru-dark [GTK2/3] 
oMm/        .dMMMMMMMMh:      :dMMMMMMMo   Icons: ubuntu-mono-dark [GTK2/3] 
 mMMNyo/:/sdMMMMMMMMM+          sMMMMMm    Terminal: tilix 
 .mMMMMMMMMMMMMMMMMMs           `NMMMm.    CPU: AMD Ryzen 5 3400G (8) @ 3.700GHz 
  `hMMMMMMMMMMM.oo+.            `MMMh`     GPU: AMD ATI 09:00.0 Picasso 
    /NMMMMMMMMMo                sMN/       Memory: 10025MiB / 30099MiB 
     `omMMMMMMMMy.            :dmo`
        :smMMMMMMMh+-`   `.:ohs:                                   
           ./oydmMMMMMMdhyo/.                                      
```

## shcコマンドの概要

[shcコマンド](https://github.com/neurobin/shc)は、C言語で実装されたシェルスクリプトコンパイラです（GPL v3）。[ARC4](https://e-words.jp/w/RC4.html)で暗号化したShell ScriptをC言語にソースコード中に埋め込み、そのコードをコンパイルする事によってバイナリを生成しています。生成したバイナリの有効期限を設定する事もできます。

以下、「バイナリ化の流れ」と「バイナリ化されたShell Scriptを実行する流れ」です。

1. "shc -f $SCRIPT"で指定された$SCRIPTを暗号化
2. $SCRIPT.x.cという名称のC言語コード（暗号化された$SCRIPTをコード中に含む）を生成
3. $SCRIPT.x.cをコンパイルし、$SCRIPT.xを生成
4. $SCRIPT.xの実行時、暗号化された$SCRIPTを復号
5. 手順4.の完了後、"sh -c $復号した文字列"を実行

上記の2.と5.の通り、途中でC言語ソースコードに変換されていますが、生成されるのはshellに依存したバイナリです（Shellの-cオプションは、指定した文字列を実行するオプション）

## shcコマンドのインストール

Ubuntuの場合は、aptパッケージマネージャーでインストールできます。

```
$ sudo apt install shc

```

最新版をビルドする場合は、以下の手順です。

```
$ sudo apt install git build-essential   (注釈) ビルドに必要なツールのインストール

$ git clone https://github.com/neurobin/shc.git
$ cd shc
$ ./configure               (注釈) システム環境に合わせた設定
$ make                      (注釈) ビルド
$ sudo make install         (注釈) インストール

```

## shcコマンドのオプション

| **オプション** | **オプション引数** | **説明** |
| :-: | :-: | :-: |
| \-e | あり | 失効日をdd/mm/yyyy形式で指定   （デフォルト：無効） |
| \-m | あり | 失効した場合のメッセージ   （デフォルト："Please contact your provider"） |
| \-f | あり | コンパイル（暗号化）対象のスクリプト名 |
| \-i | あり | Shellインタプリタへのインラインオプション（例：-e） |
| \-x | あり | printfフォーマットでコマンドを実行（例：exec('%s',@ARGV);） |
| \-l | あり | Last shellオプション（例：--） |
| \-o | あり | 出力ファイル名   （デフォルト：元ファイル名の末尾に”.x”を付与した名前） |
| \-r | なし | セキュリティを緩和する。再配布可能なバイナリを作る |
| \-v | なし | コンパイル時の出力を増やす |
| \-S | なし | rootユーザが実行するプログラムとしてuidをセットする |
| \-D | なし | デバッグ実行を有効化 |
| \-U | なし | untraceable（トレース不可な）バイナリを作成 |
| \-H | なし | 追加のセキュリティ保護（まだ未完成のオプション） |
| \-C | なし | ライセンスを表示して終了 |
| \-A | なし | shcコマンドの概要を表示して終了 |
| \-B | なし | Busybox向けにコンパイル |
| \-H | なし | ヘルプメッセージを表示して終了 |

## shcコマンドによるバイナリ生成の例

今回の例では、ユーザが管理者権限を持つかどうかを表示するスクリプト（shell.sh）をバイナリ化します。shell.shの内容は、以下の通りです。

```
#!/bin/bash

function errMsg() {
    local message="$1"
    echo -n -e "\033[31m\c"  # 文字色を赤に変更                      
    echo "${message}" >&2
    echo -n -e "\033[m\c"  　# 文字色を元に戻す                     
}

# isRoot()は、root権限を持つかどうかを確認する。
function isRoot() {
    if [ ${EUID:-${UID}} != 0 ]; then
        errMsg "${FUNCNAME[0]}: You are not root."
        exit 1
    fi
    echo "You are root."
}

isRoot

```

shcコマンドでshell.shをバイナリ化します。-oでバイナリの名前を指定できますが、今回は指定せずにデフォルトの挙動を確認します。

```
$ ls
shell.sh

(注釈) バイナリ化
$ shc -f shell.sh 

(注釈) *.xはバイナリ、*.cはバイナリ作成時に生成したC言語ソースコード
$ ls
shell.sh  shell.sh.x  shell.sh.x.c

```

オリジナルスクリプトとバイナリの実行結果を比較します。同じ結果です。

```
$ ./shell.sh
isRoot: You are not root.
$ ./shell.sh.x 
isRoot: You are not root.

$ sudo ./shell.sh
You are root.
$ sudo ./shell.sh.x 
You are root.

```
