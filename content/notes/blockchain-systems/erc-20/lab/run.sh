#!/usr/bin/env bash
# ローカルの Anvil を 127.0.0.1:18645 で起動し、experiment.py を走らせて止める。
# 公開のネットワーク・実資産・秘密鍵は使わない（Anvil の開発用アカウントに署名させる）。
set -euo pipefail
cd "$(dirname "$0")"
command -v anvil >/dev/null && command -v cast >/dev/null && command -v solc >/dev/null || {
  echo "anvil・cast（Foundry）と solc 0.8.28 を PATH に入れてください" >&2; exit 1; }
if (exec 3<>/dev/tcp/127.0.0.1/18645) 2>/dev/null; then
  echo "127.0.0.1:18645 は使用中です" >&2; exit 1
fi
anvil --host 127.0.0.1 --port 18645 --silent --order fees &
pid=$!
trap 'kill "$pid" 2>/dev/null || true' EXIT
for _ in $(seq 50); do
  cast chain-id --rpc-url http://127.0.0.1:18645 >/dev/null 2>&1 && break
  sleep 0.1
done
python3 experiment.py
