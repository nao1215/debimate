#!/bin/sh
# Cassandra 5.0.6 の 3 台（q1・q2・q3）を Docker のネットワーク q-net に作る・消す。
#   ./cluster.sh up    3 台を順に起動し、全台が UN（Up/Normal）になるまで待つ
#   ./cluster.sh down  3 台とネットワークを消す
set -eu
IMAGE=cassandra:5.0.6
case "${1:-}" in
up)
  docker network create q-net >/dev/null 2>&1 || true
  for n in q1 q2 q3; do
    # 各台を調整役にした ONE の読み取りが自分の複製を読むように、
    # 台の近さで並べる snitch にし、応答の速さで並べ替える dynamic snitch を切る
    docker run -d --name "$n" --hostname "$n" --network q-net \
      -e CASSANDRA_SEEDS=q1 -e CASSANDRA_CLUSTER_NAME=quorum-lab \
      -e CASSANDRA_ENDPOINT_SNITCH=GossipingPropertyFileSnitch -e CASSANDRA_DC=dc1 \
      -e MAX_HEAP_SIZE=768M -e HEAP_NEWSIZE=128M "$IMAGE" \
      sh -c 'echo "dynamic_snitch: false" >> /etc/cassandra/cassandra.yaml && exec docker-entrypoint.sh cassandra -f' >/dev/null
    # 1 台ずつ参加させる（同時に参加させると起動に失敗することがある）
    until docker exec "$n" nodetool status 2>/dev/null | grep -q "^UN.*$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$n")"; do sleep 3; done
    echo "$n is up"
  done
  until [ "$(docker exec q1 nodetool status 2>/dev/null | grep -c '^UN')" = 3 ]; do sleep 3; done
  until docker exec q1 cqlsh -e "describe keyspaces" >/dev/null 2>&1; do sleep 3; done
  docker exec q1 cqlsh -e "CREATE KEYSPACE IF NOT EXISTS lab WITH replication = {'class': 'NetworkTopologyStrategy', 'dc1': 3};
    CREATE TABLE IF NOT EXISTS lab.kv (k text PRIMARY KEY, v text);"
  docker exec q1 nodetool status
  ;;
down)
  docker rm -f q1 q2 q3 >/dev/null 2>&1 || true
  docker network rm q-net >/dev/null 2>&1 || true
  ;;
*) echo "usage: $0 up|down" >&2; exit 2 ;;
esac
