"""各モデルを num_ctx 4,096 と 36,864 で読み込み、/api/ps（ollama ps と同じ情報）の size を記録する。

使い方:
    python3 mem.py mem.json
"""
import json
import sys
import time

from bench import HOST, MODELS, api, wait_quiet


def main():
    rows = []
    for model, think in MODELS:
        for ctx in (4096, 36864):
            wait_quiet()
            api(HOST, "/api/chat", {"model": model, "messages": [{"role": "user", "content": "Say hi."}],
                                    "think": think, "stream": False, "keep_alive": "2m",
                                    "options": {"num_ctx": ctx, "num_predict": 4}})
            ps = [m for m in api(HOST, "/api/ps")["models"] if m["name"] == model][0]
            row = {"model": model, "num_ctx": ctx, "size": ps["size"], "size_vram": ps["size_vram"],
                   "context_length": ps.get("context_length"), "time": time.strftime("%Y-%m-%dT%H:%M:%S")}
            rows.append(row)
            print(f"{model:40s} num_ctx {ctx:6d}  size {row['size'] / 1e9:6.2f} GB  "
                  f"vram {row['size_vram'] / 1e9:6.2f} GB", flush=True)
            api(HOST, "/api/generate", {"model": model, "keep_alive": 0})
            time.sleep(3)
    with open(sys.argv[1], "w") as f:
        json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
