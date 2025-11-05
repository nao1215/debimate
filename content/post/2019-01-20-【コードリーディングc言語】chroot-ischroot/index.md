---
title: "コードリーディング(C言語)：chroot / ischroot"
type: post
date: 2019-01-20
categories:
  - "linux"
tags:
  - "codereading"
  - "command"
  - "c言語"
  - "debian"
  - "linux"
cover:
  image: images/chroot-e1547979094502.gif
  alt: "コードリーディング(C言語)：chroot / ischroot"
  hidden: false
---

## 前書き

本記事は、以下のコマンドのコードリーディング結果を記載しています。

- プロセスおよび子プロセスの(見かけ上の)ルートディレクトリを変更する[chroot](https://ja.wikipedia.org/wiki/Chroot)
- プロセスがchroot環境(jail環境)で動作しているかを検出する[ischroot](https://www.cs.drexel.edu/cgi-bin/manServer.pl/usr/share/man/man1/ischroot.1)

![](images/ischroot_chroot.png)

上記のコマンドをリーディング対象とした理由は、以下の2点です。

- 「見かけ上のルートディレクトリ変更」の実現方法を知りたかった。
- コード規模が小さい(一日で読めそう)。

一つ目の理由に関しては、仕事でchroot環境を使う機会があり、そこで興味を持ちました。ちなみに、chrootで制限された環境は、chroot監獄と呼ばれる事があります。chrootは、「システム環境を破壊する可能性のあるプログラムをテストする環境」や「ライブラリの依存を確認するためにパッケージを制限した環境」を提供できます。しかし、2019年現在ではこのような用途は、より簡便な[Docker](https://www.docker.com/)によるコンテナ環境がメインになりつつあります。

二つ目のコード規模に関しては、下表にstep数を記載します。計測対象は、coreutilsに含まれるchroot.c、debianutils-4.4に含まれるischroot.cに対して、[clocコマンド](https://github.com/AlDanial/cloc)を用いて計測しています。調査した期間が少し前なので、パッケージバージョンが古いです。しかし、基本的な仕組みを知るには問題がないので、再調査はしませんでした。

| ファイル名 | step数 | 提供パッケージ |
| --- | --- | --- |
| chroot.c | 305step | coreutils-8.23 |
| ischroot.c | 159step | debianutils-4.4 |

## 検証環境

- [Debian8.6(64bit)](https://www.debian.org/index.ja.html)
- [coreutils-8.23](https://packages.debian.org/jessie/coreutils)
- [debianutils-4.4](https://packages.debian.org/jessie/debianutils)

## chroot実装調査：coreutilesパッケージの取得

Debian環境下で、coreutilesパッケージ(ソースコード、パッチ)を取得する方法は以下の通りです。Debianのバージョンが異なる場合でも、同じ方法で取得できます。

```
$ apt-get source coreutils        (注釈) カレントディレクトリにソースコードをダウンロード
$ ls
  coreutils-8.23  coreutils_8.23-4.diff.gz
  coreutils_8.23-4.dsc  coreutils_8.23.orig.tar.gz

$ tree coreutils-8.23 -L 1 -d     (注釈) coreutile-8.23以下のディレクトリを一階層分だけ表示
  coreutils-8.23
  ├── build-aux
  ├── debian
  ├── doc
  ├── gnulib-tests
  ├── lib
  ├── m4
  ├── man
  ├── old
  ├── po
  ├── src
  └── tests

$ cd coreutils-8.23/src           (注釈) coreutilsのソースコードが格納されたディレクトリへ移動
$ ls | grep -E "chroot" 　　　　　 (注釈) chrootに関するファイルのみを表示
  chroot.c
```

## chroot実装調査：coreutils内ソースファイルの共通初期化処理

まず、coreutils内のソースファイルに共通する初期化処理に関して、chrootのソースファイルを例として説明します。説明対象は、coreutiles-8.23/src/chroot.cです。

```
int
main (int argc, char **argv)
{
  int c;

  /* Input user and groups spec.  */
  char *userspec = NULL;
  char const *username = NULL;
  char const *groups = NULL;

  /* Parsed user and group IDs.  */
  uid_t uid = -1; 
  gid_t gid = -1; 
  GETGROUPS_T *out_gids = NULL;
  size_t n_gids = 0;

  initialize_main (&argc, &argv);
  set_program_name (argv[0]);
  setlocale (LC_ALL, "");
  bindtextdomain (PACKAGE, LOCALEDIR);
  textdomain (PACKAGE);

  initialize_exit_failure (EXIT_CANCELED);
  atexit (close_stdout);
  (省略)
```

initialize\_main()は、DEC(現HP)が開発した[Virtual Memory System(OS、以下VMS)](https://ja.wikipedia.org/wiki/OpenVMS)上で、リダイレクト・ワイルドカードの仕組みを実現するための関数(マクロ)です。coreutiles-8.23/src/system.hにおける定義の通り、通常(Debian)では何も処理を実施しないマクロになっています。

```
#ifndef initialize_main
# define initialize_main(ac, av)
#endif
```

この点に関しては、[stackoverflow](http://stackoverflow.com/questions/19276701/what-does-initialize-main-argc-argv-do)に説明がありました。以下に和訳を記します。原文は、リンク先で確認できます。 

> 次のステップは、リダイレクトとワイルドカードを理解する事です。  
> Linuxやunix系統のその他のメンバーは、
> 
> cat foo\* > /tmp/foolist
> 
> のようなコマンドはfoo\*にマッチする内容を引数argvとして、catコマンドの関数main()をcallします。  
> 関数main()に実行が移される前に、出力ファイル/tmp/foolistは既に標準出力として開かれています。  
> VMSは、このような動作をしません。  
> catコマンドは拡張されていない文字列"foo\*"を探し、リダイレクト演算子">"をargvに格納します。  
> そのため、ユーティリティ自体(cat)がリダイレクト(出力ファイルを開く事)および  
> ワイルドカード("foo\*"を"foo1"、"foo2"、"foo3"に置換する事)を実施しなければなりません。

 なお、VMS上でリダイレクトとワイルドカードを実行する処理は、system.hに定義されていません。[GNU版core-utiles-8.26](http://ftp.gnu.org/gnu/coreutils/)のsystem.hでは、OS/2向けの処理(下記)が実装されていました。GNU版はVMS上で動かす可能性があるが、Debian版は動かす可能性がないため、initialize\_main()の定義に差があるのではないかと推測しました(Changelogにはこの点に関する記載なし)。

```
#ifndef initialize_main
# ifndef __OS2__
#  define initialize_main(ac, av)
# else
#  define initialize_main(ac, av) \
     do { _wildcard (ac, av); _response (ac, av); } while (0)
# endif
#endif
```

続いて、set\_program\_name()は、変数program\_name、program\_invocation\_nameに、コマンドライン引数"argv\[0\]=プログラム名(chroot)"を代入します。

一般的に、argv\[0\]にはプログラム名が格納されていますが、以下の条件ではその限りではありません。

- 関数main()をプログラム内からコールした場合(例：再帰的なmain()のコール)
- argc=0の場合(仕様として、argv\[0\]=NULLとなる)

上記の場合に備えたNULLチェックは、以下のように実装されています。argv\[0\]がNULLの場合は標準エラーにメッセージを出力した後に、プログラムを異常終了させます。

```
void
set_program_name (const char *argv0)
{
  (省略)
  /* Sanity check.  POSIX requires the invoking process to pass a non-NULL
     argv[0].  */
  if (argv0 == NULL)
    {
      /* It's a bug in the invoking program.  Help diagnosing it.  */
      fputs ("A NULL argv[0] was passed through an exec system call.\n",
             stderr);
      abort ();
    }
  (省略)
}
```

NULLチェックを終えた後、プログラム名を代入する前に、set\_program\_name()にて文字列を整形します。例として、プログラム名が"/.libs/lt-\*"の場合、"/.libs/lt-"を取り除いた文字列を代入します。

このようなプログラム名は、libtoolを使用してビルドを行った場合に命名されます。[libtool](https://autotools.io/libtool/wrappers.html)を用いてビルドした共有ライブラリは、異なるOSで共有オブジェクトを扱う際の制約を回避するように、ラッパースクリプトが生成されます。そして、実際にリンクされた(ラップされた)実行可能ファイルは.libsディレクトリ内で、プレフィックス"lt-"が付与された名称で存在します。　

以下が、文字列整形部分の処理になります。

```
void
set_program_name (const char *argv0)
{
  (省略)
  const char *slash;
  const char *base;
  (省略)

  slash = strrchr (argv0, '/');                  // argv0の末尾にある"/"へのポインタを返す
  base = (slash != NULL ? slash + 1 : argv0);    // argv0に"/"が含まれていなければargv0、
                                                 // 含まれていればslashの先頭("/")の次を指すポインタを代入。

  // 以下のif文では、baseから"/.libs/"および"lt-"を取り除いた文字列を
  // argv0に代入する。
  if (base - argv0 >= 7 && strncmp (base - 7, "/.libs/", 7) == 0)
    {
      argv0 = base;
      if (strncmp (base, "lt-", 3) == 0)
        {
          argv0 = base + 3;
          /* On glibc systems, remove the "lt-" prefix from the variable
             program_invocation_short_name.  */
#if HAVE_DECL_PROGRAM_INVOCATION_SHORT_NAME
          program_invocation_short_name = (char *) argv0;
#endif
        }
    }
    program_name = argv0;
  (省略)
}
```

初期化処理のsetlocale()からtextdomain()までは、プログラムの国際化・地域化に関する設定を行います。具体的には、[locale](http://e-words.jp/w/%E3%83%AD%E3%82%B1%E3%83%BC%E3%83%AB.html)を適切に設定する事により、文字/日付/時刻/単位/通貨などを特定の地域に特化した状態でプログラムを実行できるようにします。

プログラムのローカライズの流れは、以下の順番で行われます(詳細は後述)。

1. プログラムのメッセージ文を翻訳用関数gettext()に対応した形式で記述
2. 前手順1.のメッセージ文に対する翻訳文をカタログファイル(.po、書式あり)に記載
3. 前手順2.のカタログファイルをmsgfmtコマンドでコンパイルし、バイナリ(.mo)を生成。バイナリは"ドメイン名.mo"となり、/usr/share/locale/_/LC\_MESSAGES以下に格納されます_
4. _プログラム中にlocaleに関する初期化を記述_

_上記の手順4. に当たる内容がsetlocale()からtextdomain()までとなります。  
まず、setlocale()は、プログラムに環境変数(LC\__)を参照させ、locale情報を設定します。  
挙動としては、環境変数LC\_ALLもしくはLANGが設定されていれば全てのカテゴリでその設定を使用し、各カテゴリ(例：LC\_TIME)に設定値が入っていれば、そのカテゴリはその設定値を優先的に使用します。

  
なお、システムの現在のlocale情報を参照するには、以下のようにlocaleコマンドを実行します(出力の左辺値がカテゴリ)。

```
$ locale                 # ja_JP.UTF-8 = 日本語
  LANG=ja_JP.UTF-8
  LANGUAGE=
  LC_CTYPE="ja_JP.UTF-8"
  LC_NUMERIC="ja_JP.UTF-8"
  LC_TIME="ja_JP.UTF-8"
  LC_COLLATE="ja_JP.UTF-8"
  LC_MONETARY="ja_JP.UTF-8"
  LC_MESSAGES="ja_JP.UTF-8"
  LC_PAPER="ja_JP.UTF-8"
  LC_NAME="ja_JP.UTF-8"
  LC_ADDRESS="ja_JP.UTF-8"
  LC_TELEPHONE="ja_JP.UTF-8"
  LC_MEASUREMENT="ja_JP.UTF-8"
  LC_IDENTIFICATION="ja_JP.UTF-8"
  LC_ALL=
```

\[the\_ad id="598"\]

次に、bindtextdomain()は、ドメイン名"PACKAGE"のカタログディレクトリを"LOCALEDIR"に設定します。具体的には、変数PACKAGEはMakefile中に"coreutils"と定義され、変数LOCALEDIRはlib/configmake.h中に"/usr/share/locale"と定義されています。

例えば、日本語環境のcoreutilsがメッセージカタログを参照する場合は、"/usr/share/locale/ja/LC\_MESSAGES/coreutils.mo"を参照する事となります。

 最後に、textdomain()はドメイン名を"PACKAGE=coreutils"に設定します。  
ここで指定したドメイン情報用いて、gettext()がメッセージを適切なlocaleに翻訳(置換)します。gettext()は、エイリアスとして"\_"が与えられているため、メッセージの前の"\_"はgettext()と同等です。

例えば、chroot.cの402行目の`error (EXIT_CANCELED, errno, _("failed to set group-ID"));`は、その翻訳が以下のpoファイルに定義されています。

```
#: src/chroot.c:402
#, c-format
msgid "failed to set group-ID"                                                       
msgstr "グループ ID の設定に失敗しました"

(注釈)
poファイル中の"#:"はメッセージが存在するソースファイル名と行番号、
"#,"はprintfなどの書式付き文字列用のフラグ、msgidは翻訳対象文、msgstrは翻訳後の文章です。
```

残りのinitialize\_exit\_failure()からatexit()までは、プログラム終了に関する処理です。  
initialize\_exit\_failure()では[終了コード](https://ja.wikipedia.org/wiki/%E7%B5%82%E4%BA%86%E3%82%B9%E3%83%86%E3%83%BC%E3%82%BF%E3%82%B9)を管理するグローバル変数exit\_failureの初期化、atexit()ではプロセス終了時に自動実行するハンドラ(今回はclose\_stdout())を登録します。

一般論として、atexit()には、以下の2つの欠点があります。

- exit()の引数である終了コードを参照できない事
- 登録したハンドラ引数を渡せない事

これらの欠点を解消するために、グローバル変数exit\_failureで終了コードを管理し、  
close\_stdout()内で終了コード(exit\_failure)を引数として\_exit()をコールします。  
なお、可搬性はありませんが、ハンドラ登録と引数が渡せる[on\_exit()](https://linuxjm.osdn.jp/html/LDP_man-pages/man3/on_exit.3.html)も存在します。

ハンドラとして登録されたclose\_stdout()の定義は、以下の通りです。  
close\_stdout()を実行するプログラムは、終了する前にstdoutおよびstderr以外の  
ストリームをフラッシュする必要があります。この理由は、\_exit()がRuntimeライブラリのクリーンアップ処理を実行しないため、ライブラリが使用したストリームバッファが必ずフラッシュされるという保証がないからです。

```
void
close_stdout (void)
{
  if (close_stream (stdout) != 0
      && !(ignore_EPIPE && errno == EPIPE))
    {
      char const *write_error = _("write error");
      if (file_name)
        error (0, errno, "%s: %s", quotearg_colon (file_name),
               write_error);
      else
        error (0, errno, "%s", write_error);

      _exit (exit_failure);
    }

   if (close_stream (stderr) != 0)
     _exit (exit_failure);
}      

```

## chrootのオプション処理

初期化処理に続いて、chrootが受け取るオプションの取り扱い方法を説明します。実装を説明する前に、chrootの書式およびオプションを以下に示します。

```
[書式]
使用法: chroot [OPTION] NEWROOT [COMMAND [ARG]...]
または: chroot OPTION
```

| オプション | 説明 |
| --- | --- |
| \--userspec=USER:GROUP | 使用するユーザーおよびグループ (ID または名前) を指定します |
| \--groups=G\_LIST | g1,g2,..,gN 形式で追加のグループを指定します |
| \--help | chrootの使い方を表示します |
| \--version | バージョン情報を表示します |

上表のオプションを受け取る処理は、以下の通りです(初期化処理のatexit()の続き)。

```
while ((c = getopt_long (argc, argv, "+", long_opts, NULL)) != -1) 
    {   
      switch (c) 
        {   
        case USERSPEC:
          {   
            userspec = optarg;
            /* Treat 'user:' just like 'user'
               as we lookup the primary group by default
               (and support doing so for UIDs as well as names.  */
            size_t userlen = strlen (userspec);
            if (userlen && userspec[userlen - 1] == ':')
              userspec[userlen - 1] = '\0';
            break;
          } 

        case GROUPS:
          groups = optarg;
          break;

        case_GETOPT_HELP_CHAR;

        case_GETOPT_VERSION_CHAR (PROGRAM_NAME, AUTHORS);

        default:
          usage (EXIT_CANCELED);
        }   
    }   

  if (argc <= optind)
    {   
      error (0, 0, _("missing operand"));
      usage (EXIT_CANCELED);
    }  
```

オプション解析では、全オプションを解析し終わるまでwhileループを回し、[getopt\_long()](http://www.mm2d.net/main/prog/c/getopt-03.html)で指定したオプションの引数をchar型のuserspec/groupsに格納します。最後に、解析できなかったオプションがあれば、usageを表示してプログラムを終了します。

なお、getopt\_long()は、ハイフン２つ＋複数文字のオプション(例：--help)を解析します。getopt\_long()は、返り値としてoption構造体で指定した値(後述)を返し、  
変数optindは解析のたびに1インクリメント、変数optargはオプション引数を保持しています。

getopt\_long()の第4引数long\_opts(option構造体)の定義は、以下の通りです。

```
struct option                                                                                   
{
  /* has_argは列挙型にできません。
    コンパイラによっては、int型であるとみなす全てのコードで型不一致が発生する事があります。　*/
  const char *name; // ロングオプション名
  int has_arg; // 引数の有無(定数no_argument、required_argument、optional_argumentのいずれか)
  int *flag;   // 判定結果の格納先
  int val;     // 判定結果として返す値
};
```

```
static struct option const long_opts[] =                                                        
{
  {"groups", required_argument, NULL, GROUPS},
  {"userspec", required_argument, NULL, USERSPEC},
  {GETOPT_HELP_OPTION_DECL},    // coreutilsのテンプレであるため、system.h内で定数定義
  {GETOPT_VERSION_OPTION_DECL}, // 同上
  {NULL, 0, NULL, 0}
};
```

## ルートディレクトリの変更処理

ルートディレクトリの変更処理を説明します。この変更処理前にはuid/gidを取得する処理、変更後には変更後のルートに移動する処理を行います。

以下に該当処理を示します。英語コメントは和訳しています。

```
  /* 実際にルートを変更する場合にのみ、chroot固有のアクションを実行します。
     主な違いは、作業ディレクトリを変更しない事です。*/
  /* (元に戻す - 無条件に実行する) */
  if (1)
    {
      /* ユーザーとグループを2度探す必要があります。
        - ひとつ目は、chrootの外部で、潜在的に必要なpasswd/group解析プラグイン(例：NSS)をロードする場合。
          (補足)NSS(Name Service Switch)は、システムが使用する各種情報の検索順を指定するために使用され、
               検索順を指定するファイルは、通常/etc/nsswitch.confです。
        - ふたつ目は、chrootの内部でIDが異なる際に解析をやり直す場合。
          chroot内部での解析は、chrootコマンド自体が--userオプションをサポートしている事に
          対する主な理由になります。*/
      if (userspec)
        ignore_value (parse_user_spec (userspec, &uid, &gid, NULL, NULL));

      /* gidが指定されていない場合は、これを実行してください。
         getgroupsで使用するためのユーザー名も参照してください。*/
      if (uid_set (uid) && (! groups || gid_unset (gid)))
        { 
          const struct passwd *pwd;
          if ((pwd = getpwuid (uid)))
            { 
              if (gid_unset (gid))
                gid = pwd->pw_gid;
              username = pwd->pw_name;
            }
        }

      if (groups && *groups)
        ignore_value (parse_additional_groups (groups, &out_gids, &n_gids,
                                               false));
      (省略)

      if (chroot (argv[optind]) != 0)
        error (EXIT_CANCELED, errno, _("cannot change root directory to %s"),
               argv[optind]);

      if (chdir ("/"))
        error (EXIT_CANCELED, errno, _("cannot chdir to root directory"));
    }

```

まず、ignore\_value(parse\_user\_spec())において、uid、gidを取得します。ignore\_valueは、GCC(Ver3.4以降)において値をvoid型にキャストした際のWarningを抑制するマクロです。parse\_user\_specは、オプション引数を格納したuserspec(コロン区切りで、user名:group名を保持)より、USERNAME、uid、GROUPNAME、gidを抽出します。グループなしで区切りを指定した場合(例："user:")、指定ユーザーのログイングループが使用されます。

続く`if (uid_set (uid) && (! groups || gid_unset (gid)))`以下のブロックは、---groupsオプションで補助グループが指定されていない場合、もしくはparse\_user\_spec()でグループを解析できなかった場合に実行されます。その内容は、uidを基にパスワードファイルのエントリーを取得し(getpwuid()部分)、そのエントリーからグループ名(pwd->pw\_gid)、ユーザ名(pwd->pw\_name)を取得する事です。

前述のブロックとは異なり、続くparse\_additional\_groups()は、---groupsオプションで補助グループが指定されている場合に実行されます。parse\_additional\_groups()の第一引数(groups)には、カンマ区切りで補助グループが指定されています。この指定された補助グループ情報より、parse\_additional\_groups()は、gid\_t型の配列(out\_gids)、グループの個数(n\_gids、配列の要素数)を取得します。

最後に、chrootコマンドのメインとなる処理がchroot()、chdir("/")部分です。引数となるargv\[optind\]のチェック(指定されたPATHが存在するかのチェック)を行っていないため、不正なPATH(argv\[optind\])をchroot()に渡すと、エラーとなります。chroot()以降、プロセスが処理する絶対PATHは、chroot()の引数を開始点として処理されます。chdir()は、chroot()がワーキングディレクトリを変更しないため、代わりにワーキングディレクトリを変更します。

ちなみに、chdir("/")を行わなければ、容易にプロセスがjail環境から抜け出せます。ここまでソースコードを読んで分かった事ですが、

個人的な結論

chrootコマンド ≒ chrootシステムコール

## ルートディレクトリ変更後のコマンド処理

前提として、chrootコマンドは、その引数にjail環境で実行するコマンドを指定できます。コマンドの指定がない場合は、シェルによる対話型の処理が始まります。

ルートディレクトリの変更後のコマンド処理を以下に示します。

```
if (argc == optind + 1)
    {
      /* No command.  Run an interactive shell.  */
      char *shell = getenv ("SHELL");
      if (shell == NULL)
        shell = bad_cast ("/bin/sh");
      argv[0] = shell;
      argv[1] = bad_cast ("-i");
      argv[2] = NULL;
    }
  else
    {
      /* The following arguments give the command.  */
      argv += optind + 1;
    }

  /* Attempt to set all three: supplementary groups, group ID, user ID.
     Diagnose any failures.  If any have failed, exit before execvp.  */
  if (userspec)
    {
      char const *err = parse_user_spec (userspec, &uid, &gid, NULL, NULL);

      if (err && uid_unset (uid) && gid_unset (gid))
        error (EXIT_CANCELED, errno, "%s", err);
    }

  /* If no gid is supplied or looked up, do so now.
     Also lookup the username for use with getgroups.  */
  if (uid_set (uid) && (! groups || gid_unset (gid)))
    {
      const struct passwd *pwd;
      if ((pwd = getpwuid (uid)))
        {
          if (gid_unset (gid))
            gid = pwd->pw_gid;
          username = pwd->pw_name;
        }
      else if (gid_unset (gid))
        {
          error (EXIT_CANCELED, errno,
                 _("no group specified for unknown uid: %d"), (int) uid);
        }
    }

  GETGROUPS_T *gids = out_gids;
  GETGROUPS_T *in_gids = NULL;
  if (groups && *groups)
    {
      if (parse_additional_groups (groups, &in_gids, &n_gids, !n_gids) != 0)
        {
          if (! n_gids)
            exit (EXIT_CANCELED);
          /* else look-up outside the chroot worked, then go with those.  */
        }
      else
        gids = in_gids;
    }

  (省略)

  if ((uid_set (uid) || groups) && setgroups (n_gids, gids) != 0)
    error (EXIT_CANCELED, errno, _("failed to %s supplemental groups"),
           gids ? "set" : "clear");

  free (in_gids);
  free (out_gids);

  if (gid_set (gid) && setgid (gid))
    error (EXIT_CANCELED, errno, _("failed to set group-ID"));

  if (uid_set (uid) && setuid (uid))
    error (EXIT_CANCELED, errno, _("failed to set user-ID"));

  /* Execute the given command.  */
  execvp (argv[0], argv);

  {
    int exit_status = (errno == ENOENT ? EXIT_ENOENT : EXIT_CANNOT_INVOKE);
    error (0, errno, _("failed to run command %s"), quote (argv[0]));
    exit (exit_status);
  }
```

まず、最初のif(argc == optind + 1)〜elseのブロックを説明します。chrootコマンドにjail環境で実行したいコマンドが指定されていない場合(if文の方)、環境変数SHELLから使用するシェルを指定します。

環境変数SHELLが設定されていなければ、強制的にargv\[0\]は"/bin/sh"となります。argv\[1\]は、シェルを対話型で起動させるオプション("-i")を指定します。argv\[2\]にNULLを代入する理由は、execvp()でコマンド(argv\[0\])を実行する際に、引数のリストにNULL終端が必要なためです。

続くif(userspec)、if(uid\_set (uid) && (! groups || gid\_unset (gid)))、  
if(groups && \*groups)のブロックの内容は、再度uid/gid/補助グループを取得する処理になります。同じ処理を2回繰り返す理由は、元々のルート環境とjail環境では、uid/gidの設定が異なる可能性があるからです。具体的には、2つの環境において、/etc/passwd(uidの名前解決用ファイル)、/etc/group(gidの名前解決用ファイル)が同じ内容ではない可能性があります。そのため、2回ほどuid/gid/補助グループを取得する必要があります。

最後までの流れは、uid/gid/補助グループの設定、およびexecvp()によるコマンド実行です。必要なコマンド・ライブラリがなければ、エラー終了です。

\[the\_ad id="598"\]

## ischroot実装調査：debianutilsパッケージの取得

基本的に、debianutilsパッケージの取得は、coreutilsの取得と同じです。

```
$ apt-get source debianutils
$ ls
  debianutils-4.4  debianutils_4.4.dsc  debianutils_4.4.tar.gz

$ tree debianutils-4.4 -L 1 -d
  debianutils-4.4
  ├── debian
  └── po4a

$ cd debianutils-4.4/
$ ls | grep -E "ischroot"
  ischroot.1
  ischroot.c
```

## ischrootコマンドの挙動(manより抜粋)

ischrootコマンドは、マイナーなため、使用方法を説明します。本コマンドは、現プロセスがjail環境かどうかをischrootコマンドの返り値で示します。

以下に、返り値の一覧を示します。

| 返り値 | 説明 |
| --- | --- |
| 0 | 現在のプロセスは、jail環境で動作している。 |
| 1 | 現在のプロセスは、通常の環境で動作している。 |
| 2 | ischrootコマンドを一般ユーザが実行している(ischrootは管理者権限が必須)。 |

実行例を以下に示します。

```
$ ischroot
$ echo $?          (注釈) 返り値の表示
2

$ sudo ischroot
$ echo $?
1
```

ischrootのオプションは、以下の通りです。

| オプション | 説明 |
| --- | --- |
| \-f, --default-false | ischrootコマンドを一般ユーザが実行した場合の返り値が1になる。 |
| \-t, --default-true | ischrootコマンドを一般ユーザが実行した場合の返り値が0になる。 |
| \--help | ヘルプを表示する |
| \--version | バージョン情報を表示する |

## ischrootの実装

```
int main(int argc, char *argv[])
{
  int default_false = 0;
  int default_true = 0;
  int exit_status;

  for (;;) {
    int c;
    int option_index = 0;

    static struct option long_options[] = { 
      {"default-false", 0, 0, 'f'},
      {"default-true", 0, 0, 't'},
      {"help", 0, 0, 'h'},
      {"version", 0, 0, 'V'},
      {0, 0, 0, 0}
    };  
    c = getopt_long(argc, argv, "fthV", long_options, &option_index);
    if (c == EOF)
      break;
    switch (c) {
    case 'f':
      default_false = 1;
      break;
    case 't':
      default_true = 1;
      break;
    case 'h':
      usage();
      break;
    case 'V':
      version();
      break;
    default:
      fprintf(stderr, "Try `ischroot --help' for more information.\n");
      exit(1);
    }   
  }

  if (default_false && default_true) {
    fprintf(stderr, "Can't default to both true and false!\n");
    fprintf(stderr, "Try `ischroot --help' for more information.\n");
    exit(1);
  }

  if (isfakechroot())
    exit_status = 0;
  else
    exit_status = ischroot();

  if (exit_status == 2) {
    if (default_true)
      exit_status = 0;
    if (default_false)
      exit_status = 1;
  }

  return exit_status;
} 
```

最初のオプション解析部分は、chrootコマンドと同じ要領で解析できるので、説明を割愛します。(オプションであるdefault\_false、default\_trueを同時に指定した場合は、エラー終了のようですね)

続くisfakechroot()の定義は、以下の通りです。

```
int isfakechroot()
{
  const char *fakechroot, *ldpreload;
  return ((fakechroot = getenv("FAKECHROOT")) &&
      (strcmp("true", fakechroot) == 0) &&
      (NULL != getenv("FAKECHROOT_BASE")) &&
      (ldpreload = getenv("LD_PRELOAD")) &&                                                     
      (NULL != strstr(ldpreload, "libfakechroot.so")));
}
```

isfakechroot()では、環境がFAKECHROOT環境か、必要なライブラリがpreloadされているか確認します。ここでのFAKECHROOT環境では、libc(glibc)関数を上書きするライブラリをpreloadされているため、root権限無しでパッケージを構築する作業などが可能になります。

具体的には、ここでのpreloadされているライブラリとはlibfakechroot.soであり、  
preloadされているかは環境変数LD\_PRELOADにlibfakechroot.soへのPATHがあるかで判断できます。なお、libfakechroot.soには、libc(glibc)関数が再定義されており、  
LD\_PRELOADを指定してアプリを実行した場合、再定義された関数を用いてアプリが動作します。

続くischroot()は、現在の環境がFAKECHROOT環境でない場合のみ、実行されます。  
ischrootは、configure時に指定した実行環境により、定義が異なります。ここでの定義は、Linux環境/FreeBSD環境/GNU Hurd環境/その他、の4種類存在します。

今回は、Debian環境であるため、Linux環境の定義を以下に示します。

```
static int ischroot()
{
  struct stat st1, st2;

  if (stat("/", &st1))
    return 2;
  if (stat("/proc/1/root", &st2)) {
    /* Does /proc/1/root exist at all? */
    if (lstat("/proc/1/root" , &st2))
      return 2;
    /* Are we root? */
    if (geteuid() != 0)
      return 2;
    /* Root can not read /proc/1/root, assume vserver or similar */
    return 0;
  } else if ((st1.st_dev == st2.st_dev) && (st1.st_ino == st2.st_ino))
    return 1;
  else
    return 0;
}
```

ischroot()では、"/"のデバイスIDおよび"/proc/1/root"のデバイスID、"/"のinode番号および"/proc/1/root"のinode番号を比較します。"/proc/1/root"が存在し、かつ管理者権限で実行しているにも関わらず、"/proc/1/root"の状態が読み取れない場合は、jail環境と判定されます。

なお、返り値として2を返すのは、以下のケースが想定されています。

- ischrootコマンドが管理者権限で実行されていない場合
- "/"の情報が読み取れない場合(/procがマウントされていない場合)
- /proc/1/rootが存在しない場合

以上が、ischrootコマンドの処理となります。

## 参考書籍

[LINUXプログラミングインタフェース(O'Reilly)](https://www.oreilly.co.jp/books/9784873115856/)  
[Inside Linux Software オープンソースソフトウェアのからくりとしくみ(翔泳社)](http://www.shoeisha.co.jp/book/detail/9784798112831)

## 最後に

coreutilsは、様々なOS環境で動作させる事を意識した作りであったため、「この訳分からん処理は、どんな意図で実装されているんだ……」と感じる点が多々ありました。ただし、文献数やマクロの変態さを考慮すれば、Linux Kernelよりcoreutilsは読みやすい部類かなと。
