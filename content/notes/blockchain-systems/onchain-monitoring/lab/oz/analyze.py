"""runs/<ver>/<scen>/ の生データから output/<ver>/results.json と summary.txt を作る。

実行: python3 analyze.py v170   （または main）
数値はすべて timeline.jsonl・sink.jsonl・monitor.log・run.json から数える。作らない。
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

OZ = Path(__file__).resolve().parent
ANSI = re.compile(r'\x1b\[[0-9;]*m')
PATTERNS = {
    'missed_blocks': r'Missed \d+ blocks',
    'skipped_blocks': r'skipped \d+ blocks',
    'filter_failed_hold': r'Filtering block \d+ failed \(hold',
    'filter_failed_skip': r'failed after \d+ holds in a row',
    'filter_failed_saved_missed': r'saving it as missed for recovery',
    'batch_failed': r'Failed to process block batch',
    'jsonrpc_error': r'JSON-RPC error from',
    'notification_failed': r'(?i)(failed to (send|execute) (notification|trigger)|notification failed|Failed to send webhook|webhook.*fail)',
    'recovery': r'(?i)recover',
    'error_lines': r' ERROR ',
    'warn_lines': r' WARN ',
}


# 観測に対する説明（ソースで確かめた箇所）。v170 = monitor-src/oz-v170, main = monitor-src/openzeppelin-monitor
NOTES = {
    'S0': '欠けなし。全件 1 回ずつ。通知の遅れは cron（*/10 秒）待ち。',
    'S1a_full': 'faultproxy の既定どおり eth_getBlockByNumber(15) も失敗。EVM の get_blocks は 1 つでも失敗すると範囲全体が Err（clients/evm/client.rs get_blocks の try_collect）で、tick は「Failed to process block batch」でチェックポイントを進めない。次の tick の開始は max(last+1, 確定-max_past_blocks) なので、既定 12 ブロックの窓を外れた分は INFO の「skipped N blocks」だけで飛ばされる（service.rs process_new_blocks）。恒久の失敗でも止まらず、失敗ブロックを含む塊ごと消える。消える量は失敗ブロックが塊のどこにあるか（tick の区切り）で 6〜16 件と変わった。main の #544 はフィルタ段の失敗だけが対象で、この経路は v170 と同じ。',
    'S1b_full': '20 秒で直っても、直る前に次の tick の窓が量 15 を過ぎていたため消えた（skipped 6 blocks）。',
    'S1a_logs': 'eth_getLogs だけ失敗。v170: filter_block の Err を process_block が result.ok() で捨て（bootstrap/mod.rs process_block）、一致なしとして checkpoint が進む。ログは転送層の WARN と「Error occurred, JSON-RPC error」の ERROR 1 行だけで、どのブロックの通知を落としたかは出ない。lag は 0 のまま。main: 3 tick 保留（WARN hold 1..3 of 3、lag が 1→10→20 と見える）後、ERROR「skipping it, so its matches are lost」で飛ばす（service.rs dispatch_processed_block, MAX_FILTER_FAILURE_HOLDS=3）。',
    'S1b_logs': 'v170: 黙って消える（a と同じ）。main: 保留中に直り、次の tick で量 15 が届いた（遅れて、順番どおり）。',
    'S1a_logs_rec': 'recovery 有効（*/5 秒, max_retries 3）。v170 はフィルタ段の失敗を missed に保存しない（missed は取得段の Dense の穴か Sparse の failed_blocks だけ）ので recovery は何もしない。main は missed に保存→recovery が 3 回失敗→status Failed で以後試さない。',
    'S1b_logs_rec': 'main: recovery を有効にすると保留（3 tick 待つ）の代わりに missed へ回る。*/5 秒×3 回の再試行が 20 秒の障害の内に尽き（最後の試行は障害が直る 10ms 前）、Failed で確定して消えた。recovery 無しの S1b_logs では届いていたので、有効にした方が消えた。',
    'S1b_logs_rec15': 'recovery の cron を */15 秒にすると、2 回目の試行（障害の後）で取り戻した。量 15 は他より 25 秒ほど遅れ、順番も後ろに届く。v170 は recovery の対象にならず消える。',
    'S2_term_default': '停止中の 60 件のうち再起動直後の窓（max_past_blocks 既定 12）に入らない 56 件が INFO「skipped 56 blocks」だけで消えた。SIGTERM は約 1 秒で終了コード 0。',
    'S2_kill_default': 'kill -9 でも SIGTERM と同じ（通知の直後で tick の合間に止めたため、処理途中の殺しは試せていない）。二重なし。',
    'S2_term_unlimited': 'max_past_blocks = "unlimited" で停止中の分も全部届いた。二重なし。',
    'S2_kill_unlimited': '再実行では全件。1 回目（S2_kill_unlimited_run1）は量 7（停止の前、通常運転中の block 7）だけが届かず、ログに何も出なかった。eth_getLogs(7) は失敗なしで呼ばれ、sink への要求も来ていない。同条件 S0 を 8 回（debug ログ付き）繰り返しても再現せず、理由は確かめられていない。',
    'S2_kill_unlimited_run1': '量 7 だけ理由不明の欠け（S2_kill_unlimited の注を参照）。',
    'S2_term_default_rec': 'recovery を有効にしても max_past_blocks で飛ばしたブロックは missed に保存されない（skipped は info のみ）ので戻らない。',
    'S3_c1': 'reorg の時点でチェックポイントは 23（=頭 24 - 1）。置き換えた 22,23 は通知済みのまま残り（取り消しなし）、新しい 1022,1023 はチェックポイントより前なので処理されず消えた。未処理だった 24 の位置の 1024 だけ届いた。reorg を示すログは何も出ない。',
    'S3_c5': '確認数 5 > reorg の深さ 3 なので、置き換え前のブロックは未処理。新しい 3 件だけ届き、古い 3 件は通知されない。正しい結果。',
    'S4': 'webhook の再送は既定の retry_policy（max_retries 3）で 1 回目＋3 回の計 4 回を約 1 秒以内に打ち、尽きると ERROR ログで捨てる。60 秒の障害中に通知を試みた分は全部消えた。チェックポイントは通知の成否と無関係に進む（trigger は tokio::spawn で投げっぱなし）。metrics に通知失敗の数は無い。',
    'S5': 'RPC 停止 5 分の間、プロセスは生きたまま。各 tick の eth_blockNumber が 1 回失敗し（rpc_request_errors_total が tick ごとに +1、計 30）、ERROR 2 行/tick。block_checkpoint_lag は保存時しか更新されないので 0 のまま凍った。回復後は max_past_blocks 既定の窓の外 295 件を INFO「skipped」だけで飛ばした。health の口は無い（/health は 404）。',
    'S5_unlimited': '"unlimited" なら回復後に停止中の 300 件も全部届いた（MAX_BATCHES_PER_TICK の上限内）。lag はやはり 0 のまま。',
    '_artifact_startup_S1a_full': '起動手順の不具合の証拠（集計から外す）。チェックポイント 1 を置いて頭 1・確定 0 のときに tick が走ると、last(1) >= confirmed(0) の分岐で checkpoint に confirmed=0 を保存し、次の tick が初回扱い（last==0）で最新の確定ブロックから始め、2..8 を飛ばした（service.rs process_new_blocks の else 分岐、main も同じ形）。RPC が一時的に低い頭を返すとチェックポイントが戻りうることを示すが、それ自体はシナリオ外で未検証。',
}
for i in range(1, 5):
    NOTES[f'S0_r{i}'] = 'S0 の繰り返し（debug ログ）。欠けなし。'


def jl(p):
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def log_summary(text):
    lines = [ANSI.sub('', l) for l in text.splitlines()]
    out = {}
    for k, pat in PATTERNS.items():
        hits = [l for l in lines if re.search(pat, l)]
        out[k] = {'count': len(hits), 'examples': [h[:400] for h in hits[:3]] + ([hits[-1][:400]] if len(hits) > 3 else [])}
    return out


def ranges(xs):
    xs = sorted(xs)
    out, start, prev = [], None, None
    for x in xs:
        if start is None:
            start = prev = x
        elif x == prev + 1:
            prev = x
        else:
            out.append([start, prev])
            start = prev = x
    if start is not None:
        out.append([start, prev])
    return out


def analyze(rd):
    run = json.loads((rd / 'run.json').read_text())
    tl = jl(rd / 'timeline.jsonl')
    sink = jl(rd / 'sink.jsonl')
    t0 = next(e['t'] for e in tl if e['ev'] == 'run_start')
    mined_t = {}
    for e in tl:
        if e['ev'] == 'mined' and e.get('amount') is not None:
            mined_t[e['amount']] = e['t']
    for e in tl:
        if e['ev'] == 'reorg':
            for a in e['new_amounts']:
                mined_t[a] = e['t']
    attempts = defaultdict(list)
    for r in sink:
        if 'control' in r:
            continue
        body = r['body'].get('body', '') if isinstance(r['body'], dict) else str(r['body'])
        m = re.search(r'amount=(\d+)', body)
        a = int(m.group(1)) if m else None
        attempts[a].append({'t': round(r['t'] - t0, 3), 'status': r['status']})
    expected = run['canonical']
    delivered = []
    for a, at in sorted(attempts.items(), key=lambda kv: (kv[0] is None, kv[0])):
        ok = [x for x in at if x['status'] == 200]
        delivered.append({'amount': a, 'count': len(ok), 'attempts': len(at),
                          'first_ok_t': ok[0]['t'] if ok else None,
                          'emitted_t': round(mined_t[a] - t0, 3) if a in mined_t else None,
                          'latency_s': round(ok[0]['t'] - (mined_t[a] - t0), 3) if ok and a in mined_t else None,
                          'statuses': [x['status'] for x in at]})
    ok_count = {d['amount']: d['count'] for d in delivered}
    missing = [a for a in expected if ok_count.get(a, 0) == 0]
    duplicated = [{'amount': a, 'count': c} for a, c in ok_count.items() if c > 1]
    stale = [a for a, c in ok_count.items() if c > 0 and a not in expected]
    # チェックポイントの変化と metrics の時系列
    cp, last = [], object()
    for e in tl:
        if e['ev'] == 'sample' and e['checkpoint'] != last:
            cp.append({'t': round(e['t'] - t0, 3), 'checkpoint': e['checkpoint'], 'head': e['head'], 'alive': e['alive']})
            last = e['checkpoint']
    metrics = [{'t': round(e['t'] - t0, 3), 'alive': e['alive'], **e['values']} for e in tl if e['ev'] == 'metrics']
    alive_changes, la = [], None
    for e in tl:
        if e['ev'] == 'sample' and e['alive'] != la:
            alive_changes.append({'t': round(e['t'] - t0, 3), 'alive': e['alive'], 'exit': e.get('exit')})
            la = e['alive']
    events = [{'t': round(e['t'] - t0, 3), **{k: v for k, v in e.items() if k not in ('t',)}}
              for e in tl if e['ev'] not in ('sample', 'metrics', 'mined')]
    logs = log_summary((rd / 'monitor.log').read_text(errors='replace'))
    return {
        'ver': run['ver'], 'scen': run['scen'], 'run': rd.name, 'opts': run['opts'], 'versions': run['versions'],
        'expected': expected, 'expected_count': len(expected),
        'delivered': delivered, 'delivered_ok_distinct': sum(1 for a in expected if ok_count.get(a, 0) > 0),
        'missing': missing, 'missing_ranges': ranges(missing), 'duplicated': duplicated,
        'stale_delivered_not_canonical': stale, 'retractions': [],
        'monitor_alive_at_end': run['monitor_alive_at_end'], 'health_probe': run['health_probe'],
        'alive_changes': alive_changes, 'checkpoint_timeline': cp, 'metrics_timeline': metrics,
        'control_events': events, 'log': logs,
        'notes': NOTES.get(rd.name, ''),
        'mined_times': {str(a): round(t - t0, 3) for a, t in sorted(mined_t.items())},
    }


def line(r):
    lg = r['log']
    keys = [k for k in PATTERNS if lg[k]['count'] and k not in ('error_lines', 'warn_lines')]
    lags = [m.get('block_checkpoint_lag{network="anvil_local"}') for m in r['metrics_timeline']]
    lags = [x for x in lags if x is not None]
    s = [f"== {r['run']} opts={json.dumps(r['opts'], ensure_ascii=False)}",
         f"  expected {r['expected_count']} / delivered(distinct) {r['delivered_ok_distinct']} / missing {len(r['missing'])} {r['missing_ranges']}",
         f"  duplicated {r['duplicated']} / stale(not canonical) {r['stale_delivered_not_canonical']} / retractions none",
         f"  alive_at_end {r['monitor_alive_at_end']} alive_changes {r['alive_changes']}",
         f"  log ERROR {lg['error_lines']['count']} WARN {lg['warn_lines']['count']} hits {', '.join(f'{k}={lg[k]['count']}' for k in keys)}",
         f"  checkpoint_lag metric samples {lags[:40]}{' ...' if len(lags) > 40 else ''}",
         f"  final checkpoint {r['checkpoint_timeline'][-1] if r['checkpoint_timeline'] else None}"]
    for k in keys:
        for ex in lg[k]['examples'][:2]:
            s.append(f"    [{k}] {ex[:300]}")
    ev = [e for e in r['control_events'] if e['ev'] not in ('run_start', 'checkpoint_seeded', 'deployed')]
    for e in ev:
        d = {k: v for k, v in e.items() if k not in ('canonical', 'old_hashes', 'new_hashes')}
        s.append(f"    @{e['t']}s {json.dumps(d, ensure_ascii=False)[:300]}")
    s.append(f"  notes: {r['notes']}")
    return '\n'.join(s)


if __name__ == '__main__':
    ver = sys.argv[1]
    out = OZ / 'output' / ver
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    for rd in sorted((OZ / 'runs' / ver).iterdir()):
        if (rd / 'run.json').exists():
            results[rd.name] = analyze(rd)
    (out / 'results.json').write_text(json.dumps(results, indent=1, ensure_ascii=False))
    (out / 'summary.txt').write_text('\n\n'.join(line(r) for r in results.values()) + '\n')
    print((out / 'summary.txt').read_text())
