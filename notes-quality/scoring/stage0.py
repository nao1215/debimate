"""段階 0: 技術ノートを LLM を使わずに数える。結果は stage0.csv。"""
import csv, glob, json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.environ.get('NQ_OUT', os.getcwd())
notes = sorted(glob.glob(f'{ROOT}/content/notes/*/*/index.md')) + sorted(glob.glob(f'{ROOT}/projects/ml/notes/*/*/index.md'))
_st = f'{ROOT}/.note-review/state.json'
hof = {h['path'] for h in json.load(open(_st))['hall_of_fame']} if os.path.exists(_st) else set()
url_of = {p: ('/ml/' if '/projects/ml/' in p else '/notes/') + '/'.join(p.split('/')[-3:-1]) + '/' for p in notes}
bodies = {p: open(p, encoding='utf-8').read() for p in notes}

def body(raw):
    m = re.match(r'^---\n(.*?)\n---\n', raw, re.S)
    return (m.group(1), raw[m.end():]) if m else ('', raw)

rows = []
for p in notes:
    fm, b = body(bodies[p])
    date = (re.search(r'^date:\s*(\S+)', fm, re.M) or [None, ''])[1]
    title = (re.search(r'^title:\s*"?(.*?)"?\s*$', fm, re.M) or [None, ''])[1]
    figs = re.findall(r'\{\{<\s*figure[^>]*src="([^"]+)"', b)
    figs += re.findall(r'!\[[^\]]*\]\(([^)\s]+)', re.sub(r'```.*?```', '', b, flags=re.S))
    mer = len(re.findall(r'```mermaid', b))
    code = len(re.findall(r'^```(?!mermaid)\w*', b, re.M)) // 2
    # 図を挟まずに続くコードブロック（出力を含む）の最長の連続
    blocks, run, maxrun = re.split(r'(\{\{<\s*figure[^>]*>\}\}|```mermaid.*?```)', b, flags=re.S), 0, 0
    for seg in blocks:
        if seg.startswith('{{') or seg.startswith('```mermaid'):
            run = 0
            continue
        for c in re.findall(r'```(?!mermaid)\w*\n(.*?)```', seg, re.S):
            run += len(c)
            maxrun = max(maxrun, run)
    text = re.sub(r'```.*?```', '', b, flags=re.S)
    chars = len(re.sub(r'\s', '', re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)))
    paras = [x for x in re.split(r'\n\s*\n', text) if x.strip() and not x.lstrip().startswith(('{{', '|', '#', '-', '<', '1.'))]
    long_p = sum(1 for x in paras if len(re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', x).strip()) > 200)
    out_int = set(re.findall(r'\]\((/notes/[^)#]+/|/ml/[^)#]+/|\.\./[^)#]+/)', b))
    ext = len(re.findall(r'\]\(https?://', b))
    me = url_of[p]
    slug, sec = p.split('/')[-2], p.split('/')[-3]
    def links_to(q):
        b2 = bodies[q]
        if me in b2:
            return True
        return q.split('/')[-3] == sec and re.search(r'\]\(\.\./' + re.escape(slug) + r'/', b2) is not None
    inbound = sum(1 for q in notes if q != p and links_to(q))
    has_lab = os.path.isdir(os.path.join(os.path.dirname(p), 'lab'))
    first_img = figs[0].rsplit('.', 1)[-1] if figs else ''
    rel = os.path.relpath(p, ROOT)
    updated = subprocess.run(['git', '-C', ROOT, 'log', '-1', '--format=%cs', '--', rel], capture_output=True, text=True).stdout.strip()
    rows.append(dict(path=rel, section=('ml-' + rel.split('/')[3]) if rel.startswith('projects/') else rel.split('/')[2], date=date, updated=updated, title=title, chars=chars,
                     figures=len(figs), mermaid=mer, code_blocks=code, max_code_run=maxrun,
                     long_paras=long_p, out_links=len(out_int), inbound=inbound, ext_links=ext,
                     lab=int(has_lab), first_img=first_img, hof=int(rel in hof)))
with open(os.path.join(OUT, 'stage0.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
print(len(rows))
