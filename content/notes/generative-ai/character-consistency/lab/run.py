"""同じキャラクターを描き分ける実験の生成（Python 標準ライブラリだけ）。

  STYLE_LORA=<loras/ の中のファイル名> STYLE_TRIGGER=<起動語> python3 run.py <PNG の保存先> <依頼の名前> ...
  python3 run.py --list            # 依頼の名前の一覧

- 人物は、説明用の画風 LoRA（既定の名前 example_style_lora.safetensors、起動語 <trigger>）を強さ 0.75 で当てる。
  実名は環境変数で渡し、ログとワークフローの JSON には既定の名前だけを書く
- 依頼は 1 枚ずつ送り、自分の prompt_id だけを待つ（comfy.py）。待ち行列の削除や設定の変更はしない
- 参照画像・img2img・ControlNet の依頼は、基準の絵（base.png）を先に作ってから送る
"""
import copy
import json
import os
import sys

import comfy

HERE = os.path.dirname(os.path.abspath(__file__))
LORA_PUBLIC, TRIGGER_PUBLIC = "example_style_lora.safetensors", "<trigger>"
LORA = os.environ.get("STYLE_LORA", LORA_PUBLIC)
TRIGGER = os.environ.get("STYLE_TRIGGER", TRIGGER_PUBLIC)
CKPT = "waiIllustriousSDXL_v170.safetensors"
STRENGTH = 0.75
W, H = 832, 1216
BASE_SEED = int(os.environ.get("BASE_SEED", "20261111"))

# キャラクターの指定（全ての依頼で同じ）。場面の語だけを {scene} に差し込む
CHARACTER = ("1girl, solo, adult woman, mature female, 20s, brown hair, medium hair, low ponytail, "
             "parted bangs, forehead, open eyes, visible eyes, green eyes, eye highlights, long eyelashes, lips, earrings, "
             "jewelry, nail polish, medium breasts, white collared shirt, navy cardigan, long sleeves")
# 物差しの目盛り用の別人（髪・目・服を変える）
OTHER = ("1girl, solo, adult woman, mature female, 20s, blonde hair, short hair, bob cut, "
         "parted bangs, forehead, open eyes, visible eyes, blue eyes, eye highlights, long eyelashes, lips, earrings, "
         "jewelry, nail polish, medium breasts, black turtleneck, long sleeves")
POSITIVE = "<trigger>, " + CHARACTER + ", {scene}, masterpiece, best quality, highly detailed"
NEGATIVE = ("lowres, bad quality, bad anatomy, bad hands, extra limbs, text, signature, watermark, logo, collage, "
            "(multiple views:1.2), inset, zoom layer, variations, border, frame, heart, hair over eyes, "
            "hair over one eye, covered eyes, blunt bangs, closed eyes, half-closed eyes, multicolored hair, "
            "streaked hair, two-tone hair, oversaturated, neon colors, nsfw, nude, nipples, cleavage, underwear, "
            "child, loli, aged down, 2girls, multiple girls, large breasts, huge breasts, sleepy eyes, sultry")

SCENES = {
    "base": "neutral expression, closed mouth, standing, arms at sides, upper body, looking at viewer, "
            "simple background, white background",
    "smile": "smile, closed mouth, standing, arms at sides, upper body, looking at viewer, "
             "simple background, white background",
    "wave": "smile, waving, hand up, standing, upper body, looking at viewer, simple background, white background",
    "cafe": "smile, sitting, holding cup, coffee cup, table, cafe, indoors, upper body, looking at viewer",
}


