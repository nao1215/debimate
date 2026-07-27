#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime
import re
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
POST_ROOT = REPO_ROOT / "content" / "post" / "ja"
FRONT_MATTER_DELIM = "---"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WHITESPACE_PATTERN = re.compile(r"[\s　]+")
NON_SLUG_PATTERN = re.compile(r"[^\w\-]", re.UNICODE)


def iter_post_files() -> list[Path]:
    return sorted(path / "index.md" for path in POST_ROOT.iterdir() if (path / "index.md").is_file())


def split_front_matter(text: str) -> tuple[str, list[str], str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != FRONT_MATTER_DELIM:
        raise ValueError("missing YAML front matter")

    closing = None
    for index in range(1, len(lines)):
        if lines[index].strip() == FRONT_MATTER_DELIM:
            closing = index
            break
    if closing is None:
        raise ValueError("unterminated YAML front matter")

    return lines[0], lines[1:closing], "".join(lines[closing + 1 :])


def extract_aliases(front_matter_lines: list[str]) -> tuple[list[str], int | None, int | None]:
    start = None
    end = None
    aliases: list[str] = []

    for index, line in enumerate(front_matter_lines):
        if line.strip() == "aliases:":
            start = index
            end = index + 1
            while end < len(front_matter_lines):
                candidate = front_matter_lines[end]
                if re.match(r"^\s*-\s+", candidate):
                    aliases.append(re.sub(r"^\s*-\s+", "", candidate).strip())
                    end += 1
                    continue
                break
            break

    return aliases, start, end


def slugify(text: str) -> str:
    """移行前のブログが URL に使っていた slug 規則を再現する。

    空白（半角・全角）をハイフンへ寄せ、記号を落とし、英大文字を小文字にする。
    """
    return NON_SLUG_PATTERN.sub("", WHITESPACE_PATTERN.sub("-", text.lower()))


def desired_aliases(index_path: Path, unique_dates: set[str]) -> list[str]:
    dirname = index_path.parent.name
    date_text = dirname[:10]
    if not DATE_PATTERN.match(date_text):
        raise ValueError(f"directory does not start with YYYY-MM-DD: {dirname}")

    year, month, day = date_text.split("-")
    aliases = [f"/post/{dirname}/"]

    # ディレクトリ名は "YYYY-MM-DD-<slug>" が基本だが、区切りハイフンを欠く
    # ディレクトリも存在するため、両方から slug を取り出す。
    slug = dirname[11:] if len(dirname) > 11 and dirname[10] == "-" else dirname[10:]
    if slug:
        legacy_slug = slugify(slug)
        aliases.append(f"/{year}/{month}/{day}/{slug}/")
        aliases.append(f"/{year}/{month}/{day}/{legacy_slug}/")
        # 初回 Hugo 移行時は記号を落とした slug で配信していた。
        aliases.append(f"/post/{slugify(dirname)}/")
        # WordPress からのエクスポート時に日付が 1 日前へずれた記事があるため、
        # 翌日分の日付 URL も張る。確度は落ちるので優先度は最後に置く。
        shifted = datetime.date(int(year), int(month), int(day)) + datetime.timedelta(days=1)
        aliases.append(f"/{shifted:%Y/%m/%d}/{slug}/")
        aliases.append(f"/{shifted:%Y/%m/%d}/{legacy_slug}/")

    if date_text in unique_dates:
        aliases.append(f"/{year}/{month}/{day}/")

    return list(dict.fromkeys(aliases))


def render_alias_block(aliases: list[str]) -> list[str]:
    return ["aliases:\n"] + [f"- {alias}\n" for alias in aliases]


def resolve_conflicts(plans: dict[Path, list[str]]) -> dict[Path, list[str]]:
    """複数記事が同じ alias を要求した場合、確度の高い方だけを残す。

    Hugo は alias が重複すると片方を黙って捨てるため、ここで確定させる。
    desired_aliases() は確度の高い順に並べているので、その順位を優先度に使う。
    """
    claims: list[tuple[int, str, str, Path]] = [
        (rank, alias, str(index_path), index_path)
        for index_path, aliases in plans.items()
        for rank, alias in enumerate(aliases)
    ]

    owner: dict[str, Path] = {}
    for _, alias, _, index_path in sorted(claims):
        owner.setdefault(alias, index_path)

    return {path: [a for a in aliases if owner[a] == path] for path, aliases in plans.items()}


def update_front_matter(index_path: Path, aliases: list[str], check_only: bool) -> bool:
    original = index_path.read_text(encoding="utf-8")
    opening, front_matter_lines, body = split_front_matter(original)
    existing_aliases, start, end = extract_aliases(front_matter_lines)

    merged_aliases = list(dict.fromkeys(existing_aliases + aliases))
    alias_block = render_alias_block(merged_aliases)

    if start is None:
        new_front_matter_lines = front_matter_lines + alias_block
    else:
        new_front_matter_lines = front_matter_lines[:start] + alias_block + front_matter_lines[end:]

    updated = opening + "".join(new_front_matter_lines) + f"{FRONT_MATTER_DELIM}\n" + body
    if updated == original:
        return False

    if not check_only:
        index_path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure Hugo aliases exist for migrated blog posts.")
    parser.add_argument("--check", action="store_true", help="exit non-zero when updates would be required")
    args = parser.parse_args()

    post_files = iter_post_files()
    date_counts = Counter(path.parent.name[:10] for path in post_files)
    unique_dates = {date_text for date_text, count in date_counts.items() if count == 1}

    plans = resolve_conflicts({path: desired_aliases(path, unique_dates) for path in post_files})

    changed = 0
    for index_path in post_files:
        if update_front_matter(index_path, plans[index_path], check_only=args.check):
            changed += 1

    if args.check and changed:
        print(f"{changed} files would be updated")
        return 1

    print(f"updated {changed} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
