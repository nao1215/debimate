"""生成した PNG から、色がどこに付いたかと人数を機械で測る。

- 領域: CLIPSeg（CIDAS/clipseg-rd64-refined）に "hair" "eyes" "shirt" "skirt" などの
  語を渡し、確率 0.5 以上の画素をその物の領域とする
- 色: 領域の画素を HSV にし、彩度と明るさの足りない画素（黒・白・灰）を除いて色相で数える
- 人数・髪の色・露出: WD tagger（SmilingWolf/wd-vit-tagger-v3）のタグの確率
CPU で動く。

使い方:
    python measure.py <PNG の保存先> <結果の JSON>
"""
import csv
import glob
import json
import os
import sys

import numpy as np
import onnxruntime as ort
import torch
from huggingface_hub import hf_hub_download
from PIL import Image
from transformers import CLIPSegForImageSegmentation, CLIPSegProcessor

SEG = "CIDAS/clipseg-rd64-refined"
TAGGER = "SmilingWolf/wd-vit-tagger-v3"

# 色相の範囲（度）。aqua は青緑、blue は青
HUES = {"aqua": (150, 200), "blue": (205, 255)}


class Seg:
    def __init__(self):
        self.proc = CLIPSegProcessor.from_pretrained(SEG)
        self.model = CLIPSegForImageSegmentation.from_pretrained(SEG).eval()

    def masks(self, img, words):
        inp = self.proc(text=words, images=[img] * len(words), padding=True,
                        return_tensors="pt")
        with torch.no_grad():
            logits = self.model(**inp).logits            # [語の数, 352, 352]
        prob = torch.sigmoid(logits).reshape(len(words), 1, 352, 352)
        prob = torch.nn.functional.interpolate(prob, size=img.size[::-1], mode="bilinear")
        return {w: prob[i, 0].numpy() >= 0.5 for i, w in enumerate(words)}


class Tagger:
    def __init__(self):
        self.sess = ort.InferenceSession(hf_hub_download(TAGGER, "model.onnx"))
        with open(hf_hub_download(TAGGER, "selected_tags.csv")) as f:
            self.names = [r["name"] for r in csv.DictReader(f)]

    def tags(self, img):
        size = self.sess.get_inputs()[0].shape[1]       # 448
        sq = Image.new("RGB", (max(img.size),) * 2, (255, 255, 255))
        sq.paste(img, ((sq.width - img.width) // 2, (sq.height - img.height) // 2))
        x = np.asarray(sq.resize((size, size), Image.BICUBIC), dtype=np.float32)[:, :, ::-1]
        prob = self.sess.run(None, {self.sess.get_inputs()[0].name: x[None].copy()})[0][0]
        return dict(zip(self.names, prob.tolist()))


def hsv(img):
    a = np.asarray(img.convert("HSV"), dtype=np.float32)
    return a[..., 0] * 360 / 255, a[..., 1] / 255, a[..., 2] / 255


def hue_share(h, s, v, mask, name):
    """領域のうち、色の付いた画素（彩度 0.25 以上・明るさ 0.2 以上）で name の色相の割合。"""
    lo, hi = HUES[name]
    colored = mask & (s >= 0.25) & (v >= 0.2)
    hit = colored & (h >= lo) & (h <= hi)
    return float(hit.sum() / max(mask.sum(), 1))


def lab_mean(img, mask):
    """領域の平均の L*a*b*（sRGB, D65）。"""
    rgb = np.asarray(img, dtype=np.float64)[mask] / 255
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    lab = np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)
    return lab.mean(0).round(2).tolist()


def measure(path, seg, tagger):
    cond = os.path.basename(os.path.dirname(path))
    kind = cond[2:] if cond.startswith("s_") else cond   # s_ は画風 LoRA を当てた条件
    img = Image.open(path).convert("RGB")
    h, s, v = hsv(img)
    r = {"cond": cond, "seed": int(os.path.basename(path)[:-4])}
    if kind.startswith(("eye", "rep", "light")):
        m = seg.masks(img, ["hair", "eyes", "face"])
        hair = m["hair"] & ~m["eyes"]                    # 目の画素は髪から除く
        r["hair_px"] = int(hair.sum())
        r["hair_aqua"] = hue_share(h, s, v, hair, "aqua")
        r["eyes_aqua"] = hue_share(h, s, v, m["eyes"], "aqua")
        if cond.startswith("s_"):                        # 立ち絵: シャツとスカートの色も見る
            m2 = seg.masks(img, ["shirt", "skirt"])
            for part in ("shirt", "skirt"):
                r[part + "_blue"] = hue_share(h, s, v, m2[part], "blue")
        r["lab_all"] = lab_mean(img, np.ones_like(hair))
        r["lab_face"] = lab_mean(img, m["face"]) if m["face"].any() else None
    elif kind.startswith("tone"):
        m = seg.masks(img, ["dress", "clothes"])
        cl = m["dress"] | m["clothes"]
        dark = cl & (v < 0.3)
        ys, xs = np.nonzero(cl)
        cx, cy = int(np.median(xs)), int(np.median(ys))   # 服の領域の中心で 4 つに割る
        def share(part):
            return float((dark & part).sum() / max((cl & part).sum(), 1))
        cols = np.arange(cl.shape[1])[None, :]
        rows = np.arange(cl.shape[0])[:, None]
        r["dark_left"], r["dark_right"] = share(cols < cx), share(cols >= cx)
        r["dark_top"], r["dark_bottom"] = share(rows < cy), share(rows >= cy)
        r["lr"] = abs(r["dark_left"] - r["dark_right"])
        r["tb"] = abs(r["dark_top"] - r["dark_bottom"])
    if kind.startswith(("ar", "eye", "rep", "tone")):
        t = tagger.tags(img)
        for k in ("solo", "1girl", "2girls", "multiple_girls", "multiple_views",
                  "aqua_hair", "multicolored_hair", "streaked_hair", "two-tone_hair",
                  "colored_inner_hair", "sensitive", "questionable", "explicit"):
            if k in t:
                r["tag:" + k] = round(t[k], 4)
    return r


def main():
    src, out = sys.argv[1], sys.argv[2]
    seg, tagger = Seg(), Tagger()
    rows = [measure(p, seg, tagger)
            for p in sorted(glob.glob(os.path.join(src, "*", "*.png")))]
    with open(out, "w") as f:
        json.dump(rows, f, indent=1)
    print(f"{len(rows)} images")


if __name__ == "__main__":
    main()
