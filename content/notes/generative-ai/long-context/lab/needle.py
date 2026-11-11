"""長い文章の途中に 1 文（針）を埋め、位置・長さ・紛らわしい文の有無を変えて答えさせる。

python3 needle.py <pg1661.txt> <結果の JSONL>
ollama（http://localhost:11434）で qwen3:8b を、思考なし・temperature 0 で呼ぶ。
干し草は Project Gutenberg の The Adventures of Sherlock Holmes（pg1661）の本文。
"""
import json
import re
import sys
import time
import urllib.request

MODEL = "qwen3:8b"
LENGTHS = [8_000, 32_000, 96_000]          # 文字数。英文なのでおよそ 2K / 8K / 24K トークン
DEPTHS = [0.0, 0.25, 0.5, 0.75, 1.0]       # 針を置く位置（0 が先頭、1 が末尾）
TRIALS = [                                 # (プロジェクト名, 正解, 紛らわしい文 3 つ)
    ("Aurora", "7341", ["The secret code for project Aurelia is 7314.",
                        "The old secret code for project Aurora, retired last year, was 7431.",
                        "The secret code for project Aurore is 1347."]),
    ("Borealis", "5826", ["The secret code for project Borneo is 5862.",
                          "The old secret code for project Borealis, retired last year, was 8526.",
                          "The secret code for project Boreal is 2658."]),
    ("Cascade", "9153", ["The secret code for project Cascara is 9135.",
                         "The old secret code for project Cascade, retired last year, was 1953.",
                         "The secret code for project Arcade is 3159."]),
    ("Dynamo", "2468", ["The secret code for project Dynasty is 2486.",
                        "The old secret code for project Dynamo, retired last year, was 4268.",
                        "The secret code for project Dinamo is 8642."]),
]
DISTRACTOR_DEPTHS = [0.1, 0.4, 0.85]


def sentences(text):
    """文の切れ目（ピリオドと空白）の位置の一覧。"""
    return [m.end() for m in re.finditer(r"\. ", text)]


def insert(text, cuts, depth, s):
    """depth に最も近い文の切れ目に s を差し込む。"""
    if depth <= 0:
        return s + " " + text
    if depth >= 1:
        return text + " " + s
    pos = min(cuts, key=lambda c: abs(c - depth * len(text)))
    return text[:pos] + s + " " + text[pos:]


def ask(prompt):
    body = {"model": MODEL, "prompt": prompt, "stream": False, "think": False,
            "options": {"num_ctx": 32768, "temperature": 0, "seed": 1, "num_predict": 16}}
    req = urllib.request.Request("http://localhost:11434/api/generate", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=1800))


def main():
    raw = open(sys.argv[1], encoding="utf-8").read()
    start = raw.find("*** START")
    body = " ".join(raw[raw.find("\n", start) + 1:].split())   # 改行をまとめて 1 行の本文にする
    out = open(sys.argv[2], "a", encoding="utf-8")
    for length in LENGTHS:
        hay = body[:length]
        hay = hay[:hay.rfind(". ") + 1]
        for depth in DEPTHS:
            for name, code, distractors in TRIALS:
                for cond in ["needle_only", "with_distractors"]:
                    text = hay
                    if cond == "with_distractors":       # 後ろから差し込み、前の位置をずらさない
                        for d, s in sorted(zip(DISTRACTOR_DEPTHS, distractors), reverse=True):
                            text = insert(text, sentences(text), d, s)
                    text = insert(text, sentences(text), depth,
                                  f"The secret code for project {name} is {code}.")
                    prompt = (text + f"\n\nQuestion: What is the current secret code for project {name}? "
                              "Answer with the number only.")
                    t = time.time()
                    r = ask(prompt)
                    got = re.findall(r"\d{4}", r["response"])
                    rec = {"length_chars": length, "tokens": r["prompt_eval_count"], "depth": depth,
                           "project": name, "cond": cond, "answer": code,
                           "response": r["response"].strip(), "correct": bool(got) and got[0] == code,
                           "seconds": round(time.time() - t, 1)}
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    out.flush()
                    print(rec, flush=True)


if __name__ == "__main__":
    main()
