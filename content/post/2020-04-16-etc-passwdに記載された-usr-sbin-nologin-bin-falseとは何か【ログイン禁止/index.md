---
title: "/etc/passwdに記載された/usr/sbin/nologin, /bin/falseとは何か【ログイン禁止】"
type: post
date: 2020-04-16
categories:
  - "linux"
tags:
  - "debian"
  - "login"
  - "shell"
cover:
  image: images/login-3938429_640-1-min.jpg
  alt: "/etc/passwdに記載された/usr/sbin/nologin, /bin/falseとは何か【ログイン禁止】"
  hidden: false
---

## 前書き

先日、Rubyのコーディング練習がてらに、ユーザ情報を出力するコマンドの仕様をボンヤリと考えていました。

<blockquote class="twitter-tweet"><p dir="ltr" lang="ja">Rubyの練習用に「neofetchがシステムの情報出すなら、自分はユーザ情報を表示するコマンド作るか」と思ったが、既に類似仕様のfingerコマンド(<a href="https://t.co/epoOGD4zlC">https://t.co/epoOGD4zlC</a>)があった。<br>そりゃ、あるよね。</p>— Nao (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1250631227733708802?ref_src=twsrc%5Etfw">April 16, 2020</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

出力すべきユーザ情報には「ユーザが使用しているログインシェル」を含めようと考え、「/etc/passwd」を確認したら、ログインシェルを記載するセクションに予想外の記述がありました。その記述とは、「/usr/sbin/nologin」および「/bin/false」です。明らかに、シェルではありません。

結論から言えば、nologinコマンドとfalseコマンドはユーザログインを拒否するための記述です。システムユーザ（デーモンなど）がログインシェルを使用できる場合、セキュリティリスクがあるため、nologin／falseコマンドでログインを拒否します。

私が細かな仕様を知らなかったため、本記事ではnologin／falseコマンドの仕様に関する調査結果を説明します。

## 検証環境

```
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 10 (buster) x86_64 
 ,$$P'              `$$$.     Kernel: 4.19.67 
',$$P       ,ggs.     `$$b:   Uptime: 5 days, 2 hours, 46 mins 
`d$$'     ,$P"'   .    $$$    Packages: 3805 (dpkg) 
 $$P      d$'     ,    $$P    Shell: fish 3.0.2 
 $$:      $$.   - ,d$$'    Resolution: 2560x1080 
 $$;      Y$b._   _,d$P'      DE: Cinnamon 3.8.8 
 Y$$.    `.`"Y$$$$P"'         WM: Mutter (Muffin) 
 `$$b      "-.__              WM Theme: (Albatross) 
  `Y$$                        Theme: Blackbird [GTK2/3] 
   `Y$$.                      Icons: hicolor [GTK2/3] 
     `$$b.                    Terminal: gnome-terminal 
       `Y$$b.                 CPU: AMD Ryzen 7 3800X 8- (16) @ 3.900GHz 
          `"Y$b._             GPU: NVIDIA NVIDIA Corporation TU107 
              `"""            Memory: 6818MiB / 64404MiB
```

## 前提：/etc/passwdの仕様

「/etc/passwd」は、ユーザ情報を管理しているファイルであり、下表に示す情報が保管されています。1行が1ユーザに対応し、下表の番号が小さいフィールドから順番に記載されています。フィールド間の区切り文字には":"が用いられます。

| **フィールド** | **説明** |
| --- | --- |
| 第1フィールド | ユーザ名 |
| 第2フィールド |   パスワード用のフィールドであり、記載内容は以下のいずれか。   x：/etc/shadow にハッシュ化パスワードを記載する方式   \*：アカウントを一時的に無効化   無記入：パスワード設定なし   |
| 第3フィールド | ユーザ番号（UID） |
| 第4フィールド | グループ番号（GID） |
| 第5フィールド | コメント（ユーザのフルネームや役割） |
| 第6フィールド | ホームディレクトリのPATH |
| 第7フィールド | ログインシェル（絶対PATH） |

以下に、/etc/passwdの記載例を示します。

```
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin

```

## nologinコマンドの仕様

nologinコマンドを実行した場合、ログインを試みたユーザが利用不可である旨のメッセージが出力されます。

```
$ sudo nologin
This account is currently not available.

```

より詳細な説明は、manページ（"$ man 8 nologin"で表示するページ）に記載されています。アカウントが利用不可能な旨をメッセージで知らせるため、"politely refuse a login　(ログインを丁寧に拒否する)"と説明されているのでしょう。

```
NOLOGIN(8)                            System Management Commands                           NOLOGIN(8)

NAME
       nologin - politely refuse a login

SYNOPSIS
       nologin

DESCRIPTION
       The nologin command displays a message that an account is not available and exits non-zero. It
       is intended as a replacement shell field for accounts that have been disabled.

       To disable all logins, investigate nologin(5).

SEE ALSO
       login(1), nologin(5).

HISTORY
       The nologin command appeared in BSD 4.4.

shadow-utils 4.5                              07/27/2018                                   NOLOGIN(8)

```

manには、「nologinコマンドは非0（失敗）の値を返して終了する」と記載されているので、実装を確認します。

## nologinコマンドの実装

まず、ソースコードの取得方法を示し、その後にコードを示します。

```
(注釈)：どのパッケージが、nologinコマンドを提供するかを確認
$ apt-file -F search /usr/sbin/nologin
login: /usr/sbin/nologin 

(注釈)：nologinコマンドのソースコードを取得
$ apt source login

(注釈)：取得したソースを確認。
　　　 バイナリパッケージ名はloginだが、ソースパッケージ名はshadow。
$ ls
shadow-4.5  shadow_4.5-1.1.debian.tar.xz  shadow_4.5-1.1.dsc  shadow_4.5.orig.tar.xz

(注釈)：取得したソースの表示
$ cat shadow-4.5/src/nologin.c

```

```
// BSDライセンスの記述は省略

#include 

#ident "$Id$"

#include 
#include 
#include 
#include 

int main (void)
{
	const char *user, *tty;

	tty = ttyname (0);
	if (NULL == tty) {
		tty = "UNKNOWN";
	}
	user = getlogin ();
	if (NULL == user) {
		user = "UNKNOWN";
	}
	openlog ("nologin", LOG_CONS, LOG_AUTH);
	syslog (LOG_CRIT, "Attempted login by %s on %s", us、er, tty);
	closelog ();

	printf ("%s", "This account is currently not available.\n");

	return EXIT_FAILURE;
}

```

上記の処理は、大したことをしていません。

- ttyname()で端末デバイス名（例：/dev/pts/2）を取得
- getlogin()でユーザ名（例：nao）を取得
- syslog()で、ユーザがログインを試みた記録を端末名、ユーザ名付きで保存
- 固定文字列"This account is currently not available."を出力

[syslog()](https://nxmnpg.lemoda.net/ja/3/syslog)は、システムからのメッセージをロギングする仕組みを利用しており、メッセージの格納先は「/etc/syslog.conf」もしくは「/etc/rsyslog.conf」の設定に従って変わります。基本的なログ出力先は「/var/log」以下であり、認証系の場合は「/var/log/auth.log」が格納先です。

実際に確認した所、以下のログが「/var/log/auth.log」に残っていました。

```
$ sudo cat /var/log/auth.log | grep Att
Apr 16 20:24:01 debian nologin: Attempted login by nao on /dev/pts/1

```

## Debianはnologinコマンドのログイン拒否メッセージを変更不可

色々なサイトで、「/etc/nologin.txtを編集すれば、ログイン拒否メッセージを変更可能」と書かれています。しかし、前述の実装の限り、ログイン拒否メッセージは固定の文字列です。

```
	printf ("%s", "This account is currently not available.\n");

```

調査した結果、Debianのnologinコマンドは「/etc/nologin.txt」を確認しませんが、[Linux Kernel Organization](https://en.wikipedia.org/wiki/Linux_Kernel_Organization)が配布している[util-linux](https://github.com/karelzak/util-linux)版は「/etc/nologin.txt」を確認するようです（[util-linux版ソースコード](https://github.com/karelzak/util-linux/blob/master/login-utils/nologin.c)を参照）

\[the\_ad id="598"\]

## falseコマンドの仕様

falseコマンドは、失敗を意味する値（1）を返して終了します。ログイン用のコマンドではなく、coreutilsパッケージが提供するコマンドの一つです。

メッセージも出さずに終了するため、nologinコマンドよりやや不親切です。しかし、悪意を持ったユーザが連続ログインを試みた際のシステム負荷はfalseコマンドの方が低く、その点でメリットがあります。

```
$ false       (注釈)：実行しても何も表示されない

(注釈)：終了ステータスの確認
$ echo $?
1

```

## falseコマンドの実装

falseコマンドの実装方法は、トリッキーで面白いです。coreutils-8.30/src/false.cに実装がありますが、たったの２行です。

```
(注釈)：どのパッケージが、falseコマンドを提供するかを確認
$ apt-file -F search /bin/false
coreutils: /bin/false         

(注釈)：falseコマンドのソースコードを取得
$ apt source coreutils

(注釈)：取得したソースの表示
$ cat coreutils-8.30/src/false.c

```

```
#define EXIT_STATUS EXIT_FAILURE
#include "true.c"

```

#incldeはファイルを展開するだけなので、true.cファイルを#include行に展開しています。true.cはtrueコマンド用ソースコードであり、trueコマンドはfalseと逆の挙動をします。つまり、必ず成功を意味する値（0）を返して終了します。

true.cファイル内では、EXIT\_STATUSが未定義の場合、「#define EXIT\_STATUS EXIT\_SUCCESS」と定義しています。

```
#ifndef EXIT_STATUS              
# define EXIT_STATUS EXIT_SUCCESS
#endif                           

```

つまり、true.cをコンパイルした場合はEXIT\_STATUSは成功になり、false.cをコンパイルした場合はEXIT\_STATUSは失敗となります。読めばすぐ理解できますが、このような実装は初めて見ました。

## まとめ

nologin／falseコマンドの仕様差異

- nologin／falseコマンドともに、セキュリティ対策で用いるログイン拒否コマンド。
- nologinコマンドは、ログイン拒否メッセージ（Debian版は変更不可）を出力する。
- falseコマンドは、失敗ステータスを返すだけで、メッセージを出力しない。
