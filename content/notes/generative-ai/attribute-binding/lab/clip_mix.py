"""SDXL の 2 つの text encoder で、色の語を 1 つ変えた時に、
どのトークンの出力が変わるかを数える。

ComfyUI のライブラリ（comfy）でチェックポイントの text encoder だけを CPU に読み、
CLIPSetLastLayer -2 と同じ層の出力（UNet の cross-attention に渡す 77 x 2048 の列）を
1 語だけ違う 2 つのプロンプトで比べる。2048 次元のうち先頭の 768 が CLIP ViT-L、
残りの 1280 が OpenCLIP ViT-bigG の出力である。ComfyUI のサーバーには触れない。

使い方（ComfyUI の Python 環境で、ComfyUI のディレクトリを第 1 引数に）:
    python clip_mix.py <ComfyUI のディレクトリ> <チェックポイント> [結果の JSON]
"""
import json
import sys

PAIRS = {   # 1 語だけ違う 2 つのプロンプト
    "eyes_last":  ("1girl, black hair, aqua eyes", "1girl, black hair, brown eyes"),
    "eyes_first": ("1girl, aqua eyes, black hair", "1girl, brown eyes, black hair"),
    # 比べる基準: hair の直前の色の語そのものを変えた時
    "hair_self":  ("1girl, brown eyes, aqua hair", "1girl, brown eyes, black hair"),
}


def main():
    comfy_dir, ckpt = sys.argv[1], sys.argv[2]
    out_path = sys.argv[3] if len(sys.argv) > 3 else None
    sys.argv = [sys.argv[0], "--cpu"]          # GPU を使わない
    sys.path.insert(0, comfy_dir)
    import torch
    import comfy.options
    comfy.options.enable_args_parsing()
    import comfy.sd

    _, clip, *_ = comfy.sd.load_checkpoint_guess_config(
        ckpt, output_vae=False, output_clip=True, output_model=False)
    clip.clip_layer(-2)                        # CLIPSetLastLayer -2 と同じ
    vocab = {v: k for k, v in clip.tokenizer.clip_l.tokenizer.get_vocab().items()}

    def encode(text):
        tokens = clip.tokenize(text)
        cond = clip.encode_from_tokens(tokens)[0].float()      # [77, 2048]
        ids = [t[0] for t in tokens["l"][0]]
        n = ids.index(49407) + 1                               # 最初の終わりのトークンまで
        return cond, [vocab[i] for i in ids[:n]], n

    cos = torch.nn.functional.cosine_similarity
    result = {}
    for name, (a, b) in PAIRS.items():
        ca, toks, n = encode(a)
        cb, _, _ = encode(b)
        # トークンごとの差: 1 - コサイン類似度（0 なら全く同じ）
        dl = (1 - cos(ca[:, :768], cb[:, :768], dim=-1)).tolist()
        dg = (1 - cos(ca[:, 768:], cb[:, 768:], dim=-1)).tolist()
        print(f"[{name}] {a!r} vs {b!r}")
        print("   # token          CLIP-L  bigG")
        for i, t in enumerate(toks):
            print(f"  {i:2d} {t:<14} {dl[i]:.4f}  {dg[i]:.4f}")
        print(f"  padding {77 - n} tokens: CLIP-L max {max(dl[n:]):.4f}, "
              f"bigG max {max(dg[n:]):.4f}")
        result[name] = {"tokens": toks, "clip_l": dl[:n], "bigg": dg[:n],
                        "pad_l_max": max(dl[n:]), "pad_g_max": max(dg[n:])}
    if out_path:
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
