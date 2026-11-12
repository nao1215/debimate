#!/usr/bin/env bash
# 手元の anvil を 3 台（127.0.0.1:18745〜18747）起動して実験し、終わったら止める。
# 起動と停止は experiment.py が行う。公開ネットワークには繋がない。
set -euo pipefail
cd "$(dirname "$0")"
python3 experiment.py | tee output/stdout.txt
