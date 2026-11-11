"""入力の長さとモデルを変えて、prefill（プロンプトの処理）と decode（1 トークンずつの生成）の速さを分けて測る。

Ollama の /api/chat の応答にある値から速さを出す（Python 標準ライブラリだけ）。
  prefill: prompt_eval_count / prompt_eval_duration（トークン毎秒）
  decode : eval_count / eval_duration（トークン毎秒）

- num_ctx は全てのモデル・長さで 36,864 に固定する（KV キャッシュの確保量を揃える）
- 先頭に毎回違う札を置き、前回のプロンプトのキャッシュを使わせない
- temperature 0、seed 1、num_predict 128。思考は "think": false（gpt-oss は false を受け付けないので "low"）
- 他の GPU 作業と重ならないように、各回の前に次の 3 つが揃うまで待つ
    他の作業の ollama.lock・comfy.lock が無い（自分が取った ollama.lock は除く） / ComfyUI の待ち行列が空 / GPU の使用率が 3 秒続けて 10% 以下
- 各回の最中も 0.5 秒ごとに GPU の使用率・ComfyUI の待ち行列・ロックを記録し、乱れた回に印を付けて測り直す

使い方:
    python3 bench.py runs.jsonl [ROUNDS]
"""
import json
import os
import statistics
import sys
import threading
import time
import urllib.request
import uuid

HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
OTHER_OLLAMA = "127.0.0.1:11435"          # 同じ機械で動く別の Ollama（他の作業が使う）
COMFY = "127.0.0.1:8188"
GPU_BUSY = "/sys/class/drm/card1/device/gpu_busy_percent"
LOCK_DIR = os.environ.get("LOCK_DIR", "")  # ollama.lock・comfy.lock を置くディレクトリ（空なら見ない）

MODELS = [  # (Ollama の名前, think の値)
    ("qwen3:8b", False),
    ("qwen3-coder:30b", False),
    ("hf.co/ggml-org/gpt-oss-20b-GGUF:latest", "low"),
]
LINES = [12, 110, 450, 900]               # 詰め物の行数。およそ 500・4K・16K・32K トークン
NUM_CTX = 36864
NUM_PREDICT = 128
TAIL = "\nIgnore the records above. Write the integers from 1 to 400 separated by commas."


def api(host, path, body=None, timeout=1800):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"http://{host}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def filler(n, seed):
    """灯台守の記録を n 行。行ごとに数字が変わるので、同じ文の繰り返しにならない。"""
    return "\n".join(
        f"Record {seed}-{i}: at {i % 24:02d}:{(i * 7 + seed) % 60:02d} the keeper checked lamp "
        f"{(i + seed) % 5}, noted wind {(i * 13 + seed) % 40} knots from {['N', 'E', 'S', 'W'][i % 4]}, "
        f"and refilled {(i * 3 + seed) % 9} liters of oil."
        for i in range(1, n + 1))


def gpu_busy():
    with open(GPU_BUSY) as f:
        return int(f.read())


def comfy_queue():
    try:
        q = api(COMFY, "/queue", timeout=5)
        return len(q["queue_running"]) + len(q["queue_pending"])
    except Exception:
        return -1                         # ComfyUI が止まっている


OWNER = "local-llm-speed"                 # 自分が取ったロックの中身。これは数えない


def locks():
    if not LOCK_DIR:
        return []
    held = []
    for n in ("ollama.lock", "comfy.lock"):
        try:
            with open(os.path.join(LOCK_DIR, n)) as f:
                if f.read().strip() != OWNER:
                    held.append(n)
        except FileNotFoundError:
            pass
    return held


def others_loaded():
    try:
        return [m["name"] for m in api(OTHER_OLLAMA, "/api/ps", timeout=5)["models"]]
    except Exception:
        return []


def wait_quiet():
    """ロックが無く、ComfyUI が空で、GPU が 3 秒続けて 10% 以下になるまで待つ。"""
    quiet = 0
    while quiet < 6:
        if locks() or comfy_queue() > 0 or others_loaded() or gpu_busy() > 10:
            quiet = 0
            time.sleep(5)
        else:
            quiet += 1
            time.sleep(0.5)


