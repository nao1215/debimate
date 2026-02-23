---
title: "【Bash / Ruby / Python3】ディレクトリの存在を確認する方法の比較"
type: post
date: 2020-04-06
categories:
  - "linux"
tags:
  - "bash"
  - "linux"
  - "python"
  - "ruby"
  - "shellscript"
cover:
  image: "images/folder-2013209_640-min-1.jpg"
  alt: "【Bash / Ruby / Python3】ディレクトリの存在を確認する方法の比較"
  hidden: false
---

### 前書き

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、ディレクトリの存在を確認する方法を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

- [Bash(Shell Script)からRubyやPythonに乗り換え！頻繁に使う処理を各言語で比較](https://debimate.jp/post/2020-04-05-bashshell-script%E3%81%8B%E3%82%89ruby%E3%82%84python%E3%81%AB%E4%B9%97%E3%82%8A%E6%8F%9B%E3%81%88%E9%A0%BB%E7%B9%81%E3%81%AB%E4%BD%BF%E3%81%86%E5%87%A6%E7%90%86%E3%82%92%E5%90%84%E8%A8%80/)

---


### 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

---


### 比較：ディレクトリの存在を確認する方法

ディレクトリの存在確認は、ファイルのコピー先（ディレクトリ）が存在するかどうかのチェックなどで使用する機会が多いです。

以下に、各言語の実装例および実行例を示します。

**Bashの場合**

```
#!/bin/bash

# test_dirディレクトリが存在するディレクトリで、
# 以下のコードを実行する。

# ディレクトリが存在するケース
if [ -d "test_dir" ]; then
    # こちらが実行される。
    echo "test_dirが存在する。"
else
    echo "test_dirが存在しない。"
fi

# ディレクトリが存在しないケース
if [ -d "not_exist" ]; then
    echo "not_existが存在する。"
else
    # こちらが実行される。
    echo "not_existが存在しない。"
fi
```

**Rubyの場合**

```
#!/usr/bin/env ruby

# test_dirディレクトリが存在するディレクトリで、
# 以下のコードを実行する。

# ディレクトリが存在するケース
if Dir.exist?("test_dir")
  # こちらが実行される。
  printf("%s: test_dirが存在する。\n", Dir.exist?("test_dir"))
else
  printf("%s: bash.shが存在しない。\n", Dir.exist?("test_dir"))
end

# ディレクトリが存在しないケース
if Dir.exist?("not_exist")
  printf("%s: not_existが存在する。\n", Dir.exist?("not_exist"))
else
  # こちらが実行される。
  printf("%s: not_existが存在しない。\n", Dir.exist?("not_exist"))
end

```

**Python3の場合**

```
#!/usr/bin/env python3
import os

# test_dirディレクトリが存在するディレクトリで、
# 以下のコードを実行する。

# ディレクトリが存在するケース
if(os.path.isdir("test_dir")):
    # こちらが実行される。
    print("%s: test_dirが存在する。" % os.path.isdir("test_dir"))
else:
    print("%s: test_dirが存在しない。" %  os.path.isdir("test_dir"))

# ディレクトリが存在しないケース
if(os.path.isfile("not_exist")):
    print("%s: not_existが存在する。" % os.path.isdir("not_exist"))
else:
    # こちらが実行される。
    print("%s: not_existが存在しない。" %  os.path.isdir("not_exist"))

```

**Bash、Ruby、Python3の実行例**

```
$ ls  　　(注釈)：実行ディレクトリにあるファイル、ディレクトリの確認
bash.sh  python.py  ruby.rb  test_dir

$ ./bash.sh 
test_dirが存在する。
not_existが存在しない。

$ ./ruby.rb 
true: test_dirが存在する。
false: not_existが存在しない。

$ ./python.py 
True: test_dirが存在する。
False: not_existが存在しない。

```
