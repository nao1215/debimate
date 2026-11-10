"""safetensors のヘッダーだけを読み、LoRA とベースモデルのパラメータ数を数える。

テンソルの中身は読まない。Python 標準ライブラリだけで動く。

使い方:
    python3 count_params.py <LoRA の .safetensors> <ベースモデルの .safetensors> [結果の JSON]
"""
import json
import math
import os
import struct
import sys
from collections import Counter


def read_header(path):
    """先頭 8 バイト（リトルエンディアンの u64）がヘッダー長、続く JSON がヘッダー。"""
    with open(path, "rb") as f:
        (length,) = struct.unpack("<Q", f.read(8))
        header = json.loads(f.read(length))
    metadata = header.pop("__metadata__", {})
    return length, header, metadata


def numel(shape):
    return math.prod(shape)  # 0 次元（スカラー）の shape [] は 1 になる


def main():
    lora_path, base_path = sys.argv[1], sys.argv[2]
    out_path = sys.argv[3] if len(sys.argv) > 3 else None

    # --- LoRA ---
    hlen, lora, meta = read_header(lora_path)
    print(f"[LoRA] {os.path.basename(lora_path)}")
    print(f"  file size       : {os.path.getsize(lora_path):,} bytes (header {hlen:,} bytes)")
    print(f"  tensors         : {len(lora):,}")
    print(f"  dtype           : {dict(Counter(t['dtype'] for t in lora.values()))}")
    print(f"  network_dim (r) : {meta.get('ss_network_dim')}")
    print(f"  network_alpha   : {meta.get('ss_network_alpha')}")
    print(f"  trained on      : {meta.get('ss_sd_model_name')}")
    print(f"  base SHA-256    : {meta.get('ss_new_sd_model_hash')}")

    downs = {k[: -len(".lora_down.weight")]: v for k, v in lora.items()
             if k.endswith(".lora_down.weight")}
    ranks = Counter(v["shape"][0] for v in downs.values())
    targets = Counter(name.split("_")[1] for name in downs)  # lora_unet_... / lora_te1_...
    print(f"  target layers   : {len(downs)} {dict(targets)}")
    print(f"  ranks           : {dict(ranks)}")

    # alpha は層ごとのスカラー（学習しない係数）なので数えない
    lora_params = sum(numel(v["shape"]) for k, v in lora.items() if k.endswith(".weight"))
    # 差分を足す先の W の大きさ: up が [out, r]、down が [r, in] なので W は [out, in]
    full_params = 0
    for name, down in downs.items():
        up = lora[name + ".lora_up.weight"]
        full_params += up["shape"][0] * numel(down["shape"][1:])
    print(f"  LoRA params     : {lora_params:,}")
    print(f"  W of targets    : {full_params:,} (same layers, full matrices)")

    # --- ベースモデル ---
    hlen, base, _ = read_header(base_path)
    groups = Counter()
    for k, v in base.items():
        if k.startswith("model.diffusion_model."):
            g = "UNet"
        elif k.startswith("conditioner.embedders.0."):
            g = "Text encoder 1 (CLIP ViT-L)"
        elif k.startswith("conditioner.embedders.1."):
            g = "Text encoder 2 (OpenCLIP ViT-bigG)"
        elif k.startswith("first_stage_model."):
            g = "VAE"
        else:
            g = "other"
        groups[g] += numel(v["shape"])
    total = sum(groups.values())
    print(f"\n[Base] {os.path.basename(base_path)}")
    print(f"  file size       : {os.path.getsize(base_path):,} bytes (header {hlen:,} bytes)")
    print(f"  tensors         : {len(base):,}")
    for g, n in sorted(groups.items(), key=lambda x: -x[1]):
        print(f"  {g:<34}: {n:>13,}")
    print(f"  {'total':<34}: {total:>13,}")

    unet = groups["UNet"]
    te = groups["Text encoder 1 (CLIP ViT-L)"] + groups["Text encoder 2 (OpenCLIP ViT-bigG)"]
    print("\n[Ratio]")
    print(f"  LoRA / UNet          : {lora_params / unet:.3%}")
    print(f"  LoRA / text encoders : {lora_params / te:.3%}")
    print(f"  LoRA / whole model   : {lora_params / total:.3%}")
    print(f"  LoRA / W of targets  : {lora_params / full_params:.3%}")

    if out_path:
        with open(out_path, "w") as f:
            json.dump({
                "rank": sorted(ranks), "alpha": meta.get("ss_network_alpha"),
                "target_layers": len(downs), "lora_params": lora_params,
                "target_full_params": full_params, "base_groups": groups,
                "base_total": total,
            }, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
