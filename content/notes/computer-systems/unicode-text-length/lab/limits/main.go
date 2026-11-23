// limits は、同じ文字列が上限を決めている側の単位でどう数えられるかを確かめる。
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
