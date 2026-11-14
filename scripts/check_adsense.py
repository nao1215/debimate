#!/usr/bin/env python3
"""Ensure published pages contain no AdSense scripts or advertising slots."""

from html.parser import HTMLParser
from pathlib import Path
import sys


class AdSenseMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.script = False
        self.found = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.script = True
            self.found |= "googlesyndication.com" in attrs.get("src", "")
        self.found |= "adsbygoogle" in attrs.get("class", "").split()
        self.found |= "data-ad-slot" in attrs or "data-ad-client" in attrs
        self.found |= tag == "meta" and attrs.get("name") == "google-adsense-account"

    def handle_data(self, data):
        if self.script:
            self.found |= "adsbygoogle" in data

    def handle_endtag(self, tag):
        if tag == "script":
            self.script = False


def check(root: Path) -> None:
    pages = list(root.rglob("*.html"))
    assert pages, f"No built HTML pages found: {root}"
    remaining = []
    for path in pages:
        parser = AdSenseMarkup()
        parser.feed(path.read_text(errors="replace"))
        if parser.found:
            remaining.append(str(path))
    assert not remaining, "AdSense remains in:\n" + "\n".join(remaining)
    assert not (root / "ads.txt").exists(), "Obsolete ads.txt remains in build output"
    print(f"AdSense removal verified: {len(pages)} pages contain no ad scripts or slots")


if __name__ == "__main__":
    check(Path(sys.argv[1] if len(sys.argv) > 1 else "public"))
