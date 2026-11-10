"""ComfyUI の API を 1 件ずつ呼ぶ小さなクライアント（Python 標準ライブラリだけ）。

- 依頼は 1 件ずつ送り、自分の prompt_id だけを /history で待つ
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
CLIENT_ID = "debimate-diffusion-" + uuid.uuid4().hex[:8]


def _get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read())


def _post(path, obj):
    req = urllib.request.Request(BASE + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def load_state():
    """送る直前の負荷: 待ち行列の長さ、GPU の使用率、CPU の load average。"""
    q = _get("/queue")
    state = {"queue_running": len(q["queue_running"]), "queue_pending": len(q["queue_pending"])}
    try:
        with open("/sys/class/drm/card1/device/gpu_busy_percent") as f:
            state["gpu_busy_percent"] = int(f.read())
    except OSError:
        pass
    try:
        state["loadavg_1m"] = round(os.getloadavg()[0], 2)
    except OSError:
        pass
    return state


def run(workflow, outputs):
    """1 件を送り、終わるまで待つ。outputs は {SaveImage のノード番号: 保存先の PNG}。"""
    before = load_state()
    pid = _post("/prompt", {"prompt": workflow, "client_id": CLIENT_ID})["prompt_id"]
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
    for node, path in outputs.items():
        img = h["outputs"][node]["images"][0]
        q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img["subfolder"],
                                    "type": img["type"]})
        with urllib.request.urlopen(f"{BASE}/view?{q}", timeout=60) as r, open(path, "wb") as f:
            f.write(r.read())
    seconds = (stamps["execution_success"] - stamps["execution_start"]) / 1000
    return {"prompt_id": pid, "seconds": round(seconds, 2), "cached_nodes": cached,
            "load_before": before, "outputs": h["outputs"]}
