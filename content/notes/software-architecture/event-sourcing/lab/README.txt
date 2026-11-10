replay_time.py: イベントの再生で Order を復元する時間を、ストリームの長さと
スナップショットの間隔ごとに実測する

  python3 content/notes/software-architecture/event-sourcing/lab/replay_time.py \
      > content/notes/software-architecture/event-sourcing/lab/replay_time_output.txt
  uv run --with matplotlib python content/notes/software-architecture/event-sourcing/figures.py
      # images/event-sourcing_replay_time.svg を replay_time_output.txt から作る

  Python 3.10 以上、標準ライブラリだけ。45 秒ほどかかる。
  時間は実測なので実行ごとに変わる（混んだマシンで 1〜2 割）。
  再生した件数（replayed 列）と復元した状態は毎回同じになる。
