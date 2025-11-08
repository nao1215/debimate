---
title: "【Java】enum（列挙子）の持つメソッド、基本的な使い方、応用（シングルトン）【実装例付き】"
type: post
date: 2021-02-21
categories:
  - "linux"
tags:
  - "enum"
  - "java"
cover:
  image: "images/athletic-field-1867053_640-min.jpg"
  alt: "【Java】enum（列挙子）の持つメソッド、基本的な使い方、応用（シングルトン）【実装例付き】"
  hidden: false
---

## 前書き：君、C言語のenumと雰囲気違うね

仕事でJavaのコードを読んでいる時、「Javaのenumは、C言語のenumより多機能だな」と感じる場面がありました。

Javaのenumを多機能と感じた例として、以下の3点が挙げられます。

- enumにメソッドがある（メソッドを実装できる）
- 複数のフィールド（変数）を持てる
- シングルトンを作成する際にenumを使用する

他の言語と比較しても多機能なJavaのenumに関して、本記事では基本的な使い方から応用（シングルトンとして利用する方法）まで順番に説明していきます。

## enumが持つメソッド一覧

[Java SE11のjava.baseモジュールのjava.lang.Enum](https://docs.oracle.com/javase/jp/11/docs/api/java.base/java/lang/Enum.html)には、下表のメソッドが定義されています。例外を投げるclone()、実装できないfinalize()を除いて、下表のメソッドの実装例／実行結果を順に示します。

| **No.** | **メソッド名** | **返り値の型** | **説明** |
| :-- | :-- | :-- | :-- |
| 1 | clone() | Object | Clone不可。CloneNotSupportedExceptionをスロー。 |
| 2 | compareTo(E o) | int | enum定数の順序を比較 |
| 3 | equals(Object other) | boolean | enum定数が同じかどうかをチェック |
| 4 | finalize() | void | finalizeメソッドを持てない |
| 5 | getDeclaringClass() | Class<E> | enum定数のenum型に対応するClassオブジェクトを返す |
| 6 | hashCode() | int | enum定数のハッシュコードを返す |
| 7 | name() | String | enum定数の名前を返す |
| 8 | ordinal() | int | enum定数の序数（番号）を返す |
| 9 | toString() | String | enum定数の名前を返す |
| 10 | valueOf(Class<T> enumType, String name) | Enum<T> | 指定された名前のenum定数を返す |

compareTo()メソッド 

enum定数の序列（番号）の差を結果として返しますが、直感的ではないので使いづらい印象です。

```
public class App {
    enum Actor {
        GINA, YULIA, LUCIE
    }

    public static void main(String[] args) {
        Actor gina = Actor.GINA;
        Actor yulia = Actor.YULIA;
        Actor lucie = Actor.LUCIE;

        System.out.println("GINA == GINA:" + gina.compareTo(Actor.GINA));
        System.out.println("GINA == YULIA:" + gina.compareTo(Actor.YULIA));
        System.out.println("GINA == LUCIE:" + gina.compareTo(Actor.LUCIE));
        System.out.println("YULIA == GINA:" + yulia.compareTo(Actor.GINA));
        System.out.println("YULIA == YULIA:" + yulia.compareTo(Actor.YULIA));
        System.out.println("YULIA == LUCIE:" + yulia.compareTo(Actor.LUCIE));
        System.out.println("LUCIE == GINA:" + lucie.compareTo(Actor.GINA));
        System.out.println("LUCIE == YULIA:" + lucie.compareTo(Actor.YULIA));
        System.out.println("LUCIE == LUCIE:" + lucie.compareTo(Actor.LUCIE));
    }
}
```

```
GINA == GINA:0
GINA == YULIA:-1
GINA == LUCIE:-2
YULIA == GINA:1
YULIA == YULIA:0
YULIA == LUCIE:-1
LUCIE == GINA:2
LUCIE == YULIA:1
LUCIE == LUCIE:0

```

getDeclaringClass() 

enum定数が定義されているファイル名とenum名を返します。

```
public class App {
    enum Actor {
        GINA, YULIA, LUCIE
    }

    public static void main(String[] args) {
        Actor gina = Actor.GINA;
        Actor yulia = Actor.YULIA;
        Actor lucie = Actor.LUCIE;

        System.out.println("GINA's class = " + gina.getDeclaringClass());
        System.out.println("YULIA's class = " + yulia.getDeclaringClass());
        System.out.println("LUCIE's class" + lucie.getDeclaringClass());
    }
}

```

```
GINA's class = class Test.App$Actor
YULIA's class = class Test.App$Actor
LUCIE's classclass Test.App$Actor

```

equals()メソッド 

equals()メソッドを使用しなくても、"=="で比較できます。

```
public class App {
    enum Actor {
        GINA, YULIA, LUCIE
    }

    public static void main(String[] args) {
        Actor gina = Actor.GINA;
        Actor yulia = Actor.YULIA;
        Actor lucie = Actor.LUCIE;

        System.out.println("GINA == GINA:" + gina.equals(Actor.GINA));
        System.out.println("GINA == YULIA:" + gina.equals(Actor.YULIA));
        System.out.println("GINA == LUCIE:" + gina.equals(Actor.LUCIE));
        System.out.println("YULIA == GINA:" + yulia.equals(Actor.GINA));
        System.out.println("YULIA == YULIA:" + yulia.equals(Actor.YULIA));
        System.out.println("YULIA == LUCIE:" + yulia.equals(Actor.LUCIE));
        System.out.println("LUCIE == GINA:" + lucie.equals(Actor.GINA));
        System.out.println("LUCIE == YULIA:" + lucie.equals(Actor.YULIA));
        System.out.println("LUCIE == LUCIE:" + lucie.equals(Actor.LUCIE));

        System.out.println("");
        System.out.println("---以下、補足(==による比較)---");
        System.out.printf("GINA == GINA:%b\n", gina == Actor.GINA);
        System.out.printf("GINA == YULIA:%b\n", gina == Actor.YULIA);
        System.out.printf("GINA == LUCIE:%b\n", gina == Actor.LUCIE);
    }
}
```

```
GINA == GINA:true
GINA == YULIA:false
GINA == LUCIE:false
YULIA == GINA:false
YULIA == YULIA:true
YULIA == LUCIE:false
LUCIE == GINA:false
LUCIE == YULIA:false
LUCIE == LUCIE:true

---以下、補足(==による比較)---
GINA == GINA:true
GINA == YULIA:false
GINA == LUCIE:false

```

hashCode()メソッド 

enum定数のハッシュ値を算出します。

ハッシュ値は、ハッシュテーブル探索(HashMap、HashSet)で使用されるため、以下の条件を満たして実装する必要があります（enumの場合は、デフォルトで条件を満たしています）

- equals() の結果で true を返すオブジェクトは、同じハッシュ値である事
- ハッシュ値が異なる場合は、equals() の結果で false を返す事
- equals() の結果でfalse を返すオブジェクト（複数）が、同じハッシュ値を返しても良い

```
public class App {
    enum Actor {
        GINA, YULIA, LUCIE
    }

    public static void main(String[] args) {
        Actor gina = Actor.GINA;
        Actor yulia = Actor.YULIA;
        Actor lucie = Actor.LUCIE;

        System.out.printf("GINA hashcode = %d\n", gina.hashCode());
        System.out.printf("YULIA hashcode = %d\n", yulia.hashCode());
        System.out.printf("LUCIE hashcode = %d\n", lucie.hashCode());
    }
}
```

```
GINA hashcode = 1878246837
YULIA hashcode = 523429237
LUCIE hashcode = 664740647

```

name()メソッド 

enum定数の定義名称を返します。

ユーザフレンドリーな名称を返すには、toString()メソッドを使用した方が良いとAPIドキュメントに書かれています。

つまり、ユーザフレンドリーな文字列を返すようにtoString()メソッドをオーバライドし、name()メソッドの使用を控えた方が好ましいという事です。toString()をオーバライドする例は、toString()メソッドの実装例として後述します。

```
public class App {
    enum Actor {
        GINA, YULIA, LUCIE
    }

    public static void main(String[] args) {
        Actor gina = Actor.GINA;
        Actor yulia = Actor.YULIA;
        Actor lucie = Actor.LUCIE;

        System.out.printf("GINA = %s\n", gina.name());
        System.out.printf("YULIA = %s\n", yulia.name());
        System.out.printf("LUCIE = %s\n", lucie.name());
    }
}
```

```
GINA = GINA
YULIA = YULIA
LUCIE = LUCIE

```

ordinal()メソッド 

enum定数の序数（番号）を返します。序数は、0オリジンであり、enum定数が増えるとインクリメントされる仕様です。

```
public class App {
    enum Actor {
        GINA, YULIA, LUCIE
    }

    public static void main(String[] args) {
        Actor gina = Actor.GINA;
        Actor yulia = Actor.YULIA;
        Actor lucie = Actor.LUCIE;

        System.out.printf("GINA = %s\n", gina.ordinal());
        System.out.printf("YULIA = %s\n", yulia.ordinal());
        System.out.printf("LUCIE = %s\n", lucie.ordinal());
    }
}
```

```
GINA = 0
YULIA = 1
LUCIE = 2

```

toString()メソッド 

toString()メソッドは、オーバライドしていなければname()と同じ結果を返します。

以下の例では、toString()メソッドをオーバライドし、name()メソッドとは異なる文字列を返します。今までの実装と異なる箇所は、以下の3点です。

- enum定数ごとに文字列（変数name）を持つ
- toString()は、変数nameをそのまま返す
- コンストラクタの公開範囲はprivate

```
public class App {
    enum Actor {
        GINA("Gina Gerson"), YULIA("Yulia Nova"), LUCIE("Lucie Wilde");

        private final String name;

        private Actor(final String name) {
            this.name = name;
        }

        @Override
        public String toString() {
            return name;
        }
    }

    public static void main(String[] args) {
        Actor gina = Actor.GINA;
        Actor yulia = Actor.YULIA;
        Actor lucie = Actor.LUCIE;

        System.out.println("[name()]");
        System.out.printf("GINA = %s\n", gina.name());
        System.out.printf("YULIA = %s\n", yulia.name());
        System.out.printf("LUCIE = %s\n\n", lucie.name());

        System.out.println("[toString()]");
        System.out.printf("GINA = %s\n", gina.toString());
        System.out.printf("YULIA = %s\n", yulia.toString());
        System.out.printf("LUCIE = %s\n", lucie.toString());
    }
}
```

```
[name()]
GINA = GINA
YULIA = YULIA
LUCIE = LUCIE

[toString()]
GINA = Gina Gerson
YULIA = Yulia Nova
LUCIE = Lucie Wilde

```

values()メソッド 

enum定数の名称を全て返します。

```
public class App {
    enum Actor {
        GINA, YULIA, LUCIE
    }

    public static void main(String[] args) {
        System.out.println("[Actor List up]");
        for (Actor actor : Actor.values()) {
            System.out.println("---" + actor);
        }
    }
}
```

```
[Actor List up]
---GINA
---YULIA
---LUCIE

```

## C言語ライクな使い方の例

Javaのenumの最も単純な使い方の例として、enum Actor（役者）を定義して、whoメソッドの引数がどの役者であったかを判定するプログラムを以下に示します。

enum Actor {}部分の実装は、C言語であれば連番を1から順に割り当てている状態です。

```
public class App {
    enum Actor {
        GINA, YULIA, LUCIE
    }

    private static void who(Actor actor) {
        switch (actor) {
            case GINA:
                System.out.println("I'm GINA");
                break;
            case YULIA:
                System.out.println("I'm YULIA");
                break;
            case LUCIE:
                System.out.println("I'm LUCIE");
                break;
            default: // 通せない。defaultを消すのが正しい。
                System.out.println("who are you?");
                break;
        }
    }

    public static void main(String[] args) {
        try {
            who(Actor.valueOf("GINA"));
            who(Actor.valueOf("YULIA"));
            who(Actor.LUCIE);
            who(Actor.valueOf("Katyuska Moon Fox"));
        } catch (IllegalArgumentException e) {
            System.out.println("Can't convert string.");
            System.out.println(e);
        }
}
```

enum定数を指定（例：Actor.LUCIE）して、whoメソッドにActorクラスとして引数渡しできます。この使い方は、C言語と比較して違和感がありません。

実行結果を以下に示します。

```
I'm GINA
I'm YULIA
I'm LUCIE
Can't convert string.
java.lang.IllegalArgumentException: No enum constant Test.App.Actor.Katyuska Moon Fox

```

## enum定数が数値と文字列を持つ例（C言語では不可）

C言語ではenum定数に複数の値を持たせられませんが、Javaでは複数の変数を持たせられます。変数の内容を渡すgetterメソッドを追加する事もできます。

複数の変数を持てるので、「国名や国コード（例：日本, +81）」、「バージョンとバージョン名称（11, Bullseye）」など、組み合わせが決まっているものをenumで表現しやすくなります。

以下の例では、曜日とIDを変数として持つenumの例です。各変数には、getterメソッドを追加しています。

```
public class App {
    enum Week {
        MONDAY(0, "月曜日"), TUESDAY(1, "火曜日"), WEDNESDAY(2, "水曜日"), 
        THUESDAY(3, "木曜日"), FRIDAY(4, "金曜日"),
        SATURDAY(5, "土曜日"), SUNDAY(6, "日曜日");

        private final Integer id;
        private final String name;

        private Week(final Integer id, final String name) {
            this.id = id;
            this.name = name;
        }

        public Integer getId() {
            return id;
        }

        public String getName() {
            return name;
        }

        @Override
        public String toString() {
            return id.toString() + ":" + name;
        }
    }

    public static void main(String[] args) {
        System.out.printf("%d:%s\n", Week.MONDAY.getId(), Week.MONDAY.getName());
        System.out.printf("%d:%s\n", Week.TUESDAY.getId(), Week.TUESDAY.getName());
        System.out.printf("%d:%s\n", Week.WEDNESDAY.getId(), Week.WEDNESDAY.getName());
        System.out.printf("%d:%s\n", Week.THUESDAY.getId(), Week.THUESDAY.getName());
        System.out.printf("%d:%s\n", Week.FRIDAY.getId(), Week.FRIDAY.getName());
        System.out.printf("%d:%s\n", Week.SATURDAY.getId(), Week.SATURDAY.getName());
        System.out.printf("%d:%s\n", Week.SUNDAY.getId(), Week.SUNDAY.getName());

        System.out.println("");
        System.out.println("[toString]");
        System.out.println(Week.MONDAY.toString());
        System.out.println(Week.TUESDAY.toString());
        System.out.println(Week.WEDNESDAY.toString());
        System.out.println(Week.THUESDAY.toString());
        System.out.println(Week.FRIDAY.toString());
        System.out.println(Week.SATURDAY.toString());
        System.out.println(Week.SUNDAY.toString());
    }
}
```

実行結果は、以下の通りです。

```
0:月曜日
1:火曜日
2:水曜日
3:木曜日
4:金曜日
5:土曜日
6:日曜日

[toString]
0:月曜日
1:火曜日
2:水曜日
3:木曜日
4:金曜日
5:土曜日
6:日曜日

```

## 応用：enumでシングルトンを作成

Javaの言語仕様上、Enumがグローバルに唯一のインスタンスとなる事が保証されます。Enumは、厳密なSingletonであり、スレッドセーフかつabstractな実装もできます。

シングルトンを作成する方法に関して、以下の記事で紹介しています。

- [【Singeltonパターン】考え方は単純だが、使いどころが大切なデザインパターン【コード例はRubyとJava】](https://debimate.jp/post/2020-04-26-singelton%E3%83%91%E3%82%BF%E3%83%BC%E3%83%B3%E8%80%83%E3%81%88%E6%96%B9%E3%81%AF%E5%8D%98%E7%B4%94%E3%81%A0%E3%81%8C%E4%BD%BF%E3%81%84%E3%81%A9%E3%81%93%E3%82%8D%E3%81%8C/)

##  後書き

Javaのenumは、拡張性が高すぎる印象です。使い方の方針を予め考えておかないと、過剰設計なプログラムを産み出しそうです。
