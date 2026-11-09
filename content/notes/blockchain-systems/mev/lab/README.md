# ローカル実験

Python 3.8 以降の標準ライブラリだけで実行できます。

```sh
python3 sandwich.py
```

`output.txt` は Python 3.14 で実行した結果です。

ネットワークには接続せず、Uniswap v2 の `getAmountOut` と同じ式（手数料 0.3%）を整数で計算するだけです。プールの残高（3,000,000 USDC / 1,000 ETH）と取引の額は説明用の値で、gas 代は含めていません。

本文の図（`../images/mev_slippage.svg`）は、同じ関数を使う `../figures.py` で生成します。
