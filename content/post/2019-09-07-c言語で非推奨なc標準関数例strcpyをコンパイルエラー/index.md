---
title: "C言語で非推奨なC標準関数(例:strcpy)をコンパイルエラーにする方法"
type: post
date: 2019-09-07
categories:
  - "linux"
tags:
  - "c言語"
  - "linux"
cover:
  image: images/banned-1726366_640.jpg
  alt: "C言語で非推奨なC標準関数(例:strcpy)をコンパイルエラーにする方法"
  hidden: false
---

## 前書き

C言語は歴史の長い言語のため、非推奨関数があります。例えば、strcpy()は文字列をコピーする際にサイズチェックをしないため、バッファオーバーフローを引き起こす可能性があります。そのため、一般的には、strcpy()の代替関数としてstrcpy\_s()を使用する事が推奨されています。

開発プロジェクトにおいて、「コーディング中の注意力」および「レビュー」によって、非推奨関数の混入を防ぐ事は困難です。現実的な問題として、

- 新人やロートル(古い慣習をアップデートしない人)の参加
- 開発ルール(使用関数の規約など)に従わない人
- 時間的な制約によるレビューの簡素化

があります。上記の問題を解決するには、人の手を使わずにシステムが禁止関数の使用を検知する方法が望ましいです。そのような方法として、[gitでは禁止関数リストをheaderファイルに書き、禁止関数を使用した場合はコンパイルエラーを起こす仕組み](https://www.spinics.net/lists/git/msg337206.html)が導入されました。

コンパイラを利用した方法であれば、エンジニアのスキル習熟度に左右されませんし(実行はコマンドを叩くだけ)、人の目と違い検知漏れが発生しません。今まで、禁止関数を強制的にコンパイルエラーにする発想が無かったため、本記事ではその仕組みに関して説明します。

## 禁止関数リストbanned.hについて

[GitHubにgit(banned.h)のオリジナルコード](https://github.com/git/git/blob/master/banned.h)があります。2019年9月7日時点で、banned.hの中身は以下の通りです。gitにおける禁止関数は、strcpy()、strcat()、strncpy()、strncat()、sprintf()、vsprintf()と定めているようです。

```
#ifndef BANNED_H
#define BANNED_H

/*
 * This header lists functions that have been banned from our code base,
 * because they're too easy to misuse (and even if used correctly,
 * complicate audits). Including this header turns them into compile-time
 * errors.
 */

#define BANNED(func) sorry_##func##_is_a_banned_function

#undef strcpy
#define strcpy(x,y) BANNED(strcpy)
#undef strcat
#define strcat(x,y) BANNED(strcat)
#undef strncpy
#define strncpy(x,y,n) BANNED(strncpy)
#undef strncat
#define strncat(x,y,n) BANNED(strncat)

#undef sprintf
#undef vsprintf
#ifdef HAVE_VARIADIC_MACROS
#define sprintf(...) BANNED(sprintf)
#define vsprintf(...) BANNED(vsprintf)
#else
#define sprintf(buf,fmt,arg) BANNED(sprintf)
#define vsprintf(buf,fmt,arg) BANNED(sprintf)
#endif

#endif /* BANNED_H */
```

banned.hで使用されているBANNEDマクロについて、説明します。

```
#define BANNED(func) sorry_##func##_is_a_banned_function

```

上記マクロ中の##は、文字連結用の演算子です。そのため、BANNEDマクロを使用すると、sorry\_func\_is\_a\_banned\_functionという文字列が生成されます。func部分には、関数名が挿入される想定で定義されています。

上記のbanned.hを確認すれば、

```
#define 禁止関数名(禁止関数の引数, ...) BANNED(禁止関数名)

```

という形でマクロ(禁止関数リスト)を列挙している事が分かります。banned.hをインクルードしているソースコード中で、禁止関数を使用した場合はコンパイル時にエラーとなります。例えば、strcpyを含んだコードをコンパイルした場合、以下のようなエラーが出ます。

```
main.c: In function ‘main’:
banned.h:4:22: error: ‘sorry_strcpy_is_a_banned_function’ undeclared (first use in this function)
 #define BANNED(func) sorry_##func##_is_a_banned_function
                      ^~~~~~
banned.h:7:21: note: in expansion of macro ‘BANNED’
 #define strcpy(x,y) BANNED(strcpy)
                     ^~~~~~
main.c:9:5: note: in expansion of macro ‘strcpy’
     strcpy(str1, str2);
     ^~~~~~

```

## 禁止関数の追加例

禁止関数の追加例として、文字列を数値に変換するatoi()をbanned.hに加えて、コンパイルエラーを起こす方法を以下に示します。banned.hの変更方法(banned.h)、atoi()を呼び出すコード(main.c)、コンパイル例を順に記載します。

```
#ifndef BANNED_H
#define BANNED_H

/* 省略 */

/* atoi関数を新規に禁止リストへ追加 */
#undef atoi
#define atoi(x) BANNED(atoi)

#endif /* BANNED_H */
```

```
#include 
#include 
#include "banned.h"

int main(void) {
    char str[] = "123";
    atoi(str);
    return 0;
}

```

```
$ ls
banned.h  main.c

$ gcc -o main main.c 
In file included from main.c:3:
main.c: In function ‘main’:
banned.h:4:22: error: ‘sorry_atoi_is_a_banned_function’ undeclared (first use in this function)
 #define BANNED(func) sorry_##func##_is_a_banned_function
                      ^~~~~~
banned.h:8:17: note: in expansion of macro ‘BANNED’
 #define atoi(x) BANNED(atoi)
                 ^~~~~~
main.c:7:5: note: in expansion of macro ‘atoi’
     atoi(str);
     ^~~~
banned.h:4:22: note: each undeclared identifier is reported only once for each function it appears in
 #define BANNED(func) sorry_##func##_is_a_banned_function
                      ^~~~~~
banned.h:8:17: note: in expansion of macro ‘BANNED’
 #define atoi(x) BANNED(atoi)
                 ^~~~~~
main.c:7:5: note: in expansion of macro ‘atoi’
     atoi(str);
     ^~~~

```

想定通り、"error: ‘sorry\_atoi\_is\_a\_banned\_function’ undeclared"が表示されている事がログから読み取れます。

## C言語の時代遅れ・非推奨な関数の調べ方

時代遅れ・非推奨な関数を調べるには、CERT(Computer Emergency Response Team)を参照する方法があります。CERTは、セキュリティインシデントに関する情報を提供しており、日本版のJPCERTも存在します。

このCERT(JPCERT)が提供する情報の中に、「[非推奨関数や時代遅れの関数を使用しない](https://www.jpcert.or.jp/sc-rules/c-msc24-c.html) 」があります。このページでは、「使用すべきではない関数」と「代替関数」がリストアップされています。まずは、このリストを参照すれば、一通りの情報は取得できます。

より網羅的に調べる場合は、CERTのテクニカルマネージャが執筆した「C/C++セキュアコーディング 第2版 」がオススメです。

<iframe style="width: 120px; height: 240px;" marginwidth="0" marginheight="0" scrolling="no" frameborder="0" src="//rcm-fe.amazon-adsystem.com/e/cm?lt1=_blank&amp;bc1=000000&amp;IS2=1&amp;bg1=FFFFFF&amp;fc1=000000&amp;lc1=0000FF&amp;t=debimate07-22&amp;language=ja_JP&amp;o=9&amp;p=8&amp;l=as4&amp;m=amazon&amp;f=ifr&amp;ref=as_ss_li_til&amp;asins=4048919873&amp;linkId=25bb9070658de82d92c92986df54119a"></iframe>
