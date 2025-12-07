---
title: "【Golang】2022年に開発した自作CLIコマンド／ライブラリに対する所感と宣伝【OSS】"
type: post
date: 2022-02-05
categories:
  - "linux"
  - "体験談"
tags:
  - "golang"
  - "oss"
cover:
  image: "images/laptop-g6f30a755b_640.jpg"
  alt: "【Golang】2022年に開発した自作CLIコマンド／ライブラリに対する所感と宣伝【OSS】"
  hidden: false
---

### 前書き：Golangでの開発が増えた

最近、Golangで小さいCLIコマンド／ライブラリを書き殴る事が増えました。

その理由としては、環境の変化が大きいです。前職では組み込みエンジニアとして複数言語を使用していましたが、現職ではGolang固定です。Golangを書けば書くほど現職に関係するスキルが上がるので、積極的にGolangを使うようになりました。

（あと、C言語に慣れてた私とGolangは相性が良かった）

CLIコマンドを数個作ったタイミングで、「書き捨てるだけでは勿体ないので、振り返り活動もしたいな」と感じ始めました。何故そのCLIコマンドを作ろうと思ったか、も思い出として忘れないようにしたい気持ちがあります。

で、この手の記事を年末に一気に書くのは辛い。本当に辛い。そこで、年初のうちから本記事に各CLIコマンドに対する所感を記録します。あと、宣伝も兼ねています。興味あったらOSSを使ってください（感想やバグ報告をできればお聞かせください）

---


### Mimixbox：BusyBoxインスパイアコマンド

