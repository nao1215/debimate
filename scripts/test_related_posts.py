"""Exercise the real Hugo templates against an independent ranking oracle."""
import datetime
import json
import os
from pathlib import Path
import random
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
HUGO = shlex.split(os.environ.get("HUGO", "hugo"))


class RelatedPostsTest(unittest.TestCase):
    def test_ranking_ties_duplicates_case_and_unrelated_growth(self):
        rng = random.Random(42)
        records = {}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            partials = root / "layouts/partials"
            partials.mkdir(parents=True)
            for name in ["related_posts.html", "related_posts_index.html",
                         "home_note_card.html", "home_post_card.html"]:
                shutil.copyfile(ROOT / "layouts/partials" / name, partials / name)
            for name in ["post_meta.html", "cover.html", "new_badge.html", "notes/card_cover.html"]:
                stub = partials / name
                stub.parent.mkdir(parents=True, exist_ok=True)
                stub.write_text("")
            (root / "hugo.toml").write_text('''baseURL = "https://example.test/"
disableKinds = ["taxonomy", "term", "RSS", "sitemap"]
[params.relatedPosts]
enabled = true
count = 4
''')
            # Emit the source order too: fully tied candidates retain Hugo's page order.
            (root / "layouts/index.html").write_text('''
{{ $rows := slice }}
{{ range site.RegularPages }}
  {{ if ne .Section "unrelated" }}
    {{ $rows = $rows | append (dict "url" .RelPermalink "html" (partial "related_posts.html" .)) }}
  {{ end }}
{{ end }}
{{ $rows | jsonify | safeHTML }}
''')
            for i in range(36):
                section = ["post", "notes", "isolated"][i % 3]
                # Small date range deliberately creates ties and equal date distances.
                meta = {"title": f"Page {i:02}", "date": f"2020-01-{1 + i % 3:02}",
                        "build": {"render": "link"}}
                if i % 4:
                    meta.update({field: rng.choices(["Go", "go", "CLI", "日本語"], k=i % 3 + 1)
                                 for field in ["tags", "series", "categories"]})
                path = root / "content" / section / f"p{i}.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(meta) + "\nBody")
                records[f"/{section}/p{i}/"] = {**meta, "section": section}

            def build():
                result = subprocess.run(HUGO + ["--source", str(root)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return json.loads((root / "public/index.html").read_text())

            rows = build()
            self.assertEqual(len(rows), len(records))
            order = [row["url"] for row in rows]
            for row in rows:
                current = records[row["url"]]
                ranked = []
                for url in order:
                    other = records[url]
                    if url == row["url"]:
                        continue
                    score = 3 * (current["section"] == other["section"])
                    for field, weight in [("series", 100), ("tags", 20), ("categories", 8)]:
                        score += weight * len(set(current.get(field, [])) & set(other.get(field, [])))
                    if score:
                        gap = abs((datetime.date.fromisoformat(current["date"]) -
                                   datetime.date.fromisoformat(other["date"])).days)
                        ranked.append((url, score, gap))
                ranked.sort(key=lambda item: (-item[1], item[2]))
                actual = [urlparse(url).path for url in re.findall(r'href="([^"]+)"', row["html"])]
                self.assertEqual(actual, [item[0] for item in ranked[:4]], row["url"])

            # Adding unrelated content must not change any recommendations.
            extra = root / "content/unrelated"
            extra.mkdir()
            for i in range(100):
                (extra / f"p{i}.md").write_text(json.dumps({"title": f"Extra {i}",
                    "date": "2021-01-01", "build": {"render": "link"}}))
            self.assertEqual(build(), rows)


if __name__ == "__main__":
    unittest.main()
