---
title: "【LPICで見た】/etc/motdの内容を出力しているのは誰？【答え:sshd】"
type: post
date: 2020-12-01
categories:
  - "linux"
tags:
  - "codereading"
  - "debian"
  - "linux"
  - "lpic"
  - "motd"
cover:
  image: "images/typewriter-1170657_640-min.jpg"
  alt: "【LPICで見た】/etc/motdの内容を出力しているのは誰？【答え:sshd】"
  hidden: false
---

###  前書き：Message Of The Dayファイルとは

LPIC受験者は、よくご存知の/etc/motd (Message Of The Day)ファイル。

ユーザがLinuxサーバにsshログインした際に、/etc/motdファイルの内容がターミナル上に表示されます。

例えば、Raspberry Piでは、/etc/motdファイルに以下の内容が記載されています。

```
The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
```

Raspberry Piにsshログインすると、以下のように/etc/motdファイルの内容が出力されます。

```
(注釈)：Debian PCからsshでRaspberry Piにログイン（mortorheadはホスト名）
nao@debian:~ $ ssh mortorhead 

Linux motorhead 5.4.72-v8+ #1356 SMP PREEMPT Thu Oct 22 13:58:52 BST 2020 aarch64

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
Last login: Tue Dec  1 20:59:07 2020 from 192.168.1.36

Wi-Fi is currently blocked by rfkill.
Use raspi-config to set the country before use.

lemmy@motorhead:~ $    (注釈) sshログイン直後のプロンプト

```

/etc/motdファイルの主な用途（記載内容）は、以下がパッと思いつきます。

- チームメンバへの連絡を記載
- サーバを見分けるためのロゴ追加
- イタズラ、負の感情の吐露（私はコレをよくします）

で、不意に「**/etc/motdファイルの内容をターミナルに表示しているのは誰よ」**と疑問が湧いたので、調査した内容を本記事で紹介します。Debian環境を前提とします。

本記事で説明する内容

- /etc/motdファイルの作成者
- /etc/motdを表示する人
- /etc/motdメッセージを非表示にする方法

### /etc/motdファイルはbase-filesが生成

そもそも、/etc/motdファイルは誰が作るのでしょうか。

特定ファイルが収録されているパッケージを教えてくれるapt-fileコマンドを使用すると、OSの基本的なシステムファイルを提供するbase-filesパッケージがヒットします。

```
$ apt-file -F search /etc/motd
(注釈) 完全一致の-Fオプションでは、何も表示されない。

(注釈) 検索条件を緩めると大量にヒットする
$ apt-file search motd
aide-common: /usr/share/aide/config/aide/aide.conf.d/31_aide_pam_motd
alien-arena-data: /usr/share/games/alien-arena/arena/motd.txt
anope: /etc/anope/services.motd
ansible: /usr/lib/python3/dist-packages/ansible/modules/storage/netapp/na_ontap_motd.py
ansible-doc: /usr/share/doc/ansible-doc/html/modules/na_ontap_motd_module.html
assaultcube-data: /usr/share/games/assaultcube/config/motd_en.txt
atheme-services: /usr/share/doc/atheme-services/examples/atheme.motd.example
base-files: /etc/update-motd.d/10-uname
base-files: /usr/share/base-files/motd         ★お目当てのファイル
：
：(省略)

```

base-filesパッケージを取得して中身を確認すると、/etc/motdファイルの原型が見つかります。しかし、一部の情報（#OSNAME#）が変数の状態です。

```
(注釈) base-fileパッケージのソースコード取得
$ apt source base-files

(注釈)motdファイル（原型）の確認
$ cd base-files-10.3+deb10u6/
$ cat share/motd 

The programs included with the Debian #OSNAME# system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian #OSNAME# comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.

```

上記のmotdファイルで登場した#OSNAME#を書き換えてくれる人は、base-filesパッケージ内のDebianパッケージ生成スクリプトdebian/rules（中身はMakefile）です。sedコマンドで#OSNAME#文字列を置換しています。

```
#!/usr/bin/make -f

OSNAME = "GNU/`uname | sed -e 's/GNU\///'`"
ifeq ($(DEB_HOST_GNU_SYSTEM),linux)
  OSNAME=GNU/Linux
endif
ifeq ($(DEB_HOST_GNU_SYSTEM),gnu)
  OSNAME=GNU/Hurd
endif

(省略)
	sed -e "s#&$(OSNAME)&g" share/motd     > $(DESTDIR)/usr/share/base-files/motd

```

### motdを表示する人 = sshd (openssh-server)

では、本題である/etc/motdファイルの内容を表示する人は誰でしょうか。

皆さんの予想通り、犯人はsshd（openssh-serverパッケージ）でした。

先ほどと同様に、aptコマンドでopenssh-serverパッケージを取得して中身を確認した所、openssh-7.9p1/session.cに関数do\_motd()が定義されていました。

以下に示す通り、do\_motd()の中で/etc/motdファイルの内容を表示しています。

```
/*
 * Display the message of the day.
 */
void
do_motd(void)
{
	FILE *f;
	char buf[256];

	if (options.print_motd) {
#ifdef HAVE_LOGIN_CAP
		f = fopen(login_getcapstr(lc, "welcome", "/etc/motd",
		    "/etc/motd"), "r");
#else
		f = fopen("/etc/motd", "r");
#endif
		if (f) {
			while (fgets(buf, sizeof(buf), f))
				fputs(buf, stdout);
			fclose(f);
		}
	}
}

```

### motdメッセージを非表示にする方法

前述したopenssh-7.9p1/session.cを読んでいた時に気づきましたが、${HOME}/.hushloginファイルが存在する場合は、ログイン時にmotdメッセージを出力しないようです。

```
/*
 * Check for quiet login, either .hushlogin or command given.
 */
int
check_quietlogin(Session *s, const char *command)
{
	char buf[256];
	struct passwd *pw = s->pw;
	struct stat st;

	/* Return 1 if .hushlogin exists or a command given. */
	if (command != NULL)
		return 1;
	snprintf(buf, sizeof(buf), "%.200s/.hushlogin", pw->pw_dir);
#ifdef HAVE_LOGIN_CAP
	if (login_getcapbool(lc, "hushlogin", 0) || stat(buf, &st) >= 0)
		return 1;
#else
	if (stat(buf, &st) >= 0)
		return 1;
#endif
	return 0;
}

/* administrative, login(1)-like work */
void
do_login(struct ssh *ssh, Session *s, const char *command)
{
       /* 省略 */

	if (check_quietlogin(s, command))
		return;

	display_loginmsg();

	do_motd();     /* ~/.hushloginが存在すると、ここまで達しない */
}

```

恐らく、ssh認証方式によってmotdメッセージの出力有無が決まっているのでしょう（この内容はLPIC出題内容にあったかどうか忘れました）

### 補足：Debian 8以降やUbuntuにおけるmotdの仕組み

motdは、PAMモジュールを使用して表示されるケースもあります。興味がある方は、以下の記事を確認してください。

- [Ubuntu (20.04)へsshログインした際に表示されるWelcomeメッセージの仕組みと表示しない方法](https://debimate.jp/post/2021-08-14-ubuntu-20-04%E3%81%B8ssh%E3%83%AD%E3%82%B0%E3%82%A4%E3%83%B3%E3%81%97%E3%81%9F%E9%9A%9B%E3%81%AB%E8%A1%A8%E7%A4%BA%E3%81%95%E3%82%8C%E3%82%8Bwelcome%E3%83%A1%E3%83%83%E3%82%BB%E3%83%BC%E3%82%B8/)