[MimixBox](https://github.com/nao1215/mimixbox)は、BusyBoxと同じく、シングルバイナリの中にUnixユーティリティコマンドが複数入っているコマンドです。Golangの勉強題材を考えるのが面倒で「Unixコマンドの再実装が楽だな」と考えて、開発を始めました。

開発は、有給消化期間（2021年11月〜12月）に実施。2022年は、軽微な変更のみ。

以下は、開発直後に書いた記事です。

- [MimixBox（BusyBoxインスパイア）の概要、開発時の気づき、PR募集について【Golang学習】](https://debimate.jp/post/2021-11-28-golang%E5%AD%A6%E7%BF%92mimixboxbusybox%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%91%E3%82%A4%E3%82%A2%E3%81%AE%E6%A6%82%E8%A6%81%E9%96%8B%E7%99%BA%E6%99%82/)

MimixBoxは、実装1万\[LOC\]、結合テストも部分的に実施しているなど、気合が入っていたコマンドです。Twitterアカウントを作成し、[Redditで宣伝](https://www.reddit.com/r/golang/comments/rj7e44/mimixbox_mimic_busybox_on_linux/)し、「Pull Requestsを貰って、良いプロジェクトにするぞ！」と気合い入れてました（過去形）

その結果、私のレポジトリの中でStarが一番多く、初めてのPRも来るなど、一定の成果は得られました（2022年2月22日追記：gupコマンドにStar数を抜かれました）。Unixコマンドの実装お作法に関する学びもありました。

**が、失敗プロジェクトだと感じています。**

MimixBoxはUnix哲学に反していて、色んな機能を詰め込もうとし過ぎました。「実装対象のコマンドが多い」、「オプションも多い」、「テスト大変」など、弊害がチラホラ現れました。おかげさまでモチベもだだ下がり。

オリジナルコマンドをMimixBoxに詰め込んだりもしていましたが、別プロジェクトとして管理しようかなと考えている段階です。コントリビュータが多ければ話が違うのでしょうけど、私一人で開発しきれない……

---


### osinfo：OS情報取得ライブラリ

[osinfoライブラリ](https://github.com/nao1215/osinfo)は、[neofetch](https://github.com/dylanaraps/neofetch)と同等の機能を提供しようとしたライブラリです（未完成）。

neofetchは、Linuxディストリ／Unix／Mac／iPhone／iPad／Windowsなどの実行環境に合わせてシステム情報を取得するコマンドです（以下の実行例を参照）

```
$ neofetch
           ./oydmMMMMMMmdyo/.              nao@nao 
        :smMMMMMMMMMMMhs+:++yhs:           ------- 
     `omMMMMMMMMMMMN+`        `odo`        OS: Ubuntu Budgie 21.10 x86_64 
    /NMMMMMMMMMMMMN- `sN/       Host: B450 I AORUS PRO WIFI 
  `hMMMMmhhmMMMMMMh               sMh`     Kernel: 5.13.0-28-generic 
 .mMmo- /yMMMMm`              `MMm.    Uptime: 8 hours, 37 mins 
 mN/       yMMMMMMMd- MMMm    Packages: 3491 (dpkg), 16 (snap) 
oN- oMMMMMMMMMms+//+o+:    :MMMMo   Shell: bash 5.1.8 
m/          +NMMMMMMMMMMMMMMMMm. :NMMMMm   Resolution: 1920x1080, 2560x1080 
M`           .NMMMMMMMMMMMMMMMNodMMMMMMM   DE: Budgie 10.5.3 
M- sMMMMMMMMMMMMMMMMMMMMMMMMM   WM: Mutter(Budgie) 
mm`           mMMMMMMMMMNdhhdNMMMMMMMMMm   Theme: Yaru-dark [GTK2/3] 
oMm/        .dMMMMMMMMh:      :dMMMMMMMo   Icons: ubuntu-mono-dark [GTK2/3] 
 mMMNyo/:/sdMMMMMMMMM+          sMMMMMm    Terminal: gnome-terminal 
 .mMMMMMMMMMMMMMMMMMs           `NMMMm.    CPU: AMD Ryzen 5 3400G (8) @ 3.700GH 
  `hMMMMMMMMMMM.oo+.            `MMMh`     GPU: AMD ATI 09:00.0 Picasso 
    /NMMMMMMMMMo                sMN/       Memory: 8668MiB / 30032MiB 
     `omMMMMMMMMy.            :dmo`
        :smMMMMMMMh+-`   `.:ohs:                                   
           ./oydmMMMMMMdhyo/.                                      

```

osinfoライブラリは、前述のMimixBoxにneofetch（golang実装）を組み込むために開発を始めました。[neofetchのコード自体は一度読んだ事があった](https://debimate.jp/post/2019-01-22-%E3%82%B3%E3%83%BC%E3%83%89%E3%83%AA%E3%83%BC%E3%83%87%E3%82%A3%E3%83%B3%E3%82%B0bash%E3%82%B7%E3%82%B9%E3%83%86%E3%83%A0%E6%83%85%E5%A0%B1%E8%A1%A8%E7%A4%BA%E3%83%84%E3%83%BC%E3%83%ABneo/)ので「すぐに実装できるだろう」と安易に考えていました。

しかし、ディストリごとに泥臭く設定ファイルを確認したり、Mac／Winにしか存在しないシステムコマンドを叩いたり、忍耐の居る作業が続く事に途中で気づきました。致命的な問題点は、BSDやWindows、マイナーLinuxディストリなどのテスト環境が確保できない点でした。

えっ、そんな事は実装する前に分かるだろうって？私は勢いで開発している(๑•̀ㅁ•́๑)✧

で、前述したMimixBox開発のモチベダウンも影響して、osinfoライブラリは実装完了する事なく幕を閉じました。このライブラリは、リポジトリごと削除する可能性が高いですね。

---


### ubume：プロジェクトテンプレート生成コマンド

[ubume](https://github.com/nao1215/mkgoprj)は、Golangでプロジェクトを作る際に「何度も何度も同じようなファイルを作るの怠いな」と感じて、数時間で実装しました。実装中は、[gradle（Java）](http://gradle.monochromeroad.com/docs/)や[valdo（Vala）](https://github.com/Prince781/valdo)のようなジェネレータをイメージしてました。

- [【Golang】プロジェクトテンプレート生成ツール（ubume）を試作【改善案を募集】](https://debimate.jp/post/2022-01-11-golang%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E3%83%86%E3%83%B3%E3%83%97%E3%83%AC%E3%83%BC%E3%83%88%E7%94%9F%E6%88%90%E3%83%84%E3%83%BC%E3%83%ABubume/)

ubumeは、個人的には便利なコマンドですし、毎日150cloneぐらいはされているので、そこそこ需要を満たせているのかなと感じています。私は頻繁に使うので、ちょこちょこ機能追加してます。

ただ、失敗したな、と感じている点が2つあります。

- ubume（[姑獲鳥](https://kotobank.jp/word/%E5%A7%91%E7%8D%B2%E9%B3%A5-1757610#:~:text=%E3%81%93%E3%81%8B%E3%81%8F%E2%80%90%E3%81%A1%E3%82%87%E3%81%86%20%E3%82%B3%E3%82%AF%E3%83%AE%E3%82%AF%E3%83%86%E3%82%A6%E3%80%90%E5%A7%91,%E7%94%A3%E5%A5%B3\(%E3%81%86%E3%81%B6%E3%82%81\)%E3%80%82)）という名称は、子供に害をなす妖怪から考えた事
- 設計がプロジェクトテンプレート種類の増加に耐えられない事

1つ目（命名ミス）に関しては、プロジェクトを子供に見立てて「子供（出産）に関係する神様探そう！」と考え、良いのが見つからず、パッと思いついた"姑獲鳥 (ubume)"を採用しました。[京極夏彦](https://amzn.to/3Hw0mbi)、好きなんです。でも意味が悪かった。かなり後悔しています。

2つ目（設計ミス）に関しては、今でも解決方法が思い浮かばず。プロジェクトの種類（例：ライブラリ、web用、複数コマンドが同居など）が増えると、生成すべきディレクトリ構成が変わります。ubumeは、それらの構成（PATH情報、ディレクトリ名／ファイル名、ファイル内容）を一つ一つコードにベタ書きしています。

**分かりやすく言うと、if文がメチャメチャ多い**。一回リファクタしていますが、それでも設計に問題があるので、どこかで手を打ちたい。

2022年4月19日追記：ubumeからmkgoprojヘリネームしました。ちょこちょこ機能追加を続けていて、mkgoprjで作ったCLIコマンドは自動でシェル補完（\[TAB\]入力による補完）が効くようになってます（以下の記事の対応が入ってます）

- [【Golang】spf13/cobraが提供する入力補完（shell completion）をファイル形式でインストールする方法【bash, zsh, fish】](https://debimate.jp/post/2022-04-17-golangspf13-cobra%E3%81%8C%E6%8F%90%E4%BE%9B%E3%81%99%E3%82%8B%E5%85%A5%E5%8A%9B%E8%A3%9C%E5%AE%8Cshell-completion%E3%82%92%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB/)

---


### gal：AUTHORファイル生成コマンド

[gal（ギャル）](https://github.com/nao1215/gal)は、MimixBox開発中にパッと作りました。

MimixBoxにコントリビュートしてくださった方が居たので、AUTHORS.mdを作成する必要性が出ました。AUTHORS.mdを手動作成すると、そのうち記載が漏れそうだったのでgalを実装しました（当時は、コントリビュータが増える前提で考えていました）。

galの実装は、シンプルです。

コミットログからユーザ名とユーザメールアドレスを抽出し、抽出した情報（行）から重複行を削除し、最後にアルファベット順にユーザ情報をAUTHORS.mdに書き込んでいます。内部でgitコマンドを実行するため、svnなどでバージョン管理しているプロジェクトには対応していません。

2022年2月に機能追加を行い、「コミット数の降順（コミット数の多いユーザが先頭に来る並べ方）」もしくは「修正行数の降順（修正量が多いユーザが先頭に来る並べ方）」を追加しました。個人的には、もう追加したい機能がないので開発終了。

余談ですが、「次は自動でChangelog.mdを生成だ！」と考えていたら、[git-chglog](https://blog.wadackel.me/2018/git-chglog/)が存在していて出鼻をくじかれました。

---


### speaker：テキスト音声読み上げ（時報機能付き）

[speaker](https://github.com/nao1215/speaker)は、会社の時報をリモートワーク環境で再現するために作成したコマンドです。

私の会社では、コアタイムの開始／終了、定時付近に時報が流れます。なお、この時報は、Raspberry PiとGoogle Homeを用いたお手製です（雑に聴いた話なので、詳しい仕様は把握していない）

残念な事に「暫くフルリモートにします」とお達しが出て、時報を聴けなくなりました。そこで、時報コマンド（speaker）を実装して、会社の時報（例：ｷｮｳﾓｼﾞｭﾝﾁｮｳ ｱｼﾀﾓｼﾞｭﾝﾁｮｳ）を再現する事にしました。

speakerは、主機能が3つあります。

- テキストを音声読み上げする機能
- 時報機能（cron設定ファイルに指定時刻で音声読み上げする設定を追記）
- 登録した時報を削除する機能

テキストto音声の部分は、外部ライブラリ（[hegedustibor/htgo-tts](https://github.com/hegedustibor/htgo-tts)）を使用しました。外部ライブラリは、GoogleのAPIを用いてテキストをmp3ファイルに変換しています。mp3再生には、[faiface/beep](https://github.com/faiface/beep)を利用しました。cron設定ファイルにアクセスするライブラリは見当たらなかったので、自作しました（地味にプラットフォーム間の差異があった）

speakerには、致命バグと仕様不備があります。

- Linux環境で時報が再生されない（Mac環境では時報は動く）
- 条件は不明だが、長いテキストはmp3に変換できない
- Zoomミーティング中に時報が流れてしまう（時報をスキップできない）

Linux環境では、cronを経由してしまうと音声が再生されないバグがあります。Terminalからspeakerを実行した場合は音声が流れます。ただ、「会社の時報を"Mac環境"で再現する」という目的は果たしているので、修正するモチベが無いです。

余談ですが、speakerを公開して数時間で「翻訳機能をつけてくれ！」と要望がきましたが、「嫌だ」と突っぱねました。気軽に面倒な事を言われても対応できないよ……（若い時は対応したかもしれない）

---


### subaru：fortuneインスパイアコマンド

[subaru](https://github.com/nao1215/subaru)は、[go:embed機能（バイナリへのファイル埋め込み）](https://pkg.go.dev/embed)と[エキスパートたちのGo言語](https://amzn.to/3rpcZPM)（書籍）で学んだ内容をアウトプットするために作りました。ジョークコマンドの一種です。

- [【Golang】go:embedを用いて格言表示コマンド（subaru）を開発](https://debimate.jp/post/2022-02-05-golanggoembed%E3%82%92%E7%94%A8%E3%81%84%E3%81%A6%E6%A0%BC%E8%A8%80%E8%A1%A8%E7%A4%BA%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89subaru%E3%82%92%E9%96%8B%E7%99%BA/)

元ネタの[fortuneコマンド](https://ja.wikipedia.org/wiki/Fortune_\(UNIX\))は、アメリカのフォーチュンクッキー（格言が書かれた紙が入ったクッキー）を模したコマンドです。コードを読んでいないのですが、格言はテキストファイルに書かれているらしいです。subaruも同じ方針を採用しました。

Golangでは、go installコマンドを用いてバイナリをインストールする方法が人気です。この方法は、ひと手間を加えないと外部ファイル（格言が書かれたテキストファイル）をシステムにインストールできません。この課題を解決するために、subaruではgo:embed機能を使用しています。実装の詳細は、上記の記事に記載しています。興味がある方はご覧ください。

subaruの裏テーマは、PRを沢山貰う事です。私は色んな方が参加してOSSをより良くする姿に憧れがあります（その割には他の人のOSSにコントリビュートしていませんが…）。そのため、格言の追加に伴うコード修正が発生しないような設計にしました。

「PRした事ないな」という方がいらっしゃれば、是非PRの練習台に[subaruコマンド](https://github.com/nao1215/subaru)を使用してください。

---


### goavl：goa framework linter

[goavl](https://github.com/nao1215/goavl)は、[goa framework version 1.x](https://github.com/shogo82148/goa-v1)用のlinterです。

- [【Golang】goa（ver 1.x）frameworkのlinter（goavl）を試作【go/astを利用】](https://debimate.jp/post/2022-02-11-golanggoaver-1-xframework%E3%81%AElintergoavl%E3%82%92%E8%A9%A6%E4%BD%9Cgo-ast%E3%82%92%E5%88%A9%E7%94%A8/)

goaは、DSLからgolangソースコードを生成するツールです。私は2022年にgoaとお友達になったのですが、goaはツレナイ子でした。具体的には、DSL文法エラーメッセージが非常に簡素でした。その結果、「DSLの書き方が悪いのは分かるが、どこに問題があるのかが検討もつかない」という状態に陥る事が何回かありました。

goaに冷たくされるという課題の解決として、私はlinterの作成を思いつきました。

しかし、golang用linterのプラグインとしてgoa linterを作ってもマージされる可能性が低く、goa本体への導入も面倒でした。さらに言えば、会社では諸般の事情で公式のgoaを用いず、フォーク版を使っている事が話をさらに面倒臭くしていました。

そこで、完全自前でlinterを作成する運びとしました。休日を一日潰して作りました。goavlは、以下の画像で示すように、「指摘箇所（ファイル、行数）」と「直し方」を出力してくれます。あとは、「チェック項目の追加」と「Visual Studio Code」との連携ができれば完璧ですかね。

![](images/Screenshot-from-2022-02-11-23-46-32.png)

---


### gup：$GOPATH/bin以下のバイナリ一括更新

[gup](https://github.com/nao1215/gup)は、"$ go install"で$GOPATH/bin以下にインストールしたバイナリを最新版に更新するコマンドです。以下の記事は開発直後の内容であり、最新の仕様は[Zenn](https://zenn.dev/nao1215/articles/aef3fe318848d6)で公開しています。

- [【Golang】go installで取得した$GOPATH/bin以下のバイナリを一括更新するgupコマンドを試作](https://debimate.jp/post/2022-02-20-golanggo-install%E3%81%A7%E5%8F%96%E5%BE%97%E3%81%97%E3%81%9Fgopath-bin%E4%BB%A5%E4%B8%8B%E3%81%AE%E3%83%90%E3%82%A4%E3%83%8A%E3%83%AA%E3%82%92%E4%B8%80%E6%8B%AC%E6%9B%B4%E6%96%B0/)

gupのイメージは、"brew upgrade"や"apt upgrade"です。初期仕様では、シェルのコマンド履歴を解析したり、ユーザーに手動設定を求める仕様であり、少し微妙な感じでした。

今現在は、"$ go version -m"から必要な情報を取得する設計に変更しており、完全自動で$GOPATH/bin以下のバイナリを更新できるようになりました。ヒントを下さった[@shogo82148](https://twitter.com/shogo82148)氏に感謝しています。この方は何でも知っています。

で、仕様を変更した瞬間に、急にStar数がバンバン増え始めました（Redditで宣伝もしたけどさ…）。

<blockquote class="twitter-tweet" data-dnt="true"><p dir="ltr" lang="ja">なんだろう、1.5ヶ月かけて作ったOSS（画像の上側）のStar数を一日で抜くの止めてもらっていいですか？<br><br>golangのバイナリをアップデートするだけのgupコマンドが、ここまで伸びるとは思わなかった。<br>gup（<a href="https://t.co/gvTIlaoh9Q">https://t.co/gvTIlaoh9Q</a>）はシェルでも作れるレベルなのに……OSS良く分からん。 <a href="https://t.co/wVCKmG9TN5">pic.twitter.com/wVCKmG9TN5</a></p>— Nao31 (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1496093095641124865?ref_src=twsrc%5Etfw">February 22, 2022</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

何もしなくてもPull Requestが来たので、「この機会を逃してはいけない！」と考え、機能追加を沢山しました。今は、一括アップデート、指定コマンドのみのアップデート、dry run、$GOPATH/bin（$GOBIN）にインストール済みコマンドリストの表示など、追加済みです。

何やかんやで、gupは公開から一週間でStarを50個も集めてしまったので、今後作るOSSは「打倒 gup！」という目標を掲げていきます。

---


### nameconv：命名規則を変更するライブラリ

[nameconv](https://github.com/nao1215/nameconv)は、文字列の命名規則を変更したり、文字列の命名規則が何か（例：スネークケース or not）を判定するためのライブラリです。文字列のパースをする人は、使用する可能性があるライブラリ。

nameconvは、私がフルスクラッチで作成したライブラリではなく、[casee（作者：pinzolo氏）](https://github.com/pinzolo/casee)と[camelcase（作者：fatih氏）](https://github.com/fatih/camelcase)をフォーク（かつマージ）しています。フォーク元との差異は、「テストやAPI修正／追加」と「[ドキュメント整備](https://pkg.go.dev/github.com/nao1215/nameconv)」です。

nameconvは、前述の[goavl](https://github.com/nao1215/goavl)やCSVファイル操作コマンド（構想段階）で、必要な機能（文字列変換）を提供します。2つのコマンドで使用する機能のため、ライブラリ化しました。

フォーク元を使わなかった理由は、「フォーク元の更新が年単位で止まっている事」と「修正したい箇所があった事」です。Pull Requestを出してもマージされないかな、という判断をしました。

少し予定が狂った所は、caseeの更新が再開された事です。何故、このタイミングで……

---


### posixer：POSIXコマンドのインストール有無をチェック

[posixer](https://github.com/nao1215/posixer)は、[POSIX](http://get.posixcertified.ieee.org/)（UNIX系OS間での移植性を高めるための標準規格）で定められたコマンドがシステムにインストールされているかどうかを返すコマンドです。POSIXについて調査する機会があり、「こんな読みづらいIEEEのドキュメントをイチイチ見てられないぞ」と思い、2時間ぐらいで開発しました。

名前は、今後POSIXに関係する機能を詰め込む可能性があるので、"POSIX" + "インターフェース的な名称（〜er）"としています。少し強気な名称だと思ってます。

POSIXコマンドは全160個あり、大別して3種類に分けられます。具体的には、「シェルビルトインコマンド」「POSIXシステムに必須なコマンド」「オプショナルなコマンド」の3種類です。posixerは、これらのPOSIXコマンドリストを表示するlistサブコマンド、システムにPOSIXコマンドがインストール済みかどうかをチェックするcheckサブコマンドを提供します。

以下、checkサブコマンドの実行例です。

```
$ posixer check
+------------+----------------+----------------+
|    NAME    |      TYPE      | IN YOUR SYSTEM |
+------------+----------------+----------------+
| alias      | shell built-in | installed      |
| bg         | shell built-in | installed      |
| cd         | shell built-in | installed      |
   :
   :
| wait       | shell built-in | installed      |
| ar         | required       | installed      |
| at         | required       | installed      |
   :
   :
| mesg       | required       | installed      |
| sact       | optional       | not installed  |
   :
   :
| what       | optional       | not installed  |
| yacc       | optional       | installed      |
| zcat       | optional       | installed      |
+------------+----------------+----------------+
```

結果を表で出力している理由は、[olekukonko/tablewriter](https://github.com/olekukonko/tablewriter)を使いたかったからです。作ったは良いけど、こんなコマンドは自分でも要らない（使うタイミングが殆どない）と思ってます。

---


### contributor：コントリビュータリストを表示

[contributor](https://github.com/nao1215/contributor)は、コードもしくはドキュメントを修正した人のリストを表示するコマンドです。gitで管理しているプロジェクトのみ対応しています。1時間ぐらいでガッと作りました。

contributorを作成したキッカケは、「このリポジトリでどれぐらいコードを修正したかな」と思う機会が多々あり、その度に複雑なgitコマンドをタイピングするのが苦痛だった事です。この程度はシェルで作れますが、前述のgalコマンド（AUTHORSファイル生成コマンド）を再利用すれば簡単に作れると気づいたため、golangで実装しました。

リリース後に、デフォルトブランチ名がmasterの場合は修正行数が0になるバグに遭遇しましたが、それ以外は特に問題が見つかっていません。

以下、contributorコマンドの実行例です。

```
$ contributor 
+-------------------------+-----------------------------------------------------------+-----------+-----------+
|          NAME           |                           EMAIL                           | +(APPEND) | -(DELETE) |
+-------------------------+-----------------------------------------------------------+-----------+-----------+
| Ichinose Shogo          | shogo82148@gmail.com                                      |     11042 |      6044 |
| Daisuke Maki            | lestrrat+github@gmail.com                                 |       866 |       223 |
| Songmu                  | y.songmu@gmail.com                                        |       237 |        65 |
| Stefan Tudose           | stefan.tudose@data4life.care                              |        14 |        12 |
| mattn                   | mattn.jp@gmail.com                                        |         9 |         9 |
| yusuke-enomoto          | yusuke.enomoto@dena.com                                   |         8 |         6 |
| pyros2097               | pyros2097@gmail.com                                       |         3 |         1 |
| catatsuy                | catatsuy@catatsuy.org                                     |         2 |         2 |
| Shoma Okamoto           | 32533860+shmokmt@users.noreply.github.com                 |         1 |         1 |
| nasa9084                | nasa.9084.bassclarinet@gmail.com                          |         1 |         1 |
| dependabot-preview[bot] | 27856297+dependabot-preview[bot]@users.noreply.github.com |         0 |         0 |
+-------------------------+-----------------------------------------------------------+-----------+-----------+
```

---


###  sqly：CSVに対してSQLを実行するCLI

2022年の集大成。DDDを採用したり、SQLiteを利用したりと、サーバーサイドで得た知見を活かしています。

- [【Golang】CSV／TSV／LTSV／JSONにSQLを実行するsqlyコマンドを作った話【開発背景／設計／使い方】](https://debimate.jp/post/2022-12-02-golangcsvtsvltsvjson%E3%81%ABsql%E3%82%92%E5%AE%9F%E8%A1%8C%E3%81%99%E3%82%8Bsqly%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89%E3%82%92%E4%BD%9C%E3%81%A3%E3%81%9F/)

---


### CLIコマンド作成時に参考にした情報

- [UNIXという考え方〜その設計思想と哲学〜](https://amzn.to/3Gt5ZWu)
- [コマンドラインツールについて語るときに僕の語ること / Taichi Nakashima](https://www.youtube.com/watch?v=M8jfKWvz15A&t=1077s)
- [Readme Driven Development](https://tom.preston-werner.com/2010/08/23/readme-driven-development.html)

---


### 最後に：本記事は2022年の間、適宜更新されます

まだ2022年2月ですが、CLIコマンドを結構作ったなと感じています（追記：2022年4月時点で4万5千\[LOC\]も実装していました、ビックリ）

ただ、機能が小粒かつ魅力に乏しい感じがしています。実装規模も1〜3時間程度で書き上げられる内容ばかりです。様々な方に使っていただけるOSSを作りたいけど、アイデアがない現状。
