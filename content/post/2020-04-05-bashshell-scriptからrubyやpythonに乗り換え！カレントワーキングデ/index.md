---
title: "【Bash / Ruby / Python3】カレントワーキングディレクトリを取得する方法の比較"
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
  image: images/the-location-of-the-1724293_640.jpg
  alt: "【Bash / Ruby / Python3】カレントワーキングディレクトリを取得する方法の比較"
  hidden: false
---

## 前書き 

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、カレントワーキングディレクトリの取得方法を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

https://debimate.jp/2020/04/05/bashshell-script%e3%81%8b%e3%82%89ruby%e3%82%84python%e3%81%ab%e4%b9%97%e3%82%8a%e6%8f%9b%e3%81%88%ef%bc%81%e9%a0%bb%e7%b9%81%e3%81%ab%e4%bd%bf%e3%81%86%e5%87%a6%e7%90%86%e3%82%92%e5%90%84%e8%a8%80/

## 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

## 比較：カレントワーキングディレクトリの取得

カレントワーキングディレクトリ（CWD）のPATHは、他のディレクトリに移動した後にScript実行時点のディレクトリへ戻る際に必要となります。そのため、ディレクトリ移動の前に、取得する機会が多いです。

ディレクトリの移動例と合わせて、以下に実装方法と実行例を示します。

**Bashの場合**

```
#!/bin/bash

# カレントワーキングディレクトリの取得
CWD="$(pwd)"      # pwd(Print Working Dirctory)コマンドで取得
echo "${CWD}"

# 一つ上のディレクトリ階層へ移動
cd ..
# 現在のディレクトリを出力
echo "$(pwd)"

# スクリプト実行時点のディレクトリへ復帰
cd "${CWD}"
echo "$(pwd)"
```

**Rubyの場合**

```
#!/usr/bin/env ruby

# カレントワーキングディレクトリの取得
cwd = __dir__
p(cwd)

# 一つ上のディレクトリ階層へ移動
Dir::chdir("..")
# 現在のディレクトリを出力
p(Dir::pwd())   # CWDは、この書き方でも取得可能

# スクリプト実行時点のディレクトリへ復帰
Dir::chdir(cwd)
p(Dir::pwd())

```

**Python3の場合**

```
#!/usr/bin/env python3
import os

# カレントワーキングディレクトリの取得
cwd = os.getcwd()
print(cwd)

# 一つ上のディレクトリ階層へ移動
os.chdir("..")
# 現在のディレクトリを出力
print(os.getcwd())

# スクリプト実行時点のディレクトリへ復帰
os.chdir(cwd)
print(os.getcwd())

```

**Bash、Ruby、Python3の実行例**

```
$ ./bash.sh
/home/nao/scripts
/home/nao
/home/nao/scripts

$ ./ruby.rb
"/home/nao/scripts"
"/home/nao"
"/home/nao/scripts"

$ ./python.py
/home/nao/scripts
/home/nao
/home/nao/scripts

```
