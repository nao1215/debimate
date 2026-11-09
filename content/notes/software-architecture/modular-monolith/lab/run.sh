#!/bin/sh
# shop/ を一時ディレクトリに複製し、境界を破る変更を 1 つずつ入れて
# go build と depcheck.sh の結果を表示します。shop/ 自体は変更しません。
set -u
export GOFLAGS=-buildvcs=false # 一時ディレクトリは git の管理外なので VCS 情報を埋め込まない
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

fresh() { rm -rf "$work/shop"; cp -R "$here/shop" "$work/shop"; cd "$work/shop"; }
build() { go build ./... 2>&1 && echo "go build: 成功"; }
check() { ./depcheck.sh; echo "depcheck.sh の終了コード: $?"; }

echo "== [0] 変更前"
fresh; build; check

echo "== [1] billing が orders の internal を import する"
fresh
cat > billing/markpaid.go <<'GO'
package billing

import "example.com/shop/orders/internal/store"

// MarkPaid は orders の表の Status を直接書き換えます（境界違反）。
func MarkPaid(s *store.Store, id string) {
	r, _ := s.Find(id)
	r.Status = "paid"
	s.Save(r)
}
GO
build

echo "== [2] orders のパッケージが billing を直接 import する（パッケージの循環）"
fresh
cat > orders/charge.go <<'GO'
package orders

import "example.com/shop/billing"

// PlaceAndCharge は注文を作り、続けて請求します。
func PlaceAndCharge(id string, total int) (string, error) {
	Place(id, total)
	return billing.Charge(id)
}
GO
build

echo "== [3] orders の下に billing を呼ぶパッケージを足す（モジュール間の循環）"
fresh
mkdir -p orders/notify
cat > orders/notify/notify.go <<'GO'
package notify

import "example.com/shop/billing"

// AfterPlace は注文の直後に請求します。billing は orders に依存しているので、
// モジュールの単位では orders と billing が互いに依存します。
func AfterPlace(id string) (string, error) { return billing.Charge(id) }
GO
build; check

echo "== [4] モジュールの外の internal に orders の表を読む SQL を置く"
fresh
mkdir -p internal/ordersql
cat > internal/ordersql/ordersql.go <<'GO'
package ordersql

// UnpaidTotal は orders の表を直接読む SQL です。
const UnpaidTotal = "SELECT SUM(total) FROM orders WHERE status = 'placed'"
GO
cat > billing/report.go <<'GO'
package billing

import "example.com/shop/internal/ordersql"

// ReportQuery は請求の集計に使う SQL を返します。
func ReportQuery() string { return ordersql.UnpaidTotal }
GO
build; check
