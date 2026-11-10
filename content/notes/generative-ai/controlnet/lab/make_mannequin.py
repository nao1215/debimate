"""MPFB で成人の人体（人形）と骨組みを作り、.blend に保存する（Blender 4.5 + MPFB 2.0.18）。

使い方: blender --background --python make_mannequin.py -- <保存先の .blend>
"""
import sys

import bpy
from bl_ext.user_default.mpfb.services.humanservice import HumanService

out = sys.argv[sys.argv.index("--") + 1]
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)

# gender 1.0 = 男性、age 0.5 = 25 歳前後（MPFB の macro の既定の範囲）。体型は中くらい
macro = {"gender": 1.0, "age": 0.5, "muscle": 0.5, "weight": 0.5, "proportions": 0.5, "height": 0.5,
         "race": {"asian": 0.34, "caucasian": 0.33, "african": 0.33}}
body = HumanService.create_human(macro_detail_dict=macro, feet_on_ground=True, scale=0.1)
arm = HumanService.add_builtin_rig(body, "game_engine", import_weights=True)
print("DIMS", tuple(round(v, 3) for v in body.dimensions), "ARM", arm.name)
bpy.ops.wm.save_as_mainfile(filepath=out)
