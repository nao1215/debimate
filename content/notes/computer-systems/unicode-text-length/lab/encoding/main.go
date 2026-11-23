// encoding は、Shift_JIS のバイト列を UTF-8 として扱った時と、
// x/text のデコーダー・エンコーダーに渡した時に何が返るかを確かめる。
package main

import (
	"fmt"
	"unicode/utf8"

	"golang.org/x/text/encoding"
	"golang.org/x/text/encoding/japanese"
)

func main() {
	sjis := []byte{0x93, 0x8c, 0x8b, 0x9e} // 「東京」の Shift_JIS
	fmt.Printf("1. UTF-8 として正しいか: %v, そのまま文字列にすると %q\n", utf8.Valid(sjis), string(sjis))

	text, err := japanese.ShiftJIS.NewDecoder().Bytes(sjis)
	fmt.Printf("2. Shift_JIS として読む: %q, err=%v\n", text, err)

	broken := []byte{0x93, 0x8c, 0xff, 0xfe} // Shift_JIS としても意味の無いバイトを含む
	text, err = japanese.ShiftJIS.NewDecoder().Bytes(broken)
	fmt.Printf("3. 壊れたバイトを読む: %q, err=%v\n", text, err)

	_, err = japanese.ShiftJIS.NewEncoder().String("ほっけ 𩸽")
	fmt.Printf("4. Shift_JIS に無い文字を書く: err=%v\n", err)

	out, err := encoding.ReplaceUnsupported(japanese.ShiftJIS.NewEncoder()).String("ほっけ 𩸽")
	fmt.Printf("5. ReplaceUnsupported で書く: %q, err=%v\n", out, err)
}
