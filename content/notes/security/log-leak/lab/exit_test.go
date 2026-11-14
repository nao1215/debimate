package main

import (
	"bytes"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"log/slog"
	"strings"
	"testing"
)

// 出口のテスト: 目印の偽のシークレット（canary）を入れて処理を通し、
// 出口（ここではログ）に目印がどの表現でも現れないことを確かめる。

// handleImport は不具合のある関数。失敗時に引数をまとめてログへ書く。
func handleImport(log *slog.Logger, p ImportParams) {
	log.Error("import failed", "params", fmt.Sprintf("%+v", p))
}

// handleImportFixed は、出して良い項目だけを選んで書く関数。
func handleImportFixed(log *slog.Logger, p ImportParams) {
	log.Error("import failed", "wallet", p.WalletName, "mnemonic_len", len(p.Mnemonic))
}

func forms(secret string) []string {
	return []string{
		secret,
		hex.EncodeToString([]byte(secret)),
		base64.StdEncoding.EncodeToString([]byte(secret)),
		base64.RawURLEncoding.EncodeToString([]byte(secret)),
	}
}

func checkExit(t *testing.T, handle func(*slog.Logger, ImportParams)) {
	t.Helper()
	var out bytes.Buffer
	handle(slog.New(slog.NewJSONHandler(&out, nil)), ImportParams{WalletName: "main", Mnemonic: canary})
	if out.Len() == 0 {
		t.Fatal("ログが 1 行も出ていない。出ないことを漏れないことと取り違えない")
	}
	for _, f := range forms(canary) {
		if strings.Contains(out.String(), f) {
			t.Errorf("出口に目印が出た: %q", f)
		}
	}
}

func TestImportLeaks(t *testing.T)   { checkExit(t, handleImport) }
func TestImportFixedOK(t *testing.T) { checkExit(t, handleImportFixed) }
