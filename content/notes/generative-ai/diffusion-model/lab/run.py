"""拡散モデルのノートの生成実験。依頼は 1 件ずつ送り、自分の prompt_id だけを待つ。

使い方: python3 run.py <実験名> <PNG の保存先>
  trajectory  28 ステップの途中（k = 0, 2, 4, 7, 10, 14, 20, 28）で止め、x_k と予測した x0 を画像に戻す
  forward     描き終えた潜在に、列の j 番目の sigma のノイズを足して画像に戻す
  steps       ステップ数 8 / 16 / 28 / 50（euler、normal）
  samplers    28 ステップで euler_ancestral（normal）と dpmpp_2m（karras）
  cfg         CFG 1.0 と 9.0（euler、28 ステップ）
  rerun       steps の 28 ステップをもう一度送り、画素が一致するかを確かめる
結果は <実験名>_log.json に追記する（prompt_id・実行秒数・cached_nodes・送る直前の負荷）。
"""
import json
import math
import os
import sys
import zlib

import comfy
import wf

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEDULE = json.load(open(os.path.join(HERE, "schedule.json")))["normal"]   # schedule.py の出力


def scale(k):
    return 1 / math.sqrt(1 + SCHEDULE[k] ** 2)


def pixels(path):
    """PNG の画素（IDAT を展開したバイト列）。Pillow を使わずに比べるため。"""
    data = open(path, "rb").read()
    pos, idat = 8, b""
    while pos < len(data):
        n = int.from_bytes(data[pos:pos + 4], "big")
        if data[pos + 4:pos + 8] == b"IDAT":
            idat += data[pos + 8:pos + 8 + n]
        pos += 12 + n
    return zlib.decompress(idat)


def log(name, row):
    path = os.path.join(HERE, f"{name}_log.json")
    rows = json.load(open(path)) if os.path.exists(path) else []
    row = {k: v for k, v in row.items() if k != "outputs"}
    rows.append(row)
    json.dump(rows, open(path, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(row, ensure_ascii=False))


def main():
    name, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    if name == "trajectory":
        for k in [0, 2, 4, 7, 10, 14, 20, 28]:
            w, nodes = wf.partial(k, scale(k))
            files = {nodes["x"]: os.path.join(out, f"x_{k:02d}.png")}
            if "x0" in nodes:
                files[nodes["x0"]] = os.path.join(out, f"x0_{k:02d}.png")
            log(name, {"k": k, "sigma": SCHEDULE[k], "scale": scale(k), **comfy.run(w, files)})
    elif name == "forward":
        js = [27, 24, 20, 14, 10, 4, 1]
        w, nodes = wf.forward(js, [scale(j) for j in js])
        files = {nodes[j]: os.path.join(out, f"fwd_{j:02d}.png") for j in js}
        r = comfy.run(w, files)
        latent = r["outputs"]["99"]["latents"][0]
        log(name, {"js": js, "sigmas": [SCHEDULE[j] for j in js], "latent_file": latent, **r})
    elif name in ("steps", "samplers", "cfg", "rerun"):
        jobs = {
            "steps": [(f"steps_{n:02d}", dict(steps=n)) for n in (8, 16, 28, 50)],
            "samplers": [("sampler_euler_ancestral", dict(steps=28, sampler="euler_ancestral")),
                         ("sampler_dpmpp_2m_karras", dict(steps=28, sampler="dpmpp_2m", scheduler="karras"))],
            "cfg": [(f"cfg_{c:.1f}", dict(steps=28, cfg=c)) for c in (1.0, 9.0)],
            "rerun": [("rerun_steps_28", dict(steps=28))],
        }[name]
        for tag, kw in jobs:
            png = os.path.join(out, tag + ".png")
            r = comfy.run(wf.ksampler(**kw), {"9": png})
            row = {"tag": tag, **kw, **r}
            if name == "rerun":
                row["identical_to_steps_28"] = pixels(png) == pixels(os.path.join(out, "steps_28.png"))
                row["identical_to_trajectory_x_28"] = pixels(png) == pixels(os.path.join(out, "x_28.png"))
            log(name, row)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
