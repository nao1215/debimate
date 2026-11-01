#!/usr/bin/env python3
"""Bound initial documents and home batches, not the growing content archive."""
import argparse
import gzip
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


class Preloads(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.urls = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and {"preload", "prefetch"} & set(attrs.get("rel", "").split()):
            self.urls.append(attrs.get("href", ""))


def check(root, limits):
    failures = []
    checked = 0
    largest = {}

    def measure(path, budget, group):
        nonlocal checked
        if not path.is_file():
            failures.append(f"Missing required artifact: {path}")
            return
        raw = path.read_bytes()
        sizes = {"bytes": len(raw), "gzip_bytes": len(gzip.compress(raw, mtime=0))}
        checked += 1
        if sizes["bytes"] > largest.get(group, {}).get("bytes", -1):
            largest[group] = {"path": str(path.relative_to(root)), **sizes}
        for metric, limit in budget.items():
            if sizes[metric] > limit:
                failures.append(f"{path}: {metric}={sizes[metric]} exceeds {limit}")

    for relative, budget in limits["pages"].items():
        measure(root / relative, budget, relative)
    for path in (root / "weeknotes").glob("[0-9][0-9][0-9][0-9]/**/index.html"):
        measure(path, limits["annual"], "annual")
    for path in (root / "assets/home").glob("*.json"):
        measure(path, limits["home_batch"], "home_batch")
    search = root / "search/index.html"
    if search.is_file():
        for url in Preloads(search.read_text()).urls:
            if urlparse(url).path.endswith("index.json"):
                failures.append("Search must not preload its index before a query")

    # Informational only: growth of the content corpus is expected, not a release error.
    index = root / "index.json"
    report = {"checked": checked, "largest": largest}
    if index.is_file():
        raw = index.read_bytes()
        report["search_index_informational"] = {
            "records": len(json.loads(raw)), "bytes": len(raw),
            "gzip_bytes": len(gzip.compress(raw, mtime=0)),
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit("Performance budget failed:\n" + "\n".join(failures))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-dir", type=Path, default=Path("public"))
    parser.add_argument("--limits", type=Path, default=Path("config/performance-budgets.json"))
    args = parser.parse_args()
    check(args.public_dir, json.loads(args.limits.read_text()))
