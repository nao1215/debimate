"""2 つの文をつなげないと答えられない問い（2 段の参照）を、長さと 2 文の置き方を変えて答えさせる。

python3 twohop.py <pg1661.txt> <結果の JSONL>
文 A「プロジェクト X は部屋 N のチームが管理する」と文 B「部屋 N のチームの暗証番号は C」を埋め、
「X を管理するチームの暗証番号は」と問う。部屋番号と暗証番号の似た紛らわしい文も 3 つ埋める。
needle.py と同じく qwen3:8b を思考なし・temperature 0 で呼ぶ。
"""
import json
import re
import sys
import time

from needle import ask, insert, sentences

LENGTHS = [8_000, 32_000, 96_000]
PLACEMENTS = {                      # (文 A の位置, 文 B の位置)
    "near_start": (0.10, 0.12),
    "near_middle": (0.50, 0.52),
    "near_end": (0.88, 0.90),
    "far_apart": (0.10, 0.90),
}
TRIALS = [  # (プロジェクト, 部屋, 正解, 紛らわしい文)
    ("Aurora", "214", "7341", ["The team in Room 241 uses the access code 7314.",
                               "The team in Room 412 uses the access code 3417.",
                               "Project Aurelia is managed by the team in Room 241."]),
    ("Borealis", "358", "5826", ["The team in Room 385 uses the access code 5862.",
                                 "The team in Room 853 uses the access code 8256.",
                                 "Project Borneo is managed by the team in Room 385."]),
    ("Cascade", "627", "9153", ["The team in Room 672 uses the access code 9135.",
                                "The team in Room 276 uses the access code 1593.",
                                "Project Cascara is managed by the team in Room 672."]),
    ("Dynamo", "739", "2468", ["The team in Room 793 uses the access code 2486.",
                               "The team in Room 397 uses the access code 6842.",
                               "Project Dynasty is managed by the team in Room 793."]),
]
DISTRACTOR_DEPTHS = [0.3, 0.7, 0.95]


def main():
    raw = open(sys.argv[1], encoding="utf-8").read()
    start = raw.find("*** START")
    body = " ".join(raw[raw.find("\n", start) + 1:].split())
    out = open(sys.argv[2], "a", encoding="utf-8")
    for length in LENGTHS:
        hay = body[:length]
        hay = hay[:hay.rfind(". ") + 1]
        for placement, (da, db) in PLACEMENTS.items():
            for name, room, code, distractors in TRIALS:
                text = hay
                facts = [(db, f"The team in Room {room} uses the access code {code}."),
                         (da, f"Project {name} is managed by the team in Room {room}.")]
                facts += list(zip(DISTRACTOR_DEPTHS, distractors))
                for d, s in sorted(facts, reverse=True):          # 後ろから差し込む
                    text = insert(text, sentences(text), d, s)
                prompt = (text + f"\n\nQuestion: What is the access code used by the team that manages "
                          f"project {name}? Answer with the number only.")
                t = time.time()
                r = ask(prompt)
                got = re.findall(r"\d{4}", r["response"])
                rec = {"length_chars": length, "tokens": r["prompt_eval_count"], "placement": placement,
                       "project": name, "answer": code, "response": r["response"].strip(),
                       "correct": bool(got) and got[0] == code, "seconds": round(time.time() - t, 1)}
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                print(rec, flush=True)


if __name__ == "__main__":
    main()
