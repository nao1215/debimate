#!/usr/bin/env python3
"""Check the built Weeknotes migration: redirects, feeds, and legacy images."""

import argparse
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from check_links import parse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-dir", type=Path, default=Path("public"))
    root = parser.parse_args().public_dir
    content = Path(__file__).resolve().parents[1] / "content/weeknotes"

    redirects = {"": "", "page/1/": ""}
    for page in content.glob("*/*/index.md"):
        slug = f"{page.parent.parent.name}-{page.parent.name}"
        if (root / "weeknotes" / slug / "index.html").exists():
            redirects[f"{slug}/"] = f"{slug}/"
    for source, target in redirects.items():
        page = root / "weekly" / source / "index.html"
        expected = f"https://debimate.jp/weeknotes/{target}"
        parsed = parse(page)
        assert parsed.is_redirect_stub and expected in parsed.urls, page
        text = page.read_text()
        assert f"url={expected}" in text, page
        assert "window.location.search" in text, page
        assert "window.location.hash" in text, page
        assert "window.location.replace" in text, page

    old = ET.parse(root / "weekly/index.xml")
    new = ET.parse(root / "weeknotes/index.xml")
    assert [i.text for i in old.findall("channel/item/link")] == [
        i.text for i in new.findall("channel/item/link")
    ], "Legacy feed must track current Weeknotes"
    for item in old.findall("channel/item"):
        link = item.findtext("link")
        assert item.findtext("guid") == link.replace("/weeknotes/", "/weekly/")
        assert (root / urlparse(link).path.strip("/") / "index.html").exists()

    for image in content.rglob("*"):
        if image.suffix in {".webp", ".gif"}:
            relative = image.relative_to(content)
            if len(relative.parts) > 2:
                year, month_day, *rest = relative.parts
                relative = Path(f"{year}-{month_day}", *rest)
            legacy = root / "weekly" / relative
            assert legacy.read_bytes() == image.read_bytes(), legacy
    assert not list((root / "weekly").rglob("*.md")), "Do not publish source Markdown"
    assert "https://debimate.jp/weekly/" not in (root / "sitemap.xml").read_text()
    print(f"Weeknotes migration verified: {len(redirects)} redirects, RSS, and images")


if __name__ == "__main__":
    main()
