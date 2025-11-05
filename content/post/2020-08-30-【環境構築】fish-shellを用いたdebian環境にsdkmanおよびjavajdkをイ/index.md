---
title: "【環境構築】fish shellを用いたDebian環境にSDKMANおよびJava(JDK)をインストールする方法"
type: post
date: 2020-08-30
categories:
  - "linux"
tags:
  - "debian"
  - "java"
  - "linux"
  - "sdkman"
  - "環境構築"
cover:
  image: images/Screenshot-from-2020-08-30-11-24-14-min.jpg
  alt: "【環境構築】fish shellを用いたDebian環境にSDKMANおよびJava(JDK)をインストールする方法"
  hidden: false
---

## 前書き：SDKMANはbash（もしくはzsh）前提

[SDKMAN](https://sdkman.io/)は、JDK（Java開発環境）やGroovy、Scala、Gradleなどのバージョン管理ツールです。主に、JVM系のツールを管理します。Rubyのrbenv、Pythonのpyenvと同様の立ち位置のツールであり、CLIから任意のバージョンのソフト（例：Java）をインストール／使用／削除できます。

SDKMANの公式サイトに書かれている通り、SDKMANはbashで実装されています。そのため、Login Shellがbashの場合は問題なく動作しますが、fish環境では実行時にエラーが出てしまいます。

本記事では、fish環境にSDKMANをイントールし、SDKMAN経由でJava（JDK）をインストールする方法を紹介します。

## 検証環境

```
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 10 (buster) x86_64 
 ,$$P'              `$$$.     Kernel: 4.19.67 
',$$P       ,ggs.     `$$b:   Uptime: 25 mins 
`d$$'     ,$P"'   .    $$$    Packages: 4325 (dpkg), 13 (flatpak) 
 $$P      d$'     ,    $$P    Shell: fish 3.0.2 
 $$:      $$.   - ,d$$'    Resolution: 2560x1080 
 $$;      Y$b._   _,d$P'      DE: Pantheon 
 Y$$.    `.`"Y$$$$P"'         WM: Mutter(Gala) 
 `$$b      "-.__              Terminal: io.elementary.t 
  `Y$$                        CPU: AMD Ryzen 7 3800X 8- (16) @ 3.900GHz 
   `Y$$.                      GPU: NVIDIA NVIDIA Corporation TU107 
     `$$b.                    Memory: 3457MiB / 64404MiB 
       `Y$$b.
          `"Y$b._                                     
```

## SDKMANのインストール

まず、SDKMANの依存パッケージをインストールします。SDKMAN公式サイトに依存パッケージ情報（curl, zip/unzip）が記載されていますが、実際は以下のパッケージ5個をインストールしなければいけません。

```
$ sudo apt install bash zip unzip curl sed

```

次に、SDKMANをインストールします。curlコマンドで、SDKMANをインストールするためのShell Scriptをダウンロードし、その内容をbashで実行します。

```
$ curl -s "https://get.sdkman.io" | bash

```

上記のコマンドが成功すれば、SDKMANは"$HOME/.sdkman"にインストールされます。

## fishとfisherをインストール

この段階でLogin Shellをfish（shell）に変更していない場合、以下の記事を参考に変更してください。また、SDKMANをfishで使うには、fisher（fishプラグインマネージャ）も必要ですので、合わせてインストールしてください。

https://debimate.jp/2019/06/15/%E7%92%B0%E5%A2%83%E6%A7%8B%E7%AF%89%EF%BC%9A%E3%83%A6%E3%83%BC%E3%82%B6%E3%83%95%E3%83%AC%E3%83%B3%E3%83%89%E3%83%AA%E3%83%BC%E3%81%A7%E8%A3%9C%E5%AE%8C%E6%A9%9F%E8%83%BD%E3%81%AE%E5%BC%B7%E5%8A%9B/

## SDKMAN! for fishプラグインのインストール

SDKMANは、bash起動時に設定ファイル（sdkman-init.sh）を読み込みます。この仕組みがfishでは上手く動かないので、別途プラグイン（[SDKMAN! for fish](https://github.com/reitzig/sdkman-for-fish)）をインストールする事によって、この問題を解決します。

プラグインのインストール手順は、以下の通りです。

```
$ fisher add reitzig/sdkman-for-fish@v1.4.0

```

\[the\_ad id="598"\]

## Javaのインストール

ここまでの手順でSDKMANが動作します。ここからは、Javaをインストールする手順を説明します。

まずは、インストールできるJavaのVersionを確認します。前提情報ですが、Javaは複数のベンダが公開しているJDKディストリビューションがあります。いずれのJDKも、マルチプラットフォーム（Win／Mac／Linux）対応であり、OpenJDKをベースにしています。特にこだわりがなければ、リファレンス実装であるJava.netが公開しているJDKを選択しましょう。

以下、OpenJDK（Version13.02）のインストール手順です。

```
$ sdk selfupdate       (注釈)：SDKMAN自体を更新

$ sdk list java
================================================================================
Available Java Versions
================================================================================
 Vendor        | Use | Version      | Dist    | Status     | Identifier
--------------------------------------------------------------------------------
 AdoptOpenJDK  |     | 14.0.2.j9    | adpt    |            | 14.0.2.j9-adpt      
               |     | 14.0.2.hs    | adpt    |            | 14.0.2.hs-adpt      
               |     | 13.0.2.j9    | adpt    |            | 13.0.2.j9-adpt      
               |     | 13.0.2.hs    | adpt    |            | 13.0.2.hs-adpt      
               |     | 12.0.2.j9    | adpt    |            | 12.0.2.j9-adpt      
               |     | 12.0.2.hs    | adpt    |            | 12.0.2.hs-adpt      
               |     | 11.0.8.j9    | adpt    |            | 11.0.8.j9-adpt      
               |     | 11.0.8.hs    | adpt    |            | 11.0.8.hs-adpt      
               |     | 8.0.265.j9   | adpt    |            | 8.0.265.j9-adpt     
               |     | 8.0.265.hs   | adpt    |            | 8.0.265.hs-adpt     
 Amazon        |     | 11.0.8       | amzn    |            | 11.0.8-amzn         
               |     | 8.0.265      | amzn    |            | 8.0.265-amzn        
 Azul Zulu     |     | 14.0.2       | zulu    |            | 14.0.2-zulu         
               |     | 13.0.4       | zulu    |            | 13.0.4-zulu         
               |     | 13.0.4.fx    | zulu    |            | 13.0.4.fx-zulu      
               |     | 12.0.2       | zulu    |            | 12.0.2-zulu         
               |     | 11.0.8       | zulu    |            | 11.0.8-zulu         
               |     | 11.0.8.fx    | zulu    |            | 11.0.8.fx-zulu      
               |     | 10.0.2       | zulu    |            | 10.0.2-zulu         
               |     | 9.0.7        | zulu    |            | 9.0.7-zulu          
               |     | 8.0.265      | zulu    |            | 8.0.265-zulu        
               |     | 8.0.265.fx   | zulu    |            | 8.0.265.fx-zulu     
               |     | 8.0.232.fx   | zulu    |            | 8.0.232.fx-zulu     
               |     | 7.0.262      | zulu    |            | 7.0.262-zulu        
               |     | 6.0.119      | zulu    |            | 6.0.119-zulu        
 BellSoft      |     | 14.0.2.fx    | librca  |            | 14.0.2.fx-librca    
               |     | 14.0.2       | librca  |            | 14.0.2-librca       
               |     | 13.0.2.fx    | librca  |            | 13.0.2.fx-librca    
               |     | 13.0.2       | librca  |            | 13.0.2-librca       
               |     | 12.0.2       | librca  |            | 12.0.2-librca       
               |     | 11.0.8.fx    | librca  |            | 11.0.8.fx-librca    
               |     | 11.0.8       | librca  |            | 11.0.8-librca       
               |     | 8.0.265.fx   | librca  |            | 8.0.265.fx-librca   
               |     | 8.0.265      | librca  |            | 8.0.265-librca      
 GraalVM       |     | 20.2.0.r11   | grl     |            | 20.2.0.r11-grl      
               |     | 20.2.0.r8    | grl     |            | 20.2.0.r8-grl       
               |     | 20.1.0.r11   | grl     |            | 20.1.0.r11-grl      
               |     | 20.1.0.r8    | grl     |            | 20.1.0.r8-grl       
               |     | 20.0.0.r11   | grl     |            | 20.0.0.r11-grl      
               |     | 20.0.0.r8    | grl     |            | 20.0.0.r8-grl       
               |     | 19.3.1.r11   | grl     |            | 19.3.1.r11-grl      
               |     | 19.3.1.r8    | grl     |            | 19.3.1.r8-grl       
 Java.net      |     | 16.ea.13     | open    |            | 16.ea.13-open       
               |     | 15.ea.36     | open    |            | 15.ea.36-open       
               |     | 14.0.2       | open    | installed  | 14.0.2-open         
               |     | 13.0.2       | open    |            | 13.0.2-open         
               |     | 12.0.2       | open    |            | 12.0.2-open         
               |     | 11.0.8       | open    |            | 11.0.8-open         
               | >>> | 10.0.2       | open    | installed  | 10.0.2-open         
               |     | 9.0.4        | open    |            | 9.0.4-open          
               |     | 8.0.265      | open    | installed  | 8.0.265-open        
 SAP           |     | 14.0.2       | sapmchn |            | 14.0.2-sapmchn      
               |     | 13.0.2       | sapmchn |            | 13.0.2-sapmchn      
               |     | 12.0.2       | sapmchn |            | 12.0.2-sapmchn      
               |     | 11.0.8       | sapmchn |            | 11.0.8-sapmchn      
================================================================================
Use the Identifier for installation:

    $ sdk install java 11.0.3.hs-adpt
================================================================================

$ sdk install java 13.0.2-open      (注釈)：OpenJDKのインストール

Downloading: java 13.0.2-open

In progress...

################################################################## 100.0%

Repackaging Java 13.0.2-open...

Done repackaging...

Installing: java 13.0.2-open
Done installing!

Do you want java 13.0.2-open to be set as default? (Y/n): Y  (注釈)：インストールしたJDKをデフォルトJDKに変更

Setting java 13.0.2-open as default.

```

## 環境変数JAVA\_HOMEの設定

最後に、JDKのインストール先を環境変数JAVA\_HOMEに設定します。

SDKMANがインストールするJDKは、"$HOME/.sdkman/candidates/java/"以下にインストールされます。同ディレクトリ内にcurrentというシンボリックリンクがあり、このリンクはデフォルトJDKのディレクトリを指しています。

```
$ ls -al /home/nao/.sdkman/candidates/java/ 
合計 24
drwxr-xr-x 6 nao nao 4096  8月 30 12:35 ./
drwxr-xr-x 4 nao nao 4096  8月 13 19:46 ../
drwxr-xr-x 9 nao nao 4096  8月 30 00:15 10.0.2-open/
drwxr-xr-x 8 nao nao 4096  8月 30 12:35 13.0.2-open/
drwxr-xr-x 8 nao nao 4096  8月 13 19:46 14.0.2-open/
drwxr-xr-x 9 nao nao 4096  7月 27 20:49 8.0.265-open/
lrwxrwxrwx 1 nao nao   11  8月 30 12:35 current -> 13.0.2-open/

```

そのため、環境変数JAVA\_HOMEには"$HOME/.sdkman/candidates/java/current"を設定します。使用するJDKを変更したとしても、SDKMANがcurrentシンボリックリンクが指すディレクトリを変更してくれるため、環境変数JAVA\_HOMEの設定を修正する必要がありません。

以下、fishの設定ファイル（$HOME/.config/fish/config.fish）に環境変数JAVA\_HOMEを設定する例です。

```
$ nvim ~/.config/fish/config.fish      (注釈) 使用するエディタは任意 

```

```
# 以下の二行を追記
set -x JAVA_HOME $HOME/.sdkman/candidates/java/current/
set -x PATH $PATH $JAVA_HOME/bin

```
