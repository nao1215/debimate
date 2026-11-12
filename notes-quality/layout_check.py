"""PC 幅（1280）で描いた時の見栄えを数える。

箇条書きの 1 項目が何行に折り返すか、表のマスが何行になるかを、hugo でビルドしたページを
headless Chrome で描いて数える（2026-11-11 著者の指定。撮影を目で見る代わりに数で止める）。

使い方:
    python3 notes-quality/layout_check.py <ノートの index.md> [...]
    python3 notes-quality/layout_check.py --public <hugo の出力先> <index.md> ...

hugo の出力は .note-review/work/layout/public に置く（/tmp は RAM のため）。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORK = REPO / ".note-review" / "work" / "layout"

# 何行から数えるか。手本（Wallet・Sidecar・stdout-buffering）の実測で決める。
# 手本の実測（2026-11-12）: Wallet は箇条書き 3 行が 2 項目・文字のマス 4 行が 1 個、stdout-buffering は箇条書き 3 行が 4 項目、
# Sidecar は全て 2 行以内。番号付きの手順（事故の経路など）と、コードが半分を超えるマスは数えない。
LI_MAX_LINES = 3     # 箇条書き（ul）の 1 項目はこの行数まで
TD_MAX_LINES = 4     # 文字の表のマスはこの行数まで

MEASURE_JS = r"""
<script>
window.addEventListener('load', () => {
  const root = document.querySelector('.post-content') || document.body;
  const lines = el => {
    const r = document.createRange();
    const tops = new Set();
    const walk = n => {
      for (const c of n.childNodes) {
        if (c.nodeType === 3 && c.textContent.trim()) {
          r.selectNodeContents(c);
          for (const b of r.getClientRects()) if (b.width > 0) tops.add(Math.round(b.top));
        } else if (c.nodeType === 1 && !['UL', 'OL', 'PRE', 'DETAILS'].includes(c.tagName)) walk(c);
      }
    };
    walk(el);
    return tops.size;
  };
  const out = { li: [], td: [] };
  const vis = el => !el.closest('details:not([open])');
  root.querySelectorAll('ul > li').forEach(li => { if (vis(li) && !li.closest('nav, .toc')) out.li.push([lines(li), li.innerText.split('\n')[0].slice(0, 40)]); });
  const codeShare = el => { const t = el.innerText.length || 1; let c = 0; el.querySelectorAll('code').forEach(x => c += x.innerText.length); return c / t; };
  root.querySelectorAll('td, th').forEach(td => { if (vis(td) && codeShare(td) <= 0.5) out.td.push([lines(td), td.innerText.slice(0, 40)]); });
  const pre = document.createElement('pre'); pre.id = 'layout-out'; pre.textContent = JSON.stringify(out);
  document.body.appendChild(pre);
});
</script>
"""


def url_path(rel):
    rel = rel.replace("\\", "/")
    m = re.match(r"projects/ml/notes/(.+)/index\.md$", rel)
    if m:
        return f"ml/{m.group(1)}/index.html"
    m = re.match(r"content/notes/(.+)/index\.md$", rel)
    if m:
        return f"notes/{m.group(1)}/index.html"
    raise SystemExit(f"ノートの index.md ではない: {rel}")


def build(public):
    public.mkdir(parents=True, exist_ok=True)
    subprocess.run(["hugo", "--quiet", "-d", str(public), "--baseURL", f"file://{public}/"],
                   cwd=REPO, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def measure(public, rel):
    page = public / url_path(rel)
    if not page.exists():
        return None
    html = page.read_text(encoding="utf-8")
    html = html.replace("</body>", MEASURE_JS + "</body>", 1)
    with tempfile.NamedTemporaryFile("w", suffix=".html", dir=page.parent, delete=False, encoding="utf-8") as f:
        f.write(html)
        tmp = f.name
    try:
        r = subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
                            "--allow-file-access-from-files", "--window-size=1280,900",
                            "--virtual-time-budget=8000", "--dump-dom", f"file://{tmp}"],
                           capture_output=True, text=True, timeout=120)
    finally:
        os.unlink(tmp)
    m = re.search(r'<pre id="layout-out">(.*?)</pre>', r.stdout, re.S)
    if not m:
        return None
    import html as h
    return json.loads(h.unescape(m.group(1)))


def main(argv):
    args = argv[1:]
    own = None
    if args[:1] == ["--public"]:
        public = Path(args[1]); args = args[2:]
    else:
        # 2 本を並行で見ることがあるので、出力先は実行ごとに分けて、終わったら消す
        WORK.mkdir(parents=True, exist_ok=True)
        own = public = Path(tempfile.mkdtemp(prefix="public-", dir=WORK))
        build(public)
    try:
        return report(public, args)
    finally:
        if own:
            shutil.rmtree(own, ignore_errors=True)


def report(public, args):
    bad = 0
    for rel in args:
        res = measure(public, rel)
        if res is None:
            print(f"?? {rel}: ページを描けなかった（hugo の出力に無い）")
            continue
        li = [x for x in res["li"] if x[0] > LI_MAX_LINES]
        td = [x for x in res["td"] if x[0] > TD_MAX_LINES]
        if li or td:
            bad += 1
            print(f"NG {rel}: 箇条書き {len(li)} 項目が {LI_MAX_LINES + 1} 行以上、表のマス {len(td)} 個が {TD_MAX_LINES + 1} 行以上（PC 幅 1280）")
            for n, t in li[:5]:
                print(f"   箇条書き {n} 行: {t}")
            for n, t in td[:5]:
                print(f"   表のマス {n} 行: {t}")
        else:
            print(f"OK {rel}: 箇条書き {len(res['li'])} 項目・表のマス {len(res['td'])} 個とも上限内")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
