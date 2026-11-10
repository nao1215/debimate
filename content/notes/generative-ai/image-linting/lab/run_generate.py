"""検品の実験に使う画像を ComfyUI の API で 1 枚ずつ生成する。

designs.json の 4 つの服装（A〜D）× 条件 3 種（plain / neon / pose）× seed 6 個 = 72 枚と、
服装ごとの基準の絵（plain、reference_seed）4 枚を作る。
依頼は 1 枚ずつ送り、自分が送った prompt_id の完了だけを待つ。
待ち行列の削除や中断（/queue の clear、/interrupt）は使わない。
保存先に同じ名前の PNG があれば送らない（途中から再開できる）。
Python 標準ライブラリだけで動く。

使い方:
    python3 run_generate.py <PNG の保存先> [--only 名前,名前] [--suffix _again] [ComfyUI の URL]
"""
import copy
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CLIENT_ID = "debimate-image-linting"


def post_json(base, path, body):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def get_json(base, path):
    with urllib.request.urlopen(base + path) as r:
        return json.load(r)


def build_jobs(spec):
    """(名前, プロンプト, seed) の一覧。名前は A_plain_20261110 の形。"""
    jobs = []
    for key, d in spec["designs"].items():
        def prompt(cond):
            return ", ".join([d["subject"], spec["common"], d["outfit"],
                              spec["conditions"][cond]])
        jobs.append((f"{key}_ref_{spec['reference_seed']}", prompt("plain"),
                     spec["reference_seed"]))
        for cond in spec["conditions"]:
            for seed in spec["seeds"]:
                jobs.append((f"{key}_{cond}_{seed}", prompt(cond), seed))
    return jobs


def generate(base, workflow, name, text, seed, dst):
    wf = copy.deepcopy(workflow)
    wf["4"]["inputs"]["text"] = text
    wf["7"]["inputs"]["seed"] = seed            # seed は必ず明示する
    wf["9"]["inputs"]["filename_prefix"] = f"debimate_image_linting/{name}"
    pid = post_json(base, "/prompt", {"prompt": wf, "client_id": CLIENT_ID})["prompt_id"]
    t0 = time.time()
    while True:                                 # 自分の prompt_id だけを見る
        hist = get_json(base, f"/history/{pid}")
        if pid in hist:
            break
        time.sleep(2)
    status = hist[pid].get("status", {})
    if status.get("status_str") != "success":
        raise RuntimeError(f"{name} failed: {status}")
    img = hist[pid]["outputs"]["9"]["images"][0]
    q = urllib.parse.urlencode({"filename": img["filename"],
                                "subfolder": img["subfolder"], "type": img["type"]})
    with urllib.request.urlopen(f"{base}/view?{q}") as r, open(dst, "wb") as f:
        f.write(r.read())
    return pid, time.time() - t0


def main():
    args = sys.argv[1:]
    out_dir = args.pop(0)
    only, suffix, base = None, "", "http://127.0.0.1:8188"
    while args:
        a = args.pop(0)
        if a == "--only":
            only = set(args.pop(0).split(","))
        elif a == "--suffix":
            suffix = args.pop(0)
        else:
            base = a
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(HERE, "workflow_api.json")) as f:
        workflow = json.load(f)
    with open(os.path.join(HERE, "designs.json")) as f:
        spec = json.load(f)

    for name, text, seed in build_jobs(spec):
        if only and name not in only:
            continue
        dst = os.path.join(out_dir, f"{name}{suffix}.png")
        if os.path.exists(dst):
            continue
        pid, sec = generate(base, workflow, name, text, seed, dst)
        print(f"{name}{suffix} seed={seed} prompt_id={pid} {sec:.1f}s", flush=True)


if __name__ == "__main__":
    main()
