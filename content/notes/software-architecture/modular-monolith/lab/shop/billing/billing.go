// Package billing は請求モジュールの公開 API です。
package billing

import (
	"fmt"

	"example.com/shop/orders"
)

// Charge は注文の金額を請求します。注文は orders の公開 API で読みます。
func Charge(orderID string) (string, error) {
	o, ok := orders.Get(orderID)
	if !ok {
		return "", fmt.Errorf("order %s not found", orderID)
	}
	return fmt.Sprintf("charged %d yen for %s", o.Total, o.ID), nil
}
