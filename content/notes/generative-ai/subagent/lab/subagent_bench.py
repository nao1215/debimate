"""1 つのコンテキストに全資料を積む方式と、資料ごとに子に抽出させる方式を比べる。

python3 -I subagent_bench.py <Gutenberg の txt があるディレクトリ> <結果の JSONL>

ollama（http://localhost:11434）の qwen3:8b を、思考なし・temperature 0・seed 1 で呼ぶ。
資料は Project Gutenberg のパブリックドメインの 6 冊から 14,000 字ずつ切り出し、
支店ごとの在庫の数（正解 1 文）と、紛らわしい数（予測・前月の 2 文）を埋めたもの。

方式は 3 つ。
  single      親が全資料を read_file で読んだ形にして、ツールの結果を全部積んだまま答える
  sub_brief   子が資料を 1 つずつ読み、親の指示（支店名・品目・10 月の実績）に沿って 1 行を返す
  sub_vague   子に「要約して」とだけ頼み、親はその要約だけで答える（情報が落ちる例）
"""
import json
import re
import sys
import time
import urllib.request
import uuid

MODEL = "qwen3:8b"
OPTIONS = {"num_ctx": 32768, "temperature": 0, "seed": 1}
BOOKS = ["pg1661", "pg84", "pg1342", "pg11", "pg2701", "pg98"]
BRANCHES = ["Harbor", "Ridge", "Mill", "Orchard", "Station", "Bridge"]
DOC_CHARS = 14_000
FACT_SETS = [  # (品目, 6 支店の 10 月の実績)
    ("tea", [412, 275, 638, 153, 509, 347]),
    ("salt", [286, 734, 195, 462, 821, 359]),
    ("copper", [571, 248, 916, 383, 127, 694]),
    ("wool", [339, 862, 417, 705, 264, 158]),
]
DOC_COUNTS = [1, 2, 4, 6]


def body_of(path):
    raw = open(path, encoding="utf-8").read()
    start = raw.find("*** START")
    return " ".join(raw[raw.find("\n", start) + 1:].split())


def insert(text, depth, s):
    """depth（0〜1）に最も近い文の切れ目に s を差し込む。"""
    cuts = [m.end() for m in re.finditer(r"\. ", text)]
    pos = min(cuts, key=lambda c: abs(c - depth * len(text)))
    return text[:pos] + s + " " + text[pos:]


def make_doc(body, branch, item, n):
    text = body[len(body) // 3:]
    text = text[text.find(". ") + 2:][:DOC_CHARS]           # 文の頭から始め、文の終わりで切る
    text = text[:text.rfind(". ") + 1]
    facts = [  # 後ろの位置から差し込み、前の位置をずらさない
        (0.8, f"Planning memo: the {branch} branch had forecast {n + 90} crates of {item} for October."),
        (0.55, f"Inventory note: the {branch} branch reported {n} crates of {item} in October."),
        (0.3, f"Inventory note: the {branch} branch reported {n - 60} crates of {item} in September."),
    ]
    for depth, s in facts:
        text = insert(text, depth, s)
    return f"Archive of the {branch} branch (excerpt of old papers kept in the branch).\n\n{text}"


def chat(messages):
    # 先頭に毎回別の ID を入れて、前の呼び出しのプロンプトキャッシュを使わせない
    messages = [{"role": "system", "content": f"Request id: {uuid.uuid4()}\n" + messages[0]["content"]}] + messages[1:]
    body = {"model": MODEL, "messages": messages, "stream": False, "think": False, "options": OPTIONS}
    req = urllib.request.Request("http://localhost:11434/api/chat", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    t = time.time()
    r = json.load(urllib.request.urlopen(req, timeout=3600))
    return {"text": r["message"]["content"].strip(), "prompt": r["prompt_eval_count"],
            "output": r["eval_count"], "sec": time.time() - t}


PARENT_SYSTEM = "You are a research agent. Use the tool results in this conversation to answer."


def question(item, branches):
    return (f"Each file is the archive of one branch: {', '.join(branches)}. "
            f"For each branch, how many crates of {item} did it report for October "
            "(the actual report, not a forecast)? Answer one line per branch in the form "
            f"'{branches[0]}: 123' (branch name, colon, number), then a last line 'Total: number'.")


def tool_turns(name, contents):
    """親が name のツールを資料の数だけ呼び、結果を受け取った形の会話を作る。"""
    calls = [{"function": {"name": name, "arguments": {"path": f"{b.lower()}.txt"}}}
             for b, _ in contents]
    msgs = [{"role": "assistant", "content": "", "tool_calls": calls}]
    msgs += [{"role": "tool", "content": c} for _, c in contents]
    return msgs


def child_brief(branch, item):
    return (f"You are a subagent. The parent agent needs one number from the file below: "
            f"the number of crates of {item} that the {branch} branch actually reported for "
            "October. Ignore forecasts and other months. Reply with exactly one line "
            f"'{branch}: <number>', or '{branch}: not found'.")


CHILD_VAGUE = "You are a subagent. Summarize the file below in 3 sentences."


def run(item, nums, books, k):
    branches = BRANCHES[:k]
    docs = [(b, make_doc(books[i], b, item, nums[i])) for i, b in enumerate(branches)]
    q = question(item, branches)
    out = {}
    # single: 全資料を親のコンテキストに積む
    r = chat([{"role": "system", "content": PARENT_SYSTEM}, {"role": "user", "content": q}]
             + tool_turns("read_file", docs))
    out["single"] = {"answer": r["text"], "parent_prompt": r["prompt"],
                     "total": r["prompt"] + r["output"], "sec": r["sec"], "children": []}
    # sub_brief / sub_vague: 子が 1 つずつ読み、親には子の返事だけが戻る
    for mode in ["sub_brief", "sub_vague"]:
        kids = []
        for b, d in docs:
            sys_msg = child_brief(b, item) if mode == "sub_brief" else CHILD_VAGUE
            kids.append(chat([{"role": "system", "content": sys_msg},
                              {"role": "user", "content": f"File {b.lower()}.txt:\n\n{d}"}]))
        r = chat([{"role": "system", "content": PARENT_SYSTEM}, {"role": "user", "content": q}]
                 + tool_turns("delegate", [(b, c["text"]) for (b, _), c in zip(docs, kids)]))
        out[mode] = {"answer": r["text"], "parent_prompt": r["prompt"],
                     "total": r["prompt"] + r["output"] + sum(c["prompt"] + c["output"] for c in kids),
                     "sec": r["sec"] + sum(c["sec"] for c in kids),
                     "children": [c["text"] for c in kids]}
    for mode, rec in out.items():
        got = dict(re.findall(r"(\w+)\s*:\s*(\d+)", rec["answer"]))
        rec["correct"] = sum(got.get(b) == str(n) for b, n in zip(branches, nums))
        rec["total_ok"] = got.get("Total") == str(sum(nums[:k]))
        rec.update({"mode": mode, "item": item, "k": k, "truth": nums[:k]})
    return out


def main():
    books = [body_of(f"{sys.argv[1]}/{b}.txt") for b in BOOKS]
    f = open(sys.argv[2], "a", encoding="utf-8")
    for k in DOC_COUNTS:
        for item, nums in FACT_SETS:
            for rec in run(item, nums, books, k).values():
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                print(rec["k"], rec["item"], rec["mode"], rec["correct"], rec["total_ok"],
                      rec["parent_prompt"], rec["total"], round(rec["sec"], 1), flush=True)


if __name__ == "__main__":
    main()
