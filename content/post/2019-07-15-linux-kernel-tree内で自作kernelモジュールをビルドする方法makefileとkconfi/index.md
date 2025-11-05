---
title: "Linux Kernel Tree内で自作Kernelモジュールをビルドする方法(MakefileとKconfigの書き方)"
type: post
date: 2019-07-15
categories:
  - "linux"
tags:
  - "debian"
  - "linux"
  - "linuxkernel"
  - "環境構築"
cover:
  image: images/Screenshot-from-2019-07-15-12-39-42-min-300x228.jpg
  alt: "Linux Kernel Tree内で自作Kernelモジュールをビルドする方法(MakefileとKconfigの書き方)"
  hidden: false
images: ["post/2019-07-15-linux-kernel-tree内で自作kernelモジュールをビルドする方法makefileとkconfi/images/Screenshot-from-2019-07-15-12-39-42-min-300x228.jpg"]
---

## 前書き

[過去の記事(環境構築: Linux Kernelモジュールの作成準備)](https://debimate.jp/2019/01/27/%e7%92%b0%e5%a2%83%e6%a7%8b%e7%af%89-linux-kernel%e3%83%a2%e3%82%b8%e3%83%a5%e3%83%bc%e3%83%ab%e3%81%ae%e4%bd%9c%e6%88%90%e6%ba%96%e5%82%99/)では、

- Linux Kernelソースコード
- 自作Kernelモジュール

を分離して管理していました。ディレクトリ構成は、以下のような状態です。

```
Current directory
├── linux-source-4.9 # Linux Kernelソースコード
└── org_module       # 自作Kernelモジュール
```

この構成では、自作KernelモジュールおよびLinux Kernelソースコードを同時にビルドできません。そこで、本記事では、自作Kernelモジュールをlinux-source-4.9の中に移動させ、Kernelルートディレクトリ(linux-source-4.9)にあるMakefileから自作Kernelモジュールをビルドする方法を示します。

## 検証環境

検証環境は、Debian10(buster)で実施します。本記事では、既存のKernelモジュールを利用して、手順を説明します。自作Kernelモジュールを0ベースで作成したい方は、以下の過去記事も合わせて確認して下さい。

```
$ neofetch 
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 10 (buster) x86_64 
 ,$$P'              `$$$.     Kernel: 4.19.0-5-amd64 
',$$P       ,ggs.     `$$b:   Uptime: 15 hours, 4 minutes 
`d$$'     ,$P"'   .    $$$    Packages: 2466 (dpkg) 
 $$P      d$'     ,    $$P    Shell: fish 3.0.2 
 $$:      $$.   - ,d$$'    Resolution: 2560x1080 
 $$;      Y$b._   _,d$P'      DE: Cinnamon 3.8.8 
 Y$$.    `.`"Y$$$$P"'         WM: Mutter (Muffin) 
 `$$b      "-.__              WM Theme: cinnamon (Albatross) 
  `Y$$                        Theme: BlackMATE [GTK2/3] 
   `Y$$.                      Icons: gnome [GTK2/3] 
     `$$b.                    Terminal: gnome-terminal 
       `Y$$b.                 CPU: Intel i3-6100U (4) @ 2.300GHz 
          `"Y$b._             GPU: Intel HD Graphics 520 
              `"""            Memory: 2918MiB / 32060MiB 

```

https://debimate.jp/2019/01/27/%E7%92%B0%E5%A2%83%E6%A7%8B%E7%AF%89-linux-kernel%E3%83%A2%E3%82%B8%E3%83%A5%E3%83%BC%E3%83%AB%E3%81%AE%E4%BD%9C%E6%88%90%E6%BA%96%E5%82%99/

## Linux Kernelのビルドに必要なパッケージのinstall

Linux Kernelのビルド時に必要なパッケージをinstallします。以下の手順は、Debian前提です。

```
$ sudo apt update
$ sudo apt upgrade
$ sudo apt install gawk wget git diffstat unzip texinfo gcc-multilib \
build-essential chrpath socat libsdl1.2-dev xterm libncurses5-dev \
lzop flex libelf-dev kmod

```

## Linux KernelソースおよびKernelモジュールの取得

Linux KernelソースコードおよびKernelモジュールを取得します。aptコマンドで取得したLinux Kernelソースコードは、/usr/src以下にtarballで格納されます。具体的には、linux-source-<Version>.tar.xzが一時開発元オリジナルソースコード、その他のファイルがDebian独自のパッチです。[詳細は、Debian公式サイトに記載されています。](https://packages.debian.org/stretch/all/linux-source-4.9/filelist)

Kernelモジュールは、過去記事で作成したCharacter DriverをGitHubから取得(再利用)します。

```
(注釈) Linux Kernelソースコードの取得
$ uname -r       (注釈) Kernelバージョンの確認
4.19.0-5-amd64
$ sudo apt install linux-source-4.19  (注釈) linux-source-X.Xの"X.X"は、unameコマンドで確認したバージョンを記載。
$ tar xf /usr/src/linux-source-4.19.tar.xz

(注釈) Kernelモジュールの取得
$ git clone https://github.com/nao1215/LinuxKernelArticle.git

(注釈) ディレクトリ構成の確認
$ ls 
LinuxKernelArticle/  linux-source-4.19/

```

\[the\_ad id="598"\]

## Kernelモジュール移動およびKconfig修正

自作Kernelモジュールは、以下の構成になっています。自作Kernelモジュール(Charcter Device)は01\_char\_deviceディレクトリ以下であり、testは自作Kernelモジュールのテスト用プログラムです。

```
$ tree LinuxKernelArticle/ 
LinuxKernelArticle/
├── 01_char_device
│   ├── kernel_moduel
│   │   ├── Makefile
│   │   └── debimate_module.c
│   └── test
│       ├── Makefile
│       └── test.c
├── LICENSE
└── README.md

```

今回必要なdebimate\_module.cのみを移動させます。移動先は、linux-source-4.19以下に存在するCharcter Device用ディレクトリ(linux-source-4.19/drivers/char/ )です。

```
$ cp LinuxKernelArticle/01_char_device/kernel_moduel/debimate_module.c linux-source-4.19/drivers/char/.

```

移動した自作Kernelモジュール(Charcter Device)をビルド対象に含めるため、linux-source-4.19/drivers/char/Kconfigに以下を追記します。

```
config DEBIMATE_DRIVER
	tristate "DEBIMATE Test Module."
	depends on X86
	default n
	help
	This is debimate test module.

```

追記時の注意点として、Kconfig内の"endmenu"より前に追記しないと、make menuconfig時に自作Kernelモジュール用の設定が表示されません。追記した項目(例：tristate)のそれぞれの意味合いを下表に示します。

| **項目** | **役割** |
| --- | --- |
| tristate | tristateはビルド時に以下の3種類の選択肢が選べる場合のみ、使用可能です(triが3を意味するため、この名称が使われています)。Kernelは機能をモジュール化できない場合があり、その際はtristateの代わりにboolを使用します。    1. Kernelモジュールが組み込み可能(y) 2. モジュール化が可能(m) 3. ビルドしないか(n)   |
| bool | boolは、tristateではない時(機能をモジュール化できない時)に使用します。 |
| depends on | Kernelモジュールが依存しているアーキテクチャや機能を記載します。AND条件は"&&" 、OR条件は"\|\|"で記載します。今回はX86を記載していますが、実際はX86と依存関係がないです(正しくは、TTYに依存しています)。 |
| default | ビルド時のデフォルト(以下のy/m/nのいずれか)を設定します。    1. Kernelモジュールが組み込み可能(y) 2. モジュール化が可能(m) 3. ビルドしないか(n)   |
| help | make menuconfigで表示するHELPメッセージ |

## Makefileの修正

修正対象のMakefileは、修正したKconfigと同じ階層にあります。今回は、linux-source-4.19/drivers/char/Makefileに対して、以下の1行を追記します。

```
obj-$(CONFIG_DEBIMATE_DRIVER) += debimate_module.o

```

追記した行に関して説明します。

obj-$(CONFIG\_DEBIMATE\_DRIVER)におけるDEBIMETE\_DRIVER部分は、Kconfigの"config"以降に記載した文字列と同じです。例えば、Kconfigに"config XYZ\_TEST"と記載していた場合、obj-$(CONFIG\_XYZ\_TEST)と記載します。

debimate\_module.o部分は、Kernelモジュールソースコード名と同名でなければいけません(拡張子部分は除く)。例えば、Kernelモジュールがtest\_test.cという名称の場合、test\_test.oと記載します。

\[the\_ad id="598"\]

## 自作Kernelモジュール用コンフィグが表示されるかを確認

linux-source-4.19直下で、make menuconfigを実行します。実行後、Kernel Configuration画面が表示されます。

```
$ pwd    
/home/nao/KERNEL2/linux-source-4.19

$ make menuconfig

```

今回追加した自作Kernelモジュール用の設定は、Device Drivers -> Character devices -> DEBIMATE Test Module. に存在します。デフォルトでは、ビルド対象に含まれていないため(=n設定のため)、DEBIMATE Test Module.までカーソルを移動した後に、"m"を押下する事によってモジュール化を有効にします。Kernel内部に組み込む場合は、"y"を押下して下さい。

![Kernel Config](images/Screenshot-from-2019-07-15-12-39-42-min-300x228.jpg)

## 自作モジュールのビルド確認

今回は、Kernel全体をビルドせず、モジュールのみをビルドします。

```
$ pwd                        
/home/nao/KERNEL2/linux-source-4.19

$ make -j4 modules      (注釈) -jオプションの後の数値は、CPUコア数。

(注釈) ビルド終了後、Kernelモジュールが以下に作成されています。
$ ls drivers/char/debimate_module.ko
drivers/char/debimate_module.ko

```

\[the\_ad id="598"\]

## 最後に：Character Device作成方法に興味がある方へ

本記事で使用したCharacter Deviceに関する記事があります。Character Deviceの作成方法に興味がある方は、ご参考にして下さい。

https://debimate.jp/2019/06/23/linux-kernel%E3%81%AE%E7%B0%A1%E5%8D%98%E3%81%AAcharacter-device%E3%82%92%E4%BD%9C%E6%88%90%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95linked-list-api%E3%81%AE%E4%BD%BF%E7%94%A8%E6%96%B9%E6%B3%95%E3%82%B5/
