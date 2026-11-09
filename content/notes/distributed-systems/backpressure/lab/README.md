# ローカル実験

Python 3.8 以降の標準ライブラリだけで実行できます。外部サービスには接続しません。

```sh
python3 queue_experiment.py results.json   # 実験 1: 上限なし / block / reject のキュー
python3 retry_amplification.py             # 実験 2: 多層の再試行で届く試行回数の最大値
```

- `output.txt` と `results.json` は Python 3.14.4 で実行した実験 1 の結果です。asyncio のタイマー精度に左右されるので、数値は実行のたびに少し変わります。
- `retry_output.txt` は実験 2 の結果です。計算だけなので毎回同じ値になります。
- `results.json` を書き換えたら、Page Bundle 直下の `figures.py`（`uv run --with matplotlib python figures.py`）で `images/queue_growth.svg` を作り直します。
