# CI のベンチマークのノートの実験

計測は GitHub Actions の標準のランナー（`ubuntu-latest`、イメージ ubuntu26）で、2026-11-13 に行いました。計測のワークフローと測ったプログラムは [nao1215/ci-bench-noise](https://github.com/nao1215/ci-bench-noise) にあります。

| ワークフロー | 内容 | 回数 |
|---|---|---|
| `noise.yml` | 1 つのジョブで base（`slowdown.txt` が 0）と head（N）をビルドし、`himorime compare --against HEAD`（交互）、`himorime run` を 2 回（順番）、`hyperfine` で測る | N = 0 を 30 ジョブ（run 43338754452）、N = 2・5・10・12・15・20 を各 10 ジョブ（run 43338766280） |
| `instructions.yml` | base（0%）と head（N%）の 2 つのビルドの命令数を cachegrind で 3 回ずつ数え、`perf stat` も試し、`hyperfine` で時間も測る | N = 0・2・5 を各 8 ジョブ（run 43340072310） |

himorime は v0.5.3、閾値は時間 10%・CPU 時間 15%・メモリ 15%（著者の他の CLI と同じ）、1 側 20 回、ウォームアップ 2 回です。

| ファイル | 内容 |
|---|---|
| `extract.py` | `gh run download` で取ったアーティファクトから `output/*.csv` を作る |
| `analyze.py` | ノートの数値を全部数え直す。出力は `output/analysis.txt` |
| `paired.py` | 同じ値を、base と head を別々に選び直す方法（himorime）と、巡ごとの組で選び直す 2 つの方法で判定し直す。閾値 10%・3%・2%、巡 20・10。出力は `output/paired.txt` |
| `output/jobs.csv` | ジョブごとの CPU、イメージ、himorime の判定と変化 |
| `output/samples.csv` | 時間の生の値（ns）。`mode` が `interleaved`（himorime compare）、`sequential`（himorime run 2 回）、`hyperfine`（中央値だけ） |
| `output/instructions.csv` | ジョブごとの命令数（cachegrind の I refs）と時間 |
| `output/desktop_samples.csv` | 著者のデスクトップで `himorime compare` を回した 40 回（A/A と 5%・10%・20% を 10 回ずつ）の時間の生の値。巡の順 |

```sh
gh run download 43338754452 -R nao1215/ci-bench-noise -D noise-aa
gh run download 43338766280 -R nao1215/ci-bench-noise -D noise-slow
gh run download 43340072310 -R nao1215/ci-bench-noise -D instr
python3 -I extract.py noise-aa noise-slow --instr instr --desktop desktop
python3 -I analyze.py > output/analysis.txt
python3 -I paired.py > output/paired.txt
```

デスクトップの計測は、2026-11-13 に AMD Ryzen AI Max+ 395（32 スレッド）の Ubuntu 26.04 で、himorime v0.5.2 を使い、`ci-bench-noise` の作業ツリーで次を回しました。計測中は裏で別の作業が動いていて、負荷平均は 8 前後でした。

```sh
for s in 0 5 10 20; do for r in $(seq 1 10); do
  echo $s > slowdown.txt
  himorime compare --against HEAD --quiet --format json --output desktop/s${s}_r${r}.json himorime.yaml
  git checkout -q -- slowdown.txt
done; done
```

アーティファクトの保存期間は 90 日なので、それより後は `output/*.csv` から `analyze.py` だけを走らせてください。

`analyze.py` の判定は、himorime の時間の比べ方（中央値、閾値 10%、信頼度 0.95、パーセンタイル ブートストラップ 2,000 回）を簡単にした写しです。himorime の判定と 90 ジョブ全部で一致することも確かめています。

最初の計測（run 43337627577・43337639455）では、測ったプログラムが端数の仕事を小さな配列の並べ替えで足していたので、2% 遅くした版が 1.5% 遅くしかなりませんでした。プログラムを直して測り直したのが上の run で、ノートの数値はこちらだけを使っています。

図は 1 つ上の `figures.py` が `output/` を読んで描きます（`python3 figures.py`）。
