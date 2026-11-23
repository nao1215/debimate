#!/bin/bash
# 使い方: ./run_all.sh <ver> <base> [scen...]   例: ./run_all.sh v170 18720
cd "$(dirname "$0")"
ver=$1; base=$2; shift 2
scens=${@:-S0 S1a_full S1b_full S1a_logs S1b_logs S1a_logs_rec S1b_logs_rec S2_term_default S2_kill_default S2_term_unlimited S2_kill_unlimited S2_term_default_rec S3_c1 S3_c5 S4 S5 S5_unlimited}
for s in $scens; do
  echo "=== $ver $s $(date +%T)"
  timeout 900 python3 drive.py --ver $ver --scen $s --base $base || echo "FAILED $ver $s"
done
python3 analyze.py $ver > /dev/null
echo "ALL_DONE $ver $(date +%T)"
