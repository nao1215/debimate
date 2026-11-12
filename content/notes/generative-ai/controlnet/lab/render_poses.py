"""MPFB の 3D モデルにポーズを付け、同じカメラから深度マップ（depth map）と OpenPose の 18 点の座標を書き出す。

使い方: blender --background <make_mannequin.py の .blend> --python render_poses.py -- poses.json <出力先>

- ポーズの座標は人物の基準の座標（m）。x = 人物の左、f = 人物の前、z = 上
- 手足の位置は IK（Inverse Kinematics、手先の位置から肘・膝の曲がりを決める仕組み）の目標で置く
- 棒（staff）は右手に付いて、tip の方向を向く単純な円柱
- 深度マップは近いほど明るい白黒の画像（背景は黒）。カメラは平行投影で全ポーズ共通
- 18 点は MPFB の rig.openpose.json の定義（頂点の平均か、関節の補助の立方体の中心）を、
  ポーズを付けた後のメッシュで計算して画面に写す。鼻・目・耳は、体に隠れる時は書き出さない
"""
import json
import math
import os
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
POSES = json.load(open(argv[0]))
OUT = argv[1]
os.makedirs(OUT, exist_ok=True)

scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in bpy.data.objects if o.type == "MESH")

root = bpy.data.objects.new("Facing", None)
scene.collection.objects.link(root)
arm.parent = root


def local(p):  # 人物の基準（x 左、f 前、z 上）→ root の座標（正面は -Y）
    return Vector((p[0], -p[1], p[2]))


def empty(name):
    e = bpy.data.objects.new(name, None)
    scene.collection.objects.link(e)
    e.parent = root
    return e


T = {n: empty(n) for n in ["t_hand_r", "t_hand_l", "t_foot_r", "t_foot_l", "p_elbow_r", "p_elbow_l",
                           "p_knee_r", "p_knee_l", "t_tip"]}


def ik(bone, target, pole, pole_angle):
    c = arm.pose.bones[bone].constraints.new("IK")
    c.target, c.pole_target = T[target], T[pole]
    c.pole_angle, c.chain_count = math.radians(pole_angle), 2


ik("lowerarm_r", "t_hand_r", "p_elbow_r", 180)
ik("lowerarm_l", "t_hand_l", "p_elbow_l", 0)
ik("calf_r", "t_foot_r", "p_knee_r", -90)
ik("calf_l", "t_foot_l", "p_knee_l", -90)

# 棒: 半径 2.5 cm、握りから先へ up m、後ろへ down m
bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=1, vertices=24)
staff = bpy.context.active_object
staff.name = "staff"
up, down = POSES["_staff"]["up"], POSES["_staff"]["down"]
for v in staff.data.vertices:
    v.co.z = up if v.co.z > 0 else -down
c = staff.constraints.new("COPY_LOCATION")
c.target, c.subtarget, c.head_tail = arm, "hand_r", 0.5
c = staff.constraints.new("DAMPED_TRACK")
c.target, c.track_axis = T["t_tip"], "TRACK_Z"

# 服の厚み: 骨ごとの頂点グループを法線方向に膨らませる（骨組みより前に掛けるので、どのポーズでも付いてくる）
for name, amount in POSES.get("_bulk", {}).items():
    m = body.modifiers.new("bulk_" + name, "DISPLACE")
    m.vertex_group, m.strength, m.mid_level, m.direction = name, amount, 0, "NORMAL"
    body.modifiers.move(body.modifiers.find(m.name), 0)

# カメラ: 平行投影、正面（-Y）から +Y を見る
CAM = POSES["_camera"]
cam_data = bpy.data.cameras.new("cam")
cam_data.type, cam_data.ortho_scale = "ORTHO", CAM["ortho"]
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
cam.location, cam.rotation_euler = (CAM["x"], -8, CAM["z"]), (math.radians(90), 0, 0)
scene.camera = cam
W, H = CAM["w"], CAM["h"]
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.resolution_percentage = 100
scene.render.engine, scene.cycles.samples, scene.cycles.device = "CYCLES", 8, "CPU"
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
scene.world = world

