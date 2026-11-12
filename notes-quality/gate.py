#!/usr/bin/env python3
"""技術ノート（content/notes）と ML ノート（projects/ml/notes）の関門。

    python3 notes-quality/gate.py note <index.md>          # 書き終えた時。全部の規則
    python3 notes-quality/gate.py note --diff <index.md>   # 既存ノートの小さな修正。HEAD から足した行だけ
    python3 notes-quality/gate.py commit                   # pre-commit: staged のノートを規則で見る
    python3 notes-quality/gate.py push <base> <head> [--ng-list <file>]
                                                           # pre-push と CI: 規則に加え、総合 4 以上の点の記録。
                                                           # --ng-list で NG のノートの Page Bundle を書き出す（CI がビルドから外す）
    python3 notes-quality/gate.py score <index.md> --overall 4 --product 36 --baseline 5,5,3,2,2 --by <採点した担当>
                                                           # 別の担当の採点し直しを scores/ に記録する（自己採点は不可）
    python3 notes-quality/gate.py record <index.md>        # 冒頭の型と題の形を opening_log.tsv に足す

全部通れば終了コード 0、NG があれば 1。

2026-11-12 著者の指定。
- 規則と文体の資料はこのディレクトリが基準。スキル（debimate-visual-notes・create-tech-notes）はここを読む。
- push できるのは、変えたノートが scores/<key>.json で総合 4 以上と記録され、その記録が今の版
  （git の blob）か、そこから足した行が SMALL 行以下の版に対するものである時だけ。
- 例外: 既存のノートへの小さな修正（足した行が SMALL 行以下で、足した行が規則を通る）は点の記録が無くても通す。
  逆向きのリンクの 1 文などを足すため。
- `>` で始まる引用の行は語の判定から外す（ブログ記事・weeknotes・外部の文からの引用のため）。
"""
import csv, difflib, glob, json, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import no_chain  # noqa: E402  名詞を「の」で 3 つ以上つなぐ表現（2026-11-12 著者）

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TYPES = ['フラット', '場面', '結果', '誤解', '問い']
NOTE_RE = re.compile(r'(?:content/notes|projects/ml/notes)/([^/]+)/([^/]+)/index\.md$')
SMALL = 5          # 小さな修正とみなす足した行の数
MAJOR_LINES = 40   # これ以上足した改稿は全部の規則で見る
MAJOR_RATIO = 0.3
BASELINE = [5, 5, 3, 2, 2]  # 基準の 5 本（wallet, transaction-scope, quorum, adapter, sidecar）の点
# 点の記録の基準。「4 点」は、関門の質の判定を通った上で別の担当が付けた点だけを指す（2026-11-12 著者
# 「基準 4 が NG になるのはバグでは」）。これより前に付けた点（standard が無い記録）は旧基準として扱う
STANDARD = 'gate-v1'
# 手本の記事（Wallet・Transaction Scope・stdout-buffering・Sidecar）が引っかかる規則は、止めずに注意として出す
# （2026-11-12 著者の指定）。数で決めた上限と書き方の型の規則が対象。著者が禁止と明示した
# 「を、」・太字・「確かめ」などの揺れ・表記の旧形・details と #### の前後の <br> は NG のまま
NOTICE_RX = re.compile('|'.join([
    '折り返す箇条書き', '表のマスが長い', '括弧が多い・長い段落', '型の節が残っている', '文末の括弧でリンクを添えている',
    'WebP でない図', '図の生成元に英語だけのラベル',
    '「版」をバージョンの意味', '英語の引用に日本語訳', '他のノートを「記事」と呼んでいる', '300 字を超える段落',
    '本人が使わない言い回しがある',
]))
NOTICES = []
# Wallet は著者が調整した基準の記事で、触らない（debimate-visual-notes §2）。関門の対象から外す
EXEMPT = {'content/notes/blockchain-systems/wallet/index.md'}


def git(*a, check=False):
    r = subprocess.run(['git', '-C', ROOT, *a], capture_output=True, text=True, errors='replace')
    return r.stdout if (r.returncode == 0 or not check) else None


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, errors='replace', cwd=ROOT)
    return r.returncode, r.stdout + r.stderr


