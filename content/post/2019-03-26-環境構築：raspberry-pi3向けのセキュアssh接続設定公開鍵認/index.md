---
title: "Raspberry Pi3向けのセキュアSSH接続設定(公開鍵認証、rootアクセス禁止、ログインユーザ設定など)"
type: post
date: 2019-03-26
categories:
  - "linux"
tags:
  - "linux"
  - "raspberrypi"
  - "環境構築"
cover:
  image: images/raspberry-pi-1383832_640.jpg
  alt: "Raspberry Pi3向けのセキュアSSH接続設定(公開鍵認証、rootアクセス禁止、ログインユーザ設定など)"
  hidden: false
images: ["post/2019-03-26-環境構築：raspberry-pi3向けのセキュアssh接続設定公開鍵認/images/raspberry-pi-1383832_640.jpg"]
---

## 前書き：SSHをよりセキュアに

SSH(Secure SHell)は、通信を暗号化した状態でリモートPCに接続するソフトウェアです。SSHは便利な反面、外部PCからの接続を許可するため、セキュリティ対策が必要です。本記事では、SSHのセキュリティ対策設定を記載します。Raspberry Pi3前提で記載しますが、他の環境でも同じ内容が(ほぼ)実施可能です。

以下の順番で手順を記載します。

実施順

- ログイン形式を公開鍵認証に変更
- rootアクセスを禁止
- ログインユーザ設定(ホワイトリスト作成)
- Port番号を任意の番号に変更
- プロトコル変更

## ログイン形式を公開鍵認証に変更

SSHによるログイン方式は、以下の2種類があります(正確には、チャレンジレスポンス認証もあります)。これらの形式の特徴を説明した後、公開鍵認証に変更する手順を示します。

ログイン形式

- パスワード認証方式(デフォルト)
- 公開鍵認証方式

パスワード認証は、一般的にセキュアではないとみなされています。その理由は、複数回トライすれば第三者がログインできる可能性があるためです。特に、Raspberry Piシリーズは、初期ユーザ名(pi)および初期パスワード(raspberry)が有名です。そのため、初期設定状態は様々な方法で狙われるため、危険です。このような背景から、piユーザを別名に変更、もしくはパスワードを変更することが推奨されています。

一方で、公開鍵認証はセキュアと考えられています。公開鍵は、秘密鍵とペアで取り扱われ、サーバ側(今回の例ではRaspberry Pi3)に格納されます。秘密鍵は、文字通り秘密(非公開)な状態でユーザが管理します。認証時、ユーザは秘密鍵から生成される署名をサーバに提供し、サーバは格納している公開鍵と渡された署名を検証します。

公開鍵認証がセキュアな理由は、1）サーバにパスワードを公開しない事、2）秘密鍵自体をサーバに公開しない事、3）サーバに提示する署名は流用困難である事、の3点が挙げられます。

以上が、各ログイン方式の差異説明です。本題のログイン方式を公開鍵認証に変更する手順は、以下の通りです。

Host側の手順

まず、公開鍵と秘密鍵のペアを作成します。暗号化形式はRSA形式(最もセキュアな形式はed25519)、鍵の長さはデフォルト値(2048bit)の2倍とします。以下のコマンド実行後、公開鍵=id\_rsa.pub、秘密鍵=id\_rsaが生成されます。

```
$ ssh-keygen -t rsa -b 4096 -C "n.chika156@gmail.com(注釈：自分のメールアドレスを入力)"
Generating public/private rsa key pair.
Enter file in which to save the key (/home/nao/.ssh/id_rsa): (注釈)：Enterで良い
Enter passphrase (empty for no passphrase): 　　　　　　　　   (注釈)：パスワードを入力。
Enter same passphrase again: 　　　　　　　　　　　　　　　     　(注釈)：パスワード再入力。
Your identification has been saved in /home/nao/.ssh/id_rsa.
Your public key has been saved in /home/nao/.ssh/id_rsa.pub.
The key fingerprint is:
SHA256:eRFZ6VUf+qRCMnTJuaaBBt8pNZKQ9DprtQngJpnbnRk n.chika156@gmail.com
The key's randomart image is:
+---[RSA 4096]----+
|    .oo ..o++. o.|
|     o.o.oo=. o o|
|   .  o.=o+o.o ..|
|  + . .= =++. +  |
| + o E..S =. . . |
|  = . O oo  .    |
| . . * o         |
|    .            |
|                 |
+----[SHA256]-----+

```

