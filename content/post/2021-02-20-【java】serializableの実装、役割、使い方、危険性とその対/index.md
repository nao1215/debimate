---
title: "【Java】Serializableの実装、役割、使い方、危険性とその対策【serialVersionUIDとは】"
type: post
date: 2021-02-20
categories:
  - "linux"
tags:
  - "java"
  - "serializable"
cover:
  image: "images/puzzle-654957_640-min.jpg"
  alt: "【Java】Serializableの実装、役割、使い方、危険性とその対策【serialVersionUIDとは】"
  hidden: false
---

### 前書き： Javaの勉強中に見つけたSerializable

2021年になってから、腰を据えてJavaの勉強を始めました。

<blockquote class="twitter-tweet"><p dir="ltr" lang="ja">今年はJavaを後輩に教える機会があり、自分もJava歴が短くて手探り感がある。勉強が必要だ。<br><br>JavaのOSS（小規模）を読みたいが、何か良いものはないかなー。以前、「Apacheのコードを読もう！」と考えた時期があった記憶もある。が、もう少し小規模なプロジェクトから始めたい。</p>— Nao03@疲れて会話がUDP (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1358326056193724416?ref_src=twsrc%5Etfw">February 7, 2021</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

私はJava学習の一環として[Java Core API](https://docs.oracle.com/javase/jp/13/docs/api/index.html)のソースコードを読んでおり、その際にjava.io.FileクラスでSerializableインターフェースをimplementsしている記述を見かけました。

```
public class File implements Serializable, Comparable<File> {}
```

「Serializableインターフェースは、クラスをByte配列に変換するために用いる」という理解でしたが、詳細な内容については知識がありませんでした。

そのため、本記事ではSerializableインターフェースに関する調査内容を紹介します。

### Serializableインターフェースの実装

[Serializableインターフェース](https://docs.oracle.com/javase/jp/11/docs/api/java.base/java/io/Serializable.html)は、[java.baseモジュールのjava.ioパッケージ](https://docs.oracle.com/javase/jp/11/docs/api/java.base/java/io/package-summary.html)に実装があります。

中身は空のため、インターフェースを実装するクラスに特定の属性を付与するためのマーカーインタフェースである事が分かります。

```
public interface Serializable {}
```

### Serializableインターフェースの役割

Serializableインターフェースを継承したクラスは、そのクラス自体をByte配列（シリアライズされたデータ）として他の仮想マシンに送信したり、ファイルとして保存できます。Byte配列をデシリアライズ（クラスに復元）する事もできます。

データを可搬性（ポータビリティ）のある形にしたい時、使用するイメージです。

Serializableインターフェースの役割（機能）

- オブジェクト（データ）をシリアライズ／デシリアライズ可能
- シリアライズしたデータは、Byte配列として送信可能
- シリアライズしたデータは、ファイルとして書き出し可能　　　　

※ 正確には、ObjectOutputStreamクラス／ObjectInputStreamクラスがSerializableインターフェースを実装したクラスをシリアライズ／デシリアライズします。

### シリアライズ対象／対象外のデータ 

クラスには、大別してメソッド（関数）とフィールド（変数）があります。この中で、シリアライズされるデータ／シリアライズされないデータは以下の通りです。

- **シリアライズ対象**　：フィールド
- **シリアライズ対象外**：メソッド、static修飾子やtransient修飾子の付いたフィールド

以上を踏まえ、サンプルクラスを以下に示します（serialVersionUIDの説明は、後述します）。

```
class SampleSerial implements Serializable {
    private static final long serialVersionUID = -2170800526658571026L; // シリアライズ対象外
    private int age; // シリアライズ対象
    private String sex; // シリアライズ対象
    private transient String company; // シリアライズ対象外

    // シリアライズ対象外
    SampleSerial() {
        this.age = -1;
        this.sex = "";
        this.company = "";
    }

    // シリアライズ対象外
    SampleSerial(int age, String sex, String company) {
        this.age = age;
        this.sex = sex;
        this.company = company;
    }

    // シリアライズ対象外
    @Override
    public String toString() {
        String str = "Age:" + age + "\n"
                    + "Sex:" + sex + "\n"
                    + "Company:" + company + "\n";
        return str;
    }
}
```

### serialVersionUIDとは

serialVersionUIDは、シリアライズしたデータのバージョン情報です。

異なるバージョンのシリアライズデータのデシリアライズを試みた場合、InvalidClassExceptionが発生します。基本的には、クラスに変更が加わったタイミングでバージョンを変更します。未定義の場合は、コンパイラがWarningを出します。

一般的には人間がserialVersionUIDを手動で追加せず、エディタやIDEの自動生成機能でlong型の数値を定義します。Eclipse、IntelliJ IDE、Visual Studio Codeは、serialVersionUIDの自動生成に対応しています。

バージョン管理が不要な場合は、@SuppressWarningsでWarningを抑制できます。

```
@SuppressWarnings("serial")
class SampleSerial implements Serializable {
  // (省略)
}
```

### シリアライズ／デシリアライズの実装例

実装例として、Serializableインターフェースを実装したSampleSerialクラスをserial.serバイナリとしてシリアライズし、serial.serバイナリをデシリアライズするコードを以下に示します。

なお、シリアライズしたバイナリの拡張子は、慣習的に".ser"とするようです。

```
import java.io.Serializable;

import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.ObjectOutputStream;
import java.io.FileInputStream;
import java.io.ObjectInputStream;

class SampleSerial implements Serializable {
    private static final long serialVersionUID = -2170800526658571026L; // シリアライズ対象外
    private int age; // シリアライズ対象
    private String sex; // シリアライズ対象
    private transient String company; // シリアライズ対象外

    // シリアライズ対象外
    SampleSerial() {
        this.age = -1;
        this.sex = "";
        this.company = "";
    }

    // シリアライズ対象外
    SampleSerial(int age, String sex, String company) {
        this.age = age;
        this.sex = sex;
        this.company = company;
    }

    // シリアライズ対象外
    @Override
    public String toString() {
        String str = "Age:" + age + "\n"
               + "Sex:" + sex + "\n"
               + "Company:" + company + "\n";
        return str;
    }
}

public class App {

    static final String serialFile = "./serial.ser";

    public static void main(String[] args) {
        SampleSerial serial_1 = new SampleSerial(30, "man", "unknown");
        SampleSerial serial_2 = new SampleSerial();

        System.out.println("[元データ]\n" + serial_1.toString());
        System.out.println("[デシリアライズ前]\n" + serial_2.toString());

        mkSerialFile(serial_1);
        serial_2 = readSerialFile();

        System.out.println("[デシリアライズ後]\n" + serial_2.toString());
    }

    // シリアライズ化したファイル（serial.ser）を作成
    private static void mkSerialFile(Object obj) {
        try (FileOutputStream fileOutStream = new FileOutputStream(serialFile);
                ObjectOutputStream outStream = new ObjectOutputStream(fileOutStream)) {
            outStream.writeObject(obj);
            outStream.flush();
            outStream.reset();
        } catch (FileNotFoundException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    // シリアライズ化したファイル（serial.ser）をクラスにデシリアライズ
    private static SampleSerial readSerialFile() {
        SampleSerial ss = new SampleSerial();

        try (FileInputStream fileInStream = new FileInputStream(serialFile);
                ObjectInputStream inStream = new ObjectInputStream(fileInStream)) {
            ss = (SampleSerial) inStream.readObject();

        } catch (ClassNotFoundException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return ss;
    }
}

```

実行例は、以下の通りです。

```
[元データ]
Age:30
Sex:man
Company:unknown

[デシリアライズ前]
Age:-1
Sex:
Company:

[デシリアライズ後]
Age:30
Sex:man
Company:null

```

デシリアライズ前後で、SampleSerialインスタンスのフィールド情報が変化している事が分かります。transient修飾子を付けたフィールド（company）は、シリアライズされていないため、デシリアライズ後にnullとなっています。

なお、serial.serバイナリは、以下の状態で出力されていました。

```
��srTest.SampleSerial���l"H��IageLsextLjava/lang/String;xptmany

```

### Serializableインターフェースの危険性と対策

[Effective Java（第三版）](https://amzn.to/3blJ2qw)で触れられていますが、Serializableインターフェース（正確にはデシリアライズ処理）は、悪意を持ったプログラムの攻撃対象となる可能性が高いです。

[改変されたシリアライズデータをデシリアライズしてしまう](https://www.jpcert.or.jp/java-rules/ser13-j.html)と、セキュリティ問題を引き起こす可能性があります（例：[デシリアライズを悪用したリモートコード実行](https://www.infoq.com/jp/news/2015/11/commons-exploit/)）。下手に実装すると、脆弱性のあるプログラムとなってしまいます。

では、どのように対策すべきかと言えば、以下の項目が一般的のようです。

シリアライズ／デシリアライズに対するセキュリティ対策

- 意図しないデータ／クラスのデシリアライズを避ける
- セキュリティマネージャによるチェックを必ず実施する
- シリアライズ／デシリアライズの代替手段として、json形式を使用する

[JPCERT CCで様々な対策](https://www.jpcert.or.jp/java-rules/#c13)が示されていますが、どれも「難しい事を簡単そうに言ってくれますね」という印象です（個人の感想です）。

そもそも、シリアライズ／デシリアライズを利用しなければいけない場面は、あまり多くはありません。パッと思いつくのは、ネットワークに関する低レイヤーのアプリぐらいです。もしくは、難読化を施したいデータ（例：ゲームのセーブデータなど）でしょうか。

そのため、プログラム言語や環境を選ばないjson形式でデータのやり取りを実施した方が現代的と思われます。Web APIは殆どがjson形式ですし、ネット上の知見の多さを踏まえても、json形式は好ましいフォーマットではないでしょうか。

### 後書き

調査した内容の結論が**「Serializableインターフェースを使用しない方が良い」**は、堪えますね。

C言語では構造体のパディングを意識しながらパケットヘッダを作成した記憶がありますが、Javaではもう少し直感的にByte配列を作れそうに感じました。
