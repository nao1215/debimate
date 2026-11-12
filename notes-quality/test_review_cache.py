"""review_cache.py の回帰テスト: python3 notes-quality/test_review_cache.py"""
import json, subprocess, tempfile
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().with_name('review_cache.py'))
with tempfile.TemporaryDirectory() as t:
    root = Path(t); repo = root / 'repo'; repo.mkdir()
    p = repo / 'content/notes/test/index.md'; p.parent.mkdir(parents=True); p.write_text('Original\n')
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    store = root / 'reviews'

    def run(*args, ok=True):
        r = subprocess.run(['python3', SCRIPT, '--repo', str(repo), '--store', str(store), *args], capture_output=True, text=True)
        assert (r.returncode == 0) == ok, r.stderr
        return r.stdout

    assert json.loads(run('scan'))['counts']['unread'] == 1
    snap = json.loads(run('inspect', 'content/notes/test/index.md'))['manifest']['fingerprint']
    ev = root / 'e.json'
    ev.write_text(json.dumps(dict(judgment='normal', reason='example', body='read', figures='none', code_results='none', sources='none needed', limitations='none')))
    run('record', 'content/notes/test/index.md', '--expected', snap, '--level', 'complete', '--evidence', str(ev))
    assert json.loads(run('scan'))['selection_ready']
    p.write_text('Changed without commit\n')
    assert json.loads(run('scan'))['counts']['changed'] == 1
    diff = run('diff', 'content/notes/test/index.md'); assert '-Original' in diff and '+Changed without commit' in diff
    run('record', 'content/notes/test/index.md', '--expected', snap, '--level', 'complete', '--evidence', str(ev), ok=False)
    p.write_text('Original\n'); assert json.loads(run('scan'))['selection_ready']
    asset = p.parent / 'chart.svg'; asset.write_text('<svg/>'); assert json.loads(run('scan'))['counts']['changed'] == 1
    asset.unlink(); shared = repo / 'assets/css/notes.css'; shared.parent.mkdir(parents=True); shared.write_text('color: red')
    assert json.loads(run('scan'))['counts']['changed'] == 1
    assert 'SHARED RENDERING CHANGE assets/css/notes.css' in run('diff', 'content/notes/test/index.md')
    shared.unlink(); snap = json.loads(run('inspect', 'content/notes/test/index.md'))['manifest']['fingerprint']
    run('record', 'content/notes/test/index.md', '--expected', snap, '--level', 'partial', '--evidence', str(ev))
    assert json.loads(run('scan'))['counts']['incomplete'] == 1
    rec = json.loads((store / 'notes__test.json').read_text()); assert len(rec['history']) == 1
    p.unlink(); assert json.loads(run('scan'))['removed'] == ['content/notes/test/index.md']
print('PASS: initial scan, unchanged reuse, dirty diff, stale fingerprint rejection, asset/shared changes, partial/history, removal')
