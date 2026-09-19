#!/usr/bin/env python3
"""Ensure the AdSense loader is emitted exactly where an ad slot exists."""

from pathlib import Path


LOADER = "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
SLOT = 'data-ad-slot="7574390420"'
MINIFIED_SLOT = "data-ad-slot=7574390420"


def check(root: Path) -> None:
    ad_pages = 0
    mismatches = []
    for path in root.rglob("*.html"):
        html = path.read_text(errors="replace")
        has_loader = LOADER in html
        has_slot = SLOT in html or MINIFIED_SLOT in html
        if has_loader != has_slot:
            mismatches.append((path, has_loader, has_slot))
        if has_slot:
            ad_pages += 1

    assert not mismatches, "AdSense loader/slot mismatch:\n" + "\n".join(
        f"  {path}: loader={loader}, slot={slot}"
        for path, loader, slot in mismatches
    )
    assert ad_pages, "No pages with AdSense slots found"
    print(f"AdSense loading verified: loader limited to {ad_pages} pages with ad slots")


if __name__ == "__main__":
    check(Path("public"))
