---
title: "gdisk/mkfsコマンドで2TB以上の大容量HDDをフォーマットする方法"
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
  image: "images/hard-drive-607461_640-min.jpg"
  alt: "gdisk/mkfsコマンドで2TB以上の大容量HDDをフォーマットする方法"
  hidden: false
---

### 前書き：何故HDDを2TBまでしか認識しないか

本記事では、gdisk/mkfsコマンドを用いて2TB超のHDDをフォーマットする方法を紹介します。

前提知識ですが、HDDは2TBの壁が存在します。HDDは、MBR(Master Boot Record)形式を用いて、パーティション(領域)をセクター単位で管理しています。通常のHDDは、セクターサイズが512Byteであり、パーティション内のセクター開始位置とセクター数の管理には4Byte(32bit)を使用します。この制約によって、「最大2TB(アクセスできるセクター数×セクターサイズ = 2の32乗×512)」までしか管理できません。

つまり、MBRにしか対応していないコマンド(例：fdisk)でHDDフォーマットを実行した場合、2TBまでしか認識しません。**2TB以上のHDDを取り扱う場合は、gdiskコマンドを使用します。**gdiskは、GPT(GUID Partition Table)形式でHDD領域を管理します。GPTは、セクター管理に8Byte(64bit)を使用できるため、最大8ZB(=2の64乗×512Byte)まで管理できます。一般的なHDDサイズ(2TB〜8TB)であれば、確実にフォーマットできます。

### 検証環境

Debian10環境とWestern DigitalのHDD(4TB、3.5インチ)を使用します。

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

<iframe style="width: 120px; height: 240px;" marginwidth="0" marginheight="0" scrolling="no" frameborder="0" src="//rcm-fe.amazon-adsystem.com/e/cm?lt1=_blank&amp;bc1=000000&amp;IS2=1&amp;bg1=FFFFFF&amp;fc1=000000&amp;lc1=0000FF&amp;t=debimate07-22&amp;language=ja_JP&amp;o=9&amp;p=8&amp;l=as4&amp;m=amazon&amp;f=ifr&amp;ref=as_ss_li_til&amp;asins=B01MRSPHIW&amp;linkId=5abcaca97012902ee766d24a0e9452d9"></iframe>

### gdiskのインストール

以下の手順でgdiskコマンドをインストール可能です。また、HDDがどのPATH(/dev/sd\*)で認識されているかを調べるために、hwinfoコマンドも一緒にインストールします。

```
$ sudo apt install gdisk 
$ sudo apt install hwinfo   (注釈)：ハードウェア情報を調べるコマンド  

```

### フォーマット対象のHDDを調査する方法

フォーマット対象のPATH情報(/dev/sd\*のいずれか)を明確にしなければ、OSが入ったSSDやHDDを誤って消去する可能性があります。そこで、hwinfoコマンドを用いて、HDDの型番情報から、フォーマット対象のHDD PATHを明確にします。

```
$ sudo hwinfo --disk --short
disk:                                                           
  /dev/sdb             WDC WD40EZRZ-00G
  /dev/sdc             WDC WDS200T2B0B
  /dev/sda             WDC WD40EZRZ-00G

```

hwinfo出力結果のWDはWestern Digitalの略で、検証環境ではWD社のデバイスが3個認識されている事になります。TOSHIBAやSeagateのHDDも、会社名が出力されます。上記の情報(型番)だけで、フォーマット対象が明確にならなかった場合は、shortオプションを削除すれば詳細な情報が得られます。

