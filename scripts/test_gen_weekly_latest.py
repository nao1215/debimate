from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path

from scripts.gen_weekly_latest import (
    WeeklySection,
    extract_sections,
    render_output,
    select_latest_section,
    write_output,
)


class ExtractSectionsTest(unittest.TestCase):
    def test_extract_sections_reads_weekly_headings(self) -> None:
        markdown = """
## 2026

### 2026/07/27週
text

### 2026/08/03週
text
"""

        sections = extract_sections(markdown)

        self.assertEqual(
            sections,
            [
                WeeklySection("2026/07/27週", dt.date(2026, 7, 27), "20260727週"),
                WeeklySection("2026/08/03週", dt.date(2026, 8, 3), "20260803週"),
            ],
        )


class SelectLatestSectionTest(unittest.TestCase):
    def test_future_headings_are_ignored(self) -> None:
        sections = [
            WeeklySection("2026/07/27週", dt.date(2026, 7, 27), "20260727週"),
            WeeklySection("2026/08/03週", dt.date(2026, 8, 3), "20260803週"),
            WeeklySection("2026/08/10週", dt.date(2026, 8, 10), "20260810週"),
        ]

        latest = select_latest_section(sections, dt.date(2026, 8, 2))

        self.assertEqual(latest, sections[0])

    def test_monday_switches_to_that_week(self) -> None:
        sections = [
            WeeklySection("2026/07/27週", dt.date(2026, 7, 27), "20260727週"),
            WeeklySection("2026/08/03週", dt.date(2026, 8, 3), "20260803週"),
        ]

        latest = select_latest_section(sections, dt.date(2026, 8, 3))

        self.assertEqual(latest, sections[1])

    def test_returns_none_when_every_heading_is_in_the_future(self) -> None:
        sections = [WeeklySection("2026/08/03週", dt.date(2026, 8, 3), "20260803週")]

        latest = select_latest_section(sections, dt.date(2026, 8, 2))

        self.assertIsNone(latest)


class RenderOutputTest(unittest.TestCase):
    def test_render_output_for_selected_section(self) -> None:
        rendered = render_output(WeeklySection("2026/07/27週", dt.date(2026, 7, 27), "20260727週"))

        self.assertEqual(
            rendered,
            'available = true\n'
            'path = "/weekly/"\n'
            'title = "2026/07/27週"\n'
            'week_start = "2026-07-27"\n'
            'fragment = "20260727週"\n',
        )

    def test_render_output_without_published_section(self) -> None:
        rendered = render_output(None)

        self.assertEqual(
            rendered,
            'available = false\n'
            'path = "/weekly/"\n',
        )


class WriteOutputTest(unittest.TestCase):
    def test_write_output_detects_stale_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "weekly_latest.toml"

            self.assertTrue(write_output("a\n", output_path, check_only=False))
            self.assertFalse(write_output("a\n", output_path, check_only=False))
            self.assertTrue(write_output("b\n", output_path, check_only=True))


if __name__ == "__main__":
    unittest.main()
