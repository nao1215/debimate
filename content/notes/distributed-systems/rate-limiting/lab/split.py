"""上限を 2 台のサーバーで半分ずつ分け合う時と、中央で数える時の比較。

利用者 1 人が 60 秒の間に 60 件を均等な間隔で送る。上限は 60 秒あたり 60 件なので、本来はすべて通る。
ロードバランサーが、そのうち割合 p をサーバー 1 に、残りをサーバー 2 に送る。
  split   : 各サーバーが 30 件ずつの固定窓を自分のメモリで数える
  central : 1 か所（中央の数）で 60 件の固定窓を数える

  python3 split.py
"""
import json
import os

from limiters import FixedWindow

N, LIMIT, WINDOW = 60, 60, 60.0


def run(p):
    arrivals = [i * WINDOW / N for i in range(N)]
    # 割合 p に近くなるよう、到着ごとに振り分け先を決める（誤差拡散で偏りなく混ぜる）
    acc, route = 0.0, []
    for _ in arrivals:
        acc += p
        if acc >= 1.0 - 1e-9:
            acc -= 1.0
            route.append(1)
        else:
            route.append(2)
    local = {1: FixedWindow(LIMIT // 2, WINDOW), 2: FixedWindow(LIMIT // 2, WINDOW)}
    central = FixedWindow(LIMIT, WINDOW)
    split_ok = sum(local[s].allow(t) for t, s in zip(arrivals, route))
    central_ok = sum(central.allow(t) for t in arrivals)
    return {"p": p, "to_server1": route.count(1), "split": split_ok, "central": central_ok}


def main():
    rows = [run(p / 100) for p in range(50, 101, 5)]
    print(f"{'p':>5} {'server1':>7} {'split':>5} {'central':>7}")
    for r in rows:
        print(f"{r['p']:5.2f} {r['to_server1']:7} {r['split']:5} {r['central']:7}")
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "split_results.json"), "w") as f:
        json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
