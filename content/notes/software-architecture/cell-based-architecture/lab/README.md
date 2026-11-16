# Cell-based Architecture の実験

## ポイズンピル（run.py）

8 台のアプリケーションサーバー（worker.py）の前に nginx を置き、顧客 c007 がポイズンピルを 1 回送った時に、何台が落ち、何人の顧客の要求が失敗するかを数えます。nginx の振り分けだけを 4 通りに変えます。

- shared: 8 台を 1 つの upstream にまとめる
- shared_post: shared と同じで、ポイズンピルだけ POST で送る
- cells: 2 台ずつ 4 つのセルに分け、顧客 ID からセルを引く表（map）で振り分ける
- shuffle: 顧客ごとに 8 台から 2 台の組を割り当てる（28 通り）

nginx の upstream と proxy の設定は、どの方式も既定のままです。手元では nginx 1.29.5（nginx:alpine のイメージ）と Python 3.14.4 で動かしました。docker と、ポート 9001〜9008・18080 が空いていることが要ります。

```sh
LAB_WORK=<作業用のディレクトリ> python3 run.py
```

要約は output.txt、要求ごとの記録と台の停止・起動の時刻は results/<方式>.json に書きます。要求の数や時刻は実行ごとに少し変わります。

## セルを足した時の移動（remap.py）

10,000 人の顧客を 4 つのセルに割り当てた後に 5 つ目のセルを足し、剰余・コンシステントハッシュ法・割り当て表で、別のセルへ移る顧客の数を数えます。標準ライブラリだけを使います。

```sh
python3 remap.py
```

結果は remap_output.txt と同じになります。

## 組の重なり（overlap.py）

Shuffle Sharding で台数 n と組の大きさ k を変えた時に、ポイズンピルを送る顧客の組と全て重なる確率と、一部だけ重なる確率を組み合わせの数から求めます。標準ライブラリだけを使います。

```sh
python3 overlap.py
```

結果は overlap_output.txt と同じになります。
