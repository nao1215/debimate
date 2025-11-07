---
title: "Shell Scriptにバイナリ（例：tarball）を埋め込み、実行時にバイナリを取り出す方法"
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
  image: "images/walnuts-1739021_640-min.jpg"
  alt: "Shell Scriptにバイナリ（例：tarball）を埋め込み、実行時にバイナリを取り出す方法"
  hidden: false
---

## 前書き：スクリプトサイズが大きい理由

プロプラエタリソフト（例：商用ソフト）のShell Scriptインストーラのサイズを見たら、数百MBだった事はありませんか？

そのような場合は、.deb/.rpmパッケージやtarball等のバイナリがShell Scriptに埋め込まれている可能性が高いです。このようなインストーラは、実行時にバイナリ部分だけを取り出してから、バイナリを操作します。

上記の作りにする理由は、インストーラを単一スクリプト（一つのファイル）にしたいからでしょう。インストール手順がシンプルになりますし、ユーザが操作ミスする可能性も減ります。また、"$ wget $INSTALLER\_URL | sh"という形式でインストールもできます（複数のURLに対してwgetする必要がなくなります）。

本記事では、Shell Scriptにバイナリを埋め込み、実行時にバイナリを取り出す方法を紹介します。

## 検証環境

Ubuntu 21.04、Bash 5.1.4、tar (GNU tar) 1.34を使用します。

```
           ./oydmMMMMMMmdyo/.              nao@nao 
        :smMMMMMMMMMMMhs+:++yhs:           ------- 
     `omMMMMMMMMMMMN+`        `odo`        OS: Ubuntu Budgie 21.04 x86_64 
    /NMMMMMMMMMMMMN- `sN/       Host: B450 I AORUS PRO WIFI 
  `hMMMMmhhmMMMMMMh               sMh`     Kernel: 5.11.0-31-generic 
 .mMmo- /yMMMMm`              `MMm.    Uptime: 15 hours, 59 mins 
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
    /NMMMMMMMMMo                sMN/       Memory: 8887MiB / 30099MiB 
     `omMMMMMMMMy.            :dmo`
        :smMMMMMMMh+-`   `.:ohs:                                   
           ./oydmMMMMMMdhyo/.                                      
```

## 検証用のtarball作成

Shell Script（test.sh）を含むbinディレクトリを圧縮して、tarballを作成します。tarballの中に、他のファイル（例：パッケージや画像）を含んでも問題ありません。

```
$ ls bin/
test.sh

$ cat bin/test.sh
#/bin/bash
echo "Hello World"

$ tar cvfz bin.tar.gz bin

$ ls
bin  bin.tar.gz
```

## tarballを埋め込んだShell Scriptの作り方

Shell Scriptの末尾にバイナリを埋め込み、バイナリを実行時に取り出す考え方は、以下の通りです。

- 編集時：Shell Scriptの末尾に、tarball開始位置の目印（検索用マーカ）を付与
- 編集時：Shell Scriptの末尾（検索用マーカの後）に、tarballを連結（結合）
- 実行時：検索用マーカの次の行からShell Script末尾までを抽出（抽出した内容=tarball）

以下、Shell Script（embed.sh）の例です。

```
#!/bin/bash

# 本スクリプト名
SCRIPT_NAME="$0"
# tarballの展開先
WORK_DIR=/tmp
# 検索用マーカの次行（行番号）
EMBEDDED_START=""

# 検索用マーカの次行（行番号）を取得
function getEmbeddedLine() {
    # ・__EMBEDDED_MARKER__=検索用のマーカ（tarball開始行の一つ前）
    # ・NR=現在処理しているレコード（行）番号。
    EMBEDDED_START=$(awk '/^__EMBEDDED_MARKER__/ { print NR + 1; exit 0; }' $SCRIPT_NAME)
}

# Shell Scriptに埋め込まれたtarballを展開する。
function extractTarball() {
    # base64コマンドでバイナリをテキストフォーマットにデコード。
    tail -n +${EMBEDDED_START} $SCRIPT_NAME | base64 -d | tar -zpx -C $WORK_DIR
}

# tarball展開後の処理（任意の処理）
function afterExtractTarball() {
    cd ${WORK_DIR}
    ./bin/test.sh
}

getEmbeddedLine
extractTarball
afterExtractTarball
# 明示的に終了する。終了しない場合、後続のtarballまで処理が進んでしまう
exit 0

__EMBEDDED_MARKER__

```

embed.shのextractTarball()内では、tarballの内容をbase64コマンドでデコードしています。デコードする事が重要ではなく、tarballをbase64エンコード（英数字、記号2つ、パディングによる表現）でShell Scriptに埋め込む事が目的です。

以下、base64エンコードでtarballをShell Scriptに埋め込む例です。

```
$ base64 bin.tar.gz >> embed.sh

(注釈) 埋め込み後、 embeded.sh中の__EMBEDDED_MARKER__の次行にテキストが
　　　 来ていなければ調整してください。以下、埋め込み後の状態例です。
__EMBEDDED_MARKER__
H4sIAAAAAAAAA+3SQQqDMBRF0YxdRbDzmtTEbKE76FhbwYIYMHb/JpSCIx2FUnrP5AfyIQ9euudU
icxU5JxNUzurtvNDaKP1pdGmNlqk7TikzR0seYWlnaUUU+t3947uf1QX+1/6sJzDkO2Nw/5r9+7f
OtdYI1Q8ukZIlS3Rxp/3f6rSD+jaMBRFfx+8LK/9OHp58/P4KItvxwMAAAAAAAAAAAAAAACwYwW8
6GfKACgAAA==

```

base64エンコーディングされていない状態、すなわちtarballをShell Scriptにそのまま連結した場合は、Shell Scriptの編集が出来なくなります。正確には、編集後に保存できますが、実行時に以下のエラーが出ます（保存時にtarball部分が意図しない形式に変換され、展開に失敗してしまう）。

```
gzip: stdin: unexpected end of file
tar: Child returned status 1
tar: Error is not recoverable: exiting now

```

また、Shell Scriptを編集していなくても、base64エンコーディングしていない場合はBashがtarballに含まれるNULL文字を省略する可能性があります（"warning: command substitution: ignored null byte in input"がtarball展開時に表示される事があります）。

NULL文字が省略された場合、tarball展開時にチェックサムチェックエラーが発生し、処理が継続できなくなります。

## tarball結合後のShell Script実行例

embed.shは、tarballを/tmp以下に展開後、/tmp/bin/test.shを実行します。test.shは"Hello World"を表示し、終了します。

```
$ ./embed.sh 
Hello World

```

## おまけ：Shell Scriptをバイナリ化する方法

https://debimate.jp/2021/08/29/shc%ef%bc%88shell-script-compiler%ef%bc%89%e3%81%a7%e3%82%b9%e3%82%af%e3%83%aa%e3%83%97%e3%83%88%e3%82%92%e3%83%90%e3%82%a4%e3%83%8a%e3%83%aa%e5%8c%96%ef%bc%88%e6%9a%97%e5%8f%b7%e5%8c%96%ef%bc%89/
