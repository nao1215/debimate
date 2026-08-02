#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
WEEKLY_INDEX = REPO_ROOT / "content" / "weekly" / "_index.md"
OUTPUT_PATH = REPO_ROOT / "data" / "generated" / "weekly_latest.toml"
JST = ZoneInfo("Asia/Tokyo")
HEADING_PATTERN = re.compile(r"^###\s+(\d{4})/(\d{2})/(\d{2})週\s*$", re.MULTILINE)


@dataclass(frozen=True)
class WeeklySection:
    title: str
    week_start: dt.date
    fragment: str


def extract_sections(markdown: str) -> list[WeeklySection]:
    sections: list[WeeklySection] = []
    for match in HEADING_PATTERN.finditer(markdown):
        year, month, day = (int(part) for part in match.groups())
        week_start = dt.date(year, month, day)
        title = f"{year:04d}/{month:02d}/{day:02d}週"
        sections.append(
            WeeklySection(
                title=title,
                week_start=week_start,
                fragment=f"{year:04d}{month:02d}{day:02d}週",
            )
        )
    return sections


def select_latest_section(sections: list[WeeklySection], as_of: dt.date) -> WeeklySection | None:
    published = [section for section in sections if section.week_start <= as_of]
    if not published:
        return None
    return max(published, key=lambda section: section.week_start)


def toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_output(section: WeeklySection | None) -> str:
    lines = [
        f"available = {'true' if section is not None else 'false'}",
        f'path = "/weekly/"',
    ]
    if section is None:
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            f"title = {toml_string(section.title)}",
            f'week_start = "{section.week_start.isoformat()}"',
            f"fragment = {toml_string(section.fragment)}",
        ]
    )
    return "\n".join(lines) + "\n"


def current_jst_date() -> dt.date:
    return dt.datetime.now(JST).date()


def write_output(content: str, output_path: Path, check_only: bool) -> bool:
    current = output_path.read_text(encoding="utf-8") if output_path.exists() else None
    if current == content:
        return False

    if not check_only:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate data for the latest published weekly section link on the home page."
    )
    parser.add_argument("--check", action="store_true", help="exit non-zero when the generated file is stale")
    parser.add_argument(
        "--as-of",
        type=dt.date.fromisoformat,
        default=current_jst_date(),
        help="select the latest section whose date is not after this YYYY-MM-DD value",
    )
    args = parser.parse_args()

    sections = extract_sections(WEEKLY_INDEX.read_text(encoding="utf-8"))
    latest = select_latest_section(sections, args.as_of)
    generated = render_output(latest)

    changed = write_output(generated, OUTPUT_PATH, check_only=args.check)
    if args.check and changed:
        print(f"{OUTPUT_PATH.relative_to(REPO_ROOT)} is stale")
        return 1

    if latest is None:
        print("no published weekly section was selected")
    else:
        print(f"selected {latest.title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
