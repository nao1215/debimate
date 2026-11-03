#!/usr/bin/env bash
set -euo pipefail
LAB_MODE=token python3 "$(dirname "$0")/../../smart-contract/lab/run.py"
