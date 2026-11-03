// Run against the actual production artifact; do not rebuild with different URLs.
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdir, appendFile } from 'node:fs/promises';

await mkdir('reports/browser', { recursive: true });
const port = process.env.BROWSER_TEST_PORT || '8138';
const origin = `http://127.0.0.1:${port}`;
const server = spawn('python3', ['-u', '-m', 'http.server', port, '--bind', '127.0.0.1', '--directory', 'public'], { stdio: ['ignore', 'pipe', 'pipe'] });
const stopped = once(server, 'exit');
const ready = new Promise((resolve, reject) => {
  server.stdout.on('data', chunk => { if (chunk.toString().includes('Serving HTTP')) resolve(); });
  server.once('error', reject);
  server.once('exit', code => reject(new Error(`HTTP server exited: ${code}`)));
});
server.stderr.on('data', chunk => { void appendFile('reports/browser/server.log', chunk); });
try {
  await ready;
  for (const suite of ['home_scroll', 'home', 'archives', 'search', 'home_media', 'oss']) {
    const child = spawn(process.execPath, [`scripts/check_${suite}_browser.mjs`, origin], { stdio: ['ignore', 'pipe', 'pipe'] });
    for (const [stream, output] of [[child.stdout, process.stdout], [child.stderr, process.stderr]]) {
      stream.on('data', chunk => {
        output.write(chunk);
        void appendFile(`reports/browser/${suite}.log`, chunk);
      });
    }
    const timeout = setTimeout(() => child.kill('SIGTERM'), 180_000);
    try {
      const [code, signal] = await once(child, 'exit');
      if (code !== 0) throw new Error(`${suite} browser checks failed (${signal || code})`);
    } finally { clearTimeout(timeout); }
  }
} finally {
  server.kill('SIGTERM');
  await stopped;
}
