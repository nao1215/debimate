# Taxonomy Guidelines

As of July 19, 2026, this site has 169 tags and the following normalized categories:

- `プログラミング`
- `インフラ`
- `OSS`
- `キャリア`
- `ブログ運営`
- `生活`
- `書評`
- `音楽`
- `ロシア`
- `エンタメ`

## Category rules

- Use `categories` for the article's reader-facing entry point.
- Use `tags` for specific technologies, products, and concepts.
- Use `series` for continuous collections such as `機械学習ノート`.

### Category assignment

- `プログラミング`
  Code, language features, algorithms, APIs, testing, code reading, and library design.
- `インフラ`
  OS setup, Debian/Ubuntu, Raspberry Pi, Docker, Kubernetes, servers, terminals, and environment setup.
- `OSS`
  Articles about publishing, maintaining, contributing to, or announcing open-source software.
- `キャリア`
  Work style, management, job changes, reflections, and professional growth.
- `ブログ運営`
  Analytics, AdSense, migration, PV, monetization, and blog operations.
- `生活`
  Daily life, language learning, travel, family, and personal topics not better represented by another category.
- `書評`
  Book reviews and reading notes.
- `音楽`
  Music reviews and listening logs.
- `ロシア`
  Russia-related cultural, travel, and language topics.
- `エンタメ`
  Games, films, and adjacent entertainment topics.

## Tag rules

- Prefer one canonical tag per concept.
- Keep English tags lowercase.
- Remove tags that simply restate the category.
- Avoid broad format tags such as `review`.

## Rules already applied

- Merged aliases:
  - `go言語` -> `golang`
  - `shell` -> `shellscript`
  - `レビュー` -> `review`
- Removed broad category-duplicate tags:
  - `linux`
  - `体験談`
  - `書籍`
  - `hrhm`
  - `russia`
- Removed the generic format tag `review`.

## Audit command

Run the following from the repository root:

```bash
python3 scripts/tag_audit.py
```

This prints counts for tags, categories, and series so future cleanup can stay rule-based instead of ad hoc.
