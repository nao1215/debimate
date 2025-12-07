---
title: "Raspberry Pi3(Linux Kernel)のBoot Sequence Step1:アーキテクチャ依存部"
type: post
date: 2018-12-31
categories:
  - "linux"
tags:
  - "linux"
  - "linuxkernel"
  - "raspberrypi"
cover:
  image: "images/Raspberry-Pi-3-Ports-1-1833x1080-e1546321071607.jpg"
  alt: "Raspberry Pi3(Linux Kernel)のBoot Sequence Step1:アーキテクチャ依存部"
  hidden: false
---

### 前書き

シングルボードコンピュータの[Raspberry Pi3](https://www.raspberrypi.org/)を用いて、[Linux Kernel](https://www.kernel.org/)のBoot Sequenceを調査します。その調査結果を複数回に分けて、記事にします。対象のLinux Kernelは、[Raspberry Pi(OS)のソースコード rpi-4.1.y](https://github.com/raspberrypi/linux)とします。

本記事では、電源投入からinitプロセスが立ち上がるまでを記載します。

---


### Raspberry Piの起動に関わるソフトウェア

Raspberry Piに電源が投入された後、複数のBootloaderが実行されます。Bootloaderが多段の理由は、公式で情報がありません。推測ですが、バイナリサイズや起動コードの隠蔽が目的ではないかと考えています。

| **名称** | **格納先** | **役割** |
| --- | --- | --- |
| Primary   bootloader | SoC内ROM | bootcode.binをL2 cacheに読み込んだ後、   bootcode.binに制御を移す事 |
| bootcode.bin(※) | microSD   (/boot/bootcode.bin) | start.elfをRAMへ読み込んだ後、   start.elfに制御を移す事 |
| start.elf |   microSD   (/boot/start.elf)   | config.txt、cmdline.txtを読み込んだ後   kernel.img、Device Tree BlobをRAMに展開。   その後、kernel7.imgに制御を移す事。 |
| kernel7.img | microSD   (/boot/kernel7.img) | Linux Kernelの初期化を実施した後、   systemd(initプロセス)を実行する事 |
| systemd | microSD   (/lib/systemd/systemd) | 各種サービスを稼働した後、   コマンドプロンプト(shell)を実行する事 |

※2012年10月まで、start.elfを読み込むためのloader.bin(三段階目)が存在したが、削除された。参考：[https://www.raspberrypi.org/forums/viewtopic.php?f=66&t=65022](https://www.raspberrypi.org/forums/viewtopic.php?f=66&t=65022)

---


### 起動シーケンスの概略

1. 電源を投入
2. GPU(Broadcom VideoCore IV)が起動
3. GPUがSoCのROMからPrimary Bootloaderを読み込み、実行
4. GPUがmicroSDからL2キャッシュにbootcode.binを読み込み、実行
5. bootloader.bin内でGPU firmware(start.elf)を読み込む
6. start.elf内でconfig.txt、cmdline.txtを読み込み、
7. kernel7.imgとDTBを読み込む
8. start.elf内でkernel7.img(Linux Kernel)のStart Addressに移動
9. Linux Kernelが初期化プロセス(デバイスの初期化、Linux Kernelサブシステムの初期化など)を実行
10. Linux Kernelがsystemd(initプロセス)を起動

---


### 参考

[How does Raspberry Pi boot?](https://raspberrypi.stackexchange.com/questions/10489/how-does-raspberry-pi-boot)

[Raspberry PI bare metal Part 1: The Boot Process](http://kariddi.blogspot.com/2012/08/raspberry-pi-bare-metal-part-1-boot.html)

[HOW THE RASPBERRY PI BOOTS UP](https://thekandyancode.wordpress.com/2013/09/21/how-the-raspberry-pi-boots-up/)
