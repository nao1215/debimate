"""同じ文面と seed で、深度マップ（人形の体型 × 服の厚み）と強さだけを変えて 1 枚ずつ描く。

使い方: python3 run_depth.py <深度マップのディレクトリ> <PNG の保存先> <計画の名前>
  計画: compare（文面だけ、と 2 体 × 服の厚みなし・あり × 2 ポーズを強さ 0.7 で、各 2 seed）
        sweep（正面のポーズで、4 つの人形を強さ 0.4 と 1.0 で、各 2 seed）
        loose（ゆったりした服の文面で、文面だけと 4 つの人形の正面を強さ 0.7 で、各 2 seed）
ログは <PNG の保存先>/log_<計画>.json に足していく（prompt_id・実行秒数・送る直前の負荷）。
Python 標準ライブラリだけで動く。
"""
import json
import os
import sys

import comfy

CKPT = "waiIllustriousSDXL_v170.safetensors"
UNION = "xinsir_union_promax_sdxl.safetensors"
PROMPT = ("masterpiece, best quality, 1girl, solo, adult woman, long brown hair, ponytail, knight, "
          "silver plate armor, breastplate, pauldrons, gauntlets, armored boots, dark trousers, "
          "standing, full body, simple background, white background")
NEG = ("lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, signature, watermark, logo, "
       "nsfw, nude, child, multiple girls, multiple views")
# loose の計画の文面: 体から離れる服を頼む
LOOSE = ("masterpiece, best quality, 1girl, solo, adult woman, long brown hair, ponytail, "
         "oversized grey hoodie, baggy cargo pants, white sneakers, standing, full body, simple background, "
         "white background")
SEEDS = [20261112, 20261113]
DOLLS = [f"{d}_{k}" for d in ("real", "anime") for k in ("plain", "bulk")]


def workflow(seed, control=None, prompt=PROMPT):
    """control = None（文面だけ）か {"image", "strength", "end"}。union の depth を使う。"""
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPSetLastLayer", "inputs": {"clip": ["1", 1], "stop_at_clip_layer": -2}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
            "seed": seed, "steps": 28, "cfg": 5.5, "sampler_name": "euler_ancestral", "scheduler": "normal",
            "denoise": 1.0}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "debimate_depth_body/out"}},
    }
    if control:
        wf["10"] = {"class_type": "LoadImage", "inputs": {"image": control["image"]}}
        wf["11"] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": UNION}}
        wf["12"] = {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["11", 0], "type": "depth"}}
        wf["13"] = {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["3", 0], "negative": ["4", 0], "control_net": ["12", 0], "image": ["10", 0],
            "strength": control["strength"], "start_percent": 0.0, "end_percent": control["end"],
            "vae": ["1", 2]}}
        wf["6"]["inputs"]["positive"], wf["6"]["inputs"]["negative"] = ["13", 0], ["13", 1]
    return wf


def plan(name):
    """(出力名, seed, 条件) の列。条件の image は深度マップのファイル名。"""
    jobs = []
    if name == "compare":
        for seed in SEEDS:
            jobs.append((f"text_{seed}", seed, None))
            for pose in ("front", "turn"):
                for doll in DOLLS:
                    jobs.append((f"{doll}_{pose}_s070_{seed}", seed,
                                 dict(image=f"{doll}_{pose}.png", strength=0.7, end=0.6)))
    elif name == "sweep":
        for seed in SEEDS:
            for doll in DOLLS:
                for s in (0.4, 1.0):
                    jobs.append((f"{doll}_front_s{int(s * 100):03d}_{seed}", seed,
                                 dict(image=f"{doll}_front.png", strength=s, end=0.6)))
    elif name == "loose":
        for seed in SEEDS:
            jobs.append((f"loose_text_{seed}", seed, None))
            for doll in DOLLS:
                jobs.append((f"loose_{doll}_front_s070_{seed}", seed,
                             dict(image=f"{doll}_front.png", strength=0.7, end=0.6)))
    return jobs


def main():
    cond_dir, out, name = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    log_path = os.path.join(out, f"log_{name}.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else {}
    uploaded = {}
    for tag, seed, control in plan(name):
        png = os.path.join(out, tag + ".png")
        if os.path.exists(png):
            continue
        if control:
            img = control["image"]
            if img not in uploaded:
                uploaded[img] = comfy.upload(os.path.join(cond_dir, img))
            control = dict(control, image=uploaded[img])
        r = comfy.run(workflow(seed, control, LOOSE if name == "loose" else PROMPT), png, "8")
        log[tag] = dict(r, seed=seed, control=control)
        json.dump(log, open(log_path, "w"), indent=1)
        print(tag, r["seconds"], "s", flush=True)


if __name__ == "__main__":
    main()
