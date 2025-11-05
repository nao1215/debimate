---
title: "【Bash / Ruby / Python3】新規ディレクトリ作成方法、ディレクトリ削除方法の比較"
type: post
date: 2020-04-10
categories:
  - "linux"
tags:
  - "bash"
  - "linux"
  - "python"
  - "ruby"
  - "shellscript"
cover:
  image: images/folder-2517423_640-min.jpg
  alt: "【Bash / Ruby / Python3】新規ディレクトリ作成方法、ディレクトリ削除方法の比較"
  hidden: false
---

## 前書き

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、「新規ディレクトリの作成方法」および「ディレクトリ削除方法」を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

https://debimate.jp/2020/04/05/bashshell-script%e3%81%8b%e3%82%89ruby%e3%82%84python%e3%81%ab%e4%b9%97%e3%82%8a%e6%8f%9b%e3%81%88%ef%bc%81%e9%a0%bb%e7%b9%81%e3%81%ab%e4%bd%bf%e3%81%86%e5%87%a6%e7%90%86%e3%82%92%e5%90%84%e8%a8%80/

## 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

## 比較：「新規ディレクトリの作成方法」および「ディレクトリ削除方法」

自動化Scriptでは、設定ファイル保存用のディレクトリを作成したり、一時保管場所としていたディレクトリを削除する機会が多いです。

以下に、各言語の実装例および実行例を示します。

**Bashの場合**

```
#!/bin/bash

# -pオプション：親ディレクトリ含めて新規ディレクトリを作成する。
echo "新規ディレクトリ(new_dir/child_dir)を作成します。"
mkdir -p new_dir/child_dir

echo "ディレクトリ作成の確認をします。"
tree

echo "---"
# -rオプション：ディレクトリとディレクトリ内部にあるファイルを削除する。
# -fオプション：確認無しで、強制的にファイルを削除する。
echo "ディレクトリ(new_dir)を削除します。"
rm -rf new_dir

echo "ディレクトリ削除の確認をします。"
tree
```

**Rubyの場合**

```
#!/usr/bin/env ruby

require "fileutils"

puts("新規ディレクトリ(new_dir/child_dir)を作成します。")
FileUtils.mkdir_p('new_dir/child_dir')

# system()は、外部コマンド(例：/bin以下のバイナリ)を実行する。
puts("ディレクトリ作成の確認をします。")
system('tree')

# Dir.rmdir()　　　：空のディレクトリを削除する場合に使用する。
# FileUtils.rm_r() ：再帰的にディレクトリの削除を行う。
# FileUtils.rm_rf()：再帰的にディレクトリを"強制的"に削除する。
puts("---")
puts("ディレクトリ(new_dir)を削除します。")
FileUtils.rm_rf('new_dir')

puts("ディレクトリ削除の確認をします。")
system('tree')

```

**Pythonの場合**

```
#!/usr/bin/env python3

import os
import subprocess
import shutil

print("新規ディレクトリ(new_dir/child_dir)を作成します。")
os.makedirs('new_dir/child_dir')

# subprocess.run()は、外部コマンド(例：/bin以下のバイナリ)を実行する。
print("ディレクトリ作成の確認をします。")
subprocess.run('tree')

# os.rmdir()　　 ：空のディレクトリを削除する場合に使用する。
# shutil.rmtree()：再帰的にディレクトリの削除を行う（削除確認なし）。
print("---")
print("ディレクトリ(new_dir)を削除します。")
shutil.rmtree('new_dir')

print("ディレクトリ削除の確認をします。")
subprocess.run('tree')

```

**Bash、Ruby、Python3の実行例**

```
$ ./bash.sh 
新規ディレクトリ(new_dir/child_dir)を作成します。
ディレクトリ作成の確認をします。
.
├── bash.sh
├── new_dir
│   └── child_dir
├── python.py
└── ruby.rb

2 directories, 3 files
---
ディレクトリ(new_dir)を削除します。
ディレクトリ削除の確認をします。
.
├── bash.sh
├── python.py
└── ruby.rb

0 directories, 3 files

$ ./ruby.rb 
新規ディレクトリ(new_dir/child_dir)を作成します。
ディレクトリ作成の確認をします。
.
├── bash.sh
├── new_dir
│   └── child_dir
├── python.py
└── ruby.rb

2 directories, 3 files
---
ディレクトリ(new_dir)を削除します。
ディレクトリ削除の確認をします。
.
├── bash.sh
├── python.py
└── ruby.rb

0 directories, 3 files

$ ./python.py 
新規ディレクトリ(new_dir/child_dir)を作成します。
ディレクトリ作成の確認をします。
.
├── bash.sh
├── new_dir
│   └── child_dir
├── python.py
└── ruby.rb

2 directories, 3 files
---
ディレクトリ(new_dir)を削除します。
ディレクトリ削除の確認をします。
.
├── bash.sh
├── python.py
└── ruby.rb

0 directories, 3 files

```
