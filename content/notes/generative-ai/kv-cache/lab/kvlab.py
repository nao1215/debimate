"""KV キャッシュの実験で共通に使う道具（Python 標準ライブラリだけ）。

- Ollama の HTTP API を呼ぶ
- /api/ps を記録する
- サーバーのログ（systemd の journal）から、読み込み時の "kv cache" などの行を拾う
- 長さを変えられる詰め物の文章を作る
"""
import json
import os
import subprocess
import time
import urllib.request

HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11435")
# ログを読むコマンド。著者の環境では Ollama を systemd のユーザーサービス local-llm で動かしている
LOG_UNIT = os.environ.get("KVLAB_LOG_UNIT", "local-llm")
MODELS_DIR = os.environ.get("OLLAMA_MODELS", os.path.expanduser("~/.ollama/models"))


def api(path, body=None, timeout=900):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"http://{HOST}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ps():
    """/api/ps を短い形にする（名前・size・size_vram・context_length）。"""
    out = []
    for m in api("/api/ps")["models"]:
        out.append({"name": m["name"], "size": m["size"], "size_vram": m["size_vram"],
                    "context_length": m.get("context_length")})
    return out


def ps_line(rows):
    return "; ".join(f'{r["name"]} size={r["size"]/1e9:.2f}GB vram={r["size_vram"]/1e9:.2f}GB '
                     f'ctx={r["context_length"]}' for r in rows) or "(none)"


def blob_of(model):
    """モデル名から重みの blob（sha256-...）を引く。ログの "starting runner" 行と照合するため。"""
    name, tag = model.split(":")
    path = os.path.join(MODELS_DIR, "manifests/registry.ollama.ai/library", name, tag)
    with open(path) as f:
        man = json.load(f)
    for layer in man["layers"]:
        if layer["mediaType"] == "application/vnd.ollama.image.model":
            return layer["digest"].replace(":", "-")
    raise RuntimeError(model)


def load_log(model, since_epoch):
    """since_epoch 以降のログから、model を読み込んだ時の行（KvSize と device.go の内訳）を返す。"""
    try:
        txt = subprocess.run(["journalctl", "--user", "-u", LOG_UNIT, "--since", f"@{since_epoch:.0f}",
                              "--no-pager", "-o", "cat"], capture_output=True, text=True,
                             timeout=30).stdout
    except Exception as e:  # ログが読めない環境では空で返す
        return {"error": str(e)}
    blob = blob_of(model)
    lines = txt.splitlines()
    found = None
    for i, ln in enumerate(lines):
        if "starting runner" in ln and blob in ln:
            found = i
    if found is None:
        return {}
    info = {}
    for ln in lines[found:found + 80]:
        if "KvSize:" in ln and "Operation:commit" in ln:
            info["KvSize"] = int(ln.split("KvSize:")[1].split()[0])
            info["KvCacheType"] = ln.split("KvCacheType:")[1].split(" ")[0] or "(empty)"
        if "source=device.go" in ln:
            msg = ln.split('msg="')[1].split('"')[0]
            dev = ln.split("device=")[1].split()[0] if "device=" in ln else "-"
            size = ln.split('size="')[1].split('"')[0]
            info[f"{msg} {dev}"] = size
            if msg == "total memory":
                break
    return info


def unload(model):
    try:
        api("/api/generate", {"model": model, "keep_alive": 0})
    except Exception:
        pass
    # 実際に消えるまで待つ（他の作業の都合で長引いた時は記録して先へ進む）
    for _ in range(60):
        if all(r["name"] != model for r in ps()):
            return True
        time.sleep(1)
    return False


def filler(n_lines, seed=0):
    """数えやすい詰め物。1 行はおよそ 25 トークン（qwen3 で prompt_eval_count を見て調整）。"""
    rows = []
    for i in range(n_lines):
        k = (i * 7919 + seed * 104729) % 100000
        rows.append(f"Record {i + 1}: sensor S{k % 97:02d} reported {k % 1000} units "
                    f"at hour {k % 24} on day {k % 31 + 1}.")
    return "\n".join(rows)


def generate(model, prompt, num_ctx=None, num_predict=64, keep_alive="10m"):
    opts = {"temperature": 0, "seed": 1, "num_predict": num_predict}
    if num_ctx is not None:
        opts["num_ctx"] = num_ctx
    body = {"model": model, "prompt": prompt, "stream": False, "think": False,
            "options": opts, "keep_alive": keep_alive}
    t0 = time.time()
    r = api("/api/generate", body)
    r["wall"] = time.time() - t0
    r["thinking_chars"] = len(r.get("thinking") or "")
    return r
