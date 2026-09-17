---
title: "2026/09/14週"
date: 2026-09-14T00:00:00+09:00
aliases:
  - /weekly/2026-09-14/
---

#### 時のオカリナリメイク（Nintendo Direct）

<iframe width="560" height="315" style="display: block; margin-inline: auto; max-width: 100%;" src="https://www.youtube.com/embed/7URsVYKWubQ?si=Xvwly9kzI8mBGeLS" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

時のオカリナのリメイクが待ち遠しい。リンクの服は手編みっぽかったが、一体コキリ族の誰が作ったのだろうか。ここまで現代化されたグラフィックの中でコッコいじめをすると、果たしてどんな恐ろしい形相でコッコが飛び交うのだろうか。

子供の頃に NINTENDO 64 を持っていないのに、時のオカリナだけを買ってもらった。N64時代の黒を基調としたパッケージは、小学生が見ても格好良さを感じたものだ。オープニングで沈む月をバックにエポナと突き進むのも、印象的だった。当時プレイしたゲームの中では難易度が高く、ジャブジャブ様、水の神殿で詰まった記憶がある。死亡回数は18回だ。ムジュラの仮面が個人的な本命なので、そこに繋げるために売り上げへ貢献しなければならない。

20～30年もあればゼルダがリメイクされると考えれば、私が70歳になる前にはもう一度リメイクされる可能性がある。老後の楽しみができた。

----

#### gup が Meta Package Manager に組み込まれた

[Topgrade](https://github.com/topgrade-rs/topgrade) に続き、[gup](https://github.com/nao1215/gup) が [meta-package-manager](https://github.com/kdeldycke/meta-package-manager) に組み込まれた。

{{< figure src="mpm.webp" alt="Meta Package Manager に組み込まれた gup" >}}

mpm は、以下の機能を実現するために gup の幅広い機能を使っていた。

- 個別更新：`gup update <name>` を実行
- 全更新：`gup update` を実行
- インストール済み一覧表示：`gup list --json` を解析
- 最新ではないコマンド表示：`gup check --json` を解析
- 削除：`gup remove --force <name>` を実行

json 出力機能が有効に使われる日が来るとは、思いもしなかった。json といえば、最近 [jsonize](https://github.com/nao1215/jsonize) コマンドを作った理由は「コマンド同士で連携するには、パイプか json が必要。しかし、json 出力がないコマンドもある」と考えたからだ。grep や awk、sed を駆使すれば jsonize は不要なんだが、そのワンライナーを書くのが厳しい人に向けて作った。とは言え、ワンライナー作成自体、最近は LLM 任せにしがちだ。

----

#### Wasm は便利な中間表現

[ncruces/wasm2go](https://github.com/ncruces/wasm2go) を眺めていて、Wasm を中間表現として C/C++などの既存資産を CGO なしの Go パッケージに組み込む案は、実用的だと感じた。特段新しい案でもない。[「GoにおけるFFIのこれまでとこれから（Go Conference 2026、goccy 氏）」](https://speakerdeck.com/goccy/go-niokeru-ffi-no-kore-madeto-korekara) でも似た内容が触れられていた。例えば、SQLite は利用しているシステムコールが少ないため、Wasm to Go しやすい。

オリジナルコードを参照させながら LLM に他言語版を実装させる案もあるが、機械的に置換した方が安心。トークンを浪費しないし、誤解釈によるバグを埋め込まない。個人的に試してみたいのは、[NKF（Network Kanji Filter）](https://github.com/nurse/nkf) の Go 化である。NKF は、文字コードや改行コードを変換するツールで、昔の印象だと精度が良かった。作業としては NKF を Wasm to Go して、型やら良い感じの API を独自設計して提供する必要がある。

文字コードの領域は、Go において決定版ライブラリが恐らく存在せず（ないよね？）、メンテ状況が怪しいライブラリが多い。文字コードは沼なので、ライブラリ開発自体が難しい。その結果として、「Excel を CSV として保存すると Shift-JIS になるから、UTF-8 に変換しようか」みたいなエッジケースだけ個別対応する羽目になる。2022年頃から文字コード自動判別ライブラリが欲しかったので、今度文字コードで苦しんだらライブラリを開発するかも。

----

#### 5年ぶりに Neovim 環境を整えた

スッとコードを読むときのために Neovim 環境を作った。私は、組み込み時代は画面全部をターミナルで覆って開発するスタイルだった。バックエンドエンジニアになってから、Visual Studio Code を使うようになり、Neovim を使う機会がなかった。コードリーディングには Neovim が便利なので、環境を準備しておいた。書くなら VS Code、読むなら Neovim の使い分け。VS Code は最近やや重く、機能が増えすぎた。

昔はターミナル背景を透過させたり、色んなプラグインを試したりしていたが、必要な機能だけを設定した。設定いじりに熱中すると、肝心の開発が進まない。

{{< figure src="neovim.webp" alt="Neovim の開発環境" >}}

---

#### 比較表を書くと、改善する羽目になる

[nao1215/jsonize](https://github.com/nao1215/jsonize) がある程度完成したので、 [記事](/post/ja/2026-09-16-jsonizeでjsonをunixパイプラインの共通言語にする/)を書いたり、類似ツールとの比較表を書いたりしていた。

比較表は厄介だ。サボりがバレる。脳内でイマジナリー上司に詰められる。

詰められる例
- 私　　　　　　「A、B、C の項目に関して、A と C は競合より優れています」
- 上司（非実在）「何故 B で負けているんだ？勝つ方法は？」
- 私　　　　　　「一応、こうすれば勝てますが...」
- 上司（非実在）「方法があるなら、なぜ勝つまでやらないんだ？」
- 私　　　　　　「改善してから、再提出します」

上記の会話例は創作だが、似た会話をした経験は何度かある。先輩からは「比較表を書いたら、全部 ◯ にしないと駄目だよ。☓ があると何か言われちゃうからね」と教えてもらったものだ。性能改善に繋がるなら問題ないのだが、どうしようもない場合は言葉遊びや隠蔽工作みたいな方向に倒れる可能性もある。

jsonize は比較表を導入したせいで、性能改善する羽目になっている。例えば、Python 製ツールに Go 製の jsonize が速度で負けている部分があった。原因は、膨大なパーサーデータを起動時に読み込んでいたこと。読み込みタイミングを変更によって条件次第では7倍以上高速になった。

最初は「ありのままの姿（比較表）を見せればいいか」と考えていたのに、表をレビューしたらお化粧したくなってしまった。負けず嫌いとは違うのだ。なぜベストを尽くさないのか、と指摘された感じがする。巧遅拙速が良いと教えられて育ってきたが、結局拙いものは許されない。
