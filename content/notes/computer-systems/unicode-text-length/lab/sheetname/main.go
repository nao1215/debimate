// sheetname は、大文字と小文字だけが違う名前を SQLite と excelize がどう扱うかを確かめる。
// SQLite の確認は sheetname/sqlite_names.py で行う。
package main

import (
	"fmt"
	"strings"

	"github.com/xuri/excelize/v2"
)

func main() {
	lower, upper := "x\u00e4y", "x\u00c4y" // xäy と xÄy
	fmt.Printf("EqualFold(%s, %s) = %v\n", lower, upper, strings.EqualFold(lower, upper))

	f := excelize.NewFile()
	a, _ := f.NewSheet(lower)
	b, _ := f.NewSheet(upper)
	fmt.Printf("NewSheet(%s)=%d NewSheet(%s)=%d sheets=%q\n", lower, a, upper, b, f.GetSheetList())

	sigma, final := "\u03c3", "\u03c2" // σ と ς
	fmt.Printf("ToLower(%s)=%s ToLower(%s)=%s EqualFold=%v\n",
		sigma, strings.ToLower(sigma), final, strings.ToLower(final), strings.EqualFold(sigma, final))
}
