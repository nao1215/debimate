"""OOM killer ノートの図を生成する。実測ではなく模式図。

earlyoom を入れていない PC で、空きメモリが減っていく時の経過を描く。
earlyoom の縦線は「入れていれば、この時点で SIGTERM を送る」位置を示す。

    python3 figures.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.family"] = ["Noto Sans CJK JP", "sans-serif"]
plt.rcParams["svg.fonttype"] = "none"

t = np.linspace(0, 100, 400)
# 空きメモリ(%)：回収と退避で、減り方が次第に鈍る
avail = 2 + 68 * np.exp(-t / 25)
# 応答の遅さ（相対値 0〜1）：空きが 20% を切った頃から悪化し、5% 付近で最悪になる
lag = np.clip((20 - avail) / 15, 0, 1) ** 1.5

t_early = t[np.argmax(avail < 10)]  # 空きメモリが 10% を切る時点
t_freeze = t[np.argmax(lag > 0.6)]  # 応答が大きく悪化した時点
t_kernel = 96                       # カーネルの OOM killer が動く時点

fig, ax = plt.subplots(figsize=(9, 4.4))
ax2 = ax.twinx()

ax.plot(t, avail, color="#222", lw=2, label="空きメモリ（左の軸）")
ax2.plot(t, lag, color="#888", lw=2, ls="--", label="操作への応答の遅さ（右の軸）")
ax.axhline(10, color="#555", lw=1, ls=":")
ax.text(1, 11.5, "10%", fontsize=10, color="#333")

ax.axvspan(t_freeze, t_kernel, color="#ddd", alpha=0.6, lw=0)
ax.text((t_freeze + t_kernel) / 2, 45, "GUI が固まって\n見える区間", ha="center", fontsize=10, color="#333")

ax.axvline(t_early, color="#555", lw=1, ls="--")
ax.text(t_early - 1, 70, "earlyoom を入れていれば\nここで SIGTERM を送る\n（空きスワップも 10% 以下の時）",
        ha="right", fontsize=9.5, color="#333")
ax.axvline(t_kernel, color="#222", lw=1.5)
ax.text(t_kernel - 1, 18, "カーネルの\nOOM killer", ha="right", fontsize=10, color="#222")

ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax2.set_ylim(0, 1.05)
ax.set_xlabel("時間", fontsize=11)
ax.set_ylabel("空きメモリ（%）", fontsize=11)
ax2.set_ylabel("応答の遅さ（相対値）", fontsize=11)
ax.set_xticks([])
ax2.set_yticks([])
for a in (ax, ax2):
    a.spines["top"].set_visible(False)

lines = ax.get_lines()[:1] + ax2.get_lines()[:1]
ax.legend(lines, [l.get_label() for l in lines], loc="upper left", bbox_to_anchor=(0.0, 1.02), frameon=False, fontsize=10)
fig.tight_layout()
fig.savefig("images/oom_timeline.svg", facecolor="#ffffff")
