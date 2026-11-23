// iso2022jp は、ESC を含む値を ISO-2022-JP で書いて読み直す。
package main

import (
	"fmt"

	"golang.org/x/text/encoding/japanese"
)

func main() {
	value := "name,id\nx\x1b$By,1\nz,2\n" // ESC $ B は ISO-2022-JP で JIS X 0208 へ切り替える合図
	written, err := japanese.ISO2022JP.NewEncoder().String(value)
	fmt.Printf("書いたバイト列: %q, err=%v\n", written, err)
	read, err := japanese.ISO2022JP.NewDecoder().String(written)
	fmt.Printf("デコードした値: %q, err=%v\n", read, err)
}
