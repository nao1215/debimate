#!/usr/bin/env bash
# ローカルの Anvil を 127.0.0.1:18745 で起動し、experiment.py を走らせて止める。
# 公開のネットワークには繋がない。署名は Anvil の開発用アカウントが eth_sendTransaction で行う。
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
anvil --port 18745 --silent --accounts 10 --balance 10000 &
pid=$!
trap 'kill $pid 2>/dev/null || true' EXIT
for _ in $(seq 50); do cast chain-id --rpc-url http://127.0.0.1:18745 >/dev/null 2>&1 && break; sleep 0.1; done
python3 "$here/experiment.py" | tee "$here/output/summary.txt"
