"""生成した絵に、服のタグが付くかを WD EVA02-Large Tagger v3 で数える。

モデルは https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3 の model.onnx と selected_tags.csv。
前処理はモデルの配布元の手順に合わせる（白地の正方形に置いて 448 px に縮め、BGR の 0〜255 の float）。

使い方: uv run --with onnxruntime==1.20.1 --with pillow==12.0.0 --with numpy==2.1.3 \
          python clothes_tags.py <model.onnx と selected_tags.csv のディレクトリ> <結果の JSON> <PNG>...
"""
import csv
import json
import os
import sys

import numpy as np
import onnxruntime as ort
from PIL import Image

# 見るタグ: 体に貼り付く服と、厚みのある服
WATCH = ["skin tight", "bodysuit", "leggings", "tight pants", "pants", "baggy pants", "oversized clothes",
         "armor", "breastplate", "pauldrons", "armored boots", "cape"]


def main():
    d, out, pngs = sys.argv[1], sys.argv[2], sys.argv[3:]
    names = [t["name"].replace("_", " ") for t in csv.DictReader(open(os.path.join(d, "selected_tags.csv")))]
    sess = ort.InferenceSession(os.path.join(d, "model.onnx"), providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    size = inp.shape[1]
    res = {}
    for p in pngs:
        im = Image.open(p).convert("RGB")
        s = max(im.size)
        sq = Image.new("RGB", (s, s), (255, 255, 255))
        sq.paste(im, ((s - im.width) // 2, (s - im.height) // 2))
        x = np.asarray(sq.resize((size, size), Image.BICUBIC), dtype=np.float32)[:, :, ::-1]
        pr = sess.run(None, {inp.name: np.ascontiguousarray(x[None])})[0][0]
        prob = dict(zip(names, pr.tolist()))
        tag = os.path.basename(p)[:-4]
        res[tag] = {w: round(prob[w], 3) for w in WATCH}
        print(tag, {w: v for w, v in res[tag].items() if v >= 0.35}, flush=True)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
