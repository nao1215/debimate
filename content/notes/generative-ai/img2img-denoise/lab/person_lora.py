"""実験 3 の人物を、説明用の画風 LoRA を当てて描く。

LoRA のファイル名と起動語は環境変数から読む（既定は example_style_lora.safetensors と <trigger>）。
  STYLE_LORA=<loras/ の中のファイル名> STYLE_TRIGGER=<起動語> python3 person_lora.py candidates <PNG の保存先> <seed> ...
  STYLE_LORA=... STYLE_TRIGGER=... python3 person_lora.py hires <PNG の保存先> <seed1> <seed2> <seed3>

- candidates: 1 段目（768x1344、28 ステップ）だけを、指定した seed で 1 枚ずつ描く
- hires: seed1・seed2 で、1 段目だけの依頼と、1.5 倍（1152x2016）・20 ステップ・denoise 0.45 の 2 段目まで
  通した依頼を送る。seed3 で、2 段目まで通した依頼をもう 1 回送る
ログとワークフローの JSON には、環境変数の値ではなく既定の名前を書く。
BASE_ONLY=1 を付けると、LoRA と起動語を外し、ベースモデルだけで同じ文面を描く。
"""
import copy
import json
import os
import sys

import comfy
import run_extra

LORA_PUBLIC, TRIGGER_PUBLIC = "example_style_lora.safetensors", "<trigger>"
LORA = os.environ.get("STYLE_LORA", LORA_PUBLIC)
TRIGGER = os.environ.get("STYLE_TRIGGER", TRIGGER_PUBLIC)
STRENGTH = 1.0
W, H = 768, 1344  # 立ち姿の全身は縦長にする（832x1216 では 2 人並びが多かった）
HERE = os.path.dirname(os.path.abspath(__file__))

POSITIVE = ("<trigger>, masterpiece, best quality, rating:general, 1girl, solo, adult woman, mature female, 20s, "
            "black hair, long hair, parted bangs, open eyes, visible eyes, forehead, detailed eyes, sharp eyes, almond-shaped eyes, long eyelashes, eye highlights, calm dignified expression, lips, earrings, "
            "jewelry, nail polish, white blouse, long sleeves, black wide-leg pants, black loafers, full body, "
            "standing, standing straight, arms at sides, front view, simple background, grey background, looking at viewer")
NEGATIVE = ("lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, bad anatomy, bad hands, "
            "extra fingers, missing fingers, extra limbs, deformed, text, signature, watermark, logo, "
            "multiple views, 2girls, multiple girls, character sheet, reference sheet, child, loli, aged down, nude, nipples, "
            "nsfw, cleavage, midriff, navel, underwear, swimsuit, school uniform, serafuku, blunt bangs, multicolored hair, streaked hair, two-tone hair, gradient hair, colored inner hair, hair over eyes, hair over one eye, covered eyes, closed eyes, half-closed eyes, sleepy eyes, sultry, bare shoulders, off-shoulder, leaning forward")



def with_lora(wf, lora, trigger):
    """txt2img のワークフローに LoraLoader（ノード 20）を挟む。"""
    wf = copy.deepcopy(wf)
    wf["20"] = {"class_type": "LoraLoader",
                "inputs": {"model": ["1", 0], "clip": ["1", 1], "lora_name": lora,
                           "strength_model": STRENGTH, "strength_clip": STRENGTH}}
    wf["2"]["inputs"]["clip"] = ["20", 1]
    for node in wf.values():
        if node["class_type"] == "KSampler":
            node["inputs"]["model"] = ["20", 0]
        if node["class_type"] == "CLIPTextEncode":
            node["inputs"]["text"] = node["inputs"]["text"].replace(TRIGGER_PUBLIC, trigger)
    return wf


def first_stage(seed, prefix):
    return run_extra.txt2img(POSITIVE, NEGATIVE, seed, W, H, prefix)


BASE_ONLY = os.environ.get("BASE_ONLY") == "1"  # 1 なら LoRA を使わず、ベースモデルだけで描く


def without_lora(wf):
    wf = copy.deepcopy(wf)
    for node in wf.values():
        if node["class_type"] == "CLIPTextEncode":
            node["inputs"]["text"] = node["inputs"]["text"].replace(TRIGGER_PUBLIC + ", ", "")
    return wf


def send(public_wf, png, save_node):
    """実名の LoRA と起動語に差し替えて送る。返すログに実名は入らない。"""
    if BASE_ONLY:
        return comfy.run(without_lora(public_wf), png, save_node)
    return comfy.run(with_lora(public_wf, LORA, TRIGGER), png, save_node)


def record(log, path, r, **kw):
    r.update(kw)
    print(json.dumps({k: r[k] for k in r if k != "load_before"}, ensure_ascii=False), flush=True)
    log.append(r)
    with open(path, "w") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)


def main():
    mode, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    log = []
    if mode == "candidates":
        # 1 段目だけを seed ごとに 1 枚ずつ描く。目で確かめて、載せられる絵が 3 つ揃うまで seed を足す
        path = os.path.join(out, "candidates_log.json")
        log = json.load(open(path)) if os.path.exists(path) else []
        for s in [int(x) for x in sys.argv[3:]]:
            r = send(first_stage(s, "debimate_img2img/cand"), os.path.join(out, f"cand_{s}.png"), "9")
            record(log, path, r, seed=s)
    elif mode == "hires":
        # 使う seed は 3 つ。前の 2 つは 1 段目だけの依頼と 2 段目まで通した依頼、3 つ目は通した依頼だけ
        seeds = [int(x) for x in sys.argv[3:6]]
        path = os.path.join(out, "hires_log.json")
        for s in seeds[:2]:
            first = first_stage(s, "debimate_img2img/person_1x")
            record(log, path, send(first, os.path.join(out, f"person_{s}_1x.png"), "9"), name="1x_only", seed=s)
            both = run_extra.add_redraw(copy.deepcopy(first), ["8", 0], s, 20, 0.45, "debimate_img2img/person_hires")
            record(log, path, send(both, os.path.join(out, f"person_{s}_hires.png"), "14"), name="hires_chain", seed=s)
        s = seeds[2]
        both = run_extra.add_redraw(first_stage(s, "debimate_img2img/person_1x"), ["8", 0], s, 20, 0.45,
                                    "debimate_img2img/person_hires")
        record(log, path, send(both, os.path.join(out, f"person_{s}_hires.png"), "14"), name="hires_chain", seed=s)
        os.makedirs(os.path.join(HERE, "workflows"), exist_ok=True)
        with open(os.path.join(HERE, "workflows", "hires_fix.json"), "w") as f:
            json.dump(with_lora(both, LORA_PUBLIC, TRIGGER_PUBLIC), f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
