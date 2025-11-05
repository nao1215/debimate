---
title: "【Bash / Ruby / Python3】新規ファイル作成（一時ファイル作成含む）やファイル削除する方法の比較"
type: post
date: 2020-04-07
categories:
  - "linux"
tags:
  - "bash"
  - "linux"
  - "python"
  - "ruby"
  - "shellscript"
cover:
  image: images/attach-3592638_640.jpg
  alt: "【Bash / Ruby / Python3】新規ファイル作成（一時ファイル作成含む）やファイル削除する方法の比較"
  hidden: false
images: ["images/attach-3592638_640.jpg"]
---

## 前書き

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、新規ファイル作成（一時ファイル作成含む）やファイル削除する方法を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

https://debimate.jp/2020/04/05/bashshell-script%e3%81%8b%e3%82%89ruby%e3%82%84python%e3%81%ab%e4%b9%97%e3%82%8a%e6%8f%9b%e3%81%88%ef%bc%81%e9%a0%bb%e7%b9%81%e3%81%ab%e4%bd%bf%e3%81%86%e5%87%a6%e7%90%86%e3%82%92%e5%90%84%e8%a8%80/

## 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

## 比較：新規ファイル作成（一時ファイル作成含む）やファイル削除

自動化Scriptでは、一時的なファイルに情報を書き出したり、設定をファイルに書き出したりするために、ファイルを作成する機会が多いです。また、不要となったタイミングでファイルの後始末（削除）まで実施した方が行儀が良いです。

以下に、各言語の実装例および実行例を示します。

**Bashの場合**

```
#!/bin/bash

echo "1. ファイル(test_file.txt)作成"
touch test_file.txt
# [他の方法]
# echo -n > test_file.txt 
# -nオプションで、改行が無しの空ファイルを生成している。

# 一時ファイルは、以下の手順で作成すると、
# 「ファイル名がtmp.XXX(XXX=ユニーク文字列)」かつ「パーミッションが600」となる。
echo ""
echo "2. /tmp以下に一時ファイル作成"
TMP=$(mktemp)

echo ""
echo "3. 作成したファイルを表示"
ls test_file.txt
ls $TMP

echo ""
echo "4. 作成したファイルを削除"
rm test_file.txt
rm $TMP

echo ""
echo "5. ファイル削除の確認"
ls test_file.txt
ls $TMP
```

**Rubyの場合**

```
#!/usr/bin/env ruby

require 'tempfile'

printf("1. ファイル(test_file.txt)作成\n")
file = File.open("test_file.txt", "w")
# [他の方法]
# require 'fileutils'
# FileUtils.touch("test_file.txt")

# 一時ファイルは、以下の手順で作成すると、
# 「ファイル名が"basename日付-PID-n"」かつ「パーミッションが600」となる。
# Tempfile.newの()引数は、任意の文字列
printf("\n")
printf("2. /tmp以下に一時ファイル作成\n")
tmp_file = Tempfile.new('basename')

printf("\n")
printf("3. 作成したファイルを表示\n")
file_path = File.absolute_path(file.path)
tmpfile_path = File.absolute_path(tmp_file.path)
printf("%s\n", file_path)
printf("%s\n", tmpfile_path)

printf("\n")
printf("4. 作成したファイルを削除\n")
file.close()
tmp_file.close()
FileUtils.rm(file.path)
tmp_file.delete()

printf("\n")
printf("5. ファイル削除の確認\n")
printf("test_file.txtは存在するか?：%s\n", File.exist?(file_path))
printf("一時ファイルは存在するか?：%s\n", File.exist?(tmpfile_path))

```

**Python3の場合**

```
#!/usr/bin/env python3
import os
import tempfile

print("1. ファイル(test_file.txt)作成")
f = open("test_file.txt", "w")

# 一時ファイルは、以下の手順で作成すると、
# 「ファイル名がtmpXXX(XXX=ユニーク文字列)」かつ「パーミッションが600」となる。
print("")
print("2. /tmp以下に一時ファイル作成")
tmp_file = tempfile.NamedTemporaryFile()

print("")
print("3. 作成したファイルを表示")
file_path = os.path.abspath("test_file.txt")
tmpfile_path = tmp_file.name
print("%s" % file_path)<div class="box_simple"><p><strong>Python3の場合</strong></p></div>
print("%s" % tmpfile_path)

print("")
print("4. 作成したファイルを削除")
f.close()
os.remove("test_file.txt")
tmp_file.close()   # 一時ファイルはクローズすると破棄される。

print("")
print("5. ファイル削除の確認")
print("test_file.txtは存在するか?：%s" %  os.path.isfile(file_path))
print("一時ファイルは存在するか?：%s" %  os.path.isfile(tmpfile_path))

```

**Bash、Ruby、Python3の実行例**

```
$ ./bash.sh 
1. ファイル(test_file.txt)作成

2. /tmp以下に一時ファイル作成

3. 作成したファイルを表示
test_file.txt
/tmp/tmp.xpu3XUcwGx

4. 作成したファイルを削除

5. ファイル削除の確認
ls: 'test_file.txt' にアクセスできません: そのようなファイルやディレクトリはありません
ls: '/tmp/tmp.xpu3XUcwGx' にアクセスできません: そのようなファイルやディレクトリはありません

$ ./ruby.rb 
1. ファイル(test_file.txt)作成

2. /tmp以下に一時ファイル作成

3. 作成したファイルを表示
/home/nao/scripts/test_file.txt
/tmp/basename20200407-23474-7ichnp

4. 作成したファイルを削除

5. ファイル削除の確認
test_file.txtは存在するか?：false
一時ファイルは存在するか?：false

$ ./python.py 
1. ファイル(test_file.txt)作成

2. /tmp以下に一時ファイル作成

3. 作成したファイルを表示
/home/nao/scripts/test_file.txt
/tmp/tmptjp4ptro

4. 作成したファイルを削除

5. ファイル削除の確認
test_file.txtは存在するか?：False
一時ファイルは存在するか?：False

```
