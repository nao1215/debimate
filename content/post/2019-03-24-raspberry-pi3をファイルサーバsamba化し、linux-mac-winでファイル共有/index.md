---
title: "Raspberry Pi3をsambaファイルサーバ化し、Linux/Mac/Winでファイル共有(外付けSSDを使用)"
type: post
date: 2019-03-24
categories:
  - "linux"
tags:
  - "linux"
  - "raspberrypi"
  - "環境構築"
cover:
  image: "images/Raspberry-Pi3_min.jpg"
  alt: "Raspberry Pi3をsambaファイルサーバ化し、Linux/Mac/Winでファイル共有(外付けSSDを使用)"
  hidden: false
---

### 前書き

家庭内にLinux/Mac/Windows環境が存在する場合、各PCから写真などを閲覧する事が手間な場合があります。クラウドが一つの解決策ですが、写真はサイズが大きいため、クラウドを無料使用できる範囲を超えます（あと、クラウドは同期が遅い）。そこで、各PCでファイルを共有するため、Rapsberry Pi3を[samba](https://www.samba.org/)ファイルサーバ化します。sambaはUNIX系OS上でWindows互換のファイルサーバ・プリントサーバを立ち上げるOSSです。

本記事では、Raspberry Pi3上にファイルサーバを立ち上げるまでの手順4点を示します。ただし、Raspberry Pi3にRaspbian(OS)をインストール済み、かつネットワーク接続設定済みの状態と仮定しています。

手順

- sambaパッケージのインストール
- Raspberry Pi3を固定IP化
- 外部ストレージの自動マウント設定
- sambaの設定・立ち上げ

---


### 環境

| **項目** | **機器/Version** | **用途・備考** |
| --- | --- | --- |
| ボード | Raspberry Pi3 Model B | samba(Version 4.5.16-Debian)が動作する環境 |
| OS用ストレージ | MicroSDカード(Silicon Power、16GB、Class10) | Class4以上かつ16GB以上の容量が必要。Raspbianが導入されている前提。 |
| ファイルサーバ用ストレージ | Transcend 外付けSSD 128GB USB3.0 MLC TS128GESD400K | 用途に合わせて、サイズ・種類(HDD or SSD)を決め、変更して良い。 |
| モニタ | ASUS VZ249H |   Raspberry Pi3用。SSHでRaspberry Pi3に接続する場合、およびファイルサーバ化の手順が終了した場合、不要。   |
| 電源(ターゲット) | microUSB - USBケーブル、iPad mini2用のUSB充電器 | 特になし |
| 映像/音声 | HDMIケーブル(PS4付属品) | ファイルサーバ化の手順が終了した場合、不要。 |
| 入出力装置 | キーボード、マウス(USB接続) | ファイルサーバ化の手順が終了した場合、不要。 |

```
$ neofetch
  .',;:cc;,'.    .,;::c:,,.    nao@nao 
 ,ooolcloooo:  'oooooccloo:    ------- 
 .looooc;;:ol  :oc;;:ooooo'    OS: Raspbian GNU/Linux 9.8 (stretch) armv7l 
   ;oooooo:      ,ooooooc.     Model: Raspberry Pi 3 Model B Rev 1.2 
     .,:;'.       .;:;'.       Kernel: 4.14.98-v7+ 
     .... ..'''''. ....        Uptime: 1 hour, 6 minutes 
   .''.   ..'''''.  ..''.      Packages: 1580 
   ..  .....    .....  ..      Shell: bash 4.4.12 
  .  .'''''''  .''''''.  .     CPU: ARMv7 rev 4 (v7l) (4) @ 1.2GHz 
.'' .''''''''  .'''''''. ''.   Memory: 72MB / 926MB 
'''  '''''''    .''''''  '''    
.'    ........... ...    .'.   ████████████████████████ 
  ....    ''''''''.   .''.      
  '''''.  ''''''''. .''''' 
   '''''.  .'''''. .'''''. 
    ..''.     .    .''.. 
          .''''''' 
           ...... 

```

---


### sambaパッケージのインストール

exfat-fuse、cifs-utilsは、Windows側のファイルシステムをmountする場合に備えて、インストールします。autofsは、外部ストレージを自動でmount/unmoutするために導入します。

```
$ sudo apt update
$ sudo apt upgrade
$ sudo apt install samba exfat-fuse cifs-utils autofs

$ samba -V (注釈)：今回使用するsambaのVersion
Version 4.5.16-Debian

```

---


### Raspberry Pi3を固定IP化

各PCはRaspberry PiのIPアドレスに対してアクセスする事もあるため、固定IP化します。IPの固定化方法は、以下の記事を参照してください。固定後のIPアドレスは、"192.168.10.108"と仮定します。

- [Raspberry Piに固定IPを割り当てる方法](https://debimate.jp/post/2019-03-24-raspberry-pi3%E3%82%92%E5%9B%BA%E5%AE%9Aip%E5%8C%96%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95/)

---


### 外部ストレージの自動マウント設定

今回の例では、各PCはネットワーク経由で、外部ストレージ(SSD)にアクセスします。そのため、外部ストレージをmountし、適切なファイルシステムに変更する必要があります。今回は、OS起動時にmountを手動で行う手間を省くため、外部ストレージのUUID(一意な識別子)を用いて自動mountします。自動mountする場合は、外部ストレージ接続順で変動するPATH(例：/dev/sdb)より、UUID(固定値)を用いた方が好ましいです。

まず、外部ストレージをRaspberry Pi3にUSB接続します。dmesgで判別できない場合は、"sudo fdisk -l"でもストレージ情報が確認できます。

```
$ sudo dmesg | tail  (注釈)：外部ストレージをUSB接続後、dmesgで直近のブロックデバイスを確認(今回は、sdb)
[ 2049.947935] usb-storage 1-1.2:1.0: USB Mass Storage device detected
[ 2049.950957] scsi host1: usb-storage 1-1.2:1.0
[ 2050.966300] scsi 1:0:0:0: Direct-Access     StoreJet TS128GESD400K    0    PQ: 0 ANSI: 6
[ 2050.967154] sd 1:0:0:0: Attached scsi generic sg0 type 0
[ 2050.971090] sd 1:0:0:0: [sdb] 250069680 512-byte logical blocks: (128 GB/119 GiB)
[ 2050.971524] sd 1:0:0:0: [sdb] Write Protect is off
[ 2050.971536] sd 1:0:0:0: [sdb] Mode Sense: 43 00 00 00
[ 2050.971960] sd 1:0:0:0: [sdb] Write cache: enabled, read cache: enabled, doesn't support DPO or FUA
[ 2050.976316]  sdb: sdb1
[ 2050.978609] sd 1:0:0:0: [sdb] Attached SCSI disk

```

次に、外部ストレージ(/dev/sdb)のファイルシステムを消去し、exfat形式にフォーマットします。

```
$ sudo wipefs -a /dev/sdb    (注釈)：ファイルシステムからパーティション情報を消去

$ sudo fdisk /dev/sdb　(注釈)：パーティションの作成
 
(注釈)：次の順で実行
　n：パーティションの作成
　　  ⇒ 以降の選択肢は全て[Enter]
　p：パーティションの表示
　　 ⇒ /dev/sdb1にType=Linux のパーティションが表示されればOK
　w：書き込み（設定を反映）
　q：終了

$ sudo mkfs.exfat /dev/sdb1   (注釈)：exfatファイルシステムを作成
```

最後に、自動mount設定をautofsによって実現します。自動mountは/etc/fstabを用いても実現できます。しかし、autofsの方がアクセス要求があった場合のみmountを行うため、システム負荷が低いです。また、fstabの場合、設定を失敗した場合(外部ストレージをmount出来なかった場合)、Raspberry Pi3が起動失敗し、Emergency Modeに移行します。その後の復旧作業が面倒なため、autofsを用います。

外部ストレージ(/dev/sdb)のUUIDを調べた後、"/etc/auto.master "および"/etc/auto.misc "に以下を追記します。

```
$ sudo blkid /dev/sdb1  (注釈)：UUIDの確認
/dev/sdb1: LABEL="NFS" UUID="5B2B-6E3C" TYPE="exfat" PARTUUID="6b70f462-01"

$ sudo vi /etc/auto.master

[以下、/etc/auto.master内]
# 以下を追記。
# マウントポイント　マウント対処を記載したファイル名　　オプション
/mnt    /etc/auto.misc

```

```
$ sudo vi /etc/auto.misc

[以下、/etc/auto.misc内]
# 追記項目
# マウントポイント　オプション　マウント対象
ssd             -fstype=exfat-fuse,rw,umask=000 :/dev/disk/by-uuid/5B2B-6E3C

```

---


### sambaの設定・立ち上げ

smb.confを編集し、ネットワークに公開するディレクトリの設定を行います。Raspberry Pi上にnaoユーザが存在すると仮定し、以下の設定ファイルを記載しています。

```
$ sudo vi /etc/samba/smb.conf

[以下、/etc/samba/smb.conf内]
# 追記項目は以下の通り。

# 外部PCから見えるディレクトリ名
[pi] 
  # 自由記入
  comment = Raspberry pi 

  # 外部公開するディレクトリ
  path = /mnt/ssd                 
  # guest okの別名。接続時、パスワードが要求されない。
  public = yes

   # 読み込みのみかどうか
  read only = no

  # ネットワークに表示するかどうか
  browsable = yes

  # Raspberry Pi3上のユーザ名(ファイル操作は、このユーザの権限で実施)
  force user = nao               

```

上記の設定後、testparmコマンドでsmb.confの構文エラーチェックを行います。問題がなければsamba(および関連デーモン)を自動起動するように設定し、Raspberry Pi3を再起動します。

```
# smb.confの構文チェックを行う。
$ testparm
rlimit_max: increasing rlimit_max (1024) to minimum Windows limit (16384)
Load smb config files from /etc/samba/smb.conf
rlimit_max: increasing rlimit_max (1024) to minimum Windows limit (16384)
Processing section "[homes]"
Processing section "[printers]"
Processing section "[print$]"
Processing section "[samba]"
Loaded services file OK.     (注釈) この表示が出ればOK。

(注釈) 省略

# sambaに関わるデーモンを有効化
$ sudo systemctl enable smbd
$ sudo systemctl enable nmbd

# 再起動
$ sudo reboot

```

---


### sambaアクセス権を設定する場合

sambaアクセス時にユーザパスワード認証を行いたい場合は、以下のように設定します。

```
$ sudo vi /etc/samba/smb.conf

[以下、/etc/samba/smb.conf内]
# 以下のように設定されているかどうかを確認する。
[global]
    # sambaアクセス時にユーザ名とパスワードの入力を求める設定
    security = user
    # その他の設定項目は省略
        

# 外部PCから見えるディレクトリ名
[pi] 
    # アクセス許可するユーザ名
    valid users = nao
    # その他の設定項目は省略

```

次に、pdbeditコマンドを使って、Sambaユーザを登録します。登録するSambaユーザ名は、Raspberry Pi（Linux）のシステム上に存在し、かつsambaアクセスを許可したいユーザ名（smb.confのvalid usersに記載したユーザ名）にする必要があります。

今回の例では、naoユーザを新規作成します。

```
$ sudo pdbedit -a nao

```

以上が終了した後、Raspberry Piを再起動すれば設定が反映されます。
