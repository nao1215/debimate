#!/usr/bin/env bash
# kind（v0.30.0）でローカルの Kubernetes を 1 台作り、4 つのマニフェストを順に流して、最後にクラスタを消す。
#   ./run.sh > output.txt
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
KIND=${KIND:-kind}
name=note-sidecar
"$KIND" create cluster --name "$name" --wait 120s >/dev/null 2>&1
trap '"$KIND" delete cluster --name "$name" >/dev/null 2>&1 || true' EXIT
k() { docker exec -i "$name-control-plane" kubectl "$@"; }
k version 2>/dev/null | grep -i server
k run pull --image=busybox:1.37 --restart=Never -- true >/dev/null; k wait --for=jsonpath='{.status.phase}'=Succeeded pod/pull --timeout=180s >/dev/null; k delete pod pull >/dev/null

echo "== 1. Job: sidecar を普通のコンテナとして同居"
k apply -f - < "$here/job-plain.yaml" >/dev/null
sleep 30
k get job job-plain -o jsonpath='{"succeeded: "}{.status.succeeded}{"  active: "}{.status.active}{"  start: "}{.status.startTime}{"\n"}'
k get pods -l job-name=job-plain -o jsonpath='{range .items[*].status.containerStatuses[*]}{.name}{": "}{.state}{"\n"}{end}'

for j in job-native job-native-term; do
  echo "== 2. Job: sidecar を Sidecar Containers として同居（$j）"
  k apply -f - < "$here/$j.yaml" >/dev/null
  k wait --for=condition=complete job/$j --timeout=180s >/dev/null
  k get job $j -o jsonpath='{"succeeded: "}{.status.succeeded}{"  start: "}{.status.startTime}{"  completion: "}{.status.completionTime}{"\n"}'
  k get pods -l job-name=$j -o jsonpath='{range .items[*].status.containerStatuses[*]}{.name}{": finished "}{.state.terminated.finishedAt}{" exit "}{.state.terminated.exitCode}{"\n"}{end}{range .items[*].status.initContainerStatuses[*]}{.name}{": finished "}{.state.terminated.finishedAt}{" exit "}{.state.terminated.exitCode}{"\n"}{end}'
  echo "-- $j の log-shipper のログ"
  k logs -l job-name=$j -c log-shipper 2>&1 | tail -2
done

echo "== 3. 起動順: プロキシを普通のコンテナとして同居"
k apply -f - < "$here/proxy-plain.yaml" >/dev/null
sleep 40
k get pod proxy-plain -o jsonpath='{range .status.containerStatuses[*]}{.name}{": restarts="}{.restartCount}{" ready="}{.ready}{"\n"}{end}'
echo "-- 時刻（pod の作成、各コンテナの直前の終了と今の開始）"
k get pod proxy-plain -o jsonpath='{"pod created "}{.metadata.creationTimestamp}{"\n"}{range .status.containerStatuses[*]}{.name}{" last started "}{.lastState.terminated.startedAt}{" last finished "}{.lastState.terminated.finishedAt}{" now started "}{.state.running.startedAt}{"\n"}{end}'
k get events --field-selector involvedObject.name=proxy-plain --sort-by=.firstTimestamp -o jsonpath='{range .items[*]}{.firstTimestamp}{" "}{.lastTimestamp}{" "}{.reason}{" "}{.count}{" "}{.message}{"\n"}{end}' | grep -E "Started|BackOff" || true
echo "-- main の直前（2 回目）の失敗のログ（--previous）"
k logs proxy-plain -c main --previous 2>&1 | tail -3 || true
echo "-- main の今のログ"
k logs proxy-plain -c main 2>&1 | tail -3

echo "== 4. 起動順: プロキシを Sidecar Containers として同居（startupProbe）"
k apply -f - < "$here/proxy-native.yaml" >/dev/null
sleep 40
k get pod proxy-native -o jsonpath='{range .status.initContainerStatuses[*]}{.name}{": restarts="}{.restartCount}{" ready="}{.ready}{"\n"}{end}{range .status.containerStatuses[*]}{.name}{": restarts="}{.restartCount}{" ready="}{.ready}{"\n"}{end}'
echo "-- main のログ"
k logs proxy-native -c main 2>&1 | tail -3
echo "-- コンテナの開始時刻"
k get pod proxy-native -o jsonpath='{"pod created "}{.metadata.creationTimestamp}{"\n"}{range .status.initContainerStatuses[*]}{.name}{" started "}{.state.running.startedAt}{"\n"}{end}{range .status.containerStatuses[*]}{.name}{" started "}{.state.running.startedAt}{"\n"}{end}'
