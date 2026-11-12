#!/usr/bin/env python3
"""debimate の新しいページを Bluesky へ「題名 + URL」で投稿する（.github/workflows/bsky-announce.yml から呼ぶ）。

対象と取り出し方:
- 記事（/post/）・技術ノート（/notes/）・ML ノート（/ml/）: 公開中のサイトの index.xml から題名・URL・pubDate を取る。
  対象は、pubDate が範囲に入るものと、範囲内の commit で公開されたもの（新しく足された、または draft から外れた
  Markdown と同じ題名のもの）。後者は、draft の間に書いた古い date のまま公開した時の取りこぼしを防ぐ。
  書き直しでは date を変えず draft にもしないので、書き直したノートは対象にならない。
- weeknotes: 1 話ずつの topic ページ（/weeknotes/YYYY-MM-DD/<sha256(見出し行)の先頭 12 桁>/）を投稿する。
  topic の日付は週の月曜で固定なので、git の差分で「範囲内に足された #### 見出し」を探す。
  draft から外れた週は、その週の見出しを全部対象にする。
  URL の作り方は content/weeknotes/_content.gotmpl と layouts/partials/weeknotes/headings.html に合わせる。

範囲:
- recent（既定。毎日昼の CI が使う）: JST の昨日と今日に公開された分
  （weeknotes は昨日の 0 時から今までの commit で足された見出し）。前の回と重なる分は、投稿済みの URL として飛ばす。
  まだ公開されていない URL は飛ばすので、cron の後にデプロイされた分は次の回に投稿する。
- yesterday: JST の昨日（または --date の日）に公開された分。取りこぼした日を後から流す時に使う。
- latest: 種類ごとに最新の 1 件。

二重投稿の防止: 投稿前に公開 API（getAuthorFeed、認証不要）で自分の投稿を遡り、同じ URL が既にあれば飛ばす。
投稿は bsky（nao1215/bluesky-terminal-client）の `bsky post` に任せる。URL は bsky が押せるリンクにする。
"""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

SITE = "https://debimate.jp"
JST = dt.timezone(dt.timedelta(hours=9))
KINDS = ("post", "notes", "ml", "weeknotes")
REPO = Path(__file__).resolve().parent.parent
WEEKNOTES_GLOB = "content/weeknotes/*/*/index.md"
UA = "debimate-bsky-announce"
MAX_POSTS = 10  # 誤って大量に流さないための上限
# 告知する記事・ノートの置き場所（weeknotes は見出しで扱うので別）
ANNOUNCED_DIRS = ("content/post/", "content/notes/", "projects/ml/notes/")


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read()


def is_live(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status == 200
    except Exception:
        return False


# --- 記事・技術ノート・ML ノート（RSS） ---

def rss_items() -> list[dict]:
    root = ET.fromstring(fetch(f"{SITE}/index.xml"))
    items = []
    for it in root.iter("item"):
        link = (it.findtext("link") or "").strip()
        title = html.unescape((it.findtext("title") or "").strip())
        pub = it.findtext("pubDate")
        path = urllib.parse.urlparse(link).path
        kind = path.strip("/").split("/")[0]
        if kind not in ("post", "notes", "ml") or not pub or not title:
            continue
        # 各セクションの一覧ページ自体は除く
        if path.rstrip("/").count("/") < 2:
            continue
        when = email.utils.parsedate_to_datetime(pub).astimezone(JST)
        items.append({"kind": kind, "title": title, "url": link, "date": when.date()})
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


# --- weeknotes（git の差分から見出しを拾う） ---

CODE_FENCE = re.compile(r"(?ms)^`{3,}[^\n]*\n.*?^`{3,}\s*$|^~{3,}[^\n]*\n.*?^~{3,}\s*$")
HEADING = re.compile(r"(?m)^####[ \t]+[^\r\n]+")


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True).stdout


def headings(source: str) -> list[str]:
    return HEADING.findall(CODE_FENCE.sub("", source))


def topic_title(heading: str) -> str:
    t = re.sub(r"^####[ \t]+", "", heading)
    t = re.sub(r"[ \t]+#+[ \t]*$", "", t)
    t = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"[`*_]", "", t)
    return html.unescape(t).strip()


def week_date(source: str) -> str | None:
    m = re.search(r"(?m)^date:\s*\"?(\d{4}-\d{2}-\d{2})", source)
    return m.group(1) if m else None


def is_draft(source: str) -> bool:
    return bool(re.search(r"(?m)^draft:\s*true\s*$", front_matter(source)))


def front_matter(source: str) -> str:
    m = re.match(r"(?s)^---\r?\n(.*?)\r?\n---", source)
    return m.group(1) if m else ""


