---
title: "【Java 11】Shebangを用いたJavaソースファイル（単一）の実行方法 + Shebangエラー回避方法"
type: post
date: 2020-07-23
categories:
  - "linux"
tags:
  - "java"
  - "linux"
  - "shebang"
cover:
  image: "images/eyecatch-openjdk.png"
  alt: "【Java 11】Shebangを用いたJavaソースファイル（単一）の実行方法 + Shebangエラー回避方法"
  hidden: false
---

## 前書き：コンパイル無しでJavaアプリが動かせる 

最近のJavaは、リリースペースが半年に一回と早まり、新機能が次々と追加されています。新機能の中で、Java 11からコンパイル無しでJavaソースファイル（単一ファイル）が実行できる機能があり、本記事ではその使い方（およびShebangエラー回避方法）を説明します。

## 本記事で使用したJavaのバージョン

OSはDebian（Linux）とし、Java 11環境で検証しました。

```
nao@debian ~> java --version 
openjdk 11.0.7 2020-04-14
OpenJDK Runtime Environment (build 11.0.7+10-post-Debian-3deb10u1)
OpenJDK 64-Bit Server VM (build 11.0.7+10-post-Debian-3deb10u1, mixed mode, sharing)
```

## 使用方法・実行例：JavaコードにShebangを付けるだけ

Javaソースコードをコンパイル無しで実行するには、以下のコード（helloソースファイル）のように、"#!/usr/bin/java"をShebangとして一行目に追加します。

```
#!/usr/bin/java --source 11

public class App {
    public static void main(String[] args) {
        System.out.println("Hello Terminal");
    }
}

```

環境によっては、"#!/usr/bin/java"にjavaが存在しない事があります。自身の環境で、javaがどのPATHに存在するかを調べるには、whichコマンドを用いてください。

私の環境とwhichコマンドの結果（以下）が異なる場合、Shebangを"#!<whichコマンドの結果>"と、書き換える必要があります。例えば、javaのPATHが"/bin/java"の場合、Shebangは"#!/bin/java"となります。

```
nao@debian ~> which java
/usr/bin/java　　　　※ 実行環境によって、表示されるPATHが変わります。

```

Shebangの--source部分は、Javaバージョンを指定します。バージョンは"java --version"コマンドで確認できます。

実行例は、以下の通りです。

```
nao@debian ~> bat hello -l java 
───────┬───────────────────────────────────────────────────────────
       │ File: hello
───────┼───────────────────────────────────────────────────────────
   1   │ #!/usr/bin/java --source 11
   2   │ 
   3   │ public class App {
   4   │     public static void main(String[] args) {
   5   │         System.out.println("Hello Terminal");
   6   │     }
   7   │ }
───────┴───────────────────────────────────────────────────────────
nao@debian ~> chmod a+x hello
nao@debian ~> ./hello
Hello Terminal

```

## 拡張子に".java"が付いているとエラー

上記の説明で使用したhelloソースコードをhello.javaにリネームし、実行すると以下のエラーが出ます。"--source 11"を除去しても、同様の結果になります。

```
nao@debian ~> cp hello hello.java

nao@debian ~> ./hello.java
./hello.java:1: エラー: '#'は不正な文字です
#!/usr/bin/java --source 11
^
./hello.java:1: エラー: class、interfaceまたはenumがありません
#!/usr/bin/java --source 11
  ^
エラー2個
エラー: コンパイルが失敗しました

```

本エラーに関してですが、拡張子に".java"が付与されている場合、Shebangが機能せず、正しく動かない事が示されています（[外部サイトでの説明](https://stackoverflow.com/questions/52530470/java-11-executing-source-file-via-shebang-is-not-working)）。
