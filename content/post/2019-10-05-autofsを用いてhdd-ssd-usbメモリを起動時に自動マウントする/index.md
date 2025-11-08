---
title: "autofsを用いてHDD/SSD/USBメモリを起動時に自動マウントする方法(Debian)"
type: post
date: 2019-10-05
categories:
  - "linux"
tags:
  - "debian"
  - "hdd"
  - "linux"
  - "環境構築"
cover:
  image: "images/drive-3410753_640-min.jpg"
  alt: "autofsを用いてHDD/SSD/USBメモリを起動時に自動マウントする方法(Debian)"
  hidden: false
---

## 前書き

本記事では、autofsを用いて、HDD/SSD/USBメモリ(SATA接続 or M.2接続 or USB接続)を自動的にマウントする方法を紹介します。

一般的に、SATA接続の内蔵HDDなどはシステム起動時に自動的にマウントされません。自動マウントを有効化する方法として、/etc/fstabにマウント対象のストレージ情報を書きます。しかし、fstabによる方法は、デバイスにアクセスする頻度が少なくても、マウント対象のファイルシステム向けのリソースを消費します。また、設定を失敗した場合(ストレージをマウント出来なかった場合)、システムの起動に失敗し、Emergency Modeに移行する事があります。

これらの欠点を回避する方法として、autofs(automountユーティリティ)を使用します。autofsは、ストレージの自動マウント・アンマウントが可能であり、リソースを適宜節約できます。

## 検証環境

検証環境はDebian10とします。使用するHDD/SSDのフォーマット方法が知りたい場合は、以下の記事を参照してください。

```
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 10 (buster) x86_64 
 ,$$P'              `$$$.     Kernel: 4.19.67 
',$$P       ,ggs.     `$$b:   Uptime: 1 hour, 44 mins 
`d$$'     ,$P"'   .    $$$    Packages: 2282 (dpkg) 
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
              `"""            Memory: 37627MiB / 64404Mi
```

[gdisk/mkfsコマンドで2TB以上の大容量HDDをフォーマットする方法](https://debimate.jp/post/2019-10-05-gdisk-mkfs%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89%E3%81%A72tb%E4%BB%A5%E4%B8%8A%E3%81%AEhdd%E3%82%92%E3%83%95%E3%82%A9%E3%83%BC%E3%83%9E%E3%83%83%E3%83%88%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95/)

## autofsのインストール

autofsおよびストレージ情報を調べるためのe2fsprogsをインストールします。

```
$ sudo apt install autofs 
$ sudo apt install e2fsprogs 

```

## ストレージ情報(UUID)の調査

自動マウントを行うには、ストレージを識別するための[UUID(Universally Unique Identifier)](_wp_link_placeholder)およびファイルシステムを調査する必要があります。e2fsprogsパッケージに含まれるblkidコマンドを用いれば、以下のように両方の情報が得られます。

```
$ sudo blkid
/dev/sdb1: UUID="fecb3b9a-af4a-4a09-abdd-3fa633beaaa6" TYPE="ext4" PARTLABEL="Linux filesystem" PARTUUID="77628419-733e-44bb-9184-ed2967136b25"
/dev/sda: UUID="6cefaadb-8064-4177-be4d-4c96c50985ee" TYPE="ext4"
/dev/sdc1: UUID="8364-533A" TYPE="vfat" PARTUUID="7f5d2470-3daa-4244-985f-b5e830b54ae7"
/dev/sdc2: UUID="f4e3d49b-d0ef-4c6c-87de-bb3291f68dd2" TYPE="ext4" PARTUUID="69a3a018-3f7a-4187-abfc-da792e3bc38d"
/dev/sdc3: UUID="d0c09a3f-06f8-4411-a3c0-dcba2f407958" TYPE="swap" PARTUUID="f17a390a-769e-4d2c-876f-705680ff674c"

```

## autofs設定ファイルに自動マウント情報を追記

自動マウントを有効化するため、”/etc/auto.master “および”/etc/auto.misc “を編集します。私の環境では自動マウント対象は、

1. /dev/sda、UUID=6cefaadb-8064-4177-be4d-4c96c50985ee、fs=ext4
2. /dev/sdb1、UUID=fecb3b9a-af4a-4a09-abdd-3fa633beaaa6、fs=ext4

となります。

1.のストレージは/misc/hdd1、2.のストレージは/misc/hdd2にマウントする設定とします。auto.masterおよびauto.miscの書き換え方は以下の通りです。

```
$ sudo vi /etc/auto.master
 
[以下、/etc/auto.master内]
# 以下を追記。
# マウントポイント　マウント対処を記載したファイル名　　オプション(今回はなし)
/misc    /etc/auto.misc

# 以下をコメントアウト
# +auto.master

```

```
$ sudo vi /etc/auto.misc
 
[以下、/etc/auto.misc内]
# 追記項目
# マウントポイント　オプション　マウント対象
hdd1             -fstype=ext4,rw :/dev/disk/by-uuid/6cefaadb-8064-4177-be4d-4c96c50985ee
hdd2             -fstype=ext4,rw :/dev/disk/by-uuid/fecb3b9a-af4a-4a09-abdd-3fa633beaaa6

```

## 自動マウントに失敗する場合

自動マウントに失敗する場合は、設定ミスや[udisk(他機能)](https://wiki.archlinux.jp/index.php/Udisks)との競合が考えられます。一度、autofsを停止して、手動でautomountコマンドを実行すれば、自動マウントに失敗する理由が調査できます。

```
$ sudo systemctl stop autofs   (注釈)：autofsの停止
$ sudo automount -f -v         (注釈)：自動マウントの手動実行

```

例えば、/etc/auto.masterの"+auto.master"のコメントアウトを忘れた場合、

"lookup(file): failed to read included master map auto.master"

とエラーがでます。
