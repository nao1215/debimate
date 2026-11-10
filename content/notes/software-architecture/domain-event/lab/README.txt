redelivery.py: コミットと ack の間で落ちる at-least-once 配送を再現し、
処理済みの記録が無い時と有る時で、余分に引き当てた在庫の個数を数える

  python3 content/notes/software-architecture/domain-event/lab/redelivery.py \
      > content/notes/software-architecture/domain-event/lab/redelivery_output.txt
  python3 content/notes/software-architecture/domain-event/figures.py
      # images/domain-event_redelivery.svg を redelivery_output.txt から作る

  Python 3.10 以上、標準ライブラリだけ。障害は seed 固定の乱数で起こすので、
  再実行しても出力は同じになる（SQLite のバージョン表示を除く）。
