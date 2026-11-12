"""条件ごとのプロンプトと解像度で、seed を変えて ComfyUI に 1 枚ずつ送る。

依頼は 1 枚ずつ送り、自分の prompt_id の完了を待ってから次を送る。
待ち行列の削除や中断はしない。Python 標準ライブラリだけで動く。

使い方:
    python3 gen.py <保存先ディレクトリ> <条件名> [seed の数] [ComfyUI の URL]

条件名は CONDITIONS のキー。seed は 1000 から順に seed の数だけ使う。
保存済みの PNG があれば、その seed は送らない。
"""
import copy
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
FIRST_SEED = 1000
NEG = "lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, signature, watermark, logo"
NEG_PERSON = NEG + ", nsfw, nude, cleavage, underwear, swimsuit, revealing clothes, multiple views"
Q = "masterpiece, best quality, general, "
BG = ", simple background, white background"
# 人物は成人で服を着た上半身か全身。体の部位を強調する語は書かない
PERSON = Q + "1girl, solo, adult, mature female, "
EYE = "upper body, looking at viewer, long hair, white collared shirt, "
BODY = "full body, standing, long sleeves, "
# 画風 LoRA を当てる条件。LoRA のファイル名と起動語は環境変数から読む
STYLE_LORA = os.environ.get("STYLE_LORA", "example_style_lora.safetensors")
STYLE_TRIGGER = os.environ.get("STYLE_TRIGGER", "<trigger>")
STYLE_STRENGTH = 0.75
# 立ち絵のプロンプト（目を見せた立ち絵で実績のある語順とネガティブプロンプト）。起動語は先頭に足す
S_HEAD = ("adult, mature adult, 1woman, mature female, 20s, black hair, long hair, parted bangs, "
          "open eyes, visible eyes")
S_TAIL = ("white collared shirt, long sleeves, long navy skirt, fully clothed, white background, "
          "simple background, (solo:1.2), single character, standing, full body, centered")
S_QUALITY = "masterpiece, best quality, highly detailed"
S_CLOTHES = "white collared shirt, long sleeves, long navy skirt"
S_EYES = "sharp eyes, eye highlights, detailed eyes"
NEG_REP = (", half-closed eyes, closed eyes, multicolored hair, streaked hair, two-tone hair, "
           "gradient hair, colored inner hair")
NEG_STYLE = ("(2girls:1.2), (2boys:1.2), close-up, cleavage, underwear, panties, bra, lingerie, "
             "nude, lifted skirt, see-through, inset, zoom layer, variations, face focus, portrait, "
             "upper body, cropped, holding object, from behind, looking back, back focus, "
             "ass focus, hair over one eye, covered eyes, blunt bangs, colored background, "
             "curtains, wall, pillar, frame, border, lowres, bad quality, bad anatomy, bad hands, "
             "extra limbs, text, signature, watermark, child, loli, shota, petite, aged down, "
             "young, heart")


def c(positive, w=1024, h=1024, neg=NEG_PERSON, lora=False):
    """positive が組なら、2 つを別々に CLIP に通して ConditioningConcat でつなぐ。
    lora が真なら、画風 LoRA を当て、プロンプトの先頭に起動語を置く。"""
    return {"positive": positive, "width": w, "height": h, "negative": neg, "lora": lora}


def s_(extra="", w=768, h=1344, clothes=None):
    """立ち絵のプロンプトに語を足した条件。extra は髪の色・目の色の後ろに入る。
    clothes を渡すと、服の語（white collared shirt, long sleeves, long navy skirt）を置き換える。"""
    head = S_HEAD + (", " + extra if extra else "")
    tail = S_TAIL if clothes is None else S_TAIL.replace(S_CLOTHES, clothes)
    return c(", ".join([head, tail, S_QUALITY]), w, h, neg=NEG_STYLE, lora=True)


def r_(extra="", w=768, h=1344, clothes=None):
    """s_ のプロンプトに、目をはっきり描く語と、髪を単色にするネガティブプロンプトを足した条件（本文に絵を載せる組）。"""
    head = S_HEAD + ", " + S_EYES + (", " + extra if extra else "")
    tail = S_TAIL if clothes is None else S_TAIL.replace(S_CLOTHES, clothes)
    return c(", ".join([head, tail, S_QUALITY]), w, h, neg=NEG_STYLE + NEG_REP, lora=True)


