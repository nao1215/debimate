#!/bin/sh
# 実験の手順。Redis は 127.0.0.1 だけで待ち受けるコンテナで動かし、終わったら消す。
set -eu
cd "$(dirname "$0")"

python3 simulate.py | tee output_simulate.txt
python3 split.py | tee output_split.txt

docker run -d --rm --name ratelimit-lab-redis -p 127.0.0.1:16379:6379 redis:7.4.1-alpine >/dev/null
trap 'docker stop ratelimit-lab-redis >/dev/null' EXIT
sleep 1
python3 race.py | tee output_race.txt
