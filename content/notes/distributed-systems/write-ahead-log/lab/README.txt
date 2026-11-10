WAL lab

  go run .        # main.go: append, truncate and corrupt a 3-entry log, then replay it
  go test ./...

fsync batching measurement (fsyncbench/main.go, about 1 minute)

  go run ./fsyncbench -dir /path/on/a/real/disk > fsyncbench_output.txt
  python3 ../figures.py   # regenerates images/write-ahead-log_fsync_batch.svg from the output

Use a directory on a real disk, not tmpfs (/tmp may be tmpfs). The output
starts with the OS, filesystem and device. It is a measurement, so numbers
change between runs; fsyncbench_output.txt was taken on 2026-11-10 while
other processes were running on the same machine.