def txt2img(scene, seed, prefix, lora=True, other=False):
    pos = POSITIVE.format(scene=SCENES[scene])
    if other:
        pos = pos.replace(CHARACTER, OTHER)
    if not lora:
        pos = pos.replace(TRIGGER_PUBLIC + ", ", "")
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPSetLastLayer", "inputs": {"clip": ["1", 1], "stop_at_clip_layer": -2}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": pos}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEGATIVE}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": W, "height": H, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
            "seed": seed, "steps": 28, "cfg": 5.5, "sampler_name": "euler_ancestral", "scheduler": "normal",
            "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix}},
    }
    if lora:
        wf["20"] = {"class_type": "LoraLoader", "inputs": {
            "model": ["1", 0], "clip": ["1", 1], "lora_name": LORA_PUBLIC,
            "strength_model": STRENGTH, "strength_clip": STRENGTH}}
        wf["2"]["inputs"]["clip"] = ["20", 1]
        wf["7"]["inputs"]["model"] = ["20", 0]
    return wf


def add_ipadapter(wf, ref, weight, start=0.0):
    """参照画像（IP-Adapter Plus）を KSampler の手前のモデルに掛ける。start は掛け始める位置（0〜1）。"""
    wf["30"] = {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}}
    wf["31"] = {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}}
    wf["32"] = {"class_type": "LoadImage", "inputs": {"image": ref}}
    wf["33"] = {"class_type": "IPAdapterAdvanced", "inputs": {
        "model": wf["7"]["inputs"]["model"], "ipadapter": ["30", 0], "image": ["32", 0], "clip_vision": ["31", 0],
        "weight": weight, "weight_type": "linear", "combine_embeds": "concat", "start_at": start, "end_at": 1.0,
        "embeds_scaling": "V only"}}
    wf["7"]["inputs"]["model"] = ["33", 0]
    return wf


def add_img2img(wf, ref, denoise):
    """基準の絵を潜在に変え、途中の段から描き直す。"""
    wf["50"] = {"class_type": "LoadImage", "inputs": {"image": ref}}
    wf["51"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["50", 0], "vae": ["1", 2]}}
    wf["7"]["inputs"]["latent_image"] = ["51", 0]
    wf["7"]["inputs"]["denoise"] = denoise
    del wf["5"]
    return wf


def add_openpose(wf, ref, strength=1.0):
    """基準の絵から DWPose で骨格を取り、ControlNet Union の openpose で縛る。骨格の画像も保存する。"""
    wf["40"] = {"class_type": "LoadImage", "inputs": {"image": ref}}
    wf["41"] = {"class_type": "DWPreprocessor", "inputs": {
        "image": ["40", 0], "detect_hand": "enable", "detect_body": "enable", "detect_face": "enable",
        "resolution": 1024, "scale_stick_for_xinsr_cn": "enable"}}
    wf["42"] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "xinsir_union_promax_sdxl.safetensors"}}
    wf["43"] = {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["42", 0], "type": "openpose"}}
    wf["44"] = {"class_type": "ControlNetApplyAdvanced", "inputs": {
        "positive": ["3", 0], "negative": ["4", 0], "control_net": ["43", 0], "image": ["41", 0],
        "strength": strength, "start_percent": 0.0, "end_percent": 1.0, "vae": ["1", 2]}}
    wf["7"]["inputs"]["positive"] = ["44", 0]
    wf["7"]["inputs"]["negative"] = ["44", 1]
    wf["45"] = {"class_type": "SaveImage", "inputs": {"images": ["41", 0], "filename_prefix": "debimate_charcons/pose"}}
    return wf


OUT = "."
S = BASE_SEED
# 依頼の名前 -> (場面, seed, 付け足す手段)
JOBS = {}
for i in range(4):                                   # (a) 同じ文面・seed だけ変える（候補を兼ねる）
    JOBS[f"seed_{i}"] = ("base", S + i, None)
for i in range(4):                                   # (c) 画風 LoRA を外す
    JOBS[f"nolora_{i}"] = ("base", S + i, "nolora")
