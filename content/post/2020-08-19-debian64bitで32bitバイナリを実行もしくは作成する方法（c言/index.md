---
title: "Debian(64bit)で32bitバイナリを実行もしくは作成する方法（C言語）"
type: post
date: 2020-08-19
categories:
  - "linux"
tags:
  - "c言語"
  - "debian"
  - "linux"
cover:
  image: images/processor-2217771_640-min.jpg
  alt: "Debian(64bit)で32bitバイナリを実行もしくは作成する方法（C言語）"
  hidden: false
images: ["images/processor-2217771_640-min.jpg"]
---

## 検証環境

Debian10(64Bit)、Ryzen 7 3800X環境で検証します。CPUアーキテクチャはIntel／AMDを想定しており、ARMに関しては本記事で説明しません。

```
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 10 (buster) x86_64 
 ,$$P'              `$$$.     Kernel: 4.19.67 
',$$P       ,ggs.     `$$b:   Uptime: 6 days, 9 hours, 18 mins 
`d$$'     ,$P"'   .    $$$    Packages: 3967 (dpkg), 10 (flatpak) 
 $$P      d$'     ,    $$P    Shell: fish 3.0.2 
 $$:      $$.   - ,d$$'    Resolution: 2560x1080 
 $$;      Y$b._   _,d$P'      DE: Cinnamon 3.8.8 
 Y$$.    `.`"Y$$$$P"'         WM: Mutter (Muffin) 
 `$$b      "-.__              WM Theme: (Albatross) 
  `Y$$                        Theme: Blackbird [GTK2/3] 
   `Y$$.                      Icons: hicolor [GTK2/3] 
     `$$b.                    Terminal: gnome-terminal 
       `Y$$b.                 CPU: AMD Ryzen 7 3800X 8- (16) @ 3.900GHz 
          `"Y$b._             GPU: NVIDIA NVIDIA Corporation TU107 
              `"""            Memory: 7095MiB / 64404MiB 
```

## Host環境／実行バイナリのBit数を確認する方法

まず、前提条件となる「Host環境のBit数」および「実行バイナリのBit数」を確認する方法です。

ビルドを行うHost環境のBit数は、unameコマンドで確認できます。i386（i686）と表示された場合は32Bit、x86\_64と表示された場合は64Bitです。以下、実行例（64Bit）です。

```
$ uname -a　(注釈)：-aオプションは、全てのシステム情報を表示します。
Linux debian 4.19.67 #1 SMP Sat Sep 28 23:50:53 JST 2019 x86_64 GNU/Linux

```

実行バイナリのBit数はfileコマンドで確認できます。以下、実行例（32Bit）です。

```
$ file sample_binary 
sample_binary: ELF 32-bit LSB pie executable, Intel 80386, version 1 (SYSV), dynamically linked, interpreter /lib/ld-linux.so.2, for GNU/Linux 3.2.0, BuildID[sha1]=04ac1983fddf51757d34321b3d8d45111a9c813f, not stripped

```

## 32Bitバイナリの実行方法

64Bit環境で32Bitバイナリを実行すると、"No such file or direcotry."と表示され、バイナリが存在するにも関わらず実行できない（認識すらしていない）事があります。

この現象の原因は、32Bitライブラリが不足している事です。DebianおよびDebian派生のUbuntuなどは、[Multiarch](https://wiki.debian.org/Multiarch/HOWTO)と呼ばれる仕組みで、複数のCPUアーキテクチャ（例：32Bitと64Bitのアーキテクチャ）向けのソフトウェアをインストールできます。

Multiarchを利用する場合、まずはi386（Host環境とは別アーキテクチャ）のパッケージを取得できる状態にします。

```
$ sudo dpkg --add-architecture i386
$ sudo dpkg --print-foreign-architectures   (注釈)：追加アーキテクチャの確認。
i386

```

次に、32Bitバイナリを実行するために必要なライブラリをインストールします。CPUアーキテクチャを指定したパッケージは、"apt install <パッケージ名:アーキテクチャ名>"の書式で取得できます。

```
$ sudo apt update
$ sudo apt install libstdc++6:i386 libgcc1:i386 zlib1g:i386 libncurses5:i386 multiarch-support gcc-multilib

```

上記のインストール処理が終了すれば、32bitバイナリが実行できます。以下、実行例です。

```
(注釈)：Bit数の確認
$ file 32bit_binary 
32bit_binary: ELF 32-bit LSB pie executable, Intel 80386, version 1 (SYSV), dynamically linked, interpreter /lib/ld-linux.so.2, for GNU/Linux 3.2.0, BuildID[sha1]=375d7a9f91f0a183b6f1dce43b83787cc63e0f73, not stripped

(注釈)：実行
$ ./32bit_binary 
32bit Binary

```

## 32Bitバイナリの作成（コンパイル）方法

64Bit環境で32Bitバイナリを作成するには、gccオプションの"-m32"を使用します。以下、-m32オプションの有無で、生成されるバイナリのBit数が変わる例です。

```
(注釈)：-m32オプションがない場合
$ gcc test.c -o test
$ file test
test: ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux 3.2.0, BuildID[sha1]=446c15466765086c05a6e953f231601e9c3cb56d, not stripped

(注釈)：-m32オプションがある場合
$ gcc -m32 test.c -o test
$ file test
test: ELF 32-bit LSB pie executable, Intel 80386, version 1 (SYSV), dynamically linked, interpreter /lib/ld-linux.so.2, for GNU/Linux 3.2.0, BuildID[sha1]=375d7a9f91f0a183b6f1dce43b83787cc63e0f73, not stripped

```
