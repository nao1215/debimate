---
title: "【Bash / Ruby / Python3】ユーザ入力(input)受け付け方法の比較"
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
  image: "images/laptop-820274_640-min.jpg"
  alt: "【Bash / Ruby / Python3】ユーザ入力(input)受け付け方法の比較"
  hidden: false
---

### 前書き

自動化Script作成時に、Bash (Shell Script)ではなく、RubyやPython3を用いた方がScriptのメンテナンス負荷が低くなります。自動化Scriptに使用するプログラミング言語変更を目的として、各言語の実装を比較します。

本記事では、ユーザからのキーボード入力を受け付ける方法を比較します。比較では、実装例および実行例をそれぞれ示します。

Bashではなく、RubyやPython3を使った方が好ましい理由は、以下の記事に記載しています。この記事には、各プログラミング言語の様々な実装（ディレクトリ操作やファイル操作など）を比較した他記事へのリンクを一覧にまとめています。

- [Bash(Shell Script)からRubyやPythonに乗り換え！頻繁に使う処理を各言語で比較](https://debimate.jp/post/2020-04-05-bashshell-script%E3%81%8B%E3%82%89ruby%E3%82%84python%E3%81%AB%E4%B9%97%E3%82%8A%E6%8F%9B%E3%81%88%E9%A0%BB%E7%B9%81%E3%81%AB%E4%BD%BF%E3%81%86%E5%87%A6%E7%90%86%E3%82%92%E5%90%84%E8%A8%80/)


### 各言語のVersion

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

### 比較：ユーザ入力の受け付け

自動化Scriptでは、ある程度処理が進んだ後に、処理を継続してよいかをユーザに尋ねる機会が多いです。そのような場合に、キーボード入力を受け付け、入力されたキーに応じた処理を実施します。

以下に、各言語の実装例および実行例を示します。

**Bashの場合**

```
#!/bin/bash

# "Yes", "Y", "y"のいずれかが入力されるまで、入力を受け付ける例
# echoコマンドに-nオプションを付ける事で、改行無し。
while true
do
    echo -n "次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:"
    read input
    case ${input} in
    "y" | "Y" | "Yes")
        echo "次の処理に進みます。"
        # breakして、ループを抜ける。
        break ;;
    "n" | "N" | "No")
        echo  "キー入力を再度待ちます。"
        # breakしないため、無限ループする。
        ;;
    *)
        # 入力受付のデフォルト値。こちらもbreakせず、無限ループする。
        echo  "${input}：未対応のキー入力"
        ;;
    esac
done

echo "ユーザ入力の受付終了"
```

**Rubyの場合**

```
#!/usr/bin/env ruby

# "Yes", "Y", "y"のいずれかが入力されるまで、入力を受け付ける例
while true
  printf("次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:")
  input = gets()
  case input.chomp! 
  when "y", "Y", "Yes" then
    printf("次の処理に進みます。\n")
    break
  when "n", "N", "No" then
    printf("キー入力を再度待ちます。\n")
  else
    printf(input + "：未対応のキー入力\n")
  end
end

printf("ユーザ入力の受付終了\n")

```

**Python3の場合**

```
#!/usr/bin/env python3

import sys

while True:
    key_input = input("次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:")
    # PythonにSwitch-case文は存在しない。
    if key_input  in {"y", "Y", "Yes"}:
        print("次の処理に進みます。")
        break
    elif key_input in {"n", "N", "No"}:
        print("キー入力を再度待ちます。")
    else:
        print(key_input + "：未対応のキー入力")

print("ユーザ入力の受付終了")

```

**Bash、Ruby、Python3の実行例**

```
$ ./bash.sh 
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:n
キー入力を再度待ちます。
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:No
キー入力を再度待ちます。
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:N
キー入力を再度待ちます。
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:bash
bash：未対応のキー入力
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:Yes
次の処理に進みます。
ユーザ入力の受付終了

$ ./ruby.rb 
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:No
キー入力を再度待ちます。
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:n
キー入力を再度待ちます。
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:N
キー入力を再度待ちます。
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:ruby
ruby：未対応のキー入力
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:y
次の処理に進みます。
ユーザ入力の受付終了

$ ./python.py 
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:N
キー入力を再度待ちます。
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:n
キー入力を再度待ちます。
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:No
キー入力を再度待ちます。
次の処理に進む場合はYes、再度キー入力を受け付ける場合はNo:Y
次の処理に進みます。
ユーザ入力の受付終了

```
