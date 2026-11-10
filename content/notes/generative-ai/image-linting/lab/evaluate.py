"""features.json（lint_features.py）と labels.json（目で付けた合否）から、
検査ごとの誤った棄却・誤った合格と、検査を直列に重ねた時の通過率を数える。
最後に、顔の切り抜きで「同じ服装か」を CLIP とタグの cos で比べる。

閾値と必須のタグは、合否のラベルを付ける前に決めて、この下の定数に書いた値のまま動かしていない。

使い方:
    python3 evaluate.py <features.json> <labels.json> [結果の JSON]
"""
import itertools
import json
import math
import sys

import numpy as np

TAG = 0.35                       # タグが「出ている」とみなす確率
CLIP_MIN = 0.80                  # 基準の絵との CLIP の cos の下限
BORDER_MAX = 30.0                # 左右の端の平均色と白の距離（RGB、0〜441）の上限
NEON_MAX = 0.02                  # 彩度も明るさも高い画素の割合の上限

OUTFIT = {                       # 服装ごとに必須のタグ（| はどれか 1 つ）
    "A": ["red_jacket", "black_hair", "denim|jeans"],
    "B": ["green_sweater", "blonde_hair", "black_skirt"],
    "C": ["brown_hair", "suit|blue_suit", "red_necktie"],
    "D": ["grey_hair|white_hair", "raincoat|yellow_raincoat", "grey_pants"],
}
SUBJECT = {"A": "1girl", "B": "1girl", "C": "1boy", "D": "1girl"}
CROWD = ["multiple_girls", "2girls", "3girls", "multiple_boys", "2boys", "3boys",
         "multiple_views", "1girl", "1boy"]          # 自分の SUBJECT は後で外す
BROKEN = ["bad_hands", "bad_anatomy", "extra_arms", "extra_digits", "bad_feet",
          "text", "english_text", "watermark", "signature"]
RATINGS = ["general", "sensitive", "questionable", "explicit"]


def make_checks(names):
    ix = {n: i for i, n in enumerate(names)}

    def p(rec, tag):
        return rec["tags"][ix[tag]] if tag in ix else 0.0

    def any_of(rec, alt):
        return max(p(rec, t) for t in alt.split("|")) >= TAG

    def crowd_tags(rec, d):
        bad = [t for t in CROWD if t != SUBJECT[d] and p(rec, t) >= TAG]
        return not bad and p(rec, SUBJECT[d]) >= TAG

    return [
        ("人数（タグ）", crowd_tags),
        ("人数（検出器）", lambda r, d: len(r["people"]) == 1 and len(r["faces"]) == 1),
        ("崩れ・文字（タグ）", lambda r, d: all(p(r, t) < TAG for t in BROKEN)),
        ("露出（レーティング）",
         lambda r, d: max(RATINGS, key=lambda t: p(r, t)) == "general"),
        ("服（タグ）", lambda r, d: all(any_of(r, a) for a in OUTFIT[d])),
        ("色（統計）", lambda r, d: r["color"]["border_dist_from_white"] <= BORDER_MAX
         and r["color"]["neon_ratio"] <= NEON_MAX),
        ("基準の絵との近さ（CLIP）", lambda r, d: r["clip_to_ref"] >= CLIP_MIN),
    ]


