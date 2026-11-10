"""本文の実験 1 の対照と実験 2 の生成。どれも 1 枚ずつ送り、自分の prompt_id だけを待つ。

  control : 下絵を使わない txt2img（EmptyLatentImage、denoise 1.0）。下絵の 1.0 と比べる
  morph   : 金貨の静物を txt2img で 1 枚描き、1.5 倍に拡大して全体を描き直す
            （denoise 0.3〜0.75、金貨を書かない文面。0.6 だけ金貨を書いた文面でも描く）
  （実験 3 の hires fix は person_lora.py。ここの txt2img と add_redraw を使う）

使い方: python3 run_extra.py <control|morph> <PNG の保存先>
結果は <PNG の保存先>/<モード>_log.json に書く。ワークフローは workflows/ に JSON で書き出す。
"""
import copy
import json
import os
import sys

import comfy

HERE = os.path.dirname(os.path.abspath(__file__))
CKPT = "waiIllustriousSDXL_v170.safetensors"
NEG_OBJ = ("lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, "
           "signature, watermark, logo, 1girl, 1boy, person")
STILL = ("masterpiece, best quality, no humans, still life, red apple, blue book, lemon, "
         "wooden table, plain wall, indoors")
COINS = ("masterpiece, best quality, no humans, still life, pile of gold coins, "
         "small wooden treasure chest, wooden table, candle, indoors")
GENERIC = "masterpiece, best quality, no humans, still life, wooden table, indoors"


def base_nodes(pos, neg):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPSetLastLayer", "inputs": {"clip": ["1", 1], "stop_at_clip_layer": -2}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": pos}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": neg}},
    }


def ksampler(latent, seed, steps, denoise):
    return {"class_type": "KSampler",
            "inputs": {"model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0],
                       "latent_image": latent, "seed": seed, "steps": steps, "cfg": 5.5,
                       "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": denoise}}


def txt2img(pos, neg, seed, w, h, prefix):
    wf = base_nodes(pos, neg)
    wf["5"] = {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}}
    wf["7"] = ksampler(["5", 0], seed, 28, 1.0)
    wf["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}}
    wf["9"] = {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix}}
    return wf


def add_redraw(wf, image_src, seed, steps, denoise, prefix):
    """image_src の画像を 1.5 倍（lanczos）に拡大し、VAE で潜在に戻して描き直す。"""
    wf["10"] = {"class_type": "ImageScaleBy",
                "inputs": {"image": image_src, "upscale_method": "lanczos", "scale_by": 1.5}}
    wf["11"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["1", 2]}}
    wf["12"] = ksampler(["11", 0], seed, steps, denoise)
    wf["13"] = {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["1", 2]}}
    wf["14"] = {"class_type": "SaveImage", "inputs": {"images": ["13", 0], "filename_prefix": prefix}}
    return wf


def dump(name, wf):
    os.makedirs(os.path.join(HERE, "workflows"), exist_ok=True)
    with open(os.path.join(HERE, "workflows", f"{name}.json"), "w") as f:
        json.dump(wf, f, indent=1, ensure_ascii=False)


def record(log, path, r, **kw):
    r.update(kw)
    print(json.dumps(r, ensure_ascii=False), flush=True)
    log.append(r)
    with open(path, "w") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)


def main():
    mode, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    log_path = os.path.join(out, f"{mode}_log.json")
    log = []
    seed = 20261110
    if mode == "control":
        wf = txt2img(STILL, NEG_OBJ, seed, 1024, 1024, "debimate_img2img/control")
        dump("control_txt2img", wf)
        record(log, log_path, comfy.run(wf, os.path.join(out, "control_txt2img.png"), "9"), name="control")
    elif mode == "morph":
        wf = txt2img(COINS, NEG_OBJ, seed, 1024, 1024, "debimate_img2img/coins")
        dump("morph_base_txt2img", wf)
        base_png = os.path.join(out, "coins_base.png")
        record(log, log_path, comfy.run(wf, base_png, "9"), name="base")
        image = comfy.upload(base_png)
        for d, text, tag in [(0.3, GENERIC, "g"), (0.45, GENERIC, "g"), (0.5, GENERIC, "g"),
                             (0.6, GENERIC, "g"), (0.75, GENERIC, "g"), (0.6, COINS, "c")]:
            wf = base_nodes(text, NEG_OBJ)
            wf["5"] = {"class_type": "LoadImage", "inputs": {"image": image}}
            add_redraw(wf, ["5", 0], seed, 28, d, "debimate_img2img/coins_redraw")
            if tag == "g" and d == 0.6:
                dump("morph_redraw", wf)
            png = os.path.join(out, f"coins_{tag}_{int(round(d * 100)):03d}.png")
            record(log, log_path, comfy.run(wf, png, "14"), name=f"redraw_{tag}", denoise=d)


if __name__ == "__main__":
    main()
