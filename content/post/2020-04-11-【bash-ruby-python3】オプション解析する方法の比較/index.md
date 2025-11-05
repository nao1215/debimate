---
title: "【Bash / Ruby / Python3】オプション解析する方法の比較"
type: post
date: 2020-04-11
categories:
  - "linux"
tags:
  - "bash"
  - "linux"
  - "python"
  - "ruby"
  - "shellscript"
cover:
  image: "images/settings-3311593_640.png"
  alt: "【Bash / Ruby / Python3】オプション解析する方法の比較"
  hidden: false
---

## 前書き

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、オプション解析する方法を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

https://debimate.jp/2020/04/05/bashshell-script%e3%81%8b%e3%82%89ruby%e3%82%84python%e3%81%ab%e4%b9%97%e3%82%8a%e6%8f%9b%e3%81%88%ef%bc%81%e9%a0%bb%e7%b9%81%e3%81%ab%e4%bd%bf%e3%81%86%e5%87%a6%e7%90%86%e3%82%92%e5%90%84%e8%a8%80/

## 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

## 比較：オプション解析する方法

自動化Scriptでは、他のコマンドと同様に、オプションに応じて処理を変更する実装にする機会が多いです。例えば、ログ出力先をユーザがオプションで指定したディレクトリに変更したり、ログレベルを柔軟に変更したりする場合などが、オプションが必要な例として挙げられます。

以下に、各言語の実装例および実行例を示します。

**Bashの場合**

Bashのオプション解析には、getopts（bashビルトインコマンド）を用いた方法、getoptコマンド（外部コマンド）を用いた方法の二通りがあります。

getoptsによるオプション解析 と異なり、getoptはロングオプションも使用出来るメリットがあります。 ただし、デメリットとして、getoptはBSD実装(Mac、OpenBSD等)とGNU実装(Debian系、RedHas系)で差異があります。

BSD実装の場合はロングオプションが使用できず、引数の後にオプションを指定できないデメリットがあります。今回の例では、Linux環境を前提としているのでgetoptを使用した方法を示します。getoptsを使用した方法は、番外として、本記事の最後に示します。

```
#!/bin/bash

# getoptコマンドを用いたオプション解析
# getopts（bashビルトインコマンド）と異なり、getoptはロングオプションも使用可能。
# ただし、getoptはBSD実装(Mac、OpenBSD等)／GNU実装(Debian系、RedHas系)で差異があり、
# BSD実装の場合はロングオプション使用不可、引数の後にオプション指定不可。

# -oオプション：ショートオプションとする英字を指定する。
#               今回の例では、"-h"、-m"をオプションとしている。
#               英字の後に":"を書いた場合は、その英字はオプション引数を必要とする。
# -lオプション：ロングオプションとする英文字列を指定する。
#               オプション引数が必要な場合、英文字列の後に":"を指定する。
# -nオプション：エラーメッセージに出力するスクリプト名
#               指定がない場合は、"getopt:〜"という形式でエラー出力される。
# --オプション："--"の後にパラメータが続く必要がある。
# $@          ：Shell Scriptに渡された全ての引数
OPT=$(getopt -o hm: -l help,message: -n $0 -- "$@")
if [ $? != 0 ] ; then
    exit 1
fi
eval set -- "$OPT"

while true
do
    # 引数を解析した後、必ずshiftで引数をずらす必要がある。
    case $1 in
        -h | --help)
            echo "helpメッセージのつもり"
            shift
            ;;
        -m | --message)
            echo "messageオプションの処理（オプション引数：$2）"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "不正なオプションです。" 1>&2
            exit 1
            ;;
    esac
done

```

**Rubyの場合**

```
#!/usr/bin/env ruby

require 'optparse'

option = {}
OptionParser.new do |opt|
  # opt.on()にオプションを指定する。
  # オプション引数なしの場合、第一引数はオプション名(例:-z)を指定する。
  # オプション引数ありの場合、第一引数はオプション名と変数名(例：-l var)を指定する。
  # 省略可能なオプション引数ありの場合、変数名を[]で囲む。
  # {}部分は、オプション指定時の処理。今回は、hashに変数を保持している。
  opt.on('-m', '--message MSG', '出力するメッセージを指定する') {|m| option[:message] = m}

  begin
    # parse!()は、実行時に登録していない引数を指定された場合や、
    # 必須のオプション引数がなかった場合に例外を出す。
    # 例外発生時は、helpメッセージを手動で表示する。
    opt.parse!(ARGV)
  rescue => exception
    puts(opt)
    exit 1
  end
end

puts("messageオプションの処理（オプション引数：" + option[:message] + ")")

```

