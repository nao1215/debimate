# Metamorphic Testing ノートの実験

著者の環境: Ubuntu 26.04、jz v0.9.1、wc (uutils coreutils) 0.8.0、GNU wc 9.7（`gnuwc`）、Go 1.26.4、Python 3.14.4。

| ファイル | 内容 | 出力 |
|---|---|---|
| `exp1_wc_concat.sh` | 関係「jz run wc A B = jz run wc A ++ jz run wc B」 | `output/exp1_wc_concat.txt` |
| `exp2_token_sweep.py` | トークン感度（1 文字変えて出力が変わるか） | `output/exp2_token_sweep.txt`、`.json` |
| `exp3_quick/main.go` | testing/quick で語数の連結の関係を当てる | `output/exp3_quick.txt` |

```sh
./exp1_wc_concat.sh                 # jz と jq が要る
python3 exp2_token_sweep.py output/exp2_token_sweep.json
(cd exp3_quick && go run .)
```

図は 1 つ上の `figures.py` が `output/` を読んで描きます（`python3 figures.py`）。
