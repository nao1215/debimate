---
title: "Debian: 任意のtesting/unstableパッケージのみをinstallする方法(システム全体はstableを維持)"
type: post
date: 2019-03-09
categories:
  - "linux"
tags:
  - "debian"
  - "linux"
  - "環境構築"
cover:
  image: "images/debian.jpg"
  alt: "Debian: 任意のtesting/unstableパッケージのみをinstallする方法(システム全体はstableを維持)"
  hidden: false
---

### 前書き

Debianパッケージは、基本的な使い方をしていれば、安定版(stable)がシステムにinstallされます。しかし、「使用したいパッケージがstableにない場合」や「より新しいパッケージを使いたい場合」、システムにtesting/unstableパッケージを導入する必要性がでてきます。

この際、システム全体をtesting/unstableに変更したくない人は、多いと思います。その理由の一つは、パッケージが期待よりテストされていなかった場合、downgrade作業を実施しなければならないからです。最悪のケースは、testing/unstableから元々の環境(stable)へのdowngradeが失敗した場合、システムの再インストールが必要となる事です。

以上を踏まえて、本記事では、任意のtesting/unstableパッケージのみをシステムにinstallする方法を記載します。実施内容の概要は、以下の3点です。

実施内容(概要)

- testing/unstableのミラーサーバをsources.listに追加
- installパッケージ毎の優先度を設定(Versionコントロール)
- testing/unstableパッケージのinstall

---


### 前提：2019年3月時点のDebian Version

