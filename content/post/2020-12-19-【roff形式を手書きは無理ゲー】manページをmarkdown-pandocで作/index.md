---
title: "【roff形式を手書きは無理ゲー】manページをMarkdown + Pandocで作成【with manページお作法】"
type: post
date: 2020-12-19
categories:
  - "linux"
tags:
  - "debian"
  - "linux"
  - "man"
cover:
  image: "images/books-1845614_640-min.jpg"
  alt: "【roff形式を手書きは無理ゲー】manページをMarkdown + Pandocで作成【with manページお作法】"
  hidden: false
---

## 前書き：manualページは伝統的なドキュメント

manページは、UNIX系OSのドキュメントであり、コマンドやシステムコールなどの説明が記載されています。

Unix v7の時代（1979年）から変化が少ないため、2020年現在の視点で見ると表現力に難があります。具体的には以下のような欠点があり、manページを良質なドキュメントとするには文章力を試されます。

- 画像を挿入できない
- ハイパーリンク非対応
- Terminalからしか参照できない（manページをHTMLに変換して公開しているサイトはあります）

勿論、manページより表現力が高い[Texinfo](https://ja.wikipedia.org/wiki/Texinfo)、[Docbook](https://ja.wikipedia.org/wiki/DocBook)などの代替ドキュメントフォーマットもあります。

しかし、個人的にはシステムコールやコマンドの詳細を調べる時は、manページを参照する事が多いです。そのため、manページを作成する機会が少なからずありますが、人間が書くにはmanページ（roff形式の文書）の書式は辛いものがあります。

roffの書式は、以下の例のように、パッと見で「学習コスト高そうだな」と感じてしまいます。

```
.TH "SERIAL" "1" "2020年11月" "" ""
.hy
.SH 名前
.PP
serial \[en] シリアル番号付きのファイル名にリネームする。
.SH 書式
.PP
\f[B]serial\f[] OPTIONS DIRECTORY_PATH
.SH 説明
.PP
\f[B]serial\f[]は、任意のディレクトリ以下にあるファイルの名前をユーザ指定の名前に連番を付与してリネームするCLIコマンドです。serialは、リネームしたファイルの格納先ディレクトリを指定できます。また、オリジナルファイルを保持したい場合、リネームではなくファイルコピーができます。
.SH 例
.PP
\f[B]カレントディレクトリにあるファイルの名前をシリアル番号付きのファイル名にリネームする。\f[]
.IP
.nf
```

そこで、本記事ではPandocを用いてMarkdown（人が読み書きしやすい形式）からmanページを生成する方法を説明します。また、「manページの基本的な説明」および「manページに記載する内容」も合わせて説明します。

本記事で説明する内容

- Pandocのインストール
- Markdownをmanページに変換する方法
- manページ命名規則とセクション番号
- manページに記載する内容
- Markdownの記載例
- manページの置き場

## 検証環境

```
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 10 (buster) x86_64 
 ,$$P'              `$$$.     Kernel: 4.19.67 
',$$P       ,ggs.     `$$b:   Uptime: 2 hours, 42 mins 
`d$$'     ,$P"'   .    $$$    Packages: 4053 (dpkg), 13 (flatpak), 6 (snap) 
 $$P      d$'     ,    $$P    Shell: fish 3.0.2 
 $$:      $$.   - ,d$$'    Resolution: 2560x1080 
 $$;      Y$b._   _,d$P'      DE: Pantheon 
 Y$$.    `.`"Y$$$$P"'         WM: Mutter(Gala) 
 `$$b      "-.__              Terminal: io.elementary.t 
  `Y$$                        CPU: AMD Ryzen 7 3800X 8- (16) @ 3.900GHz 
   `Y$$.                      GPU: NVIDIA NVIDIA Corporation TU107 
     `$$b.                    Memory: 5949MiB / 64404MiB 
       `Y$$b.
          `"Y$b._                                     

```

## Pandocのインストール

[Pandoc](https://pandoc.org/)は、ドキュメント変換ツール（Python製）です。

Markdownをmanページに変換するだけであれば、[Ronn](https://rtomayko.github.io/ronn/)（ruby製）もあります。しかし、Pandocは多種多様なフォーマット変換に対応しています。また、Pandocの方がRonnよりも活発に開発を続けています。この2点が、Pandocを選んだ理由です。

Debian環境では、aptパッケージマネージャでPandocをインストールできます。

```
$ sudo apt install pandoc 

```

## Markdownをmanページに変換する方法

Markdownをmanページに変換する場合は、-sオプションでヘッダ／フッタの付与、-tオプションで変換フォーマットを指定します。

```
$ pandoc markdown.md -s -t man > man.1

```

## manページ命名規則とセクション番号

manページの命名規則は、以下の通りです。拡張子が1〜8の数字（セクション番号）となります。

```
[manページの命名規則]
　<ドキュメント名>.<セクション番号>

```

| **項目** | **役割** |
| --- | --- |
| ドキュメント名 | manページの内容を端的に示す名前（例：systemd）   ユーザは、ドキュメント名をもとにmanページを参照します（例：$ man systemd） |
| セクション番号 | manページの内容に従い、割り当てられた1〜8の番号。   それぞれの番号の意味合いは下表を参照。 |

| **セクション番号** | **説明する内容** |
| --- | --- |
| 1 | 一般的なコマンド |
| 2 | システムコール（Linux Kernelが提供するAPI、もしくはそのラッパーAPI） |
| 3 | ライブラリAPI |
| 4 | 特殊ファイル（例：/dev以下のファイル） |
| 5 | 各種ファイルフォーマットとその規則 |
| 6 | ゲーム |
| 7 | その他（慣習、約束事、プロトコル説明など） |
| 8 | システム管理コマンド、デーモン |

基本的に、manページはgz形式／bz2形式など圧縮されています。

例えば、serialコマンドのmanページをgz形式で圧縮する場合は、manページ名が"serial.1.gz"になります。serial.1.gzの生成手順例は、以下の通りです。

1. Markdown(serial.1.md)をmanページに変換（$ pandoc serial.1.md -s -t man > serial.1）
2. manページをgz形式で圧縮（$ gzip -f serial.1）

## manページに記載する内容

manページには、標準の書式（セクション）が存在します。

頻繁に登場するセクションを下表に示します。全てのセクションを記載する必要はないため、他のmanページの内容を参考にしながら、記載すべき内容を吟味してください。

| **セクション名** | **説明する内容** |
| --- | --- |
| NAME | コマンド名、コマンド使用目的、ドキュメント概要など |
| SYNOPSIS | コマンドオプション／引数リスト、API引数、ヘッダファイル情報 |
| DESCRIPTION | コマンドや関数の役割／動作に関する説明 |
| EXAMPLE | 使用方法の例 |
| OPTIONS | コマンドオプション一覧 |
| ENVIRONMENT | 環境変数の一覧 |
| EXIT STATUS | 終了ステータス一覧 |
| FILES | コマンド／API／デーモンなどに関連するファイル |
| BUGS | 既知のバグ |
| WARNINGS | 警告したい事柄 |
| NOTES | メモ（関連ドキュメントへのURLなど） |
| SEE ALSO | 他に参照すべき資料やmanページの情報 |
| AUTHOR | 著者名 |
| HISTORY | 開発に関する歴史的な経緯の説明 |
| COPYRIGHT | コピーライト情報 |
| LICENSE | ライセンス情報 |

表に存在しないセクションは多数存在しますし、独自のセクションを作成しても問題はありません。ただし、なるべく慣習に合わせて作成した方が読者の負荷が減ります。

## Markdownの記載例

例として、私が以前作成した[serialコマンド](https://github.com/nao1215/serial)のmanページ用Markdownを以下に示します。

1〜3行目は"%"記号で始まり、記載内容する内容が決まっています。

- 1行目：ヘッダに表示する内容とセクション番号
- 2行目：著者情報（フッタにAUTHORセクションとして表示されます）
- 3行目：フッタに表示する年月日（更新日付）

残りの部分は、[Markdownの文法](https://web-cheatsheet.com/markdown)に従って記載してください（セクション開始の"#"記号、\*\*強調\*\*、インデントの”:"記号が分かれば、ある程度作成できると思います）

```
% SERIAL(1)
% Naohiro CHIKAMATSU <n.chika156@gmail.com>
% November 2020

# NAME

serial – rename the file name to the name with a serial number.

# SYNOPSIS

**serial** [OPTIONS] DIRECTORY_PATH

# DESCRIPTION
**serial** is a CLI command that renames files under any directory to 
the format user specified file name with serial number.
serial can specify the destination directory of the renamed file. Also, 
if you want to keep the original file, you can copy the file instead of 
renaming the file.

# EXAMPLES
**Rename the file name to the name with a serial number at current directory.**

    $ ls
      a.txt  b.txt  c.txt
    $ serial --name demo  .
      Rename a.txt to demo_1.txt
      Rename b.txt to demo_2.txt
      Rename c.txt to demo_3.txt

**Copy & Rename the file at specified directory.**

    $ serial -p -k -n ../../dir/demo .
      Copy a.txt to ../../dir/0_demo.txt
      Copy b.txt to ../../dir/1_demo.txt
      Copy c.txt to ../../dir/2_demo.txt

# OPTIONS
**-d**, **--dry-run**
:   Output the file renaming result to standard output (do not update the file).

**-f**, **--force**
:   Forcibly overwrite and save even if a file with the same name exists.

**-h**, **--help**
:   Show help message.

**-k**, **--keep**
:   Keep the file before renaming (not rename, do copy).

**-n new_filename**, **--name=new_filename**
:   Base file name with/without directory path (assign a serial number to this file name).

**-p**, **--prefix**
:   Add a serial number to the beginning of the file name.

**-s**, **--suffix**
:   Add a serial number to the end of the file name(default).

**-v**, **--version**
:   Show serial command version.

# EXIT VALUES
**0**
:   Success

**1**
:   There is an error in the argument of the serial command.

# BUGS
See GitHub Issues: https://github.com/nao1215/serial/issues

# LICENSE
serial command project is licensed under the terms of the MIT license.

```

## manページの置き場

manページの置き場（格納先）は、/etc/man.configもしくは/etc/manpath.configの変数MANDATORY\_MANPATHに記載されています。

私の環境では、以下のディレクトリにmanページ格納先対象でした。

- /usr/man
- /usr/share/man　　※ 実際はココにしか入っていませんでした
- /usr/local/share/man

上記のディレクトリを確認すると、ja=日本語、en=英語、……、のように言語毎にディレクトリが細分化されている事が分かります。適切な場所に格納しましょう。

```
$ ls /usr/share/man
ca  de  eo  fi  hu  ja    man2  man5  man8  pl     ro  sl  tr  zh_CHS
cs  el  es  fr  id  ko    man3  man6  nb    pt     ru  sr  uk  zh_CN
da  en  et  hr  it  man1  man4  man7  nl    pt_BR  sk  sv  vi  zh_TW

```
