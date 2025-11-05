---
title: "【寄稿】Software Design 2022年6月号 第1特集（第3章 シェルスクリプトの使い方）"
type: post
date: 2022-05-15
categories:
  - "linux"
  - "体験談"
tags:
  - "linux"
  - "体験談"
  - "書籍"
cover:
  image: images/642206.jpg
  alt: "【寄稿】Software Design 2022年6月号 第1特集（第3章 シェルスクリプトの使い方）"
  hidden: false
---

## Software Design誌 2回目の寄稿！

技術評論社の[Software Design 2022年6月号](https://gihyo.jp/magazine/SD/archive/2022/202206) 第1特集 第3章 「シェルスクリプトの使い方」に寄稿する機会をいただきました！2022年1月号に続いて、2回目の寄稿です。表紙がワンちゃんからネコちゃんに戻っています！

![](images/Screenshot-from-2022-05-15-18-57-15.png)

<iframe style="width: 120px; height: 240px;" sandbox="allow-popups allow-scripts allow-modals allow-forms allow-same-origin" marginwidth="0" marginheight="0" scrolling="no" frameborder="0" src="//rcm-fe.amazon-adsystem.com/e/cm?lt1=_blank&amp;bc1=000000&amp;IS2=1&amp;bg1=FFFFFF&amp;fc1=000000&amp;lc1=0000FF&amp;t=debimate07-22&amp;language=ja_JP&amp;o=9&amp;p=8&amp;l=as4&amp;m=amazon&amp;f=ifr&amp;ref=as_ss_li_til&amp;asins=B09Y49MS88&amp;linkId=8996464fb0daeea988a888e7d2a39770"></iframe>

2022年1月号に記事を寄稿した際は、前職から「社名を公開しない方が良い」と言われて所属を隠しました。今回は、現職から社名の公開を許可されたので「[フラー株式会社](https://www.fuller-inc.com/)」とバッチリ記載が入っています。

フラーは、組み込みエンジニア（私）をサーバーサイドとして雇ってくださった稀有な会社です。フルリモートで働ける素晴らしい会社。

## 寄稿のキッカケ

[前回のSoftware Design 2022年1月号](https://debimate.jp/2021/12/17/software-design-2022%e5%b9%b41%e6%9c%88%e5%8f%b7-%e7%ac%ac2%e7%89%b9%e9%9b%86%ef%bc%88%e7%ac%ac1%e7%ab%a0%e3%80%81%e7%ac%ac2%e7%ab%a0%ef%bc%89%e3%81%ab%e5%af%84%e7%a8%bf%e3%80%90%e3%82%ad%e3%83%83/)は、本技術ブログ経由で寄稿依頼をいただきました。

「BashからPythonに乗り換えた方が良い」という趣旨の記事を本技術ブログで書いており、その内容を補強した記事の寄稿を依頼されました。最終的に「Pythonで自動化スクリプト シェルスクリプトもいいけどPythonもね」という記事を寄稿しました（このタイトルは私が決めたものではありません）

今回（2022年6月号）は、「前回の記事を読む限り、シェルスクリプトにも並々ならぬ想いがありそうだった（技術評論社のご担当者様 談）」という事で、また寄稿のお話をいただきました。

前回の記事はPythonを推す内容でしたが、私は「シェルスクリプトを否定したくない、悪者にしたくない」と考えていました。そのため、「シェルは良いツールだ。でも、チーム開発や大規模開発で弱みがある。適材適所でシェルスクリプトかPythonを選択すれば良い」という趣旨の主張を記事に盛り込みました。

その主張が「並々ならぬ想い」として伝わったようです。正直なところ、私はPythonよりシェルスクリプトの方が利用頻度高いので、前回の寄稿では「なぜ私にPython記事の寄稿依頼を？」と感じながら執筆していました。

## 執筆後の感想

まず、執筆期間がタイト（最終的には余裕ありましたけど）。

今回は、前回の21ページよりもページ数が少ない9ページの執筆でした。前回も今回も執筆期間が1ヶ月ぐらい（今回は正確には約25日）。依頼承諾したタイミングは「子供が産まれて1週間しか経ってないけど、本当に締切に間に合うのか」とビクビクしていました。

しかし、最終的には20日（15日で全部書き終え、残り5日で見直し）で書き上げました。余裕を持って原稿を提出できて、安心しました。前職で仕様書を書きまくっていた経験が活きたのかもしれません。

次に、記事の内容はページ数の都合上、消化不良です。

今回は、読者に「最近のシェルスクリプト開発環境」と「安全対策」だけでもシッカリと覚えていただけば良いと考え、割り切って記事を執筆しました。他にも割り切ったポイントがあり、「Visual Studio Codeユーザーのためにプラグイン名を書くけど、Vimmerはつよつよだから自力で環境構築できるでしょ！」と考え、Vim系の情報を省きました。Vimmerを信頼してます。

ページ数があれば、「シェルがどんな役割を持っていて〜」とか「よく使うUnix／Linuxにはcatやgrepなどがあって〜」などを丁寧に説明した事でしょう。しかし、今回は潔く説明しませんでした。書き始めると100ページでも足りないので……

とは言え、結構マニアックな内容もねじ込んでいたりして、中級者以上の人も楽しめるようにしました。バイナリ埋め込みインストーラなんて、皆さん作った事がありますか？経験が無ければ、是非[Software Design 2022年6月号](https://amzn.to/3NbZsmE)をご一読ください！

<blockquote class="twitter-tweet"><p dir="ltr" lang="ja">Software Design 2022年6月号（5月18日発売予定）に、記事を寄稿させていただきました<br><br>第1特集 第3章 シェルスクリプトの使い方<br><br>「シェルスクリプト開発サポートツール紹介」「誤ったファイル削除の防止」「バイナリ埋め込みインストーラ」など、初心者以外の方も楽しめる内容です！ <a href="https://t.co/mfwxwgDZIK">https://t.co/mfwxwgDZIK</a></p>— Nao31@MIN-NIIGATA (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1519163900540850176?ref_src=twsrc%5Etfw">April 27, 2022</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

## 最後に：同人／商業で記事や書籍の執筆を続けたい

私が書いた記事は雑誌として出版され、合計3冊販売されています。技術評論社（および ご担当者様）には感謝の気持で一杯です。こんなに出版されるなんて……自分でも信じられない。

<iframe style="width: 120px; height: 240px;" sandbox="allow-popups allow-scripts allow-modals allow-forms allow-same-origin" marginwidth="0" marginheight="0" scrolling="no" frameborder="0" src="//rcm-fe.amazon-adsystem.com/e/cm?lt1=_blank&amp;bc1=000000&amp;IS2=1&amp;bg1=FFFFFF&amp;fc1=000000&amp;lc1=0000FF&amp;t=debimate07-22&amp;language=ja_JP&amp;o=9&amp;p=8&amp;l=as4&amp;m=amazon&amp;f=ifr&amp;ref=as_ss_li_til&amp;asins=B09NQSQXLZ&amp;linkId=0d7f5819b5fe3701039acd9a219fb8e3"></iframe>

<iframe style="width: 120px; height: 240px;" sandbox="allow-popups allow-scripts allow-modals allow-forms allow-same-origin" marginwidth="0" marginheight="0" scrolling="no" frameborder="0" src="//rcm-fe.amazon-adsystem.com/e/cm?lt1=_blank&amp;bc1=000000&amp;IS2=1&amp;bg1=FFFFFF&amp;fc1=000000&amp;lc1=0000FF&amp;t=debimate07-22&amp;language=ja_JP&amp;o=9&amp;p=8&amp;l=as4&amp;m=amazon&amp;f=ifr&amp;ref=as_ss_li_til&amp;asins=B09TQC63VG&amp;linkId=c819874ac616c3ed21c3f70b941d029f"></iframe>

<iframe style="width: 120px; height: 240px;" sandbox="allow-popups allow-scripts allow-modals allow-forms allow-same-origin" marginwidth="0" marginheight="0" scrolling="no" frameborder="0" src="//rcm-fe.amazon-adsystem.com/e/cm?lt1=_blank&amp;bc1=000000&amp;IS2=1&amp;bg1=FFFFFF&amp;fc1=000000&amp;lc1=0000FF&amp;t=debimate07-22&amp;language=ja_JP&amp;o=9&amp;p=8&amp;l=as4&amp;m=amazon&amp;f=ifr&amp;ref=as_ss_li_til&amp;asins=B09ZTWCZNK&amp;linkId=ecd005546335b44403d008c74f71dc59"></iframe>

記事や書籍を執筆する事は知識の整理に繋がりますし、社会貢献できている感じもするので、今後も続けていこうと考えています。

今まではアウトプットの場として技術ブログをメインにしていました。しかし、ある程度まとまった量の情報を提供したい気持ちが強くなってきたので、[技術書展](https://techbookfest.org/)や[BOOTH](https://booth.pm/ja)などで書籍を執筆しようと考えています。特に、現職で使っているGolangの本を書きたいですね！