下表に、2019年3月時点のDebian Version名を示します。[コードネームは、Toy Storyのキャラから選ばれています](https://wiki.debian.org/DebianReleases)。映画を見た事ある人は、何故sidが開発者向けのVersionかが想像できると思います。

| **状態** | **コードネーム(Ver)** | **説明** |
| --- | --- | --- |
| oldstable | jessie(8.x) | 次Versionの安定版リリース後(testingがstableに移行後)、旧安定版として区別されます。初回リリースから少なくとも5年間、LTS(Long Term Support)の対象。 |
| stable | stretch(9.x) | 現行の安定版。安定版は、2年間隔でリリースされます。 |
| testing | buster(10.x) | 次の安定版として、公開テスト中のVersion。 |
| unstable | sid(なし) | 開発者向けのVersion。コードネームは、常に"sid"。 |
| experimental | experimental | unstableに導入する前の実験段階Version。一般ユーザだけでなく、開発者に対しても「installは危険」と警告されています。 |

---


### testing/unstableのミラーサーバをsources.listに追加

デフォルトの状態では、install時Version向け(例：stretch)のミラーサーバのみがsources.listに追加されています。testing/unstableパッケージをミラーサーバからダウンロードするため、/etc/apt/sources.listを修正しなければいけません。

修正例として、/etc/apt/sources.listに以下の4行を追記します。管理者権限が必要です。

```
deb http://ftp.jp.debian.org/debian/ testing main non-free
deb-src http://ftp.jp.debian.org/debian/ testing main non-free
deb http://ftp.jp.debian.org/debian/ unstable main non-free
deb-src http://ftp.jp.debian.org/debian/ unstable main non-free
```

"http://ftp.jp.debian.org/debian/"部分は、好きなミラーサーバを選択してください[(ミラーサーバ一覧へのリンク)](https://www.debian.or.jp/using/mirror.html)。上記で重要な部分は、"testing"もしくは"unstable"と記載した箇所です。通常であれば、stableのVersion(例：stretch)と書かれています。testing/unstableを追記した事により、これらのVersionのパッケージをミラーサーバからダウンロード可能な状態になりました(正確には、apt updateまで必要)。

---


### installパッケージ毎の優先度を設定(Versionコントロール)

aptコマンドは、preferencesファイルによって、システムへ導入するパッケージを制御できます。今回は、「システム全体はstable」を維持しつつ、「apt install時に指定があった場合のみ、testing/unstableパッケージを導入可能」という状態を作ります。

前述の状態を作るため、/etc/apt/preferencesを新規作成し、以下の内容を記載します。

```
Package: *
Pin: release a=stable
Pin-Priority: 900

Package: *
Pin: release a=testing
Pin-Priority: 99

Package: *
Pin: release a=unstable
Pin-Priority: 89

```

"Package:"では、Versionコントール対象のパッケージを選択します。"\*"はワイルドカードなので、全てのパッケージが対象になります。

"Pin:"では、パッケージをどのVersionで固定するかを設定します。"release a="で、「アーカイブ名がstable/testing/unstableと設定されたパッケージを使う」と設定しています。

"Pin-Priority:"は、最も重要な箇所で、パッケージinstall時の優先度を設定しています。優先度が1000に近いパッケージが優先的にinstallされます。そのため、上記の例では、stableパッケージが最優先でinstallされます。

また、0 < Priority < 100の範囲は、「"apt install"でパッケージを指定すればinstallできますが、依存対象のパッケージを暗黙的にupdateをしない」という意味です。つまり、依存関係の満たせないtesting/unstableパッケージは、installできません。

下表に、Pin-Priority(優先度)の割り当てを示します。

| **優先度** | **説明** |
| --- | --- |
| P >= 1000 | パッケージをdowngradeしたい場合に指定 |
| 990 <= P < 1000 | install済みパッケージVersionの方が新しいのでなければ、stable以外でもパッケージをinstall。 |
| 500 <= P < 990 | stableに属するVersionが公開済み、もしくはinstall済みパッケージVersionの方が新しいのでなければ、パッケージをinstall。500は、現在 install されていないパッケージの デフォルト優先度。 |
| 100 <= P < 500 | stable以外に属するVersionが公開済み、もしくはインストール済みVersionの方が新しいのでなければ、パッケージをinstall。 |
| 0 < P < 100 | パッケージがinstallされていない場合、パッケージをinstall |
| P < 0 | install禁止。 |
| P = 0 | 動作未定義。 |

testing/unstableは、優先度として100 <= Priority < 500の範囲を指定しても良いです。ただし、testing/unstableパッケージの依存関係を満たすパッケージVersionが未作成(作成中)の場合、install時にエラーとなります。

---


### testing/unstableパッケージのinstall

testing/unstableパッケージのinstall例として、依存関係を満たせるケースと、満たせないケースの2点を紹介します。以下の手順を実行する前に、"sudo apt update"を実施してください。この段階で、パッケージがtesting/unstableに置き換わる事はありません。なお、testing/unstableをinstallする場合、以下の書式を用います。

書式

\# apt install <package\_name>/<Version>

依存関係を満たせるケース

```
$ sudo apt install cowsay/testing
$ cowsay test
 ______
< test >
 ------
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||

$ apt source cowsay/testing  (注釈)ソースコードもtestingがDownload可能
$ ls　　　　　　　　　　　 (注釈)testingは、3.03+dfsg2-6。stretchは、3.03+dfsg2-3。
cowsay-3.03+dfsg2                  cowsay_3.03+dfsg2-6.dsc
cowsay_3.03+dfsg2-6.debian.tar.xz  cowsay_3.03+dfsg2.orig.tar.gz

```

依存関係を満たせないケース(Perl)

依存関係を満たせるケースと同じ手順を実施した場合、以下のようにエラーとなります。

```
$ sudo apt install perl/unstable
パッケージリストを読み込んでいます... 完了
依存関係ツリーを作成しています                
状態情報を読み取っています... 完了
'perl' のバージョン '5.28.1-4' (Debian:testing, Debian:unstable [amd64]) を選択しました
'perl' のために 'perl-base' のバージョン '5.28.1-4' (Debian:testing, Debian:unstable [amd64]) を選択しました
'perl-base' のために 'libc6' のバージョン '2.28-8' (Debian:unstable [amd64]) を選択しました
'libc6' のために 'libidn2-0' のバージョン '2.0.5-1' (Debian:testing, Debian:unstable [amd64]) を選択しました
'perl' のために 'perl-modules-5.28' のバージョン '5.28.1-4' (Debian:testing, Debian:unstable [all]) を選択しました
'perl' のために 'libperl5.28' のバージョン '5.28.1-4' (Debian:testing, Debian:unstable [amd64]) を選択しました
'libperl5.28' のために 'libgdbm-compat4' のバージョン '1.18.1-3' (Debian:testing, Debian:unstable [amd64]) を選択しました
インストールすることができないパッケージがありました。おそらく、あり得
ない状況を要求したか、(不安定版ディストリビューションを使用しているの
であれば) 必要なパッケージがまだ作成されていなかったり Incoming から移
動されていないことが考えられます。
以下の情報がこの問題を解決するために役立つかもしれません:

以下のパッケージには満たせない依存関係があります:
 perl : 依存: perl-base (= 5.28.1-4) しかし、5.24.1-3+deb9u5 はインストールされようとしています
        依存: perl-modules-5.28 (>= 5.28.1-4) しかし、インストールされようとしていません
        依存: libperl5.28 (= 5.28.1-4) しかし、インストールされようとしていません
E: 問題を解決することができません。壊れた変更禁止パッケージがあります。

```

このような場合は、aptコマンドの"-t"オプションでinstallパッケージのVersionを指定します。ちなみに、以下の手順はglibcが更新されるため、実行しないでください。影響範囲が大きく、システムが壊れてしまう可能性があります。

```
$ sudo apt install -t unstable perl
$ perl -e 'print "Hello,World\n";'
Hello,World

```

---


### 参考

[Debian Experimental](https://wiki.debian.org/DebianExperimental)

[Debian管理者ハンドブック](https://debian-handbook.info/download/ja-JP/stable/debian-handbook.pdf)
