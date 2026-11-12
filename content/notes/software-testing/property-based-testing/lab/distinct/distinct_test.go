package distinct

import (
	"encoding/binary"
	"fmt"
	"math/rand"
	"os"
	"reflect"
	"strconv"
	"strings"
	"testing"
	"testing/quick"

	"pgregory.net/rapid"
)

// 表は a と b の 2 列。セルは nil、int64、string のどれか。
type table [][2]any

func (tb table) rows() []map[string]any {
	rows := make([]map[string]any, len(tb))
	for i, r := range tb {
		rows[i] = map[string]any{"a": r[0], "b": r[1]}
	}
	return rows
}

// プロパティ: Distinct が返す行の数は、値が本当に異なる行の数に等しい。
// セルは nil・int64・string だけなので、[2]any を map の鍵にすれば
// 「型と値が両方同じ」の比較になる。
func check(tb table) error {
	want := map[[2]any]struct{}{}
	for _, r := range tb {
		want[r] = struct{}{}
	}
	rowKey := makeRowKey
	if os.Getenv("KEY") == "fixed" {
		rowKey = fixedRowKey
	}
	got := len(DistinctWith(tb.rows(), []string{"a", "b"}, rowKey))
	if got != len(want) {
		return fmt.Errorf("Distinct は %d 行、異なる行は %d 行", got, len(want))
	}
	return nil
}

// 狭いジェネレーター: 整数は 0〜9、文字列は 0〜2 文字で、文字は数字・x・NUL だけ。
const narrowRunes = "0123456789x\x00"

func narrowCell(r *rand.Rand) any {
	switch r.Intn(3) {
	case 0:
		return nil
	case 1:
		return int64(r.Intn(10))
	default:
		var b strings.Builder
		for range r.Intn(3) {
			b.WriteByte(narrowRunes[r.Intn(len(narrowRunes))])
		}
		return b.String()
	}
}

// 広いジェネレーター: 整数は int64 の全範囲、文字列は testing/quick が string に使う既定の生成。
func broadCell(r *rand.Rand) any {
	switch r.Intn(3) {
	case 0:
		return nil
	case 1:
		return r.Int63() - r.Int63()
	default:
		v, _ := quick.Value(reflect.TypeFor[string](), r)
		return v.String()
	}
}

type narrowTable table
type broadTable table

func genTable(r *rand.Rand, cell func(*rand.Rand) any) table {
	tb := make(table, r.Intn(21)) // 0〜20 行
	for i := range tb {
		tb[i] = [2]any{cell(r), cell(r)}
	}
	return tb
}

func (narrowTable) Generate(r *rand.Rand, _ int) reflect.Value {
	return reflect.ValueOf(narrowTable(genTable(r, narrowCell)))
}

func (broadTable) Generate(r *rand.Rand, _ int) reflect.Value {
	return reflect.ValueOf(broadTable(genTable(r, broadCell)))
}

// testing/quick を種 1〜SEEDS で回し、種ごとに 1 行の TSV を出す。
// 列: 種、見つけたか、何回目の入力か、反例の行数、反例。
func TestQuickSeeds(t *testing.T) {
	seeds, _ := strconv.Atoi(os.Getenv("SEEDS"))
	if seeds == 0 {
		t.Skip("SEEDS が無い")
	}
	gen := os.Getenv("GEN")
	for seed := 1; seed <= seeds; seed++ {
		cfg := &quick.Config{MaxCount: 500, Rand: rand.New(rand.NewSource(int64(seed)))}
		var err error
		if gen == "broad" {
			err = quick.Check(func(tb broadTable) bool { return check(table(tb)) == nil }, cfg)
		} else {
			err = quick.Check(func(tb narrowTable) bool { return check(table(tb)) == nil }, cfg)
		}
		ce, ok := err.(*quick.CheckError)
		if !ok {
			fmt.Printf("quick\t%s\t%d\tno\t-\t-\t-\n", gen, seed)
			continue
		}
		var tb table
		switch v := ce.In[0].(type) {
		case narrowTable:
			tb = table(v)
		case broadTable:
			tb = table(v)
		}
		fmt.Printf("quick\t%s\t%d\tyes\t%d\t%d\t%s\n", gen, seed, ce.Count, len(tb), show(tb))
	}
}

