# 決済サービス（架空）が v2 で status に REVIEW（不正検知の審査中）を足した時と、
# v3 で status を payment_status に改名した時に、3 つの版の 4 か所が何をするかを数える。
import ast
import logging
import sys
import traceback

import acl
import no_acl

logging.basicConfig(format="  ログ: %(message)s", stream=sys.stdout, level=logging.WARNING)

PLACES = ["shipping", "mail", "sales", "stock"]
LABEL = {"shipping": "出荷", "mail": "メール", "sales": "売上", "stock": "在庫"}
# REVIEW の正しい扱い: 審査が終わるまで、決まっていない支払いとして扱う
EXPECTED = {"shipping": "出荷を待つ", "mail": "送らない", "sales": "計上しない", "stock": "引当を保つ"}


def version_a(p):  # 4 か所が生の値を読む
    return [getattr(no_acl, f)(p) for f in PLACES]


def version_b(p):  # 1 回だけ翻訳し、4 か所は翻訳した語を読む
    s = acl.translate_with_fallback(p)
    return [getattr(acl, f)(s) for f in PLACES]


def version_c(p):
    s = acl.translate(p)
    return [getattr(acl, f)(s) for f in PLACES]


VERSIONS = {"A: ACL なし": version_a,
            "B: ACL（知らない値は入金待ち）": version_b,
            "C: ACL（知らない値は確認中）": version_c}

# 1. v1 の値では 3 つの版が同じ動きをする（書き換えで振る舞いを変えていない）
v1 = {}
for st in ["PAID", "PENDING", "FAILED"]:
    p = {"payment_id": "pay_v1", "status": st, "amount": 3980}
    rows = {name: run(p) for name, run in VERSIONS.items()}
    assert len({tuple(r) for r in rows.values()}) == 1, rows
    v1[st] = rows["A: ACL なし"]
print("v1 の 3 つの値（PAID・PENDING・FAILED）では、3 つの版の 4 か所が全て同じ動き")

# 2. v2: status に REVIEW が増えた
print("\n== v2: status=REVIEW の支払いが 1 件届いた")
review = {"payment_id": "pay_0042", "status": "REVIEW", "amount": 3980}
for name, run in VERSIONS.items():
    print(name)
    got = run(review)
    for i, f in enumerate(PLACES):
        like = "・".join(st for st in v1 if v1[st][i] == got[i])
        like = f"v1 の {like} と同じ扱い" if like else "v1 のどの値とも違う扱い"
        mark = "" if got[i] == EXPECTED[f] else f"  ← 誤り（正しくは {EXPECTED[f]}）"
        print(f"  {LABEL[f]:　<3} {got[i]:　<8} {like}{mark}")
    print(f"  誤り {sum(g != EXPECTED[f] for g, f in zip(got, PLACES))}/4 か所、例外 0 件")

# 3. v3: status が payment_status に改名された
print("\n== v3: status が payment_status に改名された")
renamed = {"payment_id": "pay_0043", "payment_status": "PAID", "amount": 3980}
for name, run in VERSIONS.items():
    where = set()
    try:
        run(renamed)
    except KeyError:
        where.add(traceback.extract_tb(sys.exc_info()[2])[-1].name)
    # A は最初の 1 か所で止まるので、4 か所を 1 つずつ呼んで数え直す
    if name.startswith("A"):
        for f in PLACES:
            try:
                getattr(no_acl, f)(renamed)
            except KeyError:
                where.add(f)
    print(f"{name}: KeyError を出した関数 {len(where)} 個（{', '.join(sorted(where))}）")

# 4. 上流の項目名 "status" を読む関数
print('\n== 上流の項目名 "status" を読む関数')
for path in ["no_acl.py", "acl.py"]:
    tree = ast.parse(open(path, encoding="utf-8").read())
    funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
             and any(isinstance(c, ast.Constant) and c.value == "status" for c in ast.walk(n))]
    print(f"{path}: {len(funcs)} 個（{', '.join(funcs)}）")
