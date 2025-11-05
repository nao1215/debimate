---
title: "Linux Kernel: 構造体メンバポインタから構造体の先頭ポインタを得るcontainer_ofマクロ"
type: post
date: 2019-04-06
categories:
  - "linux"
tags:
  - "c言語"
  - "linux"
  - "linuxkernel"
cover:
  image: images/container_of.png
  alt: "Linux Kernel: 構造体メンバポインタから構造体の先頭ポインタを得るcontainer_ofマクロ"
  hidden: false
images: ["post/2019-04-06-linux-kernel-構造体メンバポインタから構造体の先頭ポイ/images/container_of.png"]
---

## container\_ofマクロとは

container\_ofマクロは、Linux Kernelで用いられ、「構造体メンバポインタ」から「そのメンバを含む構造体の先頭ポインタ」を得られるマクロです。C言語では、[offsetofマクロ](http://www.c-tipsref.com/reference/stddef/offsetof.html)によって構造体メンバアドレスのオフセット(構造体先頭アドレスからメンバ変数までのオフセット)を算出できます。container\_ofマクロは、このオフセットを利用し、構造体の先頭アドレスを算出しています。

本記事では、container\_ofマクロに関して、以下の内容を解説します。

解説内容

- container\_ofマクロの定義
- 引数
- 使用例(User空間での使用例)
- 実装解説

## container\_ofマクロの定義

container\_ofマクロは、$(KERNEL\_TOP\_DIR)/include/linux/kernel.hに定義されています。

```
/**                                                                           
 * container_of - cast a member of a structure out to the containing structure
 * @ptr:    the pointer to the member.                                        
 * @type:   the type of the container struct this is embedded in.             
 * @member: the name of the member within the struct.                         
 *                                                                            
 */                                                                           
#define container_of(ptr, type, member) ({          \                         
    const typeof( ((type *)0)->member ) *__mptr = (ptr);    \                 
    (type *)( (char *)__mptr - offsetof(type,member) );})                     
```

## 引数

| **No.** | **引数名** | **説明** |
| --- | --- | --- |
| 1 | ptr | 構造体メンバへのポインタ |
| 2 | type | 第一引数ptrが指す構造体メンバを含む構造体名 |
| 3 | member | 第一引数ptrが指す構造体メンバの名称 |

## 使用例(User空間での使用例)

User空間でもcontainer\_ofマクロは動作するため、今回の使用例ではUser空間のサンプルプログラムを用います。以下のサンプルプログラムは、game構造体のメンバ変数(price、genre、score)のポインタを用いて、game構造体の先頭ポインタを取得します。また、「メンバ変数アドレス」と「構造体の先頭アドレス」のオフセットも合わせて表示します。

以下、サンプルコードおよび実行例です。

```
#include <stdio.h>     
#include <stdlib.h>  
#include <string.h>
#include <stddef.h>                                             
                                                                                  
#define container_of(ptr, type, member) ({          \                             
    const typeof( ((type *)0)->member ) *__mptr = (ptr);    \                     
    (type *)( (char *)__mptr - offsetof(type,member) );})                         
                                                                                  
struct game {                                                                     
    int  price;                                                                   
    char genre[256];                                                              
    char score[128];                                                              
};                                                                                
                                                                                  
int main (void) {                                                                 
    struct game *g = NULL;                                                        
                                                                                  
    g = (struct game *)malloc(sizeof(struct game));                               
    memset(g, 0, sizeof(struct game));                                            
                                                                                  
    printf("Struct head address            = %p\n\n", g);                         
                                                                                  
    printf("Struct member price address    = %p\n", &g->price);                   
    printf("OFFSET:head <-> member price   = %p\n", offsetof(struct game, price));
    printf("Struct head address from price = %p\n\n",                             
            container_of(&g->price, struct game, price));                         
                                                                                  
    printf("Struct member genre address    = %p\n", g->genre);                    
    printf("OFFSET:head <-> member genre   = %p\n", offsetof(struct game, genre));
    printf("Struct head address from genre = %p\n\n",                             
            container_of(g->genre, struct game, genre));                          
                                                                                  
    printf("Struct member score address    = %p\n", g->score);                    
    printf("OFFSET:head <-> member score   = %p\n", offsetof(struct game, score));
    printf("Struct head address from score = %p\n",                               
            container_of(g->score, struct game, score));                          

    free(g); 
    g = NULL;

    return 0;
}                                                              
```

```
$ gcc -o test test.c

$ ./test 
Struct head address            = 0x55cf6e4c4260  (注釈)：game構造体の先頭アドレス

 (注釈)：メンバ変数priceは、構造体の先頭メンバのため、game構造体の先頭アドレスと元々一致しています。
Struct member price address    = 0x55cf6e4c4260  
OFFSET:head <-> member price   = (nil)
Struct head address from price = 0x55cf6e4c4260

Struct member genre address    = 0x55cf6e4c4264
OFFSET:head <-> member genre   = 0x4
Struct head address from genre = 0x55cf6e4c4260 (注釈)：メンバ変数genreからgame構造体の先頭アドレスを取得

Struct member score address    = 0x55cf6e4c4364
OFFSET:head <-> member score   = 0x104
Struct head address from score = 0x55cf6e4c4260 (注釈)：メンバ変数scoreからgame構造体の先頭アドレスを取得

```

## 実装解説

以下の通り、container\_ofの定義を読みやすい形に整形しました。

```
#define container_of(ptr, type, member) 
({                                                          \                         
    const typeof( ((type *)0)->member ) *__mptr = (ptr);    \                 
    (type *)( (char *)__mptr - offsetof(type,member) );
})                     
```

まず、container\_ofマクロは、変数\_\_mptrに構造体メンバ変数のアドレスを代入しています。抑えるべきポイントは、以下の3点であり、重要なのは3点目(補足を後述)です。

ポイント

- (type \*)0)->memberは、変数memberを取得するため、便宜的にNULLポインタをキャストしています
- typeof()は、引数で指定した変数の型を返します(gcc拡張構文)
- 型を指定してポインタを得る理由は、コンパイル時に異常なアドレスを参照する事を防止したいから

