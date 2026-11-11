"""基準の絵（base.png）と各画像の近さを数える。

  python3 metrics.py faces <PNG のディレクトリ> faces.json            # 顔の切り抜きと CLIP の近さ（torch と transformers）
  python3 metrics.py tags  <PNG のディレクトリ> faces.json metrics.json  # WD tagger のタグ（onnxruntime）

手元では 1 段目を ComfyUI の venv（torch 2.12・transformers 5.17）、2 段目を onnxruntime 1.30 の venv で動かした。

使うモデル（環境変数で場所を変えられる）
  CLIPSEG_MODEL  CIDAS/clipseg-rd64-refined   文字で指定した物の範囲を推定する。"face" の範囲を顔の切り抜きにする
                 https://huggingface.co/CIDAS/clipseg-rd64-refined
  CLIP_MODEL     openai/clip-vit-large-patch14   画像の埋め込み
                 https://huggingface.co/openai/clip-vit-large-patch14
  WD_TAGGER      wd-eva02-large-tagger-v3 の model.onnx と selected_tags.csv を置いたディレクトリ
                 https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3

数えるもの
  face_clip  顔の切り抜きどうしの CLIP の画像埋め込みの cos 類似度（基準の顔と比べる）
  face_tags  顔の切り抜きのタグ（確率 0.35 以上、表情・視線・構図の語を除く）の Jaccard 係数（基準と比べる）
  attrs      全体の画像で、文面に書いた属性のタグ（髪・目・服）が確率 0.35 以上で出たか
  saturation 全体の画像の HSV の彩度の平均（色の転びの目安）
faces.json には顔の埋め込み（emb）も残す。figures.py が、組の中の総当たりの近さをここから数える。
"""
import csv
import json
import os
import sys

import numpy as np
from PIL import Image

CLIPSEG = os.environ.get("CLIPSEG_MODEL", "CIDAS/clipseg-rd64-refined")
CLIP = os.environ.get("CLIP_MODEL", "openai/clip-vit-large-patch14")
TAGGER = os.environ.get("WD_TAGGER", "wd-eva02-large-tagger-v3")
THRESH = 0.35
# 文面に書いた属性（run.py の CHARACTER の語）に対応するタグ
ATTRS = ["brown hair", "medium hair", "low ponytail", "parted bangs", "green eyes", "earrings",
         "collared shirt", "white shirt", "cardigan", "long sleeves"]
# 顔のタグから除く、表情・視線・構図・背景の語
EXCLUDE = {"smile", "closed mouth", "open mouth", "looking at viewer", "blush", "teeth", ":d", ":)", "grin",
           "parted lips", "looking to the side", "looking away", "portrait", "close-up", "solo", "1girl",
           "simple background", "white background", "upper body", "head tilt", "light smile", "expressionless",
           "eye focus", "smirk", "happy", "indoors", "blurry", "blurry background", "depth of field"}


def names_in(src):
    return sorted(f[:-4] for f in os.listdir(src)
                  if f.endswith(".png") and not f.endswith(("_skeleton.png", "_face.png")))


