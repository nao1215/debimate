"""段階 1 用の抜き出しを作る: python3 extract.py <slug-path>... -> extracts/<section>__<slug>.md"""
import csv, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.environ.get('NQ_OUT', os.getcwd())
stage0 = {r['path']: r for r in csv.DictReader(open(os.path.join(OUT, 'stage0.csv')))}
os.makedirs(os.path.join(OUT, 'extracts'), exist_ok=True)

def strip(s):
    s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)
    return s.strip()

for slug in sys.argv[1:]:
    rel = f'content/notes/{slug}/index.md'
    if not os.path.exists(os.path.join(ROOT, rel)):
        rel = f'projects/ml/notes/{slug}/index.md'
    src = os.environ.get('SRC')
    raw = open(src or os.path.join(ROOT, rel), encoding='utf-8').read()
    m = re.match(r'^---\n(.*?)\n---\n', raw, re.S)
    fm, body = m.group(1), raw[m.end():]
    title = re.search(r'^title:\s*"?(.*?)"?\s*$', fm, re.M).group(1)
    nocode = re.sub(r'```.*?```', '[コード]', body, flags=re.S)
    nocode = re.sub(r'!\[([^\]]*)\]\([^)]+\)', lambda m: '{{< figure caption="' + m.group(1).replace('"', '') + '" >}}', nocode)
    parts = re.split(r'\n---\n', nocode, maxsplit=1)
    intro = parts[0].strip()
    intro = re.sub(r'\{\{<\s*figure[^>]*caption="([^"]*)"[^>]*>\}\}', r'[図: \1]', intro)
    k = intro.rfind('\n本記事では')
    k = k + 1 if k >= 0 else intro.find('本記事では')
    intro_core = intro[:k] if k > 0 else intro
    out = [f'# {title}', f'path: {rel}', '機械で数えた値: ' + ', '.join(f'{k}={v}' for k, v in stage0[rel].items() if k not in ('path', 'title')), '', '## 冒頭', strip(intro_core)[:2600] + ('\n\n（以下「本記事では」の段落）\n' + strip(intro[k:])[:1500] if k > 0 else ''), '', '## 節の並びと最初の 1 文']
    for sec in re.split(r'\n(?=#{3,4} )', nocode)[1:]:
        head, _, rest = sec.partition('\n')
        sent = ''
        for line in rest.split('\n'):
            t = line.strip()
            if not t or t.startswith(('{{', '<', '|', '[コード]', '-', '---')):
                continue
            sent = strip(t)
            sent = sent[:sent.find('。') + 1] if '。' in sent else sent[:140]
            break
        figs = re.findall(r'caption="([^"]*)"', rest)
        refs = len(re.findall(r'\]\(https?://', sec))
        codes = rest.count('[コード]')
        out.append(f'- {head.strip("# ")}: {sent}' + (f' ［図: {" / ".join(figs)}］' if figs else '') + (f' ［コード {codes} 個］' if codes else '') + f' ［{len(re.sub(chr(92)+"s", "", rest))} 字、外部リンク {refs}］')
    secs = re.split(r'\n(?=### )', nocode)
    k = next((i for i, x in enumerate(secs) if x.startswith('### 利点')), None)
    tail = secs[k:] if k is not None else secs[-2:]
    out += ['', '## 結び（利点の節以降、無ければ最後の 2 節）', strip('\n'.join(tail))[:2400]]
    open(f'{OUT}/extracts/{slug.replace("/", "__")}{os.environ.get("SUFFIX", "")}.md', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print(slug, len('\n'.join(out)))
