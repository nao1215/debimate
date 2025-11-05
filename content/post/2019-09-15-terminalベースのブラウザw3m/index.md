---
title: "Terminalベースのブラウザw3m"
type: post
date: 2019-09-15
categories:
  - "linux"
tags:
  - "debian"
  - "linux"
  - "w3m"
  - "環境構築"
cover:
  image: images/w3m.jpg
  alt: "Terminalベースのブラウザw3m"
  hidden: false
---

## 前書き

前回、キーボードのみで操作を完結させる手段として、keynavを紹介しました。

https://debimate.jp/2019/09/15/%e3%83%9e%e3%82%a6%e3%82%b9%e3%83%9d%e3%82%a4%e3%83%b3%e3%82%bf%e3%82%92%e3%82%ad%e3%83%bc%e3%83%9c%e3%83%bc%e3%83%89%e3%81%a7%e6%93%8d%e4%bd%9c%e3%81%99%e3%82%8bkeynav/

同じように、キーボードで操作が完結できる[w3m](http://w3m.sourceforge.net/index.ja.html)を本記事で紹介します。[w3m(WWW-wo-Miru)](http://w3m.sourceforge.net/index.ja.html%0A)は、日本人が作成したテキストベースWebブラウザです。端末上でWeb検索作業できますが、使いづらい部分があったため、それらを補うスクリプトも本記事に記載します。

## 検証環境

```
       _,met$$$$$gg.          nao@debian 
    ,g$$$$$$$$$$$$$$$P.       ---------- 
  ,g$$P"     """Y$$.".        OS: Debian GNU/Linux 10 (buster) x86_64 
 ,$$P'              `$$$.     Kernel: 4.19.0-6-amd64 
',$$P       ,ggs.     `$$b:   Uptime: 46 minutes 
`d$$'     ,$P"'   .    $$$    Packages: 2476 (dpkg) 
 $$P      d$'     ,    $$P    Shell: fish 3.0.2 
 $$:      $$.   - ,d$$'    Resolution: 2560x1080 
 $$;      Y$b._   _,d$P'      DE: Cinnamon 3.8.8 
 Y$$.    `.`"Y$$$$P"'         WM: Mutter (Muffin) 
 `$$b      "-.__              WM Theme: cinnamon (Albatross) 
  `Y$$                        Theme: BlackMATE [GTK2/3] 
   `Y$$.                      Icons: gnome [GTK2/3] 
     `$$b.                    Terminal: gnome-terminal 
       `Y$$b.                 CPU: Intel i3-6100U (4) @ 2.300GHz 
          `"Y$b._             GPU: Intel HD Graphics 520 
              `"""            Memory: 2974MiB / 32060MiB 
```

## w3mのインストール方法

```
$ sudo apt update
$ sudo apt install w3m
$ sudo apt install w3m-img   (注釈)端末上で画像を表示したい場合はインストール
 
```

## w3mの起動方法

\[起動書式\]

```
w3m $URL
```

\[起動例\]

```
w3m http://google.com
```

![w3m](images/w3m.jpg)

## スクリプトによる起動簡略化

w3mの使いづらい点の一つに、起動時のURL入力があります。この問題を解消するために、以下のggleスクリプトを用いれば、"ggle \[検索ワード(複数可、スペース区切り)\]"で検索が出来ます。

```
#!/bin/bash
# @(#) google to change argument of w3m command from URL to search word.
#
ARGS=""
ARG=""

function showUsage() {
    cat <<_EOT_
  Usage:
    ./google 
  Description:
    Read this script
  Options:
    -h|--help : show usage.
_EOT_
exit 1
}

# Check args
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    showUsage
fi

# Connect arguments as character string
for ARG in "$@"
do
    ARGS="${ARGS}+${ARG}"
done
ARGS=$(echo ${ARGS} | sed 's/^\+//')

# Start web searching
w3m http://www.google.co.jp/search?q="${ARGS}"     
```

ggleスクリプトは、以下の手順でインストールしてください。

```
$ chmod a+x ggle    (注釈) ggleスクリプトは手動でコピーしてください
$ sudo cp ggle /usr/local/bin/.
```

## 最後に

w3mの操作マニュアルは、[公式サイト](http://w3m.sourceforge.net/MANUAL.ja.html)を参照して下さい。
