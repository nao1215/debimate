package main

import (
	"fmt"
	"unicode/utf8"
)

func main() {
	s := "\U0001F468\u200d\U0001F469\u200d\U0001F467" // 👨‍👩‍👧
	fmt.Println("go len(s)                   =", len(s))
	fmt.Println("go utf8.RuneCountInString   =", utf8.RuneCountInString(s))
}
