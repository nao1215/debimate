"""inference-serving ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/inference-serving_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/mlops/inference-serving"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Latency distribution for online inference
# ============================================================
rng = np.random.default_rng(0)
# Simulated request latencies (ms)
# Most requests fast, but heavy tail
n = 100_000
base = rng.gamma(shape=2.0, scale=15, size=n)  # bulk
tail = rng.exponential(scale=80, size=n) * (rng.random(n) < 0.05)
latencies = base + tail

p50 = np.percentile(latencies, 50)
p95 = np.percentile(latencies, 95)
p99 = np.percentile(latencies, 99)

plt.figure(figsize=(8.5, 4.5))
plt.hist(latencies, bins=80, range=(0, 350), color=COLOR_BLUE, edgecolor="white")
for p, label, color in [(p50, "P50", COLOR_GREEN), (p95, "P95", COLOR_ORANGE),
                          (p99, "P99", COLOR_RED)]:
    plt.axvline(p, color=color, lw=2, ls="--", label=f"{label} = {p:.0f}ms")
plt.xlabel("latency (ms)")
plt.ylabel("requests")
plt.title("Online inference: P99 dominates UX, not the average")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("serving_latency_distribution.svg")


# ============================================================
# Fig 2: Batch vs Online cost/throughput
# ============================================================
modes = ["Online\n(low latency)", "Micro-batch\n(50ms aggregation)",
         "Mini-batch\n(1s aggregation)", "Offline batch\n(daily 1B rows)"]
latency_p99 = [50, 120, 800, 8 * 3600 * 1000]  # ms
throughput = [200, 1500, 8000, 1_000_000_000 / (8 * 3600)]  # req/s
cost_per_million = [12, 4, 1.5, 0.3]  # $

fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

ax = axes[0]
bars = ax.bar(modes, latency_p99, color=[COLOR_RED, COLOR_ORANGE, COLOR_BLUE, COLOR_GREEN])
ax.set_yscale("log")
ax.set_ylabel("P99 latency (ms, log scale)")
ax.set_title("Latency (lower is better)")
for b, v in zip(bars, latency_p99):
    if v < 1000:
        ax.text(b.get_x() + b.get_width()/2, v * 1.2, f"{v}ms", ha="center", fontsize=9)
    elif v < 1_000_000:
        ax.text(b.get_x() + b.get_width()/2, v * 1.2, f"{v/1000:.1f}s", ha="center", fontsize=9)
    else:
        ax.text(b.get_x() + b.get_width()/2, v * 1.2, f"{v/1000/3600:.0f}h", ha="center", fontsize=9)
ax.tick_params(axis="x", labelsize=8)
ax.grid(True, alpha=0.25, axis="y")

ax = axes[1]
bars = ax.bar(modes, throughput, color=[COLOR_RED, COLOR_ORANGE, COLOR_BLUE, COLOR_GREEN])
ax.set_yscale("log")
ax.set_ylabel("throughput (req/s, log scale)")
ax.set_title("Throughput (higher is better)")
for b, v in zip(bars, throughput):
    if v >= 1000:
        ax.text(b.get_x() + b.get_width()/2, v * 1.2, f"{v/1000:.1f}k", ha="center", fontsize=9)
    else:
        ax.text(b.get_x() + b.get_width()/2, v * 1.2, f"{v:.0f}", ha="center", fontsize=9)
ax.tick_params(axis="x", labelsize=8)
ax.grid(True, alpha=0.25, axis="y")

ax = axes[2]
bars = ax.bar(modes, cost_per_million, color=[COLOR_RED, COLOR_ORANGE, COLOR_BLUE, COLOR_GREEN])
ax.set_ylabel("$ per 1M predictions")
ax.set_title("Cost (lower is better)")
for b, v in zip(bars, cost_per_million):
    ax.text(b.get_x() + b.get_width()/2, v + 0.3, f"${v}", ha="center", fontsize=9)
ax.tick_params(axis="x", labelsize=8)
ax.grid(True, alpha=0.25, axis="y")

plt.suptitle("Online vs batch: same accuracy, very different latency/throughput/cost",
             y=1.02)
plt.tight_layout()
save("serving_modes_compare.svg")


# ============================================================
# Fig 3: Replica scaling - throughput vs latency
# ============================================================
replicas = np.arange(1, 17)
# Throughput grows linearly (approximation); latency grows mildly per replica
# Modeling each replica has ~150 req/s capacity, but request queue adds tail latency
capacity = 150
total_throughput = capacity * replicas
# Single-replica P99 around 80ms, drops to 60 then plateaus
p99_per_load = 60 + 40 * np.exp(-replicas / 4)

fig, ax1 = plt.subplots(figsize=(8.5, 4.5))
color = COLOR_BLUE
ax1.set_xlabel("number of replicas")
ax1.set_ylabel("max throughput (req/s)", color=color)
ax1.plot(replicas, total_throughput, "o-", color=color, lw=2, markersize=6)
ax1.tick_params(axis="y", labelcolor=color)
ax1.grid(True, alpha=0.25)

ax2 = ax1.twinx()
color = COLOR_RED
ax2.set_ylabel("P99 latency under full load (ms)", color=color)
ax2.plot(replicas, p99_per_load, "s-", color=color, lw=2, markersize=6)
ax2.tick_params(axis="y", labelcolor=color)
ax2.set_ylim(40, 110)

plt.title("Horizontal scaling: throughput is linear, latency improves up to a knee point")
plt.tight_layout()
save("serving_replica_scaling.svg")


# ============================================================
# Fig 4: Caching effect on tail latency
# ============================================================
# Compare 3 strategies: no cache, in-memory cache 30% hit, in-memory 70% hit
no_cache = rng.gamma(shape=2.0, scale=20, size=20000) + 5
# 30% hit -> 30% latency = 2-5ms, 70% miss = normal
hit_30 = np.where(rng.random(20000) < 0.30,
                   rng.uniform(1, 5, 20000),
                   rng.gamma(shape=2.0, scale=20, size=20000) + 5)
hit_70 = np.where(rng.random(20000) < 0.70,
                   rng.uniform(1, 5, 20000),
                   rng.gamma(shape=2.0, scale=20, size=20000) + 5)

fig, ax = plt.subplots(figsize=(8, 5))
for arr, label, color in [(no_cache, "No cache", COLOR_RED),
                            (hit_30, "Cache 30% hit", COLOR_ORANGE),
                            (hit_70, "Cache 70% hit", COLOR_GREEN)]:
    p99 = np.percentile(arr, 99)
    sorted_arr = np.sort(arr)
    cdf = np.arange(1, len(arr) + 1) / len(arr)
    ax.plot(sorted_arr, cdf, color=color, lw=2,
            label=f"{label} (P99 = {p99:.0f}ms)")
ax.set_xscale("log")
ax.set_xlabel("latency (ms, log scale)")
ax.set_ylabel("cumulative fraction of requests")
ax.set_title("Caching dramatically improves the tail (P99)")
ax.legend(loc="lower right")
ax.grid(True, alpha=0.25)
plt.tight_layout()
save("serving_cache_effect.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
