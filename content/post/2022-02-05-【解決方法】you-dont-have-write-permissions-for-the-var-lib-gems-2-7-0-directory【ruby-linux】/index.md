---
title: "【解決方法】You don't have write permissions for the /var/lib/gems/2.7.0 directory【Ruby, Linux】"
type: post
date: 2022-02-05
categories:
  - "linux"
tags:
  - "linux"
  - "ruby"
  - "ubuntu"
  - "エラー解決"
cover:
  image: images/diamond-g26c8044a7_640.jpg
  alt: "【解決方法】You don't have write permissions for the /var/lib/gems/2.7.0 directory【Ruby, Linux】"
  hidden: false
---

## 前書き：gem installでコケる

原因は単なる権限の問題。Ruby初心者なので自分用にメモします。

まずは、前提情報です。Ubuntu 21.10、Ruby 2.7.4\[x86\_64-linux-gnu\]で、[femパッケージ（パッケージ作成ツール）](https://github.com/jordansissel/fpm#things-that-should-work)のインストールを試みました。結果は、/var/lib/gems以下のパーミッションエラー。

```
$ gem install fpm
（省略）
ERROR:  While executing gem ... (Gem::FilePermissionError)
    You don't have write permissions for the /var/lib/gems/2.7.0 directory.
```

/var/lib/gemsは、Rubyのgem（rubyパッケージ）が格納されるディレクトリです。/var/lib以下は、基本的にはrootユーザ／rootグループの所有物で、かつ一般ユーザーが書き込みできない権限設定になっています。

短絡的に「"$ sudo chmod -R a+w /var/lib/gems"、ﾀｰﾝｯ!!  権限変更ヨシ！」とするのは乱暴です。乱暴な事をして/var/lib/gemsの権限を変えても、次は「/usr/local/binの権限がないよ（You don't have write permissions for the /usr/local/bin directory.）」と怒られます。

そこで本記事では、gemインストール時の権限エラー解決方法を2通り紹介します。

## 検証環境

```
           ./oydmMMMMMMmdyo/.              nao@nao 
        :smMMMMMMMMMMMhs+:++yhs:           ------- 
     `omMMMMMMMMMMMN+`        `odo`        OS: Ubuntu Budgie 21.10 x86_64 
    /NMMMMMMMMMMMMN- `sN/       Host: B450 I AORUS PRO WIFI 
  `hMMMMmhhmMMMMMMh               sMh`     Kernel: 5.13.0-28-generic 
 .mMmo- /yMMMMm`              `MMm.    Uptime: 57 mins 
 mN/       yMMMMMMMd- MMMm    Packages: 3492 (dpkg), 16 (snap) 
oN- oMMMMMMMMMms+//+o+:    :MMMMo   Shell: bash 5.1.8 
m/          +NMMMMMMMMMMMMMMMMm. :NMMMMm   Resolution: 1920x1080, 2560x1080 
M`           .NMMMMMMMMMMMMMMMNodMMMMMMM   DE: Budgie 10.5.3 
M- sMMMMMMMMMMMMMMMMMMMMMMMMM   WM: Mutter(Budgie) 
mm`           mMMMMMMMMMNdhhdNMMMMMMMMMm   Theme: Yaru-dark [GTK2/3] 
oMm/        .dMMMMMMMMh:      :dMMMMMMMo   Icons: ubuntu-mono-dark [GTK2/3] 
 mMMNyo/:/sdMMMMMMMMM+          sMMMMMm    Terminal: tilix 
 .mMMMMMMMMMMMMMMMMMs           `NMMMm.    CPU: AMD Ryzen 5 3400G (8) @ 3.700GH 
  `hMMMMMMMMMMM.oo+.            `MMMh`     GPU: AMD ATI 09:00.0 Picasso 
    /NMMMMMMMMMo                sMN/       Memory: 3471MiB / 30032MiB 
     `omMMMMMMMMy.            :dmo`
        :smMMMMMMMh+-`   `.:ohs:                                   
           ./oydmMMMMMMdhyo/.                                      

```

## 解決方法その１：環境変数GEM\_HOMEを変更

複数バージョンのRubyを使用しない人にとっては、この解決方法が簡単です。

環境変数GEM\_HOMEは、gemインストール先を意味します。一般ユーザーの書き込み権限がある場所にGEM\_HOMEを変更すれば、表題のエラーが解決します。

```
（注釈）gemのインストール先を作成。
$ mkdir ~/.ruby                                     

（注釈）GEM_HOMEを変更し、PATH解決できるように変更
$ echo 'export GEM_HOME=~/.ruby/' >> ~/.bashrc
$ echo 'export PATH="$PATH:~/.ruby/bin"' >> ~/.bashrc

（注釈）変更した設定の読み込み。
$ source ~/.bashrc    　　　　　　　　　　　　　
```

## 解決方法その2：rbenvを使用

Rubyのバージョンをコントロールしたい人向けの解決策です。

rbenvは、複数バージョンのrubyを共存できるようにするツールであり、一般ユーザーに権限があるディレクトリを操作します。そのため、rbenvを使用すると、自動的に権限問題が解消されます。

rbenvを用いた解決策の流れとしては、

1. システムからrubyをアンインストール
2. rbenv（+ rubyのビルド）に必要なパッケージをインストール
3. rbenvとruby-buildをインストール
4. rbenvのPATHを通すため、環境変数の設定
5. ruby（gem）インストール

を行います。上記の内容を順番に説明します。

まず、システムからrubyをアンインストールします。

```
$ sudo apt remove ruby
```

rbenv（+ rubyのビルド）に必要なパッケージをインストールします。

```
$ sudo apt update
$ sudo apt install git curl libssl-dev libreadline-dev zlib1g-dev autoconf bison build-essential libyaml-dev libreadline-dev libncurses5-dev libffi-dev libgdbm-dev
```

rbenvとruby-buildをインストールします。

```
$ curl -sL https://github.com/rbenv/rbenv-installer/raw/main/bin/rbenv-installer | bash -
```

rbenvのPATHを通すため、環境変数の設定をします。

```
$ echo 'export PATH="$HOME/.rbenv/bin:$PATH"' >> ~/.bashrc
$ echo 'eval "$(rbenv init -)"' >> ~/.bashrc
$ source ~/.bashrc
```

Ruby（gem付き）をインストールします。"rbenv install -l"でrubyのバージョン一覧が確認できるので、任意のバージョンを選択してください。

```
$ rbenv install -l
2.6.9
2.7.5
3.0.3
3.1.0        (注釈) 今回はこのバージョンをインストールします
jruby-9.3.3.0
mruby-3.0.0
rbx-5.0
truffleruby-22.0.0.2
truffleruby+graalvm-22.0.0.2

$ rbenv install 3.1.0　　　　　（注釈）実行時間が長いので注意

(注釈) システムで使うRubyバージョンを指定
$ rbenv global 3.1.0

```

最後の"rbenv global $(任意のバージョン)"を実行しないと、システムで使用するRubyが未確定の状態となります。この状態でgemを実行すると、"rbenv: gem: command not found"となるので、注意してください。

## 最後に

Ruby界隈の人ではないので、rbenvでバージョンコントロールするのは大変そうだなという他人事な感想を持ちました。慣れると楽なんでしょうか。Python界隈も同じ問題があり、大変そう。
