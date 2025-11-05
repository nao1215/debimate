---
title: "mmdebstrapによるarmhf向けrootfsの作成方法(公式最小サイズ27MB)"
type: post
date: 2019-03-10
categories:
  - "linux"
tags:
  - "debian"
  - "linux"
  - "開発環境"
cover:
  image: images/debian-1277387_960_720.png
  alt: "mmdebstrapによるarmhf向けrootfsの作成方法(公式最小サイズ27MB)"
  hidden: false
images: ["images/debian-1277387_960_720.png"]
---

## mmdebstrapとは

[mmdebstrap](https://gitlab.mister-muffin.de/josch/mmdebstrap)とは、最小構成rootfsを作成するための[debootstrap](https://manpages.debian.org/stretch/debootstrap/debootstrap.8.en.html)を代替するコマンドです。debootstrapと同様に、[Debianサポートアーキテクチャ](https://www.debian.org/ports/index.ja.html)向けのrootfsを作成できます。mm(Multi-Mirror)が意味するように、複数のミラーサーバを使用する事により、debootstrapより3〜6倍ほど高速に動作します。

2019年3月現在(Debian9, stretch環境)では、mmdebstrapはtesting/unstableに存在します。stableに存在しないmmdebstrapを知ったキッカケは、debian-embeddedのメーリスです。128MB以下のrootfsを作成する方法がメーリス内で質問され、mmdebstrapの開発者(Johannes Schauer)がその方法の一つとして紹介していました。質問自体は、最終的にmmdebstrapが作成するrootfsのサイズがネックになり、他の方法([Yocto](https://www.yoctoproject.org/))が採用されていました。

mmdebstrapは開発中ですが、組み込み分野で使用される可能性もあります。そのため、本記事ではmmdebstrapの基本的な特徴を押さえた後、stretch環境への導入方法、rootfsの作成方法を記載します。

## mmdebstrapの良い点

以下の内容は、[公式レポジトリのREADME](https://gitlab.mister-muffin.de/josch/mmdebstrap)を日本語訳し、意味が通るように補足・意訳しています。比較対象は、debootstrapです。

良い点

- 複数のミラーサーバが使用可能(debootstrapは、単一ミラーを使用)
- ミラーサーバがDebian stableとしてセキュリティ更新される点
- debootstrapより、3〜6倍高速
- 必須パッケージおよびaptコマンドを含むrootfsが11秒で作成可能
- [aptコマンド](https://manpages.debian.org/stretch/apt/apt.8.ja.html)を含むrootfs(.tar.gz)が**27MB以下**
- [namespace](https://linuxjm.osdn.jp/html/LDP_man-pages/man7/namespaces.7.html)、[fakechroot](https://linux.die.net/man/1/fakechroot)、[proot](https://github.com/proot-me/PRoot/blob/master/doc/proot/manual.txt)を用いた非管理者権限での動作が可能
- [nodev(特殊デバイス)](https://www.atmarkit.co.jp/ait/articles/1802/15/news035.html)としてマウントされたFilesystem上で操作可能
- mmdebstrapとアーキテクチャが異なる場合は、qemuを用いてrootfsを作成

開発者は、「rootfsはDebian stableのセキュリティ更新に追従しなければいけない」と考えていたようです。debootstrapは2009年時点からこの問題([＃543819](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=543819)、[＃762222](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=762222))を解決できていませんでした。一方で、mmdebstrapはaptコマンドを用いる事によって、このセキュリティ問題を対策しました。ちなみに、debootstrapはwgetコマンドによってrootfsを作成しています。

aptコマンドを使用した恩恵として、debootstrapより3〜6倍高速になりました。下表は、 開発者がIntel Core i5-5200U(ノートPC)で検証した結果(速度比較)です。

| **variant** | **mmdebstrap** | **debootstrap** |
| --- | --- | --- |
|   minbase   ([必須・推奨](https://wiki.debian.org/DependencyHell)・aptパッケージから構成されたrootfs)   | 14.18 s | 51.47 s |
|   buildddpkgopt   (minbaseに[build-essential](https://packages.debian.org/ja/stretch/build-essential)を含めたrootfs)   | 20.55 s | 59.38 s |
| \- (minbaseに重要なパッケージを含めたrootfs。   debootstrapのデフォルト構成) | 18.98 s | 127.18 s |

## mmdebstrapの書式・オプション

```
書式
mmdebstrap [OPTION...] [SUITE [TARGET [MIRROR...]]]
OPTION：後述
SUITE ：Debianのリリースコードネーム、Version(例：stretch、testing)
TARGET：rootfs作成先ディレクトリ名、もしくはrootfs圧縮ファイル名
MIRROR：ミラーサーバ(デフォルト：http://deb.debian.org/debian)
```

rootfs(TARGET)形式は、非圧縮(ディレクトリ)、tar(アーカイブ)、gzip(gz)、compress(Z)、bzip2、lzip(lz)、lzma(lzma)、lzop(lzo)、lz4、xz、zstd(zst)です。

| **Option** | **説明** |
| --- | --- |
| help | ヘルプを表示。 |
| variant | rootfsにインストール対象のパッケージを指定。パッケージ名を直接指定せず、extract, custom, essential, apt, required(デフォルト), minbase, buildd, important, debootstrap, -, standardから選択します。詳細は後述。 |
| mode | rootfs作成時の権限をauto(デフォルト), [sudo](https://linuxjm.osdn.jp/html/sudo/man8/sudo.8.html), root, [unshare](https://www.commandlinux.com/man-page/man1/unshare.1.html), [fakeroot](https://wiki.debian.org/FakeRoot), [fakechroot](https://linux.die.net/man/1/fakechroot)、[proot](https://github.com/proot-me/PRoot/blob/master/doc/proot/manual.txt)から選択します。 |
| aptopt | rootfs作成時に、aptコマンドへ渡すオプションを指定します。   指定オプションはrootfs内"/etc/apt/apt.conf.d/99mmdebstrap"に記載されます。 |
| dpkgopt | rootfs作成時に、dpkgコマンドへ渡すオプションを指定します。   指定オプションはrootfs内"/etc/dpkg/dpkg.cfg.d/99mmdebstrap"に記載されます。 |
| include | rootfsに追加したいパッケージをカンマ区切りで記載します。   variantsがextract/custom以外は、依存関係を解決します。 |
| components | [Debianフリーソフトウェアガイドライン](https://www.debian.org/distrib/packages.ja.html)に従って、rootfsに導入するパッケージを制限します。main, contrib, non-freeのいずれかをカンマ区切りで記載します。 |
| architectures | rootfsのアーキテクチャをカンマ区切りで指定します。amd64, arm64, armel, armhf, i386, mips, mips64el, mipsel, ppc64el, s390xの中から選択します。   なお、powerpcは、stretchよりサポート対象外です。 |

| **Variants** | **説明** |
| --- | --- |
| extract | デフォルトでは何もinstallしません("Essential:yes"パッケージも同様)。 |
| custom | "include"オプションで指定されたパッケージのみinstallします。 |
| essential | "Essential:yes"パッケージをinstallします。 |
| apt | essentialにaptコマンドを加えて、installします。 |
| required, minbase | essentialに"Priority:required"パッケージとaptコマンドを加えて、installします。 |
| buildd | minbaseに[build-essential](https://packages.debian.org/ja/stretch/build-essential)を加えて、installします。 |
| important, debootstrap, - | requiredに"Priority:important"パッケージを加えて、installします。 |
| standard | "Priority:standard"パッケージを全てinstallします。 |

## mmdebstrapのinstall方法

今回使用した環境は、以下の通りです。

```
$ neofetch
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 9.8 (stretch) x86_64 
 ,$$P'              `$$$.     Kernel: 4.9.0-8-amd64 
',$$P       ,ggs.     `$$b:   Uptime: 17 hours, 39 minutes 
`d$$'     ,$P"'   .    $$$    Packages: 2675 
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
              `"""            Memory: 4093MB / 32069MB 

```

mmdebstrapは、Debian9(stretch)に提供されていません。そのため、以下の記事を参考にtesting/unstableパッケージをinstallできるようにしてください。

https://debimate.jp/2019/03/09/debian-%E4%BB%BB%E6%84%8F%E3%81%AEtesting-unstable%E3%83%91%E3%83%83%E3%82%B1%E3%83%BC%E3%82%B8%E3%81%AE%E3%81%BF%E3%82%92install%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95%E3%82%B7%E3%82%B9%E3%83%86/

上記の記事内容を実施後、以下のaptコマンドを実行してください。testingミラーサーバからinstallするパッケージはmmdebstrapのみで、他のパッケージはstretchミラーサーバから取得します。また、[mmdebstrap推奨パッケージ(≒依存パッケージ)](https://packages.debian.org/buster/mmdebstrap)は、明示的に指定しないとinstallされません。そのため、以下の手順ではarch-test(推奨パッケージ)などを列挙して記載しています。installしなかった場合、HOST(native)環境向けrootfsしか作成できません。

```
$ sudo apt install mmdebstrap/testing arch-test fakechroot fakeroot mount \
uidmap binfmt-support dpkg-dev proot  qemu-user qemu-user-static

```

## mmdebstrapの実行例

まず、Host環境(amd64)向けrootfs作成の成功例・失敗例を示した後、Target環境について説明します。

HOST環境向けは、「管理者権限を付けてtesting/unstableを指定した場合」および「管理者権限を付けない方法(proot、fakechroot、fakeroot、unshare)」が失敗しました。つまり、Host環境向けは、管理者権限を付けてstable rootfsを作成するケースしか成功しません。失敗例は全てのログを示すと数が多いため、prootを指定した場合のみを例示します。

**HOST環境向けrootfs作成の成功例(sudo権限、testingを指定)**

```
$ sudo mmdebstrap stable host-stable-success
I: automatically chosen mode: root
I: chroot architecture amd64 is equal to the host's architecture
I: running apt-get update...
done
I: downloading packages with apt...
done
I: extracting archives...
done
I: installing packages...
done
I: downloading apt...
done
I: installing apt...
done
I: installing remaining packages inside the chroot...
done
I: cleaning package lists and apt cache...
done
done

$ sudo du -sh host-stable-success
185M	host-stable-success/
$ sudo chroot host-stable-success　(注釈)：chrootし、動作検証を実施

# pwd
/

# ls
bin   dev  home  lib32	libx32	mnt  proc  run	 srv  tmp  var
boot  etc  lib	 lib64	media	opt  root  sbin  sys  usr

# apt update
# apt install figlet
# figlet test
 _            _   
| |_ ___  ___| |_ 
| __/ _ \/ __| __|
| ||  __/\__ \ |_ 
 \__\___||___/\__|
```

**HOST環境向けrootfs作成の失敗例(proot、stableを指定)**

```
$ mmdebstrap --mode=proot stable host-stable
I: chroot architecture amd64 is equal to the host's architecture
I: running apt-get update...
done
I: downloading packages with apt...
done
I: extracting archives...
done
I: installing packages...
done
I: downloading apt...
done
I: installing apt...
done
mount: only root can use "--options" option
mount failed: 256 at /usr/bin/mmdebstrap line 1201.

$ du -sh host-stable　(注釈)：完全に失敗したわけではないため、rootfs自体はあります
189M	host-stable

$ sudo chroot host-stable　(注釈)：chrootで、作成したrootfs内でコマンド検証
# pwd
/

# ls
bin   dev  home  lib32	libx32	mnt  proc  run	 srv  tmp  var
boot  etc  lib	 lib64	media	opt  root  sbin  sys  usr

# apt update　　(注釈)：aptコマンドの実行により、動作停止。
0% [Waiting for headers] [Waiting for headers]

```

Target環境(armhf)の成功例では、不要なファイル(man, locale, doc)を削除し、rootfsサイズを小さくしたケース(35MB)を示します。Target環境はHOST環境向けと逆で、管理者権限を付けると失敗するため、失敗例はその例を示します。

**Target環境向けrootfs作成の成功例(proot、unstableを指定)**

```
$ mmdebstrap --variant=essential \
     --dpkgopt='path-exclude=/usr/share/man/*' \
     --dpkgopt='path-exclude=/usr/share/locale/*' \
     --dpkgopt='path-exclude=/usr/share/doc/*' \
      --architecture=armhf unstable > rpi-unstable-exclude.tar.gz
I: automatically chosen mode: proot
I: armhf cannot be executed, falling back to qemu-user
I: running apt-get update...
done
I: downloading packages with apt...
done
I: extracting archives...
done
qemu: Unsupported syscall: 382
I: installing packages...
done
I: re-installing packages because of path-exclude...
done
I: cleaning package lists and apt cache...
done
done
I: creating tarball...
done

$ du -sh rpi-unstable-exclude.tar.gz 
35M	rpi-unstable-exclude.tar.gz

(Target環境向けrootfsの動作結果は、後述)
```

**Target環境向けのrootfs作成の失敗例(sudo権限、stable指定)**

```
$ sudo mmdebstrap --architecture=armhf stable > rpi-stable.tar.gz
I: automatically chosen mode: root
I: armhf cannot be executed, falling back to qemu-user
I: running apt-get update...
done
I: downloading packages with apt...
done
I: extracting archives...
done
I: installing packages...
done
/usr/sbin/chroot: failed to run command ‘dpkg’: Permission denied
env --unset=APT_CONFIG /usr/sbin/chroot /tmp/PadtB2OVfO dpkg --install --force-depends failed at /usr/bin/mmdebstrap line 501.

$ du -sh rpi-stable.tar.gz 　(注釈)：rootfsの中身が空っぽ
0	rpi-stable.tar.gz

```

\[the\_ad id="598"\]

## Raspberry Pi3環境でのrootfs動作確認

上記の手順で作成したTarget環境向けrootfsをRaspberry Pi3にコピーし、動作確認します。

```
(注釈)：Raspberry Pi3は起動済みで、SSHは鍵認証形式。
$ scp rpi-unstable-exclude.tar.gz nao@rpi:/home/nao
rpi-unstable-exclude.tar.gz                 100%   34MB   1.6MB/s   00:20    

$ ssh rpi　(注釈)：Raspberry Pi環境にログイン
Linux nao 4.14.79-v7+ #1159 SMP Sun Nov 4 17:50:20 GMT 2018 armv7l

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
Last login: Sat Mar  9 21:28:28 2019 from 192.168.10.110

$ ls　(注釈)：rootfs(tarball)の存在確認
rpi-unstable-exclude.tar.gz  ダウンロード  テンプレート  デスクトップ
ドキュメント  ビデオ  音楽  画像  公開

$ mkdir chroot
$ cd chroot/
$ sudo tar xf ../rpi-unstable-exclude.tar.gz 　(注釈)：rootfsを/home/nao/chroot下に展開

$ sudo chroot /home/nao/chroot　(注釈)：rootfs環境にchroot
bash: warning: setlocale: LC_ALL: cannot change locale (ja_JP.UTF-8)
# pwd
/
# ls
bin  boot  dev	etc  home  lib	lib32  lib64  libx32  media  mnt
opt  proc  root  run sbin  srv  sys tmp  usr  var
# echo Hello World
Hello World

# apt update　(注釈)：essentialにaptコマンドは含まれないため、実行不可
bash: apt: command not found
# find . -name "*.[1-9].gz"
(manページがないため、何も表示されない)
# find . -name "*.mo"
(localeファイルがないため、何も表示されない)
# ls /usr/share/doc
(documentがないため、何も表示されない)

```

## おまけ: 最小rootfs作成に挑戦……敗北

私が作成したTarget環境(armhf)向けのrootfsは、35MBです。このサイズは、組み込み環境としては大きいです。rootfsサイズは、起動速度にも関わるため、より小さいサイズのrootfsを試みました。結果は駄目でしたが、考え方と実行結果ログを残しておきます。

最小rootfs作成の挑戦結果(まとめ)

- variantオプションがcustomの場合、最小rootfsが作成できそう(予想)
- custom選択時は、includeオプションで指定パッケージは依存解決されない(仕様)
- busyboxベースのrootfs環境は、エラーを読む限り作成が許されていない(予想)
- rootfsに不要なファイルは、man、doc、locale、aptコマンドのゴミ(事実)

前提として、以下の通り、busyboxベース(busybox + ログインシステム)はエラーが発生して作成できません。

```
$ mmdebstrap --variant=custom \
>      --dpkgopt='path-exclude=/usr/share/man/*' \
>      --dpkgopt='path-exclude=/usr/share/locale/*' \
>      --dpkgopt='path-exclude=/usr/share/doc/*' \
>      --dpkgopt='path-exclude=/var/lib/apt/lists/*debian*' \
>      --dpkgopt='path-exclude=/var/cache/apt/*.bin' \
>      --include=busybox,login,passwd,uidmap,base-files \
>      --architecture=armhf stable > rpi-stable-min.tar.gz
I: automatically chosen mode: proot
I: armhf cannot be executed, falling back to qemu-user
I: running apt-get update...
done
I: downloading packages with apt...
done
I: extracting archives...
done
I: installing packages...
done
dpkg: warning: 'sh' not found in PATH or not executable
dpkg: warning: 'rm' not found in PATH or not executable
dpkg: warning: 'diff' not found in PATH or not executable
dpkg: warning: 'ldconfig' not found in PATH or not executable
dpkg: error: 4 expected programs not found in PATH or not executable
Note: root's PATH should usually contain /usr/local/sbin, /usr/sbin and /sbin
env --unset=APT_CONFIG proot --root-id --bind=/dev --rootfs=/tmp/ZHyl0fOB8r --cwd=/ --qemu=qemu-arm dpkg --install --force-depends failed at /usr/bin/mmdebstrap line 501.

```

上記のエラーを考慮した場合、bash(dash、fishも可能)、coreutils、diffutils、libc-binが最低限必要な事が分かります。さらに、基本的なログインシステムを提供するには、[login](https://packages.debian.org/ja/stretch/login), [passwd](https://packages.debian.org/ja/stretch/passwd), [uidmap](https://packages.debian.org/ja/stretch/uidmap), [base-files](https://packages.debian.org/ja/stretch/linux-base)も導入しなければいけません。極めつけとして、variantオプションがcustomの場合は、依存関係を自動的に解決しないため、依存解決用パッケージをincludeオプションに渡さなければなりません。依存関係を手動で列挙する事は苦痛なため、これ以上の挑戦を止めました。

最後に、パッケージをinstallした後に、除外するファイルについてです。「mmdebstrapの実行例」と同じく、man、locale、docが削除できます。さらに、aptコマンド実行後のゴミも削除できます。これらの削除対象ファイルに関しては、[2015年のELBE(Embedded Linux Build Enviroment)](https://elbe-rfs.org/images/20150322-clt-elbe.pdf)で言及されています。
