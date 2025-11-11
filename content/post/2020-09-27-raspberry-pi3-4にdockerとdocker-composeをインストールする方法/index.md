---
title: "Raspberry Pi3/4にDockerとdocker-composeをインストールする方法"
type: post
date: 2020-09-27
categories:
  - "linux"
tags:
  - "docker"
  - "linux"
  - "raspberrypi"
cover:
  image: "images/lfVWBmiW_400x400-min.jpg"
  alt: "Raspberry Pi3/4にDockerとdocker-composeをインストールする方法"
  hidden: false
---

### 前書き

本記事では、Raspberry Pi3/4（32bit、64bit）のいずれかに対して、Dockerおよびdocker-composeをインストールする方法を紹介します。

Raspberry Piのネットワーク設定が終了している状態を前提とします。

### 前準備

Dockerはcgroups機能（プロセスが使用するリソースを制限する機能）を使用するため、/boot/cmdline.txtを編集してcgroupsを有効化します。

```
※編集前
console=serial0,115200 console=tty1 root=PARTUUID=2677d299-02 rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait

※編集後（cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1を追加）
console=serial0,115200 console=tty1 root=PARTUUID=2677d299-02 rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1

```

編集が終わった後、再起動するとcgroups機能が有効になります。

### Dockerのインストール

まずは、Dockerの依存パッケージをインストールします。

```
$ sudo apt update
$ sudo apt install apt-transport-https ca-certificates curl gnupg2 software-properties-common
```

次に、Dockerインストール時に用いる署名鍵を取得します。

```
(注釈) bash環境で実行してください。fishなどでは変数展開できません。
$ curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg | sudo apt-key add -

(注釈) $(. /etc/os-release; echo "$ID")の部分は、"debian"です。

```

aptパッケージマネージャのソースリストに対して、Docker公式リポジトリを追加します。

```
$ echo "deb [arch=$(dpkg --print-architecture)] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") \
     $(lsb_release -cs) stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list

```

最後に、Docker CE（Community Edition）をインストールし、必要であればシステム起動時にDockerが自動起動するようにsystemdの設定を変更します。

```
$ sudo apt update
$ sudo apt install -y --no-install-recommends docker-ce cgroupfs-mount

(注釈) Dockerの有効化と起動 
$ sudo systemctl enable docker
$ sudo systemctl start docker

```

### docker-composeのインストール

Docker Composeは、複数のコンテナから構成されるアプリにおいて、コンテナの起動や停止を簡単できるようにするツールです。

公式サイトが配布しているバイナリがARM向けではないため、Python3パッケージマネージャであるpip3でインストールできるVersionを使用します（[この対応は、公式サイトにも記載があります](https://docs.docker.jp/compose/install.html)）。

そのため、まずはpip3の依存パッケージをインストールします。

```
$ sudo apt install libffi-dev libssl-dev python3 python3-pip python3-dev

```

Docker Composeをインストールします。

```
$ sudo pip3 install docker-compose

```

私は、Docker Composeインストール中にmicroSDカード容量（16GB）が足りなくなり、エラーとなりました。より容量の大きいmicroSDカードに移行する場合は、以下の記事を参考にしてください。

- [Raspberry Pi4のimage（データ）をバックアップし、より大容量なmicroSDカードにリストアする方法](https://debimate.jp/post/2020-09-02-raspberry-pi4%E3%81%AEimage%E3%83%87%E3%83%BC%E3%82%BF%E3%82%92%E3%83%90%E3%83%83%E3%82%AF%E3%82%A2%E3%83%83%E3%83%97%E3%81%97%E3%82%88%E3%82%8A%E5%A4%A7%E5%AE%B9%E9%87%8F/)
