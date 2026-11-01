#!/usr/bin/env python3
"""Build and audit a page locally with Lighthouse (Node.js and Chrome required)."""
import argparse
import functools
import gzip
import io
import json
import subprocess
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class CompressedHandler(SimpleHTTPRequestHandler):
    """Serve text compressed, as production hosting normally does."""
    def log_message(self, *_args):
        pass

    def send_head(self):
        path = Path(self.translate_path(self.path))
        if path.is_dir():
            path = path / 'index.html'
        if path.is_file() and path.suffix in {'.html', '.css', '.js', '.json', '.svg', '.xml'} and 'gzip' in self.headers.get('Accept-Encoding', ''):
            data = gzip.compress(path.read_bytes(), mtime=0)
            self.send_response(200)
            self.send_header('Content-Type', self.guess_type(str(path)))
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Vary', 'Accept-Encoding')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            return io.BytesIO(data)
        return super().send_head()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-dir', type=Path, help='Existing build; its baseURL must match --port')
    parser.add_argument('--path', default='/', help='Page path, e.g. /post/, /weeknotes/2026/, /games/')
    parser.add_argument('--port', type=int, default=8139)
    parser.add_argument('--output', type=Path, default=Path('reports/lighthouse/home'))
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--lighthouse', help='Installed Lighthouse executable; defaults to npx lighthouse@13.0.3')
    args = parser.parse_args()
    if args.runs < 1:
        parser.error('--runs must be at least 1')
    url = f'http://127.0.0.1:{args.port}/'
    if not args.path.startswith('/') or args.path.startswith('//') or '#' in args.path:
        parser.error('--path must be a local path beginning with / and without a fragment')
    page_url = url.rstrip('/') + args.path
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='debimate-audit-') as temp:
        root = args.site_dir.resolve() if args.site_dir else Path(temp) / 'public'
        if not args.site_dir:
            subprocess.run(['hugo', '--minify', '--destination', str(root), '--baseURL', url], check=True)
        if not (root / 'index.html').is_file():
            parser.error(f'No index.html in {root}')
        server = ThreadingHTTPServer(('127.0.0.1', args.port), functools.partial(CompressedHandler, directory=str(root)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        command = [args.lighthouse] if args.lighthouse else ['npx', '--yes', 'lighthouse@13.0.3']
        results = []
        try:
            for i in range(1, args.runs + 1):
                prefix = f'{output}-{i}'
                subprocess.run([*command, page_url, '--chrome-flags=--headless --no-sandbox', '--output=html', '--output=json', f'--output-path={prefix}', '--quiet'], check=True)
                report = json.loads(Path(f'{prefix}.report.json').read_text())
                result = {'run': i, 'scores': {k: v['score'] * 100 for k, v in report['categories'].items()},
                          'metrics': {k: report['audits'][k].get('numericValue') for k in ['first-contentful-paint', 'largest-contentful-paint', 'total-blocking-time', 'cumulative-layout-shift']}}
                results.append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
        finally:
            server.shutdown()
            server.server_close()
        Path(f'{output}-summary.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
        print(f'Reports: {output}-*.report.html')


if __name__ == '__main__':
    main()
