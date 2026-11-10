callcost/main.go: in-process と out-of-process で Exporter.Export 1 回の所要時間を測る

  cd content/notes/software-architecture/plugin-architecture/lab/callcost
  go run . > ../callcost_output.txt          # Go 1.26、Linux。40 秒ほどかかる
  cd ../../../../../..
  python3 content/notes/software-architecture/plugin-architecture/figures.py
      # images/plugin-architecture_call_cost.svg を callcost_output.txt から作る

  実測なので、値は実行ごとに変わる（混んだマシンでは 2 倍程度）。
  in-process が ns、out-of-process が µs という桁の差は変わらない。
