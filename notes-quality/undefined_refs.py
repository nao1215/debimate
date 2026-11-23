"""定義せずに使う書き方を見つける（2026-11-23 著者の指定）。

    python3 notes-quality/undefined_refs.py <index.md>...   # 見つけた所を行番号付きで出す。NG があれば終了コード 1
    python3 notes-quality/undefined_refs.py --all            # content/notes と projects/ml/notes の全部

規則。NG は gate.py が新規と書き直しで止め、小さな修正では足した行に出た時だけ止める。注意は止めない。
- bare_numbers（NG）: 単位も対象も付かない数字を「にも」で 2 つ以上並べる。「同じ絵文字が 18 にも 8 にも 5 にも 1 にも
  なります」のように、何の数かが図の中にしか無い。数字の直前に名前（block 3、手順 2、seed）がある時、文の主語が量の語
  （長さ・幅・値・比など）の時、同じ数字の組がそれより前に値として出ている時（合意の 0 と 1）は除く。
- borrowed_term（NG）: 内部リンク [X](/notes/... や /ml/...) の直後の「の〈語〉として・の形で・で書・に当たる」で、〈語〉が
  リンク先の見出しにあり、このノートでは定義の形（「語」、語（english）、語とは、という語）で出てこず、それより前にも
  1 回以下しか出てこないもの。「[Metamorphic Testing](...) の関係として書けます」の「関係」が当たる。
- borrowed_term_weak（注意）: 内部リンクの直後の「の〈語〉」で、〈語〉がリンク先に偏って出る（全ノートの平均の 30 倍以上）
  のに、このノートでは定義の形で出てこず、前に 1 回以下しか出てこないもの。tombstone・ファサード・relay など。
- acronym_before_def（注意）: 略語（ABI、HTLC など）を、後の行で「略語（正式な英語名）」と定義する前に、説明無しで使っている。

判定は形態素解析を使わない近似。コードブロック・表・引用・HTML の行・URL・インラインのコードは見ない。shortcode は caption だけ見る。
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# 数字の直後に付けば何の数かが分かる助数詞・単位
UNIT = (r'(?:%|％|倍|件|個|つ|本|枚|回|度|点|人|台|行|列|字|文字|バイト|byte|bytes|B|KB|MB|GB|TB|KiB|MiB|GiB|bit|ビット|'
        r'桁|秒|分|時間|日|週|か月|ヶ月|月|年|ms|us|µs|ns|s|m|cm|mm|km|px|pt|dpi|Hz|kHz|MHz|GHz|円|ドル|ETH|BTC|gwei|wei|'
        r'セル|マス|段|層|次元|通り|番|番目|位|割|ブロック|ノード|スレッド|コア|step|steps|ステップ|エポック|epoch|epochs|'
        r'トークン|token|tokens|語|章|節|項|票|署名|鍵|ページ|画素|ピクセル|色|ch|fps|コマ|フレーム|K|M|G|k|x|×|sat|ガス)')
NUM = r'(?<![\w.\-/:#v])\d+(?:\.\d+)?'
NIMO = re.compile(rf'(?:{NUM}(?! ?{UNIT}) ?にも ?){{2,}}')
# 文の主語がこれで終われば、並んだ数字はその量の値として読める
QUANTITY = re.compile(r'(長さ|幅|値|数|比|率|係数|スコア|彩度|指標|重み|番号|差|時間|人数|一致|強さ|件数|個数|回数|サイズ|容量)$')
# 数字の直前の 1 字がこれなら、数字は名前の付いた識別子（block 3、手順 2、注文 101）
LABELED = re.compile(r'[一-龥々ァ-ヶーA-Za-z0-9)）]$')

INTERNAL = r'\[[^\]]+\]\((?:/notes/|/ml/|\.\./)[^)]*\)'
WORD = r'[一-龥々ァ-ヶーA-Za-z][一-龥々ァ-ヶーA-Za-z0-9]*'
LINK_NO = re.compile(rf'({INTERNAL}) ?の ?({WORD})(?=[ぁ-ゖ、。 ])')
BORROW_TAIL = re.compile(r' ?(として|の形で|で書|に当た)')

ACRONYM_DEF = re.compile(r'(?<![A-Za-z0-9])([A-Z][A-Z0-9]{1,6})（([A-Z][A-Za-z]+(?: [A-Za-z][A-Za-z-]*)+)[^）]*）')
COMMON_ACRONYMS = set('CPU GPU OS API URL HTTP HTTPS SQL JSON CSV HTML CSS DB ID IP TCP UDP DNS TLS SSH CLI GUI UI UX PC RAM SSD HDD IO PDF PNG AI ML LLM'.split())

_CORPUS = {}


def visible_lines(text):
    """(行番号, 読者に見える文) の列。front matter・コード・表・引用・HTML の行を除く。shortcode は caption だけ残す。"""
    lines = text.split('\n')
    start = 0
    if lines and lines[0] == '---':
        try:
            start = lines.index('---', 1) + 1
        except ValueError:
            start = 0
    out, incode = [], False
    for i, line in enumerate(lines[start:], start + 1):
        s = line.lstrip()
        if s.startswith(('```', '~~~')):
            incode = not incode
            continue
        if incode or s.startswith(('|', '>', '<')):
            continue
        if s.startswith('{{<'):
            m = re.search(r'caption="([^"]*)"', s)
            line = m.group(1) if m else ''
        line = re.sub(r'`[^`]*`', 'X', line)
        line = re.sub(r'(?<!\()https?://\S+', '', line)
        out.append((i, line))
    return out


def unlink(line):
    return re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', line)


def all_notes():
    return sorted(glob.glob(os.path.join(ROOT, 'content/notes/*/*/index.md')) + glob.glob(os.path.join(ROOT, 'projects/ml/notes/*/index.md')))


def corpus():
    if not _CORPUS:
        texts = [open(p, encoding='utf-8').read() for p in all_notes()]
        _CORPUS['texts'] = texts
        _CORPUS['size'] = max(1, sum(len(t) for t in texts))
        _CORPUS['rate'] = {}
    return _CORPUS


def concentration(word, target):
    """リンク先での語の出現率が、全ノートの平均の何倍か。"""
    c = corpus()
    if word not in c['rate']:
        c['rate'][word] = sum(t.count(word) for t in c['texts']) / c['size']
    return (target.count(word) / max(1, len(target))) / max(c['rate'][word], 1e-9)


def doc_freq(word):
    """語が出るノートの本数。多くのノートに出る語（価格・認証・ハッシュ値）は一般の語として扱う。"""
    c = corpus()
    c.setdefault('df', {})
    if word not in c['df']:
        c['df'][word] = sum(word in t for t in c['texts'])
    return c['df'][word]


def target_text(link, path=''):
    """内部リンクの先のノートの本文。見つからなければ ''。相対リンク（../lsm-tree/）は path のノートから辿る。"""
    m = re.search(r'\]\(((?:/(?:notes|ml)/|\.\./)[^)#\s]*)', link)
    if not m:
        return ''
    url = m.group(1)
    if url.startswith('..'):
        p = os.path.normpath(os.path.join(os.path.dirname(path) or ROOT, url, 'index.md'))
        return open(p, encoding='utf-8').read() if path and os.path.exists(p) else ''
    url = url.strip('/')
    if url.startswith('notes/'):
        p = os.path.join(ROOT, 'content', url, 'index.md')
    else:
        p = os.path.join(ROOT, 'projects/ml/notes', url.split('/', 1)[-1], 'index.md')
    return open(p, encoding='utf-8').read() if os.path.exists(p) else ''


def defined_here(word, text):
    w = re.escape(word)
    return bool(re.search(rf'^#+ .*{w}|「{w}」|{w}（|（{w}）|{w}とは|という{w}|{w}と呼', text, re.M))


def _bare_numbers(plain, seen):
    out = []
    for m in NIMO.finditer(plain):
        pre = plain[:m.start()].rstrip()
        if pre and LABELED.search(pre):
            continue
        sent = re.split(r'[。！？]', pre)[-1]
        subj = re.findall(r'([一-龥々ァ-ヶーA-Za-z0-9]+[さ]?) ?(?:が|は|も)', sent)
        if subj and QUANTITY.search(subj[-1]):
            continue
        # 同じ文の前で数字に単位を付けていれば（「2 セル、…1 にも 2 にも」）、単位は読み取れる
        if re.search(rf'\d ?{UNIT}', sent):
            continue
        nums = re.findall(r'\d+(?:\.\d+)?', m.group(0))
        # 同じ数字の組が前に値として並んでいれば（合意の 0 と 1 など）、読者は何の値か知っている
        pair = r' ?(?:と|か|や|にも|、) ?'.join(re.escape(x) for x in nums[:2])
        if re.search(rf'(?<![\d.]){pair}(?![\d.])', seen):
            continue
        out.append((plain[max(0, m.start() - 20):m.end() + 8].strip(),
                    f'数字 {"・".join(nums)} に単位も対象も無い。何の数かを数字に付ける（例: 「18 バイトにも 8 個にも」、'
                    '文の頭に「長さは」を置く）'))
    return out


def scan(path, text=None):
    """(行番号, 規則, 'ng' か 'notice', 抜粋, 直し方) の列。"""
    text = open(path, encoding='utf-8').read() if text is None else text
    found, seen = [], ''
    vis = visible_lines(text)
    for n, line in vis:
        plain = unlink(line)
        heading = line.lstrip().startswith('#')
        if not heading:
            for ex, hint in _bare_numbers(plain, seen):
                found.append((n, 'bare_numbers', 'ng', ex, hint))
            for m in LINK_NO.finditer(line):
                word = m.group(2)
                rest = line[m.end():]
                if len(word) < 2 or re.search(r'\d', word) or rest.startswith('（') or re.fullmatch(r'[A-Z][a-z]+', word):
                    continue
                pre = seen + unlink(line[:m.start()])
                if defined_here(word, pre + unlink(line)) or pre.count(word) > 1:
                    continue
                tgt = target_text(m.group(1), path)
                if not tgt:
                    continue
                label = unlink(m.group(0)) + rest[:10]
                in_heading = bool(re.search(rf'^#+ .*{re.escape(word)}', tgt, re.M))
                ratio = concentration(word, tgt)
                # 括弧の中の言い換え（「root（…。[Finality] の確定に当たります）」）は本文の理解に要らないので NG にしない
                in_paren = pre.count('（') > pre.count('）') if '\n' not in pre[-200:] else unlink(line[:m.start()]).count('（') > unlink(line[:m.start()]).count('）')
                if BORROW_TAIL.match(rest) and in_heading and ratio >= 5 and not in_paren:
                    found.append((n, 'borrowed_term', 'ng', label,
                                  f'「{word}」はリンク先の専門語で、このノートでは定義していない。何を指すかを本文の語で言う'))
                elif ratio >= 30 and tgt.count(word) >= 2 and doc_freq(word) < 20:
                    found.append((n, 'borrowed_term_weak', 'notice', label,
                                  f'「{word}」はリンク先に偏って出る語で、このノートでは定義していない。初出なら 1 文で説明する'))
        seen += plain + '\n'
    # 略語を定義より前に使っている
    first = {}
    for n, line in vis:
        plain = unlink(line)
        for m in ACRONYM_DEF.finditer(plain):
            ac = m.group(1)
            if ac in COMMON_ACRONYMS or ac in first and first[ac] is None:
                continue
            if ac in first:
                ln, ex = first[ac]
                if n - ln >= 3:
                    found.append((ln, 'acronym_before_def', 'notice', ex,
                                  f'{ac} を {n} 行目で定義する前に使っている。初出で正式名と役割を書くか、定義を前に移す'))
            first[ac] = None
        # 見出し・箇条書き（読者の問いの一覧）・「本記事では」の予告は、後で説明する前提の行なので数えない
        if line.lstrip().startswith(('#', '- ', '* ', '本記事では')):
            continue
        for m in re.finditer(r'(?<![A-Za-z0-9-])([A-Z][A-Z0-9]{1,6})(?![A-Za-z0-9-])', plain):
            ac = m.group(1)
            if ac in first:
                continue
            # その場で説明している（ABI は〜、ABI と呼ぶ〜、ABI（）は定義の形で拾う）
            # 後で説明すると断っている（後述の ACME、次の節で説明する HTLC）か、その語のノートへのリンクなら数えない
            if (re.match(r' ?(は|（|と呼|という)', plain[m.end():]) or re.search(r'と呼ぶ ?$|という ?$', plain[:m.start()])
                    or re.search(r'(後述の|説明する|扱う) ?$', plain[:m.start()]) or re.match(r' ?（[^）]*(後述|説明しま)', plain[m.end():])
                    or re.search(rf'\[{ac}\]\(', line)
                    or re.search(r'(節|後)で(説明|扱)い?し?ます|後述', re.split(r'。', plain[m.start():])[0])):
                first[ac] = None
                continue
            first[ac] = (n, plain[max(0, m.start() - 20):m.end() + 20].strip())
    return sorted(found)


def findings_in_added(old_text, new_text, added):
    """小さな修正で、足した行に新しく出た指摘だけ（2026-11-23）。元の版にあった指摘は数えない。"""
    before = {(r, ex) for _, r, _, ex, _ in scan('', old_text)} if old_text else set()
    added = set(added)
    lines = new_text.split('\n')
    return [f for f in scan('', new_text) if (f[1], f[3]) not in before and lines[f[0] - 1] in added]


if __name__ == '__main__':
    paths = all_notes() if '--all' in sys.argv else [a for a in sys.argv[1:] if not a.startswith('--')]
    bad = 0
    for p in paths:
        for n, rule, level, ex, hint in scan(p):
            print(f'{os.path.relpath(p, ROOT)}:{n}: {"NG" if level == "ng" else "注意"} {rule}: {ex} → {hint}')
            bad += level == 'ng'
    sys.exit(1 if bad else 0)
