---
title: "【Bash / Ruby / Python3】root権限を確認する方法の比較"
type: post
date: 2020-04-11
categories:
  - "linux"
tags:
  - "bash"
  - "linux"
  - "python"
  - "ruby"
  - "shellscript"
cover:
  image: images/password-397652_640-min-1.jpg
  alt: "【Bash / Ruby / Python3】root権限を確認する方法の比較"
  hidden: false
images: ["images/password-397652_640-min-1.jpg"]
---

## 前書き

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、root権限を確認する方法を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

https://debimate.jp/2020/04/05/bashshell-script%e3%81%8b%e3%82%89ruby%e3%82%84python%e3%81%ab%e4%b9%97%e3%82%8a%e6%8f%9b%e3%81%88%ef%bc%81%e9%a0%bb%e7%b9%81%e3%81%ab%e4%bd%bf%e3%81%86%e5%87%a6%e7%90%86%e3%82%92%e5%90%84%e8%a8%80/

## 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

## 比較：root権限を確認する方法

自動化Scriptでは、root権限を持つユーザしか実行を許可したくない場合があります。root権限の有無を確認する場合は、実行ID(EUID)とUIDを確認します。実行ID(EUID)は権限を定義するためのIDであり、UIDはユーザやプロセスを特定させるIDです。

通常の環境であれば、rootはEUID / UIDのどちらも0です。より正確に検証する場合は、ユーザ名がrootかどうか等も確認した方が好ましいですが、本記事ではEUIDとUIDのみを確認する方法を紹介します。

以下に、各言語の実装例および実行例を示します。

**Bashの場合**

```
#!/bin/bash

# 実行UID(EUID)とUIDを確認し、
# "0"(root)であれば管理者権限を持つ。
# ":-"部分は${EUID}に値が入っていなければ、${UID}の値を代入するという意味
if [ ${EUID:-${UID}} = 0 ]; then
    echo "管理者権限を持っています。"
else
    echo "このスクリプトの実行には、管理者権限が必要です。"
fi
```

**Rubyの場合**

```
#!/usr/bin/env ruby

# 実行UID(EUID)とUIDを確認し、
# "0"(root)であれば管理者権限を持つ。
if Process.euid == 0 and Process.uid == 0
  puts("管理者権限を持っています。")
else
  puts("このスクリプトの実行には、管理者権限が必要です。")
end
```

**Python3の場合**

```
#!/usr/bin/env python3

import os

# 実行UID(EUID)とUIDを確認し、
# "0"(root)であれば管理者権限を持つ。
if os.geteuid() == 0 and os.getuid() == 0 :
    print("管理者権限を持っています。")
else:
    print("このスクリプトの実行には、管理者権限が必要です。")

```

**Bash、Ruby、Python3の実行例**

```
$ ./bash.sh 
このスクリプトの実行には、管理者権限が必要です。
$ sudo ./bash.sh 
[sudo] nao のパスワード:
管理者権限を持っています。

$ ./ruby.rb 
このスクリプトの実行には、管理者権限が必要です。
nao@debian:~/scripts$ sudo ./ruby.rb 
管理者権限を持っています。

$ ./python.py 
このスクリプトの実行には、管理者権限が必要です。
$ sudo ./python.py 
管理者権限を持っています。

```
