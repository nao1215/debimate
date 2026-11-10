// Command fsyncbench measures how batching fsync calls changes the
// throughput and latency of WAL appends on a real disk.
//
// Records use the same layout as Append in ../main.go
// (length, CRC-32, index, data), with 100-byte data.
//
// Part 1 (back to back): one writer appends batchSize records, then calls
// Sync once, for one second per batch size. It prints records per second and
// the p50/p99 of one Write+Sync round.
//
// Part 2 (fixed arrival rate): records arrive every 1 ms (1,000 records/s).
// The writer waits until batchSize records have arrived, writes them, calls
// Sync, and records latency = Sync return - arrival time for each record.
//
// Each cell is the median of three repetitions. These are measurements, so
// the numbers change between runs and machines (other processes on the
// machine show up in p99).
//
// Run (use a directory on a real disk, not tmpfs):
//
//	go run ./fsyncbench -dir /path/on/disk > fsyncbench_output.txt
package main

import (
	"encoding/binary"
	"flag"
	"fmt"
	"hash/crc32"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"time"
)

const dataSize = 100

var batchSizes = []int{1, 2, 4, 8, 16, 32, 64, 128, 256}

// encode returns one record in the format of Append in ../main.go.
func encode(index uint64, data []byte) []byte {
	body := make([]byte, 8+len(data))
	binary.BigEndian.PutUint64(body, index)
	copy(body[8:], data)
	record := make([]byte, 8+len(body))
	binary.BigEndian.PutUint32(record, uint32(len(body)))
	copy(record[8:], body)
	binary.BigEndian.PutUint32(record[4:], crc32.ChecksumIEEE(append(record[:4:4], body...)))
	return record
}

func openLog(dir string) *os.File {
	f, err := os.OpenFile(filepath.Join(dir, "wal"), os.O_CREATE|os.O_RDWR|os.O_APPEND|os.O_TRUNC, 0600)
	if err != nil {
		panic(err)
	}
	return f
}

// appendBatch writes n records in one Write and makes them durable with one Sync.
func appendBatch(f *os.File, next *uint64, n int, data []byte) {
	buf := make([]byte, 0, n*(16+len(data)))
	for i := 0; i < n; i++ {
		*next++
		buf = append(buf, encode(*next, data)...)
	}
	if _, err := f.Write(buf); err != nil {
		panic(err)
	}
	if err := f.Sync(); err != nil {
		panic(err)
	}
}

func pct(xs []time.Duration, q float64) time.Duration {
	s := append([]time.Duration(nil), xs...)
	sort.Slice(s, func(i, j int) bool { return s[i] < s[j] })
	return s[min(len(s)-1, int(q*float64(len(s))))]
}

func ms(d time.Duration) float64 { return float64(d) / float64(time.Millisecond) }

const reps = 3

func median3(xs [reps]float64) float64 {
	s := xs[:]
	sort.Float64s(s)
	return s[reps/2]
}

func backToBack(dir string, data []byte) {
	fmt.Println("\n[part 1] back to back, 1 s per batch size, median of 3")
	fmt.Println("batch  records/s  syncs/s  round_p50_ms  round_p99_ms")
	for _, b := range batchSizes {
		var rps, sps, p50, p99 [reps]float64
		for r := 0; r < reps; r++ {
			f := openLog(dir)
			var next uint64
			var rounds []time.Duration
			start := time.Now()
			for time.Since(start) < time.Second {
				t := time.Now()
				appendBatch(f, &next, b, data)
				rounds = append(rounds, time.Since(t))
			}
			sec := time.Since(start).Seconds()
			f.Close()
			rps[r], sps[r] = float64(next)/sec, float64(len(rounds))/sec
			p50[r], p99[r] = ms(pct(rounds, 0.5)), ms(pct(rounds, 0.99))
		}
		fmt.Printf("%5d %10.0f %8.0f %13.3f %13.3f\n", b, median3(rps),
			median3(sps), median3(p50), median3(p99))
	}
}

func fixedRate(dir string, data []byte) {
	const interval = time.Millisecond
	const records = 2048
	fmt.Println("\n[part 2] one record every 1 ms, wait for a full batch, then Sync, median of 3")
	fmt.Println("batch  latency_p50_ms  latency_p99_ms")
	for _, b := range batchSizes[:7] {
		var p50, p99 [reps]float64
		for r := 0; r < reps; r++ {
			f := openLog(dir)
			var next uint64
			var lat []time.Duration
			start := time.Now()
			for done := 0; done < records; done += b {
				lastArrival := start.Add(time.Duration(done+b-1) * interval)
				time.Sleep(time.Until(lastArrival))
				appendBatch(f, &next, b, data)
				now := time.Now()
				for i := done; i < done+b; i++ {
					lat = append(lat, now.Sub(start.Add(time.Duration(i)*interval)))
				}
			}
			f.Close()
			p50[r], p99[r] = ms(pct(lat, 0.5)), ms(pct(lat, 0.99))
		}
		fmt.Printf("%5d %15.3f %15.3f\n", b, median3(p50), median3(p99))
	}
}

func machine(dir string) {
	fmt.Printf("go=%s os=%s/%s cpus=%d\n", runtime.Version(), runtime.GOOS, runtime.GOARCH, runtime.NumCPU())
	if b, err := os.ReadFile("/etc/os-release"); err == nil {
		for _, l := range strings.Split(string(b), "\n") {
			if strings.HasPrefix(l, "PRETTY_NAME=") {
				fmt.Println("distro=" + strings.Trim(l[len("PRETTY_NAME="):], `"`))
			}
		}
	}
	if out, err := exec.Command("uname", "-r").Output(); err == nil {
		fmt.Println("kernel=" + strings.TrimSpace(string(out)))
	}
	if out, err := exec.Command("findmnt", "-n", "-T", dir, "-o", "SOURCE,FSTYPE,OPTIONS").Output(); err == nil {
		fields := strings.Fields(string(out))
		fmt.Println("filesystem=" + strings.Join(fields, " "))
		if len(fields) > 0 {
			dev := strings.TrimPrefix(fields[0], "/dev/")
			if out, err := exec.Command("lsblk", "-ndo", "PKNAME", "/dev/"+dev).Output(); err == nil {
				if pk := strings.TrimSpace(string(out)); pk != "" {
					dev = pk
				}
			}
			if m, err := os.ReadFile("/sys/block/" + dev + "/device/model"); err == nil {
				fmt.Println("device=" + strings.TrimSpace(string(m)))
			}
		}
	}
	fmt.Printf("record=%d bytes (data %d bytes)\n", 16+dataSize, dataSize)
}

func main() {
	dir := flag.String("dir", "", "directory on the disk to measure (required)")
	flag.Parse()
	if *dir == "" {
		fmt.Fprintln(os.Stderr, "usage: fsyncbench -dir /path/on/disk")
		os.Exit(2)
	}
	if err := os.MkdirAll(*dir, 0o755); err != nil {
		panic(err)
	}
	defer os.Remove(filepath.Join(*dir, "wal"))
	data := make([]byte, dataSize)
	for i := range data {
		data[i] = 'x'
	}
	machine(*dir)
	backToBack(*dir, data)
	fixedRate(*dir, data)
}
