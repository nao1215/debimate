---
title: "【visudo / vigr / vipw】システムファイルをsudo viで編集は駄目【sudoers / group / passwd】"
type: post
date: 2020-12-16
categories:
  - "linux"
tags:
  - "debian"
  - "linux"
cover:
  image: images/key-2114046_640.jpg
  alt: "【visudo / vigr / vipw】システムファイルをsudo viで編集は駄目【sudoers / group / passwd】"
  hidden: false
images: ["images/key-2114046_640.jpg"]
---

## 前書き：システムファイルの編集は慎重に

Linuxは、ユーザ／パスワード／管理者権限などの情報を/etc以下に存在するシステムファイルで管理しています。

管理者権限があればシステムファイルを自由に書き換えられますが、書式を間違えた状態で保存してしまうとシステムが正しく動作しなくなります。下手すると、ログインできない状態に陥ります。

例えば、管理者ユーザを追加するために"sudo vi /etc/sudoers"で編集して、間違えた内容で保存して慌てた人がいらっしゃるのではないでしょうか。かく言う私もその一人でね。

そんな悲劇を減らすため、本記事ではシステムファイル編集後、書式チェックも実行するコマンドを紹介します。

## システムファイル編集用のコマンド一覧

下表に示すコマンドは、「環境変数EDITORもしくは環境変数VISUALに指定されたエディタ」もしくは「viコマンド」でシステムファイルを開き、ファイル編集後に書式チェックを実行します。

| **ファイル名** | **編集コマンド** | **ファイルの役割** |
| :-- | :-- | :-- |
| /etc/passwd | vipwもしくはvigr -p | ユーザ名、UID／GIDなどの管理 |
| /etc/shadow | vipw -s | ユーザのパスワード情報の管理 |
| /etc/group | vipw -gもしくはvigr | グループ、サブグループ、GIDなどの管理 |
| /etc/gshadow | vigr -s | グループのパスワード情報の管理 |
| /etc/sudoers | visudo | sudoコマンドを使用できるユーザ情報の管理 |

## 使用するエディタを変更したい場合

Debian環境かつvisudoコマンドは、update-alternativesコマンドで使用するエディタを変更できます。

```
$ sudo update-alternatives --config editor           
alternative editor (/usr/bin/editor を提供) には 6 個の選択肢があります。

  選択肢    パス             優先度  状態
------------------------------------------------------------
  0            /bin/nano           40        自動モード
* 1            /bin/nano           40        手動モード
  2            /usr/bin/code       0         手動モード
  3            /usr/bin/emacs      0         手動モード
  4            /usr/bin/nvim       30        手動モード
  5            /usr/bin/vim.nox    40        手動モード
  6            /usr/bin/vim.tiny   15        手動モード

現在の選択 [*] を保持するには <Enter>、さもなければ選択肢の番号のキーを押してください: 0
```

vipwコマンドおよびvigrコマンドは、上記の手順ではエディタ設定を変更できません。また、上記のエディタ一覧の/usr/bin/codeはVisual Stdio Codeですが、管理者権限で実行できません（visudo／vigr／vipwは、VS Codeを起動できません）。

vipwコマンドおよびvigrコマンドで使用するエディタを変更するには、

- ユーザをrootに変更
- 環境変数EDITORもしくは環境変数VISUALを変更

を行う必要があります。

以下、変更例です。

環境変数EDITORには、設定したいエディタの絶対PATHを指定し、exportコマンドで環境変数EDITORを反映しています。絶対PATHが分からない場合は、"$ which $(設定したいエディタ名)"で調べられます。

```
(注釈) rootユーザに変更
$ su
パスワード:

(注釈) 環境変数を設定
# export EDITOR=/bin/nano

(注釈) システムファイルを編集
# /sbin/vigr

```

## 最後に

visudoコマンドの存在を知ってからも、"sudo vi /etc/sudoers"を頑なに貫いています。
