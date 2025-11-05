---
title: "【Bash / Ruby / Python3】ファイルのコピー、ファイルの移動方法の比較"
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
  image: images/copy-160129_640-1.jpg
  alt: "【Bash / Ruby / Python3】ファイルのコピー、ファイルの移動方法の比較"
  hidden: false
---

## 前書き 

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、「ファイルのコピー方法」および「ファイル移動方法」を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

https://debimate.jp/2020/04/05/bashshell-script%e3%81%8b%e3%82%89ruby%e3%82%84python%e3%81%ab%e4%b9%97%e3%82%8a%e6%8f%9b%e3%81%88%ef%bc%81%e9%a0%bb%e7%b9%81%e3%81%ab%e4%bd%bf%e3%81%86%e5%87%a6%e7%90%86%e3%82%92%e5%90%84%e8%a8%80/

## 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

## 比較：ファイルコピー方法とファイル移動方法

自動化Scriptでは、バックアップをファイルを作成したり、編集が終わったファイルを別の場所に移動する機会が多いです。

以下に、各言語の実装例および実行例を示します。

**Bashの場合**

```
#!/bin/bash

echo "ファイルのコピー：bash.shをbash_copy.shとしてコピーします。"
cp bash.sh bash_copy.sh

# ファイルの移動
# backupディレクトリは、予め存在する状態で実行する。
# 移動時に、第二引数に別ファイル名を指定可能。
echo "ファイルの移動：bash_copy.shをbackupディレクトリに移動します。"
mv bash_copy.sh backup/.

```

**Rubyの場合**

```
#!/usr/bin/env ruby

require "fileutils"

# ファイルのコピー
puts("ファイルのコピー：ruby.rbをruby_copy.rbとしてコピーします。")
FileUtils.cp("ruby.rb", "ruby_copy.rb")

# ファイルの移動
# backupディレクトリは、予め存在する状態で実行する。
# 移動時に、第二引数に別ファイル名を指定可能。
puts("ファイルの移動：ruby_copy.rbをbackupディレクトリに移動します。")
FileUtils.mv("ruby_copy.rb", "backup/.")

```

**Pythonの場合**

```
#!/usr/bin/env python3

import shutil

# ファイルのコピー
print("ファイルのコピー：python.pyをpython_copy.pyとしてコピーします。")
shutil.copy('python.py', 'python_copy.py')

# ファイルの移動
# backupディレクトリは、予め存在する状態で実行する。
# 移動時に、第二引数に別ファイル名を指定可能。
print("ファイルの移動：python_copy.pyをbackupディレクトリに移動します。")
shutil.move('python_copy.py', 'backup/.')

```

**Bash、Ruby、Python3の実行例**

```
$ ls　　　　（注釈）：スクリプト実行前の確認
backup  bash.sh  python.py  ruby.rb

$ ./bash.sh 
ファイルのコピー：bash.shをbash_copy.shとしてコピーします。
ファイルの移動：bash_copy.shをbackupディレクトリに移動します。

$ ./ruby.rb 
ファイルのコピー：ruby.rbをruby_copy.rbとしてコピーします。
ファイルの移動：ruby_copy.rbをbackupディレクトリに移動します。

$ ./python.py 
ファイルのコピー：python.pyをpython_copy.pyとしてコピーします。
ファイルの移動：python_copy.pyをbackupディレクトリに移動します。

$ tree   (注釈)：ファイルコピーとファイル移動の確認
.
├── backup
│   ├── bash_copy.sh
│   ├── python_copy.py
│   └── ruby_copy.rb
├── bash.sh
├── python.py
└── ruby.rb

1 directory, 6 files

```
