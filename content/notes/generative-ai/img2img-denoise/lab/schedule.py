"""ComfyUI v0.35.0 の KSampler が denoise から作るノイズの段（sigma の列）を、NumPy で再現する。

SDXL（eps 予測、ModelSamplingDiscrete）と scheduler=normal の場合。
- comfy/model_sampling.py の ModelSamplingDiscrete（beta 0.00085〜0.012、1000 段）
- comfy/samplers.py の normal_scheduler と KSampler.set_steps
を写している。

使い方: python3 schedule.py [steps] [結果の JSON]
"""
import json
import sys

import numpy as np

# ModelSamplingDiscrete: betas は sqrt を線形に並べて 2 乗する（"linear" の実装）
betas = np.linspace(0.00085 ** 0.5, 0.012 ** 0.5, 1000, dtype=np.float64) ** 2
alphas_cumprod = np.cumprod(1.0 - betas)
SIGMAS = ((1 - alphas_cumprod) / alphas_cumprod) ** 0.5
LOG_SIGMAS = np.log(SIGMAS)


def sigma(t):
    t = np.clip(t, 0, len(SIGMAS) - 1)
    lo, hi = np.floor(t).astype(int), np.ceil(t).astype(int)
    w = t - lo
    return np.exp((1 - w) * LOG_SIGMAS[lo] + w * LOG_SIGMAS[hi])


def normal_scheduler(steps):
    # timestep(sigma_max) = 999、timestep(sigma_min) = 0。sigma(0) は 0 ではないので 0 を末尾に足す
    ts = np.linspace(999, 0, steps, dtype=np.float32).astype(np.float64)
    return np.append(sigma(ts), 0.0)


def ksampler_sigmas(steps, denoise):
    """KSampler.set_steps と同じ。denoise < 1 なら steps/denoise 段の列を作り、末尾の steps+1 個を使う。"""
    if denoise > 0.9999:
        return normal_scheduler(steps), steps
    new_steps = int(steps / denoise)
    return normal_scheduler(new_steps)[-(steps + 1):], new_steps


def main():
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 28
    rows = []
    print(f"sigma_max={SIGMAS[-1]:.4f} sigma_min={SIGMAS[0]:.4f}")
    print("denoise  long_schedule  skipped  sigma_start  keep(1/sqrt(1+s^2))")
    for d in [0.3, 0.45, 0.5, 0.6, 0.75, 0.86, 0.95, 1.0]:
        sig, n = ksampler_sigmas(steps, d)
        s0 = float(sig[0])
        keep = 1 / np.sqrt(1 + s0 ** 2)
        print(f"{d:7.2f}  {n:13d}  {n - steps:7d}  {s0:11.4f}  {keep:8.3f}")
        rows.append({"denoise": d, "long_schedule": n, "skipped": n - steps,
                     "sigma_start": s0, "keep": float(keep), "sigmas": [float(x) for x in sig]})
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w") as f:
            json.dump({"steps": steps, "rows": rows}, f, indent=1)


if __name__ == "__main__":
    main()
