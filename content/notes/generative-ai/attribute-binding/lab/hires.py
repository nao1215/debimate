"""代表として大きく載せる絵だけを仕上げる（1.5 倍に拡大して全体を描き直す）。

測定に使う絵は生成のままで、この仕上げは本文に大きく載せる 2 枚にだけ使う。
生成と同じ条件（プロンプト・LoRA・seed）で、1.5 倍に拡大した画像を denoise 0.4・20 ステップで
img2img する。ComfyUI に 1 枚ずつ送り、自分の prompt_id だけを待つ。Pillow を使う。

使い方:
    STYLE_LORA=... STYLE_TRIGGER=... python3 hires.py <PNG の保存先> <条件名> <seed>

結果は <PNG の保存先>/hires/<条件名>_<seed>.png。
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid

from PIL import Image

import gen

SCALE, DENOISE, STEPS = 1.5, 0.4, 20
BASE = "http://127.0.0.1:8188"


def upload(img):
    """画像を ComfyUI の input に送り、LoadImage で使う名前を返す。"""
    name = f"debimate-binding-{uuid.uuid4().hex[:12]}.png"
    buf = io.BytesIO()
    img.save(buf, "PNG")
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; "
            f"filename=\"{name}\"\r\nContent-Type: image/png\r\n\r\n").encode() + \
        buf.getvalue() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(BASE + "/upload/image", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)["name"]


def main():
    src, cond_name, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    with open(os.path.join(gen.HERE, "workflow_api.json")) as f:
        workflow = json.load(f)
    img = Image.open(os.path.join(src, cond_name, f"{seed}.png")).convert("RGB")
    big = img.resize((int(img.width * SCALE) // 8 * 8, int(img.height * SCALE) // 8 * 8),
                     Image.LANCZOS)

    wf = gen.build(workflow, gen.CONDITIONS[cond_name], seed, "debimate_binding/hires")
    wf["20"] = {"class_type": "LoadImage", "inputs": {"image": upload(big)}}
    wf["21"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["20", 0], "vae": ["1", 2]}}
    wf["7"]["inputs"].update(latent_image=["21", 0], denoise=DENOISE, steps=STEPS)
    del wf["6"]
    pid = gen.post_json(BASE, "/prompt", {"prompt": wf, "client_id": "debimate-binding"})["prompt_id"]
    while True:                                  # 自分の prompt_id だけを待つ
        hist = gen.get_json(BASE, f"/history/{pid}")
        if pid in hist:
            break
        time.sleep(3)
    if hist[pid].get("status", {}).get("status_str") != "success":
        sys.exit(f"failed: {hist[pid].get('status')}")
    out = hist[pid]["outputs"]["9"]["images"][0]
    q = urllib.parse.urlencode({"filename": out["filename"], "subfolder": out["subfolder"],
                                "type": out["type"]})
    os.makedirs(os.path.join(src, "hires"), exist_ok=True)
    dst = os.path.join(src, "hires", f"{cond_name}_{seed}.png")
    with urllib.request.urlopen(f"{BASE}/view?{q}") as r:
        Image.open(io.BytesIO(r.read())).convert("RGB").save(dst)   # メタデータは書かない
    print(f"{dst} {big.size}")


if __name__ == "__main__":
    main()
