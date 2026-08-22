#!/usr/bin/env python3
"""GitHub Discussions を取得して data/bbs.json に書き出す。

BBS (/bbs/) はこの JSON から Hugo のコンテンツアダプタ
(content/bbs/_content.gotmpl) がスレッド一覧と各スレッドのページを生成する。
書き込み側は giscus が担当し、読む側はビルド時に静的化する。

JSON のキーは全て小文字にする。Hugo はテンプレートの文脈によってデータの
キーを小文字化したりしなかったりするので、最初から小文字に揃えておく。

認証は環境変数 GITHUB_TOKEN、無ければ `gh auth token` を使う。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# 表示用タイムゾーン。Hugo の time.AsTime はオフセットを変換しないので、
# JSON に書く時点で JST (+09:00) にしておく
TZ = ZoneInfo("Asia/Tokyo")

OWNER = "nao1215"
REPO = "debimate"
# 掲示板として見せるカテゴリ。giscus (params.toml の [giscus]) が
# スレッドを作る先と一致させる。記事コメント用に過去作られた
# Announcements のスレッドは除外する
BBS_CATEGORIES = {"general"}
OUT = Path(__file__).resolve().parent.parent / "data" / "bbs.json"

QUERY = """
query($owner: String!, $repo: String!, $after: String) {
  repository(owner: $owner, name: $repo) {
    discussions(first: 100, after: $after, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        url
        bodyHTML
        createdAt
        updatedAt
        locked
        isAnswered
        author { login url avatarUrl }
        category { name slug }
        comments(last: 1) {
          totalCount
          nodes { createdAt author { login } }
        }
        reactions { totalCount }
      }
    }
  }
}
"""


def token() -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    try:
        return subprocess.run(
            ["gh", "auth", "token"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        sys.exit(f"GITHUB_TOKEN が無く gh auth token も失敗した: {exc}")


def jst(iso: str) -> str:
    """GitHub の UTC ISO8601 (…Z) を JST の ISO8601 に変換する。"""
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ).isoformat()


def graphql(tok: str, variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {tok}",
            "Content-Type": "application/json",
            "User-Agent": "debimate-bbs-fetch",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.load(res)
    if "errors" in body:
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]


def main() -> None:
    tok = token()
    threads: list[dict] = []
    after = None
    while True:
        data = graphql(tok, {"owner": OWNER, "repo": REPO, "after": after})
        conn = data["repository"]["discussions"]
        for n in conn["nodes"]:
            if (n["category"] or {}).get("slug") not in BBS_CATEGORIES:
                continue
            last = n["comments"]["nodes"][0] if n["comments"]["nodes"] else None
            last_activity = max(
                n["updatedAt"], last["createdAt"] if last else n["createdAt"]
            )
            author = n["author"] or {"login": "ghost", "url": "", "avatarUrl": ""}
            threads.append(
                {
                    "number": n["number"],
                    "title": n["title"],
                    "url": n["url"],
                    "bodyhtml": n["bodyHTML"],
                    "createdat": jst(n["createdAt"]),
                    "updatedat": jst(n["updatedAt"]),
                    "lastactivityat": jst(last_activity),
                    "locked": n["locked"],
                    "isanswered": n["isAnswered"],
                    "author": {
                        "login": author["login"],
                        "url": author["url"],
                        "avatarurl": author["avatarUrl"],
                    },
                    "category": n["category"],
                    "commentcount": n["comments"]["totalCount"],
                    "lastcommentby": (last["author"] or {}).get("login") if last else None,
                    "reactioncount": n["reactions"]["totalCount"],
                }
            )
        if not conn["pageInfo"]["hasNextPage"]:
            break
        after = conn["pageInfo"]["endCursor"]

    threads.sort(key=lambda t: t["lastactivityat"], reverse=True)
    OUT.write_text(
        json.dumps(
            {
                "fetchedat": datetime.now(TZ).isoformat(timespec="seconds"),
                "threads": threads,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT} ({len(threads)} threads)")


if __name__ == "__main__":
    main()
