"""生成した PNG から、検品に使う値を計算して features.json に書く。

使うモデル（全て ONNX、CPU で動かす）:
  WD ViT Tagger v3          : タグの確率（人数・露出・服・崩れ）
  CLIP ViT-B/32（画像側）   : 画像の埋め込み（基準の絵との近さ）
  anime_face_detection v1.4_s / anime_person_detection v1.3_s : 顔と人物の数
色の統計は NumPy だけで計算する。

使い方:
    python3 lint_features.py <PNG のディレクトリ> <モデルのディレクトリ> <出力 JSON>
"""
import json
import os
import sys

import numpy as np
import onnxruntime as ort
from PIL import Image

OPTS = ort.SessionOptions()
OPTS.intra_op_num_threads = 8


def session(path):
    return ort.InferenceSession(path, OPTS, providers=["CPUExecutionProvider"])


# ---- WD tagger -------------------------------------------------------------
def load_tagger(d):
    import csv
    with open(os.path.join(d, "selected_tags.csv")) as f:
        rows = list(csv.DictReader(f))
    return session(os.path.join(d, "model.onnx")), [r["name"] for r in rows], \
        [int(r["category"]) for r in rows]


def tag_probs(sess, img):
    """白で正方形に埋めて 448 に縮め、BGR・0〜255 の float で渡す（モデルの前処理）。"""
    w, h = img.size
    s = max(w, h)
    canvas = Image.new("RGB", (s, s), (255, 255, 255))
    canvas.paste(img, ((s - w) // 2, (s - h) // 2))
    x = np.asarray(canvas.resize((448, 448), Image.BICUBIC), dtype=np.float32)[:, :, ::-1]
    return sess.run(None, {"input": x[None].copy()})[0][0]


# ---- CLIP ------------------------------------------------------------------
MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)


def clip_embed(sess, img):
    """短い辺を 224 に縮めて中央を切り抜く（preprocessor_config.json と同じ）。"""
    w, h = img.size
    r = 224 / min(w, h)
    img = img.resize((round(w * r), round(h * r)), Image.BICUBIC)
    w, h = img.size
    l, t = (w - 224) // 2, (h - 224) // 2
    x = np.asarray(img.crop((l, t, l + 224, t + 224)), dtype=np.float32) / 255.0
    x = ((x - MEAN) / STD).transpose(2, 0, 1)[None]
    e = sess.run(None, {"pixel_values": x})[0][0]
    return e / np.linalg.norm(e)


# ---- YOLO 系の検出器（顔・人物） -------------------------------------------
def detect(sess, img, thr, size=640, iou=0.7):
    w, h = img.size
    r = size / max(w, h)
    nw, nh = round(w * r), round(h * r)
    canvas = Image.new("RGB", (size, size), (114, 114, 114))
    canvas.paste(img.resize((nw, nh), Image.BILINEAR), (0, 0))
    x = (np.asarray(canvas, dtype=np.float32) / 255.0).transpose(2, 0, 1)[None]
    out = sess.run(None, {"images": x})[0][0]           # [4 + クラス数, 候補数]
    if out.shape[0] > out.shape[1]:
        out = out.T
    boxes, scores = out[:4].T, out[4:].max(axis=0)
    keep = scores >= thr
    boxes, scores = boxes[keep], scores[keep]
    xyxy = np.stack([boxes[:, 0] - boxes[:, 2] / 2, boxes[:, 1] - boxes[:, 3] / 2,
                     boxes[:, 0] + boxes[:, 2] / 2, boxes[:, 1] + boxes[:, 3] / 2], 1) / r
    order, picked = scores.argsort()[::-1], []
    while order.size:                                    # 重なった候補を 1 つにまとめる（NMS）
        i = order[0]
        picked.append(i)
        a = xyxy[i]
        b = xyxy[order[1:]]
        inter = (np.clip(np.minimum(a[2], b[:, 2]) - np.maximum(a[0], b[:, 0]), 0, None) *
                 np.clip(np.minimum(a[3], b[:, 3]) - np.maximum(a[1], b[:, 1]), 0, None))
        area = lambda z: (z[..., 2] - z[..., 0]) * (z[..., 3] - z[..., 1])
        order = order[1:][inter / (area(a) + area(b) - inter + 1e-9) < iou]
    return [[float(v) for v in xyxy[i]] + [float(scores[i])] for i in picked]


# ---- 色の統計 ---------------------------------------------------------------
def color_stats(img):
    x = np.asarray(img, dtype=np.float32) / 255.0
    h, w, _ = x.shape
    m = max(4, w // 20)                                  # 左右の端の帯（背景のはずの所）
    border = np.concatenate([x[:, :m].reshape(-1, 3), x[:, -m:].reshape(-1, 3)])
    mx, mn = x.max(axis=2), x.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    neon = float(((sat > 0.85) & (mx > 0.85)).mean())   # 彩度も明るさも高い画素の割合
    return {
        "border_rgb": [float(v) for v in border.mean(axis=0) * 255],
        "border_dist_from_white": float(np.linalg.norm((1 - border.mean(axis=0)) * 255)),
        "neon_ratio": neon,
        "mean_saturation": float(sat.mean()),
    }


def main():
    png_dir, model_dir, out_path = sys.argv[1:4]
    tagger, names, cats = load_tagger(os.path.join(model_dir, "wd-vit-tagger-v3"))
    clip = session(os.path.join(model_dir, "clip-vit-base-patch32-onnx", "vision_model.onnx"))
    dets = {}
    for key, d in [("face", "face_detect_v1.4_s"), ("person", "person_detect_v1.3_s")]:
        with open(os.path.join(model_dir, d, "threshold.json")) as f:
            dets[key] = (session(os.path.join(model_dir, d, "model.onnx")),
                         json.load(f)["threshold"])

    result = {"tag_names": names, "tag_categories": cats, "images": {}}
    for fn in sorted(os.listdir(png_dir)):
        if not fn.endswith(".png"):
            continue
        img = Image.open(os.path.join(png_dir, fn)).convert("RGB")
        p = tag_probs(tagger, img)
        faces = detect(dets["face"][0], img, dets["face"][1])
        people = detect(dets["person"][0], img, dets["person"][1])
        rec = {
            "tags": [round(float(v), 4) for v in p],
            "clip": [round(float(v), 6) for v in clip_embed(clip, img)],
            "faces": faces, "people": people, "color": color_stats(img),
        }
        if faces:                                         # 一番確からしい顔の切り抜き
            x0, y0, x1, y1, _ = max(faces, key=lambda b: b[4])
            pad = 0.25 * (x1 - x0)
            crop = img.crop((max(0, x0 - pad), max(0, y0 - pad),
                             min(img.width, x1 + pad), min(img.height, y1 + pad)))
            rec["face_tags"] = [round(float(v), 4) for v in tag_probs(tagger, crop)]
            rec["face_clip"] = [round(float(v), 6) for v in clip_embed(clip, crop)]
        result["images"][fn[:-4]] = rec
        print(f"{fn}: faces={len(faces)} people={len(people)} "
              f"border={rec['color']['border_dist_from_white']:.1f} "
              f"neon={rec['color']['neon_ratio']:.3f}", flush=True)
    with open(out_path, "w") as f:
        json.dump(result, f)


if __name__ == "__main__":
    main()
