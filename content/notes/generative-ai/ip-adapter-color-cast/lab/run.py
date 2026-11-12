"""参照の背景・掛ける段・weight の型を変えて描く。

使い方: python3 run.py <深度マップの PNG> <make_refs.py の保存先> <PNG の保存先> <計画の名前> [背景の一覧]
  背景の一覧は white,black,green のようにカンマで区切る（既定は 3 つとも）
  計画: grid   1 段目と 2 段目 × 背景（白・黒・緑）× 型（style transfer precise・linear）× seed、重み 0.6。
               参照なしの 1 段目と 2 段目も描く
        first  1 段目だけを背景 × 型 × seed で描く（人物のいない参照に使う）
        weight 1 段目に白の参照を style transfer precise で、2 段目に緑の参照を linear で、重み 0.3・0.9 で描く
1 段目: 深度マップ（union depth、強さ 0.7、end 0.6）でプロンプトから描く（txt2img）。
2 段目: 参照なしの 1 段目の絵を denoise 0.45 で描き直す（深度マップは強さ 0.8、end 0.8）。
参照はどちらの段でも start 0、end 1 で掛ける。
ログは <PNG の保存先>/log_<計画>.json に足していく（prompt_id・実行秒数・送る直前の負荷）。
Python 標準ライブラリだけで動く。
"""
import json
import os
import sys

import comfy

CKPT = "waiIllustriousSDXL_v170.safetensors"
UNION = "xinsir_union_promax_sdxl.safetensors"
IPA = "ip-adapter-plus_sdxl_vit-h.safetensors"
VISION = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
PROMPT = ("masterpiece, best quality, 1girl, solo, adult woman, long brown hair, ponytail, knight, "
          "silver plate armor, breastplate, pauldrons, gauntlets, armored boots, dark trousers, "
          "standing, full body, simple background, white background")
NEG = ("lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, signature, watermark, logo, "
       "nsfw, nude, child, multiple girls, multiple views")
SEEDS = [20261112, 20261113, 20261114]
TYPES = {"stp": "style transfer precise", "linear": "linear"}


def workflow(seed, depth, ref=None, weight=0.6, wtype="stp", source=None):
    """ref があれば IP-Adapter を掛ける。source があれば、その絵を denoise 0.45 で描き直す（2 段目）。"""
    strength, end = (0.8, 0.8) if source else (0.7, 0.6)
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPSetLastLayer", "inputs": {"clip": ["1", 1], "stop_at_clip_layer": -2}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": PROMPT}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["13", 0], "negative": ["13", 1], "latent_image": ["5", 0],
            "seed": seed, "steps": 28, "cfg": 5.5, "sampler_name": "euler_ancestral", "scheduler": "normal",
            "denoise": 0.45 if source else 1.0}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "debimate_ipacolor/out"}},
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
        wf["5"] = {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}}
    if ref:
        wf["30"] = {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": IPA}}
        wf["31"] = {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": VISION}}
        wf["32"] = {"class_type": "LoadImage", "inputs": {"image": ref}}
        wf["33"] = {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": ["1", 0], "ipadapter": ["30", 0], "image": ["32", 0], "clip_vision": ["31", 0],
            "weight": weight, "weight_type": TYPES[wtype], "combine_embeds": "concat",
            "start_at": 0.0, "end_at": 1.0, "embeds_scaling": "V only"}}
        wf["6"]["inputs"]["model"] = ["33", 0]
    return wf


def jobs(plan, out, depth, refs, seed):
    backs = tuple(refs)
    if plan == "grid":
        yield f"s1_none_{seed}", dict(depth=depth)
        for back in backs:
            for wtype in TYPES:
                yield f"s1_{back}_{wtype}_{seed}", dict(depth=depth, ref=refs[back], wtype=wtype)
        src = comfy.upload(os.path.join(out, f"s1_none_{seed}.png"))
        yield f"s2_none_{seed}", dict(depth=depth, source=src)
        for back in backs:
            for wtype in TYPES:
                yield f"s2_{back}_{wtype}_{seed}", dict(depth=depth, ref=refs[back], wtype=wtype, source=src)
    elif plan == "first":
        for back in backs:
            for wtype in TYPES:
                yield f"s1_{back}_{wtype}_{seed}", dict(depth=depth, ref=refs[back], wtype=wtype)
    elif plan == "weight":
        src = comfy.upload(os.path.join(out, f"s1_none_{seed}.png"))
        for w in (0.3, 0.9):
            yield f"s1_white_stp_w{int(w * 10)}_{seed}", dict(depth=depth, ref=refs["white"], wtype="stp", weight=w)
            yield f"s2_green_linear_w{int(w * 10)}_{seed}", dict(depth=depth, ref=refs["green"], wtype="linear",
                                                                 weight=w, source=src)


def main():
    depth_png, ref_dir, out, plan = sys.argv[1:5]
    backs = sys.argv[5].split(",") if len(sys.argv) > 5 else ["white", "black", "green"]
    os.makedirs(out, exist_ok=True)
    log_path = os.path.join(out, f"log_{plan}.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else {}
    depth = comfy.upload(depth_png)
    refs = {b: comfy.upload(os.path.join(ref_dir, f"{b}.png")) for b in backs}
    for seed in SEEDS:
        for name, kw in jobs(plan, out, depth, refs, seed):
            png = os.path.join(out, name + ".png")
            if os.path.exists(png):
                continue
            log[name] = comfy.run(workflow(seed, **kw), png, "8")
            json.dump(log, open(log_path, "w"), indent=1)
            print(name, log[name]["seconds"], flush=True)


if __name__ == "__main__":
    main()
