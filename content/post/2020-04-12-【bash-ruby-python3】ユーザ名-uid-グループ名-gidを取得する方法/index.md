---
title: "【Bash / Ruby / Python3】ユーザ名 / UID / グループ名 / GIDを取得する方法の比較"
type: post
date: 2020-04-12
categories:
  - "linux"
tags:
  - "bash"
  - "linux"
  - "python"
  - "ruby"
  - "shellscript"
cover:
  image: "images/name-1714231_640.jpg"
  alt: "【Bash / Ruby / Python3】ユーザ名 / UID / グループ名 / GIDを取得する方法の比較"
  hidden: false
---

### 前書き

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、ユーザ名 / UID / グループ名 / GIDを取得する方法を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

- [Bash(Shell Script)からRubyやPythonに乗り換え！頻繁に使う処理を各言語で比較](https://debimate.jp/post/2020-04-05-bashshell-script%E3%81%8B%E3%82%89ruby%E3%82%84python%E3%81%AB%E4%B9%97%E3%82%8A%E6%8F%9B%E3%81%88%E9%A0%BB%E7%B9%81%E3%81%AB%E4%BD%BF%E3%81%86%E5%87%A6%E7%90%86%E3%82%92%E5%90%84%E8%A8%80/)

---


### 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

---


### 比較：ユーザ名 / UID / グループ名 / GIDを取得する方法

自動化Scriptでは、特定ユーザや特定グループのみに操作を許可する事があります。そのような場合に、ユーザ名やグループ名を取得する処理が必要になります。

以下に、各言語の実装例および実行例を示します。

**Bashの場合**

```
#!/bin/bash

echo "ユーザ名、ユーザID、グループ名、グループIDの表示"
USER_NAME=$(id -u -n)
USER_ID=$(id -u)
GROUP_NAME=$(id -g -n)
GROUP_ID=$(id -g)  # プライマリグループのみ。
echo "ユーザ名　：${USER_NAME}"
echo "UID     　：${USER_ID}"
echo "グループ名：${GROUP_NAME}"
echo "GID     　：${GROUP_ID}"
```

**Rubyの場合**

```
#!/usr/bin/env ruby

require 'etc'

puts("ユーザ名、ユーザID、グループ名、グループIDの表示")
user_id    = Process.uid
user_name  = Etc.getpwuid(user_id).name
group_id   = Process.gid
group_name = Etc.getgrgid(group_id).name

puts("ユーザ名　：" + user_name)
puts("UID     　：" + user_id.to_s())
puts("グループ名：" + group_name)
puts("GID     　：" + group_id.to_s())

```

**Python3の場合**

```
#!/usr/bin/env python3

import os
import getpass
import grp

print("ユーザ名、ユーザID、グループ名、グループIDの取得")
user_id    = os.getuid()
user_name  = getpass.getuser()
group_id   = os.getgid()
# getgrgid()はリストを返し、
# [0]グループ名、[1]暗号化されたグループパスワード、
# [2]GID、[3]グループメンバの全てのユーザ名
group_name = grp.getgrgid(group_id)[0]

print("ユーザ名　：" + user_name)
print("UID：" + str(user_id))
print("グループ名：" + group_name)
print("GID     　：" + str(group_id))

```

**Bash、Ruby、Python3の実行例**

```
$ ./bash.sh 
ユーザ名、ユーザID、グループ名、グループIDの表示
ユーザ名　：nao
UID     　：1000
グループ名：nao
GID     　：1000

$ ./ruby.rb 
ユーザ名、ユーザID、グループ名、グループIDの表示
ユーザ名　：nao
UID     　：1000
グループ名：nao
GID     　：1000

$ ./python.py 
ユーザ名、ユーザID、グループ名、グループIDの取得
ユーザ名　：nao
UID     　：1000
グループ名：nao
GID     　：1000

```