def faces_stage(src, out):
    import torch
    from transformers import CLIPModel, CLIPProcessor, CLIPSegForImageSegmentation, CLIPSegProcessor
    seg_p, seg = CLIPSegProcessor.from_pretrained(CLIPSEG), CLIPSegForImageSegmentation.from_pretrained(CLIPSEG).eval()
    clip_p, clip = CLIPProcessor.from_pretrained(CLIP), CLIPModel.from_pretrained(CLIP).eval()
    rows, emb = {}, {}
    for n in names_in(src):
        img = Image.open(os.path.join(src, n + ".png")).convert("RGB")
        with torch.no_grad():
            logits = seg(**seg_p(text=["face"], images=[img], return_tensors="pt")).logits
        prob = torch.sigmoid(logits).reshape(logits.shape[-2:]).numpy()
        prob = np.asarray(Image.fromarray((prob * 255).astype("uint8")).resize(img.size)) / 255
        ys, xs = np.where(prob > 0.4)
        # 確率 0.4 を超えた範囲を囲む正方形を顔の切り抜きにする（中心を保ち、長い辺に揃える）
        cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
        half = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2
        box = [int(max(0, cx - half)), int(max(0, cy - half)), int(min(img.width, cx + half)),
               int(min(img.height, cy + half))]
        face = img.crop(box)
        face.save(os.path.join(src, n + "_face.png"))
        with torch.no_grad():
            e = clip.get_image_features(**clip_p(images=face, return_tensors="pt"))
        if not torch.is_tensor(e):
            e = e.pooler_output
        emb[n] = torch.nn.functional.normalize(e, dim=-1)[0].numpy()
        rows[n] = {"face_box": box, "emb": [round(float(v), 6) for v in emb[n]]}
    for n in rows:
        rows[n]["face_clip"] = round(float(np.dot(emb["base"], emb[n])), 3)
    json.dump(rows, open(out, "w"), indent=1, ensure_ascii=False)


class Tagger:
    def __init__(self, d):
        import onnxruntime as ort
        self.sess = ort.InferenceSession(os.path.join(d, "model.onnx"), providers=["CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0]
        self.size = self.inp.shape[1]
        with open(os.path.join(d, "selected_tags.csv")) as f:
            rows = list(csv.DictReader(f))
        self.names = [r["name"].replace("_", " ") for r in rows]
        self.general = [r["category"] == "0" for r in rows]

    def __call__(self, img):
        # 白地に載せて正方形にし、BGR の float32（0〜255）で渡す（WD tagger v3 の前処理）
        s = max(img.size)
        canvas = Image.new("RGB", (s, s), (255, 255, 255))
        canvas.paste(img, ((s - img.width) // 2, (s - img.height) // 2))
        x = np.asarray(canvas.resize((self.size, self.size), Image.BICUBIC), dtype=np.float32)[:, :, ::-1]
        p = self.sess.run(None, {self.inp.name: np.ascontiguousarray(x[None])})[0][0]
        return {n: float(v) for n, v, g in zip(self.names, p, self.general) if g and v >= THRESH}


def tags_stage(src, faces_json, out):
    rows = json.load(open(faces_json))
    tagger = Tagger(TAGGER)
    for n, r in rows.items():
        whole = tagger(Image.open(os.path.join(src, n + ".png")).convert("RGB"))
        r["attrs"] = {a: a in whole for a in ATTRS}
        # 色の転びの目安: 画像全体の HSV の彩度（0〜1）の平均
        hsv = np.asarray(Image.open(os.path.join(src, n + ".png")).convert("HSV"), dtype=np.float32)
        r["saturation"] = round(float(hsv[:, :, 1].mean() / 255), 3)
        face = tagger(Image.open(os.path.join(src, n + "_face.png")).convert("RGB"))
        r["face_tag_list"] = sorted(t for t in face if t not in EXCLUDE)
    base = set(rows["base"]["face_tag_list"])
    for n, r in rows.items():
        mine = set(r["face_tag_list"])
        r["face_tags"] = round(len(base & mine) / len(base | mine), 3)
        r["attrs_ok"] = sum(r["attrs"].values())
        missing = [a for a, ok in r["attrs"].items() if not ok]
        print(f"{n:15s} face_clip={r['face_clip']:.3f} face_tags={r['face_tags']:.3f} "
              f"sat={r['saturation']:.3f} attrs={r['attrs_ok']}/{len(ATTRS)} missing={missing}")
    json.dump(rows, open(out, "w"), indent=1, ensure_ascii=False)


def main():
    if sys.argv[1] == "faces":
        faces_stage(sys.argv[2], sys.argv[3])
    else:
        tags_stage(sys.argv[2], sys.argv[3], sys.argv[4])


if __name__ == "__main__":
    main()
