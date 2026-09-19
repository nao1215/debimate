#!/usr/bin/env python3
"""Validate responsive cover images and homepage LCP preloading."""

from html.parser import HTMLParser
from pathlib import Path
import re


class HomePage(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.cover_images = []
        self.image_preloads = []
        self.oss_badges = []
        self.in_cover = False
        self.oss_style = ""
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        has_oss_pick = any(key == "data-oss-pick" for key, _ in attrs)
        attrs = dict(attrs)
        if tag == "figure" and "entry-cover" in attrs.get("class", "").split():
            self.in_cover = True
        if tag == "img" and self.in_cover:
            self.cover_images.append(attrs)
        if tag == "img" and "oss-card-badge" in attrs.get("class", "").split():
            self.oss_badges.append(attrs)
        if tag == "link" and "preload" in attrs.get("rel", "").split() and attrs.get("as") == "image":
            self.image_preloads.append(attrs)
        if has_oss_pick:
            self.oss_style = attrs.get("style", "")

    def handle_endtag(self, tag):
        if tag == "figure":
            self.in_cover = False


def check(root: Path) -> None:
    home = HomePage(root / "index.html")
    assert home.cover_images, "No cover images found on the homepage"
    for image in home.cover_images:
        for attribute in ("srcset", "sizes", "width", "height"):
            assert image.get(attribute), f"Homepage cover is missing {attribute}: {image.get('src')}"
        assert image.get("loading") == "lazy", f"Homepage cover must be lazy-loaded: {image.get('src')}"
        assert image.get("sizes") == (
            "(min-width: 992px) 300px, "
            "(min-width: 769px) calc((100vw - 64px) / 2 - 50px), "
            "(min-width: 652px) calc((100vw - 44px) / 2 - 30px), "
            "calc(100vw - 58px)"
        ), (
            f"Homepage cover has an inaccurate sizes hint: {image.get('sizes')}"
        )

    assert home.oss_badges, "No Featured OSS badges found on the homepage"
    for badge in home.oss_badges:
        assert badge.get("width") and badge.get("height"), (
            f"Featured OSS badge is missing intrinsic dimensions: {badge.get('src')}"
        )

    match = re.search(r"--oss-pick-bg:\s*url\(['\"]?([^'\")]+)", home.oss_style)
    assert match, "Featured OSS background image not found"
    background_url = match.group(1)
    matching_preloads = [item for item in home.image_preloads if item.get("href") == background_url]
    assert len(matching_preloads) == 1, "Featured OSS background must be preloaded exactly once"
    assert matching_preloads[0].get("fetchpriority") == "high", "LCP preload must have high priority"

    second_page = root / "page" / "2" / "index.html"
    if second_page.exists():
        assert not HomePage(second_page).image_preloads, "Pagination pages must not preload the homepage LCP image"

    print(
        f"Image delivery verified: {len(home.cover_images)} responsive covers and one LCP preload"
    )


if __name__ == "__main__":
    check(Path("public"))
