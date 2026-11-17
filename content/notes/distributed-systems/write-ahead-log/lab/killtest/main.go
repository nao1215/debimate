// killtest は、PostgreSQL のコンテナに 1 行ずつ INSERT を送り続け、
// 途中で docker kill（SIGKILL）で止めてから起動し直し、成功が返った行のうち
// 何行が残ったかを数える。
//
//	go run ./killtest -setting default
//	go run ./killtest -setting synchronous_commit=off
//	go run ./killtest -setting fsync=off
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"

	"github.com/jackc/pgx/v5"
)

const (
	container = "walpg"
	volume    = "walpgdata"
	image     = "postgres:18-alpine"
	dsn       = "postgres://postgres:pw@127.0.0.1:55432/postgres"
)

type ack struct {
	ID   int64   `json:"id"`
	AtMs float64 `json:"at_ms"` // 計測の開始からの、成功が返った時刻
	LSN  string  `json:"lsn"`   // INSERT の直後の WAL の挿入位置
}

type poll struct {
	AtMs  float64 `json:"at_ms"`
	Write string  `json:"write_lsn"` // OS に渡した（write した）位置
	Flush string  `json:"flush_lsn"` // fsync まで済んだ位置
}

type result struct {
	Setting  string  `json:"setting"`
	KillAtMs float64 `json:"kill_at_ms"`
	Acked    int     `json:"acked"`
	Survived int     `json:"survived"`
	Lost     []int64 `json:"lost"`
	Acks     []ack   `json:"acks"`
	Polls    []poll  `json:"polls"`
}

func run(args ...string) {
	out, err := exec.Command("docker", args...).CombinedOutput()
	if err != nil {
		fmt.Fprintf(os.Stderr, "docker %s: %v\n%s", strings.Join(args, " "), err, out)
		os.Exit(1)
	}
}

func connect(ctx context.Context) *pgx.Conn {
	for i := 0; i < 100; i++ {
		c, err := pgx.Connect(ctx, dsn)
		if err == nil {
			if err = c.Ping(ctx); err == nil {
				return c
			}
		}
		time.Sleep(300 * time.Millisecond)
	}
	fmt.Fprintln(os.Stderr, "cannot connect")
	os.Exit(1)
	return nil
}

func main() {
	setting := flag.String("setting", "default", "default / synchronous_commit=off / fsync=off")
	killAfter := flag.Duration("kill-after", 2*time.Second, "INSERT を始めてから止めるまで")
	out := flag.String("out", "", "結果の JSON")
	flag.Parse()
	ctx := context.Background()

	exec.Command("docker", "rm", "-f", container).Run()
	exec.Command("docker", "volume", "rm", volume).Run()
	dockerArgs := []string{"run", "-d", "--name", container, "-e", "POSTGRES_PASSWORD=pw",
		"-p", "127.0.0.1:55432:5432", "-v", volume + ":/var/lib/postgresql", image}
	if *setting != "default" {
		dockerArgs = append(dockerArgs, "-c", *setting)
	}
	run(dockerArgs...)
	time.Sleep(3 * time.Second) // 初期化の途中の一時的なサーバーに繋がないよう待つ

	c := connect(ctx)
	if _, err := c.Exec(ctx, "CREATE TABLE t (id bigint PRIMARY KEY)"); err != nil {
		panic(err)
	}
	var shown string
	c.QueryRow(ctx, "SELECT current_setting('synchronous_commit') || ' / fsync=' || current_setting('fsync')").Scan(&shown)
	fmt.Fprintln(os.Stderr, "synchronous_commit =", shown)

	poller := connect(ctx)
	start := time.Now()
	ms := func() float64 { return float64(time.Since(start).Microseconds()) / 1000 }

	var mu sync.Mutex
	res := result{Setting: *setting}
	stop := make(chan struct{})
	go func() { // 5ms ごとに WAL の書いた位置と同期した位置を記録する
		for {
			select {
			case <-stop:
				return
			default:
			}
			var w, f string
			if err := poller.QueryRow(ctx,
				"SELECT pg_current_wal_lsn()::text, pg_current_wal_flush_lsn()::text").Scan(&w, &f); err != nil {
				return
			}
			mu.Lock()
			res.Polls = append(res.Polls, poll{AtMs: ms(), Write: w, Flush: f})
			mu.Unlock()
			time.Sleep(5 * time.Millisecond)
		}
	}()
	go func() {
		time.Sleep(*killAfter)
		mu.Lock()
		res.KillAtMs = ms()
		mu.Unlock()
		run("kill", container) // SIGKILL。postmaster も子プロセスもまとめて止まる
		close(stop)
	}()

	for id := int64(1); ; id++ {
		var lsn string
		err := c.QueryRow(ctx, "INSERT INTO t VALUES ($1) RETURNING pg_current_wal_insert_lsn()::text", id).Scan(&lsn)
		if err != nil {
			break // 止めた後は失敗する。成功が返った行だけを数える
		}
		mu.Lock()
		res.Acks = append(res.Acks, ack{ID: id, AtMs: ms(), LSN: lsn})
		mu.Unlock()
	}
	<-stop
	res.Acked = len(res.Acks)

	run("start", container)
	time.Sleep(2 * time.Second)
	c2 := connect(ctx)
	present := map[int64]bool{}
	rows, err := c2.Query(ctx, "SELECT id FROM t")
	if err != nil {
		panic(err)
	}
	for rows.Next() {
		var id int64
		rows.Scan(&id)
		present[id] = true
	}
	for _, a := range res.Acks {
		if present[a.ID] {
			res.Survived++
		} else {
			res.Lost = append(res.Lost, a.ID)
		}
	}
	lastMs := 0.0
	if len(res.Acks) > 0 {
		lastMs = res.Acks[len(res.Acks)-1].AtMs
	}
	fmt.Printf("setting=%s acked=%d survived=%d lost=%d last_ack_ms=%.0f\n", *setting, res.Acked, res.Survived, len(res.Lost), lastMs)
	if *out != "" {
		b, _ := json.Marshal(res)
		os.WriteFile(*out, b, 0o644)
		logs, _ := exec.Command("docker", "logs", container).CombinedOutput()
		os.WriteFile(strings.TrimSuffix(*out, ".json")+".log", logs, 0o644)
	}
	exec.Command("docker", "rm", "-f", container).Run()
	exec.Command("docker", "volume", "rm", volume).Run()
}
