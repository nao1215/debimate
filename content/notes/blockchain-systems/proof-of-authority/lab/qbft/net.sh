#!/usr/bin/env bash
# QBFT network of four Besu validators on a local Docker network.
# No host port is published and the network has no route to the outside.
# The host reaches JSON-RPC through the container IP.
#   ./net.sh up | down | stop N | start N | ip N
set -euo pipefail
cd "$(dirname "$0")"

IMAGE=hyperledger/besu:26.11.0
NET=note-proof-of-authority-qbft
SUBNET=10.231.12.0/24
ip() { echo "10.231.12.1$1"; }   # node1 -> 10.231.12.11
name() { echo "note-proof-of-authority-qbft$1"; }
# Test-only private key, derived from a public string (see ../README.md).
key() { printf "0x%s" "$(printf "debimate-poa-test-node-%s" "$1" | sha256sum | cut -c1-64)"; }

run_node() {
  local i=$1 boot=""
  if [ "$i" != 1 ]; then
    boot="--bootnodes=enode://$(cut -c3- ../keys/node1/key.pub)@$(ip 1):30303"
  fi
  mkdir -p "data/node$i"
  key "$i" > "data/node$i/key"
  docker run -d --name "$(name "$i")" --network "$NET" --ip "$(ip "$i")" \
    --user "$(id -u):$(id -g)" -e JAVA_OPTS="-Xmx512m" \
    -v "$PWD/genesis.json:/genesis.json:ro" -v "$PWD/data/node$i:/data" \
    "$IMAGE" --data-path=/data --genesis-file=/genesis.json \
    --p2p-host="$(ip "$i")" --rpc-http-enabled --rpc-http-host=0.0.0.0 \
    --rpc-http-api=ETH,NET,QBFT,ADMIN --host-allowlist="*" \
    --profile=ENTERPRISE --logging=INFO $boot >/dev/null
}

case "${1:-}" in
  up)
    docker network create --internal --subnet "$SUBNET" "$NET" >/dev/null
    for i in 1 2 3 4; do run_node "$i"; done ;;
  down)
    for i in 1 2 3 4 5; do docker rm -f "$(name "$i")" >/dev/null 2>&1 || true; done
    docker network rm "$NET" >/dev/null 2>&1 || true
    rm -rf data ;;
  add5) run_node 5 ;;
  stop) docker stop -t 1 "$(name "$2")" >/dev/null ;;
  start) docker start "$(name "$2")" >/dev/null ;;
  ip) ip "$2" ;;
  *) echo "usage: $0 up|down|stop N|start N|add5|ip N" >&2; exit 2 ;;
esac
