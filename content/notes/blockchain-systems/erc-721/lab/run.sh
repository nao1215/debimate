#!/usr/bin/env bash
set -euo pipefail
python3 "$(dirname "$0")/run.py"
bash "$(dirname "$0")/eip7702.sh"
