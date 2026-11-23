// count は、同じ文字列を UTF-8 のバイト・UTF-16 のコード単位・
// コードポイント・書記素クラスタ・表示幅（端末のセル数）で数えて並べる。
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
