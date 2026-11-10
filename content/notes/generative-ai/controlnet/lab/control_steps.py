"""ComfyUI v0.35.0 で、ControlNet の end_percent が 28 ステップのどこまで効くかを数える（NumPy）。

- percent_to_sigma（comfy/model_sampling.py の ModelSamplingDiscrete）: percent p を sigma(999 × (1 - p)) に変える
- ControlBase.get_control（comfy/controlnet.py）: そのステップの sigma が
  [percent_to_sigma(end), percent_to_sigma(start)] の外なら、ControlNet を呼ばない
- scheduler=normal の 28 ステップの sigma の列は、img2img Denoise のノートの schedule.py と同じ計算

使い方: python3 control_steps.py
"""
import numpy as np

betas = np.linspace(0.00085 ** 0.5, 0.012 ** 0.5, 1000, dtype=np.float64) ** 2
SIGMAS = ((1 - np.cumprod(1.0 - betas)) / np.cumprod(1.0 - betas)) ** 0.5
LOG = np.log(SIGMAS)


def sigma(t):
    t = np.clip(t, 0, 999)
    lo, hi = np.floor(t).astype(int), np.ceil(t).astype(int)
    w = t - lo
    return np.exp((1 - w) * LOG[lo] + w * LOG[hi])


def percent_to_sigma(p):
    if p <= 0.0:
        return 999999999.9
    if p >= 1.0:
        return 0.0
    return float(sigma(np.float64((1.0 - p) * 999.0)))


steps = 28
ts = np.linspace(999, 0, steps, dtype=np.float32).astype(np.float64)
model_sigmas = sigma(ts)  # 28 回のモデルの呼び出しで使う sigma（末尾の 0 は呼ばない）
print("end_percent  sigma_end  active_steps  (start_percent=0)")
for end in [0.2, 0.4, 0.6, 0.8, 1.0]:
    lo, hi = percent_to_sigma(end), percent_to_sigma(0.0)
    active = [i + 1 for i, s in enumerate(model_sigmas) if lo <= s <= hi]
    print(f"{end:11.1f}  {lo:9.4f}  {len(active):2d} / {steps}  (step {active[0]}..{active[-1]})")
