# Retry and Backoff の実験

2026 年 11 月に Python 3.14.4、AMD Ryzen AI Max+ 395（CPU だけを使用）で実行しました。Python 3.14 の標準ライブラリだけで動きます（図の生成には matplotlib と Pillow が要ります）。

```sh
python3 herd.py herd.json > herd_output.txt                       # 同時に失敗した 1,000 件（約 70 秒）
python3 herd.py /tmp/spread.json 0.9 > herd_spread_output.txt     # 最初の送信を 0〜0.9 s に散らす
python3 budget.py budget.json > budget_output.txt                 # 再試行の予算
python3 layers.py > layers_output.txt                             # 3 段 × 3 回の掛け算
cd .. && python3 figures.py                                       # images/ の WebP を作り直す
```
