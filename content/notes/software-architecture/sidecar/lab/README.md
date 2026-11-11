# ローカル実験

[kind](https://kind.sigs.k8s.io/)（v0.30.0 で確認）と Docker が使える環境で実行できます。kind が PATH に無い場合は、環境変数 `KIND` に実行ファイルの場所を渡してください。

```sh
./run.sh > output.txt
```

`run.sh` は `note-sidecar` という名前の kind のクラスタ（Kubernetes v1.34.0、1 台）を作り、次のマニフェストを順に流してから、クラスタを消します。

- `job-plain.yaml`: 5 秒で終わる処理（main）に、ログを送る想定の sidecar を普通のコンテナとして同居させた Job
- `job-native.yaml`: 同じ Job で、sidecar を Sidecar Containers（`initContainers` に `restartPolicy: Always`）として置いたもの。sidecar は SIGTERM を無視する
- `job-native-term.yaml`: `job-native.yaml` の sidecar に、SIGTERM で止まる `trap` を足したもの
- `proxy-plain.yaml`: 起動するとすぐ `localhost:8080` に接続する main と、待ち受けまで 3 秒掛かるプロキシを、普通のコンテナとして並べた Pod
- `proxy-native.yaml`: 同じ構成で、プロキシを Sidecar Containers として置き、startupProbe で待ち受けを確かめる Pod

`output.txt` は 2026-11-11 に実行した結果です（見出しの文言 2 か所は、後で run.sh に合わせて手で直しました）。時刻と秒数は、イメージの取得や手元のマシンの負荷で変わります。

本文の図は、1 つ上のディレクトリの `figures.py` が `output.txt` の時刻を読んで作ります。
