#!/usr/bin/env python3
"""Check spacing between Japanese prose and ASCII technical terms.

Markdown syntax, front matter, URLs, inline code, and fenced code blocks are
excluded.  The convention is defined in the technical-note writing guide:
Japanese prose and adjacent ASCII words/numbers have a separating space.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


JAPANESE = r"[ぁ-んァ-ヶ一-龯々〆〤]"
ASCII = r"[A-Za-z0-9]"
DIRECT = re.compile(rf"{JAPANESE}{ASCII}|{ASCII}{JAPANESE}")
LINK_BEFORE = re.compile(rf"{JAPANESE}\[{ASCII}")
LINK_AFTER = re.compile(rf"\[[^\]]*{ASCII}\]\([^)]*\){JAPANESE}")


def prose_lines(path: Path) -> list[tuple[int, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    result: list[tuple[int, str]] = []
    front_matter = bool(lines and lines[0] == "---")
    fenced = False

    for number, line in enumerate(lines, 1):
        if front_matter:
            if number != 1 and line == "---":
                front_matter = False
            continue
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
            continue
        if fenced:
            continue
        # Quotations keep the original spacing of the quoted text.
        if re.match(r"^\s*>", line):
            continue

        # Keep link labels, but remove link targets, bare URLs, inline code,
        # and HTML tags so syntax and addresses are never checked as prose.
        text = re.sub(r"\]\([^)]*\)", "]()", line)
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"`[^`]*`", "", text)
        text = re.sub(r"<[^>]*>", " ", text)
        result.append((number, text))
    return result


def problems(path: Path) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for number, line in prose_lines(path):
        if DIRECT.search(line) or LINK_BEFORE.search(line) or LINK_AFTER.search(line):
            found.append((number, line))
    return found


def markdown_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            # Section indexes include legacy article and book titles.  They are
            # catalog data rather than reader-facing note prose, so check only
            # Page Bundle bodies here.
            files.extend(sorted(path.rglob("index.md")))
        elif path.suffix == ".md":
            files.append(path)
        else:
            raise SystemExit(f"not a Markdown file or directory: {path}")
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        default=["content/notes", "projects/ml/notes"],
        help="Markdown files or directories (default: all technical notes)",
    )
    args = parser.parse_args()

    failed = False
    for path in markdown_files(args.paths):
        issues = problems(path)
        if not issues:
            continue
        failed = True
        print(f"{path}:")
        for number, line in issues:
            print(f"  {number}: {line}")
    if failed:
        print("Add a space between Japanese prose and adjacent ASCII words or numbers.")
        return 1
    print("note spacing: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
