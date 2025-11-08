---
title: "Bash(Shell Script)からRubyやPythonに乗り換え！頻繁に使う処理を各言語で比較"
type: post
date: 2020-04-05
categories:
  - "linux"
tags:
  - "bash"
  - "linux"
  - "python"
  - "ruby"
  - "shellscript"
cover:
  image: "images/scripts-min.jpg"
  alt: "Bash(Shell Script)からRubyやPythonに乗り換え！頻繁に使う処理を各言語で比較"
  hidden: false
---

## 前書き：自動化にBashを使うと後々辛い

本記事では、自動化で用いる言語をBash(Shell Script)からRubyやPython3に変更する方法を紹介します。Bash / Ruby / Python3のそれぞれで、ファイル操作やディレクトリ操作などをどのように書くか、コード例と実行例を示しながら紹介します（正確には、別記事で実装例を説明します）。

大前提として、Bashは良い言語であり、私はBashが好きです。主要なLinuxディストリビューションにインストールされていますし、[POSIX互換](https://ja.wikipedia.org/wiki/POSIX)を意識して書けば移植時の修正箇所が減ります。普段のターミナル操作と同じ感覚で書けるため、多くのLinux開発者は少ない学習時間でShell Scriptを書けます。

しかし、Bashは言語としてサポートする機能が貧弱です。

Bashが機能的に貧弱な点

- 変数が全てグローバル
- コレクション（HashやList）がない
- 例外処理が弱い（trapのみ）
- オブジェクト指向ができない
- 単体テスト（[bats](https://github.com/sstephenson/bats)）するには、関数部と処理部を別ファイルに分離しなければならない

上記の機能面以外にも不満が出やすく、「シェル芸（難読化されたワンライナーを作成）する人が出てくる」、「特殊変数（$?、$@、$#...）が覚えづらい」、「while(サブシェル)の計算結果が元プロセスでは0になる」など、Bash固有の問題があります。

このような点を踏まえずにBashで自動化スクリプトを作り始めると、未来に訪れる機能追加・異常系追加・コード改善で激しく後悔する事になります。そのため、本記事では、RubyやPython3によるScriptの置き換えを推奨しています。

## 自動化ScriptにBashを採用すべきかの判断基準

具体的なコード例に入る前に、私が自動化Scriptを書く際、Bashを採用すべきかの判断基準（主観、経験則）を以下にまとめます。以下のいずれかに当てはまる場合は、Bashを使用しても問題ないと考えています。

判断基準

- RubyやPythonが環境になく、インストールもできない。
- 自動化スクリプトは、あるコマンドをキックするだけ。
- 作成予定のScriptが50〜100Step（ユーザ入力やファイル存在確認が3回程度）

判断基準に含めていないのは、プログラミング言語自体のアップデートという観点です。

後方互換性がない場合、アップデートに伴い、自動化Scriptが動作しなくなります。しかし、自動化Scriptという範囲では、枯れた技術であるBashを選んで助かった経験もなく、後方互換性がなくて困った経験もありません。自動化Scriptを少ない労力で長く運用したい場合は、プロジェクトの特性に合わせて言語選択してください。

## Bash / Ruby / Python3の実装比較（一覧）

別記事で、Bash / Ruby / Python3それぞれの実装を比較しています。リンク先がない項目は、実装の比較例を作成次第、下表を更新していきます。

| **No.** | **種類** | **実装内容** |
| --- | --- | --- |
| 1 | PATH取得 | [カレントワーキングディレクトリの取得](https://debimate.jp/post/2020-04-05-bashshell-script%E3%81%8B%E3%82%89ruby%E3%82%84python%E3%81%AB%E4%B9%97%E3%82%8A%E6%8F%9B%E3%81%88%E3%82%AB%E3%83%AC%E3%83%B3%E3%83%88%E3%83%AF%E3%83%BC%E3%82%AD%E3%83%B3%E3%82%B0%E3%83%87/) |
| 2 | PATH取得 | [実行ファイル名、実行ファイルの相対・絶対PATHの取得](https://debimate.jp/post/2020-04-05-bash-ruby-python3%E5%AE%9F%E8%A1%8C%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E5%90%8D%E5%AE%9F%E8%A1%8C%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E3%81%AE%E7%B5%B6%E5%AF%BE/) |
| 3 | ファイル操作 | [ファイルの存在確認](https://debimate.jp/post/2020-04-06-bash-ruby-python3%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E3%81%AE%E5%AD%98%E5%9C%A8%E3%82%92%E7%A2%BA%E8%AA%8D%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95%E3%81%AE%E6%AF%94%E8%BC%83/) |
| 4 | ファイル操作 | [新規ファイル作成（一時ファイル作成含む）、ファイル削除](https://debimate.jp/post/2020-04-07-bash-ruby-python3%E6%96%B0%E8%A6%8F%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E4%BD%9C%E6%88%90%E4%B8%80%E6%99%82%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E4%BD%9C%E6%88%90/) |
| 5 | ファイル操作 | [ファイル読み込み、ファイル書き込み](https://debimate.jp/post/2020-04-08-bash-ruby-python3%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E8%AA%AD%E3%81%BF%E8%BE%BC%E3%81%BF%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E6%9B%B8%E3%81%8D%E8%BE%BC%E3%81%BF/) |
| 6 | ファイル操作 | [PATHからのファイル名抽出、ファイル名(拡張子なし）取得、拡張子の取得](https://debimate.jp/post/2020-04-08-bash-ruby-python3path%E3%81%8B%E3%82%89%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E5%90%8D%E3%81%AE%E6%8A%BD%E5%87%BA%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E5%90%8D%E6%8B%A1/) |
| 7 | ファイル操作 | [ファイル一覧取得、ファイル数確認](https://debimate.jp/post/2020-04-09-bash-ruby-python3%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E4%B8%80%E8%A6%A7%E3%81%AE%E5%8F%96%E5%BE%97%E6%96%B9%E6%B3%95%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E6%95%B0/) |
| 8 | ファイル操作 | [ファイルのコピー、ファイルの移動](https://debimate.jp/post/2020-04-09-bash-ruby-python3%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E3%81%AE%E3%82%B3%E3%83%94%E3%83%BC%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E3%81%AE%E7%A7%BB%E5%8B%95%E6%96%B9/) |
| 9 | ファイル操作 | ファイルの圧縮・展開 |
| 10 | ディレクトリ操作 | [ディレクトリの存在確認](https://debimate.jp/post/2020-04-06-bash-ruby-python3%E3%83%87%E3%82%A3%E3%83%AC%E3%82%AF%E3%83%88%E3%83%AA%E3%81%AE%E5%AD%98%E5%9C%A8%E3%82%92%E7%A2%BA%E8%AA%8D%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95%E3%81%AE/) |
| 11 | ディレクトリ操作 | [新規ディレクトリ作成、ディレクトリ削除](https://debimate.jp/post/2020-04-10-bash-ruby-python3%E6%96%B0%E8%A6%8F%E3%83%87%E3%82%A3%E3%83%AC%E3%82%AF%E3%83%88%E3%83%AA%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95%E3%83%87%E3%82%A3%E3%83%AC%E3%82%AF/) |
| 12 | 文字列操作 | 文字列判定、正規表現による文字列加工 |
| 13 | 文字列操作 | [ヒアドキュメントの書き方](https://debimate.jp/post/2020-04-07-bash-ruby-python3%E3%83%92%E3%82%A2%E3%83%89%E3%82%AD%E3%83%A5%E3%83%A1%E3%83%B3%E3%83%88%E6%96%87%E5%AD%97%E5%88%97%E3%83%AA%E3%83%86%E3%83%A9%E3%83%AB%E5%9F%8B%E3%82%81/) |
| 14 | 文字列操作 | [出力文字色の変更](https://debimate.jp/post/2020-04-11-bash-ruby-python3ansi%E3%82%A8%E3%82%B9%E3%82%B1%E3%83%BC%E3%83%97%E3%82%B7%E3%83%BC%E3%82%B1%E3%83%B3%E3%82%B9%E3%82%92%E7%94%A8%E3%81%84%E3%81%9F%E5%87%BA%E5%8A%9B%E6%96%87/) |
| 15 | 権限操作 | [ユーザ名、UID、グループ名、GIDの取得](https://debimate.jp/post/2020-04-12-bash-ruby-python3%E3%83%A6%E3%83%BC%E3%82%B6%E5%90%8D-uid-%E3%82%B0%E3%83%AB%E3%83%BC%E3%83%97%E5%90%8D-gid%E3%82%92%E5%8F%96%E5%BE%97%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95/) |
| 16 | 権限操作 | [root権限確認](https://debimate.jp/post/2020-04-11-bash-ruby-python3root%E6%A8%A9%E9%99%90%E3%82%92%E7%A2%BA%E8%AA%8D%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95%E3%81%AE%E6%AF%94%E8%BC%83/) |
| 17 | 権限操作 | ファイルアクセス権の確認や変更 |
| 18 | 外部コマンド操作 | [外部コマンドの実行](https://debimate.jp/post/2020-04-12-bash-ruby-python3%E5%A4%96%E9%83%A8%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89%E3%82%92%E5%AE%9F%E8%A1%8C%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95%E3%81%AE%E6%AF%94%E8%BC%83/) |
| 19 | UI | [ユーザ入力の取得](https://debimate.jp/post/2020-04-09-bash-ruby-python3%E3%83%A6%E3%83%BC%E3%82%B6%E5%85%A5%E5%8A%9Binput%E5%8F%97%E3%81%91%E4%BB%98%E3%81%91%E6%96%B9%E6%B3%95%E3%81%AE%E6%AF%94%E8%BC%83/) |
| 20 | UI | [オプション解析](https://debimate.jp/post/2020-04-11-bash-ruby-python3%E3%82%AA%E3%83%97%E3%82%B7%E3%83%A7%E3%83%B3%E8%A7%A3%E6%9E%90%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95%E3%81%AE%E6%AF%94%E8%BC%83/) |

各言語のVersionは、以下を想定しています。

- Bash：GNU bash, バージョン 5.0.3(1)-release
- Ruby：ruby 2.5.5p157 (2019-03-15 revision 67260)
- Python：Python 3.7.3

## Bash / Ruby / Python3の参考書籍

各言語を知らない人向けに、参考書籍を紹介します。

**Bash**

<iframe style="width: 120px; height: 240px;" marginwidth="0" marginheight="0" scrolling="no" frameborder="0" src="//rcm-fe.amazon-adsystem.com/e/cm?lt1=_blank&amp;bc1=000000&amp;IS2=1&amp;bg1=FFFFFF&amp;fc1=000000&amp;lc1=0000FF&amp;t=debimate07-22&amp;language=ja_JP&amp;o=9&amp;p=8&amp;l=as4&amp;m=amazon&amp;f=ifr&amp;ref=as_ss_li_til&amp;asins=4774132020&amp;linkId=dbdbeb1f43eed0f217af5df9b4fa9c71"></iframe>

<iframe style="width: 120px; height: 240px;" marginwidth="0" marginheight="0" scrolling="no" frameborder="0" src="//rcm-fe.amazon-adsystem.com/e/cm?lt1=_blank&amp;bc1=000000&amp;IS2=1&amp;bg1=FFFFFF&amp;fc1=000000&amp;lc1=0000FF&amp;t=debimate07-22&amp;language=ja_JP&amp;o=9&amp;p=8&amp;l=as4&amp;m=amazon&amp;f=ifr&amp;ref=as_ss_li_til&amp;asins=4873112540&amp;linkId=816fa7cb609845c55ba3364e7a7bd8db"></iframe>

<iframe style="width: 120px; height: 240px;" marginwidth="0" marginheight="0" scrolling="no" frameborder="0" src="//rcm-fe.amazon-adsystem.com/e/cm?lt1=_blank&amp;bc1=000000&amp;IS2=1&amp;bg1=FFFFFF&amp;fc1=000000&amp;lc1=0000FF&amp;t=debimate07-22&amp;language=ja_JP&amp;o=9&amp;p=8&amp;l=as4&amp;m=amazon&amp;f=ifr&amp;ref=as_ss_li_til&amp;asins=4873113768&amp;linkId=a8c5e7ab6845d82eb325c498da4846ca"></iframe>

"ゲームで極める〜"の方はややマニアックな知識を取り扱い、入門bashはいつものオライリー書籍。bashクックブックは、[目次](https://www.oreilly.co.jp/books/9784873113760/)を見てピンときたら手に取ると良いかも。

個人的には、bashクックブックは入門bashよりオススメ。環境構築から始まり、実践的なTipsが多数紹介されているため、辞書的な使い方でお世話になります。

**Ruby**

https://debimate.jp/2020/01/13/review%ef%bc%9a%e3%83%97%e3%83%ad%e3%82%92%e7%9b%ae%e6%8c%87%e3%81%99%e4%ba%ba%e3%81%ae%e3%81%9f%e3%82%81%e3%81%aeruby%e5%85%a5%e9%96%80-%e8%a8%80%e8%aa%9e%e4%bb%95%e6%a7%98%e3%81%8b%e3%82%89%e3%83%86/

https://debimate.jp/2020/01/16/review%ef%bc%9a%e3%82%aa%e3%83%96%e3%82%b8%e3%82%a7%e3%82%af%e3%83%88%e6%8c%87%e5%90%91%e8%a8%ad%e8%a8%88%e5%ae%9f%e8%b7%b5%e3%82%ac%e3%82%a4%e3%83%89-ruby%e3%81%a7%e3%82%8f%e3%81%8b%e3%82%8b/

他言語からRubyを学ぶ場合は上記二冊を読んでから実践に入ると、体系的な知識が手に入る筈です。

**Python**

<iframe style="width: 120px; height: 240px;" marginwidth="0" marginheight="0" scrolling="no" frameborder="0" src="//rcm-fe.amazon-adsystem.com/e/cm?lt1=_blank&amp;bc1=000000&amp;IS2=1&amp;bg1=FFFFFF&amp;fc1=000000&amp;lc1=0000FF&amp;t=debimate07-22&amp;language=ja_JP&amp;o=9&amp;p=8&amp;l=as4&amp;m=amazon&amp;f=ifr&amp;ref=as_ss_li_til&amp;asins=4873117380&amp;linkId=d133703a4d309e62c711e7f06b5ad733"></iframe>

<iframe style="width: 120px; height: 240px;" marginwidth="0" marginheight="0" scrolling="no" frameborder="0" src="//rcm-fe.amazon-adsystem.com/e/cm?lt1=_blank&amp;bc1=000000&amp;IS2=1&amp;bg1=FFFFFF&amp;fc1=000000&amp;lc1=0000FF&amp;t=debimate07-22&amp;language=ja_JP&amp;o=9&amp;p=8&amp;l=as4&amp;m=amazon&amp;f=ifr&amp;ref=as_ss_li_til&amp;asins=487311778X&amp;linkId=c0dccca54702015ab35f1069d1354137"></iframe>

<iframe style="width: 120px; height: 240px;" marginwidth="0" marginheight="0" scrolling="no" frameborder="0" src="//rcm-fe.amazon-adsystem.com/e/cm?lt1=_blank&amp;bc1=000000&amp;IS2=1&amp;bg1=FFFFFF&amp;fc1=000000&amp;lc1=0000FF&amp;t=debimate07-22&amp;language=ja_JP&amp;o=9&amp;p=8&amp;l=as4&amp;m=amazon&amp;f=ifr&amp;ref=as_ss_li_til&amp;asins=4048930613&amp;linkId=1efc11536f97c8260129d08159ab2815"></iframe>

入門Python3で網羅的な内容を学べるので、"退屈なことは〜"の方は部分的に蛇足になる可能性があります。"エキスパートPython〜"は、簡単な自動化のレベルでは不要ですが、Pythonスキルを伸ばす上ではオススメ。
