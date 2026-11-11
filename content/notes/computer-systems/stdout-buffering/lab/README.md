# stdio Buffering の実験

ノート「stdio Buffering - パイプにつなぐと出力が遅れる・消える理由」の実験一式です。

## 環境（2026-11-11 に計測）

- Ubuntu 26.04.1 LTS（x86_64）。coreutils は uutils 0.8.0（rust-coreutils 0.8.0-0ubuntu3）が既定で、GNU 版（gnu-coreutils 9.7-3ubuntu2.1）は `gnucat` のように `gnu` を頭に付けた名前で入っている。`cp`・`mv`・`rm` は GNU 版。
- gcc 15.2.0（glibc）、Python 3.14.4、Go 1.26.4、rustc 1.98.0。
- strace はパイプへの `write(2)` の大きさの確認に使った（C は 4096 バイト、Python は約 120KB）。

## 手順

```sh
./build.sh                       # bin/ に C・Go・Rust のプログラムを作る
./exp1_languages.sh > output/exp1.tsv   # 言語ごとの到着時刻（端末・パイプ・stdbuf -oL）
./exp2_coreutils.sh > output/exp2.tsv   # GNU と uutils のフィルタ
./exp3_sigpipe.sh   > output/exp3.txt   # | head -n 1 での終わり方
./exp4_write_error.sh > output/exp4.txt # /dev/full と閉じた標準出力
python3 exp5_interrupt.py > output/exp5.txt  # 1.2 秒で SIGINT
# output/exp2_cross.txt: GNU と uutils の stdbuf と cut を入れ替えた結果（本文のコマンドを手で実行）
# output/exp4_strace_closed.txt: >&- で起動した時の poll・fcntl・openat・write（strace -e trace=poll,fcntl,openat,write）
# output/exp6_go_checked.txt: Flush と Close を確かめる Go の例（src/hello_checked.go）を /dev/full と >&- で動かした結果
python3 ../figures.py            # 図を作り直す
```

時刻はマシンの負荷で数十ミリ秒ずれます。比べているのは「書いた直後に届くか、終了時にまとめて届くか」で、ずれは結論に影響しません。

`stamp.py` は、標準入力から届いた行に、環境変数 `T0` からの経過秒を付けて出します。読む側が受け取った時刻を測るためのものです。
