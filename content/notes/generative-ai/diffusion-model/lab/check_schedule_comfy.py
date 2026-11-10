"""schedule.py の値が、ComfyUI 自身のコードで計算した sigma の列と一致するかを確かめる。

ComfyUI のディレクトリで、その Python 環境から CPU で動かす（GPU もモデルのファイルも使わない）。
  cd <ComfyUI> && <ComfyUI の python> <このファイル> --cpu
"""
import os
import sys

sys.path[0] = os.getcwd()   # lab/comfy.py ではなく ComfyUI の comfy パッケージを読む
import comfy.model_sampling as ms  # noqa: E402
import comfy.samplers as samplers  # noqa: E402
import comfy.supported_models as sm  # noqa: E402

config = sm.SDXL({"model_channels": 320, "use_linear_in_transformer": True,
                  "transformer_depth": [0, 0, 2, 2, 10, 10], "context_dim": 2048,
                  "adm_in_channels": 2816, "use_temporal_attention": False})


class ModelSampling(ms.EPS, ms.ModelSamplingDiscrete):   # model_base.model_sampling() と同じ組み合わせ
    pass


m = ModelSampling(config)
for name in ["normal", "karras", "simple"]:
    print(name, [round(float(x), 4) for x in samplers.calculate_sigmas(m, name, 28)])
