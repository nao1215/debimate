---
title: "2026/09/14週"
date: 2026-09-14T00:00:00+09:00
aliases:
  - /weekly/2026-09-14/
---

#### 時のオカリナ

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

json 出力機能が有効に使われる日が来るとは、思いもしなかった。json といえば、最近 [jsonize](https://github.com/nao1215/jsonize) コマンドを作った理由は「コマンド同士で連携するには、パイプか json が必要。しかし、json 出力がないコマンドもある」と考えたからだ。grep や awk、sed を駆使すれば jsonize は不要なんだが、そのワンライナーを書くのが厳しい人に向けて作った。私は、LLM にワンライナー作成を任せる気がする。
