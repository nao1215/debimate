// Package magic は、先頭が "FUZZ" の入力だけで壊れる 2 つの関数を持つ。
// 2 つは同じ条件を、1 バイトずつ比べるか、4 バイトをまとめて比べるかだけが違う。
package magic

// ByteByByte は先頭の 4 バイトを 1 バイトずつ比べる。
func ByteByByte(b []byte) {
	if len(b) >= 4 && b[0] == 'F' {
		if b[1] == 'U' {
			if b[2] == 'Z' {
				if b[3] == 'Z' {
					panic("FUZZ")
				}
			}
		}
	}
}

// AtOnce は先頭の 4 バイトを 1 回の比較で比べる。
func AtOnce(b []byte) {
	// 0x5a5a5546 は、"FUZZ" の 4 バイトを 1 つの整数として読んだ値。
	if len(b) >= 4 && uint32(b[0])|uint32(b[1])<<8|uint32(b[2])<<16|uint32(b[3])<<24 == 0x5a5a5546 {
		panic("FUZZ")
	}
}