def cos(a, b):
    a, b = np.asarray(a), np.asarray(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


# 顔の切り抜きのタグの cos から外す語（表情・視線・構図・背景・人数・レーティング）
STOP = {"solo", "1girl", "1boy", "portrait", "looking_at_viewer", "closed_mouth",
        "open_mouth", "parted_lips", "smile", "expressionless", "blush", "upper_body",
        "white_background", "simple_background", "transparent_background",
        "grey_background", "close-up", "light_smile", "male_focus", "general",
        "sensitive", "questionable", "explicit"}


def main():
    feats = json.load(open(sys.argv[1]))
    labels = json.load(open(sys.argv[2]))
    out_path = sys.argv[3] if len(sys.argv) > 3 else None
    names, imgs = feats["tag_names"], feats["images"]
    for name, rec in imgs.items():
        ref = imgs[f"{name[0]}_ref_20261100"]
        rec["clip_to_ref"] = cos(rec["clip"], ref["clip"])
    checks = make_checks(names)
    vocab = set(names)
    used = set(CROWD + BROKEN + RATINGS) | {t for v in OUTFIT.values() for a in v
                                            for t in a.split("|")}
    print("タグ付けのモデルの語彙に無いタグ（確率は常に 0 として扱われる）:",
          sorted(used - vocab))

    targets = sorted(n for n in imgs if "_ref_" not in n)
    good = [n for n in targets if labels[n]["ok"]]
    bad = [n for n in targets if not labels[n]["ok"]]
    print(f"評価する画像 {len(targets)} 枚（目で見て合格 {len(good)}、不合格 {len(bad)}）")
    print("基準の絵 4 枚の合否:",
          {n: all(f(imgs[n], n[0]) for _, f in checks) for n in sorted(imgs) if "_ref_" in n})

    passed = {c: {n: f(imgs[n], n[0]) for n in targets} for c, f in checks}
    rows = []
    print(f"\n{'検査':<22}{'誤った棄却':>10}{'誤った合格':>10}{'単独で止めた不合格':>12}")
    for c, _ in checks:
        fr = [n for n in good if not passed[c][n]]
        fa = [n for n in bad if passed[c][n]]
        only = [n for n in bad if not passed[c][n]
                and all(passed[o][n] for o, _ in checks if o != c)]
        rows.append({"check": c, "false_reject": len(fr), "false_accept": len(fa),
                     "caught_bad": len(bad) - len(fa), "only_this": len(only),
                     "false_reject_names": fr})
        print(f"{c:<22}{len(fr):>4} / {len(good):<4}{len(fa):>5} / {len(bad):<4}{len(only):>8}")

    # 直列に重ねた時、合格の絵が全部を通る割合（実測）と、独立を仮定した積
    print("\n段数  実測（合格の絵が全部を通る）  各段の通過率の積  (1-p)^n（p は各段の平均）")
    stages = []
    for k in range(1, len(checks) + 1):
        cs = [c for c, _ in checks[:k]]
        all_pass = sum(all(passed[c][n] for c in cs) for n in good) / len(good)
        rates = [sum(passed[c][n] for n in good) / len(good) for c in cs]
        prod = math.prod(rates)
        pbar = 1 - sum(rates) / len(rates)
        stages.append({"n": k, "measured": all_pass, "product": prod,
                       "mean_p": pbar, "formula": (1 - pbar) ** k})
        print(f"{k:>3}   {all_pass:>8.3f}                     {prod:>8.3f}        "
              f"{(1 - pbar) ** k:>8.3f}  (p={pbar:.3f})")
    caught = sum(any(not passed[c][n] for c, _ in checks) for n in bad)
    print(f"\n7 段全部で止めた不合格: {caught} / {len(bad)}")
    print(f"5% の誤りを 5 段: (1-0.05)^5 = {0.95 ** 5:.3f}")

    # 顔の切り抜きで、同じ服装か別の服装かを見分けられるか（neon 以外で合格の絵と基準の絵）
    keep = [i for i, n in enumerate(names) if n not in STOP and feats.get("tag_categories",
            [0] * len(names))[i] == 0]
    faces = sorted(n for n in imgs if "_neon_" not in n and "face_clip" in imgs[n]
                   and labels.get(n, {"ok": True})["ok"])
    same, diff = {"clip": [], "tag": []}, {"clip": [], "tag": []}
    for a, b in itertools.combinations(faces, 2):
        ta = [imgs[a]["face_tags"][i] for i in keep]
        tb = [imgs[b]["face_tags"][i] for i in keep]
        bucket = same if a[0] == b[0] else diff
        bucket["clip"].append(cos(imgs[a]["face_clip"], imgs[b]["face_clip"]))
        bucket["tag"].append(cos(ta, tb))
    print(f"\n顔の切り抜き {len(faces)} 枚（neon 以外で目で見て合格の絵と、基準の絵）")
    for k in ("clip", "tag"):
        print(f"  {k:<4} 同じ服装 {len(same[k])} 組 {min(same[k]):.2f}〜{max(same[k]):.2f}"
              f"（中央値 {np.median(same[k]):.2f}） / 別の服装 {len(diff[k])} 組 "
              f"{min(diff[k]):.2f}〜{max(diff[k]):.2f}（中央値 {np.median(diff[k]):.2f}）")

    if out_path:
        json.dump({"n_good": len(good), "n_bad": len(bad), "checks": rows,
                   "stages": stages, "identity": {"same": same, "diff": diff}},
                  open(out_path, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
