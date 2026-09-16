"""Migration checks must preserve old URLs without inventing new ones."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_weeknotes
import ensure_post_aliases


class PostAliasesTest(unittest.TestCase):
    def test_new_post_does_not_require_aliases_or_change_existing_date_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "2020-01-01-old/index.md"
            legacy.parent.mkdir()
            legacy.write_text("---\ntitle: Old\n---\nBody\n")
            manifest = root / "legacy_urls.json"
            manifest.write_text(json.dumps({"posts": [legacy.parent.name]}))
            with patch.object(ensure_post_aliases, "POST_ROOT", root), patch.object(
                ensure_post_aliases, "LEGACY_URLS", manifest
            ), contextlib.redirect_stdout(io.StringIO()):
                with patch("sys.argv", ["ensure_post_aliases"]):
                    self.assertEqual(ensure_post_aliases.main(), 0)
                original = legacy.read_text()
                self.assertIn("- /2020/01/01/\n", original)
                # Backdated new posts must also be excluded, even on the same day.
                new = root / "2020-01-01-new/index.md"
                new.parent.mkdir()
                new.write_text("---\ntitle: New\n---\nBody\n")
                with patch("sys.argv", ["ensure_post_aliases", "--check"]):
                    self.assertEqual(ensure_post_aliases.main(), 0)
                with patch("sys.argv", ["ensure_post_aliases"]):
                    self.assertEqual(ensure_post_aliases.main(), 0)
                self.assertEqual(legacy.read_text(), original)
                self.assertNotIn("aliases:", new.read_text())
                legacy.write_text(original.replace("- /2020/01/01/\n", ""))
                with patch("sys.argv", ["ensure_post_aliases", "--check"]):
                    self.assertEqual(ensure_post_aliases.main(), 1)
                legacy.unlink()
                with self.assertRaises(FileNotFoundError):
                    ensure_post_aliases.iter_post_files()


class WeeknotesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "public"
        self.content = Path(self.temp.name) / "content"
        self.old_date = "2026-09-07"
        self.new_date = "2026-09-21"
        for date in [self.old_date, self.new_date]:
            self.write(self.root / f"weeknotes/{date}/index.html", "<html></html>")
            self.write(self.content / f"2026/{date[5:]}/index.md", "---\ntitle: Week\n---\n")
            self.write(self.content / f"2026/{date[5:]}/image.webp", "image")
        for source, target in [("", ""), ("page/1/", ""), (f"{self.old_date}/", f"{self.old_date}/")]:
            url = f"https://debimate.jp/weeknotes/{target}"
            self.write(self.root / f"weekly/{source}index.html", (
                f'<link rel="canonical" href="{url}">'
                f'<meta http-equiv="refresh" content="0; url={url}">'
                '<script>window.location.replace(target + window.location.search + window.location.hash)</script>'
            ))
        self.write(self.root / f"weekly/{self.old_date}/image.webp", "image")
        self.write(self.root / "sitemap.xml", "<urlset/>")
        for section in ["weekly", "weeknotes"]:
            items = []
            for date in [self.new_date, self.old_date]:
                link = f"https://debimate.jp/weeknotes/{date}/"
                guid = link.replace("/weeknotes/", "/weekly/") if section == "weekly" and date == self.old_date else link
                items.append(f"<item><link>{link}</link><guid>{guid}</guid></item>")
            self.write(self.root / f"{section}/index.xml", "<rss><channel>" + "".join(items) + "</channel></rss>")

    @staticmethod
    def write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def check(self):
        with contextlib.redirect_stdout(io.StringIO()):
            check_weeknotes.check(self.root, self.content, [self.old_date])

    def test_new_weeknote_needs_no_legacy_redirect_or_image(self):
        self.check()
        self.assertFalse((self.root / f"weekly/{self.new_date}").exists())

    def test_missing_legacy_redirect_fails(self):
        (self.root / f"weekly/{self.old_date}/index.html").unlink()
        with self.assertRaises(FileNotFoundError):
            self.check()

    def test_missing_migrated_page_fails(self):
        (self.root / f"weeknotes/{self.old_date}/index.html").unlink()
        with self.assertRaises(AssertionError):
            self.check()

    def test_changed_legacy_image_fails(self):
        (self.root / f"weekly/{self.old_date}/image.webp").write_text("different")
        with self.assertRaises(AssertionError):
            self.check()

    def test_new_feed_item_must_use_current_guid(self):
        feed = self.root / "weekly/index.xml"
        link = f"https://debimate.jp/weeknotes/{self.new_date}/"
        feed.write_text(feed.read_text().replace(f"<guid>{link}</guid>", f'<guid>{link.replace("/weeknotes/", "/weekly/")}</guid>'))
        with self.assertRaises(AssertionError):
            self.check()


if __name__ == "__main__":
    unittest.main()
