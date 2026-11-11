"""GGUF ファイルのヘッダーだけを読み、1 トークンの decode で読む重みのバイト数を見積もる（Python 標準ライブラリだけ）。

テンソルを次の 4 つに分ける。
  embed   : token_embd.weight。1 トークンにつき 1 行しか読まない
  experts : 名前に _exps を含む MoE の専門家の重み（ffn_gate_exps など）。
            1 トークンで動くのは expert_used_count / expert_count の割合だけ
  other   : 上記以外（注意機構・ルーター・正規化・出力層など）。1 トークンごとに全部読む

使い方:
    python3 gguf_bytes.py <名前>=<GGUF のパス> [...] --json gguf.json
"""
import json
import os
import struct
import sys

# ggml の型番号 -> (名前, 1 ブロックの要素数, 1 ブロックのバイト数)
# llama.cpp の ggml/src/ggml.c の type_traits と ggml-common.h の構造体の大きさ
GGML_TYPES = {
    0: ("F32", 1, 4), 1: ("F16", 1, 2), 2: ("Q4_0", 32, 18), 3: ("Q4_1", 32, 20),
    6: ("Q5_0", 32, 22), 7: ("Q5_1", 32, 24), 8: ("Q8_0", 32, 34), 10: ("Q2_K", 256, 84),
    11: ("Q3_K", 256, 110), 12: ("Q4_K", 256, 144), 13: ("Q5_K", 256, 176),
    14: ("Q6_K", 256, 210), 30: ("BF16", 1, 2), 39: ("MXFP4", 32, 17),
}
SCALAR = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f",
          7: "<?", 10: "<Q", 11: "<q", 12: "<d"}


class Reader:
    def __init__(self, f):
        self.f = f

    def unpack(self, fmt):
        return struct.unpack(fmt, self.f.read(struct.calcsize(fmt)))[0]

    def string(self):
        return self.f.read(self.unpack("<Q")).decode("utf-8", errors="replace")

    def value(self, vtype):
        if vtype == 8:
            return self.string()
        if vtype == 9:
            itype, count = self.unpack("<I"), self.unpack("<Q")
            return [self.value(itype) for _ in range(count)]
        return self.unpack(SCALAR[vtype])


def read_gguf(path):
    with open(path, "rb") as f:
        r = Reader(f)
        assert f.read(4) == b"GGUF", path
        r.unpack("<I")
        n_tensors, n_kv = r.unpack("<Q"), r.unpack("<Q")
        meta = {}
        for _ in range(n_kv):
            key = r.string()
            meta[key] = r.value(r.unpack("<I"))
        tensors = []
        for _ in range(n_tensors):
            name = r.string()
            shape = [r.unpack("<Q") for _ in range(r.unpack("<I"))]
            ttype = r.unpack("<I")
            r.unpack("<Q")
            tensors.append((name, shape, ttype))
    return meta, tensors


def summarize(label, path):
    meta, tensors = read_gguf(path)
    arch = meta["general.architecture"]
    n_exp = meta.get(f"{arch}.expert_count", 0)
    n_used = meta.get(f"{arch}.expert_used_count", 0)
    groups = {g: {"params": 0, "bytes": 0} for g in ("embed", "experts", "other")}
    types = {}
    for name, shape, ttype in tensors:
        tname, block, nbytes = GGML_TYPES[ttype]
        n = 1
        for d in shape:
            n *= d
        b = n // block * nbytes
        g = "embed" if name == "token_embd.weight" else "experts" if "_exps" in name else "other"
        groups[g]["params"] += n
        groups[g]["bytes"] += b
        types[tname] = types.get(tname, 0) + b
        if g == "embed":
            embed_row = b // shape[1]          # 1 行（1 トークン分）のバイト数
    total_p = sum(v["params"] for v in groups.values())
    total_b = sum(v["bytes"] for v in groups.values())
    frac = n_used / n_exp if n_exp else 1.0
    active_p = groups["other"]["params"] + groups["experts"]["params"] * frac + groups["embed"]["params"] / meta.get(f"{arch}.vocab_size", len(meta.get("tokenizer.ggml.tokens", [1])))
    read_b = groups["other"]["bytes"] + groups["experts"]["bytes"] * frac + embed_row
    res = {
        "file_size": os.path.getsize(path), "arch": arch,
        "block_count": meta.get(f"{arch}.block_count"),
        "context_length": meta.get(f"{arch}.context_length"),
        "expert_count": n_exp, "expert_used_count": n_used,
        "head_count": meta.get(f"{arch}.attention.head_count"),
        "head_count_kv": meta.get(f"{arch}.attention.head_count_kv"),
        "key_length": meta.get(f"{arch}.attention.key_length"),
        "sliding_window": meta.get(f"{arch}.attention.sliding_window"),
        "groups": groups, "bytes_by_type": types,
        "total_params": total_p, "total_bytes": total_b,
        "active_params": int(active_p), "decode_read_bytes": int(read_b),
    }
    print(f"[{label}] arch={arch} file={res['file_size']:,} B  layers={res['block_count']} "
          f"experts={n_used}/{n_exp} heads={res['head_count']}/{res['head_count_kv']} "
          f"key_len={res['key_length']} sliding_window={res['sliding_window']}")
    for g, v in groups.items():
        print(f"  {g:8s} params {v['params']:15,}  bytes {v['bytes']:15,}")
    print(f"  total    params {total_p:15,}  bytes {total_b:15,}")
    print(f"  active params per token ~ {int(active_p):,}")
    print(f"  bytes read per decoded token (weights only) ~ {int(read_b):,}")
    print("  bytes by type:", ", ".join(f"{k} {v / 1e9:.2f} GB" for k, v in sorted(types.items(), key=lambda x: -x[1])))
    return res


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