// rapid のジェネレーター。狭い・広いの範囲は上の testing/quick と同じにする。
func rapidCell(gen string) *rapid.Generator[any] {
	if gen == "edge" {
		// 境界を足したジェネレーター: 整数に、float64 で正確に表せる最大の連続した整数 2^53 の前後を混ぜる。
		return rapid.OneOf(
			rapid.Just[any](nil),
			rapid.Map(rapid.OneOf(rapid.Int64Range(0, 9), rapid.Int64Range(1<<53-2, 1<<53+2)), func(v int64) any { return v }),
			rapid.Map(rapid.StringOfN(rapid.SampledFrom([]rune(narrowRunes)), 0, 2, -1), func(v string) any { return v }),
		)
	}
	if gen == "broad" {
		return rapid.OneOf(
			rapid.Just[any](nil),
			rapid.Map(rapid.Int64(), func(v int64) any { return v }),
			rapid.Map(rapid.String(), func(v string) any { return v }),
		)
	}
	return rapid.OneOf(
		rapid.Just[any](nil),
		rapid.Map(rapid.Int64Range(0, 9), func(v int64) any { return v }),
		rapid.Map(rapid.StringOfN(rapid.SampledFrom([]rune(narrowRunes)), 0, 2, -1), func(v string) any { return v }),
	)
}

func rapidTable(gen string) *rapid.Generator[table] {
	cell := rapidCell(gen)
	row := rapid.Custom(func(t *rapid.T) [2]any { return [2]any{cell.Draw(t, "a"), cell.Draw(t, "b")} })
	return rapid.Map(rapid.SliceOfN(row, 0, 20), func(v [][2]any) table { return table(v) })
}

func TestRapid(t *testing.T) {
	gen := rapidTable(os.Getenv("GEN"))
	rapid.Check(t, func(t *rapid.T) {
		tb := gen.Draw(t, "table")
		if err := check(tb); err != nil {
			logShrink(tb)
			t.Fatalf("反例 %d 行: %s: %v", len(tb), show(tb), err)
		}
	})
}

// SHRINKLOG を指定すると、プロパティが破れた表を破れた順にそのファイルへ 1 行ずつ足す。
// 最初の行が最初に見つけた反例で、その後は rapid が縮める途中で破れた表。
func logShrink(tb table) {
	p := os.Getenv("SHRINKLOG")
	if p == "" {
		return
	}
	f, err := os.OpenFile(p, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return
	}
	defer f.Close()
	fmt.Fprintf(f, "%d\t%s\n", len(tb), show(tb))
}

// go test -fuzz に掛ける。バイト列を表に読み替える。
// 1 バイト目が行の数、各セルは 1 バイトの種類の後に、整数なら 8 バイト、
// 文字列なら 1 バイトの長さ（16 で割った余り）とその長さのバイト列。
func FuzzDistinct(f *testing.F) {
	f.Add([]byte{1, 0, 0})
	f.Fuzz(func(t *testing.T, data []byte) {
		tb := decode(data)
		if err := check(tb); err != nil {
			t.Fatalf("反例 %d 行: %s: %v", len(tb), show(tb), err)
		}
	})
}

func decode(data []byte) table {
	next := func(n int) []byte {
		if len(data) < n {
			n = len(data)
		}
		b := data[:n]
		data = data[n:]
		return b
	}
	cell := func() any {
		k := next(1)
		if len(k) == 0 {
			return nil
		}
		switch k[0] % 3 {
		case 0:
			return nil
		case 1:
			b := make([]byte, 8)
			copy(b, next(8))
			return int64(binary.LittleEndian.Uint64(b))
		default:
			n := next(1)
			if len(n) == 0 {
				return ""
			}
			return string(next(int(n[0] % 16)))
		}
	}
	h := next(1)
	if len(h) == 0 {
		return nil
	}
	tb := make(table, h[0]%21)
	for i := range tb {
		tb[i] = [2]any{cell(), cell()}
	}
	return tb
}

// 反例を短く表示する。文字列は Go の引用、整数は int64(7) の形。
func show(tb table) string {
	var b strings.Builder
	b.WriteString("[")
	for i, r := range tb {
		if i > 0 {
			b.WriteString(" ")
		}
		fmt.Fprintf(&b, "{a:%s b:%s}", showCell(r[0]), showCell(r[1]))
	}
	b.WriteString("]")
	return b.String()
}

func showCell(v any) string {
	switch x := v.(type) {
	case nil:
		return "nil"
	case int64:
		return fmt.Sprintf("int64(%d)", x)
	default:
		return strconv.Quote(x.(string))
	}
}
