// truncate は、表示幅に収まるだけの書記素クラスターを残して切り詰める。
package main

import (
	"fmt"
	"strings"

	"github.com/rivo/uniseg"
)

// truncate は、表示幅が width を超えない書記素クラスターの並びまで s を切り詰める。
func truncate(s string, width int) string {
	var b strings.Builder
	used := 0
	g := uniseg.NewGraphemes(s)
	for g.Next() {
		w := g.Width()
		if used+w > width {
			break
		}
		b.WriteString(g.Str())
		used += w
	}
	return b.String()
}

func main() {
	s := "家族👨‍👩‍👧と日本🇯🇵"
	for w := 3; w <= 8; w++ {
		fmt.Printf("width=%d %q\n", w, truncate(s, w))
	}
}
