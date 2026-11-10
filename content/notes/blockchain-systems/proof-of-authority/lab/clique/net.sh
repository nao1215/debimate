#!/usr/bin/env bash
# Clique network of four Nethermind signers on an internal Docker network.
# No host port is published and the network has no route to the outside.
# Every node sits on the shared network A. node1/node2 also share network L and
# node3/node4 share network R, so `cut` (detach node3/node4 from A) splits the
# signers 2 | 2 while each pair stays connected. `heal` attaches them again.
#   ./net.sh up | down | stop N | start N | cut | heal
set -euo pipefail
cd "$(dirname "$0")"

IMAGE=nethermind/nethermind:2.2.2
NET=note-proof-of-authority-clique
SUBNET=10.231.13.0/24
ip() { echo "10.231.13.1$1"; }   # node1 -> 10.231.13.11 on network A
side() { if [ "$1" -le 2 ]; then echo L; else echo R; fi; }
sideip() { if [ "$1" -le 2 ]; then echo "10.231.14.1$1"; else echo "10.231.15.1$1"; fi; }
name() { echo "note-proof-of-authority-clique$1"; }
# Test-only private key, derived from a public string (see ../README.md).
key() { printf "debimate-poa-test-node-%s" "$1" | sha256sum | cut -c1-64; }

run_node() {
  local i=$1
  mkdir -p "data/node$i"
  docker create --name "$(name "$i")" --network "$NET" --ip "$(ip "$i")" \
    --user "$(id -u):$(id -g)" \
    -v "$PWD/chainspec.json:/chainspec.json:ro" -v "$PWD/data/node$i:/data" \
    "$IMAGE" --config none --datadir /data \
    --Init.ChainSpecPath=/chainspec.json --Init.DiscoveryEnabled=false \
    --Merge.Enabled=false --Mining.Enabled=true \
    --KeyStore.TestNodeKey="$(key "$i")" \
    --Network.ExternalIp="$(ip "$i")" \
    --Network.EnableExternalIpResolution=false \
    --JsonRpc.Enabled=true --JsonRpc.Host=0.0.0.0 \
    --JsonRpc.EnabledModules=eth,net,clique,admin \
    --Metrics.Enabled=false --log INFO >/dev/null
  docker network connect --ip "$(sideip "$i")" "$NET-$(side "$i")" "$(name "$i")"
  docker start "$(name "$i")" >/dev/null
}

case "${1:-}" in
  up)
    docker network create --internal --subnet "$SUBNET" "$NET" >/dev/null
    docker network create --internal --subnet 10.231.14.0/24 "$NET-L" >/dev/null
    docker network create --internal --subnet 10.231.15.0/24 "$NET-R" >/dev/null
    for i in 1 2 3 4; do run_node "$i"; done ;;
  down)
    for i in 1 2 3 4; do docker rm -f "$(name "$i")" >/dev/null 2>&1 || true; done
    for n in "$NET" "$NET-L" "$NET-R"; do docker network rm "$n" >/dev/null 2>&1 || true; done
    rm -rf data ;;
  stop) docker stop -t 1 "$(name "$2")" >/dev/null ;;
  start) docker start "$(name "$2")" >/dev/null ;;
  cut) for i in 3 4; do docker network disconnect "$NET" "$(name "$i")"; done ;;
  heal)  # Nethermind 2.2.2 did not redial the lost peers here, so restart them
    for i in 3 4; do docker network connect --ip "$(ip "$i")" "$NET" "$(name "$i")"; done
    docker restart -t 1 "$(name 3)" "$(name 4)" >/dev/null ;;
  *) echo "usage: $0 up|down|stop N|start N|cut|heal" >&2; exit 2 ;;
esac
