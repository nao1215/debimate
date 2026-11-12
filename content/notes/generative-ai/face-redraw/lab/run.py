"""全身の立ち絵を描き、顔だけを拡大して描き直す。比べのために、絵の全体を 2 倍で描き直した絵も作る。

使い方: python3 run.py <深度マップの PNG> <作業先> base    全身の立ち絵（832 x 1216）を seed ごとに描く
        python3 run.py <深度マップの PNG> <作業先> face    顔の枠（<作業先>/detect.json）を使って、顔だけを描き直す
        python3 run.py <深度マップの PNG> <作業先> hires   絵の全体を 2 倍（1664 x 2432）に拡大して描き直す
        python3 run.py <深度マップの PNG> <作業先> big     最初から 2 倍（1664 x 2432）で描く（深度マップは ControlNet が拡大する）
描き方: 深度マップ（union depth、強さ 0.7、end 0.6）でプロンプトから描く（txt2img）。LoRA は使わない。
顔の描き直し（ComfyUI の本体のノードだけで組む）:
  1. 顔の枠の中心を中心に、枠の長い辺 × crop_factor の正方形を切り抜く（ImageCropV2）
  2. 1024 x 1024 に拡大する（ImageScale、lanczos）
  3. img2img で描き直す（VAEEncode → KSampler の denoise → VAEDecode）
  4. 切り抜いた大きさへ縮める（ImageScale、area）
  5. 顔の枠を 1.3 倍に広げてぼかしたマスクで、元の絵へ貼り戻す（ImageCompositeMasked）
  描き直した 1024 x 1024 の絵も、貼り戻す前の姿として保存する（<名前>_crop.png）。
全体の描き直し（hires fix）: 元の絵を lanczos で 2 倍にし、denoise 0.45 の img2img に通す。ControlNet は掛けない。
ログは <作業先>/log_<計画>.json に足していく（prompt_id・実行秒数・送る直前の負荷）。
Python 標準ライブラリだけで動く。
"""
import json
import os
import sys

import comfyapi as comfy

CKPT = "waiIllustriousSDXL_v170.safetensors"
UNION = "xinsir_union_promax_sdxl.safetensors"
CHAR = ("masterpiece, best quality, 1girl, solo, adult woman, long brown hair, parted bangs, brown eyes, "
        "looking at viewer, open eyes, ")
PROMPTS = {
    # 全身を描いた時と同じプロンプト（顔を描き直す道具の多くは、何も指定しなければこれを使う）
    "same": CHAR + "navy blue jacket, brown leather belt, black trousers, brown boots, "
                   "standing, full body, simple background, white background",
    # 顔を描き直すためのプロンプト（構図の語を外し、顔の寄りの語を足す）
    "face": CHAR + "navy blue jacket, portrait, close-up, face, simple background, white background",
}
NEG = ("lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, signature, watermark, logo, "
       "nsfw, nude, child, multiple girls, multiple views, gradient background, scenery, "
       "hair over eyes, closed eyes, half-closed eyes")
SEEDS = [20261118, 20261119, 20261120, 20261121, 20261122]
W, H = 832, 1216
# 顔の描き直しの条件: (denoise, プロンプト, crop_factor)
FACE_RUNS = [(0.3, "same", 3.0), (0.45, "same", 3.0), (0.6, "same", 3.0),
             (0.45, "face", 3.0), (0.6, "face", 3.0), (0.45, "same", 1.5)]
SIDE = 1024


def common(prompt):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPSetLastLayer", "inputs": {"clip": ["1", 1], "stop_at_clip_layer": -2}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": PROMPTS[prompt]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
    }


def base_workflow(seed, depth, scale=1):
    wf = common("same")
    wf.update({
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": W * scale, "height": H * scale, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["13", 0], "negative": ["13", 1], "latent_image": ["5", 0],
            "seed": seed, "steps": 28, "cfg": 5.5, "sampler_name": "euler_ancestral", "scheduler": "normal",
            "denoise": 1.0}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "debimate_faceredraw/base"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": depth}},
        "11": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": UNION}},
        "12": {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["11", 0], "type": "depth"}},
        "13": {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["3", 0], "negative": ["4", 0], "control_net": ["12", 0], "image": ["10", 0],
            "strength": 0.7, "start_percent": 0.0, "end_percent": 0.6, "vae": ["1", 2]}},
    })
    return wf


def img2img(wf, image_ref, seed, denoise):
    """image_ref の絵を img2img で描き直すノードを足し、VAEDecode のノード番号を返す。"""
    wf.update({
        "20": {"class_type": "VAEEncode", "inputs": {"pixels": image_ref, "vae": ["1", 2]}},
        "21": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["20", 0],
            "seed": seed, "steps": 28, "cfg": 5.5, "sampler_name": "euler_ancestral", "scheduler": "normal",
            "denoise": denoise}},
        "22": {"class_type": "VAEDecode", "inputs": {"samples": ["21", 0], "vae": ["1", 2]}},
    })
    return ["22", 0]


def crop_box(box, factor):
    """顔の枠 [x1, y1, x2, y2] から、切り抜く正方形 (x, y, 辺) を決める。絵の外へ出たら内側へ寄せる。"""
    x1, y1, x2, y2 = box
    side = int(round(max(x2 - x1, y2 - y1) * factor))
    side = min(side, W, H)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    x = int(round(min(max(cx - side / 2, 0), W - side)))
    y = int(round(min(max(cy - side / 2, 0), H - side)))
    return x, y, side


