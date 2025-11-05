---
title: "Linux Command Optionの慣習(一般的なOption一覧)"
type: post
date: 2019-02-23
categories:
  - "linux"
tags:
  - "command"
  - "linux"
cover:
  image: images/bash-161382_640.png
  alt: "Linux Command Optionの慣習(一般的なOption一覧)"
  hidden: false
---

## 前書き

本記事は、Linux環境で実行するCommand Optionの慣習について、調査結果を記載します。調査動機は、「Option規格」や「一般的に用いられるOption」を知る事によって、よりよいInterfaceを持つCommandが作成できると考えたからです。特に、Option文字列(例：--version)は、他のCommandに可能な限り一致させた方が、ユーザが混乱しないと考えています。

なお、記事中に"--"という表示がありますが、この表記はハイフンが２個ある記載を意図しています。WordPressの機能によって、"--"が正しく表記されていません。

## Command Line Interface仕様の種類

Command Line Interfaceには、複数の仕様があります。

仕様

- [POSIX](https://ja.wikipedia.org/wiki/POSIX)規格（詳細は後述）
- [GNU](https://ja.wikipedia.org/wiki/GNU)のCoding Style（詳細は後述）
- その他（Command作成者が独自に決めた仕様）

現実的には、POSIX/GNUの仕様を併せ持つCommand Option Parser Library（Option解析ライブラリ）が、各言語向けに存在します。つまり、Commad Optionを解析するコードを自力で書かない限り、GNU/POSIXの仕様に（ある程度）従います。例えば、C言語であれば、getopt()がPOSIX規格の Short Option("-")を解析し、getopt\_long()がPOSIX規格/GNUのOption("-"と"--")を解釈します。これらの関数は、どちらも[Glibc](https://www.gnu.org/software/libc/)が提供する関数で、標準的なLinuxであれば導入されています。

## Command Optionに関するPOSIX規格

[POSIX規格](http://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap12.html)の中から、重要な内容のみを抜粋して記載します。

```
書式
utility_name [-a] [-b] [-c option_argument] [-d|-e] [-f[option_argument]] [operand...]
```

POSIX規格（抜粋）

- Optionは"-"で始め、Option文字列は英数字１文字
- 複数のOptionを使用する場合、"-"を省略して繋げられる (例："-a -b -c"を"-abc"と表記可)
- OptionとOption引数の間は、空白を入れる事
- Optionは、Command引数の前に存在する事
- Optionは、Command実行時に省略できる事

最後の”Optionは、Command実行時に省略できる事”に関しては、私は失敗した事があります。過去に私は、各スクリプト言語ファイルのいずれかを生成し、生成したファイルに実行権・Shebangを付与するCommandを作成しました。当然、スクリプト種類によって、Shebangが変わります。そのため、「Optionが”-r”の場合はruby、"-b"の場合はbash、"-p"の場合はpythonを作成しよう」と考えました。

しかし、Optionを用いない仕様（例："command 生成ファイル名"）とし、スクリプト種類は生成ファイル名の拡張子から判定した方が利便性が高かったです。

## Command Optionに関するGNU Coding Style

[GNU Coding Style](https://www.gnu.org/prep/standards/html_node/Command_002dLine-Interfaces.html)では、POSIX規格に従う事を推奨しています。さらに、GNUではPOSIX規格に以下の仕様を加えています。

追加仕様

- "--"およびOptionのロング名のサポート（例："-v"に対応する"--version"）
- OptionとOption引数が連結した形式のサポート（例：--test=path）
- "--version"(バージョン表示)および"--help"(ヘルプもしくはUsageの表示)を最低限サポートする事

## 一般的なOption一覧

Linuxで頻繁に使用されるCommandは、ある程度同じ意味合いのOptionを持ちます。アルファベットaからzまでのOptionで、期待される動作を下表に示します。この表は参考であり、全く違うOptionを作成しても問題はありません。

| Short Option | Long Option | 機能（オプションを実装しているCommand） |
| --- | --- | --- |
| a | all |   全ファイルや全ユーザなどを対象にした処理（du、nm、uname）   |
| b | bytes、blocks | バイトやブロックのサイズを設定（du、df） |
| c | cmd | サブプロセスに渡すCommandおよびOptionを設定（bash、python） |
| d | debug | debugメッセージを出力（多くのCommand） |
| d | dry-run |   ファイルやシステムに変更を加えずに、処理の検証     |
| d | delete |   引数で指定した対象を削除         |
| e | exclude | 除外対象（例：ファイル）を設定(rync) |
| f | file | 使用するfileを設定（awk、make、sed、tar） |
| g | group | グループを設定（install） |
| h | help | Commandを使用する上でのhelpを表示（多くのCommand） |
| i | inodes |   ブロック使用量の代わりに iノード情報を表示(ls、df)   inodes以外に、interactiveも存在（rm、mv）   |
| j | jobs | ジョブの数を設定（make） |
| k | keep | ファイル・メッセージ・リソースなどの削除を抑制（passwd、bzip） |
| l | list | ファイル・ディレクトリなどのリストを表示（unzip、ls） |
| m | mode | 権限の設定（install、mkdir） |
| n | number | 番号（例：行番号）を表示(head、tail、grep) |
| o | output | 出力ファイル名や出力ファイルパスの設定（多くのCommand） |
| p | 多種多様 | [参考文献](https://www.gnu.org/prep/standards/html_node/Option-Table.html#Option-Table)を参照 |
| q | quiet | メッセージの出力を抑制（多くのCommand） |
| r | recursive | 再帰的に処理を実行（grep、chgrp、choen、cp、ls、diff、rm） |
| s | silent | メッセージの出力を抑制（多くのCommand） |
| t | 多種多様 | [参考文献](https://www.gnu.org/prep/standards/html_node/Option-Table.html#Option-Table)を参照 |
| u | update | アップデートを実行（apt、yum、cp、mv、tar） |
| v | version | プログラムのVersion情報を表示（多くのCommand） |
| v | verbose |   詳細にメッセージを表示     |
| w | width | 幅の設定（ls、ptx） |
| x | extract | アーカイブなどから抽出するファイル一覧を表示（tar、zip） |
| y | yes | ユーザ確認する処理において、全確認項目に対してユーザがyesと回答したとみなす（apt、yum） |
| z | zip(compress) | 圧縮を有効化（tar） |

## 参考

[The Art of Unix Programming: Command-Line Options](http://www.catb.org/esr/writings/taoup/html/ch10s05.html)

[GNU Coding Standards: Table of Long Options](https://www.gnu.org/prep/standards/html_node/Option-Table.html#Option-Table)
