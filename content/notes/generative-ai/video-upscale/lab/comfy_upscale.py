"""手元の ComfyUI の API で、フレームを 1 枚ずつ拡大する。

python3 comfy_upscale.py diffusion <入力ディレクトリ> <出力ディレクトリ>
    入力（upscale.py で RealESRGAN_x4plus_anime_6B を掛けた 1024x576）を、SDXL 系のモデルで
    denoise 0.35 で描き直す（seed は全フレームで同じ）。hires fix と同じ考え方の 2 段目。
python3 comfy_upscale.py gan <入力ディレクトリ> <出力ディレクトリ>
    ComfyUI の ImageUpscaleWithModel で 4 倍にする（本文の実験では使わず、upscale.py の CPU 版を使った）
"""
import json
import sys
from pathlib import Path

import comfy

CKPT = "illustriousRealismBy_v10VAE.safetensors"
GAN = "RealESRGAN_x4plus_anime_6B.pth"
PROMPT = "dragon flying in sunset sky, detailed scales, hand in knitted glove, realistic, high quality"
NEGATIVE = "lowres, worst quality, low quality, blurry, jpeg artifacts, text, watermark"


def gan_workflow(image):
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": image}},
        "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": GAN}},
        "3": {"class_type": "ImageUpscaleWithModel",
              "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["3", 0], "filename_prefix": "debimate_video_upscale/gan"}},
    }


def diffusion_workflow(image):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": PROMPT}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": NEGATIVE}},
        "5": {"class_type": "LoadImage", "inputs": {"image": image}},
        "6": {"class_type": "VAEEncode", "inputs": {"pixels": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0],
                         "latent_image": ["6", 0], "seed": 20261111, "steps": 20, "cfg": 5.0,
                         "sampler_name": "euler", "scheduler": "normal", "denoise": 0.35}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": "debimate_video_upscale/diff"}},
    }


def main():
    mode, src, dst = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    dst.mkdir(parents=True, exist_ok=True)
    build = gan_workflow if mode == "gan" else diffusion_workflow
    log = []
    for p in sorted(src.glob("*.png")):
        image = comfy.upload(str(p), subfolder=f"debimate_video_upscale/{src.name}")
        r = comfy.run(build(image), str(dst / p.name), "9")
        log.append({"frame": p.name, **r})
        print(p.name, r["seconds"], flush=True)
    (dst / "log.json").write_text(json.dumps(log, indent=1) + "\n")


if __name__ == "__main__":
    main()
