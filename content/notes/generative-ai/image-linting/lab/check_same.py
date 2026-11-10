"""同じ seed・同じワークフローで生成し直した PNG が、元の PNG と画素まで一致するかを調べる。

使い方:
    python3 check_same.py <元の PNG のディレクトリ> <生成し直した PNG のディレクトリ>
"""
import os
import sys

import numpy as np
from PIL import Image


def main():
    a_dir, b_dir = sys.argv[1], sys.argv[2]
    for fn in sorted(os.listdir(b_dir)):
        a = np.asarray(Image.open(os.path.join(a_dir, fn)).convert("RGB"), dtype=np.int16)
        b = np.asarray(Image.open(os.path.join(b_dir, fn)).convert("RGB"), dtype=np.int16)
        diff = int((a != b).any(axis=2).sum())
        print(f"{fn}: 違う画素 {diff} / {a.shape[0] * a.shape[1]}")


if __name__ == "__main__":
    main()
