#!/usr/bin/env python3
"""Ensure Twitter widgets are loaded once and only near embedded tweets."""

from pathlib import Path
import re


WIDGET_URL = "https://platform.twitter.com/widgets.js"
DIRECT_SCRIPT = re.compile(
    r"<script\b[^>]*\bsrc=[\"']https://platform\.twitter\.com/widgets\.js[\"']",
    re.IGNORECASE,
)


def check(root: Path) -> None:
    embed_pages = 0
    for path in root.rglob("*.html"):
        html = path.read_text(errors="replace")
        has_embed = "twitter-tweet" in html
        references = html.count(WIDGET_URL)
        if has_embed:
            assert references == 1, f"Expected one Twitter loader reference: {path}"
            assert not DIRECT_SCRIPT.search(html), f"Twitter must not load eagerly: {path}"
            assert "IntersectionObserver" in html, f"Twitter lazy loader missing: {path}"
            embed_pages += 1
        else:
            assert references == 0, f"Twitter loader emitted without an embed: {path}"

    assert embed_pages, "No Twitter embed pages found"
    print(f"Twitter embeds verified: one lazy loader on {embed_pages} pages")


if __name__ == "__main__":
    check(Path("public"))
