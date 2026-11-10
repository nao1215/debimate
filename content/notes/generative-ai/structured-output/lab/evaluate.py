"""run.py の結果（JSON Lines）を、パース・スキーマ・値の 3 段で採点し、時間をまとめる。

使い方:
    uv run --with jsonschema==4.25.1 python3 evaluate.py <結果の .jsonl>... [集計の .json]
"""
import json
import statistics
import sys
from collections import defaultdict

import jsonschema

from run import N_ITEMS, SCHEMA, TIMING_ITEMS
from texts import make_items

METHODS = ["prompt", "json", "schema", "schema_bare"]


def score(content, answer):
    """3 段の判定。前の段を通らなければ後の段は False。"""
    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        return {"parse": False, "schema": False, "value": False, "fields": {}}
    ok_schema = jsonschema.Draft202012Validator(SCHEMA).is_valid(obj)
    fields = {k: ok_schema and obj.get(k) == v for k, v in answer.items()}
    return {"parse": True, "schema": ok_schema, "value": all(fields.values()),
            "fields": fields}


def fenced(content):
    """```json ... ``` で囲まれていて、囲みを外せばパースできるか。"""
    t = content.strip()
    if not t.startswith("```"):
        return False
    t = t.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        json.loads(t)
        return True
    except json.JSONDecodeError:
        return False


def main():
    paths = [a for a in sys.argv[1:] if a.endswith(".jsonl")]
    outs = [a for a in sys.argv[1:] if a.endswith(".json")]
    out_path = outs[0] if outs else None
    answers = {it["id"]: it["answer"] for it in make_items(N_ITEMS)}
    rows = [json.loads(line) for path in paths for line in open(path)]
    models = list(dict.fromkeys(r["model"] for r in rows))
    summary = {}
    for model in models:
        print(f"[{model}]")
        print(f"  {'method':<11} {'fence':>5} {'parse':>6} {'schema':>7} {'value':>6}"
              f" {'person':>7} {'date':>5} {'amount':>7}  {'tokens':>6} {'sec/call':>8}"
              f"  {'tok/s':>5}  {'rep spread':>10}  same")
        summary[model] = {}
        for method in METHODS:
            rs = [r for r in rows if r["model"] == model and r["method"] == method]
            if not rs:
                continue
            first = [r for r in rs if r["rep"] == 0]
            n = len(first)
            sc = [score(r["content"], answers[r["id"]]) for r in first]
            cnt = {k: sum(s[k] for s in sc) for k in ("parse", "schema", "value")}
            cnt["fenced"] = sum(fenced(r["content"]) for r in first)
            fld = {k: sum(s["fields"].get(k, False) for s in sc)
                   for k in ("person", "date", "amount_yen")}
            # 時間: 他のモデルとの入れ替えで毎回読み込みが入るので、total_duration ではなく
            # プロンプトの処理と生成の時間（prompt_eval + eval）を使う。
            # 繰り返しごとに 1 呼び出しの中央値を出し、その中央値と幅を見る
            # 繰り返したのは先頭の TIMING_ITEMS 件だけなので、時間はその件数で比べる
            timed = [r for r in rs if r["id"] < TIMING_ITEMS]
            per_rep = defaultdict(list)
            for r in timed:
                per_rep[r["rep"]].append(r)
            med = [statistics.median(x["prompt_eval_s"] + x["eval_s"] for x in v)
                   for v in per_rep.values()]
            tps = statistics.median(r["eval_count"] / r["eval_s"] for r in timed if r["eval_s"])
            toks = statistics.median(r["eval_count"] for r in first)
            # 繰り返した入力のうち、応答の文字列が全ての回で同じだった件数
            by_id = defaultdict(set)
            for r in timed:
                by_id[r["id"]].add(r["content"])
            same = sum(len(v) == 1 for v in by_id.values())
            n_timed = len(by_id)
            spread = f"{min(med):.2f}-{max(med):.2f}" if len(med) > 1 else "-"
            same_s = f"{same}/{n_timed}" if len(med) > 1 else "-"
            print(f"  {method:<11} {cnt['fenced']:>5} {cnt['parse']:>3}/{n} {cnt['schema']:>4}/{n} {cnt['value']:>3}/{n}"
                  f" {fld['person']:>7} {fld['date']:>5} {fld['amount_yen']:>7}  {toks:>6.0f}"
                  f" {statistics.median(med):>8.2f}  {tps:>5.1f}  {spread:>10}  {same_s}")
            summary[model][method] = {"n": n, **cnt, **fld, "tokens": toks,
                                      "sec_median": statistics.median(med),
                                      "sec_reps": med, "tok_per_s": tps, "same": same, "n_timed": n_timed,
                                      "length_stop": sum(r["done_reason"] == "length" for r in first)}
        print()
    if out_path:
        with open(out_path, "w") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
