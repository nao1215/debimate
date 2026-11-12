// 語数を数える関数で、つないだ文字列の語数の関係を testing/quick を使って検証する。
// 1 つ目の関係は誤りで、2 つ目が正しい関係。
package main

import (
	"fmt"
	"math/rand"
	"strings"
	"testing/quick"
)

// Words は空白で区切った語の数を返す。
func Words(s string) int { return len(strings.Fields(s)) }

func main() {
	cfg := &quick.Config{MaxCount: 1000, Rand: rand.New(rand.NewSource(1))}

	// 関係 1: Words(a+b) = Words(a) + Words(b)
	naive := func(a, b string) bool { return Words(a+b) == Words(a)+Words(b) }
	report("Words(a+b) == Words(a)+Words(b)", quick.Check(naive, cfg))

	// 関係 2: Words(a+" "+b) = Words(a) + Words(b)
	cfg.Rand = rand.New(rand.NewSource(1))
	spaced := func(a, b string) bool { return Words(a+" "+b) == Words(a)+Words(b) }
	report(`Words(a+" "+b) == Words(a)+Words(b)`, quick.Check(spaced, cfg))

	// 手で最小化した反例
	a, b := "x", "y"
	fmt.Printf("shrunk by hand: Words(%q)=%d, Words(%q)+Words(%q)=%d\n",
		a+b, Words(a+b), a, b, Words(a)+Words(b))
}

func report(name string, err error) {
	if err == nil {
		fmt.Printf("%s: holds for 1000 inputs\n", name)
		return
	}
	ce := err.(*quick.CheckError)
	a, b := ce.In[0].(string), ce.In[1].(string)
	fmt.Printf("%s: broken at input #%d\n", name, ce.Count)
	fmt.Printf("  a = %q (%d runes)\n  b = %q (%d runes)\n", a, len([]rune(a)), b, len([]rune(b)))
}
