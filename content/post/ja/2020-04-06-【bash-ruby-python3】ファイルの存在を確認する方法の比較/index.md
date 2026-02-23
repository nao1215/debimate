---
title: "【Bash / Ruby / Python3】ファイルの存在を確認する方法の比較"
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
  image: "images/list-2389219_640.jpg"
  alt: "【Bash / Ruby / Python3】ファイルの存在を確認する方法の比較"
  hidden: false
---

### 前書き

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、ファイルの存在を確認する方法を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

- [Bash(Shell Script)からRubyやPythonに乗り換え！頻繁に使う処理を各言語で比較](https://debimate.jp/post/2020-04-05-bashshell-script%E3%81%8B%E3%82%89ruby%E3%82%84python%E3%81%AB%E4%B9%97%E3%82%8A%E6%8F%9B%E3%81%88%E9%A0%BB%E7%B9%81%E3%81%AB%E4%BD%BF%E3%81%86%E5%87%A6%E7%90%86%E3%82%92%E5%90%84%E8%A8%80/)

---



### 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

---


### 比較：ファイルの存在を確認する方法

ファイルの存在確認は、ファイルが存在しなければ後続処理が失敗してしまう場合や、ファイルを作成すべきかどうかの判断をする際に、実施する機会が多いです。

以下に、各言語の実装例および実行例を示します。

**Bashの場合**

```
#!/bin/bash

# bash.sh、python.py、ruby.rbが存在するディレクトリで、
# 以下のコードを実行する。

# ファイルが存在するケース
if [ -f "ruby.rb" ]; then
    # こちらが実行される。
    echo "ruby.rbが存在する。"
else
    echo "ruby.rbが存在しない"
fi

# 否定演算子を使ったケース（ファイルが存在するケース）
if [ ! -f "python.py" ]; then
    echo "python.pyが存在しない。"
else
    # こちらが実行される。
    echo "python.pyが存在する。"
fi

# ファイルが存在しないケース
if [ -f "not_exist.txt" ]; then
    echo "not_exist.txtが存在する。"
else
    # こちらが実行される。
    echo "not_exist.txtが存在しない。"
fi
```

**Rubyの場合**

```
#!/usr/bin/env ruby

# bash.sh、python.py、ruby.rbが存在するディレクトリで、
# 以下のコードを実行する。

# ファイルが存在するケース
if File.exist?("bash.sh")
  # こちらが実行される。
  printf("%s: bash.shが存在する。\n", File.exist?("bash.sh"))
else
  printf("%s: bash.shが存在しない。\n", File.exist?("bash.sh"))
end

# 否定演算子を使ったケース（ファイルが存在するケース）
if !File.exist?("python.py")
  printf("%s: python.pyが存在しない。\n", !File.exist?("python.py"))
else
  # こちらが実行される。
  printf("%s: python.pyが存在する。\n", !File.exist?("python.py"))
end

# ファイルが存在しないケース
if File.exist?("not_exist.txt")
  printf("%s: not_exist.txtが存在する。\n", File.exist?("not_exist.txt"))
else
  # こちらが実行される。
  printf("%s: not_exist.txtが存在しない。\n", File.exist?("not_exist.txt"))
end

```

**Python3の場合**

```
#!/usr/bin/env python3
import os

# bash.sh、python.py、ruby.rbが存在するディレクトリで、
# 以下のコードを実行する。

# ファイルが存在するケース
if(os.path.isfile("python.py")):
    # こちらが実行される。
    print("%s: python.pyが存在する。" % os.path.isfile("python.py"))
else:
    print("%s: python.pyが存在しない。" %  os.path.isfile("python.py"))

# 否定演算子を使ったケース（ファイルが存在するケース）
if(not os.path.isfile("bash.sh")):
    print("%s: bash.shが存在する。" % (not os.path.isfile("bash.sh")))
else:
    # こちらが実行される。  
    print("%s: bash.shが存在しない。" %  (not os.path.isfile("bash.sh")))

# ファイルが存在しないケース
if(os.path.isfile("not_exist.txt")):
    print("%s: not_exist.txtが存在する。" % os.path.isfile("not_exist.txt"))
else:
    # こちらが実行される。
    print("%s: not_exist.txtが存在しない。" %  os.path.isfile("not_exist.txt"))

```

**Bash、Ruby、Python3の実行例**

```
$ ls        (注釈) 実行ディレクトリにあるファイルの確認
bash.sh  python.py  ruby.rb

$ ./bash.sh 
ruby.rbが存在する。
python.pyが存在する。
not_exist.txtが存在しない。

$ ./ruby.rb 
true: bash.shが存在する。
false: python.pyが存在する。
false: not_exist.txtが存在しない。

$ ./python.py 
True: python.pyが存在する。
False: bash.shが存在しない。
False: not_exist.txtが存在しない。

```
