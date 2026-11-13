#!/bin/sh
# 使い方: ./run.sh <stop|failover>[-minrep][-kill]
#   stop     … master のコンテナを止め、20 秒後に戻す
#   failover … SENTINEL FAILOVER で master を手動で切り替える（止めない）
#   -minrep  … Redis に --min-replicas-to-write 1 を付ける
#   -kill    … HAProxy に on-marked-down shutdown-sessions を付ける（haproxy-kill.cfg）
set -eu
cd "$(dirname "$0")"
scenario=$1
export OUT=./output/$scenario
case $scenario in *-minrep*) export REDIS_ARGS="--min-replicas-to-write 1 --min-replicas-max-lag 10";; esac
case $scenario in *-kill*) export HAPROXY_CFG=haproxy-kill.cfg;; esac
rm -rf "$OUT"; mkdir -p "$OUT"
docker compose up -d --build >/dev/null 2>&1
sleep 15                                   # replica の同期と Sentinel の検出を待つ
ev() { python3 -c "import json,time;print(json.dumps({'t':time.time(),'event':'$1'}))" >>"$OUT/events.jsonl"; }
case $scenario in
stop*)
  ev stop-a; docker compose stop -t 0 redis-a >/dev/null 2>&1
  sleep 20
  ev start-a; docker compose start redis-a >/dev/null 2>&1
  sleep 15 ;;
failover*)
  ev failover; docker compose exec -T sentinel-1 redis-cli -p 26379 sentinel failover mymaster
  sleep 20 ;;
esac
ev end
# 最後に Sentinel が master と言うインスタンスに、どの通し番号が残ったかを書き出す
master=$(docker compose exec -T sentinel-1 redis-cli -p 26379 sentinel get-master-addr-by-name mymaster | head -1)
svc=redis-$(echo "$master" | sed 's/172.28.0.11/a/;s/172.28.0.12/b/;s/172.28.0.13/c/')
echo "$master" >"$OUT/final_master.txt"
for m in static sentinel ambassador ambassador_new; do
  docker compose exec -T "$svc" redis-cli lrange "log:$m" 0 -1 >"$OUT/kept_$m.txt"
done
docker compose logs -t --no-color sentinel-1 >"$OUT/sentinel-1.log" 2>&1
docker compose logs -t --no-color ambassador >"$OUT/ambassador.log" 2>&1
docker compose down -t 0 >/dev/null 2>&1
