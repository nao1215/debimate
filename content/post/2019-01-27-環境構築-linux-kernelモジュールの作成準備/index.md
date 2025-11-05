---
title: "環境構築: Linux Kernelモジュールの作成準備"
type: post
date: 2019-01-27
categories:
  - "linux"
tags:
  - "c言語"
  - "debian"
  - "linux"
  - "linuxkernel"
  - "環境構築"
cover:
  image: "images/tux.png"
  alt: "環境構築: Linux Kernelモジュールの作成準備"
  hidden: false
---

## 前書き

本記事は、「Linux Kernel Device Driverの雛形作成」や「Linux Kernel内APIを試すためのモジュール作成」を目的として、最低限必要な環境構築手順を記載しています。

## 開発環境

```
$ neofetch
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 9.7 (stretch) x86_64 
 ,$$P'              `$$$.     Kernel: 4.9.0-8-amd64 
',$$P       ,ggs.     `$$b:   Uptime: 5 hours, 35 minutes 
`d$$'     ,$P"'   .    $$$    Packages: 2357 
 $$P      d$'     ,    $$P    Shell: bash 4.4.12 
 $$:      $$.   - ,d$$'    Resolution: 2560x1080 
 $$;      Y$b._   _,d$P'      DE: Cinnamon 3.2.7 
 Y$$.    `.`"Y$$$$P"'         WM: Mutter (Muffin) 
 `$$b      "-.__              WM Theme: Cinnamon (Albatross) 
  `Y$$                        Theme: BlackMATE [GTK2/3] 
   `Y$$.                      Icons: Gnome [GTK2/3] 
     `$$b.                    Terminal: gnome-terminal 
       `Y$$b.                 CPU: Intel i3-6100U (4) @ 2.3GHz 
          `"Y$b._             GPU: Intel Integrated Graphics 
              `"""            Memory: 3487MB / 32069MB 
```

## Linux Kenelモジュールとは

Linux Kernelモジュールとは、Linux Kenelの機能を拡張するためのオブジェクトファイル(\*.koファイル)です。特徴として、Linuxの起動後に、動的にLoad/Unloadできます。イメージとしては、アプリケーションのPluginと同等です。

Linux Kernelは、機能拡張方法が2つあります。

拡張方法

- Kernelのビルド時に機能を組み込む方法
- Kernel起動後に\*.koファイルを動的に読み込む方法

前者では、Linux Kernelのビルド前に.configファイル(ビルド設定ファイル)を編集し、必要な機能を予め取捨選択します。利点は実行時のオーバヘッドが少ない事で、欠点は組み込んだ機能を未使用でもその機能分のメモリを消費してしまう事です。この方法は、Kernelに必須な機能(メモリマネージメント等)に用いられる事が多いです。

後者も、.configファイルを編集する点では、同様です。ただし、機能の必要・不要の設定ではなく、モジュール化フラグを設定します。利点は、機能が必要になったタイミングで\*.koファイルをloadできる事で、欠点はload時にオーバヘッドがある事です。この方法は、デバイスドライバで用いられる事が多いです。

## Linux Kernel開発に必須パッケージのinstall

Linux Kernelの開発(主にビルド)で必須なパッケージをinstallします。導入順番は、Linux Kernelヘッダ、ビルド時の依存パッケージです。今回は、ディストリビューション(Debian)が提供しているパッケージを用います。

```
$ sudo apt update
$ sudo apt upgrade
$ sudo apt install linux-headers-$(uname -r)     (注釈) unameコマンドにより、このコマンドを入力しているPCのKernelバージョン用ヘッダを取得
$ sudo apt install gawk wget git diffstat unzip texinfo gcc-multilib \
build-essential chrpath socat libsdl1.2-dev xterm libncurses5-dev \
lzop flex libelf-dev kmod
```

## Linux Kernelソースコードの取得

前述の手順で入手したLinux Kernelヘッダと同じバージョンのLinux Kernelソースコードを取得します。取得したソースコードは、/usr/src以下にtarballで格納されます。具体的には、linux-source-<Version>.tar.xzが一時開発元オリジナルソースコード、その他のファイルがDebian独自のパッチです。[詳細は、Debian公式サイトに記載されています。](https://packages.debian.org/stretch/all/linux-source-4.9/filelist)

```
$ uname -r       (注釈) Kernelバージョンの確認
4.9.0-8-amd64
$ sudo apt install linux-source-4.9  (注釈) linux-source-X.Xの"X.X"は、unameコマンドで確認したバージョンを記載。
```

## Linux Kernelのビルド確認

Debian標準のLinux Kernelコンフィグ(.configファイル)を用いて、ビルド確認を行います。

手順

1. Linux Kernelソースコードのtarballを展開
2. 既存のLinux Kernelコンフィグファイル(.configファイル)をコピー
3. Kernelに追加された新機能の有効・無効・モジュール化を設定
4. ビルド

まず、Linux Kernelのソースコードが"/usr/src/linux-source-4.9.tar.xz"に存在するため、展開をします。展開先のディレクトリは任意です。今回はホームディレクトリ以下にKERNELディレクトリを作成し、その下にLinux Kernelソースコードを展開します。

```
$ mkdir ~/KERNEL
$ cd ~/KERNEL
$ tar xf /usr/src/linux-source-4.9.tar.xz
$ ls
linux-source-4.9

```

既存のLinux Kernelコンフィグファイル(.configファイル)をコピーします。既存ファイルは、"/boot"以下に存在します。環境を複数回UPGRADE("apt upgrade")している場合、複数のコンフィグファイルが存在する事があります。その場合は、最新バージョンをコピーしてください。

```
$ cd linux-source-4.9/
$ ls /boot/
System.map-4.9.0-7-amd64  config-4.9.0-7-amd64  efi   initrd.img-4.9.0-7-amd64  vmlinuz-4.9.0-7-amd64
System.map-4.9.0-8-amd64  config-4.9.0-8-amd64  grub  initrd.img-4.9.0-8-amd64  vmlinuz-4.9.0-8-amd64

$ cp /boot/config-4.9.0-8-amd64 .config      (最新バージョンは、4.9.0-8)

```

Linux Kernelのビルド対象機能およびモジュール化対象機能を設定します。新機能以外は既存設定(Debian設定)と同じ、新機能はデフォルト(無効)とします。この設定には、"make oldconfig"コマンドで設定します(有効=Y/y、無効=N/n、モジュール化=m)。"make oldconfig"コマンド中の選択肢は、全てEnter(デフォルト)を押してください。

```
$ cp /boot/config-4.9.0-8-amd64 .config
$ make oldconfig
  LEX     scripts/kconfig/zconf.lex.c
  HOSTCC  scripts/kconfig/zconf.tab.o
  HOSTLD  scripts/kconfig/conf
scripts/kconfig/conf  --oldconfig Kconfig
.config:804:warning: symbol value 'm' invalid for HOTPLUG_PCI_SHPC
.config:986:warning: symbol value 'm' invalid for NF_CT_PROTO_DCCP
.config:988:warning: symbol value 'm' invalid for NF_CT_PROTO_SCTP
.config:989:warning: symbol value 'm' invalid for NF_CT_PROTO_UDPLITE
.config:1007:warning: symbol value 'm' invalid for NF_NAT_PROTO_DCCP
.config:1008:warning: symbol value 'm' invalid for NF_NAT_PROTO_UDPLITE
.config:1009:warning: symbol value 'm' invalid for NF_NAT_PROTO_SCTP
.config:1015:warning: symbol value 'm' invalid for NF_NAT_REDIRECT
.config:1018:warning: symbol value 'm' invalid for NF_TABLES_INET
.config:1019:warning: symbol value 'm' invalid for NF_TABLES_NETDEV
.config:1194:warning: symbol value 'm' invalid for NF_TABLES_IPV4
.config:1198:warning: symbol value 'm' invalid for NF_TABLES_ARP
.config:1205:warning: symbol value 'm' invalid for NF_NAT_MASQUERADE_IPV4
.config:1239:warning: symbol value 'm' invalid for NF_TABLES_IPV6
.config:1248:warning: symbol value 'm' invalid for NF_NAT_MASQUERADE_IPV6
.config:1276:warning: symbol value 'm' invalid for NF_TABLES_BRIDGE
.config:3515:warning: symbol value 'm' invalid for HW_RANDOM_TPM
.config:4254:warning: symbol value 'm' invalid for LIRC
.config:4927:warning: symbol value 'm' invalid for HSA_AMD
.config:6901:warning: symbol value 'm' invalid for NVMEM
*
* Restart config...
*
*
* General setup
*
Compile also drivers which will not load (COMPILE_TEST) [N/y/?] n
Local version - append to kernel release (LOCALVERSION) [] 
Automatically append version information to the version string (LOCALVERSION_AUTO) [N/y/?] n
Build ID Salt (BUILD_SALT) [] (NEW) 
Kernel compression mode
  1. Gzip (KERNEL_GZIP)
  2. Bzip2 (KERNEL_BZIP2)
  3. LZMA (KERNEL_LZMA)
> 4. XZ (KERNEL_XZ)
  5. LZO (KERNEL_LZO)
  6. LZ4 (KERNEL_LZ4)
choice[1-6?]: 4
Default hostname (DEFAULT_HOSTNAME) [(none)] (none)
Support for paging of anonymous memory (swap) (SWAP) [Y/n/?] y
System V IPC (SYSVIPC) [Y/n/?] y
POSIX Message Queues (POSIX_MQUEUE) [Y/n/?] y
Enable process_vm_readv/writev syscalls (CROSS_MEMORY_ATTACH) [Y/n/?] y
uselib syscall (USELIB) [Y/n/?] y

(以下、長いため省略。基本的にEnterを押せば良い)

```

最後に、ビルドをします。ここでエラーが発生する場合は、パッケージなどが不足している可能性があります。

```
$ make -j8   (注釈) -jの後の数値は、CPUコア数×2

```

\[the\_ad id="598"\]

## Linux Kernelモジュール(雛形)を作成・ビルド

Linux Kernelモジュールの雛形を作成します。作成するファイルは、ソースファイル(今回はtest\_module.c)とMakefileです。ソース内容は、後ほど説明します。なお、Linux Kernelのコーディング規約の一つに、「Tabを使う事(size=8)」があります。基本的に私は、commitするわけではないため、この規約に従っていない場合があります。

```
$ cd ~/KERNEL
$ mkdir kernel_moduel
$ ls
kernel_moduel  linux-source-4.9

$ cd kernel_moduel
$ touch {Makefile,debimate_module.c}

```

```
#include <linux/module.h>   
       
MODULE_LICENSE("Dual BSD/GPL");
MODULE_AUTHOR("NAO <n.chika156@gmail.com>");
MODULE_INFO(free_form_info, "You can write the string here freely.");
MODULE_DESCRIPTION("This moduel is for testing");

static int __init debimate_init(void)    
{
	printk(KERN_INFO "Hello, World!\n");
	return 0;
}

static void __exit debimate_exit(void)    
{
	printk(KERN_INFO "Goodbye.\n");
}

module_init(debimate_init);
module_exit(debimate_exit); 
```

```
obj-m := debimate_module.o
all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
```

ビルドするには、makeコマンドを叩くだけで、ビルド後の生成物の"test\_module.ko"がKernelオブジェクトです。

```
$ ls  (注釈) 以下のファイルがある階層に移動してください
Makefile  debimate_module.c

$ makemake -C /lib/modules/4.9.0-8-amd64/build M=/home/nao/KERNEL/kernel_moduel modulesmake[1]: ディレクトリ '/usr/src/linux-headers-4.9.0-8-amd64' に入ります  CC [M]  /home/nao/KERNEL/kernel_moduel/debimate_module.o  Building modules, stage 2. MODPOST 1 modules  CC      /home/nao/KERNEL/kernel_moduel/debimate_module.mod.o  LD [M]  /home/nao/KERNEL/kernel_moduel/debimate_module.komake[1]: ディレクトリ '/usr/src/linux-headers-4.9.0-8-amd64' から出ます
$ ls
Makefile        debimate_module.c   debimate_module.mod.c  debimate_module.oModule.symvers  debimate_module.ko  debimate_module.mod.o  modules.order

```

## debimate\_module.cの内容説明

まず、以下のMODULE\_\*の部分を説明します。

```
#include <linux/module.h>   
       
MODULE_LICENSE("Dual BSD/GPL");
MODULE_AUTHOR("NAO <n.chika156@gmail.com>");
MODULE_INFO(free_form_info, "You can write the string here freely.");
MODULE_DESCRIPTION("This moduel is for testing");

```

MODULE\_LICENSEは、Kernelモジュールのライセンスを記載します。Kernelモジュールで使用できるライセンスは以下の通りで、Linux Kenerlソースコードの<KernelソースのTop Directory>/include/linux/module.hに記載があります 。

| **ライセンスに使用できる文字列** | **説明** |
| --- | --- |
| GPL | [GNU Public License Version2](https://ja.wikipedia.org/wiki/GNU_General_Public_License)(以下、GPLv2)か、それ以降のライセンス([GPLv3](https://www.wdic.org/w/TECH/GPLv3)) |
| GPL v2 | GPLv2 |
| GPL and additional rights | GPLv2およびその他の権利 |
| Dual BSD/GPL | [BSDライセンス](https://ja.wikipedia.org/wiki/BSD%E3%83%A9%E3%82%A4%E3%82%BB%E3%83%B3%E3%82%B9)か、GPLv2 |
| Dual MIT/GPL | [MITライセンス](https://postd.cc/mit-license-line-by-line/)か、GPLv2 |
| Dual MPL/GPL | [Mozillaライセンス](https://ja.wikipedia.org/wiki/Mozilla_Public_License)か、GPLv2 |
| Proprietary | Freeではない(制約のある)製品向けのライセンス |

ライセンスの必要性に関しては、以下のようにmodule.hに記載があります。2.と3.は、Linux Kernel Developerとベンダー企業の意見に対する折衷案のようですね。

> 1\. So modinfo can show license info for users wanting to vet their setup is free  
> 2\. So the community can ignore bug reports including proprietary modules  
> 3\. So vendors can do likewise based on their own policies
> 
> \[和訳\]  
> 1\. modinfoコマンドは、ユーザの環境がFree(自由、無料)である事を確認したいユーザーのために、ライセンス情報を表示できます  
> 2\. コミュニティは、(修正範囲に)プロプラエタリモジュールを含むバグ報告を無視できます  
> 3\. ベンダーも同様に、自分の方針に基づいて活動できます

ちなみに、ライセンスを指定していないモジュールは、ビルドが通りません。以下に、ライセンス情報をコメントアウトした場合の、ビルド結果を示します。Warningとして、"missing MODULE\_LICENSE()〜"が出ます。

```
$ make
make -C /lib/modules/4.9.0-8-amd64/build M=/home/nao/KERNEL/kernel_moduel modules
make[1]: ディレクトリ '/usr/src/linux-headers-4.9.0-8-amd64' に入ります
  CC [M]  /home/nao/KERNEL/kernel_moduel/debimate_module.o
  Building modules, stage 2.
  MODPOST 1 modules
WARNING: modpost: missing MODULE_LICENSE() in /home/nao/KERNEL/kernel_moduel/debimate_module.o
see include/linux/module.h for more information
  LD [M]  /home/nao/KERNEL/kernel_moduel/debimate_module.ko
make[1]: ディレクトリ '/usr/src/linux-headers-4.9.0-8-amd64' から出ます

```

MODULE\_AUTHOR、MODULE\_DESCRIPTIONは、見たままの内容です。前者には"モジュール作成者<メールアドレス>"を記載し、後者にはモジュールの機能説明を記載します。MODULE\_INFOは、少し特殊です。第一引数に任意のラベルをつけ、第二引数にラベルに応じた内容(文字列)を記載します。

今回のソースコードでは、以下のようにモジュール情報が表示されます。

```
$ sudo modinfo debimate_module.ko
filename:       /home/nao/KERNEL/kernel_moduel/debimate_module.ko
description:    This moduel is for testing
free_form_info: You can write the string here freely.
author:         CHIKAMATSU Naohiro <n.chika156@gmail.com>
license:        Dual BSD/GPL
depends:        
retpoline:      Y
vermagic:       4.9.0-8-amd64 SMP mod_unload modversions 

```

続いて、残りのコード(以下)を説明します。

```
static int __init debimate_init(void)    
{
	printk(KERN_INFO "Hello, World!\n");
	return 0;
}

static void __exit debimate_exit(void)
{
	printk(KERN_INFO "Goodbye.\n");
}

module_init(debimate_init);
module_exit(debimate_exit); 
```

debimate\_init()、debimate\_exit()は、KernelモジュールをLoad/Unload時に行う初期化・終了処理です。printk()はLinux Kernel内部用の出力関数です。printk()には出力レベルが存在します。出力レベル関しては、以下の記事を参照ください。

https://debimate.jp/2019/02/02/linux-kernel-prinkprint-kernel%E3%81%AB%E3%82%88%E3%82%8B%E3%83%A1%E3%83%83%E3%82%BB%E3%83%BC%E3%82%B8%E5%87%BA%E5%8A%9B/

また、初期化関数に付与された\_\_initマクロ、終了化関数に付与された\_\_exitマクロは、メモリを効率使用するためのものです。初期化関数・終了関数が実行後、これらの関数はメモリから解放されます。細かい仕様は、以下の記事を参照ください。

https://debimate.jp/2019/04/29/linux-kernel-\_\_init%E3%83%9E%E3%82%AF%E3%83%AD%E3%80%81\_\_exit%E3%83%9E%E3%82%AF%E3%83%AD%E3%81%AE%E5%BD%B9%E5%89%B2%E3%83%A1%E3%83%A2%E3%83%AA%E3%81%AE%E6%9C%89%E5%8A%B9%E5%88%A9%E7%94%A8/

module\_init()、module\_exit()は、モジュールの初期化関数および終了関数を定義します。初期化関数を呼び出す仕組みは[initcall](https://0xax.gitbooks.io/linux-insides/content/Concepts/linux-cpu-3.html)と呼ばれ、機能毎にモジュールを初期化するタイミングをずらせます。今回のKernelモジュール(module\_init)は、device向けのタイミングで初期化されます。タイミングは以下の8種類です。

1. early
2. core
3. postcore
4. arch
5. subsys
6. fs
7. device
8. late

## KernelモジュールのLoad/Unloadを確認

Load時はinsmodコマンド、Unload時はrmmodコマンドを使用します。正しくLoad/Unloadができたかを確認するため、dmsegコマンドでKernelモジュールの初期化・終了時の文字列出力を見ます。以下に、Load、Unloadの順番で実行結果を示します。

```
$ sudo insmod debimate_module.ko
$ sudo dmesg | tail -n 5
[11115.261412] IPv6: ADDRCONF(NETDEV_UP): wlx4ce6768f1c45: link is not ready
[11431.283872] IPv6: ADDRCONF(NETDEV_UP): wlx4ce6768f1c45: link is not ready
[11747.279816] IPv6: ADDRCONF(NETDEV_UP): wlx4ce6768f1c45: link is not ready
[12063.225199] IPv6: ADDRCONF(NETDEV_UP): wlx4ce6768f1c45: link is not ready
[12153.489004] Hello, World!

```

```
$ sudo rmmod debimate_module  (注釈) Unload時は、モジュール指定に".ko"は不要。
$ sudo dmesg | tail -n 5
[11431.283872] IPv6: ADDRCONF(NETDEV_UP): wlx4ce6768f1c45: link is not ready
[11747.279816] IPv6: ADDRCONF(NETDEV_UP): wlx4ce6768f1c45: link is not ready
[12063.225199] IPv6: ADDRCONF(NETDEV_UP): wlx4ce6768f1c45: link is not ready
[12153.489004] Hello, World!
[12282.487297] Goodbye.

```

以上が、Kernelモジュール開発の作成準備になります。上記のコードを発展させ、Device Driverを作成したい場合は、以下の記事を確認して下さい。

https://debimate.jp/2019/06/23/linux-kernel%E3%81%AE%E7%B0%A1%E5%8D%98%E3%81%AAcharacter-device%E3%82%92%E4%BD%9C%E6%88%90%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95linked-list-api%E3%81%AE%E4%BD%BF%E7%94%A8%E6%96%B9%E6%B3%95%E3%82%B5/
