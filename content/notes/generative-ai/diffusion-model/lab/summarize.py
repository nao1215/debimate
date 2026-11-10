"""*_log.json から、本文に載せる実行時間の表を作る（Python 標準ライブラリだけ）。

使い方: python3 summarize.py > output_runs.txt
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def rows(name):
    return json.load(open(os.path.join(HERE, f"{name}_log.json")))


print("experiment  condition                        seconds  load_before(gpu%, load1m)")
for r in rows("trajectory"):
    print(f"trajectory  k={r['k']:2d} sigma={r['sigma']:7.4f}             {r['seconds']:6.2f}  "
          f"{r['load_before'].get('gpu_busy_percent')}, {r['load_before'].get('loadavg_1m')}")
for name in ("steps", "samplers", "cfg", "rerun"):
    for r in rows(name):
        cond = f"{r['tag']}"
        extra = ""
        if name == "rerun":
            extra = (f"  identical_to_steps_28={r['identical_to_steps_28']}"
                     f" identical_to_trajectory_x_28={r['identical_to_trajectory_x_28']}")
        print(f"{name:10s}  {cond:32s} {r['seconds']:6.2f}  "
              f"{r['load_before'].get('gpu_busy_percent')}, {r['load_before'].get('loadavg_1m')}{extra}")
