"""3D モデルの深度マップを、服の厚みなし・ありの 2 通りで書き出す（Blender 4.5 + MPFB 2.0.18）。

使い方: blender --background <real.blend か anime.blend> --python render_depth.py -- poses.json <出力先> <3D モデルの名前>
出力: <出力先>/<3D モデル>_<plain|bulk>_<ポーズ>.png

- ポーズは骨の回転（度）だけで付ける（FK）。2 体で腕の長さは同じなので、同じ回転で同じ形になる
- 服の厚みは、骨ごとの頂点グループを法線方向に Displace で膨らませる（値は poses.json の _bulk、単位 m）。
  Displace は骨組み（Armature）より前に掛けるので、骨と一緒に動く
- 深度マップは近いほど明るい白黒（背景は黒）。カメラは平行投影で、2 体・全ポーズ共通
"""
import json
import math
import os
import sys

import bpy
from mathutils import Euler

argv = sys.argv[sys.argv.index("--") + 1:]
POSES, OUT, DOLL = json.load(open(argv[0])), argv[1], argv[2]
os.makedirs(OUT, exist_ok=True)

scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in bpy.data.objects if o.type == "MESH")
root = bpy.data.objects.new("Facing", None)
scene.collection.objects.link(root)
arm.parent = root

# 服の厚み（最初は強さ 0 で置き、bulk の回だけ値を入れる）
bulk = {}
for name, amount in POSES["_bulk"].items():
    m = body.modifiers.new("bulk_" + name, "DISPLACE")
    m.vertex_group, m.strength, m.mid_level, m.direction = name, 0.0, 0, "NORMAL"
    body.modifiers.move(body.modifiers.find(m.name), 0)
    bulk[m.name] = amount

# カメラ: 平行投影、正面（-Y）から +Y を見る
CAM = POSES["_camera"]
cam_data = bpy.data.cameras.new("cam")
cam_data.type, cam_data.ortho_scale = "ORTHO", CAM["ortho"]
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
cam.location, cam.rotation_euler = (0, -8, CAM["z"]), (math.radians(90), 0, 0)
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = CAM["w"], CAM["h"]
scene.render.resolution_percentage = 100
scene.render.engine, scene.cycles.samples, scene.cycles.device = "CYCLES", 8, "CPU"
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
scene.world = world

# 深度マップの材質: カメラからの距離 7.6〜8.4 m を明るさ 1.0〜0.15 に写す（近いほど明るい）
mat = bpy.data.materials.new("depth")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
camd, mr = nt.nodes.new("ShaderNodeCameraData"), nt.nodes.new("ShaderNodeMapRange")
mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 7.6, 8.4
mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0, 0.15
em, out = nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(camd.outputs["View Z Depth"], mr.inputs["Value"])
nt.links.new(mr.outputs["Result"], em.inputs["Strength"])
nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
scene.view_layers[0].material_override = mat

for name, p in POSES.items():
    if name.startswith("_"):
        continue
    root.rotation_euler = (0, 0, math.radians(p["facing"]))
    for b in arm.pose.bones:
        b.rotation_mode, b.rotation_euler, b.location = "XYZ", (0, 0, 0), (0, 0, 0)
    for b, r in p["rot"].items():
        arm.pose.bones[b].rotation_euler = Euler([math.radians(v) for v in r])
    for kind in ("plain", "bulk"):
        for mname, amount in bulk.items():
            body.modifiers[mname].strength = amount if kind == "bulk" else 0.0
        bpy.context.view_layer.update()
        scene.render.filepath = os.path.join(OUT, f"{DOLL}_{kind}_{name}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", DOLL, kind, name)
