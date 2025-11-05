---
title: "【C言語】_Generic(C11、gcc4.6以降)または__attribute__((overloadable))によるオーバーロード"
type: post
date: 2021-05-15
categories:
  - "linux"
tags:
  - "c言語"
  - "linux"
cover:
  image: images/birds-6211541_640.jpg
  alt: "【C言語】_Generic(C11、gcc4.6以降)または__attribute__((overloadable))によるオーバーロード"
  hidden: false
images: ["images/birds-6211541_640.jpg"]
---

## 前書き 

C言語にはオーバーロードがない。そんな風に考えていた時期が私にもありました。

オーバーロードとは、メソッド（関数）を多重定義する言語仕様です。例えば、Javaでは引数の順番もしくは引数の個数を変える事によって同名メソッドを複数定義できます。

私はC言語を始めて触ったのが2009年頃で、その頃の書籍を読む限りでは「C言語にはオーバーロードがない」という認識を持っていました。しかし、その認識は誤りで、最近はオーバーロードがサポートされているようです。

本記事では、オーバーロードを実現する方法を2点紹介します。

C言語でオーバーロードを実現する方法

- \_Generic(C11、gcc4.6)
- GCC拡張：\_\_attribute\_\_((overloadable))

## \_Genericのサンプルコード

\_Genericは、C11（gcc4.6）で追加された総称選択（Generic selection）マクロです。引数の型に応じて、呼び出す関数を切り替えられます。

```
[_Genericの書式]
_Generic(制御式, 型1: 式1, 型2: 式2…)

制御式＝定数、文字列リテラル、関数名、変数名など
型＝C言語で使用可能な型、もしくはdefault
式＝関数名やマクロ名

```

以下のサンプルコードでは、型ごとに異なる絶対値算出関数を呼び分けています。

```
#include <stdio.h> 
#include <stdlib.h> 
#include <math.h> 

/**
 * 型に応じて、絶対値算出関数を切り替える。
 * int型   ：abs()
 * long型  ：labs()
 * float型 ：fabsf()
 * double型：fabs()
 */ 
#define abs(x) _Generic((x), \
                        long: labs, \
                        double: fabs, \
                        float: fabsf, \
                        default: abs)(x)

int main(void) {
    int i = -2;
    long l = -100;
    double d = -3.14;
    float f = -1999.123;

    printf("int   =%d\n", abs(i));
    printf("long  =%ld\n", abs(l));
    printf("double=%.2lf\n", abs(d));
    printf("float =%.3f\n", abs(f));

    return 0;
}
```

以下が実行結果です。

```
$ gcc main.c -o main -lm
$ ./main 
int   =2
long  =100
double=3.14
float =1999.123

```

コンパイル時に警告が出ないため、型に応じて正しく関数を呼び分けられていると判断できます。なお、呼び分けられていない場合は、「printf出力フォーマットで用いる型」と「abs()の戻り値の型」が一致しないので、その旨を示す警告が出ます。

## \_Genericの利点／欠点

- 利点：C11使用をサポートしているコンパイラ（gcc、clangなど）であれば使用可能
- 欠点：オーバーロードしたい関数の引数が多い場合、マクロが複雑化

## \_\_attribute\_\_((overloadable))のサンプルコード

\_\_attribute\_\_は、GCCやclangの拡張機能であり、関数や変数などに属性を付与するために用いられます。この拡張機能を用いて、関数にoverloadable属性を付与する事によってオーバーロードが実現できます。ただし、拡張機能はCPUによって使用可否が異なります。

以下のサンプルコードでは、型ごとにprintf()を呼び分けています。引数の型だけでなく、引数の個数も変えています。

```
#include <stdio.h> 

void __attribute__((overloadable)) print(int i) {
    printf("int=%d\n", i);
}

void __attribute__((overloadable)) print(double d)  {
    printf("double=%lf\n", d);
}

void __attribute__((overloadable)) print(const char *c) {
    printf("char=%s\n", c);
}

void __attribute__((overloadable)) print(const char *c, const char *d)  {
    printf("char=%s and char=%s\n", c, d);
}

int main(void) {
    print(100);
    print(12.34);
    print("test");
    print("引数の個数", "増えたバージョン");
    return 0;
}

```

以下が実行結果です。

```
$ clang main.c -o main
$ ./main 
int=100
double=12.340000
char=test
char=引数の個数 and char=増えたバージョン

```

私の環境では、上記のサンプルコードをgcc7.5、8.3、10.3でコンパイルできませんでした。clang version 6.0.0-1ubuntu2でのみ動作確認しています。

## \_\_attribute\_\_((overloadable))の利点／欠点

- 利点：直感的な書式
- 欠点：コンパイル環境によっては、拡張機能が使用できない

## 最後に

C言語でオーバーロードできる事実は、Vala言語（C#ライクの文法であり、最終的にC言語を生成する言語）の調査中に気づきました。

C言語が使いやすくなるのは好ましい一方で、仕事で新し目のコンパイラ（言語仕様）を使えるかは別問題。悲しい気持ちになります
