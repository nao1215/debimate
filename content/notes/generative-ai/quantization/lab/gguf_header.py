"""GGUF ファイルのヘッダーだけを読み、テンソルの型ごとの個数とバイト数を数える。

テンソルの中身は読まない。Python 標準ライブラリだけで動く。

使い方:
    python3 gguf_header.py <名前>=<GGUF のパス> [<名前>=<GGUF のパス> ...] [--json 結果.json]
"""
import json
import os
import struct
import sys
from collections import defaultdict

# ggml の型番号 -> (名前, 1 ブロックの要素数, 1 ブロックのバイト数)
# 値は llama.cpp の ggml/src/ggml.c の type_traits と ggml-common.h の構造体の大きさ
GGML_TYPES = {
    0: ("F32", 1, 4),
    1: ("F16", 1, 2),
    2: ("Q4_0", 32, 18),
    3: ("Q4_1", 32, 20),
    6: ("Q5_0", 32, 22),
    7: ("Q5_1", 32, 24),
    8: ("Q8_0", 32, 34),
    10: ("Q2_K", 256, 84),
    11: ("Q3_K", 256, 110),
    12: ("Q4_K", 256, 144),
    13: ("Q5_K", 256, 176),
    14: ("Q6_K", 256, 210),
    30: ("BF16", 1, 2),
}

# GGUF のメタデータの値の型番号 -> struct の書式（8: 文字列、9: 配列は別に処理する）
SCALAR = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f",
          7: "<?", 10: "<Q", 11: "<q", 12: "<d"}


class Reader:
    def __init__(self, f):
        self.f = f

    def unpack(self, fmt):
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self.f.read(size))[0]

    def string(self):
        n = self.unpack("<Q")
        return self.f.read(n).decode("utf-8", errors="replace")

    def value(self, vtype):
        if vtype == 8:
            return self.string()
        if vtype == 9:
            itype, count = self.unpack("<I"), self.unpack("<Q")
            return [self.value(itype) for _ in range(count)]
        return self.unpack(SCALAR[vtype])


def read_gguf(path):
    """GGUF のヘッダー（メタデータとテンソルの一覧）を返す。"""
    with open(path, "rb") as f:
        r = Reader(f)
        if f.read(4) != b"GGUF":
            raise ValueError(f"{path} is not GGUF")
        version = r.unpack("<I")
        n_tensors, n_kv = r.unpack("<Q"), r.unpack("<Q")
        meta = {}
        for _ in range(n_kv):
            key = r.string()
            meta[key] = r.value(r.unpack("<I"))
        tensors = []
        for _ in range(n_tensors):
            name = r.string()
            n_dims = r.unpack("<I")
            shape = [r.unpack("<Q") for _ in range(n_dims)]
            ttype = r.unpack("<I")
            offset = r.unpack("<Q")
            tensors.append({"name": name, "shape": shape, "type": ttype, "offset": offset})
        align = meta.get("general.alignment", 32)
        data_start = (f.tell() + align - 1) // align * align
    return version, meta, tensors, data_start


def tensor_bytes(t):
    _, block, nbytes = GGML_TYPES[t["type"]]
    n = 1
    for d in t["shape"]:
        n *= d
    return n, n // block * nbytes


def summarize(label, path):
    version, meta, tensors, data_start = read_gguf(path)
    by_type = defaultdict(lambda: {"tensors": 0, "params": 0, "bytes": 0})
    for t in tensors:
        n, b = tensor_bytes(t)
        s = by_type[GGML_TYPES[t["type"]][0]]
        s["tensors"] += 1
        s["params"] += n
        s["bytes"] += b
    params = sum(s["params"] for s in by_type.values())
    weight_bytes = sum(s["bytes"] for s in by_type.values())
    size = os.path.getsize(path)
    print(f"[{label}] {os.path.basename(path)[:19]}...")
    print(f"  file size        : {size:,} bytes")
    print(f"  GGUF version     : {version}, metadata keys: {len(meta)}, tensors: {len(tensors)}")
    print(f"  general.file_type: {meta.get('general.file_type')}")
    print(f"  params           : {params:,}")
    print(f"  weight bytes     : {weight_bytes:,} ({weight_bytes * 8 / params:.2f} bits/param)")
    print(f"  header + padding : {data_start:,} bytes")
    for name, s in sorted(by_type.items(), key=lambda x: -x[1]["bytes"]):
        print(f"    {name:5s} tensors {s['tensors']:4d}  params {s['params']:13,}"
              f"  bytes {s['bytes']:13,}  ({s['bytes'] * 8 / s['params']:.4f} bits/param)")
    return {"file_size": size, "params": params, "weight_bytes": weight_bytes,
            "file_type": meta.get("general.file_type"), "by_type": dict(by_type),
            "tensor_types": {t["name"]: GGML_TYPES[t["type"]][0] for t in tensors}}


def main():
    args = sys.argv[1:]
    out = None
    if "--json" in args:
        i = args.index("--json")
        out = args[i + 1]
        del args[i:i + 2]
    result = {}
    for a in args:
        label, path = a.split("=", 1)
        result[label] = summarize(label, path)
        print()
    if out:
        with open(out, "w") as f:
            json.dump(result, f, indent=1)


if __name__ == "__main__":
    main()