# 深度マップの材質: カメラからの距離 7.4〜8.6 m を明るさ 1.0〜0.15 に写す（近いほど明るい）
mat = bpy.data.materials.new("depth")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
camd, mr = nt.nodes.new("ShaderNodeCameraData"), nt.nodes.new("ShaderNodeMapRange")
mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 7.4, 8.6
mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0, 0.15
em, out = nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(camd.outputs["View Z Depth"], mr.inputs["Value"])
nt.links.new(mr.outputs["Result"], em.inputs["Strength"])
nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
scene.view_layers[0].material_override = mat

# OpenPose の 18 点の並び（COCO の順）と、MPFB の rig.openpose.json での対応
ORDER = ["Nose", "Neck", "RShoulder", "RElbow", "RWrist", "LShoulder", "LElbow", "LWrist", "RHip", "RKnee",
         "RAnkle", "LHip", "LKnee", "LAnkle", "REye", "LEye", "REar", "LEar"]
FACE = {"Nose", "REye", "LEye", "REar", "LEar"}
rig_json = os.path.join(bpy.utils.user_resource("EXTENSIONS"), "user_default", "mpfb", "data", "rigs",
                        "standard", "rig.openpose.json")
BONES = json.load(open(rig_json))["bones"]
# 点の位置は、その名前の骨の tail。ただし Nose は Neck の tail、Neck は MidHip の tail
SRC = {k: BONES[k]["tail"] for k in ORDER if k not in ("Nose", "Neck")}
SRC["Nose"], SRC["Neck"] = BONES["Neck"]["tail"], BONES["MidHip"]["tail"]
group_index = {g.name: g.index for g in body.vertex_groups}
cube_verts = {}
for v in body.data.vertices:
    for g in v.groups:
        cube_verts.setdefault(g.group, []).append(v.index)


def keypoints():
    masks = [m for m in body.modifiers if m.type == "MASK"]
    for m in masks:  # 関節の補助の立方体は Mask で隠れているので、数える間だけ出す
        m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = body.evaluated_get(dg).to_mesh()
    pts = {}
    for k, s in SRC.items():
        idx = s["vertex_indices"] if s["strategy"] == "MEAN" else cube_verts[group_index[s["cube_name"]]]
        co = sum((me.vertices[i].co for i in idx), Vector()) / len(idx)
        pts[k] = body.matrix_world @ co
    body.evaluated_get(dg).to_mesh_clear()
    for m in masks:
        m.show_viewport = True
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    res = []
    for k in ORDER:
        co = pts[k]
        if k in FACE:  # 正面から光線を当て、手前に体があれば隠れている
            hit, loc, *_ = scene.ray_cast(dg, Vector((co.x, -8, co.z)), Vector((0, 1, 0)))
            if hit and loc.y < co.y - 0.03:
                res.append(None)
                continue
        p = world_to_camera_view(scene, cam, co)
        res.append([round(p.x * W, 1), round((1 - p.y) * H, 1)])
    return res


def apply(p):
    root.rotation_euler = (0, 0, math.radians(p["facing"]))
    for k in ["hand_r", "hand_l", "foot_r", "foot_l"]:
        T["t_" + k].location = local(p[k])
    T["t_tip"].location = local(p["tip"])
    T["p_elbow_r"].location = local(p.get("elbow_r", [-0.6, -0.4, 1.2]))
    T["p_elbow_l"].location = local(p.get("elbow_l", [0.6, -0.4, 1.2]))
    T["p_knee_r"].location = local(p.get("knee_r", [-0.15, 1.0, 0.5]))
    T["p_knee_l"].location = local(p.get("knee_l", [0.15, 1.0, 0.5]))
    for b in arm.pose.bones:
        b.rotation_mode, b.rotation_euler, b.location = "XYZ", (0, 0, 0), (0, 0, 0)
    arm.pose.bones["pelvis"].location = (0, -p.get("drop", 0), 0)
    for b, r in p.get("rot", {}).items():
        arm.pose.bones[b].rotation_euler = Euler([math.radians(v) for v in r])
    bpy.context.view_layer.update()


result = {}
for name, p in POSES.items():
    if name.startswith("_"):
        continue
    apply(p)
    scene.render.filepath = f"{OUT}/depth_{name}.png"
    bpy.ops.render.render(write_still=True)
    result[name] = keypoints()
    print("RENDERED", name, result[name])
json.dump({"order": ORDER, "width": W, "height": H, "poses": result}, open(f"{OUT}/keypoints.json", "w"), indent=1)
