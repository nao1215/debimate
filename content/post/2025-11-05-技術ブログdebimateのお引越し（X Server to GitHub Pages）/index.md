---
title: '技術ブログ debimate のお引越し（X Server to GitHub Pages）'
type: post
date: 2025-11-05
categories:
  - "体験談"
cover:
  image: "images/migrate.jpg"
  alt: "技術ブログ debimate のお引越し"
  hidden: false
---

### お引越し

2025年12月末に、debimate は X Server から GitHub Pages へ移転します。
2025年11月現在は、移行期間であり、不具合がないかのチェックをするために設けています。移行にかかった時間は、2.5時間ほどです。移行というより、ブログの見栄えの調整に時間かかりました。

私は、2018年12月から2025年11月までの間、X Server と WordPress の構成でブログ運用を続けてきました。今回、GitHub Pages（with [Hugo](https://gohugo.io/)）への移転に踏み切った理由として、以下が挙げられます。

- 毎年、レンタルサーバー代とドメイン代で約2万円の出費が地味に大きい
- WordPress でテキストを書く体験（UX）が悪かった。画面がガタついた。
- SEO を高めて、一定の金額を稼ぐ目標は達成済み（現在は SEO を気にしなくて良い）

理由の詳細を後述していきたいと思います。

### ブログは生活の一部。サーバー維持費は一生もの

私は、恐らく一生ブログに記事を投稿し続けると予想しています。更新頻度が下がっても、私は30年以上ブログを使い続けるでしょう。30年の間、維持費を払うと60万円程度の出費です。インフレを加味すると、もしかしたら100万円に近づくかもしれません。維持費を払う金銭的余裕はありますが、私は同じ金額を嫁や子供に還元した方が性に合います......嘘ついているかもしれません。ガジェット代に消えるかもしれません。

維持費を減らすことを念頭に置いたとき、どのサービスを利用するかを決める必要がありました。自宅サーバー勢ではないので、サービス利用は当然の判断ですね。私は自由を好む性格であるため、Qiita, Zenn, note などのサービスを本格的に利用する案を採用したくありませんでした（注：稀に Qiita, Zenn, note を使ってます。良いサービスだと思います）。

最も使いやすいサービスは、GitHub Pages だろうと即座に考えつきました。普段から開発で GitHub を使っていますし、GitHub Actions で CI/CD ができます。何より無料。

### WordPress は、テキスト書きづらかった

私が、WordPress 環境を改善しなかったのが最大の原因ですが、テキストが書きづらかったです。WordPress では、ブロック（段落）が自動で挿入されて、ブロック上でテキストを書きます。文字を入力すると、表示がガタついて集中が乱れました。他にもバグみたいな挙動があり、例えばコードブロックを挿入すると、下書きページから一度抜けないとコードブロックを追加挿入できませんでした。 WordPress が悪いというより、私が PHP を学んで改善する気が一切なかったのが原因です。

WordPress を褒めておくと、記事のエクスポート機能が搭載されていたのは最高でした。エクスポートした XML ファイルを [lonekorean/wordpress-export-to-markdown](https://github.com/lonekorean/wordpress-export-to-markdown) で Markdown に変換すれば、我々エンジニアが扱いやすいプレーンなテキストが手に入ります。

### マネタイズのために SEO を意識する時期は終わった

「私がなぜ、技術ブログを書き始めたか」という話をすると、技術ブログで一発当ててやるぜ！と燃えていた時期がありました。SEO 対策に X Server と契約し（ここが本当に SEO に効いたかは謎）、2018年12月から約2年間ほど毎週2本以上の記事を書き続けました。その結果、2022年頃は月2万 PV 程度の閲覧がありました。しかし、悲しい現実ですが、エンジニアはブログ内の広告を踏まない、もしくは広告を非表示にしているので、広告収入は殆どありませんでした。

広告収入が得られない一方で、技術評論社から Software Design の寄稿依頼を受け、数十万円を稼ぐことができました。この段階で、私のブログマネタイズは終わりました。3回も寄稿でき、幸せものです。
- [Software Design 2022年1月号 第2特集（第1章、第2章）に寄稿【キッカケ、感想、書き足りない内容】](https://nao1215.github.io/debimate/post/2021-12-17-software-design-2022%E5%B9%B41%E6%9C%88%E5%8F%B7-%E7%AC%AC2%E7%89%B9%E9%9B%86%E7%AC%AC1%E7%AB%A0%E7%AC%AC2%E7%AB%A0%E3%81%AB%E5%AF%84%E7%A8%BF%E3%82%AD%E3%83%83/)
- [【寄稿】Software Design 2022年6月号 第1特集（第3章 シェルスクリプトの使い方）](https://nao1215.github.io/debimate/post/2022-05-15-%E5%AF%84%E7%A8%BFsoftware-design-2022%E5%B9%B46%E6%9C%88%E5%8F%B7-%E7%AC%AC1%E7%89%B9%E9%9B%86%E7%AC%AC3%E7%AB%A0-%E3%82%B7%E3%82%A7%E3%83%AB%E3%82%B9%E3%82%AF%E3%83%AA/)
- [【寄稿】Software Design 2024年12月号 第1特集 第4章 落し穴に落ちないシェルスクリプト開発のススメ](https://nao1215.github.io/debimate/post/2024-12-07-%E5%AF%84%E7%A8%BFsoftware-design-2024%E5%B9%B412%E6%9C%88%E5%8F%B7-%E7%AC%AC1%E7%89%B9%E9%9B%86-%E7%AC%AC4%E7%AB%A0-%E8%90%BD%E3%81%97%E7%A9%B4%E3%81%AB%E8%90%BD%E3%81%A1%E3%81%AA/)

前述のように、何故か SEO 対策で X Server を利用していましたが、もう SEO は気にしていません。ブログマネタイズが終わった段階で、X Server を利用する理由がなくなっていました。

### 最後に

若干、記事が見にくくなったり、検索性が落ちた部分があります。徐々に改善していくつもりです。

これからも debimate をよろしくお願いします。

### 2025年11月8日追記：ドメインは維持！

前職のテックリードから debimate.jp を捨てることに関して、ツッコミが入りました。

<blockquote class="twitter-tweet" data-lang="ja" data-dnt="true"><p lang="ja" dir="ltr">あれURLは保持しないんですか？ <a href="https://t.co/SGXD1eTCNi">https://t.co/SGXD1eTCNi</a></p>&mdash; f96fd3a0-bdb9-4f10-b69f-8f765c1d341c ICHINOSEShogo (@shogo82148) <a href="https://twitter.com/shogo82148/status/1986428488623267933?ref_src=twsrc%5Etfw">2025年11月6日</a></blockquote> <script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

↑ のテックリードの発言は、「ドメインを廃止すると悪用されるよ」と暗に指摘しています。私はテックリードがドメインを廃止してはいけないと啓蒙していたのを見聞きしていたので、この指摘は予想できていました。なんなら、ブログの引っ越しを考えた瞬間から、このツッコミが来るだろうなと予想してました。

ドメイン料金が毎年3,000円かかるのは微妙ですが、debimate.jp は私が7年程度かけて育てたドメインです。維持することにしました。手放した瞬間に debimate.jp を弄ばれるのも、なんか微妙な気持ちになる気がしたので。

<blockquote class="twitter-tweet" data-dnt="true"><p lang="ja" dir="ltr">このままの流れでは、2026年1月1日に私が持っていたドメインは <a href="https://twitter.com/shogo82148?ref_src=twsrc%5Etfw">@shogo82148</a> に乗っ取られ、「ドメインを手放すとこんなことになるよ」と啓蒙するブログが書かれる未来が待ってます<br><br>救いの手（ドメイン代）をお待ちしております<a href="https://t.co/K5RZ1rS7pp">https://t.co/K5RZ1rS7pp</a><br>（冗談はさておき、どうするかな......）</p>&mdash; nchika (@ARC_AED) <a href="https://twitter.com/ARC_AED/status/1986436012919394740?ref_src=twsrc%5Etfw">November 6, 2025</a></blockquote> <script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

debimate.jp を維持する方針に変更した後、まずは X Server 側の Aレコード設定を変更し、GitHub Pages のカスタムドメインを debimate.jp としました。debimate.jp が GitHub Pages を表示するまでに1時間ぐらいかかりました。その後、ブログ記事内リンクを貼りなおす地道な作業をやる羽目になりました。3時間ぐらいかかりました...大変でした
