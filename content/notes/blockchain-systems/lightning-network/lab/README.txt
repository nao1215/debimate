Lightning Network のノートの実験

regtest の Bitcoin Core と LND 3 台（alice・bob・carol）を docker compose で動かし、
次を測る。実資産・公開ネットワークは使わない。

1. alice が bob へ 1,000,000 sat のチャネルを開いた直後に、受け取れる額と送れる額
2. alice から 10,000 sat を受け取った bob が送れる額
3. bob と carol の 500,000 sat のチャネルを経由して、alice が carol へ 150,000 sat ずつ払う
4. bob が古い channel.db に戻して強制クローズし、alice が 9 ブロック遅れて戻る
5. bob の強制クローズと carol の協調クローズで、資金を使えるまでのブロック数

環境（2026-11-17 に実行）
- docker compose v2、Python 3（標準ライブラリだけ）
- polarlightning/bitcoind:27.0（Bitcoin Core 27.0）
- lightninglabs/lnd:v0.18.4-beta
- 手数料率は regtest の既定値（fee_per_kw 2500）。本番の手数料とは違う

実行
    cd lab
    python3 run.py          # 10 分ほど。終わるとコンテナを消す（--keep で残す）
    cd .. && python3 figures.py

出力
- result.json: 全ての測定値（図はここから描く）
- output.txt: 実行中に表示した行

送れる額は、払えない支払い（でたらめな payment_hash）を送って
受取人まで届くかどうかで二分探索している（probe）。残高は動かない。
