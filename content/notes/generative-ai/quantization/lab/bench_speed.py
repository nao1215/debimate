"""3 つのモデルで、プロンプト処理と生成の速さ（tokens/s）を繰り返し測る。

Ollama の応答の prompt_eval_count / prompt_eval_duration と
eval_count / eval_duration から速さを出す。思考モードは "think": false で無効にする。
マシンの負荷がぶれるので、モデルを 1 回ずつ順に回す周回を ROUNDS 回繰り返し、中央値を採る。
各回の前後で /api/ps（ollama ps と同じ情報）と負荷平均を記録する。

使い方:
    OLLAMA_HOST=127.0.0.1:11435 python3 bench_speed.py speed.json
"""
import json
import os
import statistics
import sys
import time
import urllib.request

MODELS = ["qwen3:1.7b-q4_K_M", "qwen3:1.7b-q8_0", "qwen3:1.7b-fp16"]
ROUNDS = 9
BASE = "http://" + os.environ.get("OLLAMA_HOST", "127.0.0.1:11435")

# プロンプト処理を測るための長めの入力（チャットの書式を含めて 950 トークン）
NOTES = "\n".join(
    f"Log {i}: at {i % 24:02d}:{(i * 7) % 60:02d} the keeper checked lamp {i % 5}, "
    f"wrote the wind speed {(i * 13) % 40} knots, and refilled {(i * 3) % 9} liters of oil."
    for i in range(1, 25))
TASK = "Using the logs above, write a long story of at least 300 words about the lighthouse keeper."


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3600) as r:   # 他の作業の待ち行列で長く待つことがある
        return json.load(r)


def loaded():
    with urllib.request.urlopen(BASE + "/api/ps", timeout=60) as r:
        return [m["name"] for m in json.load(r)["models"]]


def generate(model, tag):
    # 先頭に毎回違う文字列を置き、前回のプロンプトのキャッシュを使わせない
    prompt = f"Request {tag}.\n{NOTES}\n\n{TASK}"
    return post("/api/chat", {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "think": False,
        "stream": False,
        "keep_alive": "10m",
        "options": {"temperature": 0, "seed": 1, "num_predict": 128, "num_ctx": 4096},
    })


def main():
    out_path = sys.argv[1]
    runs = []
    for model in MODELS:                       # 読み込みの時間を計測から外す
        generate(model, f"warmup-{model}")
    for rnd in range(ROUNDS):
        for model in MODELS:
            before = loaded()
            load1 = os.getloadavg()[0]
            res = generate(model, f"{rnd}-{model}-{time.time_ns()}")
            after = loaded()
            run = {
                "round": rnd, "model": model, "loadavg_1m": round(load1, 1),
                "ps_before": before, "ps_after": after,
                "prompt_tokens": res["prompt_eval_count"],
                # キャッシュから読んだトークン（返す版だけ）を除き、計算したトークンだけで割る
                "prompt_cached": res.get("prompt_eval_cached_count", 0),
                "prompt_tps": (res["prompt_eval_count"] - res.get("prompt_eval_cached_count", 0))
                / res["prompt_eval_duration"] * 1e9,
                "eval_tokens": res["eval_count"],
                "eval_tps": res["eval_count"] / res["eval_duration"] * 1e9,
                # 思考の文が混ざっていないか（混ざると eval_count に思考のトークンが入る）
                "thinking_chars": len(res["message"].get("thinking", "")),
                "think_tag": "<think>" in res["message"]["content"],
            }
            runs.append(run)
            others = sorted(set(before + after) - set(MODELS))
            print(f"round {rnd} {model:18s} prompt {run['prompt_tokens']:4d} tok "
                  f"(cached {run['prompt_cached']:3d}) "
                  f"{run['prompt_tps']:8.1f} tok/s | gen {run['eval_tokens']:4d} tok "
                  f"{run['eval_tps']:6.1f} tok/s | thinking {run['thinking_chars']} chars"
                  f"{' <think>!' if run['think_tag'] else ''} | load {load1:6.1f} | other models: "
                  f"{', '.join(others) or '-'}", flush=True)
    print()
    summary = {}
    for model in MODELS:
        rs = [r for r in runs if r["model"] == model]
        p = [r["prompt_tps"] for r in rs]
        g = [r["eval_tps"] for r in rs]
        summary[model] = {"prompt_median": statistics.median(p), "prompt_min": min(p),
                          "prompt_max": max(p), "eval_median": statistics.median(g),
                          "eval_min": min(g), "eval_max": max(g)}
        s = summary[model]
        print(f"{model:18s} prompt median {s['prompt_median']:7.1f} tok/s "
              f"({s['prompt_min']:.1f}-{s['prompt_max']:.1f}) | gen median "
              f"{s['eval_median']:5.1f} tok/s ({s['eval_min']:.1f}-{s['eval_max']:.1f})")
    with open(out_path, "w") as f:
        json.dump({"runs": runs, "summary": summary}, f, indent=1)


if __name__ == "__main__":
    main()