上記のポイント3点目に関して、補足します。container\_ofマクロは、本質的にはオフセット計算をしたいだけなため、char型によるポインタ計算で実装可能です。しかし、この方法では、containe\_ofマクロ使用者の実装ミスによって、異常なアドレスを参照するバグが発生する可能性があります(例：メンバ変数の名称を間違えた場合など)。一方で、構造体メンバ型を用いてポインタアドレスを取得すれば、実装ミス時にコンパイルエラーが発生します。そのため、バグを未然に防げます。

以上を踏まえると、container\_ofマクロ定義の\_\_mptrに構造体メンバアドレスを代入する処理は、以下のように読み解けます。なお、前述のサンプルコードを前提として記載しています。

```
struct game {                                                  
    int  price;                                                
    char genre[256];                                           
    char score[128];                                           
};                                                             
container_of(&g->price, struct game, price); を前提として考えれば、

container_ofマクロ定義の__mptrに構造体メンバアドレスを代入する処理は、
const typeof( ((type *)0)->member ) *__mptr = (ptr); 
　↓
const typeof( ((struct game *)0)->member ) *__mptr = (&g->price); 
　↓
const  int *__mptr = (&g->price); 
と読み解けます。

```

続いて、container\_ofマクロのオフセット計算部分 (char \*)\_\_mptr - offsetof(type,member)です。計算式は「構造体メンバアドレス - 構造体の先頭アドレスから構造体メンバ変数までのオフセット」です。前述のサンプルプログラム上でオフセットを表示しているため、その結果を用いて確認します。以下、サンプルプログラムの出力結果(一部)です。

```
Struct member score address    = 0x563ddd56f364  (注釈)：メンバ変数scoreのアドレス
OFFSET:head <-> member score   = 0x104　　    　  (注釈)：オフセット
Struct head address from score = 0x563ddd56f260  (注釈)：構造体の先頭アドレス

```

手計算すれば、

「構造体メンバアドレス (0x563ddd56f364) - 構造体の先頭アドレスから構造体メンバ変数までのオフセット(0x104) = 構造体の先頭アドレス(0x563ddd56f260)」

となる事が分かります。以下にイメージ図を示します。

```
構造体の先頭:-------------------: 0x563ddd56f260       
          |  メンバ変数price    |      ↑               
          :-------------------:  offset:0x104
          |  メンバ変数genre    |      ↓               
          :-------------------: 0x563ddd56f364       
          |  メンバ変数score    |                      
          :-------------------:                      

```
