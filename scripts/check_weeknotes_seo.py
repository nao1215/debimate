#!/usr/bin/env python3
"""Validate SEO metadata for generated Weeknotes pages without requiring aliases."""

import json
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


class Page(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.canonical = []
        self.structured = []
        self.body = []
        self.depth = 0
        self.script = None
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            self.meta[attrs.get("name", attrs.get("property"))] = attrs.get("content")
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical.append(attrs.get("href"))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.script = ""
        if tag == "div":
            if self.depth:
                self.depth += 1
            elif "post-content" in attrs.get("class", "").split():
                self.depth = 1

    def handle_data(self, data):
        if self.script is not None:
            self.script += data
        elif self.depth:
            self.body.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.script is not None:
            self.structured.append(json.loads(self.script))
            self.script = None
        if tag == "div" and self.depth:
            self.depth -= 1


def check(root: Path) -> None:
    entries = ET.parse(root / "sitemap.xml").findall("{*}url")
    urls = [entry.findtext("{*}loc") for entry in entries]
    modified = {entry.findtext("{*}loc"): entry.findtext("{*}lastmod") for entry in entries}
    topic_files = list((root / "weeknotes").glob("????-??-??/*/index.html"))
    for path in topic_files:
        page = Page(path)
        assert len(page.canonical) == 1, path
        url = page.canonical[0]
        assert urlparse(url).path == "/" + str(path.parent.relative_to(root)) + "/", path
        assert urls.count(url) == 1, f"Topic missing or duplicated in sitemap: {url}"
        assert page.meta.get("robots") == "index, follow", path
        assert page.meta.get("og:image"), path
        assert page.meta["og:image"] == page.meta.get("twitter:image"), path
        assert page.meta.get("description") == page.meta.get("og:description") == page.meta.get("twitter:description"), path
        articles = [item for item in page.structured if item.get("@type") == "BlogPosting"]
        assert len(articles) == 1, path
        article = articles[0]
        # Compare against visible text, including empty/image-only topics.
        normalize = lambda text: re.sub(r"\s+", "", text)
        assert normalize(article.get("articleBody", "")) == normalize("".join(page.body)), path
        assert article.get("dateModified") == modified[url], path
    years = {path.parent.name[:4] for path in (root / "weeknotes").glob("????-??-??/index.html")}
    for year in years:
        path = root / "weeknotes" / year / "index.html"
        page = Page(path)
        assert len(page.canonical) == 1, path
        assert urls.count(page.canonical[0]) == 1, f"Annual archive missing from sitemap: {path}"
        assert any(item.get("@type") == "CollectionPage" for item in page.structured), path
    print(f"Weeknotes SEO verified: {len(topic_files)} topics, sitemap, metadata, and structured data")


if __name__ == "__main__":
    check(Path("public"))
