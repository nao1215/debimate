"""服の厚みを付けた人形で、腕を上げていく 4 コマを書き出す（Blender 4.5 + MPFB 2.0.18）。

使い方: blender --background <real.blend> --python render_frames.py -- poses.json <出力先>
出力（コマ i = 0..3）:
  depth_f<i>.png   深度マップ（近いほど明るい白黒、背景は黒）。832 x 1216
  gen_f<i>.png     表面の各点の変形前の位置（Texture Coordinate の Generated）を色にしたもの。16 ビット・Raw・RGBA
  uv_f<i>.png      表面の各点の展開図の座標（Texture Coordinate の UV）を色にしたもの。同じ形式
  cell_f<i>.png    並べた 1 枚に使う、小さいコマの深度マップ（384 x 768。4 つ並べると 1536 x 768）

- 人形は depth-body-shape の make_dolls.py が作った real.blend（標準体型）。服の厚みは poses.json の _bulk
- ポーズは骨の回転（度）だけで付ける（FK）。体の向きは 4 コマとも _facing（度）
- カメラは平行投影。並べた 1 枚の 1 コマも、縦の写る範囲（2.1 m）とカメラの位置は同じ
"""
import json
import math
import os
import sys

import bpy
from mathutils import Euler

argv = sys.argv[sys.argv.index("--") + 1:]
POSES, OUT = json.load(open(argv[0])), argv[1]
os.makedirs(OUT, exist_ok=True)
FRAMES = sorted(k for k in POSES if not k.startswith("_"))

scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in bpy.data.objects if o.type == "MESH")
root = bpy.data.objects.new("Facing", None)
scene.collection.objects.link(root)
arm.parent = root
root.rotation_euler = (0, 0, math.radians(POSES["_facing"]))

for name, amount in POSES["_bulk"].items():
    m = body.modifiers.new("bulk_" + name, "DISPLACE")
    m.vertex_group, m.strength, m.mid_level, m.direction = name, amount, 0, "NORMAL"
    body.modifiers.move(body.modifiers.find(m.name), 0)

CAM = POSES["_camera"]
cam_data = bpy.data.cameras.new("cam")
cam_data.type, cam_data.ortho_scale = "ORTHO", CAM["ortho"]
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
cam.location, cam.rotation_euler = (CAM["x"], -8, CAM["z"]), (math.radians(90), 0, 0)
scene.camera = cam
scene.render.resolution_percentage = 100
scene.render.engine, scene.cycles.device = "CYCLES", "CPU"
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
scene.world = world


def emission_material(name, build):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    em, out = nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeOutputMaterial")
    build(nt, em)
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def depth_nodes(nt, em):
    # カメラからの距離 7.6〜8.4 m を明るさ 1.0〜0.15 に写す（depth-body-shape と同じ）
    camd, mr = nt.nodes.new("ShaderNodeCameraData"), nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 7.6, 8.4
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0, 0.15
    nt.links.new(camd.outputs["View Z Depth"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], em.inputs["Strength"])


def coord_nodes(socket):
    def build(nt, em):
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(tc.outputs[socket], em.inputs["Color"])
    return build


DEPTH = emission_material("depth", depth_nodes)
COORDS = {"gen": emission_material("gen", coord_nodes("Generated")),
          "uv": emission_material("uv", coord_nodes("UV"))}


def pose(p):
    for b in arm.pose.bones:
        b.rotation_mode, b.rotation_euler, b.location = "XYZ", (0, 0, 0), (0, 0, 0)
    for b, r in p.items():
        arm.pose.bones[b].rotation_euler = Euler([math.radians(v) for v in r])
    bpy.context.view_layer.update()


def render(path, w, h, kind):
    scene.render.resolution_x, scene.render.resolution_y = w, h
    s = scene.render.image_settings
    if kind == "depth":
        scene.view_layers[0].material_override = DEPTH
        scene.view_settings.view_transform = "Standard"
        scene.render.film_transparent = False
        scene.cycles.samples, scene.cycles.filter_width = 8, 1.5
        s.color_mode, s.color_depth = "RGB", "8"
    else:
        # 画素の境目で 2 つの面の値が混ざらないよう、ほぼ点の標本で描く
        scene.view_layers[0].material_override = COORDS[kind]
        scene.view_settings.view_transform = "Raw"
        scene.render.film_transparent = True
        scene.cycles.samples, scene.cycles.filter_width = 1, 0.01
        s.color_mode, s.color_depth = "RGBA", "16"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


for f in FRAMES:
    pose(POSES[f])
    render(os.path.join(OUT, f"depth_{f}.png"), CAM["w"], CAM["h"], "depth")
    for kind in COORDS:
        render(os.path.join(OUT, f"{kind}_{f}.png"), CAM["w"], CAM["h"], kind)
    # 並べた 1 枚の 1 コマ: 縦の範囲は同じ 2.1 m（縦が長い辺なので ortho_scale がそのまま縦になる）
    render(os.path.join(OUT, f"cell_{f}.png"), 384, 768, "depth")
    print("RENDERED", f)
