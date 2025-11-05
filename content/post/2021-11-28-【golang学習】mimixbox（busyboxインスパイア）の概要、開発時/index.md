---
title: "MimixBox（BusyBoxインスパイア）の概要、開発時の気づき、PR募集について【Golang学習】"
type: post
date: 2021-11-28
categories:
  - "linux"
  - "体験談"
tags:
  - "golang"
  - "linux"
  - "oss"
  - "体験談"
cover:
  image: images/laptop-g8777527aa_640-min.jpg
  alt: "MimixBox（BusyBoxインスパイア）の概要、開発時の気づき、PR募集について【Golang学習】"
  hidden: false
---

## MimixBoxはGolang学習用アプリとして開始 

Golang製の[MimixBox](https://github.com/nao1215/mimixbox)は、[BusyBox](https://www.busybox.net/)（多数のUnixコマンドをシングルバイナリに詰め込んだCLIアプリ）と共通点を持ちつつ、独自の目標を持つCLIアプリとして開発しています。

開発のキッカケは、Golangを学習するためです。[前職を退職](https://debimate.jp/2021/11/13/%e3%80%90%e9%80%80%e8%81%b7%e3%82%a8%e3%83%b3%e3%83%88%e3%83%aa%e3%80%91%e6%96%b0%e6%bd%9f%e5%9c%a8%e4%bd%8f%e3%81%ae%e7%b5%84%e3%81%bf%e8%be%bc%e3%81%bf%e3%82%a8%e3%83%b3%e3%82%b8%e3%83%8b%e3%82%a2/)して、新しい会社では開発経験のないGolangがメイン言語となりました。即戦力となれるよう、私は勉強のためにCLIツールや独自シェルを作り始めましたが、「全部混ぜて開発すればプロジェクト数が増えず、管理が楽では？それなら、BusyBoxを真似するか」という考えに至りました。

ここまで来れば「MimixBox - Mimic BusyBox on Linux（Linux上でBusyBoxを模倣する）」という名称を考えつくのは、一瞬でした。ちなみに、同様のプロジェクトには[toybox](https://github.com/shirou/toybox)と[gobox](https://github.com/surma/gobox)があります（皆、考える事は大体一緒）。

## MimixBoxはBusyBoxと違う道を目指す

MimixBoxは、**Linux****デスクトップ環境でのCLI（Terminal操作）が楽しくなる事**を目指します！そのため、「既存Unixコマンドの機能拡張（例：catに対する[bat](https://github.com/sharkdp/bat/blob/master/doc/README-ja.md)、lsに対する[lsd](https://github.com/Peltoche/lsd)）」や「独自コマンドの組み込み」が大事だと考えています。

上記のように考えた理由は「大きめなバイナリサイズ」と「対応コマンド数でBusyBoxに追いつけない事」です。

C言語製のBuxyBoxは、制約の多い組み込み環境でも動作する事から分かるように、バイナリサイズがかなり小さめです。私の環境では、コマンド263個を組み込んだBusyBoxのサイズは約2MBでした。

その一方で、コマンドを数個しか組み込んでいないMimixBoxは、サイズが約4MBありました（現在はコマンド42個で約5.6MB）。デバッグシンボルなどの不要な情報をstripしてもBusyBoxの2倍を超えるサイズなので、MimixBoxは組み込み環境向けとするのは無謀でした。

また、BusyBoxはコマンド数が400個以上あり、ドマイナーOSSのMimixBoxが同路線（量を増やす事）を真似しても勝ち目がありません。MimixBoxの出自はBusyBoxの模倣品ですが、BusyBoxを100%模倣しても面白くないので「じゃあ、コマンド単位の質を上げるか」と発想しました。

## MimixBoxのロードマップ

MimixBoxはGolang学習用のOSSという側面もあるので、全て独自コマンドで構成するような事はしていません。まずは、一般的なUnixコマンドを量産しつつ、合間に独自コマンドを開発するようなスタイルで進めています。

〜2022年12月：MimixBoxロードマップ

- Step1. 100件以上のUnixコマンドを実装（機能の増加、〜Version 0.XX.xx）
- Step2. オプションおよびテストを拡充（品質向上、〜Version 1.XX.xx）
- Step3. コマンドを近代的な仕様に変更（独自性の追加、〜Version 2.XX.xx）

## MimixBoxの独自オプション

MimixBoxは、BusyBoxとはオプションが異なります。下表にオプション一覧を示します。

（◯はMimixBox独自、△はBusyBoxから仕様変更、×はBusyBoxと同じ挙動）

| **オプション** | **独自（仕様変更）** | **仕様** |
| --- | --- | --- |
| \-i, --install | △ | MimixBox組み込みコマンドのシンボリックリンクを指定ディレクトリに作成する。ただし、システムに同名コマンドが存在する場合は、リンク作成しない。 |
| \-f, --full-install | ◯ | MimixBox組み込みコマンドのシンボリックリンクを指定ディレクトリに作成する |
| \-h, --help | × | ヘルプメッセージを表示する |
| \-l, --list | △ | MimixBox組み込みコマンド名称と説明文を表示する |
| \-r, --remove | ◯ | MimixBox組み込みコマンドのシンボリックリンクを削除する |
| \-v, --version | × | バージョン情報を表示する |

オプションに独自性を出した理由は、「MimixBox開発中にシステムをブッ壊したから」です。引数処理を間違えた結果、MimixBoxの提供するcatコマンドが動きませんでした。運悪くGUIライブラリがcatコマンドを使っていたので、GUI起動が必ず失敗するようになりました。

この問題の対策として、「--installオプションが安全インストール（システムに存在しないコマンドのみシンボリックリンク作成）」「--full-installオプションがBusyBoxと同仕様」としました。さらに、レスキューモードでのシステム復旧が簡便になるように、--removeオプションでシンボリックリンクを一掃できるようにしました。

現在は、Docker内でMimixBoxをテスト可能な状態にしたので、より安全に遊べます。

<blockquote class="twitter-tweet" data-conversation="none" data-theme="light"><p dir="ltr" lang="ja">MimixBox（BusyBoxのパクリ）は<br>$ make docker<br>を叩くと、Docker環境で安全にMimixBoxと遊べるようにした。ドッグフーディングし始めると、バグがチラホラ見つかる。<br><br>自前のシェルも早く準備したい。<br>ただ、Coreutils再実装ばかりではなくて、独自コマンドも追加したいのよね<a href="https://t.co/qDAPYL2mk8">https://t.co/qDAPYL2mk8</a></p>— Nao31@ (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1461950699441377281?ref_src=twsrc%5Etfw">November 20, 2021</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

## MimixBox開発中の気づき（感想）

気づき（感想）は、3つあります。その内容は、「プロジェクトの感触が良い事」「Golangと親友に慣れない事」「ユニットテストの重要性」についてです。

MimixBoxプロジェクト（2021年11月28日現在での規模は約5000\[LOC\]）は、開発開始して1ヶ月弱。Golangの文法やAPIを着実に学べており、個人的には良いプロジェクトと感じています。長期間付き合って行けそうなプロジェクトである点も好ましく、「便利なOSSになると良いなー」と考えながら実装してます。

```
-------------------------------------------------------------------------------
Language                     files          blank        comment           code
-------------------------------------------------------------------------------
Go                              56           1142           1136           4999
Markdown                        25            299              0           1186
Bourne Shell                     5             47             42            252
make                             1             10              0             32
Dockerfile                       1              5              5              7
-------------------------------------------------------------------------------
SUM:                            88           1503           1183           6476
-------------------------------------------------------------------------------
```

Golangと親友になれない件は、身も蓋もない話ですが、私はGolangがあまり好きではなく。個人的な印象では「Golangは便利なC言語」止まりであり、どちらかと言えば私はクラス指向の強いJavaやRubyの方が好み。C言語やGolangを書いている時はデータ中心に設計できなくなる傾向（癖）があり、処理をシーケンシャルに記述しがち。まだ慣れていないという事でしょうか。

ユニットテストの重要性については、言うまでもないでしょう。今回は、Version1.0.0（= コマンドを100件程度作成した状態）でユニットテストを量産する予定でした。しかし、MimixBox組み込みコマンド全体に影響がある修正が必要になった時、「テストを先に作れば良かった……」と後悔しました。

全コマンドに影響がある修正は、何度も発生しました。例えば、「[パイプ（"|"）対応](https://debimate.jp/2021/11/23/golang%e3%81%a7%e7%84%a1%e5%90%8d%e3%83%91%e3%82%a4%e3%83%97%e3%81%8b%e3%82%89%e3%83%87%e3%83%bc%e3%82%bf%e3%82%92%e5%8f%97%e3%81%91%e5%8f%96%e3%82%8b%e6%96%b9%e6%b3%95%e3%80%90terminal-isterminal/)」「リダイレクト（">"や">>"）対応」「引数で指定された環境変数の展開」あたりは、初期実装時には未対応でした。そのため、途中で機能追加しました。が、テストが無かったのでデグレしているのかが即座に分からず、手間が多くかかりました。

同じ轍を踏まないように、Version 1.0.0に移行する前にユニットテストを作り始めようかな、と考えている次第です。

## Pull Requestを歓迎します

[MimixBox](https://github.com/nao1215/mimixbox)は、2021年11月28日現在で42個のコマンドをサポートしています（一部、基本機能すら未完成コマンドがありますが……）。より多くのコマンドをサポートしたいので、「未サポートコマンド（独自コマンド含む）の追加」「オプション追加」「バグ修正」など、PRいただけると大変嬉しいです。

以下、MimixBoxに組み込んでいるコマンド（サポートコマンド）リストです。

```
nao@nao:~/.go/src/github.com/nao1215/mimixbox$ ./mimixbox --list
   base64 - Base64 encode/decode from FILR(or STDIN) to STDOUT
 basename - Print basename (PATH without"/") from file path
      cat - Concatenate files and print on the standard output
   chroot - Run command or interactive shell with special root directory
   cowsay - Print message with cow's ASCII art
       cp - Copy file(s) otr Directory(s)
 dos2unix - Change CRLF to LF
     echo - Display a line of text
   expand - Convert TAB to N space (default:N=8)
fakemovie - Adds a video playback button to the image
    false - Do nothing. Return unsuccess(1)
    ghrdc - GitHub Relase Download Counter
   groups - Print the groups to which USERNAME belongs
     head - Print the first NUMBER(default=10) lines
   hostid - Print hostid (Host Identity Number, hex)!!!Does not work properly!!!
       id - Print User ID and Group ID
 ischroot - Detect if running in a chroot
       ln - Create hard or symbolic link
     mbsh - Mimix Box Shell
   md5sum - Calculate or Check md5sum message digest
    mkdir - Make directories
   mkfifo - Make FIFO (named pipe)
       mv - Rename SOURCE to DESTINATION, or move SOURCE(s) to DIRECTORY
       nl - Write each FILE to standard output with line numbers added
     path - Manipulate filename path
       rm - Remove file(s) or directory(s)
    rmdir - Remove directory
      seq - Print a column of numbers
   serial - Rename the file to the name with a serial number
  sha1sum - alculate or Check sercure hash 1 algorithm
sha256sum - alculate or Check sercure hash 256 algorithm
sha512sum - alculate or Check sercure hash 512 algorithm
       sl - Cure your bad habit of mistyping
    sleep - Pause for NUMBER seconds(minutes, hours, days)
      tac - Print the file contents from the end to the beginning
     tail - Print the last NUMBER(default=10) lines
    touch - Update the access and modification times of each FILE to the current time
     true - Do nothing. Return success(0)
 unexpand - Convert N space to TAB(default:N=8)
 unix2dos - Change LF to CRLF
    which - Returns the file path which would be executed in the current environment
   whoami - Print login user name
```

コントリビュートに関する資料（コマンド追加方法含む）は、[コチラ](https://github.com/nao1215/mimixbox/blob/main/CONTRIBUTING.md)に記載しています。基本的なルールは、「GPLv2ライセンスのコードは含めないでください」と「テストコードなくてもOK」ぐらいしかありません。

また、MimixBoxの開発状況を伝えるためのTwitterアカウントがあります（ちょっと作るの早いと思いましたが……）。日本語と英語の両方で情報発信して行く予定ですので、ご興味があればフォローお願いいたします！

<blockquote class="twitter-tweet"><p dir="ltr" lang="en">Mimixbox 0.25.1 has been released.<br><br>The following commands have been newly added.<br>- hostid<br>- md5sum<br>- seq<br>- sha1sum／sha256sum／sha512sum<br>Furthermore, all commands support redirects.<br><br>Now, MimixBox supports 39 commands.<a href="https://t.co/YAWdc7KkMh">https://t.co/YAWdc7KkMh</a> <a href="https://t.co/3ad3NPukPH">pic.twitter.com/3ad3NPukPH</a></p>— MimixBox@ʕ◔ϖ◔ʔ (@mimixbox156) <a href="https://twitter.com/mimixbox156/status/1464499737982242817?ref_src=twsrc%5Etfw">November 27, 2021</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

## GitHub Sponsorsでスポンサーを募集中

最近話題のGitHub Sponsorsに対応しています！

金銭的な支援をいただけるのは単純に嬉しいですし、誰かにサポートしていただいている事実はそれだけでモチベーションが上がります。以下のボタンを押してもスポンサーページに飛ぶだけなので、安心してクリックしてみてください。

スポンサーの方へのお礼（金額によって対応可否が異なります）

- MimixBoxのコントリビュータリスト（支援者一覧）に名前を記載
- Twitter上でのお礼（名前およびSNSアカウントを併記）
- 優先的に開発するコマンドの決定権（コマンド1個分かつ規模200〜500\[LOC\]程度）

<iframe width="600" height="225" style="border: 0;" src="https://github.com/sponsors/nao1215/card" title="Sponsor nao1215"></iframe>

##  おまけ：2022年に作成したGolang製コマンド一覧

https://debimate.jp/2022/02/05/%e3%80%90golang%e3%80%912022%e5%b9%b4%e3%81%ab%e9%96%8b%e7%99%ba%e3%81%97%e3%81%9f%e8%87%aa%e4%bd%9ccli%e3%82%b3%e3%83%9e%e3%83%b3%e3%83%89%ef%bc%8f%e3%83%a9%e3%82%a4%e3%83%96%e3%83%a9%e3%83%aa/
