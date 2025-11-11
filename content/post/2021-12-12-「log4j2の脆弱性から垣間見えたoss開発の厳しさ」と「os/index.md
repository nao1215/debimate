---
title: "「Log4j2の脆弱性から垣間見えたOSS開発の厳しさ」と「OSS開発者に投げ銭する文化（未来）」について"
type: post
date: 2021-12-12
categories:
  - "linux"
  - "体験談"
tags:
  - "linux"
  - "oss"
  - "体験談"
  - "金銭"
cover:
  image: "images/dream.jpg"
  alt: "「Log4j2の脆弱性から垣間見えたOSS開発の厳しさ」と「OSS開発者に投げ銭する文化（未来）」について"
  hidden: false
---

### 前書き：災害レベルの脆弱性

本記事は、紛うことなきポエム記事です。Log4j2の脆弱性問題を追っている間に「OSS開発の醜い部分」を目の当たりにしたので、本記事では「せめてOSS開発者が金銭的もしくは他の手段で報われればいいのに」と主張します。

2021年12月10日、Javaのロギングライブラリであるlog4j2は[任意コード実行の脆弱性（CVE-2021-44228、内容は以下の引用文を参照）](https://www.jpcert.or.jp/at/2021/at210050.html)が見つかり、その実行方法の容易さから話題となりました。

> Apache Log4jにはLookupと呼ばれる機能があり、ログとして記録された文字列から、一部の文字列を変数として置換します。その内、JNDI Lookup機能が悪用されると、遠隔の第三者が細工した文字列を送信し、Log4jがログとして記録することで、Log4jはLookupにより指定された通信先もしくは内部パスからjava classファイルを読み込み実行し、結果として任意のコードが実行される可能性があります。
> 
> [JCERT CCより引用](https://www.jpcert.or.jp/at/2021/at210050.html)

![](images/災害.jpg)

Log4j2は有名なライブラリであり、脆弱性の影響範囲が大きかったと思われます。休日出勤で脆弱性対応された方もいらっしゃるのではないでしょうか。

### オープンソースの醜い面

Log4j2およびその開発者は、様々な媒体やSNSで糾弾されている現状です。

そのような中で[Log4j2メンテナの一人であるVolkan Yazıcı氏](https://github.com/vy)は、今回の問題の後に以下のコメントをしています（バグ対応中の様子を詳細に知りたい方は、[コチラのPull Request](https://github.com/apache/logging-log4j2/pull/608)を参照してください）

<blockquote class="twitter-tweet"><p dir="ltr" lang="en">Log4j maintainers have been working sleeplessly on mitigation measures; fixes, docs, CVE, replies to inquiries, etc. Yet nothing is stopping people to bash us, for work we aren't paid for, for a feature we all dislike yet needed to keep due to backward compatibility concerns. <a href="https://t.co/W2u6AcBUM8">https://t.co/W2u6AcBUM8</a></p>— Volkan Yazıcı (@yazicivo) <a href="https://twitter.com/yazicivo/status/1469349956880408583?ref_src=twsrc%5Etfw">December 10, 2021</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

**上記Tweetの意訳**

Log4jメンテナ達は、緩和対策に寝ずに取り組んできました。具体的には修正、ドキュメンテーション、CVE（脆弱性対応）、問い合わせへの返信などです。「無給の作業」や「後方互換性を保つためにメンテナ全員が嫌っている機能の維持」を続ける必要があります。それでも、私達に対して攻撃する人々から守るものは何もありません。

上記Tweetを読んだ時、「一言ぐらいチクリと言いたくなるわな」と思わずにいられませんでした。

そもそも、OSS開発を取り巻く環境は、

- メンテナが善意（≒無給もしくは少ないお金）で開発を継続
- 大半のOSSは見向きもされない（自己満足の世界）
- ロクに貢献もせず、OSSをフリーライドする個人／企業が大半
- 問題が発生した時は、メンテナが口撃／糾弾されてしまう

といった状態が続いています。

モチベーションを保つのが難しい状態の中、今回のlog4j2のように世界的に「あーだこーだ」と言われたら、log4j2メンテナも一言ぐらい反論したくなるよなと。そもそも、脆弱性の原因であるLookup機能は、メンテナから嫌われていた機能であり、後方互換のために残存させていたようです。

### OSS開発で金銭的に報われる未来へ（ポエム）

本題のポエムです。

Log4j2に関する情報収集の中で、海外の方は

- 「Log4j2に関する一連の出来事が自身をOSSから遠ざける理由だ。お金を払わないのに、文句を言う人がいる」
- 「何故、自分たちの使うツールの開発者に少額のお金さえ払えないのか」
- 「労働の対価は愛じゃない」

等、OSS開発と金銭を結びつけた主張をしている方が多数いらっしゃいました。

これらの主張を読む内に「OSSエコシステムの中に、お金の流れも含まれた方が好ましいのではないか」と、ふと思い立ち、本記事（ポエム）を書いています（今回のLog4j2脆弱性問題がお金の力で防げたかどうかは、考えていません）

前々からボンヤリと考えていましたが、OSS開発者へ気軽に投げ銭する文化（と感謝の気持ちを伝える文化）が広がるのがベターかなと。昔は投げ銭に対する抵抗感があったのですが、最近思い直しました。

思い直した理由としては、「[Vim/NeoVimプラグイン作者](https://zenn.dev/shougo/articles/github-sponsors)や[Linux Kernel界隈で有名な方](https://satoru-takeuchi.hatenablog.com/entry/2020/07/22/215403)がGitHub Sponsors有効化を公言した事（GitHub Sponsorsが身近になってきた事）」や「技術記事でお世話になった方へ金銭的な恩返しができる事」が大きいです（あと、月額千円なら懐がそこまで痛くないかな、という考え）

考えているだけでは何も変わらないので、私はPatreonやGitHub SponsorsでOSS開発者を支援（?）し始めました。例えば、2021年は[elementary OS](https://debimate.jp/post/2021-01-09-%E6%8E%A8%E3%81%97%E3%81%AF%E8%AA%B0oss%E9%96%8B%E7%99%BA%E3%82%92%E3%82%B5%E3%83%9D%E3%83%BC%E3%83%88%E3%81%97%E3%81%9F%E3%81%8F%E9%87%91%E9%8A%AD%E7%9A%84/)に寄付しましたし、最近は[Satoru Takeuchi氏](https://github.com/sponsors/satoru-takeuchi)と[skanehira氏](https://github.com/sponsors/skanehira)に対してGitHub Sponsorsを開始しました（少額ですが……）。

「お金を払うのが絶対正義！」という考えでもありません。例えば、OSS開発者が書いている技術ブログの広告をクリックすればお金を払わずに（自分の懐を傷めずに）、感謝の気持ちを表せます。また、御礼の言葉を開発者に直接伝えても良いでしょう。

方法は個々人によって様々だと思いますが、普段お世話になっているOSS開発者に何らかのフィードバックを与える事によって、OSS開発者がモチベーションを高く維持できるのではないかなと思います。そして、小さな活動の一つ一つによって、OSS開発者が少しでも気持ちよく開発できる未来になれば良いなと。

### おまけ：TwitterでOSSとお金について話している方々

「全ての仕事はタダでやるべきだ！」というハッカーも居ましたが、そういう方は割愛しました。

**FreeBSD／EC2プラットフォームメンテナ**

<blockquote class="twitter-tweet"><p dir="ltr" lang="en">Since "open source software maintainers should get paid" is getting lots of attention again: I've been the maintainer of the FreeBSD/EC2 platform for over a decade now, and I'm currently getting $16k/year in sponsorship.</p>— Colin Percival (@cperciva) <a href="https://twitter.com/cperciva/status/1469765310681026564?ref_src=twsrc%5Etfw">December 11, 2021</a></blockquote>

**意訳：**「OSSメンテナは報酬を受け取るべき」という話が再び注目を集めています。私は10年以上FreeBSD／EC2プラットフォームのメンテナを勤めています。そして、私は年間16,000ドルのスポンサーシップを獲得しています。

上記のTweetには続きがあり、ざっくり意訳すると「年間16,000ドルは、殆どのOSS開発者が得る金額より多い。けれども、パートタイムの仕事であることを差し引いても、少ない金額だよね」「だから、[patreon](http://patreon.com/cperciva)でお金を送って」との事。

**Gradle（Javaのビルドツール）メンテナ**

<blockquote class="twitter-tweet"><p dir="ltr" lang="en">It's a bit annoying how folks think that funding OSS would have avoided the log4j problem. It wouldn't. We all write bugs, more important is the process to fix them and how easy it is to upgrade. In this case despite not being paid, log4j maintainers did a great job.</p>— Cédric Champeau (@CedricChampeau) <a href="https://twitter.com/CedricChampeau/status/1470036680543555589?ref_src=twsrc%5Etfw">December 12, 2021</a></blockquote>

**意訳：**OSSに資金提供すればlog4jの問題を回避できたと、人々が考えるのはちょっと厄介です。そうではないと思います。私達は皆、バグを書きます。より重要なのは、バグを修正するプロセスと、アップグレードが簡単にできるかどうかという事です。今回のlog4jのケースでは、無給にも関わらず、log4jメンテナは素晴らしい仕事をしました。

上記のTweetの続きを読むと、「金銭サポートを受けると、”セキュリティ問題を早く直せ”という人が増えるのではないか」という事を懸念しています。報酬を増やすのは賛成だけど、お金をバグ／CVE修正に結び付けないで欲しいと続けています。

後は、「OSS開発者よりも、バグハンターの方が小銭稼いでるぜ！」という意見をしている方がチラホラいました。