CONDITIONS = {
    # 画風 LoRA を当てた条件（s_ で始まる）
    "s_eye_none":   s_(),
    "s_eye_aqua":   s_("aqua eyes"),
    # 縦横比の実験の 768x1344 は s_eye_none を使う
    "s_ar_832x1216":  s_("", 832, 1216),
    "s_ar_1024x1024": s_("", 1024, 1024),
    "s_light_sunset": s_("sunset"),
    "s_light_night":  s_("night"),
    # 目をはっきり描く語と、髪を単色にするネガティブプロンプトを足した組（s_rep_ で始まる）
    "s_rep_none":  r_(),
    "s_rep_aqua":  r_("aqua eyes"),
    # 縦横比・照明・two-tone の、本文に絵を載せる組（768 x 1344 は s_rep_none を使う）
    "s_rep_ar_832x1216":  r_("", 832, 1216),
    "s_rep_ar_1024x1024": r_("", 1024, 1024),
    "s_rep_light_sunset": r_("sunset"),
    "s_rep_light_night":  r_("night"),
    "s_rep_tone_two":   r_(clothes="long sleeves, two-tone dress, black and white dress"),
    "s_rep_tone_parts": r_(clothes="long sleeves, black jacket, white long skirt"),
    "s_tone_two":   s_(clothes="long sleeves, two-tone dress, black and white dress"),
    "s_tone_parts": s_(clothes="long sleeves, black jacket, white long skirt"),

    # ベースモデルだけの条件（LoRA なし）
    # 目の色が髪に移るか
    "eye_none":    c(PERSON + EYE + "black hair" + BG),
    "eye_aqua":    c(PERSON + EYE + "black hair, aqua eyes" + BG),
    "eye_aqua_rev": c(PERSON + EYE + "aqua eyes, black hair" + BG),
    "eye_aqua_concat": c((PERSON + EYE + "black hair", "aqua eyes" + BG)),
    # two-tone と部位ごとの色
    "tone_two":    c(PERSON + BODY + "two-tone dress, black and white dress" + BG),
    "tone_parts":  c(PERSON + BODY + "black jacket, white long skirt" + BG),
}


def post_json(base, path, body):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def get_json(base, path):
    with urllib.request.urlopen(base + path) as r:
        return json.load(r)


def build(workflow, cond, seed, prefix):
    wf = copy.deepcopy(workflow)
    positive = cond["positive"]
    if cond["lora"]:
        # チェックポイントと CLIPSetLastLayer・KSampler の間に LoraLoader を挟む
        wf["2"] = {"class_type": "LoraLoader",
                   "inputs": {"model": ["1", 0], "clip": ["1", 1], "lora_name": STYLE_LORA,
                              "strength_model": STYLE_STRENGTH, "strength_clip": STYLE_STRENGTH}}
        wf["3"]["inputs"]["clip"] = ["2", 1]
        wf["7"]["inputs"]["model"] = ["2", 0]
        add = STYLE_TRIGGER + ", "
        positive = add + positive if isinstance(positive, str) else (add + positive[0], positive[1])
    wf["5"]["inputs"]["text"] = cond["negative"]
    wf["6"]["inputs"]["width"] = cond["width"]
    wf["6"]["inputs"]["height"] = cond["height"]
    if isinstance(positive, str):
        wf["4"]["inputs"]["text"] = positive
    else:
        # 前半と後半を別々に CLIP に通し、トークンの並びの方向につなぐ
        first, second = positive
        wf["4"]["inputs"]["text"] = first
        wf["10"] = {"class_type": "CLIPTextEncode",
                    "inputs": {"clip": ["3", 0], "text": second}}
        wf["11"] = {"class_type": "ConditioningConcat",
                    "inputs": {"conditioning_to": ["4", 0],
                               "conditioning_from": ["10", 0]}}
        wf["7"]["inputs"]["positive"] = ["11", 0]
    wf["7"]["inputs"]["seed"] = seed          # seed は必ず明示する
    wf["9"]["inputs"]["filename_prefix"] = prefix
    return wf


def main():
    out_dir, cond = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    base = sys.argv[4] if len(sys.argv) > 4 else "http://127.0.0.1:8188"
    os.makedirs(os.path.join(out_dir, cond), exist_ok=True)
    with open(os.path.join(HERE, "workflow_api.json")) as f:
        workflow = json.load(f)

    for seed in range(FIRST_SEED, FIRST_SEED + n):
        dst = os.path.join(out_dir, cond, f"{seed}.png")
        if os.path.exists(dst):
            continue
        wf = build(workflow, CONDITIONS[cond], seed, f"debimate_binding/{cond}_{seed}")
        t0 = time.time()
        pid = post_json(base, "/prompt", {"prompt": wf, "client_id": "debimate-binding"})["prompt_id"]
        while True:                           # 自分の prompt_id だけを待つ
            hist = get_json(base, f"/history/{pid}")
            if pid in hist:
                break
            time.sleep(2)
        status = hist[pid].get("status", {})
        if status.get("status_str") != "success":
            sys.exit(f"{cond} seed={seed} failed: {status}")
        img = hist[pid]["outputs"]["9"]["images"][0]
        q = urllib.parse.urlencode({"filename": img["filename"],
                                    "subfolder": img["subfolder"], "type": img["type"]})
        with urllib.request.urlopen(f"{base}/view?{q}") as r, open(dst, "wb") as f:
            f.write(r.read())
        print(f"{cond} seed={seed} {time.time() - t0:.1f}s prompt_id={pid}", flush=True)


if __name__ == "__main__":
    main()
