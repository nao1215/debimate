---
title: "【Bash / Ruby / Python3】ファイル読み込み、ファイル書き込みの方法を比較"
type: post
date: 2020-04-08
categories:
  - "linux"
tags:
  - "bash"
  - "linux"
  - "python"
  - "ruby"
  - "shellscript"
cover:
  image: "images/document-3503099_640-min.jpg"
  alt: "【Bash / Ruby / Python3】ファイル読み込み、ファイル書き込みの方法を比較"
  hidden: false
---

### 前書き

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、「ファイルの読み込み方法」および「ファイルの書き込み方法」を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

- [Bash(Shell Script)からRubyやPythonに乗り換え！頻繁に使う処理を各言語で比較](https://debimate.jp/post/2020-04-05-bashshell-script%E3%81%8B%E3%82%89ruby%E3%82%84python%E3%81%AB%E4%B9%97%E3%82%8A%E6%8F%9B%E3%81%88%E9%A0%BB%E7%B9%81%E3%81%AB%E4%BD%BF%E3%81%86%E5%87%A6%E7%90%86%E3%82%92%E5%90%84%E8%A8%80/)

---



### 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

---


### 比較：ファイルの読み込み・書き込み

自動化スクリプトでは、ファイルの内容を読み込んで一行ずつ処理したり、別ファイルに情報を書き込む機会が多いです。

以下に、各言語の実装例および実行例を示します。

**Bashの場合**

```
#!/bin/bash

# ファイル読み込み：text.txtの内容を一行ずつ表示する。
while read line; do
    # 一行ずつ処理する。
    echo "${line}"
done < text.txt

# ファイル書き込み
echo "bash.shで追加した文章" >> text.txt

```

**Rubyの場合**

```
#!/usr/bin/env ruby

# text.txtの内容を一行ずつ表示する。
# 第二引数は、モード指定（以下、指定の一覧）
# r ：Read Only
# r+：Read + Write (ファイルの読み書き位置は先頭)
# w ：Write Only (ファイルが無ければ新規作成)
# w+：Read + Write (ファイルが無ければ新規作成。有る場合は空にする）
# a ：Append (追記)
# a+：Append + Read (読み込みはファイル先頭から、書き込みはファイル末尾から)
File.open("text.txt", "r") do |f|
  f.each_line do |line|
    # 一行ずつ処理する。
    puts(line)
  end
end

# ファイル書き込み
File.open("text.txt", "a") do |f| 
  f.puts("ruby.rbで追加した文章")
end

```

**Python3の場合**

```
#!/usr/bin/env python3

# text.txtの内容を一行ずつ表示する。
# 第二引数は、モード指定 (以下、指定の一覧）
# r ：Read Only
# r+：Read + Write (ファイルの読み書き位置は先頭)
# w ：Write Only (ファイルが無ければ新規作成)
# w+：Read + Write (ファイルが無ければ新規作成。有る場合は空にする）
# a ：Append (追記)
# a+：Append + Read (読み込みはファイル先頭から、書き込みはファイル末尾から)
# t ：テキストモード
# b ：バイナリモード
with open('text.txt', mode='rt') as f:
    for line in f:
        print(line.strip())

# ファイル書き込み
with open('text.txt', mode='at') as f:
    f.write("python.pyで追加した文章\n")

```

**Bash、Ruby、Python3の実行例**

```
$ ./bash.sh 
サンプルテキスト
スクリプトが一行ずつ読み込む
Test TEST

$ ./ruby.rb 
サンプルテキスト
スクリプトが一行ずつ読み込む
Test TEST
bash.shで追加した文章

$ ./python.py 
サンプルテキスト
スクリプトが一行ずつ読み込む
Test TEST
bash.shで追加した文章
ruby.rbで追加した文章

(注釈) 最終的なtext.txtの中身を出力
$ cat text.txt 
サンプルテキスト
スクリプトが一行ずつ読み込む
Test TEST
bash.shで追加した文章
ruby.rbで追加した文章
python.pyで追加した文章

```
