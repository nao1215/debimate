#!/usr/bin/env python3
"""Validate canonical URLs on generated pagination pages."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


class Page(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.canonical = []
        self.in_title = False
        self.is_redirect = False
        self.meta = {}
        self.title = ""
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "link" and "canonical" in attrs.get("rel", "").split():
            self.canonical.append(attrs.get("href"))
        if tag == "meta":
            self.meta[attrs.get("name", attrs.get("property"))] = attrs.get("content")
            if attrs.get("http-equiv", "").lower() == "refresh":
                self.is_redirect = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def check(root: Path) -> None:
    checked = 0
    for path in sorted(root.glob("**/page/*/index.html")):
        try:
            page_number = int(path.parent.name)
        except ValueError:
            continue
        if page_number < 2:
            continue

        page = Page(path)
        # Legacy pagination URLs are redirect pages whose canonical deliberately
        # points at the migration destination rather than at themselves.
        if page.is_redirect:
            continue

        assert len(page.canonical) == 1, f"Expected one canonical URL: {path}"
        canonical = urlparse(page.canonical[0])
        expected_path = "/" + path.parent.relative_to(root).as_posix() + "/"
        assert canonical.scheme == "https", f"Canonical must use HTTPS: {path}"
        assert canonical.netloc == "debimate.jp", f"Unexpected canonical host: {path}"
        assert unquote(canonical.path) == expected_path, (
            f"Canonical must point at the pagination page itself: {path} -> {page.canonical[0]}"
        )
        assert not canonical.query and not canonical.fragment, f"Canonical must be clean: {path}"

        suffix = f" - {page_number}ページ目"
        assert page.title.endswith(suffix), f"Page number missing from title: {path}"
        for key in ("og:title", "twitter:title", "description", "og:description", "twitter:description"):
            assert page.meta.get(key, "").endswith(suffix), (
                f"Page number missing from {key}: {path}"
            )
        checked += 1

    assert checked, "No pagination pages found"
    print(f"Pagination SEO verified: {checked} canonical URLs and unique metadata sets")


if __name__ == "__main__":
    check(Path("public"))