**Python3の場合**

```
#!/usr/bin/env python3

import argparse

# argparseモジュールは、自動でhelpオプションを作成する。

# add_argument()は、一度に２種類の記法(例："-v"、"--version")を登録できる。
# typeにはオプション引数の型、destにはオプション引数(値)の格納先となる変数名を書く。
# 引数helpには、オプションの意味合い(ヘルプ時に表示する文章)を記載する。
parser = argparse.ArgumentParser()
parser.add_argument("-m","--message", type=str, dest="msg",
                    help="出力するメッセージを指定する")
args = parser.parse_args()

if args.msg is not None:
    print("messageオプションの処理（オプション引数：%s)" % args.msg)

```

**Bash、Ruby、Python3の実行例**

Rubyは、ユーザが誤ったオプションの使い方をした場合に備えて、例外処理を作り込まないと「何が原因でエラーが発生したか」が分かりづらい印象を受けました。

```
$ ./bash.sh -h
helpメッセージのつもり
$ ./bash.sh --help
helpメッセージのつもり
$ ./bash.sh -m test_message
messageオプションの処理（オプション引数：test_message）
$ ./bash.sh -m
./bash.sh: オプションには引数が必要です -- 'm'
$ ./bash.sh --message test_message
messageオプションの処理（オプション引数：test_message）
$ ./bash.sh -a
./bash.sh: 無効なオプション -- 'a'

$ ./ruby.rb -h
Usage: ruby [options]
    -m, --message message            出力するメッセージを指定する
$ ./ruby.rb --help
Usage: ruby [options]
    -m, --message message            出力するメッセージを指定する
$ ./ruby.rb -m test_message
messageオプションの処理（オプション引数：test_message)
$ ./ruby.rb -m
Usage: ruby [options]
    -m, --message message            出力するメッセージを指定する
$ ./ruby.rb --message test_message
messageオプションの処理（オプション引数：test_message)
$ ./ruby.rb -a	
Usage: ruby [options]
    -m, --message message            出力するメッセージを指定する

$ ./python.py -h
usage: python.py [-h] [-m MSG]

optional arguments:
  -h, --help            show this help message and exit
  -m MSG, --message MSG
                        出力するメッセージ
$ ./python.py --help
usage: python.py [-h] [-m MSG]

optional arguments:
  -h, --help            show this help message and exit
  -m MSG, --message MSG
                        出力するメッセージ
$ ./python.py -m test_message
messageオプションの処理（オプション引数：test_message)
$ ./python.py -m
usage: python.py [-h] [-m MSG]
python.py: error: argument -m/--message: expected one argument
$ ./python.py --message test_message
messageオプションの処理（オプション引数：test_message)
$ ./python.py -a
usage: python.py [-h] [-m MSG]
python.py: error: unrecognized arguments: -a

```

\[the\_ad id="598"\]

## 番外：Bashでgetoptsを用いたオプション解析

**実装**

```
#!/bin/bash

# getoptsには、引数にオプションとする英字を渡す。
# そのオプション(例："d")がオプション引数を取る場合は、英字の直後に":"を書く(例："d:")。
# 以下の例では、"d"と"f"が引数を必要とするオプション。
while getopts d:f:h OPT
do
    case $OPT in
        d)  DIR_NAME=$OPTARG   # オプション引数は変数OPTARGに格納されている。
            ;;
        f)  FILE_NAME=$OPTARG
            ;;
        h)  echo "スクリプトの使い方はxxxです。"
            exit 0
            ;;
        *) echo "スクリプトの使い方はxxxです。"  # 指定していないオプションが来た場合
            exit 1
            ;;
    esac
done

echo "ディレクトリ名：${DIR_NAME}"
echo "ファイル名：${FILE_NAME}"
```

**実行例**

```
$ bash sample.sh -f file_name -d directory_name
ディレクトリ名：directory_name
ファイル名：file_name

$ bash sample.sh -f 
sample.sh: オプションには引数が必要です -- f
スクリプトの使い方はxxxです。

$ bash sample.sh -k
sample.sh: 不正なオプションです -- k
スクリプトの使い方はxxxです。
```
