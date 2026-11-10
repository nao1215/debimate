"""conditions.py の条件を、ComfyUI の API に 1 枚ずつ送って PNG を保存する。

1 枚送ったら、その prompt_id の完了を /history で待ってから次を送る。
待ち行列の他の依頼には触れない。保存済みの PNG があれば送らない（途中から再開できる）。
Python 標準ライブラリだけで動く。

使い方:
    python3 run.py <実験名: positive | negative | position | ablation> <保存先> [ComfyUI の URL]
    python3 run.py <実験名> <保存先> --again <名前> <seed>   # 同じ条件をもう一度生成して比べる
"""
import copy
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import conditions

HERE = os.path.dirname(os.path.abspath(__file__))


def post_json(base, path, body):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def get_json(base, path):
    for i in range(5):                                 # 一時的な切断は少し待って読み直す
        try:
            with urllib.request.urlopen(base + path) as r:
                return json.load(r)
        except (ConnectionError, urllib.error.URLError):
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"cannot read {path}")


def generate(base, workflow, cond, dst):
    wf = copy.deepcopy(workflow)
    wf["4"]["inputs"]["text"] = cond["positive"]
    wf["5"]["inputs"]["text"] = cond["negative"]
    wf["7"]["inputs"]["seed"] = cond["seed"]          # seed は必ず明示する
    wf["9"]["inputs"]["filename_prefix"] = "debimate_prompt_weighting/" + os.path.basename(dst)[:-4]
    pid = post_json(base, "/prompt", {"prompt": wf, "client_id": "debimate-prompt-weighting"})["prompt_id"]
    while True:                                        # 自分の prompt_id だけを待つ
        hist = get_json(base, f"/history/{pid}")
        if pid in hist:
            break
        time.sleep(2)
    status = hist[pid].get("status", {})
    if status.get("status_str") != "success":
        sys.exit(f"{dst} failed: {status}")
    img = hist[pid]["outputs"]["9"]["images"][0]
    q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img["subfolder"],
                                "type": img["type"]})
    with urllib.request.urlopen(f"{base}/view?{q}") as r:
        data = r.read()
    with open(dst, "wb") as f:
        f.write(data)
    msgs = status.get("messages", [])
    t0 = next((m[1]["timestamp"] for m in msgs if m[0] == "execution_start"), None)
    t1 = next((m[1]["timestamp"] for m in msgs if m[0] == "execution_success"), None)
    return pid, (t1 - t0) / 1000 if t0 and t1 else None, hashlib.sha256(data).hexdigest()


def main():
    exp, out_dir = sys.argv[1], sys.argv[2]
    rest = sys.argv[3:]
    base = "http://127.0.0.1:8188"
    if rest and not rest[0].startswith("--"):
        base = rest.pop(0)
    with open(os.path.join(HERE, "workflow_api.json")) as f:
        workflow = json.load(f)
    conds = conditions.EXPERIMENTS[exp]()
    d = os.path.join(out_dir, exp)
    os.makedirs(d, exist_ok=True)

    if rest[:1] == ["--again"]:                         # 再現性の確認
        name, seed = rest[1], int(rest[2])
        cond = next(c for c in conds if c["name"] == name and c["seed"] == seed)
        dst = os.path.join(d, f"again_{name}_s{seed}.png")
        pid, took, sha = generate(base, workflow, cond, dst)
        print(f"again {name} seed={seed} sha256={sha[:16]} ({took:.1f}s)")
        return

    log = open(os.path.join(d, "manifest.jsonl"), "a")
    for cond in conds:
        dst = os.path.join(d, f"{cond['name']}_s{cond['seed']}.png")
        if os.path.exists(dst):
            continue
        pid, took, sha = generate(base, workflow, cond, dst)
        print(f"{exp} {cond['name']} seed={cond['seed']} {took:.1f}s prompt_id={pid}", flush=True)
        log.write(json.dumps({**cond, "prompt_id": pid, "seconds": took, "sha256": sha}) + "\n")
        log.flush()


if __name__ == "__main__":
    main()
