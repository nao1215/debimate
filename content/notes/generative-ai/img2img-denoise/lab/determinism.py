"""同じ seed・同じワークフローで描き直して、画素が一致するかを確かめる。

  - 実験 1 の crisp・denoise 0.6（workflow_img2img.json）
  - 実験 3 の 1 段目（画風 LoRA を当てた人物。LoRA の名前と起動語は person_lora.py と同じ環境変数から読む）
使い方: python3 determinism.py <下絵のディレクトリ> <PNG のディレクトリ> <実験 3 の seed>
"""
import json
import os
import sys

import comfy
import person_lora

HERE = os.path.dirname(os.path.abspath(__file__))


def same(a, b):
    """PNG を画素で比べる（Pillow を使わず、ComfyUI の PNG を zlib で展開して比べる）。"""
    import zlib

    def pixels(path):
        data = open(path, "rb").read()
        pos, idat = 8, b""
        while pos < len(data):
            n = int.from_bytes(data[pos:pos + 4], "big")
            kind = data[pos + 4:pos + 8]
            if kind == b"IDAT":
                idat += data[pos + 8:pos + 8 + n]
            pos += 12 + n
        return zlib.decompress(idat)

    return pixels(a) == pixels(b)


def main():
    sk, png = sys.argv[1], sys.argv[2]
    wf = json.load(open(os.path.join(HERE, "workflow_img2img.json")))
    wf["5"]["inputs"]["image"] = comfy.upload(os.path.join(sk, "sketch_crisp.png"))
    wf["7"]["inputs"]["denoise"] = 0.6
    out = os.path.join(png, "rerun_crisp_060.png")
    r = comfy.run(wf, out, "9")
    print("crisp_060", r["prompt_id"], r["seconds"], "identical:", same(out, os.path.join(png, "crisp_060.png")))
    seed = int(sys.argv[3])
    out = os.path.join(png, f"rerun_person_{seed}_1x.png")
    r = person_lora.send(person_lora.first_stage(seed, "debimate_img2img/person_1x"), out, "9")
    print("person_1x", r["prompt_id"], r["seconds"], "identical:",
          same(out, os.path.join(png, f"person_{seed}_1x.png")))

if __name__ == "__main__":
    main()
