"""実験 5: 0.5 秒ごとに 1 行を出す C のプログラムをパイプにつなぎ、1.2 秒後に Ctrl-C と同じ SIGINT を
パイプライン全体（プロセスグループ）に送る。読む側（stamp.py）に何行がいつ届いたかを、バッファありと stdbuf -oL で比べる。
（bash の & で起動すると SIGINT が無視される設定を引き継ぐため、Python から起動する）"""
import os
import signal
import subprocess
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))
for cmd in ["bin/slow_c | python3 stamp.py", "stdbuf -oL bin/slow_c | python3 stamp.py"]:
    os.environ["T0"] = str(time.time())
    p = subprocess.Popen(["bash", "-c", cmd], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    time.sleep(1.2)
    os.killpg(p.pid, signal.SIGINT)
    out = p.stdout.read().decode()
    p.wait()
    print(f"== {cmd}\n届いた行数={out.count(chr(10))}")
    print(out, end="")
