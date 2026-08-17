#!/usr/bin/env python3
"""ビルド済みの public/ を走査し、サイト内リンクの切れとlocalhostリンクを検出する。

muffet と違ってネットワークへ出ないため、外部サイトの 403/429 に影響されず
デプロイ前に実行できる。見るのは以下の 3 点。

1. サイト内リンクの 404（相対リンクと https://debimate.jp/ 始まりの絶対リンク）
2. HTML を指すリンクのフラグメントが、その先の id として実在するか
3. localhost / 127.0.0.1 などローカル環境のURLが混入していないか

裸のURLを 1 行だけ置く書き方は、Goldmark の autolink がASCII以外で打ち切る
ため日本語スラッグだと壊れたhrefになる。1 はその種の事故を拾う目的が大きい。
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = REPO_ROOT / "public"
BASE_URL = "https://debimate.jp"
SITE_HOSTS = {"debimate.jp", "www.debimate.jp"}

# リンク先として辿る属性。srcset だけはカンマ区切りの複数値を持つ
URL_ATTRS = ("href", "src", "data-src", "poster")
SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "#")

# 本文が localhost を語る記事は多いので、リンク属性に現れた時だけ弾く。
# ただし hugo server のポートだけは、地の文でも貼り間違いとみなす
LOCAL_HOST_RE = re.compile(r"^(?:https?:)?//(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(?:[:/]|$)", re.IGNORECASE)
HUGO_SERVER_RE = re.compile(r"localhost:1313")


class Extractor(HTMLParser):
    """リンク候補の URL と、id/name として定義された値を集める。

    --minify 付きのビルドは属性の引用符が外れるため、正規表現ではなく
    HTMLParser で読む。meta refresh を持つページは aliases 由来の生成物
    なので、リンク元としては数えない。
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []
        self.ids: set[str] = set()
        self.is_redirect_stub = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value for name, value in attrs if value is not None}

        if tag == "meta" and values.get("http-equiv", "").lower() == "refresh":
            self.is_redirect_stub = True

        for key in ("id", "name"):
            if key in values and (tag != "meta"):
                self.ids.add(values[key])

        for attr in URL_ATTRS:
            if attr in values:
                self.urls.append(values[attr])

        # srcset は "URL 記述子, URL 記述子" の形なので分解してから足す
        if "srcset" in values:
            for candidate in values["srcset"].split(","):
                url = candidate.strip().split(" ")[0]
                if url:
                    self.urls.append(url)


def resolve(path: str) -> Path | None:
    """サイト絶対パスを public/ 配下の実ファイルへ対応付ける。無ければ None。"""
    target = PUBLIC_ROOT / unquote(path).lstrip("/")
    if target.is_dir():
        index = target / "index.html"
        return index if index.is_file() else None
    return target if target.is_file() else None


def parse(path: Path) -> Extractor:
    parser = Extractor()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parser


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()

    if not PUBLIC_ROOT.is_dir():
        print(f"{PUBLIC_ROOT.relative_to(REPO_ROOT)}/ が無い。先に hugo でビルドする")
        return 1

    pages = sorted(PUBLIC_ROOT.rglob("*.html"))
    parsed: dict[Path, Extractor] = {}
    broken: dict[str, set[str]] = defaultdict(set)
    anchors: dict[str, set[str]] = defaultdict(set)
    locals_: dict[str, set[str]] = defaultdict(set)

    for page in pages:
        source = "/" + str(page.relative_to(PUBLIC_ROOT)).removesuffix("index.html")
        document = parse(page)
        parsed[page] = document
        if document.is_redirect_stub:
            continue

        if HUGO_SERVER_RE.search(page.read_text(encoding="utf-8", errors="replace")):
            locals_["localhost:1313"].add(source)

        for raw in document.urls:
            url = raw.strip()
            if not url or url.startswith(SKIP_SCHEMES):
                continue
            if LOCAL_HOST_RE.match(url):
                locals_[url].add(source)
                continue

            parts = urlparse(urljoin(f"{BASE_URL}{source}", url))
            if parts.scheme not in ("http", "https") or parts.netloc not in SITE_HOSTS:
                continue

            target = resolve(parts.path or "/")
            if target is None:
                broken[parts.path].add(source)
            elif parts.fragment and target.suffix == ".html":
                fragment = unquote(parts.fragment)
                known = parsed.setdefault(target, parse(target)).ids
                if fragment not in known and parts.fragment not in known:
                    anchors[f"{parts.path}#{fragment}"].add(source)

    def report(title: str, findings: dict[str, set[str]]) -> None:
        print(f"{title}: {len(findings)}")
        for target in sorted(findings):
            sources = sorted(findings[target])
            print(f"  {target}")
            for source in sources[:5]:
                print(f"      linked from {source}")
            if len(sources) > 5:
                print(f"      ... and {len(sources) - 5} more")

    print(f"checked {len(pages)} html files under {PUBLIC_ROOT.relative_to(REPO_ROOT)}/")
    report("broken internal links", broken)
    report("missing anchors", anchors)
    report("localhost links", locals_)

    return 1 if (broken or anchors or locals_) else 0


if __name__ == "__main__":
    raise SystemExit(main())
