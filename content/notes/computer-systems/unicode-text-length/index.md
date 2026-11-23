---
title: "Unicode Text Handling - 文字数の数え違いと文字コードの取り違え"
date: 2026-11-23
draft: false
series: ["技術ノート", "Computer Systems"]
tags: ["computer-systems", "unicode", "text"]
weight: 3
wrapTables: true
topics: ["Text / Unicode"]
---

文字列の長さは、数える単位によって値が変わります。プログラムが扱う文字列は、[Unicode](https://www.unicode.org/) が文字ごとに振った番号を UTF-8 や UTF-16 といった文字コードでバイト列にしたものです。画面に見える「1 文字」は、その番号がいくつか集まった塊で、端末に描くと 1 マスか 2 マスを占めます。どの段階で数えるかによって、同じ絵文字が 18 にも 8 にも 5 にも 1 にもなります。

{{< figure src="images/units.webp" alt="家族の絵文字 1 つを 5 段で数えた図。UTF-8 のバイトでは F0 9F 91 A8 から始まる 18 個、UTF-16 のコード単位では D83D DC68 から始まる 8 個、コードポイントでは男性・ZWJ・女性・ZWJ・女の子の 5 個、書記素クラスターでは 1 個、端末の表示幅では 2 セル。右側に、Go の len と Rust の len() が 18、JavaScript の length が 8、Python の len と SQLite の length が 5、Intl.Segmenter と uniseg が 1 を返すと書いてある" caption="同じ家族の絵文字でも、数える単位ごとに長さが違う" align="center" >}}

テキストを扱うプログラムでは、次のような前提を置きがちです。どれも成り立たない場合があり、筆者が開発している OSS で、それぞれ不具合として表に出ました。

- 文字列の長さは 1 つに決まる。
- Backspace を 1 回押すと、見えている 1 文字が消える。
- 端末で 1 文字が占める幅は、文字ごとに決まっている。
- 画面に `id` と表示された列名は、SQL で `id` と書けば見つかる。
- 文字に戻せないバイトがあれば、どこかでエラーになる。

実例に使う OSS は、CSV や Excel に SQL を実行する [sqly](https://github.com/nao1215/sqly) と、その読み込みを担うライブラリの [filesql](https://github.com/nao1215/filesql)、ログの秘密情報を伏せる [embargo](https://github.com/nao1215/embargo)、端末の入力欄を作る [prompt](https://github.com/nao1215/prompt)、端末で動く Bluesky クライアントの [bsky](https://github.com/nao1215/bluesky-terminal-client) です。

<br>

本記事では、上記の前提を 1 つずつ実例で崩し、どこで数え、どこで切り、どこで変換すれば壊れないかを説明します。最後に、全角で書いたメールアドレスがログの伏せ字をすり抜けるなど、見た目や意味が同じでも中身が違う文字も扱います。実験のコードは Go・Python・JavaScript・Rust で書き、[lab](https://github.com/nao1215/debimate/tree/main/content/notes/computer-systems/unicode-text-length/lab) に置きました。

---

### 1 文字を数える単位

最初に、冒頭の図にある 5 段が何を数えているかを確認します。Unicode は世界の文字に U+0000 から U+10FFFF までの番号を振っており、この番号をコードポイント（code point）と呼びます。「a」は U+0061、「あ」は U+3042、家族の絵文字に含まれる男性は U+1F468 です。

コードポイントをバイト列にする規則が、文字コード（エンコーディング）です。コードポイントをバイト列にすることをエンコード、バイト列からコードポイントに戻すことをデコードと呼びます。[UTF-8](https://www.rfc-editor.org/rfc/rfc3629) は 1 つのコードポイントを 1〜4 バイトで表し、ASCII の文字は 1 バイト、かなや漢字の多くは 3 バイト、多くの絵文字は 4 バイトになります。

[UTF-16](https://www.rfc-editor.org/rfc/rfc2781) は 16 ビットのコード単位（code unit）で数え、U+FFFF までは 1 単位、それより大きいコードポイントは 2 単位の組で表します。この組をサロゲートペア（surrogate pair）と呼びます。冒頭の図で D83D と DC68 が並んでいるのが、男性を表すサロゲートペアです。

<br>

画面で 1 文字に見える単位は、書記素クラスター（grapheme cluster）です。区切り方は [Unicode Standard Annex #29](https://www.unicode.org/reports/tr29/) が決めていて、複数のコードポイントが 1 つの書記素クラスターにまとまる場合があります。

{{< figure src="images/clusters.webp" alt="4 つの書記素クラスターについて、含まれるコードポイントの足し算で描いた図。家族の絵文字は U+1F468、ZWJ、U+1F469、ZWJ、U+1F467 を ZWJ でつないだもの。肌の色付きの親指は U+1F44D に肌の色を変える修飾子 U+1F3FD を続けたもの。日本の国旗は Regional Indicator の J（U+1F1EF）と P（U+1F1F5）を並べたもの。é は e（U+0065）に結合文字 U+0301 を続けたもの" caption="見た目は 1 文字でも、中身は 2〜5 つのコードポイント" align="center" >}}

家族の絵文字は、3 人の絵文字を [ZWJ](https://www.unicode.org/reports/tr51/#Emoji_ZWJ_Sequences)（ゼロ幅接合子、U+200D）という幅の無い文字でつないでいます。

親指に続く U+1F3FD は肌の色を変える修飾子（emoji modifier）で、国旗は A〜Z に当たる Regional Indicator という記号を 2 つ並べて国コードを表します。é は合成済みの U+00E9 の 1 つでも書けますが、e の後に結合文字（combining character）の U+0301 を続けても同じ見た目になります。

<br>

以下は、いくつかの文字列を 5 つの単位で数えた Go のプログラムです。書記素クラスターと表示幅は [rivo/uniseg](https://github.com/rivo/uniseg) と [go-runewidth](https://github.com/mattn/go-runewidth) で数えています。

```go
package main

import (
	"fmt"
	"os"
	"text/tabwriter"
	"unicode/utf16"
	"unicode/utf8"

	"github.com/mattn/go-runewidth"
	"github.com/rivo/uniseg"
)

func main() {
	samples := []struct{ label, s string }{
		{"a", "a"},
		{"あ", "あ"},
		{"é（合成済み U+00E9）", "\u00e9"},
		{"é（e + U+0301）", "e\u0301"},
		{"ｶﾞ（半角カナ＋半角濁点）", "\uff76\uff9e"},
		{"𩸽（ほっけ）", "\U00029E3D"},
		{"👍🏽（肌の色付き）", "\U0001F44D\U0001F3FD"},
		{"🇯🇵（国旗）", "\U0001F1EF\U0001F1F5"},
		{"👨‍👩‍👧（家族 3 人）", "\U0001F468\u200d\U0001F469\u200d\U0001F467"},
		{"👨‍👩‍👧‍👦（家族 4 人）", "\U0001F468\u200d\U0001F469\u200d\U0001F467\u200d\U0001F466"},
	}

	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', tabwriter.AlignRight)
	fmt.Fprintln(w, "文字\tUTF-8 バイト\tUTF-16 単位\tコードポイント\t書記素\t表示幅(runewidth)\t表示幅(uniseg)\t")
	for _, x := range samples {
		fmt.Fprintf(w, "%s\t%d\t%d\t%d\t%d\t%d\t%d\t\n",
			x.label,
			len(x.s),
			len(utf16.Encode([]rune(x.s))),
			utf8.RuneCountInString(x.s),
			uniseg.GraphemeClusterCount(x.s),
			runewidth.StringWidth(x.s),
			uniseg.StringWidth(x.s),
		)
	}
	w.Flush()
}
```

実行結果を表にまとめました。UTF-8 はバイト、UTF-16 はコード単位、CP はコードポイント、書記素は書記素クラスターの数で、最後の 2 列は 2 つのライブラリが返した表示幅です。

| 文字 | UTF-8 | UTF-16 | CP | 書記素 | runewidth | uniseg |
|---|---:|---:|---:|---:|---:|---:|
| a | 1 | 1 | 1 | 1 | 1 | 1 |
| あ | 3 | 1 | 1 | 1 | 2 | 2 |
| é（合成） | 2 | 1 | 1 | 1 | 1 | 1 |
| é（分解） | 3 | 2 | 2 | 1 | 1 | 1 |
| ｶﾞ（半角） | 6 | 2 | 2 | 1 | 2 | 1 |
| 𩸽 | 4 | 2 | 1 | 1 | 2 | 2 |
| 👍🏽 | 8 | 4 | 2 | 1 | 2 | 2 |
| 🇯🇵 | 8 | 4 | 2 | 1 | 2 | 2 |
| 👨‍👩‍👧 | 18 | 8 | 5 | 1 | 2 | 2 |
| 👨‍👩‍👧‍👦 | 25 | 11 | 7 | 1 | 2 | 2 |

見た目が同じ é でも、書き方によってバイト数とコードポイント数が変わります。𩸽 は U+FFFF を超える漢字なので、絵文字と同じく UTF-16 では 2 単位です。半角の「ｶﾞ」は、半角濁点が直前の文字にくっつく扱いなので 1 つの書記素クラスターになり、幅は 2 つのライブラリで 2 と 1 に分かれました。ライブラリで幅が違う理由は、後の節で扱います。

<br>

各言語の標準の「長さ」が、どの単位を返すかも確かめました。家族 3 人の絵文字で数えた結果です。

| 書き方 | 値 | 返す単位 |
|---|---:|---|
| Go の `len(s)` | 18 | UTF-8 のバイト |
| Rust の `s.len()` | 18 | UTF-8 のバイト |
| JavaScript の `s.length` | 8 | UTF-16 のコード単位 |
| Rust の `s.encode_utf16().count()` | 8 | UTF-16 のコード単位 |
| Python の `len(s)` | 5 | コードポイント |
| Go の `utf8.RuneCountInString(s)` | 5 | コードポイント |
| Rust の `s.chars().count()` | 5 | コードポイント |
| SQLite の `length()` | 5 | コードポイント |
| JavaScript の [`Intl.Segmenter`](https://developer.mozilla.org/ja/docs/Web/JavaScript/Reference/Global_Objects/Intl/Segmenter) | 1 | 書記素クラスター |

どの言語も間違ってはおらず、それぞれ文字列を持つ形に合った単位を返しています。Go と Rust は文字列を UTF-8 のバイト列で、JavaScript は UTF-16 で、Python はコードポイントの並びで持つからです。

Firefox の文字コード変換を実装した Henri Sivonen も、ブログ記事「[It's not wrong that "🤦🏼‍♂️".length == 7](https://hsivonen.fi/string-length/)」で、長さは何に使うかで選ぶものだと論じています。LLM のトークン数はさらに別の数え方で、[トークナイザーのノート](/notes/generative-ai/tokenizer/)では同じ家族の絵文字が 8 トークンに割れました。

<br>

長さとは別に、UTF-16 のサロゲートペアは、片方だけを扱うと文字が失われます。bsky は、Windows の端末で絵文字を入力しても何も入りませんでした。Windows のコンソールは、U+FFFF を超える文字をサロゲートペアの前半と後半の 2 つのキー入力として渡します。bsky が使う端末ライブラリの [crossterm](https://github.com/crossterm-rs/crossterm) が、この 2 つを 1 文字に組み立てられずに捨てていたためです。

---

### 上限は仕様が決めた単位で数える

長さの単位が問題になるのは、上限と比べる時です。上限を決めるのはサーバーやファイル形式なので、手元で使う言語の `len` ではなく、その仕様が数える単位で比べる必要があります。

Bluesky の投稿は、Bluesky が使う通信の仕組みである AT Protocol の [lexicon](https://atproto.com/specs/lexicon)（レコードの形を決める定義）で、本文が 300 書記素クラスターかつ 3000 バイトまでと決まっています。[投稿の定義](https://github.com/bluesky-social/atproto/blob/main/packages/api/lexicons/app/bsky/feed/post.json)には `maxGraphemes: 300` と `maxLength: 3000` の 2 つがあり、lexicon の仕様は `maxLength` を UTF-8 のバイトで数えると定めています。

bsky では、家族 4 人の絵文字を 121 個並べた投稿が入力欄では通り、送った後にサーバーから拒否されました。家族 4 人の絵文字は 1 個 25 バイトなので、121 個で 3,025 バイトになり、書記素クラスターの上限には収まってもバイトの上限を超えます。

Excel のセルは、[仕様と制限](https://support.microsoft.com/ja-jp/office/excel-%E3%81%AE%E4%BB%95%E6%A7%98%E3%81%A8%E5%88%B6%E9%99%90-1672b34d-7043-467e-8e27-269d656771c3)で 32,767 文字までです。Excel のファイルを書く Go のライブラリ [excelize](https://github.com/qax-os/excelize) は、この上限を UTF-16 のコード単位で数え、絵文字は 1 個 2 単位になります。

filesql で SQL の結果を Excel のファイルに書き出すと、絵文字 16,384 個の値が、エラーも無く 1 個欠けて戻ってきました。16,384 個は 32,768 単位で、上限を 1 つ超えています。excelize は、上限を超えた値をエラーにせず切り詰めます。

```go
package main

import (
	"fmt"
	"strings"
	"unicode/utf16"

	"github.com/rivo/uniseg"
	"github.com/xuri/excelize/v2"
)

func main() {
	// Bluesky の投稿: 300 書記素かつ 3000 バイト（UTF-8）まで。
	family := "\U0001F468\u200d\U0001F469\u200d\U0001F467\u200d\U0001F466" // 👨‍👩‍👧‍👦
	post := strings.Repeat(family, 121)
	fmt.Printf("bluesky: 家族 121 個 = %d 書記素, %d バイト\n",
		uniseg.GraphemeClusterCount(post), len(post))

	// Excel のセル: 32,767 文字まで。excelize で書いて読み出す。
	for _, n := range []int{16383, 16384} {
		v := strings.Repeat("\U0001F600", n) // 😀 は UTF-16 で 2 単位
		f := excelize.NewFile()
		if err := f.SetCellValue("Sheet1", "A1", v); err != nil {
			panic(err)
		}
		got, err := f.GetCellValue("Sheet1", "A1")
		if err != nil {
			panic(err)
		}
		fmt.Printf("excel: 😀 を %d 個書く (UTF-16 で %d 単位) -> 読み出すと %d 個\n",
			n, len(utf16.Encode([]rune(v))), len([]rune(got)))
	}
}
```

```text
bluesky: 家族 121 個 = 121 書記素, 3025 バイト
excel: 😀 を 16383 個書く (UTF-16 で 32766 単位) -> 読み出すと 16383 個
excel: 😀 を 16384 個書く (UTF-16 で 32768 単位) -> 読み出すと 16383 個
```

上限に対する割合で上記の結果を並べたのが、次の図です。

{{< figure src="images/limits.webp" alt="横棒グラフ。Bluesky の投稿で家族 4 人の絵文字 121 個は、書記素クラスターでは 300 の上限に対して 121 で内側だが、UTF-8 のバイトでは 3,025 で 3,000 の上限を超える。Excel のセルで U+1F600 の絵文字 16,384 個は、コードポイントでは 32,767 の上限に対して 16,384 で内側だが、UTF-16 のコード単位では 32,768 で上限を超える" caption="同じ文字列でも、上限と違う単位で数えると、半分ほどに見える" align="center" >}}

どちらも、手元で数えた単位では上限の半分ほどなのに、上限を決めた仕様の単位では超えています。bsky は 2 つの上限を両方確かめ、filesql はセルの長さを UTF-16 のコード単位で数えて、上限を超える値は書き出しを拒否するように直しました。

<br>

逆に、バイトで数えると厳しすぎる場合もあります。Excel のセルに入る上限をバイトで数える実装は、3 バイトの漢字 32,767 個（約 98,000 バイト）の値を拒否してしまいます。漢字 32,768 個が拒否されることだけを試すテストでは、バイトで数える実装も通ってしまい、単位の取り違えに気付けません。上限の境界を試す時は、単位を取り違えると結果が変わる値を選びます。

---

### 切る・消すのは書記素クラスターの境界

長さの次は、文字列のどこで切るかです。書記素クラスターの途中で切ると、見た目の 1 文字が別の文字に化けます。修正前の bsky は、入力欄で Backspace を押すと、コードポイントを 1 つずつ消していました。

{{< figure src="images/delete.webp" alt="Backspace を押すたびに消えるものを並べた図。コードポイントごとに消すと、家族の絵文字は、女の子が消えて男性と女性の 2 人になり、次に ZWJ が消えても見た目は同じで、女性が消えて男性になり、ZWJ が消えても見た目は同じで、最後に空になる。途中の形は赤い。肌の色付きの親指は黄色の親指になってから空になり、日本の国旗は J の文字になってから空になる。書記素クラスターごとに消すと、家族の絵文字は 1 回で空になる" caption="コードポイントごとに消すと、元の文字列に無かった形が途中に現れる" align="center" >}}

家族の絵文字は、末尾にいる女の子を消した時点で男性と女性の 2 人に分かれ、消し切るまでに 5 回押す必要がありました。そのうち 2 回は ZWJ が消えるだけで、見た目は変わりません。肌の色を変えた親指は、修飾子だけが消えて黄色い親指になります。国旗は、Regional Indicator の J だけが残ります。画面の幅に合わせて行を切り詰めた表示でも、ZWJ で終わる家族の前半や、修飾子が外れた絵文字が出ていました。

カーソルの移動・削除・切り詰めは、書記素クラスターの単位で行います。区切りは自分で書かず、Go なら uniseg、Rust なら [unicode-segmentation](https://github.com/unicode-rs/unicode-segmentation)、JavaScript なら `Intl.Segmenter` が返すものを使います。以下は、Go で表示幅に収まるだけの書記素クラスターを残して切り詰める例です。

```go
// truncate は、表示幅が width を超えない書記素クラスターの並びまで s を切り詰める。
func truncate(s string, width int) string {
	var b strings.Builder
	used := 0
	g := uniseg.NewGraphemes(s)
	for g.Next() {
		w := g.Width()
		if used+w > width {
			break
		}
		b.WriteString(g.Str())
		used += w
	}
	return b.String()
}
```

<br>

結合文字も同じ問題を起こします。macOS で作られたファイル名には、é を e と U+0301 に分けて書いたものがあり、端末に貼り付けると分解した形のまま入力されます。

prompt で作った入力欄では、分解した形で書いた単語の上で Ctrl+→ を押すと、カーソルが e と U+0301 の間に止まりました。そこで Backspace を押すと、残したいアクセントだけが消えます。単語の区切りを探す処理が、結合文字を区切りと見なしていたためです。

位置の単位を取り違えると、文字が化けるだけでなくプログラムが落ちます。prompt の入力欄で、日本語を含む行の末尾に、次の行へ続ける記号のバックスラッシュを書いて Enter を押すと、アプリケーションが落ち、端末が入力を 1 文字ずつ受け取るモードのまま残りました。

位置をコードポイントで数える所と、UTF-8 のバイトで数える所が混ざっていたためです。日本語の 1 文字は 3 バイトなので、ASCII だけの行では一致していた 2 つの位置が日本語を含む行でずれ、ずれた位置で文字列の範囲外にアクセスして落ちました。端末は、打った文字が画面に出ないなど、使いにくい状態のまま残ります。

---

### 表示幅は描く端末と同じ幅の表で測る

端末に文字を並べるプログラムは、各文字が何セルを占めるかを計算してカーソルや罫線の位置を決めます。この幅の目安が、Unicode の [East Asian Width](https://www.unicode.org/reports/tr11/)（東アジアの文字幅）という属性です。漢字やかなは 2 セル、ASCII や半角カナは 1 セルで、○ や ① のように環境によって 1 にも 2 にもなる曖昧幅（Ambiguous）の文字もあります。😀 のように絵文字として描く文字の多くは 2 セルです。

幅を計算するライブラリは、この属性などから作った幅の表（文字ごとのセル数の一覧）を持っています。

問題は、幅を計算するライブラリと描く端末が、同じ幅の表を使っているとは限らないことです。go-runewidth に、東アジアの設定（曖昧幅の文字を 2 セルと数える設定）を切り替えて幅を聞くと次のようになります。

| 文字 | 通常 | 東アジアの設定 |
|---|---:|---:|
| ｶ | 1 | 1 |
| ﾞ | 1 | 1 |
| ① | 1 | 2 |
| ○ | 1 | 2 |
| α | 1 | 2 |
| タブ | 0 | 0 |

ｶ と ﾞ は 1 セルずつで、端末も半角の「ｶﾞ」を 2 セルで描きます。冒頭の表で uniseg が「ｶﾞ」を 1 と答えたのは、書記素クラスター 1 つにまとめて幅を数えたためで、この文字では端末とずれます。

タブは 0 セルと答えています。go-runewidth には「次のタブ位置まで進む」という考えが無いためです。一方、端末はタブを最大 8 セル先のタブ位置まで進めます。prompt の入力欄では、タブを含む行を貼り付けると、カーソルが文字より左に描かれ、長い行を消す時に消し残しが出ました。

{{< figure src="images/width.webp" alt="端末のセルの並びを 4 段で描いた図。上の組は a、タブ、b と入力した後で、端末は b を 9 セル目に描きカーソルを 10 セル目に置くが、タブを 0 セルと数えたプログラムは b を 2 セル目、カーソルを 3 セル目と考える。下の組は ｶﾞ の後に x を描く場合で、端末は ｶ と ﾞ と x を 1 セルずつ並べるが、ﾞ に 1 を 2 回足したプログラムでは ﾞ が 2 セルを占め、x が 4 セル目に来る" caption="プログラムが数えた幅と、端末が描いた幅がずれると、カーソルや次に描く文字の位置がずれる" align="center" >}}

<br>

図の下にある組は、ライブラリのバージョンを上げただけで幅が変わった例です。bsky の画面を描く TUI ライブラリの [ratatui](https://github.com/ratatui/ratatui) は、文字の幅を [unicode-width](https://github.com/unicode-rs/unicode-width) で数えます。unicode-width は 0.2.3 で、半角濁点（U+FF9E）の幅を 0 から 1 に変えました。

| 文字 | unicode-width 0.2.2 | unicode-width 0.2.3 |
|---|---:|---:|
| ﾞ（U+FF9E） | 0 | 1 |
| ｶﾞ | 1 | 2 |

ratatui は、半角濁点が 0 と数えられる前提で 1 を足していました。0.2.3 との組み合わせでは 1 に 1 が足され、「ｶﾞ」が 3 セルと計算されて、後ろの文字が 1 セル右にずれて表示されます。bsky では、unicode-width を 0.2.2 に戻すと表示も元に戻りました。

bsky では、タブや改行コードの CR を含む投稿でも、表示がずれました。タブや CR で区切られていた単語が、描く時に区切りを捨てたためにくっつきました。入力欄のカーソルは、幅を数える時にタブや CR を 1 セルずつ数えた分だけ右にずれました。go-runewidth がタブを 0 セルと数えたのとは逆向きの食い違いです。

描く端末どうしでも、幅は揃っていません。端末エミュレーター [Ghostty](https://ghostty.org/) の作者による「[Grapheme Clusters and Terminal Emulators](https://mitchellh.com/writing/grapheme-clusters-in-terminals)」は、主な端末を並べて比べています。ZWJ でつないだ絵文字を 2 セルで描く端末もあれば、つないだ絵文字の数だけ幅を足す端末もあります。幅の計算は、描く端末と同じ幅の表を同じバージョンで使い、バージョンを上げる時は表示のテストで確かめる必要があります。

---

### BOM は読み込みの入口で外す

幅 0 の文字が、表示だけでなくデータそのものを壊す例が BOM です。BOM（byte order mark、バイトオーダーマーク）は、ファイルの先頭に置く U+FEFF という文字です。UTF-16 では、先頭が FE FF か FF FE かでバイトの並び順を示します。UTF-8 では並び順が無いので、EF BB BF の 3 バイトで「このファイルは UTF-8 である」と示すだけです。

[Unicode Standard の第 2 章](https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-2/)にある通り、UTF-8 では必須ではありませんが、表計算ソフトが書き出す CSV や、古い Windows のメモ帳で UTF-8 として保存したテキストには付いていることがあります。

BOM を外さずに CSV をパースすると、BOM は 1 列目にある列名の一部になります。以下は、BOM を外す前の sqly v0.27.0 と現在の v1.7.5 で、BOM 付きの CSV を読み込んだ結果です。

```text
$ printf '\xef\xbb\xbfid,name\n1,alice\n2,bob\n' > bom.csv

$ sqly bom.csv --sql 'SELECT id, name FROM bom'     # v0.27.0
execute query error: SQL logic error: no such column: id (1): SELECT id, name FROM bom

$ sqly bom.csv --sql "SELECT name, hex(name) FROM pragma_table_info('bom')"   # v0.27.0
+------+------------+
| name | hex(name)  |
+------+------------+
| ﻿id   | EFBBBF6964 |
| name | 6E616D65   |
+------+------------+

$ sqly bom.csv --sql 'SELECT id, name FROM bom'     # v1.7.5
+----+-------+
| id | name  |
+----+-------+
|  1 | alice |
|  2 | bob   |
+----+-------+
```

v0.27.0 の表では、列名が `id` と表示されているのに、中身は EF BB BF 69 64 の 5 バイトです。BOM は幅 0 なので、表の上では見分けが付きません。

{{< figure src="images/bom.webp" alt="BOM 付きの CSV の 1 行目を 4 段で描いた図。ファイルのバイト EF BB BF 69 64 2C 6E 61 6D 65 0A は、UTF-8 としてデコードすると U+FEFF、i、d、カンマ、n、a、m、e、改行になる。CSV の列名では、1 列目が U+FEFF と id を合わせたものになり、2 列目は name になる。表には id と表示されるが、SQL の id とは一致せず no such column になる" caption="BOM は 1 列目の列名にくっつき、画面では見えないまま SQL の列名と食い違う" align="center" >}}

<br>

標準ライブラリの CSV パーサーも、BOM を外しません。Python の `csv` は文字コードに `utf-8-sig` を指定した時だけ外し、Go の `encoding/csv` は外す手段を持ちません。以下の上 2 行は Python で 1 行目を辞書としてパースした時のキー、3 行目は Go でパースした 1 列目の列名です（コードは [lab](https://github.com/nao1215/debimate/tree/main/content/notes/computer-systems/unicode-text-length/lab/bom) にあります）。

```text
utf-8     keys=['\ufeffid', 'name']  row.get('id')=None
utf-8-sig keys=['id', 'name']  row.get('id')='1'
header[0]="\ufeffid", == "id": false
```

<br>

BOM は 1 つとは限りません。filesql では、BOM を外すようにした後も、BOM が 2 つ付いたファイルで同じ症状が出ました。BOM を付けるプログラムが、既に BOM の付いた文字列の前にもう 1 つ付けると 2 つになり、表計算ソフトが書き出した CSV を別のツールで書き出し直すと起きることがあります。

外す処理は、すべての形式が通る読み込みの入口に 1 か所だけ置き、先頭に並ぶ BOM をすべて外します。先頭以外にある U+FEFF は、ファイルに書かれた文字として残します。

---

### 文字コードは推測せず、デコードできなければ止める

UTF-8 以外の文字コードで書かれたファイルには、BOM のような目印も無く、さらに厄介です。Shift_JIS のバイト列は多くの場合 UTF-8 として正しくないので、取り込む時に確かめていれば気付けます。しかし、確かめずに取り込むと、化けた文字が正常終了のまま流れていきます。sqly では、Shift_JIS の CSV を SQLite に取り込み、`.save` で書き戻すまでの 3 か所で文字が化けていました。

{{< figure src="images/encoding.webp" alt="CSV ファイル（Shift_JIS のバイト）から SQLite の表（TEXT は UTF-8）へ、さらに .save で同じ CSV ファイルへ書き戻す流れ。取り込む所に 1 と 2、書き戻す所に 3 の印がある。1 は UTF-8 として取り込み、東京が 4 つの化けた文字になる。2 は --encoding shift-jis で取り込み、デコードできないバイトが U+FFFD になる。3 は .save で書き戻し、UTF-8 で書かれて次に取り込むと化ける。どれもエラーにならない" caption="読み込みで 2 か所、書き戻しで 1 か所、エラーにならないまま文字が化けていた" align="center" >}}

1 つ目は、UTF-8 かどうかを確かめずに取り込んでいたことです。SQLite は TEXT を UTF-8 として扱うので、「東京」の Shift_JIS の 4 バイトは、4 つの化けた文字として保存されました。v1.0.0-rc7 では `length(city)` が 4 を返し、終了コードは 0 でした。

現在の sqly は、UTF-8 として正しくないファイルを拒否し、`--encoding` を付けて取り込み直すよう案内します。長い行は、途中で折り返して載せています。

```text
$ sqly sjis.csv --sql 'SELECT city FROM sjis'
import failed, and no table was created or changed: failed to import file sjis.csv:
  failed to read CSV record: filesql: invalid UTF-8: byte 0x93 at offset 5 is not part of a valid character
hint: this file is not UTF-8. If it is Shift-JIS, EUC-JP, or another legacy encoding,
  load it with --encoding (one of: utf-8|shift-jis|euc-jp|iso-2022-jp|utf-16le|utf-16be), e.g. --encoding shift-jis.
```

<br>

2 つ目は、`--encoding shift-jis` を付けると、壊れたファイルも置換文字（U+FFFD）入りで読み込めてしまったことです。Go の [golang.org/x/text](https://pkg.go.dev/golang.org/x/text/encoding/japanese) のデコーダーは、ブラウザが従う文字コードの規則である [WHATWG Encoding Standard](https://encoding.spec.whatwg.org/) に従い、デコードできないバイトを U+FFFD に置き換えます。エラーは返しません。

```go
broken := []byte{0x93, 0x8c, 0xff, 0xfe} // 「東」の後に、Shift_JIS としても意味の無いバイト
text, err := japanese.ShiftJIS.NewDecoder().Bytes(broken)
fmt.Printf("%q, err=%v\n", text, err)
```

```text
"東��", err=<nil>
```

置き換えるデコーダーを使う時は、置き換えが起きたかを自分で確かめる必要があります。Shift_JIS には U+FFFD という文字が無く、正しい Shift_JIS のバイト列をデコードすれば U+FFFD は出てこないので、結果に U+FFFD があれば置き換えが起きた証拠です。UTF-16 は U+FFFD を表せるので、結果ではなく元のバイト列を確かめます。現在の sqly は、置き換えが起きたら読み込みを止めます。

3 つ目は書き戻しです。`.save` は取り込んだ時の文字コードに関係なく UTF-8 で書いていたので、Shift_JIS として取り込んだファイルが黙って UTF-8 に変わり、次に同じコマンドで取り込むと化けました。書き戻す時は、取り込んだ時の文字コードで書きます。

x/text のエンコーダーは、Shift_JIS に無い文字（𩸽 など）を渡すとエラーを返します。`encoding.ReplaceUnsupported` で包むとエラーの代わりに 0x1A という制御文字へ置き換えますが、黙って文字を失うので、書けない文字があれば止める方が安全です。

<br>

書き出す文字コードによっては、文字そのものが文字コードの合図として解釈されます。ISO-2022-JP は、ESC（0x1B）で始まるエスケープシーケンスで、ASCII と漢字の集合を切り替える文字コードです。端末の色付けに使う制御文字を含むログを取り込んだ時などは、値に ESC が入ります。filesql では、値に ESC を含む表を ISO-2022-JP で書き出してデコードし直すと、その値より後ろがすべて漢字に化けました。

```text
書いたバイト列: "name,id\nx\x1b$By,1\nz,2\n", err=<nil>
デコードした値: "name,id\nx彅確憘肝", err=<nil>
```

値に含まれる `ESC $ B` が「ここから漢字」という合図として解釈され、後ろの `y,1` 改行 `z,2` 改行の 8 バイトが、2 バイトずつ区切って漢字の表で引かれ、4 文字の漢字になりました。2 行目の id と 3 行目は表から無くなりましたが、エンコードする時もデコードする時もエラーは出ていません。

どの例でも、化けたデータが正常終了のまま残るのが一番困ります。sqly は文字コードを推測せず、デコードできないと止まって利用者に `--encoding` を選んでもらう形にしました。推測が外れて化けたまま進むより、止まった方が壊れたことに気付けるからです。

---

### 見た目や意味が同じ、別の文字

ここまでは、文字を正しく数え、正しくデコードする話でした。最後は、同じ意味の文字が別のコードポイントで書かれる話です。日本語の文では、`alice＠example.com` のように全角の ＠（U+FF20）でメールアドレスを書く人がいます。ログの秘密情報を伏せる embargo は、v0.14.0 まで全角で書いたメールアドレスを伏せずにログへ出していました。

```text
== embargo v0.13.0
連絡先 alice＠example.com
  -> 連絡先 alice＠example.com
== embargo v0.20.1
連絡先 alice＠example.com
  -> 連絡先 [REDACTED]
     email: バイト 10 から 29 = "alice＠example.com"
```

全角の英数字と記号（U+FF01〜U+FF5E）は、コードポイントから 0xFEE0 を引くと半角の文字になります。そこで、全角を半角に置き換えた文字列で探す方法がよく使われます。本記事では、この置き換えを畳む（fold）と呼びます。

ただし、全角の文字は UTF-8 で 3 バイト、半角は 1 バイトなので、畳むと後ろの位置がずれます。見つけた範囲を元の文字列で伏せるには、畳んだ文字列の各バイトが元の何バイト目から来たかを対応表として残しておきます。

{{< figure src="images/fold.webp" alt="上の段が元の文字列のバイトで、10 から 19 番目に a l i c e、全角の ＠ の 3 バイト EF BC A0、e x が並ぶ。下の段が畳んだ文字列で、a l i c e、半角の @ の 40、e x が 10 から 17 番目に並ぶ。各バイトの下に、元の位置を表す数字が付いていて、15 までは同じだが、畳んだ 16 は元の 18、17 は元の 19 を指す。畳んだ文字列で見つけた範囲 10〜27 は、対応表で 10〜29 に戻してから伏せる" caption="全角の ＠ を半角に畳むと、＠ より後ろは 2 バイトずれるので、位置の対応表で元に戻す" align="center" >}}

範囲は、始まりを含み終わりを含まない形で表しています。「バイト 10 から 29」は、10〜28 番目の 19 バイトです。範囲の終わりは文字列の末尾を指すこともあるので、対応表には文字列の終わりに当たる位置も 1 つ足しておきます。全角の数字で書いた電話番号も、同じ方法で見つけられます。`０９０－１２３４－５６７８` は 13 文字ですが、伏せる範囲は元の文字列で 39 バイト分です。

```text
電話 ０９０－１２３４－５６７８
  -> 電話 [REDACTED]
     phone_jp: バイト 7 から 46 = "０９０－１２３４－５６７８"
```

<br>

Bluesky のハッシュタグでも、全角が問題になりました。公式のアプリは全角の ＃ も # と同じに扱ってハッシュタグにしますが、bsky では、全角の ＃ で書いたハッシュタグがリンクにならず、公式のアプリと違う表示になっていました。また、日本語の文で「（https://example.com）」のように全角の括弧で囲んだ URL はリンクにならず、全角の句読点が続く URL は、句読点より後ろの文までリンクに含まれていました。日本語の文は単語の間に空白が無いので、どこで URL が終わるかを全角の記号で判断する必要があります。

大文字と小文字を区別しない比較も、同じ種類の問題です。[SQLite](https://www.sqlite.org/faq.html#q18) は ASCII の大文字と小文字だけを同じと見なすので、xay と xAy は同じ表の名前ですが、xäy と xÄy は別の表になります。一方、Excel のシート名は ä と Ä も同じと見なし、excelize も Go の `strings.EqualFold`（大文字と小文字を区別せずに比べる関数）で名前を比べます。filesql では、xäy と xÄy の 2 つの表を Excel のファイルに保存し直すと、1 枚のシートに重なって片方の表が失われ、それでも保存は成功と報告されていました。

```text
CREATE TABLE xay: ok
CREATE TABLE xAy: table "xAy" already exists
CREATE TABLE xäy: ok
CREATE TABLE xÄy: ok
EqualFold(xäy, xÄy) = true
NewSheet(xäy)=1 NewSheet(xÄy)=1 sheets=["Sheet1" "xäy"]
```

上 4 行は SQLite で表を作った結果、下 2 行は excelize で xäy と xÄy のシートを作った結果です。2 回とも同じシート番号 1 が返り、シートは 1 枚しか増えませんでした。

名前を小文字にそろえて比べる方法でも足りません。ギリシャ文字のシグマには、小文字の σ と、語末で使う ς があります。Go の `strings.ToLower` は σ と ς を別の文字のまま残しますが、`strings.EqualFold` は同じ文字と見なします。名前の重複は、書き出し先と同じ比べ方で調べます。

結合文字の節で触れた é の 2 つの書き方も、意味が同じで中身が違う文字です。比べる前にどちらかの形へそろえる処理を Unicode 正規化（normalization）と呼び、合成した形を NFC、分解した形を NFD と呼びます。

全角を半角にそろえるだけなら、Unicode 正規化の NFKC（見た目の違いだけの文字を基本の文字へ寄せる正規化）でもできます。ただし NFKC は、① を 1 に、半角カナを全角カナにするなど、全角の英数字以外も変えます。どちらを使っても長さが変わるので、元の文字列のどこを伏せるかを知るには、対応表が必要です。

---

### 不具合に出会った時に確かめる順

文字数・幅・BOM・文字コードの不具合は、どれも「どの単位で、どこで扱うか」を決めていないことから起きていました。出会った時は、次の順に確かめると原因に近づけます。

1. 上限や位置を決めた仕様は、どの単位で数えているか。
2. カーソル・削除・切り詰めは、書記素クラスターの単位か。
3. 幅を測るライブラリと描く端末は、同じ幅の表とバージョンか。
4. BOM と文字コードを入口 1 か所で扱い、デコードできなければ止めているか。
5. 全角や大文字小文字を比べる時、書き出し先や検査する相手と同じ比べ方をしているか。

テストには、本記事で不具合を出した文字列をそのまま使えます。家族 4 人の絵文字（7 コードポイント、25 バイト）、👍🏽、🇯🇵、e と U+0301、ｶﾞ、𩸽、タブ、先頭の BOM、全角の ＠ と ＃、xäy と xÄy、σ と ς です。

[Property-Based Testing](/notes/software-testing/property-based-testing/) の生成に混ぜたり、画面の幅を変えながら書記素クラスターが割れていないかを確かめたりすると、手で選んだ例では見落とす組み合わせも拾えます。BOM の有無や改行コードで結果が変わらないことは、[Metamorphic Testing](/notes/software-testing/metamorphic-testing/) の関係として書けます。
