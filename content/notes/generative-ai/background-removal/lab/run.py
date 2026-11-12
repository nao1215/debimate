"""背景の色と髪の色を変えて立ち絵を描き、ComfyUI の背景除去のノードでマスクを作る。

使い方: python3 run.py <深度マップの PNG> <PNG の保存先> gen    背景（白・灰・緑）× 髪（茶・銀）× seed を描く
        python3 run.py <深度マップの PNG> <PNG の保存先> node   描いた絵を RemoveBackground に通し、マスクを保存する
        python3 run.py <深度マップの PNG> <PNG の保存先> rgba   緑の背景で描いた 1 枚（green_brown_20261115）の透過 PNG を作る
描き方: 深度マップ（union depth、強さ 0.7、end 0.6）でプロンプトから描く（txt2img）。LoRA は使わない。
マスク: LoadBackgroundRemovalModel（birefnet.safetensors）→ RemoveBackground → MaskToImage → SaveImage。
        RemoveBackground のマスクは人物が 1。透過 PNG にする時は InvertMask を挟んで JoinImageWithAlpha に渡す
        （JoinImageWithAlpha は 1 − マスク を透明度にする）。
ログは <PNG の保存先>/log_<計画>.json に足していく（prompt_id・実行秒数・送る直前の負荷）。
Python 標準ライブラリだけで動く。
"""
import json
import os
import sys

import comfyapi as comfy

CKPT = "waiIllustriousSDXL_v170.safetensors"
UNION = "xinsir_union_promax_sdxl.safetensors"
BIREFNET = "birefnet.safetensors"
BACKS = {"white": "white background", "grey": "grey background", "green": "green background"}
HAIRS = {"brown": "brown hair", "silver": "silver hair"}
PROMPT = ("masterpiece, best quality, 1girl, solo, adult woman, very long {hair}, floating hair, "
          "navy blue jacket, brown leather belt, black trousers, brown boots, "
          "standing, full body, simple background, {back}")
NEG = ("lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, signature, watermark, logo, "
       "nsfw, nude, child, multiple girls, multiple views, gradient background, scenery")
SEEDS = [20261115, 20261116, 20261117]


def gen_workflow(seed, depth, hair, back):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPSetLastLayer", "inputs": {"clip": ["1", 1], "stop_at_clip_layer": -2}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {
            "clip": ["2", 0], "text": PROMPT.format(hair=HAIRS[hair], back=BACKS[back])}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["13", 0], "negative": ["13", 1], "latent_image": ["5", 0],
            "seed": seed, "steps": 28, "cfg": 5.5, "sampler_name": "euler_ancestral", "scheduler": "normal",
            "denoise": 1.0}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "debimate_bgremove/gen"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": depth}},
        "11": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": UNION}},
        "12": {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["11", 0], "type": "depth"}},
        "13": {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["3", 0], "negative": ["4", 0], "control_net": ["12", 0], "image": ["10", 0],
            "strength": 0.7, "start_percent": 0.0, "end_percent": 0.6, "vae": ["1", 2]}},
    }


def node_workflow(image):
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": image}},
        "2": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": BIREFNET}},
        "3": {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["2", 0], "image": ["1", 0]}},
        "4": {"class_type": "MaskToImage", "inputs": {"mask": ["3", 0]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["4", 0], "filename_prefix": "debimate_bgremove/mask"}},
    }


def rgba_workflow(image):
    """LoadImage → RemoveBackground → InvertMask → JoinImageWithAlpha → SaveImage（公式のテンプレートと同じ順）。"""
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": image}},
        "2": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": BIREFNET}},
        "3": {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["2", 0], "image": ["1", 0]}},
        "4": {"class_type": "InvertMask", "inputs": {"mask": ["3", 0]}},
        "5": {"class_type": "JoinImageWithAlpha", "inputs": {"image": ["1", 0], "alpha": ["4", 0]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["5", 0], "filename_prefix": "debimate_bgremove/rgba"}},
    }


def main():
    depth_png, out, plan = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    log_path = os.path.join(out, f"log_{plan}.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else {}
    if plan == "rgba":
        name = "green_brown_20261115"
        png = os.path.join(out, f"rgba_{name}.png")
        if not os.path.exists(png):
            log[f"rgba_{name}"] = comfy.run(rgba_workflow(comfy.upload(os.path.join(out, name + ".png"))), png, "8")
            json.dump(log, open(log_path, "w"), indent=1)
        return
    depth = comfy.upload(depth_png)
    for seed in SEEDS:
        for hair in HAIRS:
            for back in BACKS:
                name = f"{back}_{hair}_{seed}"
                if plan == "gen":
                    png, wf = os.path.join(out, name + ".png"), lambda: gen_workflow(seed, depth, hair, back)
                else:
                    png = os.path.join(out, name + "_node.png")
                    wf = lambda: node_workflow(comfy.upload(os.path.join(out, name + ".png")))
                if os.path.exists(png):
                    continue
                log[name] = comfy.run(wf(), png, "8")
                json.dump(log, open(log_path, "w"), indent=1)
                print(name, log[name]["seconds"], flush=True)


if __name__ == "__main__":
    main()
