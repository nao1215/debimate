"""トークン感度: 入力の英数字トークンを 1 文字ずつ変え、出力に反映されているかを検証する。

関係: トークンを 1 文字変えたら、読み取りがエラーになるか、出力が変わるはず。
エラーにならず出力も同じなら、そのトークンは出力に反映されていない（エラーにせずに捨てている）。

dig の統計行を読む小さなパーサーを 2 つ用意する。BUGGY の SERVER 行の正規表現は、
jsonize の dig/bind の定義に 2026-09 まであった形（名前付きグループの外の [^\\n]* が
残りを飲む）を写したもの。どちらのパーサーも「どの正規表現にも一致しない行があれば
エラー」にしているので、行全体に一致する BUGGY の形はエラーにならない。
"""
import json
import re
import sys

FIXTURE = """\
;; Query time: 3 msec
;; SERVER: 127.0.0.53#53(127.0.0.53) (UDP)
;; WHEN: Wed Nov 11 10:00:00 JST 2026
;; MSG SIZE  rcvd: 56
"""

COMMON = [
    r"^;; Query time: (?P<query_time_ms>\d+) msec$",
    r"^;; WHEN: (?P<when>.+)$",
    r"^;; MSG SIZE  rcvd: (?P<msg_size>\d+)$",
]
BUGGY = COMMON + [r"^;; SERVER: (?P<server>[^\s(]+)[^\n]*$"]
FIXED = COMMON + [
    r"^;; SERVER: (?P<server>[^\s(]+)\((?P<server_name>[^)]*)\) \((?P<protocol>\w+)\)$"
]


def parse(text, patterns):
    """各行がどれかの正規表現の全体に一致しなければ ValueError。"""
    out = {}
    for line in text.splitlines():
        for p in patterns:
            m = re.match(p, line)
            if m:
                out.update(m.groupdict())
                break
        else:
            raise ValueError(f"unread line: {line!r}")
    return out


def mutate(tok):
    """最後の 1 文字だけ変える（数字は +1、英字は別の英字）。"""
    c = tok[-1]
    if c.isdigit():
        n = str((int(c) + 1) % 10)
    elif c.lower() == "z":
        n = "a" if c.islower() else "A"
    else:
        n = chr(ord(c) + 1)
    return tok[:-1] + n


def sweep(patterns):
    base = parse(FIXTURE, patterns)
    result = []
    for m in re.finditer(r"[A-Za-z0-9]+", FIXTURE):
        changed = FIXTURE[: m.start()] + mutate(m.group()) + FIXTURE[m.end():]
        try:
            reflected = parse(changed, patterns) != base
        except ValueError:
            reflected = True  # エラーになった = そのトークンは読まれている
        result.append({"start": m.start(), "token": m.group(), "reflected": reflected})
    return base, result


def report(name, patterns):
    base, result = sweep(patterns)
    lost = [r for r in result if not r["reflected"]]
    print(f"== {name}: {len(result)} checks, {len(lost)} not reflected")
    print("output:", json.dumps(base, ensure_ascii=False))
    for r in lost:
        line_no = FIXTURE.count("\n", 0, r["start"]) + 1
        print(f"  line {line_no}: {r['token']!r} changed, output unchanged")
    return result


if __name__ == "__main__":
    buggy = report("BUGGY", BUGGY)
    print()
    fixed = report("FIXED", FIXED)
    if len(sys.argv) > 1:  # 図の生成用に結果を書き出す
        with open(sys.argv[1], "w") as f:
            json.dump({"fixture": FIXTURE, "buggy": buggy, "fixed": fixed}, f, ensure_ascii=False, indent=1)
