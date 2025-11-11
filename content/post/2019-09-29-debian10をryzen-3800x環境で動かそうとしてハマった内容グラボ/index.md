---
title: "Debian10をRyzen 3800X環境で動かそうとしてハマった内容(グラボ必須、BIOS設定、Kernel設定)"
type: post
date: 2019-09-29
categories:
  - "linux"
  - "体験談"
tags:
  - "debian"
  - "ryzen"
  - "環境構築"
  - "自作pc"
cover:
  image: "images/PCリスト-min-1.jpeg"
  alt: "Debian10をRyzen 3800X環境で動かそうとしてハマった内容(グラボ必須、BIOS設定、Kernel設定)"
  hidden: false
---

### 前書き

増税前(2019年9月)に、自作PCパーツをドサッと買いました。

https://twitter.com/ARC\_AED/status/1177817660777582592

構成は、下表の通りです。評判の良い第三世代Ryzen CPUを中心に据えつつ、メモリ量を現状の32GBから64GBに増やし、ストレージも複数OSをインストール可能な環境を目指しました。

| **項目** | **単価** | **個数** | **金額（円）** | **製品名** |
| :-: | :-: | :-: | :-: | :-: |
| マザーボード | ￥17,707 | 1 | ￥17,707 | [ASUS AMD AM4 搭載 マザーボード PRIME X570-P/CSM](https://www.amazon.co.jp/gp/product/B07TWDPYLG/ref=as_li_ss_tl?ie=UTF8&psc=1&linkCode=ll1&tag=debimate07-22&linkId=00a0ac9127f36b742ce76ba12314f250&language=ja_JP) |
| CPU | ￥51,251 | 1 | ￥51,251 | [AMD Ryzen 7 3800X with Wraith Prism cooler 3.9GHz 8コア/16スレッド](https://www.amazon.co.jp/gp/product/B07SXMZLPJ/ref=as_li_ss_tl?ie=UTF8&psc=1&linkCode=ll1&tag=debimate07-22&linkId=88c2f14a47cd32eb1d26c4890203d5c3&language=ja_JP) |
| Memory(RAM) | ￥19,800 | 2 | ￥39,600 | [Team DDR4 3200Mhz(PC4-25600) 16GBx2枚(32GBkit)](https://www.amazon.co.jp/gp/product/B07QD9GKDV/ref=as_li_ss_tl?ie=UTF8&psc=1&linkCode=sl1&tag=debimate07-22&linkId=ea63d0ea83ff581e789547fed3173ed6&language=ja_JP) |
| SSD | ￥24,900 | 1 | ￥24,900 | [WD 内蔵SSD M.2-2280 2TB WDS200T2B0B-EC](https://www.amazon.co.jp/gp/product/B07SQXHQ6J/ref=ppx_od_dt_b_asin_title_s00?ie=UTF8&psc=1) |
| HDD | ￥8,590 | 2 | ￥17,180 | [WD HDD 3.5インチ 4TB WD40EZRZ/AFP2](https://www.amazon.co.jp/gp/product/B01MRSPHIW/ref=ppx_od_dt_b_asin_title_s00?ie=UTF8&psc=1) |
| グラボ | ￥18,560 | 1 | ￥18,560 | [MSI GeForce GTX 1650 AERO ITX 4G OC](https://www.amazon.co.jp/MSI-GeForce-GTX-1650-AERO/dp/B07QTWLVW3/ref=as_li_ss_tl?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&keywords=MSI+GeForce+GTX+1650+AERO+ITX+4G+OC&qid=1569736835&s=gateway&sr=8-1&linkCode=sl1&tag=debimate07-22&linkId=f9a81524ccee3b56637268a034fa10d0&language=ja_JP) |
| ケース | ￥8,152 | 1 | ￥8,152 | [ATX P110 silent](https://www.amazon.co.jp/gp/product/B0777851YQ/ref=as_li_ss_tl?ie=UTF8&psc=1&linkCode=sl1&tag=debimate07-22&linkId=2f48608d43aadda3c6e4bc8cd8f4b039&language=ja_JP) |
| 電源 | ￥13,980 | 1 | ￥13,980 | [SilverStone Strider Platinumシリーズ 550W 80PLUS](https://www.amazon.co.jp/gp/product/B015GR2NH4/ref=as_li_ss_tl?ie=UTF8&psc=1&linkCode=sl1&tag=debimate07-22&linkId=291ed06f2b4fa9269d82ae1bebe71d50&language=ja_JP) |
| **合計金額** |  |  | **￥191,330** |   |

CPUはRyzen 3900X(12コア/24スレッド)以上が魅力的でしたが、

- 3900Xが世界的な品切れ
- 3950X(16コア)やThreadripperは11月以降に発売延期
- ゲームしないため、そこまでコア数が不要

という状態だったので、3800Xを選択しました(実際は、同じ8コアの3700Xで十分だった)。

本記事では、上表のRyzen 3800X環境でDebian10を立ち上げるまでに、自作PC素人(２回目)の私がハマった内容とその解決策を示します。

### 既知の不具合：systemdのエラーで、ブート失敗

2019年7月に、HW乱数を返す命令RDRANDが常に(-1)を返す不具合があり、RDRANDを使用しているsystemdがエラーとなって、ブート失敗する事が判明しました([参考記事](https://linux.srad.jp/story/19/07/17/1633219/))。

Debian10は、この問題が見つかった時点で、運良く修正パッチが適用されています。しかし、systemdを使用する他のディストリビューションでは修正が反映されていない可能性もあるため、このバグに注意してください。

### 電源が入らない問題

説明書を読みながら各種パーツを取り付けた後、LEDは光るがCPUファンが回らない問題に遭遇しました。当然、画面には何も表示されませんでした。

https://twitter.com/ARC\_AED/status/1177867015270195202

この問題の**原因は、配線ミス**です。今回使用したマザーボードには、CPUへの電力供給を安定化させるため、電源コネクタを複数ヶ所に差し込めます。

- ATXメインコネクタ(マザーボード用)
- ATX12V(CPU用その１)
- EPS12V(CPU用その2)

ATXメインコネクタ用のケーブルは「メインコネクタ + ATX12V」の二箇所に挿せるようになっていたため、私はその両方に一本のケーブルで電源供給していました。しかし、正しくはメインコネクタだけに刺さなければいけませんでした。この挿し間違いにより、CPUへの電源供給が足りなかったようです。

この事に気づくまでの**原因切り分け方法は、「ケーブル・パーツを一つ抜いてから、電源ONを繰り返す事」**です。地味な方法ですが、一気に全パーツを外すよりも原因特定がしやすいです。ただし、マザーボード上のLEDがどこも点灯していない場合は、電源が駄目な場合もあるので、一気にパーツを外して良いです。

### BIOS画面が表示されない問題

電源が入り、ファンが回り始めて喜んだのもつかの間、モニターに何も表示されません。この際の原因切り分け方法は、マザーボードのビープ音です。マザーボードはエラー種類によって、異なるビープ音を鳴らしてくれます。エラー種類(ビープ方式)は、メーカによって差異があると思われるので、メーカHPで確認してください。

https://twitter.com/ARC\_AED/status/1177890905337913344

私の場合は、**「グラフィックボードの未検出」**が原因でした。Ryzenでは、CPU番号の末尾に"G"がついていない製品はグラフィック機能が無いです。私はその事実を知らなかったため、夜中にヨドバシカメラで以下のグラボを買ってきました。グラボを挿したらBIOS画面が出てきたので、恥ずかしい失敗でした。

<iframe style="width: 120px; height: 240px;" marginwidth="0" marginheight="0" scrolling="no" frameborder="0" src="//rcm-fe.amazon-adsystem.com/e/cm?lt1=_blank&amp;bc1=000000&amp;IS2=1&amp;bg1=FFFFFF&amp;fc1=000000&amp;lc1=0000FF&amp;t=debimate07-22&amp;language=ja_JP&amp;o=9&amp;p=8&amp;l=as4&amp;m=amazon&amp;f=ifr&amp;ref=as_ss_li_til&amp;asins=B07QTWLVW3&amp;linkId=b94ce10cb65682e99a9fb9c372376986"></iframe>

### kvm: disabled by biosエラーで停止

Debian10をUSBインストールした後、ブートシーケンス中に"kvm: diasbled by bios"エラーが出ました。KVMはKernel-based Virtual Machineの略で、仮想化技術の一つです。エラーメッセージ通り、BIOSの設定が必要でした。

BIOSの起動方法は、私の使用したマザーボードは"F2"か"Del"です。メーカによって、BIOS起動方法が異なるため、適宜調べてください。KVM有効化の設定手順は、以下の通りです。

1. BIOS起動：電源ON後にF2を連打
2. BIOS画面のAdvanced Mode(F7) > Tool > EZ Flash 3 Utilityを選択
3.  BIOS更新方法をInternet経由とし、各質問はYesでEnter
    - BIOS更新中は電源が落ちないように注意してください
4. BIOS更新後、American Megatrends画面が表示された後、F1を押下
5. BIOS画面で、Advanced > CPU Configuration > SVM = Enabledに変更
6. F10(Save & Exit)を押下

\[the\_ad id="598"\]

### sev command 0x4 timed out, disabling PSPエラーで停止

KVMエラー解消後、次に出たエラーはPSP無効化についてでした。PSPは、(AMD) Platform Security Processorの略で、セキュリティ関係のHW機能です。BIOSでは設定変更できないため、Kernelの再ビルドが必要でした。具体的には、kernelコンフィグ(.config)のCRYPTO\_DEV\_SP\_PSPオプションを無効化します。

以下に、Kernelの再ビルド・インストール手順を示します。なお、"Alt + Ctrl + F2"でtty2にログインできたため、Ryzen環境(root権限)で実施しています。

まずは、Linux Kernelをビルドできるように、パッケージを導入します。

```
# apt update
# apt upgrade
# apt install linux-headers-$(uname -r)     (注釈) unameコマンドにより、このコマンドを入力しているPCのKernelバージョン用ヘッダを取得
# apt install gawk wget git diffstat unzip texinfo gcc-multilib \
build-essential chrpath socat libsdl1.2-dev xterm libncurses5-dev \
lzop flex libelf-dev kmod libssl-dev
```

次に、Linux Kernelソースコードを取得します。

```
(注釈) Linux Kernelソースコードを取得
# uname -r       (注釈) Kernelバージョンの確認
4.19.67
# apt install linux-source-4.19  (注釈) linux-source-X.Xの"X.X"は、unameコマンドで確認したバージョンを記載

(注釈) 前手順で取得したソースコード(tarball)を展開
# mkdir ~/KERNEL
# cd ~/KERNEL
# tar xf /usr/src/linux-source-4.19.tar.xz
# ls
linux-source-4.19

```

今回の目的である「PSP無効化設定」および「Debian環境向けLinux Kernel(deb)」を作成するための設定をします。

```
(注釈) 現在使用しているLinux Kernelのコンフィグを取得
# cd linux-source-4.19/
# cp /boot/config-4.19.0-6-amd64 .config (注釈) /boot下に古いコンフィグが存在

(注釈) make oldconfigで新機能以外は既存設定と同じとし、新機能は無効に設定します。
　　　oldconfig中の選択肢は、全てEnterを押してください。
# make oldconfig

(注釈) PSP無効化(CRYPTO_DEV_SP_PSP = "n")とします。
　　　コンフィグのPATHは、menuconfig中の"/"(検索機能)で調べられます。
# make menuconfig

# vi .config
(注釈) CONFIG_SYSTEM_TRUSTED_KEY=""に変更。変更しないとビルド失敗します。

```

最後に、Linux Kernelビルド(debパッケージの生成)およびインストールします。dbg情報が付いているdebパッケージは削除し、残りのdebパッケージは全てインストールします。

```
(注釈) debパッケージを作成するため、ビルドを実施
# make -j16 bindeb-pkg

(注釈) 一つ上の階層にdebパッケージが存在するため、移動
# cd ../

(注釈) dbgという文字列を含むパッケージは、デバッグ情報付きの別バイナリなので不要。
# rm linux-image-4.19.67-dbg_4.19.67-1_amd64.deb

(注釈) ビルド生成物の確認
# ls
linux-4.19.67-falcot_4.19.67-1.diff.gz
linux-4.19.67-falcot_4.19.67-1.dsc
linux-4.19.67-falcot_4.19.67.orig.tar.gz
linux-4.19.67_4.19.67-1.diff.gz
linux-4.19.67_4.19.67-1.dsc
linux-4.19.67_4.19.67-1_amd64.buildinfo
linux-4.19.67_4.19.67-1_amd64.changes
linux-4.19.67_4.19.67.orig.tar.gz
linux-headers-4.19.67_4.19.67-1_amd64.deb
linux-image-4.19.67_4.19.67-1_amd64.deb
linux-libc-dev_4.19.67-1_amd64.deb
linux-source-4.19

(注釈) システムにインストール
# dpkg -i *.deb
# reboot　　　　 (注釈) OS再起動

```

### ログイン画面(GUI)が出てこない問題

Linux Kernelを入れ替えた後、ブートシーケンスは進むものの、ログもない黒い画面で最終的に停止する問題が発生しました。現象は、

- 画面が一度クリアされ、ログなしの黒い画面で停止
- tty2からdmesgでブートログを確認した結果、エラーなし
- Cinnamon/GNOME3デスクトップ環境を試し、変化なし

でした。

この問題を解決したのは、偶然です。調査中に、私はDebianがnon-free(企業が提供するプロプラエタなfirmware)がデフォルトで導入されない事を思い出し、結果的にログイン画面が出てこない原因がグラボのfirmwareと気づけました。

以下に、non-freeなfirmwareをインストールする手順を示します。使用するグラボ(AMD, NVIDIA)によって、使用するfirmwareが異なりますので、注意してください。本記事はNVIDIA向けの手順であり、[AMD向けは別サイトの記事](https://linuxconfig.org/how-to-install-the-latest-amd-drivers-on-debian-10-buster)を参考情報として置いておきます。

まずは、/etc/apt/sources.listを更新し、aptコマンドでnon-freeなバイナリを取得できるようにします。具体的には、debもしくはdeb-srcから始まる文の末尾に"non-free"を追加します。

```
# 注釈：debおよびdeb-srcの末尾に、"non-free"を追加
deb http://deb.debian.org/debian/ buster main contrib non-free
deb-src http://deb.debian.org/debian/ buster main contrib non-free

deb http://security.debian.org/debian-security buster/updates main contrib non-free
deb-src http://security.debian.org/debian-security buster/updates main contrib non-free

# buster-updates, previously known as 'volatile'
deb http://deb.debian.org/debian/ buster-updates main contrib non-free
deb-src http://deb.debian.org/debian/ buster-updates main contrib non-free

```

最後に、NVIDIAのグラボ向けのfirmwareを取得します。NVIDIAのfirmwareは複数種類ありますが、今回はその中から必要なfirmwareを探してくれる"nvidia-detect"コマンドを使用しました。

```
(注釈) /etc/apt/sources.listを更新したため、パッケージ情報を再取得
# apt update

(注釈) nvidia-detectコマンドを用いて、
　　　 NVIDIAのfirmwareの中で、どのfirmwareが必要かを調査
# apt install nvidia-detect

# nvidia-detect
Detected NVIDIA GPUs:
07:00.0 VGA compatible controller [0300]: NVIDIA Corporation TU107 [10de:1f82] (rev a1)

Checking card:  NVIDIA Corporation TU107 (rev a1)
Your card is supported by the default drivers.
It is recommended to install the
    nvidia-driver         (注釈) ★ インストールすべきfirmware
package.

(注釈) firmwareのインストール
# apt install nvidia-driver 

```

### 最後に

**以上の手順で、Ryzen 3800X環境でDebian10が動作しました！**

新規Hardware(今回はRyzen 3800X)をDebianで試すのは、難易度が高いと感じました。今回のPC組み立てで発生した問題もあまり情報が出てこず、組み立て完了までにトータルで12時間程度かかりました。

Linuxに詳しくない人はユーザ絶対数の多いUbuntuで試すか、まずはWindows10を導入してみた方が作業が楽に進む筈です。Debianはマイナー。
