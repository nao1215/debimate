"""ComfyUI v0.35.0 が SDXL（eps 予測）に使う sigma の列を、NumPy で再現する。

- comfy/model_sampling.py の ModelSamplingDiscrete（beta 0.00085〜0.012 の "linear"、1000 段）
- comfy/samplers.py の normal_scheduler と simple_scheduler
- comfy/k_diffusion/sampling.py の get_sigmas_karras（rho = 7）
を写している。

使い方: python3 schedule.py [steps] [結果の JSON]
"""
import json
import sys

import numpy as np

# ModelSamplingDiscrete: betas は sqrt を線形に並べて 2 乗する（make_beta_schedule の "linear"）
betas = np.linspace(0.00085 ** 0.5, 0.012 ** 0.5, 1000, dtype=np.float64) ** 2
alphas_cumprod = np.cumprod(1.0 - betas)
SIGMAS = ((1 - alphas_cumprod) / alphas_cumprod) ** 0.5     # 1000 段の sigma。添字が timestep
LOG_SIGMAS = np.log(SIGMAS)
SIGMA_MIN, SIGMA_MAX = float(SIGMAS[0]), float(SIGMAS[-1])


def sigma(t):
    """timestep（小数も可）から sigma。log sigma を線形に補間する。"""
    t = np.clip(t, 0, len(SIGMAS) - 1)
    lo, hi = np.floor(t).astype(int), np.ceil(t).astype(int)
    w = t - lo
    return np.exp((1 - w) * LOG_SIGMAS[lo] + w * LOG_SIGMAS[hi])


def normal(steps):
    # timestep 999 から 0 までを等間隔に取る。sigma(0) は 0 ではないので末尾に 0 を足す
    ts = np.linspace(999, 0, steps, dtype=np.float32).astype(np.float64)
    return np.append(sigma(ts), 0.0)


def simple(steps):
    ss = len(SIGMAS) / steps
    return np.array([SIGMAS[-(1 + int(x * ss))] for x in range(steps)] + [0.0])


def karras(steps, rho=7.0):
    ramp = np.linspace(0, 1, steps)
    lo, hi = SIGMA_MIN ** (1 / rho), SIGMA_MAX ** (1 / rho)
    return np.append((hi + ramp * (lo - hi)) ** rho, 0.0)


def main():
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 28
    print(f"sigma_min={SIGMA_MIN:.4f} sigma_max={SIGMA_MAX:.4f}  "
          f"alpha_bar(T)={alphas_cumprod[-1]:.5f}")
    table = {"normal": normal(steps), "karras": karras(steps), "simple": simple(steps)}
    print(" k   normal  signal  noise    karras")
    for k in range(steps + 1):
        s = table["normal"][k]
        # x_k / sqrt(1+s^2) = 画像 * 1/sqrt(1+s^2) + ノイズ * s/sqrt(1+s^2)
        sig, noi = 1 / np.sqrt(1 + s * s), s / np.sqrt(1 + s * s)
        print(f"{k:2d} {s:8.4f}  {sig:6.3f} {noi:6.3f}  {table['karras'][k]:8.4f}")
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w") as f:
            json.dump({"steps": steps, "sigma_min": SIGMA_MIN, "sigma_max": SIGMA_MAX,
                       **{k: [float(x) for x in v] for k, v in table.items()}}, f, indent=1)


if __name__ == "__main__":
    main()
