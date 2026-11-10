"""measure.py の結果を条件ごとに集計し、目で付けたラベルと突き合わせる。

使い方:
    python3 summarize.py measure.json labels.json [集計の JSON]

判定の閾値（measure.json の値に掛ける）
- 髪の色移り: 髪の領域（目を除く）のうち青緑の画素が 0.5% 以上
- 左右の塗り分け: 服の領域を中心で左右に割った時、暗い画素の割合の差が 0.3 以上で、
  上下に割った時の差より大きい
- 複数人: WD tagger の multiple_girls・2girls・multiple_views のどれかが 0.35 以上
"""
import json
import sys
from collections import defaultdict
from statistics import mean

T_HAIR, T_LR, T_MULTI = 0.005, 0.3, 0.35
MULTI_TAGS = ("multiple_girls", "2girls", "multiple_views")
HAIR_TAGS = ("aqua_hair", "multicolored_hair", "streaked_hair", "colored_inner_hair",
             "two-tone_hair")


def kind_of(cond):
    return cond[2:] if cond.startswith("s_") else cond   # s_ は画風 LoRA を当てた条件


def verdict(r):
    c = kind_of(r["cond"])
    if c.startswith(("eye", "rep")):
        v = {"hair_aqua": r["hair_aqua"] >= T_HAIR}
        if "tag:multiple_views" in r:
            v["multi"] = max(r.get("tag:" + k, 0) for k in MULTI_TAGS) >= T_MULTI
        return v
    if c.startswith("tone"):
        return {"split_lr": r["lr"] >= T_LR and r["lr"] > r["tb"]}
    if c.startswith("ar"):
        return {"multi": max(r.get("tag:" + k, 0) for k in MULTI_TAGS) >= T_MULTI}
    return {}


def main():
    rows = json.load(open(sys.argv[1]))
    labels = json.load(open(sys.argv[2]))
    by = defaultdict(list)
    agree = defaultdict(lambda: [0, 0])
    for r in rows:
        key = f'{r["cond"]}/{r["seed"]}'
        v = verdict(r)
        r["verdict"] = v
        by[r["cond"]].append(r)
        for k, val in v.items():
            if key in labels and k in labels[key]:
                agree[k][0] += labels[key][k] == val
                agree[k][1] += 1
    out = {}
    for cond, rs in sorted(by.items()):
        s = {"n": len(rs)}
        k = kind_of(cond)
        if k.startswith(("eye", "rep", "light")):
            s["hair_aqua_rate"] = sum(r["verdict"].get("hair_aqua", False) for r in rs)
            s["hair_aqua_share_mean"] = round(mean(r["hair_aqua"] for r in rs), 4)
            s["hair_aqua_share_range"] = [round(min(r["hair_aqua"] for r in rs), 4),
                                          round(max(r["hair_aqua"] for r in rs), 4)]
            # 比べる対象: WD tagger が髪の色のタグを 0.35 以上で付けた枚数
            s["tagger_hair_tags"] = sum(max(r.get("tag:" + t, 0) for t in HAIR_TAGS) >= T_MULTI
                                        for r in rs)
            s["lab_all_mean"] = [round(mean(r["lab_all"][i] for r in rs), 2) for i in range(3)]
            if "shirt_blue" in rs[0]:
                s["shirt_blue_mean"] = round(mean(r["shirt_blue"] for r in rs), 4)
                s["skirt_blue_mean"] = round(mean(r["skirt_blue"] for r in rs), 4)
            faces = [r["lab_face"] for r in rs if r.get("lab_face")]
            if faces:
                s["lab_face_mean"] = [round(mean(f[i] for f in faces), 2) for i in range(3)]
        if k.startswith("tone"):
            s["split_lr"] = sum(r["verdict"]["split_lr"] for r in rs)
        if k.startswith("ar"):
            s["multi"] = sum(r["verdict"]["multi"] for r in rs)
        out[cond] = s
        print(cond, json.dumps(s, ensure_ascii=False))
    # 目で付けたラベルの集計（服の色・人数・目視の色移り）
    tally = defaultdict(lambda: defaultdict(int))
    for key, lab in labels.items():
        cond = key.split("/")[0]
        for k in ("shirt", "skirt"):
            if k in lab:
                tally[cond][f"{k}={lab[k]}"] += 1
        for k in ("hair_aqua", "multi", "split_lr"):
            if lab.get(k):
                tally[cond][k] += 1
    for cond in sorted(tally):
        print("labels", cond, json.dumps(dict(sorted(tally[cond].items())), ensure_ascii=False))
    # 照明の実験の比べる相手: 語なしの立ち絵の seed 1000〜1003
    base = [r for r in by.get("s_eye_none", []) if r["seed"] < 1004]
    if base:
        s = {"n": len(base),
             "lab_all_mean": [round(mean(r["lab_all"][i] for r in base), 2) for i in range(3)],
             "lab_face_mean": [round(mean(r["lab_face"][i] for r in base), 2) for i in range(3)]}
        out["s_light_control"] = s
        print("s_light_control", json.dumps(s, ensure_ascii=False))
    for k, (ok, n) in agree.items():
        print(f"agreement with eye labels [{k}]: {ok}/{n}")
    if len(sys.argv) > 3:
        json.dump({"conditions": out, "agreement": dict(agree)}, open(sys.argv[3], "w"), indent=1)


if __name__ == "__main__":
    main()