def front_title(source: str) -> str | None:
    m = re.search(r"(?m)^title:\s*(.+?)\s*$", front_matter(source))
    if not m:
        return None
    t = m.group(1)
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
        t = t[1:-1].replace('\\"', '"') if t[0] == '"' else t[1:-1].replace("''", "'")
    return t


def show(rev: str | None, path: str) -> str | None:
    if not rev:
        return None
    try:
        return git("show", f"{rev}:{path}")
    except subprocess.CalledProcessError:
        return None


def newly_published(base: str | None, head: str) -> list[tuple[str, str]]:
    """base..head で公開された Markdown（head で draft でなく、base に無いか draft だった）の (パス, 本文)。"""
    if base:
        names = git("diff", "--name-only", "--no-renames", "--diff-filter=AM", base, head, "--", "*.md")
    else:
        names = git("show", "--name-only", "--no-renames", "--format=", head, "--", "*.md")
    out = []
    for path in names.split():
        now = show(head, path)
        if now is None or is_draft(now):
            continue
        before = show(base, path) if base else show(f"{head}^", path)
        if before is None or is_draft(before):
            out.append((path, now))
    return out


def topics_added(base: str | None, head: str) -> list[dict]:
    """base..head の間に足された #### 見出しを、head 時点の本文で topic にする。"""
    if base:
        diff = git("diff", "--unified=0", base, head, "--", WEEKNOTES_GLOB)
    else:
        diff = git("show", "--unified=0", "--format=", head, "--", WEEKNOTES_GLOB)
    added: dict[str, set[str]] = {}
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
        elif current and line.startswith("+####"):
            added.setdefault(current, set()).add(line[1:].rstrip("\r"))
    # draft から外れた週は、前から書いてあった見出しも今回初めて公開される
    for path, source in newly_published(base, head):
        if re.fullmatch(r"content/weeknotes/\d{4}/[^/]+/index\.md", path):
            added.setdefault(path, set()).update(headings(source))
    topics = []
    for path, lines in added.items():
        try:
            source = git("show", f"{head}:{path}")
        except subprocess.CalledProcessError:
            continue
        if is_draft(source):
            continue
        date = week_date(source)
        if not date:
            continue
        for h in headings(source):  # コードブロック内の #### は除かれる。順番は本文どおり
            if h in lines:
                key = hashlib.sha256(h.encode()).hexdigest()[:12]
                topics.append({"kind": "weeknotes", "title": topic_title(h),
                               "url": f"{SITE}/weeknotes/{date}/{key}/", "date": date})
    return topics


def rev_before(when: dt.datetime) -> str | None:
    out = git("rev-list", "-1", f"--before={when.isoformat()}", "HEAD").strip()
    return out or None


def window(start: dt.datetime, end: dt.datetime | None) -> tuple[str | None, str | None]:
    """start から end（None なら今の HEAD）までの commit の範囲。範囲に commit が無ければ head は None。"""
    base = rev_before(start)
    head = rev_before(end) if end else git("rev-parse", "HEAD").strip()
    return (base, head) if head and head != base else (base, None)


def published_titles(base: str | None, head: str | None) -> set[str]:
    """範囲内に公開された記事・ノートの題名（weeknotes は見出しで扱うので除く）。"""
    if not head:
        return set()
    # 記事・技術ノート・ML ノートの本文だけ。Games・OSS などの固定ページと、_index.md（一覧ページ）は告知しない
    return {t for path, src in newly_published(base, head)
            if path.startswith(ANNOUNCED_DIRS) and not Path(path).name.startswith("_")
            and (t := front_title(src))}


def weeknotes_latest() -> list[dict]:
    """見出しを足した最後の commit で足された見出しのうち、本文で最後のもの。"""
    for sha in git("log", "--format=%H", "-n", "200", "--", WEEKNOTES_GLOB).split():
        topics = topics_added(None, sha)
        if topics:
            return [topics[-1]]
    return []


# --- 二重投稿の防止 ---

def norm(url: str) -> str:
    """日本語に戻した URL とエンコードされた URL を同じものとして比べる。"""
    return urllib.parse.unquote(url).rstrip("/")


def posted_urls(actor: str, pages: int = 10) -> set[str]:
    urls: set[str] = set()
    cursor = None
    for _ in range(pages):
        q = {"actor": actor, "limit": "100", "filter": "posts_no_replies"}
        if cursor:
            q["cursor"] = cursor
        data = json.loads(fetch("https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?" + urllib.parse.urlencode(q)))
        for f in data.get("feed", []):
            rec = f["post"].get("record", {})
            for facet in rec.get("facets", []):
                for feat in facet.get("features", []):
                    if "uri" in feat:
                        urls.add(norm(feat["uri"]))
            ext = rec.get("embed", {}).get("external", {})
            if ext.get("uri"):
                urls.add(norm(ext["uri"]))
            urls.update(norm(u) for u in re.findall(r"https?://\S+", rec.get("text", "")))
        cursor = data.get("cursor")
        if not cursor:
            break
    return urls


