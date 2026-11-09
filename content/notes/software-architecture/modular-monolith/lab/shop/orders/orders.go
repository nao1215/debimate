// Package orders は注文モジュールの公開 API です。
// 他のモジュールは、このパッケージの型と関数だけを使います。
package orders

import "example.com/shop/orders/internal/store"

// Order は、他のモジュールに見せる注文の形です。
type Order struct {
	ID    string
	Total int // 最小通貨単位（円）
}

var db = store.New()

// Place は注文を作ります。
func Place(id string, total int) Order {
	db.Save(store.Row{ID: id, Total: total, Status: "placed"})
	return Order{ID: id, Total: total}
}

// Get は注文を返します。
func Get(id string) (Order, bool) {
	r, ok := db.Find(id)
	return Order{ID: r.ID, Total: r.Total}, ok
}
