"""LoRA の強さだけを変えて、ComfyUI の API に同じワークフローを送る。

seed・プロンプト・sampler などは workflow_api.json のまま固定し、
LoraLoader の strength_model / strength_clip だけを書き換える。
Python 標準ライブラリだけで動く。

使い方:
    python3 run_sweep.py <保存先ディレクトリ> [sampler] [ComfyUI の URL]

sampler を省くと workflow_api.json の euler_ancestral を使う。
"""
import copy
import json
import os
import sys
import time
import urllib.parse
import urllib.request

WEIGHTS = [0.0, 0.25, 0.5, 0.75, 1.0]
HERE = os.path.dirname(os.path.abspath(__file__))


def post_json(base, path, body):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def get_json(base, path):
    with urllib.request.urlopen(base + path) as r:
        return json.load(r)


def main():
    out_dir = sys.argv[1]
    sampler = sys.argv[2] if len(sys.argv) > 2 else None
    base = sys.argv[3] if len(sys.argv) > 3 else "http://127.0.0.1:8188"
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(HERE, "workflow_api.json")) as f:
        workflow = json.load(f)

    jobs = []
    for w in WEIGHTS:
        wf = copy.deepcopy(workflow)              # workflow_api.json を読んだ dict
        wf["2"]["inputs"]["strength_model"] = w   # UNet に掛ける強さ
        wf["2"]["inputs"]["strength_clip"] = w    # text encoder に掛ける強さ
        if sampler:                               # 対照の euler の時だけ差し替える
            wf["7"]["inputs"]["sampler_name"] = sampler
        tag = sampler or wf["7"]["inputs"]["sampler_name"]
        wf["9"]["inputs"]["filename_prefix"] = f"debimate_lora/{tag}_weight_{w:.2f}"
        res = post_json(base, "/prompt", {"prompt": wf, "client_id": "debimate-lora"})
        jobs.append((w, res["prompt_id"]))        # 自分の依頼の ID だけを控える
        print(f"queued sampler={tag} weight={w:.2f} prompt_id={res['prompt_id']}")

    for w, pid in jobs:
        while True:
            hist = get_json(base, f"/history/{pid}")
            if pid in hist:
                break
            time.sleep(3)
        status = hist[pid].get("status", {})
        if status.get("status_str") != "success":
            print(f"weight={w:.2f} failed: {status}")
            sys.exit(1)
        img = hist[pid]["outputs"]["9"]["images"][0]   # ノード 9（SaveImage）の出力
        q = urllib.parse.urlencode({"filename": img["filename"],
                                    "subfolder": img["subfolder"], "type": img["type"]})
        dst = os.path.join(out_dir, f"weight_{w:.2f}.png")
        with urllib.request.urlopen(f"{base}/view?{q}") as r, open(dst, "wb") as f:
            f.write(r.read())
        msgs = status.get("messages", [])
        t0 = next((m[1]["timestamp"] for m in msgs if m[0] == "execution_start"), None)
        t1 = next((m[1]["timestamp"] for m in msgs if m[0] == "execution_success"), None)
        took = f"{(t1 - t0) / 1000:.1f}s" if t0 and t1 else "?"
        print(f"saved {dst} (weight={w:.2f}, {took})")


if __name__ == "__main__":
    main()
