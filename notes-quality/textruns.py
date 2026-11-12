"""ノートの黒々しさを数える: 図・表・コード・見出しを挟まずに文字だけが 700 字以上続く区間と、200 字を超える段落。
使い方: python3 textruns.py content/notes/<section>/<slug>/index.md ...
目安（2026-11-11）: 基準の Wallet は区間 0 個・長い段落 5 個。区間は 0 個、長い段落は Wallet 並みを目標にする。
"""
import re,sys
def runs(path):
    s=open(path,encoding='utf-8').read().split('---',2)[2]
    lines=s.split('\n'); out=[]; cur=0; start=None; incode=False; longp=0
    for i,l in enumerate(lines,1):
        t=l.strip()
        if t.startswith('```') or t.startswith('~~~'):
            incode=not incode
            if cur>=700: out.append((start,i,cur))
            cur=0; start=None; continue
        if incode: continue
        brk = t.startswith(('{{<','<figure','<div','<video','|','![','```')) or t.startswith('#')
        if brk:
            if cur>=700: out.append((start,i,cur))
            cur=0; start=None; continue
        txt=re.sub(r'\]\([^)]*\)',']',t)
        n=len(re.sub(r'\s','',txt))
        if n and start is None: start=i
        cur+=n
        if n>200: longp+=1
    if cur>=700: out.append((start,len(lines),cur))
    return out,longp
for p in sys.argv[1:]:
    o,lp=runs(p)
    print(f"{p}: 700字以上の文字だけの区間 {len(o)} 個 / 200字超の段落 {lp} 個")
    for a,b,c in o: print(f"   行 {a}-{b}（本文の行番号は front matter 後）: {c} 字")