for sc in ("smile", "wave", "cafe"):                 # (b) seed を固定して場面の語だけ変える（seed は基準と同じ）
    JOBS[f"fixed_{sc}"] = (sc, None, None)
    JOBS[f"newseed_{sc}"] = (sc, S + 100, None)      # 対照: 参照なしで seed も変える
    for wgt in (0.5, 0.8):                           # (d) 参照画像
        JOBS[f"ipa{int(wgt * 100)}_{sc}"] = (sc, S + 100, ("ipa", wgt))
    for d in (0.5, 0.7):                             # (e) img2img
        JOBS[f"i2i{int(d * 100)}_{sc}"] = (sc, None, ("i2i", d))
for wgt, st in ((0.35, 0.0), (0.6, 0.3)):            # (d) 色の転びを抑える試し: 弱く掛ける / 前半を外す
    JOBS[f"ipa{int(wgt * 100)}s{int(st * 10)}_smile"] = ("smile", S + 100, ("ipa", wgt, st))
for sc in ("wave", "cafe"):                          # (e) img2img をさらに強く
    JOBS[f"i2i85_{sc}"] = (sc, None, ("i2i", 0.85))
for sc in ("wave", "cafe"):                          # (d) 参照なしで描いた絵を、参照を掛けて弱く描き直す
    JOBS[f"redraw_{sc}"] = (sc, S + 100, ("redraw", 0.5, 0.7))
for i in (0, 1):                                     # 物差しの目盛り: 別人
    JOBS[f"other_{i}"] = ("base", S + 300 + i, "other")
for i in (1, 2):                                     # (f) 基準の骨格で縛り、seed を変える
    JOBS[f"pose_{i}"] = ("base", S + 200 + i, ("pose", 1.0))


def build(name, base_seed, ref):
    scene, seed, extra = JOBS[name]
    seed = base_seed if seed is None else seed
    wf = txt2img(scene, seed, f"debimate_charcons/{name}", lora=(extra != "nolora"), other=(extra == "other"))
    if isinstance(extra, tuple):
        kind, *val = extra
        if kind == "redraw":                         # 下絵は同じ場面の newseed_*.png、参照は基準の絵
            add_img2img(wf, comfy.upload(os.path.join(OUT, f"newseed_{scene}.png")), val[0])
            add_ipadapter(wf, ref, val[1])
        else:
            {"ipa": add_ipadapter, "i2i": add_img2img, "pose": add_openpose}[kind](wf, ref, *val)
    return wf, seed


def real(wf):
    """公開用の名前を実名に差し替えた写しを返す。"""
    wf = copy.deepcopy(wf)
    for node in wf.values():
        if node["class_type"] == "LoraLoader":
            node["inputs"]["lora_name"] = LORA
        if node["class_type"] == "CLIPTextEncode":
            node["inputs"]["text"] = node["inputs"]["text"].replace(TRIGGER_PUBLIC, TRIGGER)
    return wf


def main():
    if sys.argv[1] == "--list":
        print("\n".join(JOBS))
        return
    global OUT
    out = OUT = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    os.makedirs(os.path.join(HERE, "workflows"), exist_ok=True)
    log_path = os.path.join(out, "log.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else []
    base_seed = int(os.environ.get("BASE_PICK", str(S)))   # 候補から選んだ基準の seed
    ref = None
    for name in sys.argv[2:]:
        if isinstance(JOBS[name][2], tuple) and ref is None:
            ref = comfy.upload(os.path.join(out, "base.png"))
        wf, seed = build(name, base_seed, ref)
        r = comfy.run(real(wf), os.path.join(out, f"{name}.png"), "9")
        if "45" in wf:
            comfy.fetch(r["prompt_id"], "45", os.path.join(out, f"{name}_skeleton.png"))
        r.update(name=name, seed=seed)
        print(json.dumps({k: v for k, v in r.items() if k != "load_before"}, ensure_ascii=False), flush=True)
        log.append(r)
        json.dump(log, open(log_path, "w"), indent=1, ensure_ascii=False)
        json.dump(wf, open(os.path.join(HERE, "workflows", f"{name}.json"), "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
