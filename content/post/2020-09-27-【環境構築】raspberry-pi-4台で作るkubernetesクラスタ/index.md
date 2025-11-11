---
title: "【環境構築】Raspberry Pi 4台で作るKubernetesクラスタ"
type: post
date: 2020-09-27
categories:
  - "linux"
tags:
  - "docker"
  - "kubernetes"
  - "raspberrypi"
  - "環境構築"
cover:
  image: "images/Screenshot-from-2020-08-31-18-38-47-min.jpg"
  alt: "【環境構築】Raspberry Pi 4台で作るKubernetesクラスタ"
  hidden: false
---

### 前書き：憧れのラズパイクラスタ

Raspberry Piでスパコンを構築する取り組みは昔からありましたが、最近は「Kubernetesクラスタを作ったよ」という報告が増えてきました。私もラズパイ4（8GB）を一台購入してラズパイが合計4台となったのをキッカケに、憧れのラズパイクラスタに手を出してみました！

本記事では「導入手順(ネットワーク接続などのセットアップ説明は除く)」や「ハマったポイント」を紹介します。

### クラスタ材料（ハード、ソフト）

| **機器・ソフト** | **個数** | **役割・備考** |
| --- | --- | --- |
| [Raspberry Pi](https://www.amazon.co.jp/%E3%80%90%E5%9B%BD%E5%86%85%E6%AD%A3%E8%A6%8F%E4%BB%A3%E7%90%86%E5%BA%97%E5%93%81%E3%80%91Raspberry-Pi4-ModelB-%E3%83%A9%E3%82%BA%E3%83%99%E3%83%AA%E3%83%BC%E3%83%91%E3%82%A44-%E6%8A%80%E9%81%A9%E5%AF%BE%E5%BF%9C%E5%93%81%E3%80%90RS%E3%83%BBOKdo%E7%89%88%E3%80%91/dp/B08B5YCSFY/ref=as_li_ss_tl?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&dchild=1&keywords=raspberry+pi+4+%EF%BC%98gb&qid=1598868515&s=computers&sr=1-3&linkCode=ll1&tag=debimate07-22&linkId=2b8d222ae0a5e442ef635a578a957e76&language=ja_JP) | 4台 | 本記事ではRaspberry Pi 3（2台）、Pi 4（2台）を使用。クラスタのMasterはメモリ使用量が大きいので、Pi4（RAM4GB以上）がオススメ。 |
| [microSD](https://www.amazon.co.jp/gp/product/B074B4BFHJ/ref=as_li_ss_tl?ie=UTF8&psc=1&linkCode=ll1&tag=debimate07-22&linkId=94ca64759ea6c9aed7e9bc30c13397da&language=ja_JP) | 4枚 | 本記事では16GB〜64GBを使用。Class10、32GB以上がオススメ。16GBの場合、クラスタ構築が終わった段階で空き容量が不足するかもしれません。 |
| [LANケーブル](https://www.amazon.co.jp/gp/product/B008RVY4BU/ref=as_li_ss_tl?ie=UTF8&psc=1&linkCode=ll1&tag=debimate07-22&linkId=6e0ec5509580d4b10c953bd226ae7a9b&language=ja_JP) | 5本 | 本記事ではCat6aを使用。 |
| [4層ラックケース](https://www.amazon.co.jp/gp/product/B07TJ15YL1/ref=as_li_ss_tl?ie=UTF8&psc=1&linkCode=ll1&tag=debimate07-22&linkId=523aa01905b623b6de7556cac25beb75&language=ja_JP) | 1個 | Raspberry Piを縦に積み上げるタイプのケース。ファンとヒートシンクも付いてきて、お得感があります。私は1層タイプのケースも予備で買いました。 |
| [USB Type A to TypeC](https://www.amazon.co.jp/gp/product/B016QCPUNM/ref=as_li_ss_tl?ie=UTF8&psc=1&linkCode=ll1&tag=debimate07-22&linkId=248f0c14cb1d30705407ffc86a04c1de&language=ja_JP) | X個 | Raspberry Pi4用の電源ケーブル。Pi4の数だけ必要。 |
| [microUSB to USB TypeA](https://www.amazon.co.jp/Anker-USB%E3%82%B1%E3%83%BC%E3%83%96%E3%83%AB%E3%80%902%E9%87%8D%E7%B7%A8%E8%BE%BC%E3%81%AE%E9%AB%98%E8%80%90%E4%B9%85%E3%83%8A%E3%82%A4%E3%83%AD%E3%83%B3%E7%B4%A0%E6%9D%90-%E7%B5%90%E6%9D%9F%E3%83%90%E3%83%B3%E3%83%89%E4%BB%98%E5%B1%9E%E3%80%91%E6%80%A5%E9%80%9F%E5%85%85%E9%9B%BB-Xperia%E3%80%81Nexus%E3%80%81Samsung%E3%80%81Android-%E5%90%84%E7%A8%AE%E3%80%81%E3%81%9D%E3%81%AE%E4%BB%96USB%E6%A9%9F%E5%99%A8%E5%AF%BE%E5%BF%9C/dp/B019Q0U31A/ref=as_li_ss_tl?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&dchild=1&keywords=microUSB&qid=1598869583&sr=8-8&linkCode=ll1&tag=debimate07-22&linkId=0cccf053a6672fe65eaa6f02b0cda0ef&language=ja_JP) | X個 | Raspberry Pi3用の電源ケーブル。Pi4の数だけ必要。 |
| [microHDMIケーブル](https://www.amazon.co.jp/gp/product/B07CLP4HPN/ref=ppx_od_dt_b_asin_title_s00?ie=UTF8&psc=1) | 1個 | Raspberry Pi4用の映像出力ケーブル。 |
| [HDMIケーブル](https://www.amazon.co.jp/5%E7%A8%AE%E9%95%B7%E3%81%95%E3%80%91iVANKY-HDMI2-0%E8%A6%8F%E6%A0%BC-Nintendo-TV%E3%81%AA%E3%81%A9%E9%81%A9%E7%94%A818gbps-%E3%83%8F%E3%82%A4%E3%82%B9%E3%83%94%E3%83%BC%E3%83%89%E3%83%97%E3%83%AC%E3%83%9F%E3%82%A2%E3%83%A0/dp/B07Y564HJV/ref=as_li_ss_tl?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&dchild=1&keywords=HDMI&qid=1598869681&sr=8-1-spons&psc=1&spLa=ZW5jcnlwdGVkUXVhbGlmaWVyPUEySUw2NjdJWUNKVkdDJmVuY3J5cHRlZElkPUExMDA3NDIyMkRZTklGM1IyMUJYRyZlbmNyeXB0ZWRBZElkPUEyMUVWRzdCOEoyN1ZEJndpZGdldE5hbWU9c3BfYXRmJmFjdGlvbj1jbGlja1JlZGlyZWN0JmRvTm90TG9nQ2xpY2s9dHJ1ZQ==&linkCode=ll1&tag=debimate07-22&linkId=4738c806ba9ee0895b90b882d7e6e62c&language=ja_JP) | 1個 | Raspberry Pi3用の映像出力ケーブル。 |
| [無線LAN親機(小型)](https://www.amazon.co.jp/dp/B07R4VGR8L/ref=as_li_ss_tl?ie=UTF8&linkCode=ll1&tag=debimate07-22&linkId=5480cd09099cf07b055eee52cf7357f5&language=ja_JP) | 1個 | 上流のルータに無線接続する時に使用しますが、有線接続の場合は不要。 |
| [スイッチングハブ](https://www.amazon.co.jp/dp/B00D5Q7V1M/ref=as_li_ss_tl?ie=UTF8&linkCode=ll1&tag=debimate07-22&linkId=f05aa96285c6d28a9e725871e62ed1a4&language=ja_JP) | 1個 | Raspberry Pi 4台のLANと接続するスイッチングハブ。 |
| [USB充電器](https://www.amazon.co.jp/dp/B00PK1QBO8/ref=as_li_ss_tl?ie=UTF8&linkCode=ll1&tag=debimate07-22&linkId=f212e73e49f3c5b8ae90deb43b9f8ac7&language=ja_JP) | 1個 | 本記事では60W、6ポートのタイプを使用。 |
| [Raspberry Pi OS with Desktop](https://www.raspberrypi.org/downloads/raspberry-pi-os/) | 1個 | Raspberry PiのOS。最終的にはデスクトップ環境は不要なので、Linuxが得意な人はLite版でも問題ありません。 |

<blockquote class="twitter-tweet"><p dir="ltr" lang="ja">自宅に余っているRaspberry Pi 2, 3とPi4 (RAM 8GB)を使って、ラズパイクラスタを作るぞ！ <a href="https://t.co/uxyBRukYqx">pic.twitter.com/uxyBRukYqx</a></p>— Nao (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1268496115520770048?ref_src=twsrc%5Etfw">June 4, 2020</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

上記のTweetでRaspberry Pi2を使ったと書いていますが、組み立て中にお亡くなりになっている事が判明したので、2から4に差し替えました。

<blockquote class="twitter-tweet"><p dir="ltr" lang="ja">ラズパイクラスタの最下段のお方（Pi2B）、天寿を全うされていました。<br>手持ちのボードで代替すると、環境構築の難易度が上がるので、ラズパイ4を補充します。 <a href="https://t.co/8Dj84by4vb">pic.twitter.com/8Dj84by4vb</a></p>— Nao (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1269173095555674113?ref_src=twsrc%5Etfw">June 6, 2020</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

### Raspberry Piの基本的なセットアップと組み立て

Raspberry Piの基本的なセットアップおよび組み立て方法は、本記事では説明しません。想定している基本的なセットアップ内容を以下に示します。

Raspberry Piの基本的なセットアップ内容（以下は説明を省略します）

- Raspberry Pi用のOSをmicroSDカードに書き込み
- Raspberry Piを起動し、キーボードや時刻の設定
- Raspberry Piを無線もしくは有線でネットワーク接続
- Raspberry Piが使用できるmicroSDの領域を拡大
- OSのアップデート

組み立てに関しては、説明書に図が多いため、1〜2時間で完了すると思われます。

<blockquote class="twitter-tweet"><p dir="ltr" lang="ja">ラズパイクラスタ組み立て中。 <a href="https://t.co/iUtDxoin4W">pic.twitter.com/iUtDxoin4W</a></p>— Nao (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1268513407407288320?ref_src=twsrc%5Etfw">June 4, 2020</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

### 全てのRaspberry Piを固定IP化

DHCP設定の場合、Raspberry Piの再起動に伴い、IPアドレスが変わってしまいます。この状態では、Host環境からRaspberry PiにSSH接続する際に不便ですので、IPアドレスを固定化します。

以下の記事を参考にIPアドレスを固定化します。SSH接続する際にIPアドレスが必須なので、メモしてください。

- [Raspberry Piに固定IPを割り当てる方法](https://debimate.jp/post/2019-03-24-raspberry-pi3%E3%82%92%E5%9B%BA%E5%AE%9Aip%E5%8C%96%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95/)

### 全てのRaspberry PiのHost名を変更

この手順は必須ではありません。SSH接続した際に、どのRaspberry Piにログインしているか（およびクラスタのMaster<->Slaveの関係）を分かりやすくするために、Host名を変更します。

Host名は、任意です。よく見られる命名規則は都市の名前、ディズニーキャラ名、太陽系の惑星名などを使用するケースです。私は、スラッシュメタル四天王（Big4）の名前を付けました。この名付けによって、ラズパイクラスタへの愛着が増します。

以下、Host名とRaspberry Piの組み合わせです。

| **機器** | **Host名** | **役割** |
| --- | --- | --- |
| Raspberry Pi4(8GB) | metallica | ラズパイクラスタのMaster |
| Raspberry Pi3 Model B | megadeth | ラズパイクラスタのSlaveその1 |
| Raspberry Pi3 Model B | slayer | ラズパイクラスタのSlaveその2 |
| Raspberry Pi4(2GB) | anthrax | ラズパイクラスタのSlaveその3 |

Host名を変える際は、hostnamectlコマンドを使用します。hostnamectlコマンドだけでは、unknown hostエラーが出るため、/etc/hostsファイルも修正します。なお、/etc/hostsは、Host名とIPアドレスを対応させる役割を持つファイルです。

```
(注釈)：Host環境からRaspberry PiにSSH接続
# ssh pi@$(Raspberry PiのIPアドレス)

(注釈)：ここからの手順はRaspberry Pi上で実施
$ sudo hostnamectl set-hostname $(任意のHost名)
$ sudo vi /etc/hosts
```

```
(注釈) 以下の記述（ファイル末尾）を変更する。

※変更前
127.0.1.1     raspberrypi

※変更後
127.0.1.1     $(任意のHost名)

```

上記の手順を全てのRaspberry Piに実行したら、"$ sudo reboot"などで再起動します。

### Raspberry Piに新規ユーザを追加し、piユーザを削除

Raspberry Piのデフォルトユーザ（piユーザ）は、パスワードが知れ渡っているため、セキュリティリスクがあります。そのため、新規ユーザ（任意のユーザ名）を作成し、piユーザを削除します。

- [【セキュリティ対策】Raspberry Pi4に新規ユーザを追加し、piユーザを削除](https://debimate.jp/post/2020-09-01-%E3%82%BB%E3%82%AD%E3%83%A5%E3%83%AA%E3%83%86%E3%82%A3%E5%AF%BE%E7%AD%96raspberry-pi4%E3%81%AB%E6%96%B0%E8%A6%8F%E3%83%A6%E3%83%BC%E3%82%B6%E3%82%92%E8%BF%BD%E5%8A%A0%E3%81%97/)

### SSH接続設定（セキュリティ対策含む）

デフォルト設定では、Raspberry PiはSSHが無効化されています。

SSHを有効化するには、Raspberry Piの/bootディレクトリにsshファイル（空ファイル）を置くか、もしくは以下のコマンドをRaspberry Pi上で実行してください。

```
$ sudo raspi-config
※ Raspberry Pi Software Configuration Tooki(raspi-config)画面で、以下の順番で選択

[5 Interfacing Options]
 ⇓
[P2 SSH]
 ⇓
[SSHを有効化するかどうかの質問に対して"Yes"]
```

デフォルトのSSH接続設定は脆弱なので、以下の記事を参考にセキュリティ対策を実施してください。

- [Raspberry Pi3向けのセキュアSSH接続設定(公開鍵認証、rootアクセス禁止、ログインユーザ設定など)](https://debimate.jp/post/2019-03-26-%E7%92%B0%E5%A2%83%E6%A7%8B%E7%AF%89raspberry-pi3%E5%90%91%E3%81%91%E3%81%AE%E3%82%BB%E3%82%AD%E3%83%A5%E3%82%A2ssh%E6%8E%A5%E7%B6%9A%E8%A8%AD%E5%AE%9A%E5%85%AC%E9%96%8B%E9%8D%B5%E8%AA%8D/)

### Dockerのインストール

ここまでの手順を実施すれば、Kubernetesのインストールまであと一歩です。

DockerとDocker Composeをインストールしますので、別記事を参照してください。

- [Raspberry Pi3/4にDockerとdocker-composeをインストールする方法](https://debimate.jp/post/2020-09-27-raspberry-pi3-4%E3%81%ABdocker%E3%81%A8docker-compose%E3%82%92%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95/)

### Kubernetesのインストール

ここまでの手順で、Kubernetesインストールのための前準備が完了しました。以降の手順は、（ようやく）Kuberbetesの環境構築となります。

まずは、Kubernetes用パッケージマネージャであるHelmをインストールします。インストールスクリプトを利用した以下の手順は私の環境で失敗したので、後述するsnapパッケージマネージャを利用して入れました。

```
※ !!! 注意：以下の手順は失敗する可能性があるため、参考情報としてみてください !!!

※ Helmインストールスクリプトの取得
$  curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
$ ls
get_helm.sh

※ 実行権限の付与
$ chmod a+x get_helm.sh

※ インストールの実行
$ ./get_helm.sh 
Downloading https://get.helm.sh/helm-v3.3.0-linux-arm64.tar.gz
tar: linux-arm64/helm: Wrote only 3072 of 10240 bytes
tar: linux-arm64/LICENSE: Cannot write: No space left on device  ※ 容量は足りているが、本エラーが出る。
tar: Exiting with failure status due to previous errors
Failed to install helm
	For support, go to https://github.com/helm/helm.

```

snapパッケージマネージャを利用したHelmインストール手順は、以下の通りです。

```
$ sudo apt update
$ sudo apt install snapd
$ sudo reboot
$ sudo snap install helm --classic

```

次に、Kubernetesクラスタの構築に用いるkubeadmin（クラスタ起動コマンド）、KubernetesをCLIで操作するkubectl、Pod管理エージェントのkubelet（Podやコンテナを起動するコンポーネント）をインストールします（[公式サイトの手順もリンクしておきます](https://kubernetes.io/ja/docs/setup/production-environment/tools/kubeadm/install-kubeadm/)）。

インストール前にレガシー版のiptablesに関する設定を行います。2020年にRaspberry Pi OS（正確にはDebian10以降）は、iptablesは内部的にnftablesを使用しており、nftablesとkubeadminに互換性がない問題があります。この問題を回避するために、iptablesをレガシーモードで使用します。

```
(注釈) レガシーツールをインストールする
$ sudo apt install -y iptables arptables ebtables

(注釈) レガシー設定を有効化
$ sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
$ sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
$ sudo update-alternatives --set arptables /usr/sbin/arptables-legacy
$ sudo update-alternatives --set ebtables /usr/sbin/ebtables-legacy

```

kubeadmin、kubectl、kubeletをインストールします。また、これらのパッケージはapt-markコマンドを用いて、パッケージ更新対象外とします。

```
(注釈) 依存パッケージのインストール
$ sudo apt update
$ sudo apt install -y apt-transport-https curl

(注釈) kubernetesの公開鍵を追加
$ curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
$ cat <<EOF | sudo tee /etc/apt/sources.list.d/kubernetes.list
deb https://apt.kubernetes.io/ kubernetes-xenial main
EOF

(注釈) インストール処理および更新対象外設定
$ sudo apt-get update
$ sudo apt-get install -y kubelet kubeadm kubectl
$ sudo apt-mark hold kubelet kubeadm kubectl

```

### Masterノードの構築

CNI（コンテナネットワーキング）プラグインは、Flannelを使用します。

```
(注釈) Flannelの場合、10.244.0.0/16を指定する。
$ sudo kubeadm init --pod-network-cidr=10.244.0.0/16

```

kubeadm initを実行後、kubectlの設定方法が出力されるので、その内容を順に実行します。また、kubeadm joinに関する設定方法も出力されるので、そちらもメモしておきます（私はメモを無くしてしまいました…）。

```
(注釈) kubectlの設定
$ mkdir -p $HOME/.kube
$ sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
$ sudo chown $(id -u):$(id -g) $HOME/.kube/config

```

Pod Network Addonをインストールします。

```
$ kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/2140ac876ef134e0ed5af15c65e414cf26827915/Documentation/kube-flannel.yml

```

### Workerノードの構築

今回はWorkerノードが3台あるため、その3台に対して以下の手順を実行し、Workerノードをクラスタに参加させます。

入力するコマンドは、Masterノードkubeadm initコマンド実行後に表示されたkubeadm joinコマンドです。

```
(注釈) 環境によって入力するコマンドが異なる。
$ sudo kubeadm join 192.168.13.2:6443 --token vpmuze.ina6swjhlxh57lds --discovery-token-ca-cert-hash sha256:fcda1034ebb1374f0a0b487cd349b29ac1c253e83e6344b4d567cf61123a509c

```

全てのWorkerノードがクラスタに参加した後、"$ kubectl get nodes"で各ノードのステータスを確認できます。STATUS部分がREADY以外の場合は、上手く設定できていない可能性があります。

### 最後に

Kubernetesクラスタ環境構築は面倒くさい部類であり、一日近くの時間を要します。

さらに、特に動かしたいDockerコンテナアプリがない場合は、「ここから先、どうすればいいんだ？」と手が止まります。少なくとも私は、何も考えずに作ったクラスタの使い道に困っています。

ハード購入費用もそこそこするので、よく考えてから手を出しましょう（戒め）。