def key_of(rel):
    m = NOTE_RE.search(rel)
    return f'{m.group(1)}__{m.group(2)}' if m else None


def drift_rows():
    p = os.path.join(HERE, 'drift_words.tsv')
    return [r for r in csv.reader(open(p, encoding='utf-8'), delimiter='\t') if r and not r[0].startswith('#')]


def variant_rules():
    """style/variants.tsv から、本人がほぼ使わない形（enforce の組で 5% 未満、組の合計 30 件以上）を返す。"""
    p = os.path.join(HERE, 'style', 'variants.tsv')
    if not os.path.exists(p):
        return []
    rows = [r for r in csv.reader(open(p, encoding='utf-8'), delimiter='\t') if r and not r[0].startswith('#') and r[0] != '組']
    rules = []
    for g in dict.fromkeys(r[0] for r in rows):
        grp = [r for r in rows if r[0] == g and r[1] == 'enforce']
        total = sum(int(r[3]) for r in grp)
        if not grp or total < 30:
            continue
        best = max(grp, key=lambda r: int(r[3]))
        others = '・'.join(r[2] for r in grp if float(r[4]) >= 0.05)
        for r in grp:
            if float(r[4]) < 0.05:
                rules.append((r[2], re.compile(r[5]), f'{others}（本人の実文で {r[2]} {r[3]} 件、{best[2]} {best[3]} 件）'))
    return rules


def added_lines(old_text, new_text):
    out = []
    for l in difflib.unified_diff(old_text.splitlines(), new_text.splitlines(), lineterm='', n=0):
        if l.startswith('+') and not l.startswith('+++'):
            out.append(l[1:])
    return out


REWRITE_SIMILARITY = 0.6  # 置き換えた行の文字の一致がこれ以上なら、書き直しではなく手直しとみなす


def rewritten_lines(old_text, new_text):
    """足した行のうち、中身を書き直した行と新しく足した行だけを返す（2026-11-12 著者の指定）。
    語の置き換えや言い回しの手直しで、元の行と文字の大半が一致する行は数えない。
    行の数だけで大きな改稿を決めると、訳語を揃えただけの直しが書き直しと同じに数えられたため。"""
    a, b = old_text.splitlines(), new_text.splitlines()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'insert':
            out += b[j1:j2]
        elif tag == 'replace':
            olds = a[i1:i2]
            for k, line in enumerate(b[j1:j2]):
                cands = [olds[k]] if len(olds) == j2 - j1 else olds
                best = max((difflib.SequenceMatcher(None, o, line).ratio() for o in cands), default=0)
                if best < REWRITE_SIMILARITY:
                    out.append(line)
    return out


def removed_lines(old_text, new_text):
    out = []
    for l in difflib.unified_diff(old_text.splitlines(), new_text.splitlines(), lineterm='', n=0):
        if l.startswith('-') and not l.startswith('---'):
            out.append(l[1:])
    return out


