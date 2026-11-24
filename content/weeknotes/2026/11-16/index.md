---
title: "2026/11/16週"
date: 2026-11-16T00:00:00+09:00
---

#### Goアプリのシークレット漏洩対策ライブラリ開発でミスった

「Go アプリがパニックした時のログで、キチンとシークレットをマスクできるか？」

{{< figure src="embargo-gopher.webp" alt="ログへ流れる紙に鍵が載っており、Gopher が [embargoed] の判子を押して止めている" caption="原作：[The Go Gopher](https://go.dev/blog/gopher) — Renée French、[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。" width="600" align="center" >}}

パニック時のメッセージが stderr を経由してログ収集基盤へ流れてしまうのではないか。この疑問から nao1215/embargo というライブラリを作ったが、競合に勝てるだけの魅力がなかった。値を Secret 型で包んで表示をマスクする方式は、一般的すぎた。競合ライブラリと比較して、強い機能差異が作り出せなかった（注：テスト周りの機能は充実させていたが、それだけでは弱かった）。

そこで、以前開発した nao1215/sensitive を [embargo](https://github.com/nao1215/embargo) にリネームし、今回作った機能を統合した。[sensitive は、テキストからクレジットカード番号などを検出してマスクするライブラリ](/post/ja/2026-02-08-sensitiveライブラリを作った話/)である。シークレットを探索するライブラリに、明示的に指定したシークレットが漏洩しないようにする機能を足した形だ。競合に負けないように、テストや設計、性能計測を突き詰めている最中だ。

<br>

ちなみに embargo は、報道の世界で使われる単語であり、解禁日時まで情報を外に出さない取り決めを指す。シークレットを外へ出さないという意味に使えて、さらに go で終わる。sensitive より好ましいので、リネームした。

完全に下ネタだが、「私達は LLM のコンドーム」という発言を最近聞いたので、真っ先に gondom（go + condom）が思い浮かんだ。意味的には完璧だった。漏れてはいけないもので、漏れても一発で終わるわけではない。しかし、重大な事態に繋がる。使えば安心。シークレット漏洩と、もう一つの漏洩。近しいものがある。

採用する勇気がなかった。

----

#### 情報漏洩。明日は我が身。

情報漏洩が発生し続けている。最近では、[楽天証券がテスト環境から顧客情報を漏らした](https://www.itmedia.co.jp/news/article/2611/18/2000003302/)。擁護するわけではないが、氏名や住所、電話番号、メールアドレスなどは鬼門なので、本番相当データが欲しくなる気持ちは理解できる。氏名が URL だったり、ミドルネームがあったり、絵文字や外字が含まれていたりと、考慮しなければならないことが多すぎる。個人情報は、綺麗なデータではない。それでも、社内手続きをした上で 1000 万口座以上の顧客データをテスト環境に置くのは、理解できなかった。

簡単に扱えるダミーデータがあれば、今回の問題は起きなかったかもしれない。Go では、[gofakeit](https://github.com/brianvoe/gofakeit) のようなダミーデータ生成ツールがあるが、残念ながら日本語の氏名や住所に対応していない。この辺は、国がツールを提供すべきではないかと思う（[住所のデータは公開されている](https://www.digital.go.jp/policies/base_registry_address)）。

{{< figure src="gofakeit-logo.webp" link="https://github.com/brianvoe/gofakeit" alt="Gofakeit のロゴ" caption="Gofakeit：Go 向けのダミーデータ生成ツール<br>出典：[GitHub](https://github.com/brianvoe/gofakeit)（2026年11月18日取得）" width="600" align="center" >}}

ユーザー視点では、退会処理をしたら個人情報の物理削除を必須とする法律、もしくは情報漏洩を厳しく罰する法律が欲しい。今は、セキュリティ対策を真面目に実施するより、情報漏洩した方が企業視点で割安なように感じられる。一定のセキュリティ基準を強制する社会的ルールが必要だ。しかし、私はエンジニア。ここまでの意見は、全てブーメラン発言🪃となる。従来どおりに実装していると、攻撃者に負ける。そんな危機感から、[nao1215/embargo](https://github.com/nao1215/embargo)（マスキングライブラリ）が生まれたりしている。

漏洩を防ぐ技術を追うなら、Rust 界隈は暗号・セキュリティに強く、面白い。「何を食べたら、こんなロジックを思いつくんだ？（例：ゼロ知識証明）」と感心する OSS に出会うことが多い。来年あたりは、Rust に傾倒していくかもしれない。

---

#### Awesome Go/Ebitengineにembargo,gozenが掲載された

[Awesome Go に embargo](https://github.com/avelino/awesome-go/pull/6907), [Awesome Ebitengine に gozen](https://github.com/sedyh/awesome-ebitengine/pull/83)が掲載された。殆ど Star が付いていないが、内容で評価されたようで安心した。なお、この裏で GitHub Sponsors が1名減っており、悲しい。

{{< figure src="awesome-embargo-gozen.webp" alt="embargo と gozen の OGP 画像を斜めの線で区切って並べたもの" caption="左：embargo、右：gozen（各リポジトリの OGP 画像）" width="600" align="center" >}}

Awesome 系に登録された OSS は、6件だ。[gup](https://github.com/nao1215/gup), [filesql](https://github.com/nao1215/filesql), [sqly](https://github.com/nao1215/sqly), [markdown](https://github.com/nao1215/markdown), [embargo](https://github.com/nao1215/embargo), [gozen](https://github.com/nao1215/gozen)。gup だけが毎年安定して Star を獲得している。

{{< figure src="awesome-star-history.webp" alt="Awesome 系に掲載された 6 個の OSS の GitHub Star 数の推移。2026 年 11 月 19 日時点で gup 629、filesql 388、sqly 197、markdown 146、gozen 4、embargo 3" caption="Awesome 系に掲載された OSS の Star History（2026 年 11 月 19 日時点、[action-readme-showcase](https://github.com/nao1215/action-readme-showcase) で生成）" width="800" align="center" >}}

Star 数の少ない embargo や gozen の方がガチガチに作り込んである。私の経験が後発 OSS に活かされている。ちなみに、2026年は40個以上のパブリック OSS を作ったが、その中の2個が awesome 行きだった。3個目（[atago](https://github.com/nao1215/atago)）を狙っているけど、果たして Approve は得られるだろうか。

----

#### ゾルトラークとなった時のオカリナ

{{< figure src="zelda-ocarina-ogp.webp" link="https://www.nintendo.com/jp/games/switch2/aa9ja/index.html" alt="森の小道でオカリナを持った子供のリンクと妖精ナビィ、右にゼルダの伝説 時のオカリナのロゴ" caption="Nintendo Switch 2 版『ゼルダの伝説 時のオカリナ』<br>出典：[任天堂 公式サイト](https://www.nintendo.com/jp/games/switch2/aa9ja/index.html)（2026年11月21日取得）" width="600" align="center" >}}

ゾルトラークは、便利な表現だ。ゾルトラークは、[葬送のフリーレン](https://frieren-anime.jp/)に登場する史上初の貫通魔法であり、長い年月の間に研究されすぎて一般攻撃魔法まで格下げされた。[時のオカリナ](https://www.nintendo.com/jp/games/switch2/aa9ja/index.html)も、今回のリメイクでゾルトラークとなった。当時を知らないユーザーは、時のオカリナを完成度の高いアクション RPG 扱いしている。[NIRVANA（グランジ）](https://www.universal-music.co.jp/nirvana/)を2026年に聴いて衝撃を受けないように、ジャンル全体が進歩しており、今現在の基準で衝撃を残す作品を作るのは難しいのだろう（時のオカリナの評価を下げる発言ではなく、一般的なモノ作りに言及している）。

1998年当時（私がプレイしたのは99年だが）、広大なハイラル平原にワクワクしたが、現代の感覚で見ると狭い。ダンジョンも狭い。マップを見ながら神殿をうろつくと、「道なりに進めばクリアできるな？」と気づいてしまう。大人になったので空間認知能力が高まったのかもしれない。余計な知識がついた今では、ブロックを動かしたり、高低差を利用した仕掛けが多いのは、3D グラフィックが作りやすいからだと、ゲスパーをしてしまう。純粋な子供時代のような楽しみ方ができない。ドキドキしながら水の神殿に入ったが、あっさりクリアできてしまった。

{{< figure src="hyrule-field-n64-vs-switch2.webp" alt="左は NINTENDO64 版のハイラル平原で、低解像度の草原の奥にデスマウンテンが小さく見える。右は Nintendo Switch 2 版の平原で、エポナに乗った大人のリンクの背後に草原と山並みが細かく描かれている" caption="ハイラル平原の比較。左：NINTENDO64 版（[Wii バーチャルコンソール版の公式ページ](https://www.nintendo.co.jp/wii/vc/vc_lzo/vc_lzo_06.html)の画面写真）、右：Nintendo Switch 2 版（[公式サイト](https://www.nintendo.com/jp/games/switch2/aa9ja/index.html)の画像）<br>出典：任天堂（2026年11月21日取得）" width="800" align="center" >}}

しかし、時のオカリナリメイクは、100点満点だ。任天堂は私（当時のプレイヤー）の思い出を大切にしてくれたのだな、と受け止めた。華麗なグラフィック、ストーリー補完、プレイしやすさ、豊富なテキストで勝負したと思っており、正当進化だった。時間の流れがあり、その流れの中でキャラが生活している。人間らしいリアクションを返す。昔から任天堂が言語化しようとしていたゼルダらしさが、表現されている。難易度はやや上がっているように感じられるが、丁度よい。簡単な部類だが（ゼルダに難易度を求めていない）。

10〜20年後に再リメイクする際は、大幅に改変しても良いと感じた。ハードの進歩を考えると、同じ方向性でリメイクしても目新しさはないだろう。リメイクしたら別作品になってしまった、というレベルを期待している。[開発者インタビュー](https://www.nintendo.com/jp/interview/aa9ja/index.html)を読む限り、任天堂は技術の継承に成功していそうなので、これからも良質なゼルダはリリースされるだろう。最後に余談だが、私は子供がいるからか、「こんなプニプニしてそうな幼子リンクに旅をさせていいのか？」と、別方向の心配が出てしまった。
