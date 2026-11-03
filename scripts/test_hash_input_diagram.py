"""Regression: diagram CSS must survive Hugo watch rebuilds.

Run: python3 -m unittest scripts.test_hash_input_diagram
"""
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('hugo'), 'hugo is required')
class DiagramStylesTest(unittest.TestCase):
    def test_styles_survive_template_and_content_rebuilds(self):
        with tempfile.TemporaryDirectory(prefix='hash-input-test-') as directory:
            root = Path(directory)
            for name in ('layouts/shortcodes/hash-input-comparison.html',
                         'layouts/shortcodes/note-panels.html',
                         'layouts/shortcodes/note-steps.html',
                         'layouts/partials/extend_head.html',
                         'assets/css/pages/note-diagrams.css',
                         'assets/css/pages/hash-input-comparison.css'):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(REPO / name, target)
            (root / 'hugo.toml').write_text("baseURL = 'http://localhost/'\n")
            layout = root / 'layouts/_default/single.html'
            layout.parent.mkdir(parents=True)
            layout.write_text('<html><head>{{ partial "extend_head.html" . }}</head><body>{{ .Content }}</body></html>')
            content = root / 'content'
            content.mkdir()
            header = '---\ntitle: Test\ndisableAdsense: true\n---\n'
            article = content / 'diagram.md'
            article.write_text(header + '{{< hash-input-comparison >}}\n{{< hash-input-comparison prefix="true" >}}\n'
                              '{{< note-panels caption="Compare" >}}\n- title: A\n  items: [one, two]\n'
                              '- title: B\n  steps: [first, second]\n{{< /note-panels >}}\n'
                              '{{< note-steps caption="Process" >}}\n- title: Start\n  body: Input\n'
                              '- title: Finish\n  body: Output\n{{< /note-steps >}}')
            (content / 'plain.md').write_text(header + 'No diagram.')
            output = root / 'public/diagram/index.html'
            with (root / 'build.log').open('w+') as log:
                process = subprocess.Popen(['hugo', '--source', str(root), '--watch',
                                            '--disableKinds', 'taxonomy,term,RSS,sitemap'], stdout=log, stderr=log)
                try:
                    def wait_for(marker):
                        deadline = time.monotonic() + 15
                        while time.monotonic() < deadline:
                            if output.exists() and marker in output.read_text():
                                return output.read_text()
                            if process.poll() is not None:
                                break
                            time.sleep(.1)
                        log.seek(0)
                        self.fail('Hugo did not rebuild: ' + log.read())

                    def check_styles(html):
                        links = re.findall(r'href="([^"]*hash-input-comparison[^\"]*\.css)"', html)
                        self.assertEqual(len(links), 1)
                        css = root / 'public' / links[0].lstrip('/')
                        self.assertIn('display:grid', css.read_text())
                        self.assertEqual(html.count('<figure class="hash-input"'), 2)
                        links = re.findall(r'href="([^"]*note-diagrams[^\"]*\.css)"', html)
                        self.assertEqual(len(links), 1)
                        self.assertIn('display:grid', (root / 'public' / links[0].lstrip('/')).read_text())
                        self.assertEqual(html.count('<figure class="note-diagram"'), 2)
                        self.assertIn('<li>one</li>', html)

                    check_styles(wait_for('hash-input__chain'))
                    shortcode = root / 'layouts/shortcodes/hash-input-comparison.html'
                    shortcode.write_text(shortcode.read_text() + '\n<span hidden>template-rebuilt</span>')
                    check_styles(wait_for('template-rebuilt'))
                    shortcode = root / 'layouts/shortcodes/note-panels.html'
                    shortcode.write_text(shortcode.read_text() + '\n<span hidden>panels-rebuilt</span>')
                    check_styles(wait_for('panels-rebuilt'))
                    shortcode = root / 'layouts/shortcodes/note-steps.html'
                    shortcode.write_text(shortcode.read_text() + '\n<span hidden>steps-rebuilt</span>')
                    check_styles(wait_for('steps-rebuilt'))
                    article.write_text(article.read_text() + '\n\nContent rebuilt.\n')
                    check_styles(wait_for('Content rebuilt.'))
                    self.assertNotIn('hash-input-comparison', (root / 'public/plain/index.html').read_text())
                    self.assertNotIn('note-diagrams', (root / 'public/plain/index.html').read_text())
                finally:
                    process.terminate()
                    process.wait(timeout=5)
