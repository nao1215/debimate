// bom は、BOM 付きの CSV を encoding/csv で読んだ時の先頭の列名を確かめる。
package main

import (
	"encoding/csv"
	"fmt"
	"strings"
)

func main() {
	r := csv.NewReader(strings.NewReader("\xef\xbb\xbfid,name\n1,alice\n"))
	header, _ := r.Read()
	fmt.Printf("header[0]=%q, == \"id\": %v\n", header[0], header[0] == "id")
}
