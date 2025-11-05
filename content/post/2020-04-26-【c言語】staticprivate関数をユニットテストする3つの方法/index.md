---
title: "【C言語】static(private)関数をユニットテストする3つの方法【単体テストのバッドノウハウ】"
type: post
date: 2020-04-26
categories:
  - "linux"
tags:
  - "c言語"
  - "linux"
  - "ユニットテスト"
cover:
  image: images/board-361516_640-min.jpg
  alt: "【C言語】static(private)関数をユニットテストする3つの方法【単体テストのバッドノウハウ】"
  hidden: false
images: ["post/2020-04-26-【c言語】staticprivate関数をユニットテストする3つの方法/images/board-361516_640-min.jpg"]
---

## 前書き：C言語のstatic関数は単体テストできます

C言語で単体テストを作成する際に、**「どうやってstatic関数をテストコードから呼び出せばいいのか？」**と迷った事はありませんか？例えば、以下のコードのprivate\_func()を他のCソースファイル（例：テストコード）から呼び出せるでしょうか。

```
#include <stdio.h>

int main(void) {
    printf("Main function\n");
    return 0;
}

static void private_func(void) {
    printf("private function\n");
}
```

結論を言えば、static関数を単体テストする方法は3通りあります。本記事では、3通りの方法をそれぞれ紹介します。

static関数を単体テストする方法

- 単体テストの時だけstatic指定子を消す方法
- static関数のラッパー関数（public）を作成する方法
- テスト対象のコードをincludeする方法

## 単体テストの時だけstatic指定子を消す方法

この方法は、#ifdef／#ifndef、#defineマクロ、gccコンパイルオプションを駆使して、static指定子を単体テスト時のみ消します。本記事で紹介する中で、この方法が最も自然です。

まず、任意のヘッダファイル（private.h）に#defineマクロと#ifdef／#ifndefを使用して、テスト時のみstatic指定子が消えるようにします。以下の例では、\_\_TEST\_\_が定義済みの場合はstatic指定子が消え、static関数がpublic関数として宣言されます。\_\_TEST\_\_が未定義の場合はstatic指定子が残り、pricate\_func()関数の宣言はヘッダファイルから消えます。

```
#ifndef __TEST__
#define STATIC static
#else
#define STATIC /* staicを指定しない */
#endif

#ifdef __TEST__
STATIC void private_func(void);
#endif

```

次に、ソースコード（private.c）では\_\_TEST\_\_が未定義の場合のみ、private\_func()関数の宣言をします。このように実装すれば、\_\_TEST\_\_の定義・未定義によって、private\_func()の宣言先がヘッダーファイルかソースファイルかが切り替わります。

```
#include  <stdio.h>
#include "private.h"

#ifndef __TEST__
STATIC void private_func(void);
#endif

STATIC void private_func(void) {
    printf("private function\n");
}

```

最後に、テストコード（test.c）を以下のように実装します。

```
#include  <stdio.h>
#include "private.h"

int main(void) {
    private_func();
}

```

\_\_TEST\_\_の定義は、gccコンパイルオプション（"-Dオプション"）で指定します。以下に実例を示します。

```
$ gcc -D__TEST__ -o test test.c private.c

(注釈)：static関数をテストコードから呼び出し
$ ./test
private function

(注釈)：gccコンパイルオプション("-D")がないと、テストコードのビルドはエラー。
　　　  通常は、Makefileでテストコードをビルドするかしないかを切り分ける。
$ gcc -o test test.c private.c
test.c: In function ‘main’:
test.c:5:5: warning: implicit declaration of function ‘private_func’ [-Wimplicit-function-declaration]
     private_func();
     ^~~~~~~~~~~~
/usr/bin/ld: /tmp/ccG3PF2q.o: in function `main':
test.c:(.text+0xa): undefined reference to `private_func'
collect2: error: ld returned 1 exit status

```

## static関数のラッパー関数（public）を作成する方法

この方法は、テスト対象static関数のラッパー関数（public）を作成します。無駄なラッパー関数がソースファイルに含まれるので、あまり好ましくないです。

まず、ソースコード（private.c）では、static関数（private\_func）のラッピングする関数（wrapper\_private\_func）を作成します。

```
#include  <stdio.h>
#include "private.h"

static void private_func(void) {
    printf("private function\n");
}

void wrapper_private_func(void) {
    printf("wrapper private function\n");
    private_func();
}

```

残りの作業は、このラッパー関数の宣言をヘッダーファイル（private.h）に記載し、テストコード（test.c）からラッパー関数を呼び出すだけです。

```
void wrapper_private_func(void);

```

```
#include  <stdio.h>
#include "private.h"

int main(void) {
    wrapper_private_func();
}

```

以下に実行例を示します。

```
$ gcc -o test test.c private.c

$ ./test
wrapper private function
private function

```

## テスト対象のコードをincludeする方法

この方法は、# includeを用いて、static関数を定義したソースファイルをテストコードに読み込む方法です。私は、この方法を初めて聞いた時、「頭がいい方法だな」と思わず、「気持ち悪っ！」と嫌悪感を示しました。今でも良く覚えています。

実装方法は簡単で、テストコードを書いたソースファイル（test.c）にテスト対象ファイル（private.c）をincludeするだけです。C言語の#includeは、指定したファイルを#include指定行に展開する仕組みなので、ヘッダーファイル以外（=ソースファイル）も指定できます。

```
#include  <stdio.h>

static void private_func(void) {
    printf("private function\n");
}

```

```
#include  <stdio.h>
#include "private.c"

int main(void) {
    private_func();
}

```

最後に、実行例を示します。

```
$ gcc -o test test.c private.c

$ ./test
private function

```

## 余談：#includeでソースファイルを読み込む実例

coreutilsパッケージで提供されるfalseコマンド（必ず1を返すコマンド）は、#includeでソースファイルを読み込んでいます。以下の記事の下部に、実装解説がありますので、興味がある方は読んでみてください。

https://debimate.jp/2020/04/16/etc-passwd%e3%81%ab%e8%a8%98%e8%bc%89%e3%81%95%e3%82%8c%e3%81%9f-usr-sbin-nologin-bin-false%e3%81%a8%e3%81%af%e4%bd%95%e3%81%8b%e3%80%90%e3%83%ad%e3%82%b0%e3%82%a4%e3%83%b3%e7%a6%81%e6%ad%a2/
