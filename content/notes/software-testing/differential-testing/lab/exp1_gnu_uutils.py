#!/usr/bin/env python3
"""実験 1: 同じ入力を GNU coreutils と uutils に渡し、出力を比べる。

各ケースを、同じファイルを作り直した別々の作業ディレクトリで両方の実装に実行させる。
呼び出し名（argv[0]）はコマンド名にそろえる。gnuls として起動すると、エラーメッセージが
"gnuls: ..." になり、それだけで差になるため。

比べ方は 2 通り。
  raw:        stdout、stderr、終了コードを全部そのまま比べる。
  normalized: stdout と終了コードを比べ、stderr は「何か出したか」だけを比べる。

使い方: python3 exp1_gnu_uutils.py [出力の JSON]
"""
import json
import getpass
import os
import subprocess
import sys
import tempfile

GNU = "/usr/bin/gnu{}"
UUTILS = "/usr/lib/cargo/bin/coreutils/{}"

# (ケース名, argv, リダイレクト)。"full" なら stdout を /dev/full に、ファイル名ならそのファイルを stdin にする。
CASES = [
    ("ls", ["ls"], None),
    ("ls -l（xattr 付き）", ["ls", "-l", "--time-style=+%Y", "attr.txt"], None),
    ("ls --bogus", ["ls", "--bogus"], None),
    ("cat 無いファイル", ["cat", "missing.txt"], None),
    ("sort", ["sort", "data.txt"], None),
    ("sort -n", ["sort", "-n", "nums.txt"], None),
    ("uniq -c", ["uniq", "-c", "data.txt"], None),
    ("wc", ["wc", "data.txt", "nums.txt"], None),
    ("head -n 2", ["head", "-n", "2", "data.txt"], None),
    ("tail -n 2", ["tail", "-n", "2", "data.txt"], None),
    ("cut -d, -f2", ["cut", "-d,", "-f2", "data.csv"], None),
    ("tr a-z A-Z", ["tr", "a-z", "A-Z"], "data.txt"),
    ("seq 0.1 0.1 0.5", ["seq", "0.1", "0.1", "0.5"], None),
    ("printf %05.1f", ["printf", "%05.1f\\n", "3.14159"], None),
    ("date -d @0", ["date", "-u", "-d", "@0"], None),
    ("numfmt --to=iec", ["numfmt", "--to=iec", "1048576"], None),
    ("expr 7 / 2", ["expr", "7", "/", "2"], None),
    ("basename", ["basename", "/a/b/c.txt", ".txt"], None),
    ("md5sum", ["md5sum", "data.txt"], None),
    ("nl", ["nl", "data.txt"], None),
    ("fold -w 3", ["fold", "-w", "3", "data.txt"], None),
    ("od -c", ["od", "-c", "nums.txt"], None),
    ("base64", ["base64", "data.txt"], None),
    ("factor 360", ["factor", "360"], None),
    ("stat -c %s", ["stat", "-c", "%s", "data.txt"], None),
    ("tac", ["tac", "data.txt"], None),
    ("paste", ["paste", "data.txt", "nums.txt"], None),
    ("du -b", ["du", "-b", "data.txt"], None),
    ("ls（/dev/full へ）", ["ls"], "full"),
    ("printf（/dev/full へ）", ["printf", "x"], "full"),
    ("sort（/dev/full へ）", ["sort", "data.txt"], "full"),
    ("md5sum（/dev/full へ）", ["md5sum", "data.txt"], "full"),
]


def make_fixture(d):
    def w(name, text):
        with open(os.path.join(d, name), "w") as f:
            f.write(text)

    w("data.txt", "pear\napple\napple\nfig\n")
    w("nums.txt", "10\n9\n100\n")
    w("data.csv", "id,name\n1,pear\n2,fig\n")
    w("attr.txt", "x\n")
    os.setxattr(os.path.join(d, "attr.txt"), "user.note", b"1")
    for name in os.listdir(d):
        os.utime(os.path.join(d, name), (978307200, 978307200))  # 2001-01-01


def run(impl, argv, redirect):
    exe = (GNU if impl == "gnu" else UUTILS).format(argv[0])
    env = {"LC_ALL": "C", "PATH": "/usr/bin:/bin", "TZ": "UTC"}
    with tempfile.TemporaryDirectory() as d:
        make_fixture(d)
        stdin = subprocess.DEVNULL
        out = subprocess.PIPE
        if redirect == "full":
            out = open("/dev/full", "w")
        elif redirect:
            stdin = open(os.path.join(d, redirect))
        p = subprocess.run(argv, executable=exe, cwd=d, env=env,
                           stdin=stdin, stdout=out, stderr=subprocess.PIPE)
        # 公開用の出力では、ls -l に出る所有者の名前を伏せる。
        user = getpass.getuser()
        return {
            "stdout": (p.stdout or b"").decode(errors="replace").replace(f" {user} ", " user ").replace(f" {user} ", " user "),
            "stderr": p.stderr.decode(errors="replace"),
            "exit": p.returncode,
        }


def main():
    results = []
    for name, argv, redirect in CASES:
        g = run("gnu", argv, redirect)
        u = run("uutils", argv, redirect)
        raw = g != u
        normalized = (g["stdout"], g["exit"], bool(g["stderr"])) != \
                     (u["stdout"], u["exit"], bool(u["stderr"]))
        results.append({"case": name, "gnu": g, "uutils": u,
                         "raw_diff": raw, "normalized_diff": normalized})

    n = len(results)
    raw = sum(r["raw_diff"] for r in results)
    norm = sum(r["normalized_diff"] for r in results)
    print(f"{n} ケース、raw で差 {raw}、normalized で差 {norm}")
    for r in results:
        if not r["raw_diff"]:
            continue
        mark = "差" if r["normalized_diff"] else "ノイズ"
        g, u = r["gnu"], r["uutils"]
        print(f"[{mark}] {r['case']}")
        print(f"  GNU    exit={g['exit']} stdout={g['stdout'][:40]!r} stderr={g['stderr'][:70]!r}")
        print(f"  uutils exit={u['exit']} stdout={u['stdout'][:40]!r} stderr={u['stderr'][:70]!r}")

    if len(sys.argv) > 1:
        with open(sys.argv[1], "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
