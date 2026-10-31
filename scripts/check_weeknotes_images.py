#!/usr/bin/env python3
"""Check reserved image space and native, crawlable responsive image delivery."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


class Images(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.images = []
        self.frames = []
        self.feed(path.read_text())

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        if tag in {"img", "iframe"}:
            assert len(attrs) == len(pairs), f"Duplicate media attributes: {pairs}"
        if tag == "img" and "/weeknotes/" in attrs.get("src", ""):
            self.images.append(attrs)
        if tag == "iframe":
            self.frames.append(attrs)


def check(root: Path) -> None:
    count = 0
    for path in (root / "weeknotes").rglob("index.html"):
        page = Images(path)
        for image in page.images:
            assert int(image.get("width", 0)) > 0, (path, image)
            assert int(image.get("height", 0)) > 0, (path, image)
            assert image.get("decoding") == "async", (path, image)
            assert image.get("loading") in {"lazy", "eager"}, (path, image)
            assert "alt" in image, (path, image)
            src = image["src"]
            # The shared fallback banner is already small; it needs no derivatives.
            if "/weeknotes/image/" in src:
                continue
            assert image.get("srcset") and image.get("sizes"), (path, image)
            widths = []
            for candidate in image["srcset"].split(","):
                url, descriptor = candidate.strip().rsplit(" ", 1)
                assert descriptor.endswith("w") and int(descriptor[:-1]) > 0
                widths.append(descriptor)
                assert (root / unquote(urlparse(url).path).lstrip("/")).is_file(), url
            assert len(widths) == len(set(widths)), (path, image)
            if image.get("fetchpriority") == "high":
                assert image["loading"] == "eager", (path, image)
                assert not image["sizes"].startswith("auto"), (path, image)
            count += 1
        for frame in page.frames:
            assert frame.get("loading") == "lazy", (path, frame)
    assert count > 0, "No responsive Weeknotes images checked"
    print(f"Weeknotes image delivery verified: {count} image uses, reserved dimensions and lazy embeds")


if __name__ == "__main__":
    check(Path("public"))
