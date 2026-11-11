package main

import (
	"bufio"
	"fmt"
	"os"
)

func main() {
	w := bufio.NewWriter(os.Stdout)
	fmt.Fprintln(w, "hello") // 失敗はバッファに溜まり、Flush でまとめて返る

	if err := w.Flush(); err != nil {
		fmt.Fprintln(os.Stderr, "write error:", err)
		os.Exit(1)
	}
	if err := os.Stdout.Close(); err != nil {
		fmt.Fprintln(os.Stderr, "close error:", err)
		os.Exit(1)
	}
}
