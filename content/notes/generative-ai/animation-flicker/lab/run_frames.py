"""腕を上げる 4 コマを、描き直す 2 通りと並べて 1 枚の、計 3 通りで描く。

使い方: python3 run_frames.py <render_frames.py の出力先> <PNG の保存先> <計画の名前>
  計画: redraw （1 コマずつプロンプトから描く。4 コマ × 各 seed。深度マップは強さ 0.7・end 0.6）
        img2img（redraw の 1 コマ目を元に、1〜4 コマ目をそれぞれの深度マップで弱く描き直す。denoise 0.45、
                 深度マップは強さ 0.8・end 0.8。どのコマも元の 1 コマ目から描き、前のコマを順につながない）
        img2img60、img2img75（img2img の denoise を 0.6、0.75 にしたもの）
        sheet  （4 コマの深度マップを横に並べた 1 枚を描く。1536 x 768、各 seed）
ログは <PNG の保存先>/log_<計画>.json に足していく（prompt_id・実行秒数・送る直前の負荷）。
Python 標準ライブラリと Pillow で動く（Pillow は並べた深度マップを作る時だけ使う）。
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
# 並べた 1 枚: 同じ人を 4 人描くので、1 人・複数の絵を打ち消す語を外し、同じ服と髪を頼む
SHEET_PROMPT = PROMPT.replace("1girl, solo, ", "multiple views, four views of the same woman, same outfit, "
                              "same hairstyle, ")
SHEET_NEG = NEG.replace(", multiple girls, multiple views", "")
SEEDS = [20261112, 20261113, 20261114]
FRAMES = ["f0", "f1", "f2", "f3"]


def workflow(seed, depth, strength, end, size, prompt=PROMPT, neg=NEG, source=None, denoise=1.0):
    """depth は ComfyUI に置いた深度マップの名前。source があれば、その絵から描き直す（img2img）。"""
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPSetLastLayer", "inputs": {"clip": ["1", 1], "stop_at_clip_layer": -2}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": neg}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["13", 0], "negative": ["13", 1], "latent_image": ["5", 0],
            "seed": seed, "steps": 28, "cfg": 5.5, "sampler_name": "euler_ancestral", "scheduler": "normal",
            "denoise": denoise}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "debimate_flicker/out"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": depth}},
        "11": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": UNION}},
        "12": {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["11", 0], "type": "depth"}},
        "13": {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["3", 0], "negative": ["4", 0], "control_net": ["12", 0], "image": ["10", 0],
            "strength": strength, "start_percent": 0.0, "end_percent": end, "vae": ["1", 2]}},
    }
    if source:
        wf["20"] = {"class_type": "LoadImage", "inputs": {"image": source}}
        wf["5"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["20", 0], "vae": ["1", 2]}}
    else:
        wf["5"] = {"class_type": "EmptyLatentImage", "inputs": {"width": size[0], "height": size[1], "batch_size": 1}}
    return wf


def sheet_depth(passes):
    """4 コマの小さい深度マップを横に並べた 1 枚を作る。"""
    from PIL import Image
    cells = [Image.open(os.path.join(passes, f"cell_{f}.png")).convert("RGB") for f in FRAMES]
    w, h = cells[0].size
    sheet = Image.new("RGB", (w * len(cells), h))
    for i, c in enumerate(cells):
        sheet.paste(c, (w * i, 0))
    path = os.path.join(passes, "sheet_depth.png")
    sheet.save(path)
    return path


def main():
    passes, out, plan = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    log_path = os.path.join(out, f"log_{plan}.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else {}
    for seed in SEEDS:
        if plan == "sheet":
            jobs = [(f"sheet_{seed}", dict(depth=comfy.upload(sheet_depth(passes)), strength=0.7, end=0.6,
                                           size=(1536, 768), prompt=SHEET_PROMPT, neg=SHEET_NEG))]
        elif plan == "redraw":
            jobs = [(f"redraw_{f}_{seed}", dict(depth=comfy.upload(os.path.join(passes, f"depth_{f}.png")),
                                                strength=0.7, end=0.6, size=(832, 1216))) for f in FRAMES]
        elif plan.startswith("img2img"):
            denoise = int(plan[7:]) / 100 if plan[7:] else 0.45
            src = comfy.upload(os.path.join(out, f"redraw_f0_{seed}.png"))
            jobs = [(f"{plan}_{f}_{seed}", dict(depth=comfy.upload(os.path.join(passes, f"depth_{f}.png")),
                                                 strength=0.8, end=0.8, size=(832, 1216), source=src,
                                                 denoise=denoise)) for f in FRAMES]
        for name, kw in jobs:
            png = os.path.join(out, name + ".png")
            if os.path.exists(png):
                continue
            log[name] = comfy.run(workflow(seed, **kw), png, "8")
            json.dump(log, open(log_path, "w"), indent=1)
            print(name, log[name]["seconds"], flush=True)


if __name__ == "__main__":
    main()
