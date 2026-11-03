package main

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"hash/crc32"
	"io"
	"os"
	"path/filepath"
)

// maxEntrySize は、indexを含む本体の最大バイト数です。
const maxEntrySize = 8 << 20

// Entry は WAL に 1 件追記する状態変更です。
type Entry struct {
	Index uint64
	Data  []byte
}

// Append は entry をログ末尾に追記し、ディスクに書き終えるまで戻りません。
func Append(f *os.File, e Entry) error {
	if len(e.Data) > maxEntrySize-8 {
		return fmt.Errorf("entry data exceeds %d bytes", maxEntrySize-8)
	}
	body := make([]byte, 8+len(e.Data))
	binary.BigEndian.PutUint64(body, e.Index)
	copy(body[8:], e.Data)

	record := make([]byte, 8+len(body))
	binary.BigEndian.PutUint32(record, uint32(len(body)))
	copy(record[8:], body)
	// チェックサムは長さと本体の両方を覆う。
	binary.BigEndian.PutUint32(record[4:], crc32.ChecksumIEEE(append(record[:4:4], body...)))

	if n, err := f.Write(record); err != nil {
		return err
	} else if n != len(record) {
		return io.ErrShortWrite
	}
	return f.Sync()
}

var ErrIncomplete = errors.New("incomplete record")
var ErrCorrupt = errors.New("corrupt record")

func Replay(r io.Reader) ([]Entry, error) {
	var entries []Entry
	header := make([]byte, 8)
	for {
		n, err := io.ReadFull(r, header)
		if err == io.EOF && n == 0 {
			return entries, nil
		}
		if err != nil {
			return entries, readError(err)
		}
		size := binary.BigEndian.Uint32(header)
		if size < 8 || size > maxEntrySize {
			return entries, ErrCorrupt
		}
		body := make([]byte, size)
		if _, err := io.ReadFull(r, body); err != nil {
			return entries, readError(err)
		}
		if crc32.ChecksumIEEE(append(header[:4:4], body...)) != binary.BigEndian.Uint32(header[4:]) {
			return entries, ErrCorrupt
		}
		entries = append(entries, Entry{
			Index: binary.BigEndian.Uint64(body),
			Data:  body[8:],
		})
	}
}

func readError(err error) error {
	if errors.Is(err, io.EOF) || errors.Is(err, io.ErrUnexpectedEOF) {
		return ErrIncomplete
	}
	return err
}
func must(err error) {
	if err != nil {
		panic(err)
	}
}

func main() {
	dir, err := os.MkdirTemp("", "wal-lab-")
	must(err)
	defer os.RemoveAll(dir)
	f, err := os.OpenFile(filepath.Join(dir, "wal"), os.O_CREATE|os.O_RDWR|os.O_APPEND, 0600)
	must(err)
	defer f.Close()
	for i := 1; i <= 3; i++ {
		must(Append(f, Entry{uint64(i), []byte("set balance=500")}))
	}
	raw, err := os.ReadFile(f.Name())
	must(err)
	printReplay := func(label string, data []byte) {
		entries, err := Replay(bytes.NewReader(data))
		fmt.Printf("%s: entries=%d error=%v\n", label, len(entries), err)
	}
	printReplay("complete", raw)
	printReplay("truncated tail", raw[:len(raw)-1])
	corrupt := bytes.Clone(raw)
	corrupt[len(raw)/3+16] ^= 1
	printReplay("corrupt middle", corrupt)
	boundary, err := os.OpenFile(filepath.Join(dir, "boundary"), os.O_CREATE|os.O_RDWR|os.O_APPEND, 0600)
	must(err)
	defer boundary.Close()
	data := bytes.Repeat([]byte{0x5a}, maxEntrySize-8)
	must(Append(boundary, Entry{1, data}))
	_, err = boundary.Seek(0, 0)
	must(err)
	entries, err := Replay(boundary)
	must(err)
	fmt.Printf("maximum data: bytes=%d entries=%d equal=%t\n", len(data), len(entries), len(entries) == 1 && bytes.Equal(entries[0].Data, data))
	oversized, err := os.OpenFile(filepath.Join(dir, "oversized"), os.O_CREATE|os.O_RDWR|os.O_APPEND, 0600)
	must(err)
	defer oversized.Close()
	err = Append(oversized, Entry{1, make([]byte, maxEntrySize-7)})
	info, statErr := oversized.Stat()
	must(statErr)
	fmt.Printf("oversized data: rejected=%t file_bytes=%d\n", err != nil, info.Size())
}
