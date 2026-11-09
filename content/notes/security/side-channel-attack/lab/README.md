# ローカル実験

## compare_timing.c（実測）

x86-64 の Linux と GCC で実行できます。計測に `rdtscp` 命令を使うので、x86-64 以外では動きません。

```sh
gcc -O2 -o compare_timing compare_timing.c
taskset -c 2 ./compare_timing
```

`taskset -c 2` は、計測中に別の CPU コアへ移らないように、プロセスをコア 2 に固定します。秘密は `rand()` で作った説明用の値で、プロセスの外には出ません。ネットワークにも接続しません。

`output.txt` は次の環境で実行した結果です（2026-11-10）。

- CPU: AMD RYZEN AI MAX+ 395（TSC は 3.0 GHz 相当で、10 ns 刻みで進む）
- OS: Linux 7.0.0、CPU の周波数ガバナは powersave
- コンパイラ: GCC 15.2.0、`-O2`
- 同じマシンで他の作業が動いており、ロードアベレージは 15〜30 前後

時間は CPU の周波数と他のプロセスの影響を受けるので、実行するたびに値が変わります。同じバイナリを 3 回実行した時の「秘密を復元できた回数（20 回中）」は次の通りでした。

| 1 候補あたりのサンプル数 | 10 | 30 | 100 | 300 |
|---|---|---|---|---|
| early_exit | 0〜7 | 16〜19 | 18〜20 | 14〜20 |
| constant_time | 0 | 0 | 0 | 0 |

`-O2` の `constant_time_equal` に条件分岐が無いことは、次で確認できます（SIMD 命令に展開され、`j` で始まる命令が出ない）。

```sh
objdump -d --no-show-raw-insn compare_timing | awk '/<constant_time_equal>:/,/^$/'
```

## simulate_remote.py（シミュレーション）

ネットワークの揺らぎを乱数で作ったシミュレーションです。実測ではありません。NumPy が必要です。

```sh
uv run --with numpy python simulate_remote.py
```

`sim_output.txt` は乱数の種を固定した実行結果です。
