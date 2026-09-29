---
title: "2026/09/28週"
date: 2026-09-28T00:00:00+09:00
---

#### OpenSSF Scorecard を導入

「OSS ライブラリのメンテナンス具合を調べるツールが欲しいな（作ろうかな）」と考え、類似 OSS を調査したら OpenSSF Scorecard に辿り着いた。OpenSSF Scorecard は、OSS の開発・配布過程にあるセキュリティ上の弱点を自動点検し、保守体制の一部を可視化する。雑に説明すれば、OSS の状態をスコア化する。

成熟したライブラリや単独開発ではスコアが低くなりがちだが、GitHub Actions に余計な権限を与えていないかをチェックできる利点がある。GitHub Actions の Runner 上で任意コマンドを実行する類の脆弱性を見かける機会が増えたので、対策をしておきたかった（参考：[相次ぐGitHub Actions 侵害から学ぶ、初期アクセス手法と開発者が知っておきたい対策](https://blog.flatt.tech/entry/2026-github-actions-security-part1)）。一先ず、Go 製の主要 OSS に OpenSSF Scorecard を導入した。導入済み OSS は、README 上部のバッジにスコアが表示されている。

ついでに、OpenSSF criticality score を計測した。gup が 0.4 を超えているので、[Claude for Open Source Program](https://claude.com/contact-sales/claude-for-oss) の申込条件を満たしていることに気づいた。計測方法によっては 0.4 を下回る説があるが......調べてから再挑戦する。

| Repository | Criticality score | Stars | Contributors | Orgs | Mentions | Releases (1y) |
|---|---|---|---|---|---|---|
| [gup](https://github.com/nao1215/gup) | 0.51532 | 606 | 25 | 6 | 1509 | 29 |
| [sqly](https://github.com/nao1215/sqly) | 0.40981 | 190 | 9 | 1 | 118 | 49 |
| [markdown](https://github.com/nao1215/markdown) | 0.37067 | 142 | 9 | 2 | 77 | 5 |
| [filesql](https://github.com/nao1215/filesql) | 0.33102 | 386 | 2 | 0 | 81 | 74 |
| [atago](https://github.com/nao1215/atago) | 0.32255 | 18 | 3 | 1 | 46 | 33 |

Measured with [criticality_score](https://github.com/ossf/criticality_score) v2.0.4 (default scorer, deps.dev disabled) on 2026-09-28.

---

#### ピンボール・パチンコゲームを作ったが、ポシャった

私は大学生の時からゲームを作りたいと考えており、そろそろライフワークとして開発の練習をすべきかと唐突に考えた。ゲーム開発の定番アドバイスには、「まずは一本完成させろ」というものがある。その言葉に従って、小さい2 D ゲームを [ebitengine](https://ebitengine.org/ja/) と [ComfyUI（画像生成ツール、ローカルで実行）](https://github.com/comfy-org/comfyui)で作ることにした。

題材には、ピンボールを選んだ。完成品は、とにかく面白くなかった。Windows のピンボールに熱中していた頃が嘘のようだ。そこで、過剰演出で人を楽しませるパチンコに変更した。これまた面白くなかった。面白くはないが、LLM を使えば容易に形にできるし、画像生成プロンプトでキャラがそこまでブレないことが分かった（好みのキャラが作れているか、と言われれば違うが）。画像から AI 臭さを抜く方法は、まだ調査中である。今回は、一旦ギラつかせた。

{{< figures >}}
{{< figure src="pachinko.webp" alt="ebitengine で作ったパチンコ" >}}
{{< figure src="pachinko_atlas_covered_3.webp" alt="パチンコの画像（Atlas Covered 3）" >}}
{{< figure src="pachinko_hero_omen.webp" alt="パチンコの画像（Hero Omen）" >}}
{{< /figures >}}

面白さを足すのには、ドメイン知識がいる。私はパチンコをしないので、何が面白いのかを理解できていなかったのが不味かった。途中で気づいたのは、当たりの穴に玉が入るかどうかをハラハラしながら見守るのが楽しいのだ。パチンコのシステムは、ユーザーに「惜しい」と思わせたり、「来るか来るか？」と手に汗握る演出や物理演算で期待を煽るべきだ。上げて下げる、みたいな手法も有効だろう。現実だと現金が溶けるが、私が作ったパチンコは金銭的に背負うものがないので真剣味に欠けやすかった。さらに、基本的に放置すれば玉が増えるので、全く感情が動かなかった。

物理演算が雑で変な場所に玉が飛んだり、どこに玉が入るとボーナスタイム（？）になるのかが分かりづらい見た目は、論外。作り込んでいくうちに「2 D より、3 D の方がやりやすいな」と真理に辿り着いて、途中でパチンコの開発を中止した。総括としては、初期ドラクエぐらいの RPG を作れそうだけど、ゲーム性をキチンと定義しないと、電気代とトークンの無駄になりそう。今、頭の中にあるのは、初期パラメータを決めたら勝手に世界が自動構築されるゲーム。SIMPLE シリーズ・THE 創造主。

---

#### 作りたいゲームの言語化

一つ前でゲーム作りの話を書いたので、その続きを書く。まず、最近内省して自己理解したが、私はゲームを作りたいわけではない。大学生の頃からゲーム作りが一つの目標だった。それは何も取り柄がなく、ゲームばかりしていた学生だったから、身近だったゲームを作りたいという発想に至っただけだ。その証拠に、いつまで経ってもゲームが完成せず、作りたいゲームジャンルも思いつかない。これだけ OSS を作っているにもかかわらず、ゲームに関しては一向に先へ進まないのだ！ガハハ。

ここからも最近の気づきだが、自分で考えた独自世界をゲーム（or 何らかの媒体）に落とし込みたい欲求がある。自分が若い頃に見聞きしたファンタジーやクトゥルフのような内容を再解釈して、独自の世界に落とし込みたい。そもそも私は、世界のすべてを把握する行為が好きっぽい。攻略本やファンブックに書かれた隠し設定を読むのが好きだし、ムジュラの仮面や NIER、ソウルシリーズのような考えさせる世界観にハマりがちだ。

そうなってくると、まずはゲームを作るより独自の世界に関する設定を書き出して、そこにフィットするゲームを考えれば前に進む気がしている。逆パターンは、エンジニアリング視点で面白いシステムを考えて、そこに設定を当て込む案。この案が、一つ前のトピックで書いた初期パラメータを決めたら勝手に世界が自動構築されるゲーム。見るだけのシムシティ。

---

#### Ubuntu で DARK SOULS REMASTERED が快適に動く

2026年6月に X でも書いた話題だが、Linux で Steam を使えば、Windows 対応ゲームをプレイできる。Linux 対応と表記されていなくても、動作する。Steam（Valve）が開発した互換レイヤーである [Proton](https://github.com/ValveSoftware/Proton) が、この偉業を成し遂げている。Proton は、2020年代で最も感動したソフトウェアの一つかもしれない。

一昔前は、「Linux はゲームができないのが弱点」が定説だった。現在は、普通にプレイできてしまう。私の環境では、DARK SOULS REMASTERED が快適に動作し、FFⅦ REMAKE が稀にモタつくぐらい。
 
{{< figures height="12rem" >}}
{{< figure src="darksoul.webp" alt="ダークソウル" >}}
{{< figure src="ff7r.webp" alt="FINAL FANTASY VII REMAKE" >}}
{{< /figures >}}

Steam で快適にプレイできることに気づいてからチマチマとゲームを買い足しているが、2 D ゲーであれば何も支障はない。問題は、積みがちなことと、任天堂ゲームがないことだ。任天堂に関しては、スーパードンキーコング2、星のカービィ（GB）を暇つぶしにプレイしている。吸い出し機を購入して PC 上のエミュでプレイする案もあるが、レトロゲーをプレイするには Nintendo Switch が快適すぎて、エミュ環境の構築を積極的に行う理由がない。

{{< figure src="gamelist.webp" alt="Steam のゲームライブラリ" align="center" >}}

現在の作業環境は、NucBox EVO-X2 であり、以下の構成だ。最近は、円安と半導体不足によって、[同じ PC の性能落ち版（RAM が64 GB と控えめ）](https://www.amazon.co.jp/dp/B0F5HDWNKR?pd_rd_i=B0F5HDWNKR&pd_rd_w=1I1QR&content-id=amzn1.sym.b8a755c3-4dc6-4219-9ded-79127776efca&pf_rd_p=b8a755c3-4dc6-4219-9ded-79127776efca&pf_rd_r=8EC1DT6F7AB41041NT31&pd_rd_wg=aCq2V&pd_rd_r=6b360132-4acb-4121-9302-fcb06d0bb8b7&sp_csd=d2lkZ2V0TmFtZT1zcF9kZXRhaWxfdGhlbWF0aWM&th=1&linkCode=ll2&tag=debimate07-22&linkId=21ed38cafc9d836c79ae03fc6cf77082&ref_=as_li_ss_tl)が37万する。2025年11月に、RAM 128 GB 版（私の PC）を買った時は29万程度だった。EVO-X2 はメモリ交換できないのが欠点だが、RAM を VRAM に回せるのが利点だ。

```shell
           `.:/ossyyyysso/:.                nao@EVO-X2
        .:oyyyyyyyyyyyyyyyyyyo:`            ----------
      -oyyyyyyyodMMyyyyyyyysyyyyo-          OS: Kubuntu 26.04.1 LTS (Resolute Raccoon) x86_64
    -syyyyyyyyyydMMyoyyyydmMMyyyyys-        Host: NucBox_EVO-X2 (Version 1.0)
   oyyysdMysyyyydMMMMMMMMMMMMMyyyyyyyo      Kernel: Linux 7.0.0-34-generic
 `oyyyydMMMMysyysoooooodMMMMyyyyyyyyyo`     Uptime: 3 hours, 9 mins
 oyyyyyydMMMMyyyyyyyyyyyysdMMysssssyyyo     Packages: 3719 (dpkg), 32 (snap)
-yyyyyyyydMysyyyyyyyyyyyyyysdMMMMMysyyy-    Shell: bash 5.3.9
oyyyysoodMyyyyyyyyyyyyyyyyyyydMMMMysyyyo    Display (LG ULTRAWIDE): 2560x1080 in 29", 60 Hz [External]
yyysdMMMMMyyyyyyyyyyyyyyyyyyysosyyyyyyyy    DE: KDE Plasma 6.6.6
yyysdMMMMMyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy    WM: KWin (Wayland)
oyyyyysosdyyyyyyyyyyyyyyyyyyydMMMMysyyyo    WM Theme: Breeze
-yyyyyyyydMysyyyyyyyyyyyyyysdMMMMMysyyy-    Theme: Breeze (Light) [Qt], Yaru [GTK2/3]
 oyyyyyydMMMysyyyyyyyyyyysdMMyoyyyoyyyo     Icons: breeze [Qt], breeze [GTK2/3/4]
 `oyyyydMMMysyyyoooooodMMMMyoyyyyyyyyo      Font: Noto Sans (10pt) [Qt], Noto Sans (10pt) [GTK2/3/4]
   oyyysyyoyyyysdMMMMMMMMMMMyyyyyyyyo       Cursor: breeze (24px)
    -syyyyyyyyydMMMysyyydMMMysyyyys-        Terminal: ghostty 1.3.1
      -oyyyyyyydMMyyyyyyysosyyyyo-          Terminal Font: JetBrainsMono Nerd Font (12pt)
        ./oyyyyyyyyyyyyyyyyyyo/.            CPU: AMD RYZEN AI MAX+ 395 (32) @ 5.19 GHz
           `.:/oosyyyysso/:.`               GPU: AMD Radeon 8060S Graphics [Integrated]
                                            Memory: 20.50 GiB / 61.43 GiB (33%)
                                            Swap: 120.00 KiB / 8.00 GiB (0%)
                                            Disk (/): 1.41 TiB / 1.79 TiB (79%) - ext4
                                            Disk (/media/nao/2nd): 808.67 GiB / 1.83 TiB (43%) - ext4
```

<br>

次の PC は、ローカル LLM できることが前提になると想定している。趣味で、Claude や Codex を契約し続けるのが厳しい。[Claude for Open Sourceに申請して1ヶ月、まだ返事がない（記事）](/post/ja/2026-09-21-claude-for-open-sourceに申請して1ヶ月まだ返事がない/)でも書いたが、LLM 代金が年間20万を超えるのだ。サブスク代としては異常だ。あと、Weekly Limit にすぐ達するのが開発者体験として許容できない。私が寝ている間も働き続けて欲しい。

そう考えると、「従来の PC 予算（20〜30万） + ローカル LLM 用の予算（数十万。気持ち次第） ≒ 50〜70万」ぐらいは現実的なレンジになる。体感的には、今は時期が悪いオジサンにならざるを得ないので、買い替えは早くても2028年か。最近は PC が壊れる前に買い替えているから、贅沢しているなと思う。昔は、HDD が断末魔の異音を数十秒鳴らして事切れるまで使っていたのに。
