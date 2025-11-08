---
title: "【Bash / Ruby / Python3】ファイル一覧の取得方法、ファイル数の確認方法の比較"
type: post
date: 2020-04-09
categories:
  - "linux"
tags:
  - "bash"
  - "linux"
  - "python"
  - "ruby"
  - "shellscript"
cover:
  image: "images/documents-1920461_640-min.jpg"
  alt: "【Bash / Ruby / Python3】ファイル一覧の取得方法、ファイル数の確認方法の比較"
  hidden: false
---

## 前書き

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、「ファイル一覧の取得方法」および「ファイル数の確認方法」を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

- [Bash(Shell Script)からRubyやPythonに乗り換え！頻繁に使う処理を各言語で比較](https://debimate.jp/post/2020-04-05-bashshell-script%E3%81%8B%E3%82%89ruby%E3%82%84python%E3%81%AB%E4%B9%97%E3%82%8A%E6%8F%9B%E3%81%88%E9%A0%BB%E7%B9%81%E3%81%AB%E4%BD%BF%E3%81%86%E5%87%A6%E7%90%86%E3%82%92%E5%90%84%E8%A8%80/)


## 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

## 比較：「ファイル一覧の取得方法」および「ファイル数の確認方法」

自動化Scriptでは、処理対象のファイル一覧を取得してから何らかの処理を逐次実行したり、進捗を示すためにファイル総数と処理済みファイル数を比べる機会が多いです。

以下に、各言語の実装例および実行例を示します。

**Bashの場合**

```
#!/bin/bash

# カレントディレクトリに存在するファイルを出力。
# 正確にはディレクトリも含まれる。
CWD=$(pwd)
echo "${CWD}以下のファイル一覧を出力"
for file_path in ${CWD}/*; do
    # basenameコマンドでPATHを削除する。
    echo "    $(basename ${file_path})"
done

# カレントディレクトリ以下のファイル数を算出
# findコマンドでファイル（ディレクトリを含まない）を検索し、
# wcコマンド -lで行数(=ファイル数)をカウントする。
FILE_NR=$(find . -type f | wc -l)
echo "ファイル数：${FILE_NR}"
```

**Rubyの場合**

```
#!/usr/bin/env ruby

# カレントディレクトリに存在するファイルを出力。
# 正確にはディレクトリも含まれる。
cwd = __dir__
printf(cwd + "以下のファイル一覧を出力\n")
# glob()の'*'は、カレントディレクトリ以下の
# 任意文字列を検索でヒットさせるための引数。
Dir.glob('*') do |item|
  puts("    " + item)
end

# カレントディレクトリ以下のファイル数を算出
count = 0
Dir.glob('*') do |item|
  if FileTest.file?(item)
    count += 1
  end
  # ファイル・ディレクトリの総数を知りたい場合は、
  # Dir.glob('*').count()で取得できる。
end
puts("ファイル数：" + count.to_s)

```

**Python3の場合**

```
#!/usr/bin/env python3

import os

# カレントディレクトリに存在するファイルを出力。
# 正確にはディレクトリも含まれる。
cwd= os.getcwd()  
print(cwd + "以下のファイル一覧を出力")
for f in os.listdir(cwd):
    print("    "  + f)

# カレントディレクトリ以下のファイル数を算出
count = 0
for f in os.listdir(cwd):
    if os.path.isfile(os.path.join(f)):
        count += 1
        # ファイル・ディレクトリの総数を知りたい場合は、
        # len(os.listdir(cwd))で取得できる
print("ファイル数：" + str(count))

```

**Bash、Ruby、Python3の実行例**

```
$ ls -l　　　(注釈)：カレントディレクトリ以下のファイル確認
合計 16
-rwxr-xr-x 1 nao nao  619  4月  9 14:14 bash.sh
drwxr-xr-x 2 nao nao 4096  4月  9 13:44 directory  (注釈)：コレだけディレクトリ
-rwxr-xr-x 1 nao nao  609  4月  9 14:14 python.py
-rwxr-xr-x 1 nao nao  701  4月  9 14:14 ruby.rb

$ ./bash.sh 
/home/nao/scripts以下のファイル一覧を出力
    bash.sh
    directory
    python.py
    ruby.rb
ファイル数：3

$ ./ruby.rb 
/home/nao/scripts以下のファイル一覧を出力
    python.py
    directory
    bash.sh
    ruby.rb
ファイル数：3

$ ./python.py 
/home/nao/scripts以下のファイル一覧を出力
    python.py
    directory
    bash.sh
    ruby.rb
ファイル数：3

```
