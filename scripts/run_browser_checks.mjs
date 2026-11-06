// Run against the actual production artifact; do not rebuild with different URLs.
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { availableParallelism } from 'node:os';
import { mkdir, appendFile } from 'node:fs/promises';

await mkdir('reports/browser', { recursive: true });
const port = process.env.BROWSER_TEST_PORT || '8138';
const origin = `http://127.0.0.1:${port}`;
// スイートはそれぞれ別のブラウザを起動し、書き出すファイル名も別なので同時に流せる。
// スクロールや動画の時間を見るスイートがあるため、CPU を取り合わない数に抑える
const jobs = Math.max(1, Number(process.env.BROWSER_CHECK_JOBS) || Math.min(4, availableParallelism()));
const suites = ['new_badges', 'archive_scroll', 'home_scroll', 'home', 'archives', 'search', 'home_media', 'oss'];

const server = spawn('python3', ['-u', '-m', 'http.server', port, '--bind', '127.0.0.1', '--directory', 'public'], { stdio: ['ignore', 'pipe', 'pipe'] });
const stopped = once(server, 'exit');
const ready = new Promise((resolve, reject) => {
  server.stdout.on('data', chunk => { if (chunk.toString().includes('Serving HTTP')) resolve(); });
  server.once('error', reject);
  server.once('exit', code => reject(new Error(`HTTP server exited: ${code}`)));
});
server.stderr.on('data', chunk => { void appendFile('reports/browser/server.log', chunk); });

// 同時に流すと出力が混ざるので、スイートごとに溜めて終わった順にまとめて出す
async function runSuite(suite) {
  const started = Date.now();
  const child = spawn(process.execPath, [`scripts/check_${suite}_browser.mjs`, origin], { stdio: ['ignore', 'pipe', 'pipe'] });
  const output = [];
  for (const stream of [child.stdout, child.stderr]) {
    stream.on('data', chunk => {
      output.push(chunk);
      void appendFile(`reports/browser/${suite}.log`, chunk);
    });
  }
  const timeout = setTimeout(() => child.kill('SIGTERM'), 180_000);
  try {
    const [code, signal] = await once(child, 'exit');
    const seconds = ((Date.now() - started) / 1000).toFixed(1);
    const ok = code === 0;
    process.stdout.write(`::group::${ok ? 'PASS' : 'FAIL'} ${suite} (${seconds}s)\n`);
    process.stdout.write(Buffer.concat(output));
    process.stdout.write('::endgroup::\n');
    return ok ? null : `${suite} browser checks failed (${signal || code})`;
  } finally { clearTimeout(timeout); }
}

try {
  await ready;
  const queue = [...suites];
  const failures = [];
  await Promise.all(Array.from({ length: Math.min(jobs, queue.length) }, async () => {
    for (let suite = queue.shift(); suite; suite = queue.shift()) {
      const failure = await runSuite(suite);
      if (failure) failures.push(failure);
    }
  }));
  if (failures.length) throw new Error(failures.join('\n'));
} finally {
  server.kill('SIGTERM');
  await stopped;
}
