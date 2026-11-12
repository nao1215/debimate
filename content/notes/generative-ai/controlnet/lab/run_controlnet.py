"""同じ文面と seed で、ControlNet の条件だけを変えて 1 枚ずつ描く（Python 標準ライブラリだけ）。

使い方: python3 run_controlnet.py <条件の画像のディレクトリ> <PNG の保存先> <計画の名前>
  計画: compare（文面だけ・骨格・深度マップ × 3 ポーズ × 2 seed）、dedicated（骨格の専用モデル）、
        sweep（深度マップの強さと end の振り）、thin（細い骨格）、canny（人形の輪郭）
ログは <PNG の保存先>/log_<計画>.json に足していく（prompt_id・実行秒数・送る直前の負荷）。
"""
import json
import os
import sys

import comfy

CKPT = "waiIllustriousSDXL_v170.safetensors"
UNION = "xinsir_union_promax_sdxl.safetensors"
OPENPOSE = "xinsir_openpose_sdxl.safetensors"
BASE = ("masterpiece, best quality, 1boy, solo, adult man, short black hair, white shirt, navy jacket, "
        "black trousers, brown boots, holding a long wooden staff, full body, simple background, white background")
POSE_TEXT = {
    "raise": "raising staff overhead with right hand, arm raised high, left hand on hip",
    "lunge": "lunging forward, thrusting staff forward with both hands, from side",
    "lookback": "from behind, looking back over shoulder, staff resting on shoulder",
}
NEG = ("lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, signature, watermark, logo, "
       "nsfw, nude, child, 1girl, multiple boys, multiple views, extra arms")
SEEDS = [20261111, 20261112]


def workflow(pose, seed, control=None):
    """control = None（文面だけ）か {"model", "type", "image", "strength", "start", "end"}。"""
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPSetLastLayer", "inputs": {"clip": ["1", 1], "stop_at_clip_layer": -2}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": f"{BASE}, {POSE_TEXT[pose]}"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
            "seed": seed, "steps": 28, "cfg": 5.5, "sampler_name": "euler_ancestral", "scheduler": "normal",
            "denoise": 1.0}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "debimate_controlnet/out"}},
    }
    if control:
        wf["10"] = {"class_type": "LoadImage", "inputs": {"image": control["image"]}}
        wf["11"] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": control["model"]}}
        cn = ["11", 0]
        if control["model"] == UNION:  # union は 1 つのモデルで種類を切り替える
            wf["12"] = {"class_type": "SetUnionControlNetType",
                        "inputs": {"control_net": ["11", 0], "type": control["type"]}}
            cn = ["12", 0]
        wf["13"] = {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["3", 0], "negative": ["4", 0], "control_net": cn, "image": ["10", 0],
            "strength": control["strength"], "start_percent": control["start"], "end_percent": control["end"],
            "vae": ["1", 2]}}
        wf["6"]["inputs"]["positive"], wf["6"]["inputs"]["negative"] = ["13", 0], ["13", 1]
    return wf


def plan(name):
    """(出力名, ポーズ, seed, 条件) の列。条件の image は条件の画像のファイル名。"""
    jobs = []
    if name == "compare":
        for pose in POSE_TEXT:
            for seed in SEEDS:
                jobs.append((f"{pose}_text_{seed}", pose, seed, None))
                jobs.append((f"{pose}_openpose_{seed}", pose, seed, dict(
                    model=UNION, type="openpose", image=f"openpose_{pose}.png", strength=1.0, start=0.0, end=1.0)))
                jobs.append((f"{pose}_depth_{seed}", pose, seed, dict(
                    model=UNION, type="depth", image=f"depth_{pose}.png", strength=0.7, start=0.0, end=0.6)))
    elif name == "dedicated":
        for pose in POSE_TEXT:
            jobs.append((f"{pose}_openposeded_{SEEDS[0]}", pose, SEEDS[0], dict(
                model=OPENPOSE, type=None, image=f"openpose_{pose}.png", strength=1.0, start=0.0, end=1.0)))
    elif name == "sweep":
        pose, seed = "lunge", SEEDS[0]
        for s in [0.3, 0.5, 1.0]:
            jobs.append((f"{pose}_depth_s{int(s * 100):03d}_e060_{seed}", pose, seed, dict(
                model=UNION, type="depth", image=f"depth_{pose}.png", strength=s, start=0.0, end=0.6)))
        for e in [0.2, 0.4, 1.0]:
            jobs.append((f"{pose}_depth_s070_e{int(e * 100):03d}_{seed}", pose, seed, dict(
                model=UNION, type="depth", image=f"depth_{pose}.png", strength=0.7, start=0.0, end=e)))
    elif name == "thin":
        for pose in ["raise", "lunge"]:
            jobs.append((f"{pose}_openposethin_{SEEDS[0]}", pose, SEEDS[0], dict(
                model=UNION, type="openpose", image=f"openpose_{pose}_thin.png", strength=1.0, start=0.0, end=1.0)))
    elif name == "canny":
        for pose in POSE_TEXT:
            jobs.append((f"{pose}_canny_{SEEDS[0]}", pose, SEEDS[0], dict(
                model=UNION, type="canny/lineart/anime_lineart/mlsd", image=f"canny_{pose}.png",
                strength=0.7, start=0.0, end=0.6)))
    return jobs


def main():
    cond_dir, out, name = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    log_path = os.path.join(out, f"log_{name}.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else {}
    uploaded = {}
    for tag, pose, seed, control in plan(name):
        png = os.path.join(out, tag + ".png")
        if os.path.exists(png):
            continue
        if control:
            img = control["image"]
            if img not in uploaded:
                uploaded[img] = comfy.upload(os.path.join(cond_dir, img))
            control = dict(control, image=uploaded[img])
        r = comfy.run(workflow(pose, seed, control), png, "8")
        log[tag] = dict(r, pose=pose, seed=seed, control=control)
        json.dump(log, open(log_path, "w"), indent=1)
        print(tag, r["seconds"], "s", flush=True)


if __name__ == "__main__":
    main()
