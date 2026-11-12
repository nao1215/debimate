package magic

// FuzzSteps は FuzzByteByByte と同じ対象を呼び、先頭から "FUZZ" と何バイト一致したかが
// 初めて増えた時の呼び出し回数・経過時間・入力の先頭 4 バイトを STEPLOG のファイルに書く。
// -parallel 1 で走らせると、ワーカーが 1 つなので回数が実行回数になる。
// exp1_steps.sh が走らせ、figures.py の steps_animation が動く図にする。

import (
	"fmt"
	"os"
	"testing"
	"time"
)

func prefixLen(b []byte) int {
	n := 0
	for n < 4 && n < len(b) && b[n] == "FUZZ"[n] {
		n++
	}
	return n
}

func FuzzSteps(f *testing.F) {
	f.Add([]byte("seed"))
	var (
		start = time.Now()
		calls int
		best  int
	)
	f.Fuzz(func(t *testing.T, b []byte) {
		calls++
		if n := prefixLen(b); n > best {
			best = n
			head := b
			if len(head) > 4 {
				head = head[:4]
			}
			if p := os.Getenv("STEPLOG"); p != "" {
				if w, err := os.OpenFile(p, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644); err == nil {
					fmt.Fprintf(w, "%d\t%d\t%d\t%q\n", n, calls, time.Since(start).Milliseconds(), head)
					w.Close()
				}
			}
		}
		ByteByByte(b)
	})
}
