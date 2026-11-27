#!/usr/bin/env python3
"""debimate の新しいページを Misskey へ「種類：題名 + 改行 + URL」で投稿する（.github/workflows/msky-announce.yml から呼ぶ）。

対象・範囲・上限は scripts/bsky_announce.py と同じで、その関数をそのまま使う。違うのは次の3つ。
- 投稿は msky（nao1215/misskey-terminal-client）の `msky post` に任せる。
- 二重投稿の防止: 投稿前に `msky author` で自分のノートを遡り、本文にある URL と同じものがあれば飛ばす。
- URL はパーセントエンコードのまま載せる。Misskey は日本語を含む URL を途中までしかリンクにしないため。
  Misskey の本文の上限は 3000 字なので、bsky の 300 字の切り詰めは要らない。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time

import bsky_announce as ba

MAX_TEXT = 3000  # Misskey の既定の maxNoteTextLength


def me() -> str:
    """ログイン中のアカウント（MSKY_TOKEN と MSKY_HOST）を @name@host で返す。"""
    out = subprocess.run(["msky", "whoami", "--json"], check=True, capture_output=True, text=True).stdout
    u = json.loads(out)
    return f"@{u['username']}@{u['host']}"


def posted_urls(actor: str, limit: int = 300) -> set[str]:
    out = subprocess.run(
        ["msky", "author", actor, "-n", str(limit), "--filter", "no-replies", "--json"],
        check=True, capture_output=True, text=True,
    ).stdout
    urls: set[str] = set()
    for line in out.splitlines():
        if not line.startswith("{"):
            continue
        n = json.loads(line)
        urls.update(ba.norm(u) for u in re.findall(r"https?://\S+", n.get("text") or ""))
    return urls


def post_text(kind: str, title: str, url: str) -> str:
    prefix = ba.PREFIXES[kind]
    room = MAX_TEXT - len(prefix) - len(url) - 1  # 改行の分
    if len(title) > room:
        title = title[: max(room - 1, 0)] + "…"
    return f"{prefix}{title}\n{url}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("recent", "yesterday", "since", "latest"), default="recent")
    ap.add_argument("--date", help="yesterday ではその日だけ、since ではその日から今日まで（JST、YYYY-MM-DD）")
    ap.add_argument("--max", type=int, default=ba.MAX_POSTS, help=f"これより多ければ何も投稿しない（既定 {ba.MAX_POSTS}）")
    ap.add_argument("--kinds", default=",".join(ba.KINDS), help=f"対象の種類（カンマ区切り）: {','.join(ba.KINDS)}")
    ap.add_argument("--dry-run", action="store_true", help="投稿せずに表示だけする")
    args = ap.parse_args()

    kinds = [k for k in args.kinds.split(",") if k]
    if bad := set(kinds) - set(ba.KINDS):
        ap.error(f"知らない種類: {', '.join(sorted(bad))}")

    candidates: list[dict] = []
    rss = ba.rss_items() if set(kinds) & {"post", "notes", "ml"} else []
    today = dt.datetime.now(ba.JST).date()
    if args.mode in ("recent", "yesterday", "since"):
        if args.mode == "recent":
            first, last, end = today - dt.timedelta(days=1), today, None
        elif args.mode == "since":
            if not args.date:
                ap.error("since には --date が要る")
            first, last, end = dt.date.fromisoformat(args.date), today, None
        else:
            first = last = dt.date.fromisoformat(args.date) if args.date else today - dt.timedelta(days=1)
            end = dt.datetime.combine(last + dt.timedelta(days=1), dt.time(), ba.JST)
        print(f"対象: {first} 〜 {last}（JST）")
        base, head = ba.window(dt.datetime.combine(first, dt.time(), ba.JST), end)
        titles = ba.published_titles(base, head)
        candidates += [i for i in rss if i["kind"] in kinds and (first <= i["date"] <= last or i["title"] in titles)]
        if "weeknotes" in kinds and head:
            candidates += ba.topics_added(base, head)
    else:
        for k in kinds:
            if k == "weeknotes":
                candidates += ba.weeknotes_latest()
            else:
                candidates += [i for i in rss if i["kind"] == k][:1]

    done = posted_urls(me())
    todo, seen = [], set()
    for c in candidates:
        key = ba.norm(c["url"])
        if key in done or key in seen:
            print(f"投稿済みのため飛ばす: {c['url']}")
            continue
        if not ba.is_live(c["url"]):
            print(f"まだ公開されていないため飛ばす: {c['url']}")
            continue
        seen.add(key)
        todo.append(c)

    if len(todo) > args.max:
        print(f"投稿が {len(todo)} 件あり上限 {args.max} を超えるため、何も投稿しない", file=sys.stderr)
        for c in todo:
            print(f"  {c['kind']}: {c['title']} {c['url']}", file=sys.stderr)
        return 1
    if not todo:
        print("投稿するものは無い")
        return 0

    for i, c in enumerate(todo):
        text = post_text(c["kind"], c["title"], c["url"])
        print(f"[{c['kind']}] {text.replace(chr(10), ' ')}")
        if args.dry_run:
            # 送らずに、本文とログインと先頭のリンクのプレビューを確かめる
            subprocess.run(["msky", "post", "--dry-run", text], check=True)
            continue
        if i:
            time.sleep(5)
        subprocess.run(["msky", "post", text], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
