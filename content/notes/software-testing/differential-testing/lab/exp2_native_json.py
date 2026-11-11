#!/usr/bin/env python3
"""実験 2: jz がテキストから作った JSON を、ip 自身が出す JSON と比べる。

`ip -br link` / `ip -br addr` の出力を jz で読んだ結果と、`ip -j -br link` / `ip -j -br addr` を、
行の位置で対にする。キーの名前は両者で違う（jz は interface、ip は ifname）ので、キーは比べず、
1 行に含まれる値の集まりを比べる。jz にだけある値は、jz が作った値か読み違えた値の候補になる。

候補のうち、次の 2 つは表現の違いとして数えるだけにする。
  アドレスと長さ: jz の "A/N" に対して、ip の JSON に A と N がある。
  ifN と N:       jz の "ifN" に対して、ip の JSON に N がある（veth の相手の番号）。
残った値を「その他」として表示する。

公開用の出力では、ループバック以外のアドレスと MAC アドレスを伏せる。

使い方: python3 exp2_native_json.py <jz の実行ファイル> [出力の JSON]
"""
import json
import re
import subprocess
import sys
from collections import Counter

PAIRS = [
    (["ip", "-br", "link"], ["ip", "-j", "-br", "link"]),
    (["ip", "-br", "addr"], ["ip", "-j", "-br", "addr"]),
]
MAC = re.compile(r"\b[0-9a-f]{2}(:[0-9a-f]{2}){5}\b")
V4 = re.compile(r"\b(?!127\.)\d{1,3}(\.\d{1,3}){3}\b")
V6 = re.compile(r"\b(fe80|fc00|fd[0-9a-f]{2}|2[0-9a-f]{3}):[0-9a-f:]*")


def leaves(v, out):
    if isinstance(v, dict):
        for x in v.values():
            leaves(x, out)
    elif isinstance(v, list):
        for x in v:
            leaves(x, out)
    elif v is not None:
        out.append(str(v))
    return out


def mask(s):
    return V6.sub("<v6>", V4.sub("<v4>", MAC.sub("<mac>", s)))


def classify(extra, missing):
    """jz にだけある値を、表現の違いとその他に分ける。"""
    kinds = Counter()
    other = []
    for v in extra.elements():
        m = re.fullmatch(r"(.+)/(\d+)", v)
        if m and missing[m.group(1)] and missing[m.group(2)]:
            kinds["アドレスと長さ"] += 1
            missing[m.group(1)] -= 1
            missing[m.group(2)] -= 1
            continue
        m = re.fullmatch(r"if(\d+)", v)
        if m and missing[m.group(1)]:
            kinds["ifN と N"] += 1
            missing[m.group(1)] -= 1
            continue
        other.append(v)
    return kinds, other


def main():
    jz = sys.argv[1]
    report = []
    for text_cmd, native_cmd in PAIRS:
        ours = json.loads(subprocess.run([jz, "run", *text_cmd], capture_output=True,
                                         text=True, check=True).stdout)
        native = json.loads(subprocess.run(native_cmd, capture_output=True, text=True,
                                           check=True).stdout)
        assert len(ours) == len(native), (len(ours), len(native))
        values = 0
        kinds = Counter()
        others = []
        for o, n in zip(ours, native):
            a, b = Counter(leaves(o, [])), Counter(leaves(n, []))
            values += sum(a.values())
            missing = b - a
            k, other = classify(a - b, missing)
            kinds += k
            for v in other:
                others.append({"jz": mask(v),
                               "native_only": sorted(mask(x) for x in (+missing).elements())})
        name = " ".join(text_cmd)
        only = sum(kinds.values()) + len(others)
        print(f"{name}: {len(ours)} 行、{values} 値、jz にだけある値 {only}"
              f"（アドレスと長さ {kinds['アドレスと長さ']}、ifN と N {kinds['ifN と N']}、"
              f"その他 {len(others)}）")
        for x in others:
            print(f"  その他: jz {x['jz']!r}、ip の JSON にだけある値 {x['native_only']}")
        report.append({"command": name, "rows": len(ours), "values": values,
                       "kinds": dict(kinds), "other": others})
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
