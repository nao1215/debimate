#!/usr/bin/env python3
"""Check RSS coverage, section boundaries, and publication order after a build."""

from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


def read_feed(path: Path) -> set[str]:
    items = ET.parse(path).findall("channel/item")
    dates = [parsedate_to_datetime(item.findtext("pubDate")) for item in items]
    assert dates == sorted(dates, reverse=True), f"Not newest first: {path}"
    links = [item.findtext("link") for item in items]
    assert len(links) == len(set(links)), f"Duplicate entries: {path}"
    for item in items:
        assert item.findtext("guid") == item.findtext("link"), path
    return set(links)


def check(root: Path) -> None:
    home = read_feed(root / "index.xml")
    for section in ("post", "notes", "weeknotes", "ml"):
        links = read_feed(root / section / "index.xml")
        assert links, f"Empty section feed: {section}"
        assert links <= home, f"Home feed missing {section} entries"
        assert all(urlparse(link).path.startswith(f"/{section}/") for link in links)
        descendants = set()
        for path in (root / section).rglob("index.xml"):
            if path != root / section / "index.xml":
                descendants.update(read_feed(path))
        assert descendants <= links, f"Missing nested entries: {section}"
    print(f"RSS checks passed: {len(home)} home entries")


if __name__ == "__main__":
    check(Path("public"))
