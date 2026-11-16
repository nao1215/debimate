#!/usr/bin/env python3
"""Check that the sitemap and the note-section redirects agree.

/notes/<section>/ and /ml/ redirect to a tab of /notes/ and are noindex, so
they must stay out of sitemap.xml. The notes index, individual notes, ML
articles and the quiz must stay in it. Redirect pages are found from the built
HTML (meta refresh), so the check follows the template rather than a URL list.
"""

from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT = Path("public")
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Redirect sections that must exist (a renamed section should fail loudly).
EXPECTED_REDIRECTS = {"/ml/", "/notes/security/", "/notes/software-architecture/"}

# Pages that must remain in the sitemap.
REQUIRED = {
    "/notes/",
    "/notes/security/passkey/",
    "/notes/software-architecture/cqrs/",
    "/ml/ml/confusion-matrix/",
    "/ml/math/mean/",
    "/ml/quiz/",
}


class Head(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.refresh = None
        self.robots = []
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        attrs = dict(attrs)
        if (attrs.get("http-equiv") or "").lower() == "refresh":
            self.refresh = attrs.get("content", "")
        if attrs.get("name") == "robots":
            self.robots.append(attrs.get("content", ""))


def section_redirects() -> set[str]:
    """Return URL paths of note sections that redirect to /notes/#<tab>."""
    found = set()
    candidates = [ROOT / "ml" / "index.html", *ROOT.glob("notes/*/index.html")]
    for path in candidates:
        if not path.exists():
            continue
        head = Head(path)
        if head.refresh and "/notes/#" in head.refresh:
            found.add("/" + path.parent.relative_to(ROOT).as_posix() + "/")
    return found


def main() -> int:
    errors = []
    tree = ET.parse(ROOT / "sitemap.xml")
    paths = {urlparse(loc.text.strip()).path for loc in tree.findall("s:url/s:loc", NS)}
    locs = [loc.text.strip() for loc in tree.findall("s:url/s:loc", NS)]

    redirects = section_redirects()
    for path in sorted(EXPECTED_REDIRECTS - redirects):
        errors.append(f"expected a redirect section but it does not redirect: {path}")
    for path in sorted(redirects):
        if path in paths:
            errors.append(f"redirect section is listed in sitemap.xml: {path}")
        robots = Head(ROOT / path.strip("/") / "index.html").robots
        if robots != ["noindex, follow"]:
            errors.append(f"redirect section should have one noindex robots meta: {path} {robots}")

    for loc in locs:
        if "#" in loc:
            errors.append(f"sitemap.xml lists a URL with a fragment: {loc}")
    for path in sorted(REQUIRED - paths):
        errors.append(f"page missing from sitemap.xml: {path}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"sitemap OK: {len(locs)} URLs, {len(redirects)} redirect sections excluded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
