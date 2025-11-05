---
title: "Ubuntu (20.04)へsshログインした際に表示されるWelcomeメッセージの仕組みと表示しない方法"
type: post
date: 2021-08-14
categories:
  - "linux"
tags:
  - "linux"
  - "lpic"
  - "ssh"
  - "ubuntu"
  - "サーバー"
cover:
  image: images/welcome-sign-2284312_640-min.jpg
  alt: "Ubuntu (20.04)へsshログインした際に表示されるWelcomeメッセージの仕組みと表示しない方法"
  hidden: false
images: ["images/welcome-sign-2284312_640-min.jpg"]
---

## 前書き：UbuntuはWelcomeメッセージが立派で邪魔

ラズパイサーバ（[Raspberry Pi OS](https://www.raspberrypi.org/software/)）から[HP小型PC](https://amzn.to/3jQZUtz)（[Ubuntu 20.04](https://releases.ubuntu.com/20.04/)）にサーバ移行した時、UbuntuのWelcomeメッセージがラズパイより立派な事に気づきました。

例えば、Ubuntuにsshログインした時、以下のようなWelcomeメッセージが出ます。

```
Welcome to Ubuntu 20.04.2 LTS (GNU/Linux 5.4.0-80-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

  System information as of Sat 14 Aug 2021 06:47:32 AM UTC

  System load:  0.1                Processes:                183
  Usage of /:   6.3% of 227.73GB   Users logged in:          0
  Memory usage: 18%                IPv4 address for docker0: XXX.XX.X.X
  Swap usage:   5%                 IPv4 address for enp2s0:  XXX.XXX.X.XX
  Temperature:  52.0 C

 * Super-optimized for small spaces - read how we shrank the memory
   footprint of MicroK8s to make it the smallest full K8s around.

   https://ubuntu.com/blog/microk8s-memory-optimisation

16 updates can be applied immediately.
To see these additional updates run: apt list --upgradable

Last login: Mon Aug  9 01:43:07 2021 from XXX.XXX.X.XX
```

上記のメッセージは、システム情報やパッケージアップデートの必要性などを教えてくれます。しかし、システム負荷は別ツールで監視する事が一般的ですし、自宅サーバの場合は常に最新バージョンにアップデートする訳ではありません。

私にとっては、sshログイン時にWelcomeメッセージが表示されない方が、不要な情報に目を通さなくて済むので嬉しいです。

そこで、本記事では「Welcomeメッセージを表示する仕組み」を説明した後に、「Welcomeメッセージを表示しない方法」を紹介します。

## 検証環境

第8世代Intel Core i3、RAM8GB、Ubuntu 20.04です。サーバーというより、ただのPC。

```
            .-/+oossssoo+/-.               nao@asagi 
        `:+ssssssssssssssssss+:`           --------- 
      -+ssssssssssssssssssyyssss+- OS: Ubuntu 20.04.2 LTS x86_64 
    .ossssssssssssssssssdMMMNysssso.       Host: HP ProDesk 400 G4 DM (Japan) 
   /ssssssssssshdmmNNmmyNMMMMhssssss/      Kernel: 5.4.0-80-generic 
  +ssssssssshmydMMMMMMMNddddyssssssss+     Uptime: 6 days, 1 hour, 47 mins 
 /sssssssshNMMMyhhyyyyhmNMMMNhssssssss/    Packages: 1042 (dpkg), 5 (snap) 
.ssssssssdMMMNhsssssssssshNMMMdssssssss.   Shell: bash 5.0.17 
+sssshhhyNMMNyssssssssssssyNMMMysssssss+   Resolution: 2560x1080 
ossyNMMMNyMMhsssssssssssssshmmmhssssssso   Terminal: /dev/pts/0 
ossyNMMMNyMMhsssssssssssssshmmmhssssssso   CPU: Intel i3-8100T (4) @ 3.100GHz 
+sssshhhyNMMNyssssssssssssyNMMMysssssss+   GPU: Intel 8th Gen Core Processor Gaussian Mixture Model 
.ssssssssdMMMNhsssssssssshNMMMdssssssss.   Memory: 1166MiB / 7807MiB 
 /sssssssshNMMMyhhyyyyhdNMMMNhssssssss/
  +sssssssssdmydMMMMMMMMddddyssssssss+                             
   /ssssssssssshdmNNNNmyNMMMMhssssss/                              
    .ossssssssssssssssssdMMMNysssso.
      -+sssssssssssssssssyyyssss+-
        `:+ssssssssssssssssss+:`
            .-/+oossssoo+/-.

```

## Welcomeメッセージは/etc/motdではない

Linuxでは、ユーザーにメッセージを伝える方法として、/etc/motdファイルを利用する事があります。motdは、Message Of The Dayの略です。

motdファイルは[base-filesパッケージ](https://packages.ubuntu.com/ja/focal/base-files)（OSのシステム情報を提供するパッケージ）が提供する設定ファイルであり、[sshdデーモン（openssh-server）](https://www.openssh.com/)がmotdファイルに書かれている内容をsshログイン時にそのまま表示します。

この仕組みに関しては、以下の記事で説明しています。興味がある方はご覧ください。

https://debimate.jp/2020/12/01/%e3%80%90lpic%e3%81%a7%e8%a6%8b%e3%81%9f%e3%80%91-etc-motd%e3%81%ae%e5%86%85%e5%ae%b9%e3%82%92%e5%87%ba%e5%8a%9b%e3%81%97%e3%81%a6%e3%81%84%e3%82%8b%e3%81%ae%e3%81%af%e8%aa%b0%ef%bc%9f%e3%80%90/

しかし、Ubuntu環境ではmotdファイルがありません。そのため、別の仕組みでWelcomeメッセージを表示しています。

```
$ cat /etc/motd
cat: /etc/motd: そのようなファイルやディレクトリはありません

```

## UbuntuのWelcomeメッセージは/etc/update-motd.d/

UbuntuのWelcomeメッセージは、/etc/update-motd.d以下にある複数のShell Scriptを順番に実行する事によって、メッセージ本文を作成しています。Scriptの実行順番は、ファイル名の先頭にある数値で制御されています。数値が小さいScriptから順番に実行されます。

以下、/etc/update-motd.d以下の情報例です。

```
$ ls -al /etc/update-motd.d/
合計 68
drwxr-xr-x   2 root root  4096  8月  4 14:21 .
drwxr-xr-x 150 root root 12288  8月 14 15:47 ..
-rwxr-xr-x   1 root root  1220  9月 16  2020 00-header
-rwxr-xr-x   1 root root  1157  9月 16  2020 10-help-text
-rwxr-xr-x   1 root root  5023  9月 16  2020 50-motd-news
-rwxr-xr-x   1 root root    96  3月 27 04:07 85-fwupd
-rwxr-xr-x   1 root root   106  5月 28 04:12 88-esm-announce
-rwxr-xr-x   1 root root   218  6月 19  2020 90-updates-available
-rwxr-xr-x   1 root root   112  5月 28 04:12 91-contract-ua-esm-status
-rwxr-xr-x   1 root root   374  7月 18  2020 91-release-upgrade
-rwxr-xr-x   1 root root   165  2月 19 21:11 92-unattended-upgrades
-rwxr-xr-x   1 root root   129  6月 19  2020 95-hwe-eol
-rwxr-xr-x   1 root root   142  6月 19  2020 98-fsck-at-reboot
-rwxr-xr-x   1 root root   144  6月 19  2020 98-reboot-required

```

例として、00-headerの内容および実行結果を以下に示します。

```
$ cat /etc/update-motd.d/00-header 
#!/bin/sh
#
#    00-header - create the header of the MOTD
#    Copyright (C) 2009-2010 Canonical Ltd.
#
#    Authors: Dustin Kirkland <kirkland@canonical.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

[ -r /etc/lsb-release ] && . /etc/lsb-release

if [ -z "$DISTRIB_DESCRIPTION" ] && [ -x /usr/bin/lsb_release ]; then
	# Fall back to using the very slow lsb_release utility
	DISTRIB_DESCRIPTION=$(lsb_release -s -d)
fi

printf "Welcome to %s (%s %s %s)\n" "$DISTRIB_DESCRIPTION" "$(uname -o)" "$(uname -r)" "$(uname -m)"

```

```
$  /etc/update-motd.d/00-header 
Welcome to Ubuntu 21.04 (GNU/Linux 5.11.0-25-generic x86_64)

```

## /etc/update-motd.d/以下のScriptを実行しているのは誰？

ログイン時に、**pam\_motd.so共有ライブラリ**が/run/motd.dynamicファイルを動的に作成した後（≒/etc/update-motd.d以下のScriptを実行した後）、motd.dynamicファイルの中身を表示します。ここでのpam（Pluggable Authentication Module）とは、ユーザ認証に関連する機能提供するモジュールです。

pam\_motd.soは、/etc/pam.d/loginと/etc/pam.d/sshdから2回呼び出される事が、[Debian Wiki](https://wiki.debian.org/motd)に記載されています。裏付けは取っていませんが、UbuntuはDebian派生ディストリのため、同じ仕組みを共有していると思われます。

pam\_motd.soを提供する[libpam-modulesパッケージ](https://packages.ubuntu.com/hirsute/libpam-modules)([pamソースパッケージ](https://packages.ubuntu.com/source/hirsute/pam))を確認すると、Debian（≒Ubuntu）環境向けのパッチ（debian/patches-applied/update-motd）内でmotd.dynamicを作成する処理が確認できます。

以下、パッチの抜粋です。

```
--- pam.orig/modules/pam_motd/pam_motd.c
+++ pam/modules/pam_motd/pam_motd.c
@@ -101,8 +101,10 @@
 			int argc, const char **argv)
 {
      /* 省略 */
 
+    /* Run the update-motd dynamic motd scripts, outputting to /run/motd.dynamic.
+       This will be displayed only when calling pam_motd with
+       motd=/run/motd.dynamic; current /etc/pam.d/login and /etc/pam.d/sshd
+       display both this file and /etc/motd. */
+    if (do_update && (stat("/etc/update-motd.d", &st) == 0)
+        && S_ISDIR(st.st_mode))
+    {
+       mode_t old_mask = umask(0022);
+       if (!system("/usr/bin/env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin run-parts --lsbsysinit /etc/update-motd.d > /run/motd.dynamic.new"))
+           rename("/run/motd.dynamic.new", "/run/motd.dynamic");
+       umask(old_mask);
+    }

```

上記のパッチから、[debianutileパッケージ](https://packages.ubuntu.com/hirsute/debianutils)が提供するrun-partsコマンドを使用して/run/motd.dynamicを生成している事が読み取れます。

motd.dynamicの生成処理、つまり"run-parts --lsbsysinit /etc/update-motd.d"を実際に実行した結果は以下の通りです。Welcomeメッセージの最下部（"Last login:〜"）以外は、motd.dynamic内に記載されている事が読み取れます。

```
$ run-parts --lsbsysinit /etc/update-motd.d
Welcome to Ubuntu 20.04.2 LTS (GNU/Linux 5.4.0-80-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

  System information as of Sat 14 Aug 2021 08:42:30 AM UTC

  System load:  0.1                Processes:                160
  Usage of /:   6.3% of 227.73GB   Users logged in:          1
  Memory usage: 21%                IPv4 address for docker0: XXX.XX.X.X
  Swap usage:   5%                 IPv4 address for enp2s0:  XXX.XXX.X.XX
  Temperature:  54.0 C

 * Super-optimized for small spaces - read how we shrank the memory
   footprint of MicroK8s to make it the smallest full K8s around.

   https://ubuntu.com/blog/microk8s-memory-optimisation

16 updates can be applied immediately.
To see these additional updates run: apt list --upgradable

```

なお、Welcomeメッセージの最下部（"Last login:〜"）はpam\_lastlog.soが表示するログイン履歴です。

## Welcomeメッセージを表示しない方法

複数の案が考えられます。

Welcomeメッセージを表示しない方法

1. /etc/update-motd.d以下のScriptの先頭（Shebangの後）に"exit;"を追加
2. /etc/update-motd.d以下のScriptの実行権限を落とす
3. $/HOME/.hushloginを追加

一番目の方法は、各Scriptに"exit;"を追加する作業が面倒な一方で、Scriptに"exit;"を付与する／付与しない事によって、Welcomeメッセージの表示したい情報／非表示にしたい情報を制御できます。

二番目の方法は、私のように横着する人向けで、全てのScriptを実行できなくする事によって、Welcomeメッセージを全て非表示にします。

以下、実行権限の落とし方の例です。

```
$ sudo chmod -x /etc/update-motd.d/*

```

一番目と二番目の方法は、システム全体に影響があります。複数人のユーザがアクセスするサーバの場合は、これらの方法を実施する前に他のユーザに迷惑がかからないかを判断した方が好ましいです。

最後の方法は、ユーザ単位でWelcomeメッセージを非表示にする方法です。/etc/update-motd.d以下のScriptを編集しないため、なるべくScriptを初期状態にしたい人向けです。ただし、ユーザ単位で.hushloginを追加する手間が発生します。

以下、.hushloginの追加方法例です。

```
(注釈)：サーバ内で.hushloginを追加
nao@asagi:~$ touch ${HOME}/.hushlogin
nao@asagi:~$ exit           (注釈)：ログアウト
logout
Connection to asagi closed.

(注釈)：再度、サーバに接続
nao@nao:$ ssh nao@asagi
nao@asagi:~$                         (注釈)：Welcomeメッセージが出ない

```
