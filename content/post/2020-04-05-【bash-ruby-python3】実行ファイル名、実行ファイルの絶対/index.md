---
title: "【Bash / Ruby / Python3】実行ファイル名、実行ファイルの絶対 / 相対PATHを取得する方法の比較"
type: post
date: 2020-04-05
categories:
  - "linux"
tags:
  - "bash"
  - "linux"
  - "python"
  - "ruby"
  - "shellscript"
cover:
  image: "images/shield-490811_640-min.jpg"
  alt: "【Bash / Ruby / Python3】実行ファイル名、実行ファイルの絶対 / 相対PATHを取得する方法の比較"
  hidden: false
---

## 前書き

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、実行ファイル名の取得方法、実行ファイルの絶対 / 相対PATH取得方法を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

- [Bash(Shell Script)からRubyやPythonに乗り換え！頻繁に使う処理を各言語で比較](https://debimate.jp/post/2020-04-05-bashshell-script%E3%81%8B%E3%82%89ruby%E3%82%84python%E3%81%AB%E4%B9%97%E3%82%8A%E6%8F%9B%E3%81%88%E9%A0%BB%E7%B9%81%E3%81%AB%E4%BD%BF%E3%81%86%E5%87%A6%E7%90%86%E3%82%92%E5%90%84%E8%A8%80/)

## 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

\[the\_ad id="598"\]

## 比較：実行ファイル名 / 実行ファイルの絶対・相対PATHの取得

実行ファイル名は、Usage（使い方）を表示するために取得する機会が多いです。実行ファイルのPATHは、そのPATH起点でディレクトリ移動やファイル操作する際などに用います。

以下に、各言語の実装方法および実行例を示します。

**Bashの場合**

```
#!/bin/bash

# ファイル名(PATHなし)の取得
echo "$(basename $0)"

# 絶対PATHでの取得
# ① 実行スクリプトの存在するPATHを取得(dirname部分)
# ② スクリプトが存在するディレクトリへ移動
# ③ pwdコマンドでスクリプトが存在するディレクトリのPATHを取得
# ④ スクリプト名("/$(basename $0)"部分)を連結
echo "$(cd $(dirname $0) && pwd)/$(basename $0)"

# 相対PATHでの取得
echo "$0"
```

**Rubyの場合**

```
#!/usr/bin/env ruby

# ファイル名(PATHなし)の取得
p(File.basename(__FILE__))

# 絶対PATHでの取得
p(File.expand_path(__FILE__))

# 相対PATHでの取得
p(__FILE__)
```

**Pythonの場合**

```
#!/usr/bin/env python3
import os

# ファイル名(PATHなし)の取得
print(os.path.basename(__file__))

# 絶対PATHでの取得
print(os.path.abspath(__file__))

# 相対PATHでの取得
print(__file__)
```

**Bash、Ruby、Python3の実行例**

```
$ ./bash.sh
bash.sh
/home/nao/scripts/bash.sh
./bash.sh

$ ./ruby.rb
"ruby.rb"
"/home/nao/scripts/ruby.rb"
"./ruby.rb"

$ ./python.py
python.py
/home/nao/scripts/python.py
./python.py

```
