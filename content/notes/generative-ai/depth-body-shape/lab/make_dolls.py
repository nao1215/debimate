"""MPFB で成人女性の 3D モデルを 2 体作り、.blend に保存する（Blender 4.5 + MPFB 2.0.18）。

- real: MPFB の既定の比率（macro の値を中くらいにした人体）
- anime: real に、太もも・すねを長くする target と、頭を小さくする target を足した人体

使い方: blender --background --python make_dolls.py -- <保存先のディレクトリ>
出力: <保存先>/real.blend、anime.blend、dolls.json（身長・頭の高さ・頭身・股下の比）
"""
import json
import os
import sys

import bpy
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)
MPFB_DIR = os.path.dirname(__import__("bl_ext.user_default.mpfb", fromlist=["x"]).__file__)
TARGETS = os.path.join(MPFB_DIR, "data", "targets")

# gender 0.0 = 女性、age 0.5 = 25 歳前後。体型の値は中くらい
MACRO = {"gender": 0.0, "age": 0.5, "muscle": 0.5, "weight": 0.5, "proportions": 0.5, "height": 0.5,
         "cupsize": 0.5, "firmness": 0.5, "race": {"asian": 0.34, "caucasian": 0.33, "african": 0.33}}
# アニメ体型: 脚を長く、頭を小さく（値は target の重み 0〜1）
ANIME = [("legs/upperlegs-height-incr.target.gz", 1.0), ("legs/lowerlegs-height-incr.target.gz", 1.0),
         ("head/head-scale-vert-decr.target.gz", 0.6), ("head/head-scale-horiz-decr.target.gz", 0.5),
         ("head/head-scale-depth-decr.target.gz", 0.5)]


def world_verts(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    return [obj.matrix_world @ v.co for v in ev.data.vertices], ev


def measure(body):
    """身長、頭の高さ（頭の頂点グループの重みが 0.5 以上の頂点の上下の幅）、股の高さ。"""
    co, ev = world_verts(body)
    zmin, zmax = min(v.z for v in co), max(v.z for v in co)
    gi = body.vertex_groups["head"].index
    head = [co[v.index].z for v in ev.data.vertices for g in v.groups if g.group == gi and g.weight >= 0.5]
    # 股の高さ: 左右の太ももの頂点グループの、上端の低い方
    crotch = []
    for name in ("thigh_l", "thigh_r"):
        ti = body.vertex_groups[name].index
        crotch.append(max(co[v.index].z for v in ev.data.vertices for g in v.groups if g.group == ti and g.weight >= 0.5))
    h, hh = zmax - zmin, max(head) - min(head)
    return {"height_m": round(h, 3), "head_m": round(hh, 3), "heads_tall": round(h / hh, 2),
            "inseam_ratio": round((min(crotch) - zmin) / h, 3)}


def make(kind):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    body = HumanService.create_human(macro_detail_dict=MACRO, feet_on_ground=True, scale=0.1)
    if kind == "anime":
        for rel, w in ANIME:
            TargetService.load_target(body, os.path.join(TARGETS, rel), weight=w)
        bpy.context.view_layer.update()
        # 脚は下へ伸びるので、足の裏が z = 0 に戻るよう持ち上げてから位置を確定する
        co, _ = world_verts(body)
        body.location.z -= min(v.z for v in co)
        bpy.ops.object.select_all(action="DESELECT")
        body.select_set(True)
        bpy.context.view_layer.objects.active = body
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    HumanService.add_builtin_rig(body, "game_engine", import_weights=True)
    m = measure(body)
    print("DOLL", kind, m)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{kind}.blend"))
    return m


json.dump({k: make(k) for k in ("real", "anime")}, open(os.path.join(OUT, "dolls.json"), "w"), indent=1)