class Monitor(threading.Thread):
    """リクエストの最中に 0.5 秒ごとに外の様子を記録する。"""

    def __init__(self):
        super().__init__(daemon=True)
        self.stop = threading.Event()
        self.busy, self.comfy, self.lock_seen, self.others = [], 0, set(), set()

    def run(self):
        while not self.stop.is_set():
            self.busy.append(gpu_busy())
            self.comfy = max(self.comfy, comfy_queue())
            self.lock_seen.update(locks())
            self.others.update(others_loaded())
            time.sleep(0.5)


def chat(model, think, prompt, num_predict=NUM_PREDICT):
    return api(HOST, "/api/chat", {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "think": think,
        "stream": False,
        "keep_alive": "10m",
        "options": {"temperature": 0, "seed": 1, "num_predict": num_predict, "num_ctx": NUM_CTX},
    })


def measure(model, think, n, rnd, ps):
    """1 回測って 1 行の dict を返す。"""
    wait_quiet()
    prompt = f"Session {uuid.uuid4().hex}\n" + filler(n, seed=rnd) + TAIL
    mon = Monitor()
    mon.start()
    t0 = time.time()
    r = chat(model, think, prompt)
    wall = time.time() - t0
    mon.stop.set()
    mon.join()
    row = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "round": rnd,
        "lines": n, "think": think,
        "prompt_eval_count": r["prompt_eval_count"],
        "prompt_eval_s": r["prompt_eval_duration"] / 1e9,
        "eval_count": r["eval_count"], "eval_s": r["eval_duration"] / 1e9,
        "load_s": r["load_duration"] / 1e9, "wall_s": wall,
        "thinking_chars": len(r["message"].get("thinking", "") or ""),
        "content_head": r["message"]["content"][:40],
        "gpu_busy_median": statistics.median(mon.busy) if mon.busy else None,
        "comfy_queue_max": mon.comfy, "locks_seen": sorted(mon.lock_seen),
        "other_ollama_models": sorted(mon.others),
        "ps": [{"name": m["name"], "size": m["size"], "size_vram": m["size_vram"],
                "context_length": m.get("context_length")} for m in ps],
    }
    row["prefill_tps"] = row["prompt_eval_count"] / row["prompt_eval_s"]
    row["decode_tps"] = row["eval_count"] / row["eval_s"]
    row["disturbed"] = bool(mon.comfy > 0 or mon.lock_seen or mon.others)
    print(f"{model[:24]:24s} r{rnd} in {row['prompt_eval_count']:6d} tok "
          f"prefill {row['prefill_tps']:7.1f} tok/s | out {row['eval_count']:3d} tok "
          f"decode {row['decode_tps']:5.1f} tok/s | think {row['thinking_chars']:4d} ch "
          f"| gpu {row['gpu_busy_median']} comfy {mon.comfy} locks {row['locks_seen']} "
          f"others {row['other_ollama_models']}{' DISTURBED' if row['disturbed'] else ''}",
          flush=True)
    return row


def main():
    """各モデル・各長さで、乱れていない回が ROUNDS 回そろうまで測る。

    出力の JSONL に既にある乱れていない回も数えるので、途中で止めても続きから測れる。
    乱れた回も印を付けて書き残す（集計では除く）。1 条件で 3 回続けて乱れたら次へ進む。
    """
    out = sys.argv[1]
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    done = {}
    if os.path.exists(out):
        for line in open(out):
            r = json.loads(line)
            if not r["disturbed"]:
                done[(r["model"], r["lines"])] = done.get((r["model"], r["lines"]), 0) + 1
    with open(out, "a") as f:
        only = os.environ.get("BENCH_MODELS")             # 一部のモデルだけ測り足す時に名前をカンマ区切りで
        for model, think in MODELS:
            if only and model not in only.split(","):
                continue
            if all(done.get((model, n), 0) >= rounds for n in LINES):
                continue
            wait_quiet()
            chat(model, think, "Say hi.", num_predict=4)      # 読み込みを計測から外す
            ps = api(HOST, "/api/ps")["models"]
            for rnd in range(rounds):
                for n in LINES:
                    misses = 0
                    while done.get((model, n), 0) <= rnd and misses < 3:
                        row = measure(model, think, n, rnd + 10 * misses, ps)
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
                        f.flush()
                        if row["disturbed"]:
                            misses += 1
                        else:
                            done[(model, n)] = done.get((model, n), 0) + 1
            api(HOST, "/api/generate", {"model": model, "keep_alive": 0})   # 次のモデルの前に降ろす


if __name__ == "__main__":
    main()
