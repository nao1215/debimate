# Proof of Authority の実験

Docker の internal ネットワーク（外部への経路なし、ホストのポート公開なし）に
4 台のノードを立て、署名者を止めた時と通信を分断した時の振る舞いを記録します。
公開のネットワーク（メインネット・テストネット）には接続しません。

| ディレクトリ | 方式 | イメージ |
|---|---|---|
| `qbft/` | QBFT | `hyperledger/besu:26.11.0`（digest `sha256:3d6ac0368d449c13c4ba075acac90d6b96afa5b3113295385d88c4d5122c8808`） |
| `clique/` | Clique | `nethermind/nethermind:2.2.2`（digest `sha256:57df9bfaaf4d577919b35a2c7b1582ee5bd1812b36a812bdf8ac88ff7dba524d`） |

秘密鍵は、`net.sh` が文字列 `debimate-poa-test-node-<N>` の SHA-256 から実行時に作る実験専用の鍵です。
`keys/` には、その鍵に対応するアドレスと公開鍵だけを置いています。
作り方が公開されているので、実際のネットワークでは使わないでください。

## 必要なもの

- Linux の Docker（ホストからブリッジネットワーク上のコンテナの IP に届くこと）
- Python 3（標準ライブラリだけを使います）
- サブネット `10.231.12.0/24`〜`10.231.15.0/24` が空いていること

## 実行

```bash
# QBFT: 4 台で 30 秒 → node4 停止 → node3 停止 → 再起動。--vote で node5 を投票で追加
cd qbft && ./net.sh up && sleep 15 && python3 scenario.py --vote; ./net.sh down

# Clique: 上記と同じ停止に加え、node1+node2 と node3+node4 に分断して戻す
# --hold を付けると、通信を戻した後さらに 5 分待って各ノードの先頭を表示する
cd clique && ./net.sh up && sleep 20 && python3 scenario.py --hold; ./net.sh down

# 規則だけのシミュレーション（Docker 不要）
python3 limits.py   # 出力は limits_output.txt と同じ
```

`net.sh down` はコンテナ・ネットワーク・`data/` を削除します。
`qbft/genesis.json` の `extraData` は、`qbft/validators.json` から
`besu rlp encode --from=validators.json --type=QBFT_EXTRA_DATA` で作りました。
`clique/chainspec.json` は Nethermind の chainspec 形式で、`extraData` に署名者 4 人のアドレスを昇順で並べています。
記事に載せた実行結果は `output/` にあります（2026-11-10 計測）。
`qbft_trial1.txt` は `--vote` 付きです。`clique_trial1〜3.txt` は、各ノードの先頭を表示する行と `--hold` を足す前の
`scenario.py` の出力で、`clique_trial4.txt` が現在の版（`--hold` 付き）の出力です。
`after heal ... dropped` は node1 から見た値で、チェーンが止まった試行では node3 と node4 は自分のブロックを保持したままです。

## 注意

- 時間の値（最初のブロックまでの秒数）はホストの負荷で変わります。記事の値は負荷平均 20〜35 のホストでの計測です。
- Nethermind 2.2.2 は、分断した後にネットワークを戻しても、切れた相手に 3 分以上つなぎ直しませんでした。
  そのため `clique/net.sh heal` は、ネットワークを戻した後に node3 と node4 のコンテナを再起動します（データは残ります）。