def face_workflow(image, seed, box, denoise, prompt, factor):
    x, y, side = crop_box(box, factor)
    wf = common(prompt)
    wf.update({
        "10": {"class_type": "LoadImage", "inputs": {"image": image}},
        "11": {"class_type": "ImageCropV2", "inputs": {
            "image": ["10", 0], "crop_region": {"x": x, "y": y, "width": side, "height": side}}},
        "12": {"class_type": "ImageScale", "inputs": {
            "image": ["11", 0], "upscale_method": "lanczos", "width": SIDE, "height": SIDE, "crop": "disabled"}},
    })
    out = img2img(wf, ["12", 0], seed, denoise)
    # 貼り戻すマスク: 顔の枠を 1.3 倍に広げた矩形を、切り抜いた正方形の中に置いてぼかす
    x1, y1, x2, y2 = box
    mw, mh = int((x2 - x1) * 1.3), int((y2 - y1) * 1.3)
    mx = int((x1 + x2) / 2 - mw / 2) - x
    my = int((y1 + y2) / 2 - mh / 2) - y
    blur = max(2, side // 24)
    wf.update({
        "30": {"class_type": "ImageScale", "inputs": {
            "image": out, "upscale_method": "area", "width": side, "height": side, "crop": "disabled"}},
        "31": {"class_type": "SolidMask", "inputs": {"value": 0.0, "width": side, "height": side}},
        "32": {"class_type": "SolidMask", "inputs": {"value": 1.0, "width": mw, "height": mh}},
        "33": {"class_type": "MaskComposite", "inputs": {
            "destination": ["31", 0], "source": ["32", 0], "x": max(mx, 0), "y": max(my, 0), "operation": "add"}},
        "34": {"class_type": "MaskToImage", "inputs": {"mask": ["33", 0]}},
        "35": {"class_type": "ImageBlur", "inputs": {"image": ["34", 0], "blur_radius": blur, "sigma": blur / 2}},
        "36": {"class_type": "ImageToMask", "inputs": {"image": ["35", 0], "channel": "red"}},
        "37": {"class_type": "ImageCompositeMasked", "inputs": {
            "destination": ["10", 0], "source": ["30", 0], "x": x, "y": y, "resize_source": False,
            "mask": ["36", 0]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["37", 0], "filename_prefix": "debimate_faceredraw/face"}},
        "9": {"class_type": "SaveImage", "inputs": {"images": out, "filename_prefix": "debimate_faceredraw/crop"}},
    })
    return wf, {"crop": [x, y, side], "mask": [x + max(mx, 0), y + max(my, 0), mw, mh], "blur": blur}


def hires_workflow(image, seed):
    wf = common("same")
    wf.update({
        "10": {"class_type": "LoadImage", "inputs": {"image": image}},
        "12": {"class_type": "ImageScale", "inputs": {
            "image": ["10", 0], "upscale_method": "lanczos", "width": W * 2, "height": H * 2, "crop": "disabled"}},
    })
    out = img2img(wf, ["12", 0], seed, 0.45)
    wf["8"] = {"class_type": "SaveImage", "inputs": {"images": out, "filename_prefix": "debimate_faceredraw/hires"}}
    return wf


def face_box(det, name):
    """遠くの顔向けの検出器（full）で、しきい値 0.5、見つからなければ 0.1 の枠を使う。"""
    for key in ("full_0.5", "full_0.1"):
        if det[name][key]:
            return det[name][key][0]["box"], key
    raise SystemExit(f"{name}: 顔が見つからない")


def main():
    depth_png, out, plan = sys.argv[1:4]
    gen = os.path.join(out, "gen")
    os.makedirs(gen, exist_ok=True)
    log_path = os.path.join(out, f"log_{plan}.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else {}

    def save():
        json.dump(log, open(log_path, "w"), indent=1)

    if plan == "base":
        depth = comfy.upload(depth_png)
        for seed in SEEDS:
            png = os.path.join(gen, f"base_{seed}.png")
            if not os.path.exists(png):
                log[f"base_{seed}"] = comfy.run(base_workflow(seed, depth), png, "8")
                save()
                print(seed, log[f"base_{seed}"]["seconds"], flush=True)
    elif plan == "big":
        depth = comfy.upload(depth_png)
        for seed in SEEDS:
            png = os.path.join(gen, f"big_{seed}.png")
            if not os.path.exists(png):
                log[f"big_{seed}"] = comfy.run(base_workflow(seed, depth, 2), png, "8")
                save()
                print(seed, log[f"big_{seed}"]["seconds"], flush=True)
    elif plan == "hires":
        for seed in SEEDS:
            png = os.path.join(gen, f"hires_{seed}.png")
            if not os.path.exists(png):
                log[f"hires_{seed}"] = comfy.run(hires_workflow(comfy.upload(os.path.join(gen, f"base_{seed}.png")), seed),
                                                 png, "8")
                save()
                print(seed, log[f"hires_{seed}"]["seconds"], flush=True)
    elif plan == "face":
        det = json.load(open(os.path.join(out, "detect.json")))
        for seed in SEEDS:
            box, key = face_box(det, f"base_{seed}")
            image = comfy.upload(os.path.join(gen, f"base_{seed}.png"))
            for denoise, prompt, factor in FACE_RUNS:
                name = f"face_{seed}_{prompt}_d{int(denoise * 100)}_c{int(factor * 10)}"
                png = os.path.join(gen, name + ".png")
                if os.path.exists(png):
                    continue
                wf, geo = face_workflow(image, seed, box, denoise, prompt, factor)
                log[name] = comfy.run(wf, png, "8")
                comfy.fetch(log[name]["prompt_id"], "9", os.path.join(gen, name + "_crop.png"))
                log[name].update(geo, box=box, detector=key)
                save()
                print(name, log[name]["seconds"], flush=True)


if __name__ == "__main__":
    main()
