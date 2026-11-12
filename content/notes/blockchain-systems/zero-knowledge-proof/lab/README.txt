Zero-Knowledge Proof のノートの実験

schnorr_zk.py
  Schnorr の知識の証明を secp256k1 の上で動かす（Python 3 の標準ライブラリだけ）。
  python3 schnorr_zk.py > output/schnorr.json
  1. 1 ビットのチャレンジを 20 ラウンド。秘密鍵を知らない 1000 人の残りの数
  2. 本物のやり取りと、シミュレーターが作ったやり取りが検証を通る数
  3. Fiat-Shamir のチャレンジに R を入れない時と入れる時に、偽造した証明が通る数
  乱数は毎回変わるので、残りの数は実行ごとに少し変わる。

circom/
  circom 2 と snarkjs（Groth16）の実験。Node.js 22 で走らせた。
  ./circom/setup.sh   ライブラリ、手元だけの powers of tau、回路のコンパイル
  ./circom/run.sh     iszero.sh と bench.mjs を走らせ、output/ に書く
  iszero.sh   制約が 1 つ足りない IsZero で、x = 5 を「0 である」と証明できるか
  bench.mjs   計算の回数 N を変えた時の、証明を作る時間・検証の時間・やり直す時間

risc0/
  RISC Zero 3.0.6 の zkVM で、積が 391 になる 2 つの整数（1 より大きい）を知っていることを証明する。
  dev-mode を切り、手元の CPU で succinct receipt を作る。手順は risc0/README.txt。
  journal の 1 ビットと、期待する image ID の 1 ビットを反転すると検証が失敗するかも見る。
  risc0/output/summary.txt が実行の出力。

output/
  schnorr.json  iszero.txt  bench.tsv  versions.txt
  bench_runs.tsv は bench.mjs を 3 回走らせた記録（1 回の中で各 15 回の最小）。
  他の処理も走っている機械（32 コア、load average 30〜44）だったので、値は 2 倍ほどぶれる。
  bench.tsv は 3 回の最小。
