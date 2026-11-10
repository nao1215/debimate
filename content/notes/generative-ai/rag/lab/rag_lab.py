"""debimate の技術ノートを文書集合にした、RAG の検索部分の実験コード。

- 文書集合: コミット COMMIT 時点の content/notes/**/index.md（git show で読む）
- 前処理: front matter・コードブロック・画像・HTML タグ・Hugo の shortcode を除き、
  リンクは文字だけを残す
- チャンク: 固定長（文字数で機械的に切る。重なり無し）と、### の節単位
- 埋め込み: Ollama の bge-m3（/api/embed）。ベクトルは長さ 1 に揃えて保存する
- 検索: 質問のベクトルとの内積（= 余弦類似度）が大きい順に k 個

使い方:
    python3 rag_lab.py build <キャッシュのディレクトリ>   # 全チャンクを埋め込んで保存する
依存: numpy（uv run --with numpy==2.3.4 python3 rag_lab.py ...）
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

import numpy as np

COMMIT = "16c40d266f3b22752613f56f41fc1ca5e2f37c08"
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 5))
OLLAMA = "http://" + os.environ.get("OLLAMA_HOST", "127.0.0.1:11435")
EMBED_MODEL = "bge-m3"
STRATEGIES = ["200", "500", "1000", "2000", "section"]


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], check=True,
                          capture_output=True, text=True).stdout


def clean(md):
    """Markdown から地の文と見出しだけを残す。見出しは '### ' のまま残す。"""
    md = re.sub(r"\A---\n.*?\n---\n", "", md, flags=re.S)       # front matter
    md = re.sub(r"^```.*?^```[ \t]*$", "", md, flags=re.S | re.M)  # コードブロック・mermaid
    md = re.sub(r"\{\{[<%].*?[%>]\}\}", "", md, flags=re.S)      # shortcode
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)                 # 画像
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)             # リンクは文字だけ
    md = re.sub(r"<[^>\n]+>", "", md)                            # HTML タグ
    lines = [ln.rstrip() for ln in md.splitlines()]
    lines = [ln for ln in lines if ln.strip() not in ("---", "")]
    return "\n".join(lines) + "\n"


def load_notes():
    """{slug: {"title", "text", "sections": [(見出し, 開始, 終了)]}} を返す。"""
    paths = [p for p in git("ls-tree", "-r", "--name-only", COMMIT, "content/notes").split()
             if p.endswith("/index.md")]
    notes = {}
    for p in sorted(paths):
        md = git("show", f"{COMMIT}:{p}")
        title = re.search(r'^title:\s*"(.*)"', md, flags=re.M).group(1)
        text = clean(md)
        heads = [(m.group(1).strip(), m.start()) for m in re.finditer(r"^### (.+)$", text, flags=re.M)]
        starts = [("(冒頭)", 0)] + heads
        sections = [(h, s, starts[i + 1][1] if i + 1 < len(starts) else len(text))
                    for i, (h, s) in enumerate(starts)]
        slug = p.split("/")[-2]
        notes[slug] = {"title": title, "text": text, "sections": sections,
                       "path": p}
    return notes


def chunk(notes, strategy):
    """[{"slug", "start", "end", "text"}] を返す。ノートをまたぐチャンクは作らない。"""
    out = []
    for slug, n in notes.items():
        text = n["text"]
        if strategy == "section":
            spans = [(s, e) for _, s, e in n["sections"]]
        else:
            size = int(strategy)
            spans = [(i, min(i + size, len(text))) for i in range(0, len(text), size)]
        for s, e in spans:
            if text[s:e].strip():
                out.append({"slug": slug, "start": s, "end": e, "text": text[s:e]})
    return out


def embed(texts, batch=16):
    vecs = []
    for i in range(0, len(texts), batch):
        body = json.dumps({"model": EMBED_MODEL, "input": texts[i:i + batch],
                           "truncate": False, "options": {"num_ctx": 8192}}).encode()
        req = urllib.request.Request(OLLAMA + "/api/embed", body,
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            vecs.extend(json.load(r)["embeddings"])
    v = np.array(vecs, dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def search(index_vecs, query_vec, k):
    """余弦類似度の上位 k 個の (チャンクの番号, 類似度)。"""
    scores = index_vecs @ query_vec          # 長さ 1 のベクトル同士なので内積 = 余弦類似度
    top = np.argsort(-scores)[:k]
    return [(int(i), float(scores[i])) for i in top]


def load_index(cache, strategy):
    chunks = json.load(open(os.path.join(cache, f"chunks_{strategy}.json")))
    vecs = np.load(os.path.join(cache, f"vecs_{strategy}.npy"))
    return chunks, vecs


def build(cache):
    os.makedirs(cache, exist_ok=True)
    notes = load_notes()
    total = sum(len(n["text"]) for n in notes.values())
    print(f"notes: {len(notes)}, characters after cleaning: {total:,}")
    for st in STRATEGIES:
        chunks = chunk(notes, st)
        vecs = embed([c["text"] for c in chunks])
        json.dump(chunks, open(os.path.join(cache, f"chunks_{st}.json"), "w"), ensure_ascii=False)
        np.save(os.path.join(cache, f"vecs_{st}.npy"), vecs)
        lens = [len(c["text"]) for c in chunks]
        print(f"strategy {st:>7}: {len(chunks):5,} chunks, "
              f"chars median {int(np.median(lens)):5,} max {max(lens):5,}")


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(sys.argv[2])
