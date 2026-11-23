#!/bin/bash
# Build OpenZeppelin Monitor v1.7.0 (4565bb1) and main (c51fccc) from source.
# SRC: a directory with the two checkouts (oz-v170, openzeppelin-monitor).
set -x
SRC=${SRC:?set SRC to the directory holding the checkouts}
OZ=$(cd "$(dirname "$0")" && pwd)
cd $SRC/oz-v170 && CARGO_TARGET_DIR=$OZ/build/target-v170 cargo build --release -j 8 --bin openzeppelin-monitor
cd $SRC/openzeppelin-monitor && CARGO_TARGET_DIR=$OZ/build/target-main cargo build --release -j 8 --bin openzeppelin-monitor
