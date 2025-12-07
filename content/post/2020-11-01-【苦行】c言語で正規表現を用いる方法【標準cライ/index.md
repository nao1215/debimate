---
title: "【苦行】C言語で正規表現を用いる方法【標準Cライブラリ(glibc)使用】"
type: post
date: 2020-11-01
categories:
  - "linux"
tags:
  - "c言語"
  - "debian"
  - "linux"
  - "正規表現"
cover:
  image: "images/regex2-min.jpg"
  alt: "【苦行】C言語で正規表現を用いる方法【標準Cライブラリ(glibc)使用】"
  hidden: false
---

###  前書き：C言語で正規表現を使う理由などない

正規表現（Regular Expression）は強力な機能なため、様々なLinuxコマンドやプログラミング言語、アプリに導入されています。特に、sed／awk／egrepコマンドやPerl／Rubyは、正規表現による文字列操作の代名詞のような存在です。

その一方で、C言語と正規表現の組み合わせはどうでしょうか。あまり馴染みがないと思われます。標準Cライブラリのregex.hが正規表現機能を提供するため、正規表現は殆どのC言語環境で使用できます。しかし、正規表現をスクリプト言語と組み合わせる人が大半ではないでしょうか。

C言語と正規表現の組み合わせは、様々な点で面倒です（C言語の文字列操作自体が面倒ですが……）。

C言語と正規表現の組み合わせで面倒な点

- C言語は文字配列を動的に拡張しない点（置換で文字数が増える場合に拡張が必要）
- 正規表現パターンマッチングまでの前処理が多い点
- 長い正規表現パターンではマッチング時にSegmentation Faultが起こる点
- メモリ操作処理（メモリ確保のmalloc()、メモリ解放のfree()）が多い点

そもそも、C言語で新規コードを書くのは負債を作るのと同じだと言われる時代に、正規表現プログラムをC言語で書く必要などありません。代替手段を探しましょう。

代替手段がなく、C言語で正規表現を使う羽目になった人（例：私）のために、本記事ではC言語による正規表現に関して説明します。

---


### C言語による正規表現の処理フロー

正規表現の使い方で思い浮かべるのは、**「s/置換前(正規表現パターン指定)/置換後の文字列/」**のような短い処理ではないでしょうか。スクリプト言語や新し目の言語であれば、正規表現を用いた文字列操作を1〜3Stepで書き表せる印象を持っていると思います

C言語では、正規表現を使用する場合に、他言語と比べて実装量が数倍に増えます。正規表現パターンを一度コンパイルする必要があり、文字列操作（置換や抽出など）も専用の処理（関数）を書かなければいけません。

具体的には、C言語による正規表現の処理は以下の流れです。

C言語による正規表現の処理フロー

1. 正規表現パターンのコンパイル（正規表現オブジェクトの作成）
2. マッチングする文字列の数だけメモリ確保
3. パターンマッチングの実施
4. マッチング文字列に対する文字列操作（置換、抽出など）
5. 確保した各種メモリの解放

