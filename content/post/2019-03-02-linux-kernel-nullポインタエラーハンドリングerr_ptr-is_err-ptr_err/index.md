---
title: "Linux Kernel: NULLポインタエラーハンドリング(ERR_PTR, IS_ERR, PTR_ERR)"
type: post
date: 2019-03-02
categories:
  - "linux"
tags:
  - "c言語"
  - "linux"
  - "linuxkernel"
cover:
  image: "images/NULL.jpg"
  alt: "Linux Kernel: NULLポインタエラーハンドリング(ERR_PTR, IS_ERR, PTR_ERR)"
  hidden: false
---

## "返り値がNULL" = "情報量がない"

C言語には、返り値としてポインタを返す関数があります。

User空間の関数で例を挙げれば、メモリを確保するmalloc()、ファイルを開くfopen()などです。これらの関数は、エラー時にNULLを返します。

しかし、**情報がNULLだけでは、どのような原因でエラーが発生したかが分かりません**。この問題への対処として、User空間のシステムコールやライブラリ関数（一部）などは、変数errnoに補足情報を付与しています（errnoについては、以下の記事に詳細を記載しました）。

[Linux Kernel: エラー番号の一覧](https://debimate.jp/post/2019-02-24-linux-kernel-%E3%82%A8%E3%83%A9%E3%83%BC%E7%95%AA%E5%8F%B7%E3%81%AE%E4%B8%80%E8%A6%A7/)

変数errnoは、User空間 <-> Kernel空間で情報をやり取りするための仕組みです。しかし、変数errnoはUser空間に存在するグローバル変数で、User空間の標準ライブラリが制御しています。つまり、Kernelが変数errnoを操作する事は、適切ではありません。

そのため、Kernel空間のNULLポインタエラーハンドリングでは、別の仕組みを用います。

具体的には、エラー時にNULLポインタを返さず、エラー番号をvoid型ポインタにキャストして返します。この方法では、返り値がポインタアドレスかエラー番号かを判断する仕組みが必要です。この仕組みを実現するために、下表に存在する関数を用います。

本記事では、これら関数の実装および使い方を説明します。

| **関数名** | **使用タイミング** | **説明** |
| --- | --- | --- |
| ERR\_PTR | エラー時にポインタを返す時 | NULLポインタの代わりに、エラー番号(errno)をポインタとして返します。 |
| IS\_ERR | 返り値（ポインタ）がエラーかどうかを判断する時 | 返り値（ポインタ）が有効なエラー番号を符号反転した値（-4095〜-1）であれば、真となります。 |
| PTR\_ERR | 返り値（ポインタ）のエラー原因を取得する時 | 返り値（ポインタ）から符号反転したエラー番号を取得します。 |

## ERR\_PTR()の実装および使用例

ERR\_PTR()は、引数で渡されたエラー番号をvoid型ポインタにキャストして返します。

```
static inline void * __must_check ERR_PTR(long error) 
{                                                     
    return (void *) error;                            
}                                                     

```

ERR\_PTR()の使用例として、memdup\_user()を示します。

本関数は、User空間のメモリ内容をKernel空間にコピーします。処理途中にあるkmalloc\_track\_caller()(Kernel版malloc)のエラー処理において、ERR\_PTR()を使用しています。

引数は、メモリ不足によるエラーを示すENOMEMで、**ERR\_PTR()にエラー番号を符号反転させて渡す事がポイント(お作法)**です。符号反転する理由は、後述のIS\_ERR()で分かります（説明します）。

なお、copy\_from\_user()で発生しているエラーは、アドレス不正です。

```
void *memdup_user(const void __user *src, size_t len)                                                                    
{                                                                                                                        
        void *p;                                                                                                         
                                                                                                                         
        /*                                                                                                               
         * Always use GFP_KERNEL, since copy_from_user() can sleep and                                                   
         * cause pagefault, which makes it pointless to use GFP_NOFS                                                     
         * or GFP_ATOMIC.                                                                                                
         */                                                                                                              
        p = kmalloc_track_caller(len, GFP_KERNEL);                                                                       
        if (!p)                                                                                                          
                return ERR_PTR(-ENOMEM);                                                                                 

        if (copy_from_user(p, src, len)) {                                                                               
                kfree(p);                                                                                                
                return ERR_PTR(-EFAULT);                                                                                 
        }
                                                                                                                  
        return p;                                                                                                        
}  

```

## IS\_ERR()の実装

IS\_ERR()は、引数で渡されたポインタの実体が、有効なエラー番号（1〜4095）であれば真を返し、異なる場合は偽を返します。

使用例は、PTR\_ERR()の使用例と一緒に示します。

```
static inline bool __must_check IS_ERR(__force const void *ptr) 
{   
    return IS_ERR_VALUE((unsigned long)ptr);   
}
#define MAX_ERRNO   4095  
#define IS_ERR_VALUE(x) unlikely((unsigned long)(void *)(x) >= (unsigned long)-MAX_ERRNO)
```

上記の実装中で登場するIS\_ERR\_VALUEマクロの判定式は、少しだけ直感的ではありません。

xが符号反転されたエラー番号と考えた場合、"x >= -4095 && x < 0"と実装すれば素直です。このような実装にした理由は、**判定式による比較回数を1回に減らすため**です。

unsigned long型にキャストした-MAX\_ERRNO(= -4095)は、"0xfffff001"です。つまり、判定式は"x >= 0xfffff001"となります。

xがこの条件を満たす時（"0xfffff001"より大きい場合）は、xが-4095〜-1(反転したエラー番号)の時のみです。ポインタアドレスが-4095〜-1になる事はないため、エラー番号のみが正しく検出できます。

また、前述のERR\_PTR()でエラー番号を符号反転させていない場合は、この判定式で意図した結果を得られません。この説明の正しさを確認するため、テストプログラム(User空間アプリ)とその実行結果を後述します。

なお、unlikelyマクロは、条件が偽である場合において、if文の実行速度を向上させる仕組みです。

基本的に、IS\_ERR()で検査されるポインタは、有効なアドレスを持つポインタです。そのため、xが-4095〜-1の範囲外となり、unlikelyマクロの判定は偽となります。逆に、条件が真の場合の高速化には、likelyマクロを用います。

```
#include                                                        
                                                                         
#define MAX_ERRNO 4095                                                   
#define IS_ERR_VALUE(x) ((unsigned long)(x) >= (unsigned long)-MAX_ERRNO)
/* このテストコードは、以下の2点を確認します。                           
 *     1) IS_ERR_VALUEマクロの動作                                       
 *     　 ただし、IS_ERR_VALUEはKernel版と実装が少し異なります。         
 *     2) エラー番号を符号反転していない場合、                           
 *     　 IS_ERR_VALUEマクロの判定が期待値通りとならない事。             
 */                                                                      
int main() {                                                             
    int i =0;                                                            
    /* エラー番号を符号反転していないケースも確認するため、              
     * ループは -4095〜4095 の範囲で行います*/                           
    for(i=-MAX_ERRNO; i<=MAX_ERRNO; i++) {                               
        printf("i=%4d, Cast Value=0x%08x, ", i, (unsigned long)i);       
        printf("%s\n", IS_ERR_VALUE(i) ? "ERRNO" : "Not ERRNO");         
    }                                                                    
    return 0;                                                            
}                                                                                                                     

```

```
$ ./test 
i=-4095, Cast Value=0xfffff001, ERRNO
i=-4094, Cast Value=0xfffff002, ERRNO
i=-4093, Cast Value=0xfffff003, ERRNO

注釈：長いため、省略

i=  -2, Cast Value=0xfffffffe, ERRNO
i=  -1, Cast Value=0xffffffff, ERRNO
i=   0, Cast Value=0x00000000, Not ERRNO
i=   1, Cast Value=0x00000001, Not ERRNO
i=   2, Cast Value=0x00000002, Not ERRNO

注釈：長いため、省略

i=4094, Cast Value=0x00000ffe, Not ERRNO
i=4095, Cast Value=0x00000fff, Not ERRNO

```

\[the\_ad id="598"\]

## PTR\_ERR()の実装および使用例（IS\_ERR()の例含む）

PTR\_ERR()は、引数で渡されたポインタをlong型にキャストして返します。

引数ptrは、IS\_ERR()で検査されている事が前提のため、long型で-4095〜-1を返す事を想定しています。

```
static inline long __must_check PTR_ERR(__force const void *ptr)
{                                                               
    return (long) ptr;                                          
}                                                               

```

最後に、PTR\_ERR()、IS\_ERR()の使用例として、キャラクタデバイス初期化処理を示します。

使用例では、デバイスをクラス登録する関数(class\_create())にて、エラー処理しています。class\_create()が返したポインタをIS\_ERR()で検査し、エラー番号が返ってきた場合はPTR\_ERR()でエラー番号を取得します。内容が理解できていれば、簡単（テンプレート）な処理だと思います。

```
#define DEV_NAME  "debimate"        
#define DEV_CLASS "debimate_class"  
#define MINOR_NR_BASE 0             
#define MAX_MINOR_NR  1             
                                    
static struct class *debimate_class;
static struct cdev   debimate_cdev; 
static dev_t dev;                   

static int debimate_init(void)                                                      
{                                                                                   
        int result                  = 0; 
        struct device *debimate_dev = NULL;                               
                                                                                    
        /* メジャー番号の動的確保 */                                                
        result = alloc_chrdev_region(&amp;dev, MINOR_NR_BASE, MAX_MINOR_NR, DEV_NAME);  
        if (0 != result) {                                                          
                pr_err("%s: alloc_chrdev_region = %d\n", __func__, result);         
                goto REGION_ERR;                                                    
        }                                                                           
                                                                                    
        /* デバイスをクラス登録 */                                                  
        debimate_class = class_create(THIS_MODULE, DEV_CLASS);                      
        if(IS_ERR(debimate_class)){                                                 
                result = PTR_ERR(debimate_class);                                   
                pr_err("%s: class_create = %d\n", __func__, result);                
                goto CREATE_CLASS_ERR;                                              
        }                                                                           
        /* 以下、処理を省略 */                                                                                                       

```
