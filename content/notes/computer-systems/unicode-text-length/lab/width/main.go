// width は、go-runewidth が返す幅を、東アジアの設定の有無で比べる。
package main

import (
	"fmt"

	"github.com/mattn/go-runewidth"
)

func main() {
	west := runewidth.NewCondition()
	west.EastAsianWidth = false
	east := runewidth.NewCondition()
	east.EastAsianWidth = true
	for _, x := range []struct{ label, s string }{
		{"ｶ", "\uff76"}, {"ﾞ", "\uff9e"}, {"①", "\u2460"}, {"○", "\u25cb"}, {"α", "\u03b1"}, {"tab", "\t"}, {"BOM", "\ufeff"},
	} {
		fmt.Printf("%s\twidth=%d\teast_asian=%d\n", x.label, west.StringWidth(x.s), east.StringWidth(x.s))
	}
}