# --- 投稿の本文 ---

MAX_GRAPHEMES = 300  # Bluesky の本文の上限（bsky も同じ数で弾く）
# bsky が URL の途中でもリンクを切る文字（bluesky-terminal-client の src/api/facets.rs の URL_BREAK・TRAILING）
URL_BREAK = set("、。，．！？：；「」『』【】〈〉《》〔〕［］｛｝　…〜“”‘’")
TRAILING = set(".,;:!?)]}\"'」。、！？）』】〉》〕］｝，．：；…”’")


def display_url(url: str) -> str:
    """日本語のスラッグはパーセントエンコードのままだと 300 字を超えるので、bsky がリンクにできる範囲で戻す。"""
    decoded = urllib.parse.unquote(url)
    if decoded == url or any(ch.isspace() or ch in URL_BREAK for ch in decoded) or decoded[-1] in TRAILING:
        return url
    return decoded


def post_text(title: str, url: str) -> str:
    link = display_url(url)
    room = MAX_GRAPHEMES - len(link) - 1  # 改行の分
    if len(title) > room:
        title = title[: max(room - 1, 0)] + "…"
    return f"{title}\n{link}" if room > 0 else link


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("recent", "yesterday", "latest"), default="recent")
    ap.add_argument("--date", help="yesterday の代わりに JST のこの日（YYYY-MM-DD）を対象にする")
    ap.add_argument("--kinds", default=",".join(KINDS), help=f"対象の種類（カンマ区切り）: {','.join(KINDS)}")
    ap.add_argument("--actor", default=os.environ.get("BSKY_IDENTIFIER"), help="二重投稿を調べる自分のハンドル")
    ap.add_argument("--dry-run", action="store_true", help="投稿せずに表示だけする")
    args = ap.parse_args()

    kinds = [k for k in args.kinds.split(",") if k]
    if bad := set(kinds) - set(KINDS):
        ap.error(f"知らない種類: {', '.join(sorted(bad))}")
    if not args.actor:
        ap.error("--actor か環境変数 BSKY_IDENTIFIER でハンドルを指定する")

    candidates: list[dict] = []
    rss = rss_items() if set(kinds) & {"post", "notes", "ml"} else []
    today = dt.datetime.now(JST).date()
    if args.mode in ("recent", "yesterday"):
        if args.mode == "recent":
            first, last, end = today - dt.timedelta(days=1), today, None
        else:
            first = last = dt.date.fromisoformat(args.date) if args.date else today - dt.timedelta(days=1)
            end = dt.datetime.combine(last + dt.timedelta(days=1), dt.time(), JST)
        print(f"対象: {first} 〜 {last}（JST）")
        base, head = window(dt.datetime.combine(first, dt.time(), JST), end)
        titles = published_titles(base, head)
        candidates += [i for i in rss if i["kind"] in kinds and (first <= i["date"] <= last or i["title"] in titles)]
        if "weeknotes" in kinds and head:
            candidates += topics_added(base, head)
    else:
        for k in kinds:
            if k == "weeknotes":
                candidates += weeknotes_latest()
            else:
                candidates += [i for i in rss if i["kind"] == k][:1]

    done = posted_urls(args.actor)
    todo, seen = [], set()
    for c in candidates:
        key = norm(c["url"])
        if key in done or key in seen:
            print(f"投稿済みのため飛ばす: {c['url']}")
            continue
        if not is_live(c["url"]):
            print(f"まだ公開されていないため飛ばす: {c['url']}")
            continue
        seen.add(key)
        todo.append(c)

    if len(todo) > MAX_POSTS:
        print(f"投稿が {len(todo)} 件あり上限 {MAX_POSTS} を超えるため、何も投稿しない", file=sys.stderr)
        for c in todo:
            print(f"  {c['kind']}: {c['title']} {c['url']}", file=sys.stderr)
        return 1
    if not todo:
        print("投稿するものは無い")
        return 0

    for i, c in enumerate(todo):
        text = post_text(c["title"], c["url"])
        print(f"[{c['kind']}] {text.replace(chr(10), ' ')}")
        if args.dry_run:
            continue
        if i:
            time.sleep(5)
        subprocess.run(["bsky", "post", text], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
