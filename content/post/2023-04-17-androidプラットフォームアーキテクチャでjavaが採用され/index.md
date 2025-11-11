---
title: "AndroidプラットフォームアーキテクチャでJavaが採用されている理由は、エンジニア人口が多いから"
type: post
date: 2023-04-17
categories:
  - "linux"
tags:
  - "android"
cover:
  image: "images/android-stack_2x-695x1024.png"
  alt: "AndroidプラットフォームアーキテクチャでJavaが採用されている理由は、エンジニア人口が多いから"
  hidden: false
---

### 前書き：何故AndroidはC/C++がメインではないのか

AndroidでJavaを採用した理由が気になって夜しか眠れなかったので、調べました。

まず、前提をおさらいします。Androidプラットフォームは、ハードウェアを制御するためにLinux Kernelを採用しています。その上にハードウェアを抽象化するためのHALレイヤーがあり、C／C++とJavaランタイム（Android Runtime）がHALの上にあります。[最近では、NativeライブラリにRustも採用され始めた](https://forest.watch.impress.co.jp/docs/news/1462573.html)と聞いています。

そして、Java API Framework（Oracle Javaとは別物）がAndroidのコアな機能を提供する形になっています。私達がAndroidアプリを開発する場合は、JavaやKotlinでJava API Frameworkを呼び出す形になっています。

\[caption id="attachment\_8352" align="aligncenter" width="523"\]![](images/android-stack_2x-695x1024.png) Android公式ドキュメント：プラットフォーム アーキテクチャより引用\[/caption\] 

組み込みLinuxの流れで考えると、「何故、全てC／C++で書かなかったのか」「Android 1.0開発当初（2005年〜2008年）は、組み込み環境が貧弱なのでJavaで書くと遅かったのではないか」と疑問に感じました。

### Javaを採用した理由は訴訟で語られていた

答えは意外なところで語られていました。

GoogleとOracleとJava著作権侵害訴訟（[GoogleがOracleのJava SE APIを1万1500行コピーしてAndroidに使用したため起きた訴訟](https://project.nikkeibp.co.jp/idg/atcl/19/00002/00205/)）で、[Andy Rubin氏](https://ja.wikipedia.org/wiki/%E3%82%A2%E3%83%B3%E3%83%87%E3%82%A3%E3%83%BB%E3%83%AB%E3%83%BC%E3%83%93%E3%83%B3)が証人として次のようなことを語っていました。

> When prompted by Google counsel Robert Van Nest if there were other programming languages that could have worked for Android, Rubin affirmed there could have been. Some of the other languages considered for Android were Javascript, Python and Lua.
> 
> Nevertheless, describing his experience from his first startup, Danger, Rubin highlighted the benefits of using Java for a smartphone -- primarily the well-known brand name as well as compatibility being that it is a common language taught at universities worldwide.
> 
> Googleの顧問弁護士であるロバート・ヴァン・ネストから、Androidで使えるプログラミング言語が他にあったかと尋ねた。ルービンは、「あったかもしれない」と肯定した。Android用に検討された他の言語には、**Javascript、Python、Lua**がある。
> 
> しかし、ルービンは最初の起業であるDangerでの経験を語りながら、スマートフォンにJavaを使うことの利点を次のように強調した。Javaは、世界中の大学で教えられている共通言語であり、知名度の高さで知られている
> 
> 引用元：[Trial: Android chief on why Java was picked for Android](https://www.zdnet.com/google-amp/article/trial-android-chief-on-why-java-was-picked-for-android/)

上記の文章を読む限り、実行速度よりもエンジニア人口を優先したように読み取れます。他のプログラミング言語候補が、JavascriptやPython、Luaのようなスクリプト言語だったことにも驚きです。遅そう。

私なら、Linux Kernelを採用した段階で「GUIにはQtかGTKやな！」と考えると思いますが、優れたエンジニアはそんな甘いことは考えないのですね

<blockquote class="twitter-tweet"><p dir="ltr" lang="ja">AndroidがJavaを採用した理由は、Javaが世界中の大学で学べ、知名度があったかららしい。Linux Kernelが下にいると、GUIはC++でQtやGTKを動かすのが順当だと考えてしまうが、そもそもガラケーもJava MEを採用してるケースがあったのね。<br><br>00年代のソフト事情を知らないから、歴史を紐解くと面白い</p>— nchika@Database Removal Newbie (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1647646365059784704?ref_src=twsrc%5Etfw">April 16, 2023</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

### おまけ：ガラケーはどんな世界だったのか

この段落は、全て推測で書いています。

私が高校生の頃（2006年ぐらい）は、まだiPhoneがありませんでした。ガラケーがガラケーと呼ばれていなかった時代です。ガラパゴスと揶揄されることもなく、ケータイ（movaとかFOMA）と呼ばれていました。

今思えば、ガラケーのOS事情はどのようになっていたのか。今更ながら疑問が芽生えました。

<blockquote class="twitter-tweet" data-conversation="none"><p dir="ltr" lang="ja">今思えば、2005年ぐらいのガラケーは、各社で異なるOSを搭載してたのだろうか<br><br>国産機種でSymbianを搭載したと思えないので、Tron系か独自RTOSを載せていた？少なくとも組み込みLinux Kernelが載るだけのパワーがあったとは思えない<br><br>独自OSの上で内製ライブラリを動かしながら開発だと…面倒そうだ</p>— nchika@Database Removal Newbie (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1647800191226097665?ref_src=twsrc%5Etfw">April 17, 2023</a></blockquote>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

「日本製のOSといえばTRONだろ」と雑に調べると、WikipediaにTRON系がガラケーに採用されていた旨の記載がありました（ソースがWikipediaという恥ずかしさ）

> 一般消費者の見えるところのOS、つまりGUIを搭載したOSとしては、2000年代前半から後半にかけて日本で普及した高機能携帯電話（ガラケー）のOSとして広く使われていた。
> 
> 引用元：[ITRON](https://ja.wikipedia.org/wiki/ITRON)

ITRONでは開発が厳しかったのか、[2000年代後半からは汎用OSとして、Symbian OSや組み込みLinuxが採用されていた](https://www.itmedia.co.jp/mobile/0312/03/n_linux.html)ようです。SymbianはNokiaが開発していたOSであり、2010年ぐらいにシェアトップだったらしいです。C++、Python、Java MEを使える環境でしたが、規制か法律の影響で確認ダイアログをウザいぐらい出していると[書籍](https://www.amazon.co.jp/%EF%BC%AE%EF%BC%AF%EF%BC%AB%EF%BC%A9%EF%BC%A1-%E5%BE%A9%E6%B4%BB%E3%81%AE%E8%BB%8C%E8%B7%A1-%E3%83%AA%E3%82%B9%E3%83%88-%E3%82%B7%E3%83%A9%E3%82%B9%E3%83%9E-ebook/dp/B07TWP8JPL?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&crid=1R4TI10F54CM3&keywords=Nokia&qid=1681743283&s=books&sprefix=nokia%2Cstripbooks%2C193&sr=1-1&linkCode=ll1&tag=debimate07-22&linkId=babff804821bdd8b777bb87b87a53ebe&language=ja_JP&ref_=as_li_ss_tl)に書かれていました（記憶違いがあるかもしれない）

組み込みLinuxはKernelがチューニングされていると言えど基本的にはLinuxですから、端末性能に合わせたrootfsを何パターンか用意して、各社お好みでライブラリをインストールしてカスタマイズしてくださいという感じだったのだろうと推測してます。BuildrootやYoctoで自分好みのLinuxを作っていたと思われます。

Symbianにしても組み込みLinuxにしても、各社の内製ライブラリが外部に公開されることが少なかったでしょうから、AndroidやiOSを開発するよりも実装量が多かったのではないかと思われます。

思い返せば、ガラケー時代は１社で年に数台の新機種ケータイをリリースしていた訳ですから、「さぞかし開発現場は修羅場であっただろう」と容易に想像できてしまう。大企業のことだからファームもミドルもアプリも外注して、短い開発期間で下請け業者が悲鳴を上げていたのではないかと（名高いYRP野比とガラケーは関係があった気がします。調べないけど）

### 最後に

自分が大学生の頃は、「Javaと英語をやっておけばエンジニアとして食いっぱぐれない」と聞いた記憶があります。しかし、その10年後の2023年現在、Javaと英語だけで生き残れるのかが怪しい時代になってきました。エンジニア業界は怖いところです。
