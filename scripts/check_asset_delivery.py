#!/usr/bin/env python3
"""Validate page-specific CSS bundles and lightweight favicon declarations."""

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


class Assets(HTMLParser):
    def __init__(self, path: Path, *, html=None):
        super().__init__(convert_charrefs=True)
        self.classes = set()
        self.element_ids = set()
        self.icons = []
        self.stylesheets = []
        self.feed(path.read_text() if html is None else html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        assert tag != "video", f"Use animated WebP instead of a video element: {attrs}"
        for value in attrs.values():
            assert not value or ".mp4" not in value.lower(), f"MP4 reference is prohibited: {value}"
        self.classes.update(attrs.get("class", "").split())
        if attrs.get("id"):
            self.element_ids.add(attrs["id"])
        if tag != "link":
            return
        rel = attrs.get("rel", "").split()
        href = attrs.get("href")
        if "icon" in rel:
            self.icons.append(href)
        if "stylesheet" in rel:
            self.stylesheets.append(href)


def local_path(root: Path, url: str) -> Path:
    return root / urlparse(url).path.lstrip("/")


def check(root: Path) -> None:
    assert not [p for p in root.rglob("*") if p.suffix.lower() == ".mp4"], "MP4 files must not be published"
    for path in root.rglob("*.html"):
        Assets(path)
    for path in (root / "assets/home").glob("*.json"):
        Assets(path, html=json.loads(path.read_text()).get("html", ""))
    article_path = next(root.glob("post/ja/*/index.html"))
    pages = {
        "home": Assets(root / "index.html"),
        "about": Assets(root / "about" / "index.html"),
        "posts": Assets(root / "post" / "ja" / "index.html"),
        "search": Assets(root / "search" / "index.html"),
        "article": Assets(article_path),
    }

    for name, page in pages.items():
        assert len(page.stylesheets) == 1, f"Expected one stylesheet on {name}"
        assert local_path(root, page.stylesheets[0]).is_file(), (
            f"Missing stylesheet on {name}: {page.stylesheets[0]}"
        )

    bundles = {page.stylesheets[0] for page in pages.values()}
    assert len(bundles) == len(pages), (
        "Home, About, Posts, Search, and article pages must use distinct CSS bundles"
    )

    css = {
        name: local_path(root, page.stylesheets[0]).read_text()
        for name, page in pages.items()
    }
    assert ".post-content" in css["about"], "About bundle is missing prose styles"
    assert ".archive-year" in css["posts"], "Posts bundle is missing archive styles"
    assert ".post-entry" in css["search"], "Search bundle is missing result-card styles"
    assert ".search-panel" in css["search"], "Search bundle is missing panel styles"
    assert ".search-result-summary" in css["search"], "Search bundle is missing summary styles"
    assert "search-panel" in pages["search"].classes
    assert {"searchInput", "searchStatus", "searchResults"} <= pages["search"].element_ids

    home = pages["home"]
    assert not any(icon and icon.endswith("favicon.ico") for icon in home.icons), (
        "The oversized legacy favicon.ico must not be requested"
    )
    assert any(icon and "favicon-16x16.png" in icon for icon in home.icons)
    assert any(icon and "favicon-32x32.png" in icon for icon in home.icons)

    print("Asset delivery verified: page-specific CSS dependencies and PNG favicons")


if __name__ == "__main__":
    check(Path("public"))
