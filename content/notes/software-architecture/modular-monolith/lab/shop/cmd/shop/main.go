// shop は 2 つのモジュールを 1 つの実行ファイルにまとめます。
package main

import (
	"fmt"

	"example.com/shop/billing"
	"example.com/shop/orders"
)

func main() {
	orders.Place("A-1", 1200)
	msg, err := billing.Charge("A-1")
	if err != nil {
		panic(err)
	}
	fmt.Println(msg)
}
