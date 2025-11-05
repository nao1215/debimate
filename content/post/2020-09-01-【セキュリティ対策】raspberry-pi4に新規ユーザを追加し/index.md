---
title: "【セキュリティ対策】Raspberry Pi4に新規ユーザを追加し、piユーザを削除"
type: post
date: 2020-09-01
categories:
  - "linux"
tags:
  - "debian"
  - "linux"
  - "raspberrypi"
cover:
  image: "images/subscribe-3534409_640-min.jpg"
  alt: "【セキュリティ対策】Raspberry Pi4に新規ユーザを追加し、piユーザを削除"
  hidden: false
---

## 前書き：piユーザは脆弱

Raspberry Piのデフォルトユーザであるpiユーザ（管理者権限あり）は、パスワードがraspberryに設定されています。この情報は悪意のあるユーザも当然知っているため、近年ではpiユーザを狙い撃ちにしたマルウェアが増えています。

一般的には、piユーザのパスワードを変更する事によって、セキュリティリスクを減らします。本記事では、もう一歩踏み込んで、piユーザ以外に管理者権限を付与した後に、piユーザを削除する方法を紹介します。

## 新規ユーザの追加

新規ユーザ名は任意ですが、本記事では新規ユーザをantonとして以下の手順を進めます。なお、antonの元ネタは、シリコンバレー（海外ドラマ）の登場人物であるギルフォイルが構築したサーバ名です。

新規ユーザの追加にはuseraddコマンドを使用し、パスワードの設定にはpasswdコマンドを使用します。

```
$ sudo useradd -m -d /home/anton -s /bin/bash anton
$ sudo passwd anton
```

useraddのオプションについて補足すると、

- \-m：ユーザのホームディレクトリがない場合は作成
- \-d：ユーザのホームディレクトリPATH
- \-s：ログインシェルの指定。

ログインシェルをBash以外に変更したい場合は/etc/shellsファイルを確認し、使用したいシェルを探してからユーザを作成してください。もしくは、ユーザ作成後にchshコマンドでシェルを変更する方法があります。

```
（注釈）：dashを使う場合
$ cat /etc/shells 
# /etc/shells: valid login shells
/bin/sh
/bin/bash
/bin/rbash
/bin/dash　　※ 絶対PATHを確認

$ sudo useradd -m -d /home/anton -s /bin/dash anton

（注釈）：ユーザ作成後にシェルを変更
 $ chsh -s /bin/dash

```

## 新規ユーザに管理者権限を付与

各ユーザの管理者権限の有無は、/etc/sudoersファイルで管理されています。/etc/sudoersファイルの書式を間違うと、sudoコマンドが使用できなくなる落とし穴があります。

一般的には、書式チェック機能があるvisudoコマンドで/etc/sudoersファイルを編集する場合が多いです（私は愚か者なので、直接vimで編集します！）。

本記事では、書き間違えが発生しない方法で、新規ユーザ（=anton）がsudoコマンドを使えるようにします。具体的には、新規ユーザをsudoグループに所属させます。

```
$ sudo gpasswd -a anton sudo

```

## 「piユーザ所属グループ」と「新規ユーザの所属グループ」を一致させる

管理者権限があるので、細かい権限を一致させる必要性薄いのですが、「新規ユーザ（=anton）」と「piユーザの所属グループ」を一致させます。

まずは、piユーザのグループを確認した後に、usermodコマンドで新規ユーザのグループ情報をpiユーザに合わせます。usermodコマンドは、-Gオプションの後に追加したいグループ名をカンマ区切りで記載します。後ほど削除するpiグループは、追加不要です。

```
$ groups pi
pi : pi adm dialout cdrom sudo audio video plugdev games users input netdev spi i2c gpio

$ sudo usermod -G adm,dialout,cdrom,sudo,audio,video,plugdev,games,users,input,netdev,spi,i2c,gpio anton

```

所属グループ情報が正しく更新されているかどうかは、groupsコマンドで確認できます。　　　　　　

```
$ groups anton
anton : anton adm dialout cdrom sudo audio video plugdev games users input netdev pi spi i2c gpio

```

## piユーザの自動ログインを解除

Raspberry Piは、CLIもしくはGUI環境にpiユーザで自動ログインするかどうかを設定できます。piユーザは後ほど削除するため、自動ログイン設定を変更しておきます。

```
$ sudo raspi-config

※ 以下の順番で画面を移動してください。
[3 Boot Options] 
　⇓
[B1 Desktop / CLI]
　⇓
CLI環境にする場合：[B1 Console]を選択
GUI環境にする場合：[B3 Desktop]を選択

```

## piユーザの削除

この段階で、piユーザは不要になったので、削除します。何か起こった時のため、piユーザのホームディレクトリは残しておきます。

userdelコマンドの実行時にエラーが発生する場合は、piユーザでログインしている可能性が高いです。piユーザがログアウトしている状態で、以下の手順を新規ユーザ（=anton）で実行してください。

```
$ sudo userdel  pi

※ ホームディレクトリを消す場合
[方法1]
$ sudo userdel -r pi

[方法2]
$ sudo userdel  pi
$ sudo rm -rf /home/pi

```
