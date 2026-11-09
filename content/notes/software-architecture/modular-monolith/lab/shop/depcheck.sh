#!/bin/sh
# ALLOW に書いた向きのモジュール間 import だけを許可します。
# go.mod のあるディレクトリで実行し、違反があれば終了コード 1 を返します。
set -eu

# モジュール名: import してよい他のモジュール（空白区切り）
ALLOW='
orders:
billing: orders
cmd: orders billing
'

mod=$(go list -m)
# 1 行に「パッケージ 直接 import するパッケージ...」を並べる（テストの import は含まない）
pkgs=$(go list -f '{{.ImportPath}}{{range .Imports}} {{.}}{{end}}' ./...)
violations=$(echo "$pkgs" | awk -v mod="$mod/" -v allow="$ALLOW" '
	BEGIN {
		n = split(allow, lines, "\n")
		for (i = 1; i <= n; i++)
			if (split(lines[i], kv, ":") == 2) ok[kv[1]] = " " kv[2] " "
	}
	# example.com/shop/billing/x -> billing
	function owner(p) { sub("^" mod, "", p); split(p, s, "/"); return s[1] }
	{
		from = owner($1)
		for (i = 2; i <= NF; i++) {
			if (index($i, mod) != 1) continue # 標準ライブラリと外部の依存
			to = owner($i)
			if (to != from && index(ok[from], " " to " ") == 0)
				printf "NG %s -> %s\n", $1, $i
		}
	}')

if [ -n "$violations" ]; then
	echo "$violations"
	exit 1
fi
echo "OK: モジュール間の import は全て許可された向きです"
