#!/usr/bin/env python3
"""Validate responsive cover images and homepage LCP preloading."""

from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlparse


class HomePage(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.cover_images = []
        self.image_preloads = []
        self.oss_badges = []
        self.in_weeknote = False
        self.in_cover = False
        self.in_note_cover = False
        self.note_covers = 0
        self.inline_note_titles = 0
        self.oss_style = ""
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        has_oss_pick = any(key == "data-oss-pick" for key, _ in attrs)
        attrs = dict(attrs)
        if tag == "article":
            self.in_weeknote = "weeknote-entry" in attrs.get("class", "").split()
        if tag == "figure" and "entry-cover" in attrs.get("class", "").split():
            self.in_cover = True
            self.in_note_cover = "note-title-cover" in attrs.get("class", "").split()
            self.note_covers += int(self.in_note_cover)
        if tag == "svg" and self.in_note_cover:
            self.inline_note_titles += 1
        if tag == "img" and self.in_cover:
            attrs["weeknote"] = self.in_weeknote
            self.cover_images.append(attrs)
        if tag == "img" and "oss-card-badge" in attrs.get("class", "").split():
            self.oss_badges.append(attrs)
        if tag == "link" and "preload" in attrs.get("rel", "").split() and attrs.get("as") == "image":
            self.image_preloads.append(attrs)
        if has_oss_pick:
            self.oss_style = attrs.get("style", "")

    def handle_endtag(self, tag):
        if tag == "article":
            self.in_weeknote = False
        if tag == "figure":
            self.in_cover = False
            self.in_note_cover = False


class SocialImages(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.images = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        key = attrs.get("property", attrs.get("name"))
        if tag == "meta" and key in ("og:image", "twitter:image"):
            self.images[key] = attrs.get("content", "")


def check_note_ogp(root):
    count = 0
    for page in root.rglob("index.html"):
        images = SocialImages(page.read_text()).images
        url = images.get("og:image", "")
        if "/assets/note-ogp/" not in url:
            continue
        assert images.get("twitter:image") == url, f"Social images differ: {page}"
        assert url.startswith("https://"), f"OGP requires an absolute URL: {page}"
        image = root / urlparse(url).path.lstrip("/")
        png = image.read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n", image
        assert int.from_bytes(png[16:20], "big") == 960, image
        assert int.from_bytes(png[20:24], "big") == 540, image
        count += 1
    assert count > 0, "No note OGP images found"
    print(f"Note OGP verified: {count} pages")


def check(root: Path) -> None:
    home = HomePage(root / "index.html")
    assert home.note_covers > 0, "Missing note cover art"
    assert home.inline_note_titles == home.note_covers, "Note lettering must render inline, without lazy image loading"
    assert home.cover_images, "No cover images found on the homepage"
    for image in home.cover_images:
        for attribute in ("width", "height"):
            assert image.get(attribute), f"Missing {attribute}: {image.get('src')}"
        assert image.get("loading") == "lazy", image.get("src")
        if image.get("src", "").endswith(".svg"):
            # Text-only vector overlays share category backgrounds through CSS.
            svg = root / image["src"].lstrip("/")
            assert svg.stat().st_size < 10000, f"Oversized title SVG: {svg}"
            assert "base64," not in svg.read_text(), f"Background embedded in {svg}"
            continue
        for attribute in ("srcset", "sizes"):
            assert image.get(attribute), f"Missing {attribute}: {image.get('src')}"
        candidates = [item.strip().rsplit(" ", 1)[-1] for item in image["srcset"].split(",") if item.strip()]
        assert len(candidates) == len(set(candidates)), f"Duplicate srcset widths: {image.get('src')}"
        expected_sizes = (
            "(min-width: 1488px) 312px, "
            "(min-width: 901px) calc((100vw - 238px) / 4), "
            "(min-width: 701px) calc((100vw - 186px) / 3), "
            "(min-width: 481px) calc((100vw - 130px) / 2), "
            "calc(100vw - 60px)"
        )
        if image["weeknote"]:
            expected_sizes = "auto, " + expected_sizes.replace("(min-width: 481px) calc((100vw - 130px) / 2), ", "")
            # Generated covers use WebP so animated sources keep moving.
            for candidate in image["srcset"].split(","):
                url, width = candidate.strip().rsplit(" ", 1)
                if "_hu_" in url:
                    assert url.endswith(".webp"), url
                    assert int(width[:-1]) <= 720, candidate
        assert image.get("sizes") == expected_sizes, f"Inaccurate homepage sizes: {image.get('sizes')}"

    assert any(image["weeknote"] for image in home.cover_images), "Missing homepage Weeknotes cards"

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
    check_note_ogp(Path("public"))
