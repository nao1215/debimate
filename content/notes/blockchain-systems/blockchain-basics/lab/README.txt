Blockchain Basics のローカル実験（Python 3 の標準ライブラリだけで動く。ネットワークは使わない）

  python3 hash_link.py > hash_link_output.txt
  python3 fork_rules.py > output.txt      # 4 通り x 20 回。手元の PC で 40 秒ほど

hash_link.py
  前のブロックのハッシュ値を持たせた 3 個のブロックを作り、ブロック 1 の中身だけを書き換えて、
  次のブロックが持つ prev と合わなくなることを示す。

fork_rules.py
  古い規則のノードと新しい規則のノードの 2 組が、本物の SHA-256 で Proof of Work を解きながら
  ブロックを作る。規則はブロックの大きさの上限だけで、厳しくする（500 バイトまで）場合と
  緩める（2000 バイトまで）場合を、新しい規則のマイナーの計算量が 70% と 30% の組み合わせで試す。
  10 回の試行を計算量の割合で 2 組に分け、両方の組を合わせて 100 個のブロックが見つかるまで続ける。
  見つかったブロックはすぐ両方の組に届き、各組は自分の規則で有効な列のうち最も長い列を選ぶ。
  output.txt の common は 2 組が共有するブロックの数、old_only / new_only は分かれた後の数
  （20 回の中央値と最小・最大）、old_lost / new_lost は自分の組の列から外れたブロックの割合（中央値）。
  trace.json は seed 1 の記録で、../figures.py が動く図を作る時に読む。

output.txt と hash_link_output.txt は 2026-11-13 に実行した結果。
