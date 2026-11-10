lost_update.py: 同じ注文を K 個の処理が読んで明細を 1 件ずつ足す時、
バージョンの検査が無いと消える明細の件数と、検査がある時の読み直しの回数を数える

  python3 content/notes/software-architecture/repository/lab/lost_update.py \
      > content/notes/software-architecture/repository/lab/lost_update_output.txt
  python3 content/notes/software-architecture/repository/figures.py
      # images/repository_lost_update.svg を lost_update_output.txt から作る

  Python 3.10 以上、標準ライブラリだけ。読み込みと保存の順番は seed 固定の乱数で決めるので、
  再実行しても出力は同じになる（SQLite のバージョン表示を除く）。
