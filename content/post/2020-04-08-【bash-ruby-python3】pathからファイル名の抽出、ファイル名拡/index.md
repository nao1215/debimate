---
title: "【Bash / Ruby / Python3】PATHからファイル名の抽出、ファイル名(拡張子なし)の取得、拡張子の取得方法の比較"
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
  image: images/icon-2488093_640-1-min.jpg
  alt: "【Bash / Ruby / Python3】PATHからファイル名の抽出、ファイル名(拡張子なし)の取得、拡張子の取得方法の比較"
  hidden: false
images: ["images/icon-2488093_640-1-min.jpg"]
---

## 前書き

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、「PATHからファイル名を抽出する方法」、「ファイル名（拡張子なし）の取得する方法」、「ファイル名から拡張子だけを取得する方法」を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

https://debimate.jp/2020/04/05/bashshell-script%e3%81%8b%e3%82%89ruby%e3%82%84python%e3%81%ab%e4%b9%97%e3%82%8a%e6%8f%9b%e3%81%88%ef%bc%81%e9%a0%bb%e7%b9%81%e3%81%ab%e4%bd%bf%e3%81%86%e5%87%a6%e7%90%86%e3%82%92%e5%90%84%e8%a8%80/

## 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

## 比較：PATHからファイル名の抽出、ファイル名(拡張子なし)の取得、拡張子の取得

自動化Scriptでは、ファイル名から何らかの情報を抽出したり、期待する拡張子かどうかをチェックする処理を実施する機会が多いです。

以下に、各言語の実装例および実行例を示します。

**Bashの場合**

```
#!/bin/bash

# ファイルの絶対PATH
FILE_PATH="/home/nao/text.txt"
echo "絶対PATH  ：${FILE_PATH}"

# PATHからファイル名(ベース名)だけを抽出する。
FILE_NAME=$(basename ${FILE_PATH})
echo "ベース名　：${FILE_NAME}"

# ファイル名（拡張子なし）を取得する。
# ${変数%パターン}で、末尾から最短一致した部分を取り除く。
FILENAME_WITHOUT_EXT="${FILE_NAME%.*}"
echo "ファイル名：${FILENAME_WITHOUT_EXT}"

# 拡張子を取得する。
# ${変数##パターン}で、先頭から最長一致した部分を取り除く。
EXT="${FILE_NAME##*.}"
echo "拡張子　　：${EXT}"
```

**Rubyの場合**

```
#!/usr/bin/env ruby

# ファイルの絶対PATH
file_path="/home/nao/text.txt"
puts("絶対PATH  ：" + file_path)

# PATHからファイル名(ベース名)だけを抽出する。
file_name = File.basename(file_path)
puts("ベース名　：" + file_name)

# ファイル名（拡張子なし）を取得する。
# ワイルドカードで削除すべき拡張子を指定している。
filename_without_ext =  File.basename(file_name, ".*")
puts("ファイル名：" + filename_without_ext)

# 拡張子を取得する。
# 拡張子には、"."が含まれる。ドットが不要な場合は、別途削除する。
ext = File.extname(file_name)
puts("拡張子　　：" + ext)
```

**Python3の場合**

```
#!/usr/bin/env python3

import os

# ファイルの絶対PATH
file_path="/home/nao/text.txt"
print("絶対PATH  ：" + file_path)

# PATHからファイル名(ベース名)だけを抽出する。
file_name =  os.path.basename(file_path)
print("ベース名　：" + file_name)

# ファイル名（拡張子なし）を取得する。
# os.path.splitextで、ファイル名("text")と拡張子(".txt")に分離する。
filename_without_ext = os.path.splitext(file_name)[0]
print("ファイル名：" + filename_without_ext)

# 拡張子を取得する。
# 拡張子には、"."が含まれる。ドットが不要な場合は、別途削除する。
ext = os.path.splitext(file_name)[1]
print("拡張子　　：" + ext)

```

**Bash、Ruby、Python3の実行例**

```
$ ./bash.sh 
絶対PATH  ：/home/nao/text.txt
ベース名　：text.txt
ファイル名：text
拡張子　　：txt

$ ./ruby.rb 
絶対PATH  ：/home/nao/text.txt
ベース名　：text.txt
ファイル名：text
拡張子　　：.txt

$ ./python.py 
絶対PATH  ：/home/nao/text.txt
ベース名　：text.txt
ファイル名：text
拡張子　　：.txt

```
