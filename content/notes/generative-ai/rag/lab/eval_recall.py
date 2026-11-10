"""チャンクの切り方ごとに Recall@k を測る。

正解の判定は 2 段階:
- note    : 上位 k 個に、正解のノートのチャンクが 1 つでもある
- evidence: 上位 k 個に、答えの根拠の文（questions.json の evidence）の半分以上を含むチャンクがある

使い方:
    python3 eval_recall.py <キャッシュのディレクトリ> [結果の JSON]
"""
import json
import os
import sys

import numpy as np

import rag_lab

KS = [1, 3, 5, 10]


def main():
    cache = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    here = os.path.dirname(os.path.abspath(__file__))
    questions = json.load(open(os.path.join(here, "questions.json")))
    notes = rag_lab.load_notes()
    qvecs = rag_lab.embed([q["q"] for q in questions])

    result = {}
    print(f"{len(questions)} questions, {len(notes)} notes (commit {rag_lab.COMMIT[:8]})")
    print(f"{'strategy':>8} {'chunks':>6} | " +
          " ".join(f"note@{k:<2}" for k in KS) + " | " +
          " ".join(f"evid@{k:<2}" for k in KS) + " | chars@5")
    for st in rag_lab.STRATEGIES:
        chunks, vecs = rag_lab.load_index(cache, st)
        note_hit = np.zeros((len(questions), 20), bool)
        evid_hit = np.zeros((len(questions), 20), bool)
        chars = np.zeros((len(questions), 20))
        first_evid = []
        for qi, (q, qv) in enumerate(zip(questions, qvecs)):
            p = notes[q["slug"]]["text"].index(q["evidence"])
            ev_s, ev_e = p, p + len(q["evidence"])
            rank = None
            for r, (ci, _) in enumerate(rag_lab.search(vecs, qv, 20)):
                c = chunks[ci]
                same = c["slug"] == q["slug"]
                overlap = min(c["end"], ev_e) - max(c["start"], ev_s) if same else 0
                note_hit[qi, r:] |= same
                if overlap * 2 >= ev_e - ev_s:
                    evid_hit[qi, r:] = True
                    rank = r + 1 if rank is None else rank
                chars[qi, r] = len(c["text"])
            first_evid.append(rank)
        chars = chars.cumsum(axis=1)
        result[st] = {
            "chunks": len(chunks),
            "note": note_hit.mean(axis=0).tolist(),
            "evidence": evid_hit.mean(axis=0).tolist(),
            "chars": np.median(chars, axis=0).tolist(),
            "first_evidence_rank": first_evid,
        }
        row = [note_hit[:, k - 1].mean() for k in KS] + [evid_hit[:, k - 1].mean() for k in KS]
        print(f"{st:>8} {len(chunks):>6} | " +
              " ".join(f"{v:7.2f}" for v in row[:4]) + " | " +
              " ".join(f"{v:7.2f}" for v in row[4:]) +
              f" | {int(np.median(chars[:, 4])):>6,}")
    print("\nrank of the first chunk holding the evidence (- = not in top 20)")
    print("  id " + " ".join(f"{st:>7}" for st in rag_lab.STRATEGIES))
    for qi, q in enumerate(questions):
        ranks = [result[st]["first_evidence_rank"][qi] for st in rag_lab.STRATEGIES]
        print(f"  {q['id']:>2} " + " ".join(f"{r if r else '-':>7}" for r in ranks))
    if out:
        json.dump(result, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
