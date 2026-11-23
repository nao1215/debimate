// fullwidth は、全角の @ や数字で書いたメールアドレス・電話番号を
// embargo が見つけるか、見つけた範囲が元の文字列のどこを指すかを確かめる。
package main

import (
	"fmt"

	"github.com/nao1215/embargo"
)

func main() {
	scanner := embargo.NewScanner(embargo.WithKinds(embargo.KindEmail, embargo.KindJPPhone))
	for _, text := range []string{
		"連絡先 alice@example.com",
		"連絡先 alice＠example.com",
		"電話 090-1234-5678",
		"電話 ０９０－１２３４－５６７８",
	} {
		findings := scanner.ScanString(text)
		fmt.Printf("%s\n  -> %s\n", text, embargo.Mask(text, findings))
		for _, f := range findings {
			fmt.Printf("     %s: バイト %d から %d = %q\n", f.Kind, f.Start, f.End, text[f.Start:f.End])
		}
	}
}