def _hits(lines):
    """行ごとの規則違反を (規則の名前, 行) で返す。コードと引用は除く。"""
    out, incode = [], False
    for t in lines:
        if t.lstrip().startswith('```'):
            incode = not incode
            continue
        if incode or t.lstrip().startswith('>'):
            continue
        for _ in range(t.count('**') // 2 or ('**' in t)):
            out.append(('太字', t))
        for _ in range(t.count('を、')):
            out.append(('「を、」', t))
        for row in drift_rows():
            for _ in range(t.count(row[0])):
                out.append((f'「{row[0]}」（本人の言い方: {row[2] if len(row) > 2 else ""}）', t))
        for c in no_chain.chains(t):
            out.append((f'名詞を「の」で 3 つ以上つなぐ表現「{c}」', t))
        tt = re.sub(r'`[^`]*`|\]\([^)]*\)|https?://\S+', '', t)
        for form, rx, hint in variant_rules():
            for _ in rx.findall(tt):
                out.append((f'「{form}」（本人の言い方: {hint}）', t))
    return out


def check_added(lines, removed=()):
    """足した行の規則違反のうち、消した行より増えたものだけを NG にする（2026-11-12）。
    同じ行にもともとあった違反は、小さな修正が持ち込んだものではないので数えない。"""
    from collections import Counter
    before = Counter(name for name, _ in _hits(removed))
    after = _hits(lines)
    ng, seen = [], Counter()
    for name, t in after:
        seen[name] += 1
        if seen[name] > before[name]:
            ng.append(f'足した行に{name}: {t[:60]}')
    return ng


def title_of(text):
    fm = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    m = re.search(r'^title:\s*"?(.*?)"?\s*$', fm.group(1), re.M) if fm else None
    return m.group(1) if m else ''


def title_shape(t):
    sub = t.split(' - ', 1)[-1]
    return 'なぜ' if re.search(r'(理由|のか|なぜ)[」）]?$', sub) else 'その他'


def opening_type(key):
    cp = os.path.join(HERE, 'checklists', f'{key}.md')
    if not os.path.exists(cp):
        return None
    for line in open(cp, encoding='utf-8'):
        if line.startswith('|') and '冒頭の型' in line:
            cell = line.strip().strip('|').split('|')[-1]
            for t in TYPES:
                if t in cell:
                    return t
    return None


def opening_hist():
    p = os.path.join(HERE, 'opening_log.tsv')
    return [r for r in csv.reader(open(p, encoding='utf-8'), delimiter='\t') if r and not r[0].startswith('#')] if os.path.exists(p) else []


def check_full(rel, process=True):
    """全部の規則。NG のリストを返す。process=False なら質の規則だけ（手続きの規則を除く）。"""
    if rel in EXEMPT:
        NOTICES.append(f'{rel} は著者が調整した基準の記事なので、関門の対象外')
        return []
    p = os.path.join(ROOT, rel)
    key = key_of(rel)
    text = open(p, encoding='utf-8').read()
    fm = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    body = text[fm.end():] if fm else text
    prose = re.sub(r'```.*?```', '', body, flags=re.S)
    prose = '\n'.join(l for l in prose.splitlines() if not l.lstrip().startswith('>'))
    ng = []

    code, out = run([sys.executable, os.path.join(HERE, 'check_note.py'), p])
    hard = [l.strip() for l in out.splitlines() if l.strip().startswith('NG:') and not NOTICE_RX.search(l)]
    NOTICES.extend(l.strip()[3:].strip() for l in out.splitlines() if l.strip().startswith('NG:') and NOTICE_RX.search(l))
    if hard:
        ng.append('check_note.py が NG:\n    ' + '\n    '.join(hard))
    code, out = run(['bash', os.path.join(HERE, 'style_check.sh'), p])
    lines = out.splitlines()
    hard = []
    for i, l in enumerate(lines):
        if re.search(r'\[(NG|ERROR)\]', l):
            detail = lines[i + 1].strip() if i + 1 < len(lines) and not lines[i + 1].lstrip().startswith('[') else ''
            (NOTICES if NOTICE_RX.search(l) else hard).append((l.strip() + ' ' + detail[:80]).strip())
    if hard:
        ng.append('style_check.sh が NG（bash notes-quality/style_check.sh で詳細）:\n    ' + '\n    '.join(hard)[:1500])
    code, out = run([sys.executable, os.path.join(HERE, 'textruns.py'), p])
    mm = re.search(r'700字以上の文字だけの区間 (\d+) 個 / 200字超の段落 (\d+) 個', out)
    if mm and int(mm.group(1)) > 0:
        ng.append(f'700 字以上の文字だけの区間が {mm.group(1)} 個（0 にする。図か空行で挟んだ <br> で割る）')
    if mm and int(mm.group(2)) > 8:
        ng.append(f'200 字超の段落が {mm.group(2)} 個（基準の Wallet は 5、上限 8）')
    for row in drift_rows():
        word, limit, hint = row[0], int(row[1]), row[2] if len(row) > 2 else ''
        n = prose.count(word)
        if n > limit:
            lines = [str(i + 1) for i, l in enumerate(text.splitlines()) if word in l][:8]
            ng.append(f'「{word}」が {n} 回（上限 {limit}）。本人の言い方: {hint}。行: {", ".join(lines)}')
    plain = re.sub(r'`[^`]*`|\]\([^)]*\)|https?://\S+', '', prose)
    for form, rx, hint in variant_rules():
        n = len(rx.findall(plain))
        if n:
            lines = [str(i + 1) for i, l in enumerate(text.splitlines()) if rx.search(re.sub(r'`[^`]*`|\]\([^)]*\)', '', l))][:8]
            ng.append(f'「{form}」が {n} 回。本人の言い方: {hint}。行: {", ".join(lines)}')
    code, out = run([sys.executable, os.path.join(HERE, 'omokage_check.py'), p])
    if code == 0 and out.strip().splitlines()[-1].strip().isdigit():
        sc = int(out.strip().splitlines()[-1])
        if sc < 85:
            ng.append(f'omokage の一致度が {sc}%（85% 以上。omokage check --explain で崩れた段落を見る）')
    ng += check_anchors(rel, text)
    ng += check_animation(p, text)
    if process:
        ng += check_process(rel, key, text)
    return ng


def webp_durations(path):
    """動く WebP の各コマの表示時間（ms）。動かない WebP なら空。"""
    import struct
    b = open(path, 'rb').read()
    if b[:4] != b'RIFF' or b[8:12] != b'WEBP':
        return []
    i, out = 12, []
    while i + 8 <= len(b):
        tag, size = b[i:i + 4], struct.unpack('<I', b[i + 4:i + 8])[0]
        if tag == b'ANMF':
            d = b[i + 20:i + 23]
            out.append(d[0] | d[1] << 8 | d[2] << 16)
        i += 8 + size + (size & 1)
    return out


def check_animation(p, text):
    """動く WebP の速さ（2026-11-12 著者の指定）。
    基準は著者が合格にした stdout-buffering・Sidecar・fuzzing・property-based-testing の実測（全体 7〜14 秒、
    最後のコマ 3 秒、caption に再生の速さ）。実際の映像の比較（全体 3 秒未満でコマが 50ms 以下）は対象外。"""
    ng = []
    bundle = os.path.dirname(p)
    for m in re.finditer(r'\{\{<\s*figure[^>]*src="([^"]+\.webp)"[^>]*>\}\}', text):
        src, tag = m.group(1), m.group(0)
        f = os.path.join(bundle, src)
        if not os.path.exists(f):
            continue
        d = webp_durations(f)
        if len(d) < 2:
            continue
        total = sum(d)
        if total < 3000 and max(d) <= 50:
            continue
        name = os.path.basename(src)
        if d[-1] < 2500:
            ng.append(f'動く図 {name}: 最後のコマが {d[-1]}ms（2.5 秒以上止めてから繰り返す）')
        if not 5000 <= total <= 20000:
            ng.append(f'動く図 {name}: 全体が {total / 1000:.1f} 秒（5〜20 秒。目安 10 秒前後）')
        fast = sum(x for x in d if x < 100)
        if fast > total / 2:
            ng.append(f'動く図 {name}: 100ms 未満のコマが全体の {fast * 100 // total}%（速すぎる。実時間より遅く、目安 0.5 倍速）')
        speed_rx = r'倍速|倍の速さ|秒で表示|秒ずつ|実時間'
        words = ' '.join(re.findall(r'(?:caption|alt)="([^"]*)"', tag))
        gens = glob.glob(os.path.join(bundle, '*.py')) + glob.glob(os.path.join(ROOT, 'projects/ml/scripts/notes', os.path.basename(bundle) + '_gen.py'))
        in_frames = any(re.search(speed_rx, open(g, encoding='utf-8').read()) for g in gens)
        if not re.search(speed_rx, words) and not in_frames:
            ng.append(f'動く図 {name}: 再生の速さが caption にもコマの中にも無い（「実測した時刻を 0.5 倍速で再生」など）')
    return ng


def heading_anchor(h):
    """Hugo（goldmark の autoHeadingID）の見出しの ID に近い形にする。"""
    h = re.sub(r'`([^`]*)`', r'\1', h).strip().lower()
    h = re.sub(r'[^\w\- ]', '', h)
    return re.sub(r' ', '-', h)


def check_anchors(rel, text):
    """他のノートからこのノートの #見出し へ張られたリンクが、今の見出しに実在するか（2026-11-12）。
    見出しを変えると、他のノートのページ内リンクが黙って切れるため。"""
    slug = rel.split('/')[-2]
    nocode = re.sub(r'```.*?```', '', text, flags=re.S)
    anchors = set()
    for m in re.finditer(r'^#{2,6}\s+(.+?)\s*$', nocode, re.M):
        h = m.group(1)
        cid = re.search(r'\{#([^}]+)\}\s*$', h)
        anchors.add(cid.group(1).lower() if cid else heading_anchor(h))
        if cid:
            anchors.add(heading_anchor(h[:cid.start()]))
    ng = []
    for base in ('content/notes', 'projects/ml/notes'):
        for p in glob.glob(os.path.join(ROOT, base, '*', '*', 'index.md')):
            if os.path.relpath(p, ROOT) == rel:
                continue
            for m in re.finditer(r'\]\(([^)\s]*' + re.escape(slug) + r'/?)#([^)\s]+)\)', open(p, encoding='utf-8').read()):
                a = m.group(2)
                try:
                    from urllib.parse import unquote
                    a = unquote(a)
                except Exception:
                    pass
                if a.lower() not in anchors:
                    ng.append(f'{os.path.relpath(p, ROOT)} から #{a} へのリンクが、このノートの見出しに無い（見出しを戻すか、リンク元を直す）')
    return ng


def check_process(rel, key, text):
    """書いた時の手続き（チェックリストと、直前 3 本との冒頭の型・題の形の重複）。
    新規と書き直しにだけ使い、既存のノートの質の判定（--quality）には使わない（2026-11-12）。"""
    ng = []
    cp = os.path.join(HERE, 'checklists', f'{key}.md')
    if not os.path.exists(cp):
        ng.append(f'完了のチェックリストが無い: notes-quality/checklists/{key}.md（notes-quality/completion_checklist.md の表を埋めて置く）')
    else:
        for line in open(cp, encoding='utf-8'):
            if not line.startswith('|') or set(line.strip()) <= set('|-: '):
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if cells[0] == '項目':
                continue
            val = cells[-1] if len(cells) > 1 else ''
            if not val or re.search(r'未実施|いいえ|^-$|TODO', val):
                ng.append(f'チェックリストの空欄・未実施: {cells[0][:40]} → 「{val}」')
        if opening_type(key) is None:
            ng.append(f'チェックリストの「冒頭の型」に {"/".join(TYPES)} のどれかを書く')

    prev = [r for r in opening_hist() if r[0] != key][-3:]
    ot, ts, title = opening_type(key), title_shape(title_of(text)), title_of(text)
    if len(prev) == 3 and ot and all(r[1] == ot for r in prev):
        ng.append(f'冒頭の型「{ot}」が直前の 3 本（{", ".join(r[0] for r in prev)}）と同じ。題材に合う別の型を選ぶ')
    if len(prev) == 3 and ts == 'なぜ' and all(r[2] == ts for r in prev):
        ng.append(f'題が直前の 3 本と同じ「〜の理由／なぜ〜のか」の形: {title}')

    # PC 幅（1280）での見栄え。箇条書きの折り返しと表のマスの行数を、描いて数える（layout_check.py。2026-11-12 著者の指定）。
    # hugo と google-chrome が要るので、無い環境では飛ばして知らせる
    if shutil.which('google-chrome') and shutil.which('hugo'):
        r = subprocess.run([sys.executable, os.path.join(HERE, 'layout_check.py'), rel],
                           cwd=ROOT, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            ng += ['PC 幅の見栄え: ' + l.strip() for l in r.stdout.splitlines() if l.strip()]
    else:
        print('  注意: hugo か google-chrome が無いので、PC 幅の見栄え（layout_check.py）を見ていない', file=sys.stderr)
    return ng


WORD = re.compile(r'[ァ-ヴー]+|[一-龥々]+|[A-Za-z][A-Za-z0-9-]*')


def _names(cell):
    """glossary.tsv のセルを、区切り（／、；・括弧）で分けた呼び名にする。英語だけの名前と 1 文字は外す。"""
    parts = re.split(r'[／/、,;；（）()「」]+', re.sub(r'（[^）]*）|\([^)]*\)', '', cell))
    return {x.strip() for x in parts if len(x.strip()) >= 2 and not re.fullmatch(r'[\x00-\x7f]+', x.strip())}


def glossary_pairs():
    """style/glossary.tsv の同じ行の（ノートでの言い方に出る語, 分野で一般的な言い方に出る語）の組。
    置き換えの取り残しは、この組に当たる置き換え（訳語の直し）だけを見る。普通の言い換えは見ない。"""
    p = os.path.join(HERE, 'style', 'glossary.tsv')
    if not os.path.exists(p):
        return set()
    out = set()
    for r in csv.reader(open(p, encoding='utf-8'), delimiter='\t'):
        if len(r) > 3 and not r[0].startswith('#') and r[0] != '組':
            olds, news = _names(r[2]), _names(r[3])
            out |= {(x, y) for x in olds - news for y in news - olds}
    return out


def _words_at(line, i1, i2):
    """line の [i1, i2) に掛かる語。"""
    return {m.group() for m in WORD.finditer(line) if m.start() < max(i2, i1 + 1) and m.end() > i1}


def replaced_terms(old_text, new_text):
    """行の中で別の語に置き換えた語（old → new の組）。手直しした行（文字の一致 0.6 以上）だけを見る。"""
    a, b = old_text.splitlines(), new_text.splitlines()
    pairs = set()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != 'replace':
            continue
        for line in b[j1:j2]:
            o = max(a[i1:i2], key=lambda x: difflib.SequenceMatcher(None, x, line).ratio())
            if difflib.SequenceMatcher(None, o, line).ratio() < REWRITE_SIMILARITY:
                continue
            for t, p1, p2, q1, q2 in difflib.SequenceMatcher(None, o, line, autojunk=False).get_opcodes():
                if t != 'replace':
                    continue
                olds = {w for w in _words_at(o, p1, p2) if w not in WORD.findall(line)}
                news = {w for w in _words_at(line, q1, q2) if w not in WORD.findall(o)}
                pairs |= {(x, y) for x in olds for y in news}
    return pairs


def check_small_whole(rel, old_text, new_text):
    """小さな修正でも全文を見る検査（2026-11-13 著者の指定）。既存の違反は数えず、今回の修正が生む食い違いだけを見る。
    1. 見出しの行を変えたら、他のノートからこのノートの #見出し へのリンクが残っているか
    2. glossary.tsv の訳語を分野の言い方に置き換えたら、古い語が同じノートの他の行に残っていないか（新旧の訳を混ぜない）。
       同じ語が別の意味で残る（lsm-tree の「併合」、tor の「経路」）ことが多く、機械では分けられないので止めずに知らせる"""
    ng = []
    if any(re.match(r'#{2,6}\s', l) for l in removed_lines(old_text, new_text)):
        ng += check_anchors(rel, new_text)
    terms = glossary_pairs()
    body = re.sub(r'```.*?```', '', new_text, flags=re.S)
    plain = re.sub(r'`[^`]*`|\]\([^)]*\)|https?://\S+', '', body)
    for old_w, new_w in sorted(replaced_terms(old_text, new_text)):
        if (old_w, new_w) not in terms:
            continue
        rows = [str(i + 1) for i, l in enumerate(new_text.splitlines()) if old_w in re.sub(r'`[^`]*`|\]\([^)]*\)|https?://\S+', '', l)]
        if old_w in WORD.findall(plain) and rows:
            print(f'  注意: {rel}: 「{old_w}」を「{new_w}」に置き換えたが、同じノートに「{old_w}」が残っている'
                  f'（行: {", ".join(rows[:8])}）。同じ訳語なら揃え、別の意味（併合する・経路上の装置など）ならそのままでよい')
    return ng


def classify(rel, old_text, new_text):
    """'new'（新規）・'major'（大きな改稿）・'small'（小さな修正）。"""
    if old_text is None:
        return 'new'
    add = len(rewritten_lines(old_text, new_text))
    total = max(1, len(old_text.splitlines()))
    if add >= MAJOR_LINES or add / total >= MAJOR_RATIO:
        return 'major'
    return 'small'


def score_check(rel, head_text):
    """scores/<key>.json が総合 4 以上で、記録した版から足した行が SMALL 以下か。"""
    key = key_of(rel)
    sp = os.path.join(HERE, 'scores', f'{key}.json')
    if not os.path.exists(sp):
        return [f'点の記録が無い: notes-quality/scores/{key}.json（読解 A・事実確認・採点し直しで総合 4 以上を記録してから push）']
    s = json.load(open(sp, encoding='utf-8'))
    ng = []
    by = s.get('by', '')
    independent = s.get('baseline') == BASELINE or '基準 5 本 5・5・3・2・2' in by or '著者' in by
    if '自己' in by or not independent:
        ng.append(f'点の記録が書いた本人の採点か、基準の 5 本を一緒に採点していない（by: {by[:60]}）。'
                  '別の担当が抜き出しだけで、基準の 5 本（5・5・3・2・2）と一緒に採点し直し、gate.py score --baseline 5,5,3,2,2 で記録する')
    if s.get('standard') != STANDARD:
        ng.append('関門より前の基準で付けた点（旧基準）。関門の質の判定を通してから、別の担当が採点し直して gate.py score で記録する')
    if s.get('overall', 0) < 4:
        ng.append(f'記録の総合が {s.get("overall")}（4 以上でないと push できない）')
    scored = git('cat-file', '-p', s.get('blob', ''), check=True) if s.get('blob') else None
    if scored is None:
        ng.append('点の記録の版（blob）がリポジトリに無い。採点し直す')
    else:
        add = added_lines(scored, head_text)
        n = len(rewritten_lines(scored, head_text))
        if n > SMALL:
            ng.append(f'採点した版から {n} 行を書き足し・書き直している（{SMALL} 行まで。語の置き換えなどの手直しは数えない）。採点し直す')
        else:
            ng += check_added(add, removed_lines(scored, head_text))
    return ng


def report(results):
    bad = False
    for rel, kind, ng in results:
        print(('NG ' if ng else 'OK ') + f'{rel}（{kind}）')
        for x in ng:
            print('  NG:', x)
        bad = bad or bool(ng)
    for x in dict.fromkeys(NOTICES):
        print('  注意:', x[:160])
    NOTICES.clear()
    return 1 if bad else 0


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cmd, rest = argv[0], argv[1:]
    if cmd == 'note':
        diff = '--diff' in rest
        rel = os.path.relpath(os.path.abspath([a for a in rest if not a.startswith('--')][0]), ROOT)
        if not key_of(rel):
            sys.exit(f'対象外のパス: {rel}')
        if diff:
            old = git('show', f'HEAD:{rel}', check=True)
            cur = open(os.path.join(ROOT, rel), encoding='utf-8').read()
            ng = check_added(added_lines(old or '', cur), removed_lines(old or '', cur))
            ng += check_small_whole(rel, old or '', cur)
            return report([(rel, '足した行だけ', ng)])
        if '--quality' in rest:
            code = report([(rel, '質の規則だけ', check_full(rel, process=False))])
        else:
            code = report([(rel, '全部の規則', check_full(rel))])
        # 相互リンクの抜けの候補は止めずに知らせる（2026-11-12 著者の指定）。
        # 前提や詳しい説明があるノートなら初出にリンクを足し、題材が違うなら足さない。チェックリストの相互リンクの行に結果を書く
        _, out = run([sys.executable, os.path.join(HERE, 'crosslinks.py'), os.path.join(ROOT, rel)])
        if out.strip():
            print('  注意: 相互リンクの抜けの候補 ' + out.strip().split(': ', 1)[-1])
        return code

    if cmd == 'commit':
        results = []
        for rel in git('diff', '--cached', '--name-only', '--diff-filter=AM').split():
            if not key_of(rel):
                continue
            old = git('show', f'HEAD:{rel}', check=True)
            new = git('show', f':{rel}')
            kind = classify(rel, old, new)
            ng = check_added(added_lines(old, new), removed_lines(old, new)) if kind == 'small' else check_full(rel)
            if kind == 'small':
                ng += check_small_whole(rel, old, new)
            results.append((rel, kind, ng))
        return report(results)

    if cmd == 'push':
        base, head = rest[0], rest[1]
        if re.fullmatch(r'0+', base) or git('cat-file', '-e', base, check=True) is None:
            base = git('rev-parse', f'{head}~1').strip()
        # 範囲の commit を 1 つずつ、親との差分で見る（2026-11-12）。pre-push を 1 commit ずつ通した直しを、
        # CI が最後に公開した版からまとめて比べると、分けた commit が合算されて大きな改稿になり、食い違うため。
        # CI も pre-push と同じく、今回 push した範囲だけを見る（2026-11-13）。
        commits = git('rev-list', '--reverse', '--no-merges', f'{base}..{head}').split() or [head]
        merged = {}
        for c in commits:
            parent = git('rev-parse', f'{c}~1').strip() if c != head or commits != [head] else base
            for line in git('diff', '--name-status', '--diff-filter=AMR', parent, c).splitlines():
                parts = line.split('\t')
                rel = parts[-1]
                if not key_of(rel):
                    continue
                old = git('show', f'{parent}:{parts[1] if parts[0].startswith("R") else rel}', check=True)
                new = git('show', f'{c}:{rel}')
                kind = classify(rel, old, new)
                if kind == 'small':
                    title = [f'{rel}\n{title_of(new)}'] if check_added.__code__.co_argcount > 2 else []
                    ng = check_added(added_lines(old, new), removed_lines(old, new), *title)
                    ng += check_small_whole(rel, old, new)
                else:
                    ng = check_full(rel) + score_check(rel, git('show', f'{head}:{rel}'))
                prev = merged.get(rel)
                rank = {'small': 0, 'major': 1, 'new': 2}
                k = kind if prev is None or rank[kind] >= rank[prev[0]] else prev[0]
                merged[rel] = (k, (prev[1] if prev else []) + [f'{c[:8]}: {x}' for x in ng])
        results = [(rel, kind, ng) for rel, (kind, ng) in merged.items()]
        if '--ng-list' in rest:
            out = rest[rest.index('--ng-list') + 1]
            with open(out, 'w', encoding='utf-8') as f:
                for rel, kind, ng in results:
                    if ng:
                        f.write(os.path.dirname(rel) + '\n')
        return report(results)

    if cmd == 'score':
        rel = os.path.relpath(os.path.abspath(rest[0]), ROOT)
        opts = dict(zip(rest[1::2], rest[2::2]))
        blob = subprocess.run(['git', '-C', ROOT, 'hash-object', '-w', rel], capture_output=True, text=True).stdout.strip()
        base = [int(x) for x in opts.get('--baseline', '').split(',') if x.strip()]
        if base != BASELINE:
            sys.exit('--baseline に、同じ回に採点した基準の 5 本の点（5,5,3,2,2）を渡す。動いていたらその回の採点は使わない')
        if '自己' in opts.get('--by', '') or not opts.get('--by'):
            sys.exit('--by に採点した担当を書く。書いた本人の採点（自己採点）は記録しない')
        q = check_full(rel, process=False)
        if q:
            print('関門の質の判定が NG なので点を記録しない（4 点は、関門の質の判定を通った上での点）:')
            for x in q:
                print('  NG:', x)
            return 1
        rec = {'path': rel, 'overall': int(opts.get('--overall', 0)), 'product': int(opts.get('--product', 0)),
               'blob': blob, 'by': opts['--by'], 'baseline': base, 'scored_at': opts.get('--at', ''),
               'standard': STANDARD}
        os.makedirs(os.path.join(HERE, 'scores'), exist_ok=True)
        json.dump(rec, open(os.path.join(HERE, 'scores', f'{key_of(rel)}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'記録した: notes-quality/scores/{key_of(rel)}.json 総合 {rec["overall"]}')
        return 0

    if cmd == 'record':
        rel = os.path.relpath(os.path.abspath(rest[0]), ROOT)
        key = key_of(rel)
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        rows = [r for r in opening_hist() if r[0] != key] + [[key, opening_type(key) or '', title_shape(title_of(text)), title_of(text)]]
        with open(os.path.join(HERE, 'opening_log.tsv'), 'w', encoding='utf-8', newline='') as f:
            f.write('# key\t冒頭の型\t題の形\t題\n')
            csv.writer(f, delimiter='\t', lineterminator='\n').writerows(rows)
        return 0
    sys.exit(__doc__)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
