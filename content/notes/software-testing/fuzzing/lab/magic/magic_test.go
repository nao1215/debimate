package magic

import (
	"math/rand/v2"
	"testing"
)

func FuzzByteByByte(f *testing.F) {
	f.Add([]byte("seed"))
	f.Fuzz(func(t *testing.T, b []byte) { ByteByByte(b) })
}

func FuzzAtOnce(f *testing.F) {
	f.Add([]byte("seed"))
	f.Fuzz(func(t *testing.T, b []byte) { AtOnce(b) })
}

// TestRandom は、カバレッジを見ずに乱数で 4 バイトを作り、1 億回 ByteByByte を呼ぶ。
func TestRandom(t *testing.T) {
	b := make([]byte, 4)
	for i := 0; i < 100_000_000; i++ {
		v := rand.Uint32()
		b[0], b[1], b[2], b[3] = byte(v), byte(v>>8), byte(v>>16), byte(v>>24)
		func() {
			defer func() {
				if recover() != nil {
					t.Fatalf("found after %d inputs", i+1)
				}
			}()
			ByteByByte(b)
		}()
	}
	t.Logf("not found in 100,000,000 inputs")
}
