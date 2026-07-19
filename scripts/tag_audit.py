#!/usr/bin/env python3

from __future__ import annotations

import collections
import os
from pathlib import Path

import yaml


ROOTS = [Path("content/post"), Path("projects/ml/notes")]


def iter_front_matter():
    for root in ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("index.md"):
            text = path.read_text(encoding="utf-8")
            if not text.startswith("---\n"):
                continue
            try:
                front = text.split("\n---\n", 1)[0][4:]
                data = yaml.safe_load(front) or {}
            except Exception as exc:  # pragma: no cover - operational output only
                print(f"WARN\t{path}\t{exc}")
                continue
            yield path, data


def main() -> None:
    tag_counts: collections.Counter[str] = collections.Counter()
    category_counts: collections.Counter[str] = collections.Counter()
    series_counts: collections.Counter[str] = collections.Counter()

    for _, data in iter_front_matter():
        for tag in data.get("tags") or []:
            tag_counts[str(tag)] += 1
        for category in data.get("categories") or []:
            category_counts[str(category)] += 1
        for series in data.get("series") or []:
            series_counts[str(series)] += 1

    print("== Tags ==")
    for name, count in tag_counts.most_common():
        print(f"{count:>3}\t{name}")
    print(f"TOTAL\t{len(tag_counts)}")

    print("\n== Categories ==")
    for name, count in category_counts.most_common():
        print(f"{count:>3}\t{name}")
    print(f"TOTAL\t{len(category_counts)}")

    print("\n== Series ==")
    for name, count in series_counts.most_common():
        print(f"{count:>3}\t{name}")
    print(f"TOTAL\t{len(series_counts)}")


if __name__ == "__main__":
    main()
