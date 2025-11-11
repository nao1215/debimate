---
title: "【Bash / Ruby / Python3】外部コマンドを実行する方法の比較"
type: post
date: 2020-04-12
categories:
  - "linux"
tags:
  - "bash"
  - "linux"
  - "python"
  - "ruby"
  - "shellscript"
cover:
  image: "images/ubuntu-3145957_640-min.jpg"
  alt: "【Bash / Ruby / Python3】外部コマンドを実行する方法の比較"
  hidden: false
---

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、外部コマンド（例：/bin以下のコマンド）を実行する方法を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

- [Bash(Shell Script)からRubyやPythonに乗り換え！頻繁に使う処理を各言語で比較](https://debimate.jp/post/2020-04-05-bashshell-script%E3%81%8B%E3%82%89ruby%E3%82%84python%E3%81%AB%E4%B9%97%E3%82%8A%E6%8F%9B%E3%81%88%E9%A0%BB%E7%B9%81%E3%81%AB%E4%BD%BF%E3%81%86%E5%87%A6%E7%90%86%E3%82%92%E5%90%84%E8%A8%80/)

### 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

### 比較：外部コマンドを実行する方法

Bashは、Bashビルトインコマンド（例：cd）だけでなく、外部コマンドを使用して処理を実行します。同様に、RubyやPython3も、外部コマンドを使用したい場面が稀に出てきます。

例えば、外部コマンドと同等の処理を新規実装しなければ実現できない時です。このような場合は、実装せずに外部コマンドを使用した方が楽です。

以下に、各言語の実装方法と実行例を示します。

**Bashの場合**

```
#!/bin/bash

SCRIPT_NAME=$(basename $0)

# カレントディレクトリに存在するファイルを木構造で表示
# -Lオプション：どの深さまでディレクトリを表示するかの指定。
echo "treeコマンドを実行します。"
tree -L 1

# treeコマンドの結果から、自身(bash.sh)を探す。
echo "---"
echo "treeコマンド結果から、${SCRIPT_NAME}を探します。"
tree -L 1 | grep "${SCRIPT_NAME}"
```

**Rubyの場合**

```
#!/usr/bin/env ruby

require 'open3'

script_name = File.basename(__FILE__)

# カレントディレクトリに存在するファイルを木構造で表示
# Open3モジュールに引数としてコマンドを渡すと、
# 標準出力、標準エラー、ステータスが返される。
stdout, stderr, status = Open3.capture3("tree -L 1")
puts(stdout)

# treeコマンドの結果から、自身(ruby.rb)を探す。
puts("---")
puts("treeコマンド結果から、%sを探します。" % script_name)
cmd = "tree -L 1 | grep " + script_name
stdout, stderr, status = Open3.capture3(cmd)
puts(stdout)

```

**Python3の場合**

```
#!/usr/bin/env python3

import os
import subprocess

script_name = os.path.basename(__file__)

# 同期実行の例
# カレントディレクトリに存在するファイルを木構造で表示する。
# subprocessモジュールを利用して実行する。
# 第一引数にコマンド名
print("treeコマンドを実行します。")
result = subprocess.run(["tree","-L","1"])

# treeコマンドの結果から、自身(python.py)を探す。
print("---")
print("treeコマンド結果から、%sを探します。" % script_name)

# 非同期実行の例
# treeコマンドとgrepコマンドをパイプでつなぐ。
# subprocessのshellがTrueの場合、コマンドをリスト形式ではなく、文字列として渡せる。
# 適切に設計しなければシェルインジェクションを引き起こす可能性がある。
#
# stdout, stderrへのPIPE指定によって、communicate()が外部コマンドの標準入力、
# 標準エラーを返す。PIPE指定なしの場合は、communicate()がNoneを返す。
cmd           = "tree -L 1 | grep " + script_name
result        = subprocess.Popen(cmd, shell=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
# communicate()で処理の結果待ちを行う。
stdout,strerr = result.communicate()
print(stdout.decode('utf-8'))  # decode処理を行わないとバイトとして扱われる。

```

**Bash、Ruby、Python3の実行例**

```
$ ./bash.sh 
treeコマンドを実行します。
.
├── bash.sh
├── python.py
└── ruby.rb

0 directories, 3 files
---
treeコマンド結果から、bash.shを探します。
├── bash.sh

$ ./ruby.rb 
.
├── bash.sh
├── python.py
└── ruby.rb

0 directories, 3 files
---
treeコマンド結果から、ruby.rbを探します。
└── ruby.rb

$ ./python.py 
treeコマンドを実行します。
.
├── bash.sh
├── python.py
└── ruby.rb

0 directories, 3 files
---
treeコマンド結果から、python.pyを探します。
├── python.py

```
