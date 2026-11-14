#!/usr/bin/env python3
"""Gleam 向けの小さな mutation testing。

確かめた時点（2026-11-14）で Gleam 専用の mutation testing ツールが見つからなかったので、
演算子と分岐の結果を 1 か所ずつ書き換え、そのたびに `gleam test` を回す。

使い方:
  python3 gleam_mutate.py <コピーした Gleam プロジェクト> <対象ファイル（プロジェクトからの相対）> <結果の JSON>

元のプロジェクトは書き換えない。必ずコピーを渡す。
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# (名前, 正規表現, 置き換え)。Gleam は整数と浮動小数で演算子が分かれる（+ と +.）。
MUTATORS = [
    ("== → !=", r"(?<![=!<>])==(?!=)", "!="),
    ("!= → ==", r"!=", "=="),
    ("<. → <=.", r"<\.", "<=."),
    ("<=. → <.", r"<=\.", "<."),
    (">=. → >.", r">=\.", ">."),
    ("-. → +.", r"-\.", "+."),
    ("&& → ||", r"&&", "||"),
    ("|| → &&", r"\|\|", "&&"),
    ("! を外す", r"!(?=[a-z])", ""),
    ("-> True → -> False", r"-> True\b", "-> False"),
    ("-> False → -> True", r"-> False\b", "-> True"),
    ("== [] → == [Nil]", r"== \[\]", "== [Nil]"),
]

# 文字列と行コメントの中は書き換えない。
SKIP = re.compile(r'"(?:[^"\\]|\\.)*"|//[^\n]*')


def spans_to_skip(src):
    return [(m.start(), m.end()) for m in SKIP.finditer(src)]


def enclosing_fn(src, line):
    """その行を含む関数の名前（行より前で最後に出た fn）。"""
    name = ""
    for l in src.split("\n")[:line]:
        m = re.match(r"\s*(?:pub )?fn (\w+)", l)
        if m:
            name = m.group(1)
    return name


def mutants(src):
    skip = spans_to_skip(src)
    for name, pat, rep in MUTATORS:
        for m in re.finditer(pat, src):
            if any(a <= m.start() < b for a, b in skip):
                continue
            line = src.count("\n", 0, m.start()) + 1
            yield name, line, src[: m.start()] + rep + src[m.end():]


def failed_tests(out):
    # gleeunit は失敗したテストを「 test: <モジュール>.<関数>」の形で出す。
    names = set(re.findall(r"^\s*test: ([a-z_0-9/]+\.[a-z_0-9]+)$", out, re.M))
    return sorted(names)


def run(proj):
    t = time.time()
    p = subprocess.run(["gleam", "test"], cwd=proj, capture_output=True, text=True, timeout=120)
    out = re.sub(r"\x1b\[[0-9;]*m", "", p.stdout + p.stderr)
    return p.returncode, out, time.time() - t


def main():
    proj, target, dest = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    path = proj / target
    original = path.read_text()
    code, out, _ = run(proj)
    assert code == 0, "元のテストが通らない"
    results = []
    try:
        for i, (name, line, src) in enumerate(mutants(original)):
            path.write_text(src)
            code, out, sec = run(proj)
            if "error:" in out and "Compiling" in out and code != 0 and "passed" not in out:
                status = "COMPILE_ERROR"
            elif code == 0:
                status = "LIVED"
            else:
                status = "KILLED"
            row = {"id": i, "mutator": name, "line": line, "function": enclosing_fn(original, line),
                   "status": status,
                   "killed_by": failed_tests(out) if status == "KILLED" else [],
                   "seconds": round(sec, 2)}
            summary = re.search(r"(\d+) passed(?:, (\d+) failures?)?", out)
            if summary:
                row["passed"] = int(summary.group(1))
                row["failures"] = int(summary.group(2) or 0)
            results.append(row)
            print(f"{status:14} L{line:<4} {name}", flush=True)
    finally:
        path.write_text(original)
    dest.write_text(json.dumps(results, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
