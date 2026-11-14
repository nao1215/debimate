// ログ漏洩のノートの実験。シークレットの値はすべて説明用の偽物（CANARY-...）。
// 外部へは何も送らない。OTel は手元の SpanRecorder だけを使う。
package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/url"
	"os"
	"runtime"
	"runtime/debug"
	"slices"
	"strconv"

	sdk "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/sdk/trace/tracetest"
	"go.opentelemetry.io/otel/trace"
)

const canary = "CANARY-abandon-ability-able"

type ImportParams struct {
	WalletName string
	Mnemonic   string
}

// 実験 1: キーの名前で消すフィルターは、値を文字列にまとめると素通りする。
func filterBypass() {
	deny := []string{"mnemonic", "private_key", "password"}
	h := slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
		ReplaceAttr: func(_ []string, a slog.Attr) slog.Attr {
			if slices.Contains(deny, a.Key) {
				return slog.String(a.Key, "[FILTERED]")
			}
			return a
		},
	})
	log := slog.New(h)
	p := ImportParams{WalletName: "main", Mnemonic: canary}
	log.Info("import", "mnemonic", p.Mnemonic)  // キーで消える
	log.Info("import", "params", fmt.Sprint(p)) // 文字列にまとめると残る
	log.Info("import", "params", fmt.Sprintf("%+v", p))
}

// Secret は書式化しても中身を出さない型（説明用の最小の例）。
type Secret struct{ v string }

func (Secret) String() string                { return "<redacted>" }
func (Secret) Format(f fmt.State, verb rune) { _, _ = f.Write([]byte("<redacted>")) }
func (Secret) LogValue() slog.Value          { return slog.StringValue("<redacted>") }

// 実験 1b: 包んだ型でも、外側の構造体の非公開フィールドに置くと fmt はメソッドを呼ばない。
func wrapped() {
	s := Secret{canary}
	fmt.Printf("direct:     %+v\n", s)
	fmt.Printf("exported:   %+v\n", struct{ S Secret }{s})
	fmt.Printf("unexported: %+v\n", struct{ s Secret }{s})
}

// 実験 2: 変換に失敗したエラー文に、入力がそのまま入るか。
func errorText() {
	_, err := strconv.Atoi(canary)
	fmt.Println("strconv.Atoi:", err)
	_, err = url.Parse("https://user:" + canary + "@example.com:port/")
	fmt.Println("url.Parse:   ", err)
	u, _ := url.Parse("https://user:" + canary + "@example.com/")
	fmt.Println("URL.String:  ", u.String())
	fmt.Println("URL.Redacted:", u.Redacted())
}

// 実験 3: 値で渡した配列は、スタックトレースに中身が 16 進で出る。
//
//go:noinline
func sign(key [2]uint64, msg string) {
	fmt.Printf("%s", debug.Stack())
	runtime.KeepAlive(key)
}

//go:noinline
func panicSign(key [2]uint64) {
	runtime.KeepAlive(key)
	panic("sign failed")
}

// 実験 4: OTel の RecordError は err.Error() とスタックを span に入れる。
//
//go:noinline
func record(s trace.Span, key [2]uint64) {
	s.RecordError(errors.New("upstream rejected token "+canary), trace.WithStackTrace(true))
	runtime.KeepAlive(key)
}

func otel() {
	r := tracetest.NewSpanRecorder()
	p := sdk.NewTracerProvider(sdk.WithSpanProcessor(r))
	_, s := p.Tracer("lab").Start(context.Background(), "pay")
	record(s, [2]uint64{0xdeadbeefcafe0001, 0x1122334455667788})
	s.End()
	for _, span := range r.Ended() {
		for _, e := range span.Events() {
			for _, a := range e.Attributes {
				fmt.Printf("%s=%s\n", a.Key, a.Value.AsString())
			}
		}
	}
}

func main() {
	switch os.Args[1] {
	case "filter":
		filterBypass()
	case "wrapped":
		wrapped()
	case "error":
		errorText()
	case "stack":
		sign([2]uint64{0xdeadbeefcafe0001, 0x1122334455667788}, "x")
	case "otel":
		otel()
	case "panic":
		panicSign([2]uint64{0xdeadbeefcafe0001, 0x1122334455667788})
	}
}
