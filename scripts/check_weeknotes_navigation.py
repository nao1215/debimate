#!/usr/bin/env python3
"""Verify the built topic index, annual archives, and adjacent-topic navigation."""

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


class Page(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.headings = 0
        self.titles = {"h1": [], "h4": []}
        self.heading_tag = None
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.links.append(attrs)
        if tag in self.titles:
            self.heading_tag = tag
            self.titles[tag].append("")
        if tag == "h4":
            self.headings += 1

    def handle_data(self, data):
        if self.heading_tag:
            self.titles[self.heading_tag][-1] += data

    def handle_endtag(self, tag):
        if tag == self.heading_tag:
            self.heading_tag = None



def check(root: Path) -> None:
    index = Page(root / "weeknotes/index.html")
    topics = [
        link["href"] for link in index.links
        if re.fullmatch(r"/weeknotes/\d{4}-\d{2}-\d{2}/[a-f0-9]{12}/", link.get("href", ""))
    ]
    assert topics, "Weeknotes index must link to individual topics"
    assert len(topics) == len(set(topics)), "Duplicate topics in index"
    assert index.headings == 0, "Index must not contain the weekly full text"
    # Source topics are appended chronologically; all reading surfaces reverse them.
    source_root = Path(__file__).resolve().parents[1] / "content/weeknotes"
    expected_topics = []
    for source in sorted(source_root.glob("[0-9]*/[0-9]*/index.md"), reverse=True):
        date = f"{source.parent.parent.name}-{source.parent.name}"
        if not (root / f"weeknotes/{date}/index.html").is_file():
            continue
        raw = re.sub(r"(?ms)^`{3,}[^\n]*\n.*?^`{3,}\s*$|^~{3,}[^\n]*\n.*?^~{3,}\s*$", "", source.read_text())
        headings = re.findall(r"(?m)^####[ \t]+[^\r\n]+", raw)
        expected_topics.extend(
            f"/weeknotes/{date}/{hashlib.sha256(h.encode()).hexdigest()[:12]}/"
            for h in reversed(headings)
        )
    assert topics == expected_topics, "Topic cards must run newest to oldest within each week"
    counts = {}
    week_titles = {}
    year_titles = {}
    for i, url in enumerate(topics):
        page = Page(root / url.strip("/") / "index.html")
        year = url.split("/")[2][:4]
        counts[year] = counts.get(year, 0) + 1
        title = page.titles["h1"][0].strip()
        week = url.split("/")[2]
        week_titles.setdefault(week, []).append(title)
        year_titles.setdefault(year, []).append(title)
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
    for week, titles in week_titles.items():
        weekly = Page(root / f"weeknotes/{week}/index.html")
        assert [t.strip() for t in weekly.titles["h4"]] == titles, f"Incorrect topic order in {week}"
    for year, count in counts.items():
        annual = Page(root / f"weeknotes/{year}/index.html")
        assert [t.strip() for t in annual.titles["h4"]] == year_titles[year], f"Incorrect topic order in {year} archive"
        assert annual.headings == count, f"Missing full-text topics in {year} archive"
        assert any(link.get("href") == f"/weeknotes/{year}/" for link in index.links)
    print(f"Weeknotes navigation verified: {len(topics)} topics, {len(counts)} annual archives")


if __name__ == "__main__":
    check(Path("public"))