全体の実装は本記事の最後で示しますが、まずは上記の処理フローを順に示します。標準C言語ライブラリが提供する正規表現APIの説明として[manページ](https://linuxjm.osdn.jp/html/LDP_man-pages/man3/regex.3.html)が存在しますので、合わせて確認してください。

---


### 正規表現パターンのコンパイル

正規表現パターン（例："^s\[0-2\].\*"）のコンパイルは、regcomp()で行います。コンパイル結果は正規表現オブジェクトと呼ばれ、regex\_t構造体に格納され、正規表現パターンマッチング時に使用します。

正規表現オブジェクト（regex\_t構造体）は、regcomp()内でメモリ確保されているため、正規表現パターンマッチング終了後にregfree()によるメモリ解放が必要です。

regcomp()のラッパー関数は、以下の形となります。

```
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <regex.h> /* 標準C言語ライブラリ（glibc）が提供する正規表現ライブラリ */

#define SUCCESS 0
#define FAILURE -1

/**
 * @brief 正規表現パターンのコンパイルを行う。
 * @param regex 正規表現パターンのコンパイル結果を記憶する。通称：正規表現オブジェクト
 * @param pattern 正規表現パターン文字列
 * @return SUCCESS：成功、FAILURE：失敗
 * @note 成功時はregexにメモリを割り当てるため、regfree()によるメモリ解放が必要。
 */
static int __regcomp(regex_t *regex, const char *pattern)
{
    if (regcomp(regex, pattern, REG_EXTENDED))
    {
        fprintf(stderr, "%s: Fail regex pattern(=%s) compile\n",
                __func__, pattern);
        return FAILURE;
    }
    return SUCCESS;
}

```

regcomp()の第三引数は、正規表現パターンのコンパイル時に属性を付与するためのビットフラグであり、下表で定義されます。

| **属性フラグ** | **説明** |
| :-- | :-- |
| REG\_EXTENDED | POSIX拡張正規表現を使用する。   このフラグが設定されない場合、 POSIX標準正規表現が使われる。 |
| REG\_ICASE | 大文字小文字の違いを無視する。 |
| REG\_NOSUB | 正規表現パターンマッチ位置を報告しない。 |
| REG\_NEWLINE | 全ての文字にマッチするオペレータに改行をマッチさせない。   改行を含まない非マッチング文字リスト (\[^...\]) に改行をマッチさせない。 |

複数の属性を指定する場合は、"REG\_EXTENDED | REG\_NEWLINE"のようにOR条件として指定します。

今回のラッパー関数では、REG\_EXTENDEDのみ指定していますが、柔軟性をもたせたい場合は引数で属性フラグを指定できる仕様に変更してください。

---


### マッチングする文字列の数だけメモリ確保

正規表現パターンマッチング結果は、regmatch\_t構造体に保存されます。前提として、正規表現では、パターン文字列の中の"("と")"で囲まれた文字列を一つのグループとして扱う事ができます。

正規表現パターンマッチング結果を保存するには、「正規表現パターン全体のマッチング結果」と「各グループに対するマッチング結果」の数だけ、メモリ確保する必要があります。

この説明だけではピンとこないと思いますので、以下に例を示します。

```
[例]
==条件==
正規表現パターン："(aa)(b(bc)(c))(dd)"
検索対象の文字列："aabbccddee"
結果の格納先　　：regmatch_t *match（メモリ確保済み）

==結果==
各グループのマッチング結果は、以下の順番で格納される。
matchの0番目：aabbccdd
matchの1番目：aa
matchの2番目：bbcc
matchの3番目：bc
matchの4番目：c
matchの5番目：dd

==注意点==
match内に、パターンマッチングした文字列が直接格納されているわけではない。
パターンマッチング文字列を取得するには、別途文字列の操作が必要。

```

正規表現パターンマッチング結果を格納するためのメモリ確保は、標準C言語ライブラリにAPIが用意されていません。そのため、以下のような関数でメモリ確保を行います。

```
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <regex.h> /* 標準C言語ライブラリ（glibc）が提供する正規表現ライブラリ */

#define SUCCESS 0
#define FAILURE -1
#define ALL_MATCH_STR_NR 1

/**
 * @brief 正規表現パターンマッチ位置を保持するためのバッファを確保する。
 * @param regex コンパイル済みの正規表現オブジェクト
 * @return NULL以外：成功、NULL：失敗
 * @note 成功時はメモリを割り当てるため、free()によるメモリ解放が必要。
 */
static regmatch_t *mallocMatchBuf(regex_t regex)
{
    regmatch_t *match = NULL;
    /*
     * re_nsubには"("と")"で囲まれたグループの数が格納されている。
     * つまり、正規表現パターン全体にマッチした文字列の数が含まれていない。
     */
    match = (regmatch_t *)malloc(sizeof(regmatch_t) * (regex.re_nsub + ALL_MATCH_STR_NR));
    if (NULL == match)
    {
        fprintf(stderr, "%s: Can't malloc memory.\n", __func__);
        return NULL;
    }
    return match;
}

```

正規表現パターン中で"("と")"で囲まれた文字列の数（グループ数）は、正規表現コンパイル後であればregex\_t構造体の変数re\_nsubに格納されています。変数re\_nsubには、正規表現パターン全体にマッチした文字列の数（= 1個）が含まれていないため、その分を加味してメモリ確保する必要があります。

---


### パターンマッチングの実施

正規表現パターンマッチングはregexec()で行い、その結果はregmatch\_t構造体に保存されます。ラッパー関数は、以下の通りです。

```
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <regex.h> /* 標準C言語ライブラリ（glibc）が提供する正規表現ライブラリ */

#define SUCCESS 0
#define FAILURE -1
#define NO_FLAG 0
#define STR_BUF_SIZE 1024

/**
 * @brief 正規表現によるパターンマッチを行う。
 * @param regex コンパイル済みの正規表現オブジェクト
 * @param target 検索対象の文字列
 * @param match 正規表現パターンマッチ位置を保持する（マッチンググループ情報）。
 * @return SUCCESS：成功、FAILURE：失敗
 */
static int __regexec(regex_t *regex, const char *target, regmatch_t *match)
{
    int err_code = 0;
    char err_msg[STR_BUF_SIZE];

    memset(err_msg, '\0', STR_BUF_SIZE);

    if ((err_code = regexec(regex, target, (regex->re_nsub + ALL_MATCH_STR_NR), match, NO_FLAG)))
    {
        /* regerror()は、regexec()のエラーメッセージを作成する。
         * エラーメッセージサイズはSTR_BUF_SIZEとなるため、文字列バッファサイズを超えない。*/
        regerror(err_code, regex, err_msg, STR_BUF_SIZE);
        fprintf(stderr, "%s: %s\n", __func__, err_msg);
        return FAILURE;
    }
    return SUCCESS;
}

```

異常系の処理において、regerror()によるエラーメッセージを取得しています。

regerror()は、文字列配列のサイズを考慮したメッセージ（メッセージ配列がサイズ不足の場合は途中で打ち切ったエラーメッセージ）を返してくれます。そこまで気の利いたエラーメッセージを返しませんが、お作法という事で紹介します。

regexec()の第5引数はパターンマッチング実行時オプションであり、下表で示すオプションをOR条件として指定できます。今回はオプション無しとしましたが、仕様変更する場合はラッパー関数に引数を増やしてください。

| **実行時オプション** | **説明** |
| :-- | :-- |
| REG\_NOTBOL | 文字列の最初の文字を行の先頭にしない。 |
| REG\_NOTEOL | 文字列の最後の文字を行の末尾にしない。 |

---


### マッチング文字列に対する文字列操作：抽出

前述したように、regmatch\_t構造体の配列\[0\]には正規表現パターン全体にマッチした文字列の情報、配列\[1\]以降にはグループ情報が格納されます。

regmatch\_t構造体にマッチングした文字列が保持される訳ではなく、変数rm\_soにマッチング文字列の先頭オフセット、変数rm\_eoにマッチング文字列の終了オフセットが保持されます。そのため、

- 終了オフセット ― 先頭オフセット = マッチングした文字列サイズ
- 検索対象文字列の開始位置 ＋ 先頭オフセット = マッチング文字列の抽出開始位置

となります。

今回は正規表現を用いた文字列操作の一例として、正規表現パターンマッチングした文字列を抽出する処理を以下に示します。

```
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <regex.h> /* 標準C言語ライブラリ（glibc）が提供する正規表現ライブラリ */

#define SUCCESS 0
#define FAILURE -1
#define NO_FLAG 0
#define STR_BUF_SIZE 1024
#define ALL_MATCH_GROUP 0
#define ALL_MATCH_STR_NR 1
#define NULL_TERMINATION_SIZE 1

/**
 * @brief マッチングした文字列を抽出する。
 * @param target 検索対象の文字列
 * @param regex コンパイル済みの正規表現パターン
 * @param match 正規表現パターンマッチング結果
 * @param result マッチングした文字列
 * @return SUCCESS：成功、FAILURE：失敗
 */
static int extractString(const char *target, regex_t *regex, regmatch_t *match, char *result[])
{
    size_t i = 0;
    size_t extract_nr = regex->re_nsub + ALL_MATCH_STR_NR;
    size_t array_element_size = sizeof(char) * (strlen(target) + NULL_TERMINATION_SIZE);
    size_t str_size = 0;

    /*
     * 抽出文字列の最大サイズは、検索対象文字列のサイズを超えないため、
     * 「抽出文字列の数 * 検索対象文字列サイズ（NULL終端含む）」のメモリ確保を行う。
     *  配列の1次元目（resulu[N][]のN分）は、メモリ確保済みと仮定する。
     */
    mallocStrArray(array_element_size, extract_nr, result);

    for (i = 0; i < extract_nr; i++, match++)
    {
        if ((FAILURE == match->rm_so) || (FAILURE == match->rm_eo))
        {
            printf("No.%ld is not match\n", i);
            continue; /* 開始／終了オフセットが-1の場合は、マッチングしていない */
        }
        str_size = match->rm_eo - match->rm_so;
        strncpy(result[i], (const char *)(&target[match->rm_so]), str_size);
        result[i][str_size] = '\0'; /* 念の為、NULL終端を付与。*/
    }

    return extract_nr;
}

/**
 * @brief 複数の文字列を保持するためメモリ確保を行う（メモリ確保は二次元目のみ）
 * @param size 文字列のサイズ
 * @param element_nr 要素数
 * @param result 文字列操作結果を格納するための二次元配列（二次元目のみ自動でメモリ確保を行う）
 * @return SUCCESS：成功、FAILURE：失敗
 */
static int mallocStrArray(size_t size, int element_nr, char *result[])
{
    size_t i = 0;
    size_t j = 0;

    for (i = 0; i < element_nr; i++)
    {
        result[i] = malloc(sizeof(char) * size);
        if (NULL == result[i])
        {
            /* メモリ確保失敗時は、途中まで確保したメモリを解放する */
            fprintf(stderr, "%s: Can't malloc memory.\n", __func__);
            for (j = 0; j < i; j++)
            {
                free(result[j]);
            }
            return FAILURE;
        }
        memset(result[i], '\0', sizeof(char) * size);
    }
    return SUCCESS;
}

```

マッチング文字列を上位関数に返す方法として、二次元配列を使用しています。一次元目だけユーザにメモリ確保して貰い、二次元目はmallocStrArray()でメモリ確保します。

この方法は手抜き実装のため欠点があり、"一次元配列の要素数＜マッチング文字列の数"となった場合は、Segmentation Faultで死んでしまいます。そのため、

- 文字列リスト（動的にリストを拡張可能）を作成し、二次元配列を文字列リストに置換
- 二次元配列の一次元目も、マッチング文字列を抽出する関数内でメモリ確保

などの設計変更が考えられます。

---


### 今まで登場した正規表現の関数を集約したAPI

正規表現による文字列の抽出や置換の度に、正規表現パターンコンパイルや正規表現オブジェクトの解放処理を実装すると不便なので、それらの処理をAPI（regex()）として集約しました。

regex()は、文字列操作部分を上位関数から引数process（関数ポインタ）として受け取ります。正規表現の実行時フラグに関する柔軟性が落ちていますが、正規表現パターンマッチング用に確保したメモリ確保／解放処理の見通しが良いです（様々な関数にメモリ操作が散らばらない）。

正規表現で加工（今回は抽出）された文字列が二次元配列resultに格納され、regex()の呼び出し元に渡されます。

```
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <regex.h> /* 標準C言語ライブラリ（glibc）が提供する正規表現ライブラリ */

#define SUCCESS 0
#define FAILURE -1
#define NO_FLAG 0
#define STR_BUF_SIZE 1024
#define ALL_MATCH_GROUP 0
#define ALL_MATCH_STR_NR 1
#define NULL_TERMINATION_SIZE 1

/**
 * @brief 正規表現によるパターンマッチを行い、processに応じた文字列操作を行う。
 * @param regex_pattern 正規表現パターン
 * @param target 検索対象の文字列
 * @param result 文字列操作結果を格納するための二次元配列（二次元目のみ自動でメモリ確保を行う）
 * @param process 文字列操作を行う関数へのポインタ
 * @return 正の値（マッチングした文字列の数）：成功、FAILURE：失敗
 * @note 正の値が返った場合は、その数の分だけresultにメモリ確保を行っているため、メモリ解放しなければいけない。
 */
static int regex(const char *regex_pattern, const char *target, char *result[],
                 int (*process)(const char *, regex_t *, regmatch_t *, char **))
{
    int err_code = SUCCESS;
    regex_t regex;
    regmatch_t *match = NULL;

    if (NULL == regex_pattern || NULL == target || NULL == process || NULL == result)
    {
        fprintf(stderr, "%s: Regular expression argument is null.\n", __func__);
        return FAILURE;
    }

    memset(&regex, 0, sizeof(regex_t));

    if ((err_code = __regcomp(&regex, regex_pattern)))
    {
        goto all_end;
    }

    if (NULL == (match = mallocMatchBuf(regex)))
    {
        goto free_regex_obj;
    }

    if ((err_code = __regexec(&regex, target, match)))
    {
        goto free_match_obj;
    }

    /* 置換やマッチング文字の抽出などを関数ポインタに応じて行う */
    err_code = process((const char *)target, &regex, match, result);

free_match_obj:
    free(match);
free_regex_obj:
    regfree(&regex);
all_end:
    return err_code;
}

```

regex()が正常終了した場合は、マッチングした文字列（抽出した文字列）の保持用にメモリ確保を行っているため、regex()の呼び出し元でメモリ解放してもらう必要があります。

呼び出し元でメモリ解放できるよう、regex()はメモリ確保した要素数を返り値として渡します。

\[the\_ad id="598"\]

---


### 実装全体と実行結果

正規表現パターンマッチングによる文字列抽出処理（置換に関する処理なし）の実装全体は、以下の通りとなります。Step数は、約140Stepでした。

他言語における正規表現処理の実装規模と比べて、規模感が数倍以上違う事がお分かりいただけると思います。

```
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <regex.h> /* 標準C言語ライブラリ（glibc）が提供する正規表現ライブラリ */

#define SUCCESS 0
#define FAILURE -1
#define NO_FLAG 0
#define STR_BUF_SIZE 1024
#define ALL_MATCH_GROUP 0
#define ALL_MATCH_STR_NR 1
#define NULL_TERMINATION_SIZE 1

static int __regcomp(regex_t *regex, const char *pattern);
static regmatch_t *mallocMatchBuf(regex_t regex);
static int __regexec(regex_t *regex, const char *target, regmatch_t *match);
static int mallocStrArray(size_t size, int element_nr, char *result[]);
static int extractString(const char *target, regex_t *regex, regmatch_t *match, char *result[]);
static int regex(const char *regex_pattern, const char *target, char *result[],
                 int (*process)(const char *, regex_t *, regmatch_t *, char **));

/**
 * @brief 正規表現パターンのコンパイルを行う。
 * @param regex 正規表現パターンのコンパイル結果を記憶する。通称：正規表現オブジェクト
 * @param pattern 正規表現パターン文字列
 * @return SUCCESS：成功、FAILURE：失敗
 * @note 成功時はregexにメモリを割り当てるため、regfree()によるメモリ解放が必要。
 */
static int __regcomp(regex_t *regex, const char *pattern)
{
    if (regcomp(regex, pattern, REG_EXTENDED))
    {
        fprintf(stderr, "%s: Fail regex pattern(=%s) compile\n",
                __func__, pattern);
        return FAILURE;
    }
    return SUCCESS;
}

/**
 * @brief 正規表現パターンマッチ位置を保持するためのバッファを確保する。
 * @param regex コンパイル済みの正規表現オブジェクト
 * @return NULL以外：成功、NULL：失敗
 * @note 成功時はメモリを割り当てるため、free()によるメモリ解放が必要。
 */
static regmatch_t *mallocMatchBuf(regex_t regex)
{
    regmatch_t *match = NULL;
    /*
     * re_nsubには"("と")"で囲まれたグループの数が格納されている。
     * つまり、正規表現パターン全体にマッチした文字列の数が含まれていない。
     */
    match = (regmatch_t *)malloc(sizeof(regmatch_t) * (regex.re_nsub + ALL_MATCH_STR_NR));
    if (NULL == match)
    {
        fprintf(stderr, "%s: Can't malloc memory.\n", __func__);
        return NULL;
    }
    return match;
}

/**
 * @brief 正規表現によるパターンマッチを行い、その結果を返す。
 * @param regex コンパイル済みの正規表現オブジェクト
 * @param target 検索対象の文字列
 * @param match 正規表現パターンマッチ位置を保持する（マッチンググループ情報）。
 * @return SUCCESS：成功、FAILURE：失敗
 */
static int __regexec(regex_t *regex, const char *target, regmatch_t *match)
{
    int err_code = 0;
    char err_msg[STR_BUF_SIZE];

    memset(err_msg, '\0', STR_BUF_SIZE);

    if ((err_code = regexec(regex, target, (regex->re_nsub + ALL_MATCH_STR_NR), match, NO_FLAG)))
    {
        /* regerror()は、regexec()のエラーメッセージを作成する。
         * エラーメッセージサイズはSTR_BUF_SIZEとなるため、文字列バッファサイズを超えない。*/
        regerror(err_code, regex, err_msg, STR_BUF_SIZE);
        fprintf(stderr, "%s: %s\n", __func__, err_msg);
        return FAILURE;
    }
    return SUCCESS;
}

/**
 * @brief 正規表現によるパターンマッチを行い、processに応じた文字列操作を行う。
 * @param regex_pattern 正規表現パターン
 * @param target 検索対象の文字列
 * @param result 文字列操作結果を格納するための二次元配列（二次元目のみ自動でメモリ確保を行う）
 * @param process 文字列操作を行う関数へのポインタ
 * @return 正の値（マッチングした文字列の数）：成功、FAILURE：失敗
 * @note 正の値が返った場合は、その数の分だけresultにメモリ確保を行っているため、メモリ解放しなければいけない。
 */
static int regex(const char *regex_pattern, const char *target, char *result[],
                 int (*process)(const char *, regex_t *, regmatch_t *, char **))
{
    int err_code = SUCCESS;
    regex_t regex;
    regmatch_t *match = NULL;

    if (NULL == regex_pattern || NULL == target || NULL == process || NULL == result)
    {
        fprintf(stderr, "%s: Regular expression argument is null.\n", __func__);
        return FAILURE;
    }

    memset(&regex, 0, sizeof(regex_t));

    if ((err_code = __regcomp(&regex, regex_pattern)))
    {
        goto all_end;
    }

    if (NULL == (match = mallocMatchBuf(regex)))
    {
        goto free_regex_obj;
    }

    if ((err_code = __regexec(&regex, target, match)))
    {
        goto free_match_obj;
    }

    /* 置換やマッチング文字の抽出などを関数ポインタに応じて行う */
    err_code = process((const char *)target, &regex, match, result);

free_match_obj:
    free(match);
free_regex_obj:
    regfree(&regex);
all_end:
    return err_code;
}

/**
 * @brief 複数の文字列を保持するためメモリ確保を行う（メモリ確保は二次元目のみ）
 * @param size 文字列のサイズ
 * @param element_nr 要素数
 * @param result 文字列操作結果を格納するための二次元配列（二次元目のみ自動でメモリ確保を行う）
 * @return SUCCESS：成功、FAILURE：失敗
 */
static int mallocStrArray(size_t size, int element_nr, char *result[])
{
    size_t i = 0;
    size_t j = 0;

    for (i = 0; i < element_nr; i++)
    {
        result[i] = malloc(sizeof(char) * size);
        if (NULL == result[i])
        {
            /* メモリ確保失敗時は、途中まで確保したメモリを解放する */
            fprintf(stderr, "%s: Can't malloc memory.\n", __func__);
            for (j = 0; j < i; j++)
            {
                free(result[j]);
            }
            return FAILURE;
        }
        memset(result[i], '\0', sizeof(char) * size);
    }
    return SUCCESS;
}

/**
 * @brief マッチングした文字列を抽出する。
 * @param target 検索対象の文字列
 * @param regex コンパイル済みの正規表現パターン
 * @param match 正規表現パターンマッチング結果
 * @param result マッチングした文字列
 * @return SUCCESS：成功、FAILURE：失敗
 */
static int extractString(const char *target, regex_t *regex, regmatch_t *match, char *result[])
{
    size_t i = 0;
    size_t extract_nr = regex->re_nsub + ALL_MATCH_STR_NR;
    size_t array_element_size = sizeof(char) * (strlen(target) + NULL_TERMINATION_SIZE);
    size_t str_size = 0;

    /*
     * 抽出文字列の最大サイズは、検索対象文字列のサイズを超えないため、
     * 「抽出文字列の数 * 検索対象文字列サイズ（NULL終端含む）」のメモリ確保を行う。
     *  配列の1次元目（resulu[N][]のN分）は、メモリ確保済みと仮定する。
     */
    mallocStrArray(array_element_size, extract_nr, result);

    for (i = 0; i < extract_nr; i++, match++)
    {
        if ((FAILURE == match->rm_so) || (FAILURE == match->rm_eo))
        {
            printf("No.%ld is not match\n", i);
            continue; /* 開始／終了オフセットが-1の場合は、マッチングしていない */
        }
        str_size = match->rm_eo - match->rm_so;
        strncpy(result[i], (const char *)(&target[match->rm_so]), str_size);
        result[i][str_size] = '\0'; /* 念の為、NULL終端を付与。*/
    }

    return extract_nr;
}

int main(void)
{
    size_t i = 0;
    size_t size = 0;
    char *result[100];
    char pattern[] = "(aa)(b(bc)(c))(dd)";
    char target[] = "aabbccdd";

    printf("===条件===\n");
    printf("  正規表現パターン：%s\n", pattern);
    printf("  検索対象の文字列：%s\n", target);
    size = regex(pattern, target, result, extractString);
    if (FAILURE == size)
    {
        return EXIT_FAILURE;
    }

    printf("===結果===\n");
    for (i = 0; i < size; i++)
    {
        printf("  マッチNo.%d　結果=%s\n", i, result[i]);
        free(result[i]);
    }

    return 0;
}

```

実行結果は以下の通りです。

```
===条件===
  正規表現パターン：(aa)(b(bc)(c))(dd)
  検索対象の文字列：aabbccdd
===結果===
  マッチNo.0　結果=aabbccdd
  マッチNo.1　結果=aa
  マッチNo.2　結果=bbcc
  マッチNo.3　結果=bc
  マッチNo.4　結果=c
  マッチNo.5　結果=dd

```

---


### 最後に

現実問題として、以下の部分は仕様変更／機能追加しないと、本記事で説明したregex()は汎用的に使用できません。

本記事の説明から仕様変更／機能追加が必要な点

1. regex()の引数であるprocess関数ポインタの引数追加（および置換処理の追加）
2. 正規表現パターンマッチング結果の返し方
3. 特定の正規表現パターンを拒否

1つ目に関しては、process関数ポインタはユーザから受け取る情報が少ないです。例えば、マッチングした文字列を置換する場合、上位関数から置換後の文字列を受け取る必要がありますが、その手段がprocess関数ポインタにはありません。正規表現の実行時フラグも制御できないので、上位関数から正規表現の実行条件を構造体で受け取るなどの仕様変更が考えられます。

2つ目に関しては、前述しましたが、パターンマッチング文字列を二次元配列に格納する際にSegmentation Faultする可能性があります。上位関数でfor文を回して二次元配列のメモリ解放する仕様もイケてないと思うので、二次元配列を文字列リストに置き換えた方が便利です。

C言語における文字列リストの取り扱い方法は、Linux Kernelの実装が参考になります。興味があれば、以下をご確認ください。

- [Linux Kernel: List構造を操作するためのAPI(Listの使い方)](https://debimate.jp/post/2019-04-07-linux-kernel-list%E6%A7%8B%E9%80%A0%E3%82%92%E6%93%8D%E4%BD%9C%E3%81%99%E3%82%8B%E3%81%9F%E3%82%81%E3%81%AEapilist%E3%81%AE%E4%BD%BF%E3%81%84%E6%96%B9/)

3つ目に関しては、glibcのregexec()は長すぎる正規表現パターン（正規表現オブジェクト）を受け取るとSegmentation Faultする事があるそうです。TerminalやGUIから正規表現パターンを受け取って正規表現パターンマッチングを行う場合は、注意が必要です。

---


### 最後の最後に一言だけ言わせて

本記事のサンプルコードを書き切るまでに、滅茶苦茶セグフォした（確保したメモリの返し方や二次元配列の操作をミスった）。
