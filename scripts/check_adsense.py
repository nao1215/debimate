#!/usr/bin/env python3
"""Ensure the AdSense loader is emitted exactly where an ad slot exists."""

from pathlib import Path
from html.parser import HTMLParser


LOADER = "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
SLOT = 'data-ad-slot="7574390420"'
MINIFIED_SLOT = "data-ad-slot=7574390420"


class ArticleLayout(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.article = False
        self.content_depth = 0
        self.content_done = False
        self.footer_seen = False
        self.slots = 0
        self.correct_position = True
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if tag == "article" and "post-single" in classes:
            self.article = True
        if tag == "div":
            if self.content_depth:
                self.content_depth += 1
            elif "post-content" in classes:
                self.content_depth = 1
        if tag == "footer" and "post-footer" in classes:
            self.footer_seen = True
        if tag == "ins" and "data-ad-slot" in attrs:
            self.slots += 1
            self.correct_position &= self.content_done and not self.footer_seen

    def handle_endtag(self, tag):
        if tag == "div" and self.content_depth:
            self.content_depth -= 1
            if not self.content_depth:
                self.content_done = True


def check(root: Path) -> None:
    ad_pages = 0
    mismatches = []
    for path in root.rglob("*.html"):
        html = path.read_text(errors="replace")
        has_loader = LOADER in html
        has_slot = SLOT in html or MINIFIED_SLOT in html
        if has_loader != has_slot:
            mismatches.append((path, has_loader, has_slot))
        layout = ArticleLayout(html)
        section = path.relative_to(root).parts[0]
        if layout.article and section in ("post", "notes", "ml", "weeknotes"):
            assert layout.slots == 1, f"Expected one article ad slot: {path}"
        if has_slot:
            assert layout.slots == 1, f"Duplicate ad slots: {path}"
            assert layout.correct_position, f"Ad must follow the body and precede the footer: {path}"
            assert html.count(LOADER) == 1, f"Duplicate AdSense loaders: {path}"
            ad_pages += 1

    assert not mismatches, "AdSense loader/slot mismatch:\n" + "\n".join(
        f"  {path}: loader={loader}, slot={slot}"
        for path, loader, slot in mismatches
    )
    assert ad_pages, "No pages with AdSense slots found"
    print(f"AdSense loading verified: loader limited to {ad_pages} pages with ad slots")


if __name__ == "__main__":
    check(Path("public"))
