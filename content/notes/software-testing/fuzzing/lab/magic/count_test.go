package magic

// FuzzCount は FuzzByteByByte と同じ対象を、何回目の呼び出しで見つけたかを数えて呼ぶ。
// -parallel 1 で走らせると、ワーカーが 1 つなので回数が実行回数になる。

import (
	"fmt"
	"testing"
)

var calls int

func FuzzCount(f *testing.F) {
	f.Add([]byte("seed"))
	f.Fuzz(func(t *testing.T, b []byte) {
		calls++
		defer func() {
			if r := recover(); r != nil {
				panic(fmt.Sprintf("found at call %d of this worker", calls))
			}
		}()
		ByteByByte(b)
	})
}
