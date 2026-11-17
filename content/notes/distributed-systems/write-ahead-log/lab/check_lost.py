"""check_lost.py: killtest -out の JSON で、消えた行と、最後に OS へ渡した位置（write_lsn の最大）より後ろの行を比べる。
  python3 check_lost.py out.json
"""
import json
import sys


def lsn(s):
    hi, lo = s.split("/")
    return (int(hi, 16) << 32) + int(lo, 16)


d = json.load(open(sys.argv[1]))
lost = set(d["lost"])
last_write = max(lsn(p["write_lsn"]) for p in d["polls"])
beyond = {a["id"] for a in d["acks"] if lsn(a["lsn"]) > last_write}
print(f"setting={d['setting']} acked={d['acked']} survived={d['survived']} lost={len(lost)}")
print(f"last_write_lsn=0/{last_write:X} acked_beyond_last_write={len(beyond)}")
print(f"lost_equals_beyond={lost == beyond} lost_ids={min(lost)}..{max(lost)}")
