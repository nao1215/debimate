#!/usr/bin/env python3
"""Verify the built topic index, annual archives, and adjacent-topic navigation."""

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


class Page(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.headings = 0
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.links.append(attrs)
        if tag == "h4":
            self.headings += 1


def check(root: Path) -> None:
    index = Page(root / "weeknotes/index.html")
    topics = [
        link["href"] for link in index.links
        if re.fullmatch(r"/weeknotes/\d{4}-\d{2}-\d{2}/[a-f0-9]{12}/", link.get("href", ""))
    ]
    assert topics, "Weeknotes index must link to individual topics"
    assert len(topics) == len(set(topics)), "Duplicate topics in index"
    assert index.headings == 0, "Index must not contain the weekly full text"
    counts = {}
    for i, url in enumerate(topics):
        page = Page(root / url.strip("/") / "index.html")
        year = url.split("/")[2][:4]
        counts[year] = counts.get(year, 0) + 1
        nav = {
            link.get("class"): urlparse(link["href"]).path
            for link in page.links
            if link.get("class") in {"prev", "index", "next"}
        }
        expected = {"index": f"/weeknotes/{year}/"}
        if i:
            expected["prev"] = topics[i - 1]
        if i + 1 < len(topics):
            expected["next"] = topics[i + 1]
        assert nav == expected, f"Incorrect navigation on {url}: {nav}"
        assert page.headings == 0, f"Other topic headings leaked into {url}"
    for year, count in counts.items():
        annual = Page(root / f"weeknotes/{year}/index.html")
        assert annual.headings == count, f"Missing full-text topics in {year} archive"
        assert any(link.get("href") == f"/weeknotes/{year}/" for link in index.links)
    print(f"Weeknotes navigation verified: {len(topics)} topics, {len(counts)} annual archives")


if __name__ == "__main__":
    check(Path("public"))
