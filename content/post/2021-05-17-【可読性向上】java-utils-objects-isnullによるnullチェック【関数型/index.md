---
title: "【可読性向上】java.utils.Objects.isNull()によるnullチェック【関数型プログラミングに便利】"
type: post
date: 2021-05-17
categories:
  - "linux"
tags:
  - "java"
cover:
  image: "images/finger-3026348_640.jpg"
  alt: "【可読性向上】java.utils.Objects.isNull()によるnullチェック【関数型プログラミングに便利】"
  hidden: false
---

## 前書き："=="や"!="による判定と何が違う？

Javaでコードを書くと、nullチェック（NullPointerException防止）は避けられません。

私のようにC言語脳の人は、"=="（等価演算子）や"!="（不等価演算子）を用いてnullチェックを行うかもしれません。しかし、[Java SE8](https://docs.oracle.com/javase/jp/8/docs/api/)以降は、null関係の判定メソッドとして[java.utils.Objects](https://docs.oracle.com/javase/jp/8/docs/api/java/util/Objects.html)にisNull()やnonNull()が用意されています。

「演算子使わずにnullチェックするメリットがあるのか？（新しい方法のメリットが分からない）」と思われる方がいらっしゃるかもしれませんが、主に２点メリットがあります。

nullチェックにisNull()やnonNull()を使うメリット

- ソースコードの可読性向上
- 演算子を用いるよりも関数型プログラミングが書きやすい

本記事では、Java SE11環境で「従来の演算子を用いたnullチェック方法」と「isNull()やnonNull()を用いた方法」を比較します。また、関数型プログラミングにおけるnullチェック方法に関しても説明します。

## 演算子を用いたnullチェック方法

以下のサンプルコードでは、文字列リストの内容を表示します。

文字列リストの表示前は、

- 文字列リストのnullチェック（"=="によるチェック）
- リストから取り出した文字列に対するnot nullチェック（"!="によるチェック）

を行います。

```
import java.util.List;
import java.util.Arrays;

public class App {
    public static void main(String[] args) {
        List<String> names = Arrays.asList("Rance", null, "Sill Plain", "KENTO Kanami", null, "Ria Parapara-Leazas" );
        System.out.println("===Argument is not null List===");
        printStr(names);
        System.out.println("===Argument is null.===");
        printStr(null);
        System.out.println("===The end.===");
    }

    /**
     * 文字列リストの内容を表示する。Listがnullの場合は、何も表示されない。
     * Listの要素がnullの場合はその要素はスキップされる。
     * @param strs 文字列リスト
     */
    private static void printStr(List<String> strs) {
        if(strs == null) {
            return;
        }
        for(String str: strs) {
            if(str != null) {
                System.out.println(str);
            }
        }
    }
}
```

以下が実行結果です。文字列リストがnullの場合は何も出力されず、リストの要素がnullの場合は文字列出力がバイパスされます。

```
===Argument is not null List===
Rance
Sill Plain
KENTO Kanami
Ria Parapara-Leazas
===Argument is null.===
===The end.===
```

## isNull()およびnonNull()を用いたnullチェック 

文字列リスト内容を出力する前述のコード（printStr()）をisNull()およびnonNull()で書き換えます。

なお、isNull(Object obj)はobjがnullの場合にtrueを返し、objが非nullの場合はfalseを返します。nonNull(Object obj)は、その逆の動作、すなわち! isNull()となります。

以下、サンプルコードです。

```
import java.util.List;
import java.util.Objects;
import java.util.Arrays;

public class App {
    public static void main(String[] args) {
        List names = Arrays.asList("Rance", null, "Sill Plain", "KENTO Kanami", null, "Ria Parapara-Leazas" );
        System.out.println("===Argument is not null List===");
        printStr(names);
        System.out.println("===Argument is null.===");
        printStr(null);
        System.out.println("===The end.===");
    }

    /**
     * 文字列リストの内容を表示する。Listがnullの場合は、何も表示されない。
     * Listの要素がnullの場合はその要素はスキップされる。
     * @param strs 文字列リスト
     */
    private static void printStr(List strs) {
        if(Objects.isNull(strs)) { // "strs == null"
            return;
        }
        for(String str: strs) {
            if(Objects.nonNull(str)) {  // "str != null"
                System.out.println(str);
            }
        }
    }
}

```

出力結果に違いはありません。

isNull()およびnonNull()を用いた方が自然言語（英語）で処理内容が記載されているため、可読性が高いです。個人的な印象としては、上記のコードはPythonライクに見えます。

なお、上記のような判定処理でisNull()／nonNull()を用いるのは冗長という意見もあります。

## 関数型プログラミングでのisNull()／nonNull()

[Java Core API（Javadoc）](https://docs.oracle.com/javase/jp/8/docs/api/java/util/Objects.html)の説明にある通り、isNull()とnonNull()は[Stram API](https://docs.oracle.com/javase/jp/11/docs/api/java.base/java/util/stream/package-summary.html)で使用するために設計されています。

> このメソッドは、[`Predicate`](https://docs.oracle.com/javase/jp/8/docs/api/java/util/function/Predicate.html "java.util.function内のインタフェース")(`filter(Objects::isNull)`)として使用するために存在します。

Streamを用いた処理は、以下の３工程に大別され、従来のfor文を用いたループ処理よりも簡潔かつ可読性の高いコードを作りやすいです。

1. Stream生成：Collectionや配列から生成
2. 中間処理     ：フィルター／加工／nullチェックなど
3. 終端処理     ：集計／出力など

以下のサンプルコードでは、Integer型リストに格納された各要素の総和を求める処理をStream APIで記述しています。総和を求めるsum()メソッド内のfilter()処理でリスト要素のnot null判定をしています。

```
import java.util.List;
import java.util.Objects;
import java.util.Arrays;
import java.util.Collection;

public class App {
    public static void main(String[] args) {
        List numbers = Arrays.asList(1, null, 2, 3, null, 4);
        System.out.println("===Calculate list==");
        System.out.println(sum(numbers));
        System.out.println("===Argument is null.===");
        System.out.println(sum(null));
        System.out.println("===The end.===");
    }

    /**
     * Integer型リストの和を返す。
     * @param integers Integer型のリスト
     * @return Integerリストの和を返す。リストがnullの場合は0を返す。
     */
    public static int sum(List integers) {
        if (Objects.isNull(integers)) {
            return 0;
        }
        return integers.stream()
            .filter(Objects::nonNull)  // 別の書き方は.filter(i -> i != null)
            .mapToInt(Integer::intValue).sum();
        }
}

```

以下が実行結果です。Integer型リストがnullの場合は0が出力され、リストの要素がnullの場合はその要素はフィルタリング（除外）されます。

```
===Calculate list==
10
===Argument is null.===
0
===The end.===

```

フィルタリング処理を「filter(i -> i != null)」と書くより、「filter(Objects::nonNull) 」と書いた方がパッと見で処理を理解しやすい筈です。

## おまけ：requireNonNull()

[requireNonNull(T obj)](https://docs.oracle.com/javase/jp/8/docs/api/java/util/Objects.html)は、指定されたオブジェクトがnullでない事を検査するメソッドです。引数がnullではない場合はobjをそのまま返しますが、nullの場合はNullPointerExceptionをスローします。

第二引数に、例外発生時のメッセージを指定できます。

> ```
>  public Foo(Bar bar, Baz baz) {
>      this.bar = Objects.requireNonNull(bar, "bar must not be null");
>      this.baz = Objects.requireNonNull(baz, "baz must not be null");
>  }
> ```

## 後書き

Javaを書く限りはnullチェックが必要ですが、C言語に比べるとJavaはAPIが揃っているので、まだマシと言えるでしょう。

ちなみに、nullチェックを不要にするAPIとして、[java.util.Optional](https://docs.oracle.com/javase/jp/8/docs/api/java/util/Optional.html)もあります。
