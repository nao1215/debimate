"""検索した上位 k 個のチャンクを qwen3:4b に渡して答えさせる。

使い方:
    python3 ask.py <キャッシュのディレクトリ> <チャンクの切り方> <k> <質問の id> [...]
    k に 0 を渡すと、検索せずに質問だけを渡す（比較用）。
Ollama の qwen3:4b は Qwen3-4B-Thinking-2507（思考を止められないモデル）で、
"think": false を渡しても思考の文が回答に混ざる。そのため "think": true で思考を
message.thinking に分け、回答（message.content）だけを表示する。temperature 0・seed 固定。
"""
import json
import os
import sys
import urllib.request

import rag_lab

LLM = "qwen3:4b"
SYSTEM = ("あなたは debimate の技術ノートについて答えるアシスタントです。"
          "与えられた資料だけを根拠に、日本語で 3 文以内で答えてください。"
          "根拠にした資料の番号を [1] のように示してください。"
          "資料に答えが無ければ「資料からは分かりません」と答えてください。")


def chat(messages):
    body = json.dumps({"model": LLM, "messages": messages, "stream": False, "think": True,
                       "options": {"temperature": 0, "seed": 42, "num_ctx": 16384}}).encode()
    req = urllib.request.Request(rag_lab.OLLAMA + "/api/chat", body,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        res = json.load(r)
    msg = res["message"]
    return msg["content"].strip(), len(msg.get("thinking", "")), res.get("eval_count")


def build_prompt(question, hits):
    """検索したチャンクを番号付きで並べ、最後に質問を置く。"""
    docs = "\n\n".join(f"[{i}] ({c['slug']})\n{c['text'].strip()}"
                       for i, c in enumerate(hits, 1))
    return f"資料:\n{docs}\n\n質問: {question}"


def main():
    cache, strategy, k = sys.argv[1], sys.argv[2], int(sys.argv[3])
    ids = [int(x) for x in sys.argv[4:]]
    here = os.path.dirname(os.path.abspath(__file__))
    questions = {q["id"]: q for q in json.load(open(os.path.join(here, "questions.json")))}
    chunks, vecs = rag_lab.load_index(cache, strategy)
    for qid in ids:
        q = questions[qid]
        print(f"=== Q{qid}: {q['q']}  (正解: {q['slug']})")
        if k == 0:
            messages = [{"role": "user", "content": q["q"] + "\n日本語で 3 文以内で答えてください。"}]
        else:
            qv = rag_lab.embed([q["q"]])[0]
            hits = []
            for rank, (ci, score) in enumerate(rag_lab.search(vecs, qv, k), 1):
                c = chunks[ci]
                hits.append(c)
                head = c["text"].strip().replace("\n", " ")[:40]
                print(f"  [{rank}] {score:.3f} {c['slug']:<28} {head}…")
            messages = [{"role": "system", "content": SYSTEM},
                        {"role": "user", "content": build_prompt(q["q"], hits)}]
        answer, think_chars, n_tokens = chat(messages)
        print(f"--- {LLM} (k={k}, chunks={strategy}, thinking {think_chars:,} chars, "
              f"{n_tokens:,} tokens generated)")
        print(answer)
        print()


if __name__ == "__main__":
    main()
