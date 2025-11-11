---
title: "環境構築：ユーザフレンドリーで補完機能の強力なfishへ移行(Login shellをbashからfishへ移行)"
type: post
date: 2019-06-15
categories:
  - "linux"
tags:
  - "dash"
  - "debian"
  - "fish"
  - "linux"
  - "shell"
  - "環境構築"
cover:
  image: "images/fish.png"
  alt: "環境構築：ユーザフレンドリーで補完機能の強力なfishへ移行(Login shellをbashからfishへ移行)"
  hidden: false
---

### 前書き

本記事では、CLI(Terminal)で用いるinteractive shellを**[fish(friendly interactive shell)](https://fishshell.com/)**に移行する方法を記載します。fishは、Debian環境のdefault shellである**dash(POSIX互換のash拡張)**やlogin shellである**bash**よりも優れた点が多いです。

fishの優れた点

- 強力なサジェスト(予測変換)・補完機能
- Tabキーを押すと、入力中コマンドの機能説明を表示(下画像)
- Terminalのカラースキーム設定が容易
- Webインターフェースでも設定変更が可能
- パッケージマネージャ(fisher)で機能拡張が可能
- デフォルト設定で使いやすい

![](images/terminal_fish-1.png)

上表で示した内容以外にも、他の高機能shell(zshなど)よりも学習コストが低い、Vimのkey bindingが使用可能など、細かい点で利点があります。ただし、唯一のデメリットとして、「fishはPOSIX互換でない事(Default shellに向かない事)」が挙げられます。

本記事では、POSIX非互換というデメリットに配慮しつつ、Login shellをbashからfishへ移行する手順を示します。

### 検証環境

Debian9(stretch)環境を使用します。Default shellはdash、Login shellはbashという環境です。

```
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 9.9 (stretch) x86_64 
 ,$$P'              `$$$.     Kernel: 4.9.0-9-amd64 
',$$P       ,ggs.     `$$b:   Uptime: 1 day, 5 hours, 31 minutes 
`d$$'     ,$P"'   .    $$$    Packages: 2284 
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
              `"""            Memory: 5106MB / 32069MB 

```

```
(注釈)：Default shellの確認。dashへのシンボリックリンク。
$ ls -al /bin/sh
lrwxrwxrwx 1 root root 4  1月 24  2017 /bin/sh -> dash

(注釈)：Login shellの確認。一番右側にLogin shellであるbashが記載されています。
$ grep $USER /etc/passwd
nao:x:1000:1000:CHIKAMATSU Naohiro,,,:/home/nao:/bin/bash

```

### fishとfisherのインストール

まずは、fish(shell)とfisher(fishプラグインマネージャ)をインストールします。Debian9(stretch)以降であれば、aptでfishを取得可能です。fisherは、[公式サイトのインストール手順](https://github.com/jorgebucaran/fisher)で取得します。

```
$ sudo apt install fish
$ curl https://git.io/fisher --create-dirs -sLo ~/.config/fish/functions/fisher.fish

```

### Login shellのみをfishに変更

「前書き」で記載したとおり、fishはPOSIX互換性がありません。そのため、Default shell をfishに変更した場合(/bin/shのシンボリックリンクが/usr/bin/fishの状態)、POSIX互換を前提としたshell scriptを読み込めず、何らかの動作異常を起こす可能性があります。

以上を踏まえると、「Default shellはdashのまま」とし、「Login shellのみをfish」に変更します。なお、.bashrcに"exec fish"を記載し、Login shellはbashのままfishを起動する方法があります。しかし、この方法ではexportした環境変数設定が弾き継がれません。そのため、Login shell自体をfishに変更する方法を採用しました。

fishは、.bashrc(bash用の設定ファイル)に記載された設定を読み込みません。そのため、.bashrcに記載されている設定を"~/.config/fish/config.fish"に移行します。この際、.bashrcとconfig.fishで環境変数設定(export)の書式が異なるため、注意が必要です。

まずは、Login Shellをbashからfishに変更します。

```
(注釈)：Login shellとして使用できるshell一覧にfishがある事を確認
$ cat /etc/shells
# /etc/shells: valid login shells
/bin/sh
/bin/dash
/bin/bash
/bin/rbash
/usr/bin/fish     # ★

(注釈)：Login shellをfishに変更。
$ chsh --shell /usr/bin/fish

```

次に、.bashrcに記載したexportやalias設定を"~/.config/fish/config.fish"に移行します。特に、自分で設定していない場合は、以下の手順は不要です。

```
(注釈)：私の環境で、.bashrcに記載した設定は、以下の4行
$ cat ~/.bashrc | tail -n 4
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64/bin/javac
export PATH=~/bin:$PATH
alias vi="/usr/local/bin/nvim"
source $HOME/.cargo/env

```

```
$ touch ~/.config/fish/config.fish
$ vi ~/.config/fish/config.fish    (注釈)：好きなエディタを使用して良い

(注釈)：設定内容は以下の通り。

```

```
# 環境変数(書式：set -x PATH hoge. リスト形式 not コロン区切り)
set -x JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64/bin/javac
set -x PATH ~/bin $PATH

# エイリアス
alias vi='/usr/local/bin/nvim'

# 別ファイル設定読み込み
source $HOME/.cargo/env

```

### お前を消す方法：Welcome to fish, the friendly interactive shell

上記の手順の後にTerminalを再起動すると分かりますが、fish起動後に

```
Welcome to fish, the friendly interactive shell
nao@debian ~> 

```

と、毎回Welcomeメッセージが出ます。そのため、"~/.config/fish/config.fish"に"set fish\_greeting"を追記し、メッセージの出力を抑制します。

```
# fish起動時のWelcome~メッセージを表示しない
set fish_greeting

```

\[the\_ad id="598"\]

### Terminalのカラースキームを変更

FishはTerminalのカラースキームが複数用意されています。最も簡単にカラースキームを設定する方法は、後述するWebブラウザを用いる方法です。

この節では、[oh-my-fish(GitHub、サンプル画像つき)](https://github.com/oh-my-fish/oh-my-fish/blob/master/docs/Themes.md)とfisherを用いて、自分好みのカラースキームを設定する方法を示します。

```
(注釈)：引数を"oh-my-fish/theme-(好きなカラーテーマ名)"に置換する事
$ fisher add oh-my-fish/theme-bobthefish

(注釈)：bobthefishは依存しているfontがあるため、別途インストール
$ sudo apt install python3-pip
$ sudo pip3 install powerline-status
$ sudo apt install fonts-powerline

```

今回の例で使用したbobthefishは、[別途カラースキーム一覧](https://github.com/oh-my-fish/theme-bobthefish#configuration)があります。好きなカラースキームを探して、"~/.config/fish/config.fish"に"set theme\_color\_scheme (カラースキーム名)"を追記すれば、反映されます。カラースキームの色合いをテストする場合は、"\_\_bobthefish\_display\_colors"で確認できます(下画像)。

![](images/fish.png)

### 便利pluginのインストール

「最近使用したディレクトリにジャンプできる[z plugin](https://github.com/jethrokuan/z)」および「あいまい検索ができる[fzf plugin](https://github.com/junegunn/fzf)」のみをインストールします。

```
(注釈)："z (ディレクトリ名)"で、最近使用したディレクトリにジャンプ可能
$ fisher add jethrokuan/z

(注釈)：曖昧検索のfzfラッパー 
　　　　Ctrl+f：ファイル曖昧検索、Ctrl+r：コマンド履歴の曖昧検索、Alt+o：ディレクトリ検索
$ git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
$ ~/.fzf/install
$ fisher add jethrokuan/fzf
$ echo ""                                            >> ~/.config/fish/config.fish
$ echo "# FZFの古いキーバインドを使わない"                >> ~/.config/fish/config.fish
$ echo "# (昔、fishのキーバインドとコンフリクトしたため)"   >> ~/.config/fish/config.fish
$ echo "set -U FZF_LEGACY_KEYBINDINGS 0"             >> ~/.config/fish/config.fish

```

### 他に設定を変更する場合：Webブラウザで設定

fishは、設定をWebブラウザ経由で変更することが出来ます。Terminalで"fish\_config"と入力し、実行すれば以下の画面が開かれます。後は、ユーザの好みで設定を適宜変更して下さい。

![](images/fish_setting.png)
