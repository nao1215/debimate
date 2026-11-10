"""ComfyUI の API を 1 枚ずつ呼ぶ小さなクライアント（Python 標準ライブラリだけ）。

- 依頼は 1 枚ずつ送り、自分の prompt_id だけを /history で待つ
- 待ち行列の削除やサーバーの設定変更はしない
- 実行時間は ComfyUI が記録する execution_start から execution_success までの差
"""
import json
import os
import time
import urllib.parse
import urllib.request
import uuid

BASE = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
CLIENT_ID = "debimate-img2img-" + uuid.uuid4().hex[:8]


def _get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read())


def _post(path, obj):
    req = urllib.request.Request(BASE + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def upload(png_path, subfolder="debimate_img2img"):
    """下絵を ComfyUI の input/<subfolder>/ に置く。LoadImage の image 名を返す。"""
    name = os.path.basename(png_path)
    boundary = uuid.uuid4().hex
    with open(png_path, "rb") as f:
        data = f.read()
    parts = []
    for key, val in (("subfolder", subfolder), ("overwrite", "true"), ("type", "input")):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{val}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
                 f'Content-Type: image/png\r\n\r\n'.encode() + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(BASE + "/upload/image", data=b"".join(parts),
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.loads(r.read())
    return f"{res['subfolder']}/{res['name']}" if res.get("subfolder") else res["name"]


def load_state():
    """送る直前の負荷: ComfyUI の待ち行列の長さ、GPU の使用率と温度、CPU の load average。"""
    q = _get("/queue")
    state = {"queue_running": len(q["queue_running"]), "queue_pending": len(q["queue_pending"])}
    try:
        with open("/sys/class/drm/card1/device/gpu_busy_percent") as f:
            state["gpu_busy_percent"] = int(f.read())
    except OSError:
        pass
    try:
        state["loadavg_1m"] = os.getloadavg()[0]
    except OSError:
        pass
    return state


def run(workflow, out_png, save_node):
    """1 枚を送り、終わるまで待って PNG を保存する。実行秒数と負荷を返す。"""
    before = load_state()
    res = _post("/prompt", {"prompt": workflow, "client_id": CLIENT_ID})
    pid = res["prompt_id"]
    while True:
        hist = _get(f"/history/{pid}")
        if pid in hist:
            break
        time.sleep(2)
    h = hist[pid]
    status = h.get("status", {})
    if status.get("status_str") != "success":
        raise RuntimeError(f"{pid}: {status}")
    msgs = status.get("messages", [])
    stamps = {m[0]: m[1]["timestamp"] for m in msgs}
    cached = [n for m in msgs if m[0] == "execution_cached" for n in m[1].get("nodes", [])]
    seconds = (stamps["execution_success"] - stamps["execution_start"]) / 1000
    img = h["outputs"][save_node]["images"][0]
    q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img["subfolder"],
                                "type": img["type"]})
    with urllib.request.urlopen(f"{BASE}/view?{q}", timeout=60) as r, open(out_png, "wb") as f:
        f.write(r.read())
    return {"prompt_id": pid, "seconds": round(seconds, 2), "cached_nodes": cached,
            "load_before": before}