```
$ sudo hwinfo --disk  
47: IDE 600.0: 10600 Disk                                       
  [Created at block.245]
  Unique ID: WZeP.L6meSe08MpF
  Parent ID: vTuk.bD2u07ABOQ0
  SysFS ID: /class/block/sdb
  SysFS BusID: 6:0:0:0
  SysFS Device Link: /devices/pci0000:00/0000:00:01.2/0000:01:00.0/0000:02:0a.0/0000:06:00.0/ata7/host6/target6:0:0/6:0:0:0
  Hardware Class: disk
  Model: "WDC WD40EZRZ-00G"
  Vendor: "WDC"
  Device: "WD40EZRZ-00G"
  Revision: "0A80"
  Serial ID: "WD-WCC7K4KTAKFF"
  Driver: "ahci", "sd"
  Driver Modules: "ahci", "sd_mod"
  Device File: /dev/sdb
  Device Files: /dev/sdb, /dev/disk/by-path/pci-0000:06:00.0-ata-6, /dev/disk/by-id/wwn-0x50014ee2bc1287b7, /dev/disk/by-id/ata-WDC_WD40EZRZ-00GXCB0_WD-WCC7K4KTAKFF
  Device Number: block 8:16-8:31
  Geometry (Logical): CHS 486401/255/63
  Size: 7814037168 sectors a 512 bytes
  Capacity: 3726 GB (4000787030016 bytes)
  Config Status: cfg=new, avail=yes, need=no, active=unknown
  Attached to: #29 (SATA controller)

48: IDE d00.0: 10600 Disk
  [Created at block.245]
  Unique ID: _kuT.+VX7mUETFg8
  Parent ID: IluS.Zk47+4RfXI1
  SysFS ID: /class/block/sdc
  SysFS BusID: 13:0:0:0
  SysFS Device Link: /devices/pci0000:00/0000:00:08.3/0000:0b:00.0/ata14/host13/target13:0:0/13:0:0:0
  Hardware Class: disk
  Model: "WDC WDS200T2B0B"
  Vendor: "WDC"
  Device: "WDS200T2B0B"
  Revision: "90WD"
  Serial ID: "192489800726"
  Driver: "ahci", "sd"
  Driver Modules: "ahci", "sd_mod"
  Device File: /dev/sdc
  Device Files: /dev/sdc, /dev/disk/by-id/wwn-0x5001b448b8e26e9a, /dev/disk/by-id/ata-WDC_WDS200T2B0B_192489800726, /dev/disk/by-path/pci-0000:0b:00.0-ata-6
  Device Number: block 8:32-8:47
  Geometry (Logical): CHS 243201/255/63
  Size: 3907029168 sectors a 512 bytes
  Capacity: 1863 GB (2000398934016 bytes)
  Config Status: cfg=new, avail=yes, need=no, active=unknown
  Attached to: #10 (SATA controller)

49: IDE 500.0: 10600 Disk
  [Created at block.245]
  Unique ID: 3OOL.Kn_944YJ_eE
  Parent ID: vTuk.bD2u07ABOQ0
  SysFS ID: /class/block/sda
  SysFS BusID: 5:0:0:0
  SysFS Device Link: /devices/pci0000:00/0000:00:01.2/0000:01:00.0/0000:02:0a.0/0000:06:00.0/ata6/host5/target5:0:0/5:0:0:0
  Hardware Class: disk
  Model: "WDC WD40EZRZ-00G"
  Vendor: "WDC"
  Device: "WD40EZRZ-00G"
  Revision: "0A80"
  Serial ID: "WD-WCC7K4KTA98E"
  Driver: "ahci", "sd"
  Driver Modules: "ahci", "sd_mod"
  Device File: /dev/sda
  Device Files: /dev/sda, /dev/disk/by-id/ata-WDC_WD40EZRZ-00GXCB0_WD-WCC7K4KTA98E, /dev/disk/by-uuid/6cefaadb-8064-4177-be4d-4c96c50985ee, /dev/disk/by-id/wwn-0x50014ee2bc1263df, /dev/disk/by-path/pci-0000:06:00.0-ata-5
  Device Number: block 8:0-8:15
  Geometry (Logical): CHS 486401/255/63
  Size: 7814037168 sectors a 512 bytes
  Capacity: 3726 GB (4000787030016 bytes)
  Config Status: cfg=new, avail=yes, need=no, active=unknown
  Attached to: #29 (SATA controller)

```

hwinfoコマンドではなく、fdiskコマンドでも詳細な情報を取得できます。以下のfdiskコマンドは、別環境の結果なので、出力例として読んでください。

```
$ sudo fdisk -l
(省略)
Disk /dev/sda: 1.8 TiB, 2000398934016 bytes, 3907029168 sectors
Disk model: Tech            
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 4096 bytes
I/O size (minimum/optimal): 4096 bytes / 4096 bytes

Disk /dev/sdb: 931.5 GiB, 1000204886016 bytes, 1953525168 sectors
Disk model:                 
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 4096 bytes
I/O size (minimum/optimal): 4096 bytes / 4096 bytes
Disklabel type: dos
Disk identifier: 0xed79b4be

Device     Boot Start        End    Sectors   Size Id Type
/dev/sdb1        2048 1953525167 1953523120 931.5G 83 Linux

Disk /dev/sdc: 119.2 GiB, 128035676160 bytes, 250069680 sectors
Disk model: TS128GESD400K   
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 33553920 bytes
Disklabel type: dos
Disk identifier: 0x3eaccbac

Device     Boot  Start       End   Sectors  Size Id Type
/dev/sdc1         8192    532479    524288  256M  c W95 FAT32 (LBA)
/dev/sdc2       532480 250069679 249537200  119G 83 Linux

```

