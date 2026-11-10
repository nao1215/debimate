"""実験で送るワークフロー（ComfyUI の API 形式）を組み立てる。Python 標準ライブラリだけ。

ノード番号は全ての実験で共通にしてある。1〜5 が同じ入力なら、ComfyUI はその出力をキャッシュから使う。
"""
CKPT = "waiIllustriousSDXL_v170.safetensors"
SEED = 20261111
CFG = 5.5
POSITIVE = ("masterpiece, best quality, no humans, scenery, lighthouse, cliff, ocean, "
            "sunset, orange sky, cloud, horizon, waves")
NEGATIVE = ("lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, "
            "signature, watermark, logo, 1girl, 1boy, person")


def base():
    """1: モデル、2: clip skip 2、3/4: プロンプトと打ち消し、5: 空の潜在（1024 x 1024）。"""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPSetLastLayer", "inputs": {"clip": ["1", 1], "stop_at_clip_layer": -2}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": POSITIVE}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEGATIVE}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
    }


def save(wf, node, src, prefix):
    """src の潜在を VAE で画像に戻して保存するノードを node, node+1 番に足す。"""
    wf[str(node)] = {"class_type": "VAEDecode", "inputs": {"samples": src, "vae": ["1", 2]}}
    wf[str(node + 1)] = {"class_type": "SaveImage",
                         "inputs": {"images": [str(node), 0], "filename_prefix": prefix}}
    return str(node + 1)


def ksampler(steps, sampler="euler", scheduler="normal", cfg=CFG, seed=SEED):
    """普通の txt2img。KSampler（7）→ VAEDecode（8）→ SaveImage（9）。"""
    wf = base()
    wf["7"] = {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
        "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": sampler,
        "scheduler": scheduler, "denoise": 1.0}}
    save(wf, 8, ["7", 0], "debimate_diffusion/ksampler")
    return wf


def partial(k, scale, steps=28):
    """28 ステップの列の先頭 k ステップだけを進める。

    10: KSamplerSelect（euler）、11: BasicScheduler、12: SplitSigmas（先頭の k+1 個）、
    13: SamplerCustom。出力 0 は k ステップ後の潜在 x_k、出力 1 は最後の 1 回で予測した x0。
    14: x_k に scale = 1/sqrt(1 + sigma_k^2) を掛ける（モデルに入る大きさに揃える）。
    """
    wf = base()
    wf["10"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}}
    wf["11"] = {"class_type": "BasicScheduler", "inputs": {
        "model": ["1", 0], "scheduler": "normal", "steps": steps, "denoise": 1.0}}
    wf["12"] = {"class_type": "SplitSigmas", "inputs": {"sigmas": ["11", 0], "step": k}}
    wf["13"] = {"class_type": "SamplerCustom", "inputs": {
        "model": ["1", 0], "add_noise": True, "noise_seed": SEED, "cfg": CFG,
        "positive": ["3", 0], "negative": ["4", 0], "sampler": ["10", 0],
        "sigmas": ["12", 0], "latent_image": ["5", 0]}}
    wf["14"] = {"class_type": "LatentMultiply", "inputs": {"samples": ["13", 0], "multiplier": scale}}
    outs = {"x": save(wf, 15, ["14", 0], f"debimate_diffusion/x_{k:02d}")}
    if k > 0:
        outs["x0"] = save(wf, 17, ["13", 1], f"debimate_diffusion/x0_{k:02d}")
    return wf, outs


def forward(js, scales, noise_seed=1):
    """28 ステップで描き終えた潜在（partial(28) と同じノード）に、sigma_j のノイズを足す。

    sigma_j は BasicScheduler の列の j 番目。SplitSigmas を 2 回使い、長さ 1 の列 [sigma_j] を作る。
    長さ 1 の列では、サンプラーはモデルを 1 回も呼ばず、noise_scaling の結果をそのまま返す。
    """
    wf, _ = partial(28, 1.0)
    del wf["14"], wf["15"], wf["16"], wf["17"], wf["18"]
    outs = {}
    node = 30
    for j, scale in zip(js, scales):
        a, b, c, m = str(node), str(node + 1), str(node + 2), str(node + 3)
        wf[a] = {"class_type": "SplitSigmas", "inputs": {"sigmas": ["11", 0], "step": j}}
        wf[b] = {"class_type": "SplitSigmas", "inputs": {"sigmas": [a, 1], "step": 0}}
        wf[c] = {"class_type": "SamplerCustom", "inputs": {
            "model": ["1", 0], "add_noise": True, "noise_seed": noise_seed, "cfg": CFG,
            "positive": ["3", 0], "negative": ["4", 0], "sampler": ["10", 0],
            "sigmas": [b, 0], "latent_image": ["13", 0]}}
        wf[m] = {"class_type": "LatentMultiply", "inputs": {"samples": [c, 0], "multiplier": scale}}
        outs[j] = save(wf, node + 4, [m, 0], f"debimate_diffusion/fwd_{j:02d}")
        node += 10
    wf["99"] = {"class_type": "SaveLatent", "inputs": {"samples": ["13", 0],
                                                       "filename_prefix": "debimate_diffusion/final"}}
    return wf, outs
