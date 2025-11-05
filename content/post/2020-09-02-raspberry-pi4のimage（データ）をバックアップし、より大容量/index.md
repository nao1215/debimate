---
title: "Raspberry Pi4のimage（データ）をバックアップし、より大容量なmicroSDカードにリストアする方法"
type: post
date: 2020-09-02
categories:
  - "linux"
tags:
  - "raspberrypi"
cover:
  image: images/hand-2605908_640-min.jpg
  alt: "Raspberry Pi4のimage（データ）をバックアップし、より大容量なmicroSDカードにリストアする方法"
  hidden: false
images: ["post/2020-09-02-raspberry-pi4のimage（データ）をバックアップし、より大容量/images/hand-2605908_640-min.jpg"]
---

## 前書き

本記事では、Raspberry Pi4のOS imageをバックアップし、より大容量なmicroSDカードにバックアップimageをリストアする方法を紹介します。

Raspberry Piには、「[SD Card Copier](https://pishop.co.za/blog/my-tutorial-post/clone-your-micro-sd-directly-on-rpi/)」というアプリがインストールされていますが、本記事では使用しません。代わりに、CLIでmicroSDカードのデータをバックアップ／リストアします。

## 検証環境

```
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 10 (buster) x86_64 
 ,$$P'              `$$$.     Kernel: 4.19.67 
',$$P       ,ggs.     `$$b:   Uptime: 1 hour, 52 mins 
`d$$'     ,$P"'   .    $$$    Packages: 4331 (dpkg), 13 (flatpak) 
 $$P      d$'     ,    $$P    Shell: fish 3.0.2 
 $$:      $$.   - ,d$$'    Resolution: 2560x1080 
 $$;      Y$b._   _,d$P'      DE: Pantheon 
 Y$$.    `.`"Y$$$$P"'         WM: Mutter(Gala) 
 `$$b      "-.__              Terminal: io.elementary.t 
  `Y$$                        CPU: AMD Ryzen 7 3800X 8- (16) @ 3.900GHz 
   `Y$$.                      GPU: NVIDIA NVIDIA Corporation TU107 
     `$$b.                    Memory: 4549MiB / 64404MiB 
       `Y$$b.
          `"Y$b._                                     
```

## Raspberry Piのバックアップimageを作成

まず、Host環境（Linux）にカードリーダーを接続し、microSDカードを挿入します。microSDカードがLinux上で、どのデバイスファイル（/dev以下のファイル）として認識されているかをfdiskコマンドで調べます。

以下の例では、HDD2個、SSD2個、microSDカード1個が搭載された環境に対して、fdiskコマンドを使用しています。

```
$ sudo fdisk -l
Disk /dev/sdc: 3.7 TiB, 4000787030016 bytes, 7814037168 sectors
Disk model: WDC WD40EZRZ-00G
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 4096 bytes
I/O size (minimum/optimal): 4096 bytes / 4096 bytes
Disklabel type: gpt
Disk identifier: 7BABC8AE-DFD4-4249-9877-E00C4E8A169C

Device     Start        End    Sectors  Size Type
/dev/sdc1   2048 7814037134 7814035087  3.7T Linux filesystem

Disk /dev/sda: 238.5 GiB, 256060514304 bytes, 500118192 sectors
Disk model: TS256GMTS800    
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
Disklabel type: gpt
Disk identifier: 87F71BE3-96D5-4AF9-B694-6E2DE9543803

Device         Start       End   Sectors   Size Type
/dev/sda1       2048   1050623   1048576   512M EFI System
/dev/sda2    1050624 433233919 432183296 206.1G Linux filesystem
/dev/sda3  433233920 500117503  66883584  31.9G Linux swap

Disk /dev/sdb: 3.7 TiB, 4000787030016 bytes, 7814037168 sectors
Disk model: WDC WD40EZRZ-00G
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 4096 bytes
I/O size (minimum/optimal): 4096 bytes / 4096 bytes
Disklabel type: gpt
Disk identifier: EEF005D9-4A2A-48EC-A27A-009F7D5BA083

Device          Start        End    Sectors  Size Type
/dev/sdb1        2048 3900000000 3899997953  1.8T Linux filesystem
/dev/sdb2  3900000256 7814037134 3914036879  1.8T Linux filesystem

Disk /dev/sdd: 1.8 TiB, 2000398934016 bytes, 3907029168 sectors
Disk model: WDC WDS200T2B0B 
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
Disklabel type: gpt
Disk identifier: CC896053-2073-495A-A3F0-3D0ECAC02B6E

Device          Start        End    Sectors  Size Type
/dev/sdd1        2048    1050623    1048576  512M EFI System
/dev/sdd2     1050624 3772981247 3771930624  1.8T Linux filesystem
/dev/sdd3  3772981248 3907028991  134047744 63.9G Linux swap

Disk /dev/sde: 14.4 GiB, 15489564672 bytes, 30253056 sectors
Disk model: STORAGE DEVICE  
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
Disklabel type: dos
Disk identifier: 0x9edea3d6

Device     Boot  Start      End  Sectors  Size Id Type
/dev/sde1         8192   532479   524288  256M  c W95 FAT32 (LBA)
/dev/sde2       532480 30253055 29720576 14.2G 83 Linux

```

上記の出力は、HDDやSSDが沢山マウントしてあるので分かりづらいですが、サイズから/dev/sdeがRaspberry Pi用のmicroSDカードだと判断できます。

次に、microSDカードのデータを"raspi.img"としてカレントディレクトリにバックアップします。バックアップには、ddコマンドを使用します。

```
※ ifがバックアップ対象、ofが出力先のファイルPATH、bsが1度に読み書きするサイズ
$ sudo dd if=/dev/sde of=raspi.img bs=10M

```

バックアップが完了した後、microSDカードをカードリーダから取り外します。

## バックアップimageをmicroSDカードにリストア

先程バックアップしたRaspberry Piのimageを新しいmicroSD（今回は64GB）にリストアします。microSDカードがどのデバイスファイルに割り当てられたかは、前述の手順と同様にfdiskコマンドで確認します（確認結果は省略し、/dev/sdeだったと仮定して以下の手順を進めます）。

バックアップと同様に、リストアにもddコマンドを使用します。

```
※ ifがバックアップしたimage、ofが出力先のmicroSDカードのPATH、bsが1度に読み書きするサイズ
$ sudo dd if=raspi.img of=/dev/sde bs=20M

```

## microSDカードのパーティションを拡張

今回の例では、Raspberry Pi用のmicroSDカードは、容量が16GBから64GBに拡張されました。しかしながら、ddコマンドで新しいmicroSDカードにリストアしただけでは、使用できる領域は16GBのままです。

そのため、microSDカードのパーティションサイズをmicroSDカードの容量限界まで拡張します。パーティションの拡張には、Raspberry Pi公式の設定ツールであるraspi-configコマンドを使用します。

以下の手順は、Raspberry Pi上で実行してください。

```
$sudo raspi-config

※ 以下の順で選択肢を選んでください。
[7 Advanced Options]
  ⇓
[A1 Expand Filesystem]
  ⇓
再起動を促すメッセージでYes

```

## おまけ：バックアップimageサイズを縮小する方法

[Raspberry Pi公式がバックアップimageを縮小するためのperlスクリプト](https://www.raspberrypi.org/forums/viewtopic.php?f=91&t=58069)を提供しています。以下の書式で使用します。

```
※ スクリプトに実行権限を付与
$ chmod a+x resizeimage.pl 

※ キャッシュをファイルに書き込まないとエラーとなるため、書き出し
$ sync

※ 書式：sudo ./resizeimage.pl $(imageの絶対PATH)
$ sudo ./resizeimage.pl  /home/nao/img/raspi.img
raspi.img:
==========
Old size - 14771 MB (14.43 GB)
New size - 7304 MB (7.13 GB)
Image file was reduced by 7467 MB (7.29 GB)

```
