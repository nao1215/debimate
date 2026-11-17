// killtest_mysql は killtest と同じ実験を MySQL 8.4（InnoDB）で行う。
// innodb_flush_log_at_trx_commit を 1・2・0 に変え、1 行ずつ INSERT を送り続けている途中で
// docker kill（SIGKILL）で止め、起動し直してから、成功が返った行のうち何行が残ったかを数える。
//
//	go run ./killtest_mysql -trx-commit 1
package main

import (
	"database/sql"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

	_ "github.com/go-sql-driver/mysql"
)

const (
	container = "walmy"
	volume    = "walmydata"
	image     = "mysql:8.4"
	dsn       = "root:pw@tcp(127.0.0.1:53306)/test"
)

func run(args ...string) {
	out, err := exec.Command("docker", args...).CombinedOutput()
	if err != nil {
		fmt.Fprintf(os.Stderr, "docker %s: %v\n%s", strings.Join(args, " "), err, out)
		os.Exit(1)
	}
}

func connect() *sql.DB {
	for i := 0; i < 200; i++ {
		db, err := sql.Open("mysql", dsn)
		if err == nil {
			db.SetMaxOpenConns(1)
			if err = db.Ping(); err == nil {
				return db
			}
			db.Close()
		}
		time.Sleep(500 * time.Millisecond)
	}
	fmt.Fprintln(os.Stderr, "cannot connect")
	os.Exit(1)
	return nil
}

func main() {
	trx := flag.String("trx-commit", "1", "innodb_flush_log_at_trx_commit")
	killAfter := flag.Duration("kill-after", 2*time.Second, "INSERT を始めてから止めるまで")
	noBinlog := flag.Bool("skip-log-bin", false, "binlog を切る（binlog の同期を外して redo log だけを見る）")
	flag.Parse()

	exec.Command("docker", "rm", "-f", container).Run()
	exec.Command("docker", "volume", "rm", volume).Run()
	args := []string{"run", "-d", "--name", container, "-e", "MYSQL_ROOT_PASSWORD=pw", "-e", "MYSQL_DATABASE=test",
		"-p", "127.0.0.1:53306:3306", "-v", volume + ":/var/lib/mysql", image,
		"--innodb-flush-log-at-trx-commit=" + *trx}
	if *noBinlog {
		args = append(args, "--skip-log-bin")
	}
	run(args...)
	time.Sleep(20 * time.Second) // 初期化の途中の一時的なサーバーに繋がないよう待つ

	db := connect()
	if _, err := db.Exec("CREATE TABLE t (id bigint PRIMARY KEY) ENGINE=InnoDB"); err != nil {
		panic(err)
	}
	var shown string
	db.QueryRow("SELECT @@innodb_flush_log_at_trx_commit").Scan(&shown)
	fmt.Fprintln(os.Stderr, "innodb_flush_log_at_trx_commit =", shown)

	go func() {
		time.Sleep(*killAfter)
		run("kill", container) // SIGKILL
	}()
	var acked int64
	for id := int64(1); ; id++ {
		if _, err := db.Exec("INSERT INTO t VALUES (?)", id); err != nil {
			break // autocommit。止めた後は失敗する。成功が返った行だけを数える
		}
		acked = id
	}
	db.Close()

	run("start", container)
	db2 := connect()
	var survived int64
	db2.QueryRow("SELECT COUNT(*) FROM t WHERE id <= ?", acked).Scan(&survived)
	fmt.Printf("skip-log-bin=%v innodb_flush_log_at_trx_commit=%s acked=%d survived=%d lost=%d\n", *noBinlog, shown, acked, survived, acked-survived)
	exec.Command("docker", "rm", "-f", container).Run()
	exec.Command("docker", "volume", "rm", volume).Run()
}
