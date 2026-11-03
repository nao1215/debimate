package main

import (
	"bytes"
	"errors"
	"io"
	"os"
	"path/filepath"
	"testing"
)

func openLog(t *testing.T) *os.File {
	t.Helper()
	f, e := os.OpenFile(filepath.Join(t.TempDir(), "wal"), os.O_CREATE|os.O_RDWR|os.O_APPEND, 0600)
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(func() { f.Close() })
	return f
}
func TestSizeBoundaryRoundTrip(t *testing.T) {
	for _, size := range []int{0, maxEntrySize - 8, maxEntrySize - 7, maxEntrySize} {
		f := openLog(t)
		data := bytes.Repeat([]byte{0x5a}, size)
		err := Append(f, Entry{1, data})
		if size > maxEntrySize-8 {
			info, e := f.Stat()
			if err == nil || e != nil || info.Size() != 0 {
				t.Fatalf("oversized %d changed log: %v", size, err)
			}
			continue
		}
		if err != nil {
			t.Fatal(err)
		}
		if _, err = f.Seek(0, 0); err != nil {
			t.Fatal(err)
		}
		got, err := Replay(f)
		if err != nil || len(got) != 1 || got[0].Index != 1 || !bytes.Equal(got[0].Data, data) {
			t.Fatalf("roundtrip %d: %v", size, err)
		}
	}
}
func TestEveryTruncation(t *testing.T) {
	f := openLog(t)
	for i := 1; i <= 3; i++ {
		if err := Append(f, Entry{uint64(i), []byte("abc")}); err != nil {
			t.Fatal(err)
		}
	}
	raw, err := os.ReadFile(f.Name())
	if err != nil {
		t.Fatal(err)
	}
	const recordSize = 19
	for cut := 0; cut <= len(raw); cut++ {
		got, err := Replay(bytes.NewReader(raw[:cut]))
		if len(got) != cut/recordSize {
			t.Fatalf("cut %d: entries %d", cut, len(got))
		}
		if cut%recordSize == 0 {
			if err != nil {
				t.Fatal(err)
			}
		} else if !errors.Is(err, ErrIncomplete) {
			t.Fatalf("cut %d: %v", cut, err)
		}
	}
}
func TestMiddleCorruptionIsError(t *testing.T) {
	f := openLog(t)
	for i := 1; i <= 3; i++ {
		if err := Append(f, Entry{uint64(i), []byte("abc")}); err != nil {
			t.Fatal(err)
		}
	}
	raw, err := os.ReadFile(f.Name())
	if err != nil {
		t.Fatal(err)
	}
	for _, offset := range []int{19, 23, 35} {
		corrupt := bytes.Clone(raw)
		corrupt[offset] ^= 0xff
		got, err := Replay(bytes.NewReader(corrupt))
		if len(got) != 1 || !errors.Is(err, ErrCorrupt) {
			t.Fatalf("offset %d: %v %d", offset, err, len(got))
		}
	}
}

type failedReader struct{}

var errDisk = errors.New("disk read failed")

func (failedReader) Read([]byte) (int, error) { return 0, errDisk }
func TestIOErrorIsPreserved(t *testing.T) {
	if _, err := Replay(io.MultiReader(bytes.NewReader(nil), failedReader{})); !errors.Is(err, errDisk) {
		t.Fatal(err)
	}
}