### gdiskコマンドによるパーティション作成

私の環境では、フォーマット対象のHDDは/dev/sdbです。gdiskコマンドを起動すると、GPT形式ではなくMBR形式でHDDが管理されているため、警告が出ます。今回のフォーマットでは、MBRをGPTに変換することが目的ですから、この警告は無視します。

```
$ sudo gdisk /dev/sdb 
GPT fdisk (gdisk) version 1.0.3

Partition table scan:
  MBR: MBR only
  BSD: not present
  APM: not present
  GPT: not present

***************************************************************
Found invalid GPT and valid MBR; converting MBR to GPT format
in memory. THIS OPERATION IS POTENTIALLY DESTRUCTIVE! Exit by
typing 'q' if you don't want to convert your MBR partitions
to GPT format!
***************************************************************

```

gdiskは、対話式で操作する必要があります。以降の手順では、

- d：既存パーティションの削除
- o：新しいGPT(GUID Partition Table)を作成
- n：新しいパーティションを作成
- p：現在のパーティションを確認
- w：ディスクに変更を書き込む

を順に実施します。既存パーティションは全て削除し、新しいパーティションは1個だけ作成します。選択肢は基本的にYesかDefault値で回答します。

```
$ sudo gdisk /dev/sdb 
Command (? for help): d      注釈)：パーティションの消去
Using 1

Command (? for help): d
No partitions　　　　　　　 (注釈)：パーティションを全て削除済み

Command (? for help): o       (注釈)：GPT作成
This option deletes all partitions and creates a new protective MBR.
Proceed? (Y/N): y

Command (? for help): n　　　　　　　　　(注釈)：新しいパーティションの作成
Partition number (1-128, default 1):  (注釈)：デフォルト値とするため、Enter
First sector (34-7814037134, default = 2048) or {+-}size{KMGTP}:     (注釈)：デフォルト値とするため、Ente
Last sector (2048-7814037134, default = 7814037134) or {+-}size{KMGTP}:      (注釈)：デフォルト値とするため、Enter
Current type is 'Linux filesystem'
Hex code or GUID (L to show codes, Enter = 8300):  (注釈)：デフォルト値とするため、Enter
Changed type of partition to 'Linux filesystem'

Command (? for help): p           (注釈)：パーティションの確認
Disk /dev/sdb: 7814037168 sectors, 3.6 TiB
Model: WDC WD40EZRZ-00G
Sector size (logical/physical): 512/4096 bytes
Disk identifier (GUID): 7BABC8AE-DFD4-4249-9877-E00C4E8A169C
Partition table holds up to 128 entries
Main partition table begins at sector 2 and ends at sector 33
First usable sector is 34, last usable sector is 7814037134
Partitions will be aligned on 2048-sector boundaries
Total free space is 2014 sectors (1007.0 KiB)

Number  Start (sector)    End (sector)  Size       Code  Name
   1            2048      7814037134   3.6 TiB     8300  Linux filesystem

Command (? for help): w        (注釈)：上記手順をHDDに反映

Final checks complete. About to write GPT data. THIS WILL OVERWRITE EXISTING
PARTITIONS!!

Do you want to proceed? (Y/N): Y        (注釈)：最終確認
OK; writing new GUID partition table (GPT) to /dev/sdb.
The operation has completed successfully.

```

### パーティションをext4形式でフォーマット

gdiskコマンドによって、/dev/sdb1パーティションが作成されています。このパーティションをmkfsコマンドによって、ext4ファイルシステムでフォーマットします。

```
$ sudo mkfs -t ext4 /dev/sdb1    
mke2fs 1.44.5 (15-Dec-2018)
/dev/sdb1 contains a ext4 file system
	last mounted on Sun Sep 29 13:59:01 2019
Proceed anyway? (y,N) y
Creating filesystem with 976754385 4k blocks and 244195328 inodes
Filesystem UUID: fecb3b9a-af4a-4a09-abdd-3fa633beaaa6
Superblock backups stored on blocks: 
	32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632, 2654208, 
	4096000, 7962624, 11239424, 20480000, 23887872, 71663616, 78675968, 
	102400000, 214990848, 512000000, 550731776, 644972544

Allocating group tables: done                            
Writing inode tables: done                            
Creating journal (262144 blocks): done
Writing superblocks and filesystem accounting information: done     

```

ここまでの手順で、フォーマットされたHDDが使用可能な状態になります。
