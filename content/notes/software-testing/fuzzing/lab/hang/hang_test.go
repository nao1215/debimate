package hang

import (
	"os"
	"strconv"
	"testing"
	"time"
)

func FuzzSleep(f *testing.F) {
	d, _ := strconv.Atoi(os.Getenv("SLEEP"))
	f.Add([]byte("seed"))
	f.Fuzz(func(t *testing.T, b []byte) {
		if len(b) > 4 {
			time.Sleep(time.Duration(d) * time.Second)
		}
	})
}
