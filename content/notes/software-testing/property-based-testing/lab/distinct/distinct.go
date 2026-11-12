// Package distinct は、filesql の frame パッケージ（commit 014315b、2026-08-20 の main）の
// Distinct と、行の鍵を作る makeRowKey を写したもの。行は列名から値への map。
// 元: https://github.com/nao1215/filesql/blob/014315b/frame/dataframe.go
// 修正: https://github.com/nao1215/filesql/commit/305c7bf （Issue #354）
package distinct

import (
	"fmt"
	"strconv"
	"strings"
)

// Distinct は、columns の値が全て等しい行を 1 行にまとめる。
func Distinct(rows []map[string]any, columns []string) []map[string]any {
	return DistinctWith(rows, columns, makeRowKey)
}

// DistinctWith は、行の鍵を作る関数を差し替えられる Distinct（実験用に足した）。
func DistinctWith(rows []map[string]any, columns []string, rowKey func(map[string]any, []string) string) []map[string]any {
	seen := make(map[string]struct{})
	var unique []map[string]any
	for _, row := range rows {
		key := rowKey(row, columns)
		if _, exists := seen[key]; !exists {
			seen[key] = struct{}{}
			unique = append(unique, row)
		}
	}
	return unique
}

// makeRowKey は修正前の filesql と同じ。値を %v で文字列にし、NUL でつなぐ。
func makeRowKey(row map[string]any, columns []string) string {
	parts := make([]string, len(columns))
	for i, col := range columns {
		parts[i] = fmt.Sprintf("%v", row[col])
	}
	// Use null byte as separator to avoid collisions
	return strings.Join(parts, "\x00")
}

// fixedRowKey は、filesql の修正（commit 305c7bf）の鍵の作り方を、この実験の型
// （nil・string・int64）の分だけ写したもの。型ごとに 1 文字の印を付け、
// 値の文字列の前に長さを書く。数は全て float64 にしてから文字列にする。
// 元: https://github.com/nao1215/filesql/blob/305c7bf/frame/dataframe.go
func fixedRowKey(row map[string]any, columns []string) string {
	var b strings.Builder
	for _, col := range columns {
		kind, text := valueKind(row[col])
		b.WriteByte(kind)
		b.WriteString(strconv.Itoa(len(text)))
		b.WriteByte(':')
		b.WriteString(text)
	}
	return b.String()
}

func valueKind(v any) (byte, string) {
	switch value := v.(type) {
	case nil:
		return 'z', ""
	case string:
		return 's', value
	case int64:
		return 'n', strconv.FormatFloat(float64(value), 'g', -1, 64)
	default:
		return 'o', fmt.Sprintf("%v", value)
	}
}