作成した公開鍵をRaspberry Pi3にコピー(転送)します。コピー先は、Raspberry Pi3環境の~/.ssh/authorized\_keysです。IPアドレスは192.168.10.108、ユーザはnaoと仮定した場合、以下のようなコマンドとなります。

```
[書式] ssh-copy-id -i 公開鍵へのPATH  ユーザ名@コピー先IPアドレス

$ ssh-copy-id -i /home/nao/.ssh/id_rsa.pub nao@192.168.10.108

```

Target(サーバ、Raspberry Pi3)側の設定

ログイン形式を公開鍵認証に変更するため、Raspberry Pi3の"/etc/ssh/sshd\_config"を管理者権限で以下のように編集します。

```
#公開鍵認証を有効化
PubkeyAuthentication yes

#パスワード認証を無効化
PasswordAuthentication no

# パスワード無しのユーザログインを禁止
PermitEmptyPasswords no

```

## rootアクセスを禁止

root権限でSSHアクセス、された場合、環境を完全に乗っ取られた状態になります。そのため、Raspberry Pi3の"/etc/ssh/sshd\_config"を管理者権限で以下のように編集します。

```
PermitRootLogin no

```

\[the\_ad id="598"\]

## ログインユーザ設定(ホワイトリスト作成)

限られたユーザのみがSSHアクセスする場合は、ログイン可能なユーザをホワイトリスト形式で制限します。そのため、Raspberry Pi3の"/etc/ssh/sshd\_config"を管理者権限で以下のように編集します。「ユーザ名指定」、「ユーザ名と接続元IPアドレスをセットで指定」、「許可する接続元IP指定」の3種類があります。

```
AllowUsers ユーザ名 ユーザ名@IPアドレス *@IPアドレス

```

## Port番号を任意の番号に変更

SSHの初期Port番号は、22番portです。この番号は有名なため、Botなどで機械的に攻撃(例：ブルートフォース)される可能性があります。そのため、[他のサービスで使用されていないポート番号](https://ja.wikipedia.org/wiki/TCP%E3%82%84UDP%E3%81%AB%E3%81%8A%E3%81%91%E3%82%8B%E3%83%9D%E3%83%BC%E3%83%88%E7%95%AA%E5%8F%B7%E3%81%AE%E4%B8%80%E8%A6%A7)に変更します。具体的には、下表のPrivate Portの範囲が適切です。

| **種類** | **範囲** | **説明** |
| --- | --- | --- |
| Well-Known Port  | 0〜1023 | 一般的なサービスが用いる番号 |
| Registered Port | 1024〜49151 | 登録済みポート番号 |
| Private Port | 49152〜65535 | 自由に使用可能なポート番号 |

使用するPort番号が決まった後、Raspberry Pi3の"/etc/ssh/sshd\_config"を管理者権限で以下のように編集します。

```
Port 49152

```

## プロトコル変更

Raspberry Pi3では、デフォルトでセキュアなプロトコル2が使用されています。そのため、Raspberry Pi3の"/etc/ssh/sshd\_config"が以下の状態かを確認するだけで良いです。

```
Protocol 2

```

## 設定確認：sshd\_configの構文チェック

本記事の手順で修正したsshd\_configの構文チェックを実施します。記述が間違えていた場合、最悪のケースは修正するまでSSHログインができなくなります。以下のコマンドで、構文チェックが出来ます。

```
$ sudo sshd -t
   (注釈)：構文が正しい場合は、何も出力されない。

```

構文チェックがOKの場合、SSHサービスを再起動すれば設定が反映されます。

```
$ sudo systemctl restart ssh

```

## SSHログインの簡略化：~/.ssh/configの設定

ここまでの手順を実施した場合、Raspberry Pi3にSSHログイン時に、「-Pオプション ポート番号」「-iオプション 秘密鍵へのPATH」を入力する必要があります。入力例は、以下のとおりです。

```
$ ssh -P 49152 -i ~/.ssh/id_rsa 192.168.10.108

```

このコマンドを毎回入力する事は面倒なため、Host(クライアント)側の~/.ssh/configにポート番号と秘密鍵へのPATHを設定しておきます。設定例は以下の通りです。

```
Host rpi           # 接続先の名称(任意)
    HostName 192.168.10.108        # 接続先のIPアドレス
    User nao                       # 接続先のユーザ名
    Port 49152                     # SSHのPort番号 
    IdentityFile ~/.ssh/id_rsa     # 秘密鍵へのPATH

```

以上の設定を行うと、以下の入力方式でSSHログインできます。

```
$ ssh rpi

```

## 後書き

ロシア人は、SSH(エスエスエイチ)を「エスエスハー」と話します。初めて聞いた時に、驚きました。
