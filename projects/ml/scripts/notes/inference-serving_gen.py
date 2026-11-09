"""inference-serving ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/inference-serving_gen.py
"""
import heapq
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "mlops" / "inference-serving"
NOTE_DIR.mkdir(parents=True, exist_ok=True)


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
# Fig 3: Replica scaling under a fixed load (M/M/c simulation)
# ============================================================
def simulate(replicas, arrival_rate=500, service_rate=150, n=200_000, seed=0):
    sim_rng = np.random.default_rng(seed)
    arrivals = np.cumsum(sim_rng.exponential(1 / arrival_rate, n))
    services = sim_rng.exponential(1 / service_rate, n)
    free_at = [0.0] * replicas
    latency = np.empty(n)
    for i in range(n):
        start = max(arrivals[i], heapq.heappop(free_at))
        end = start + services[i]
        heapq.heappush(free_at, end)
        latency[i] = end - arrivals[i]
    return latency[n // 10:] * 1000


replicas = np.arange(4, 13)
p50s, p99s = [], []
for c in replicas:
    lat = simulate(int(c))
    p50s.append(np.percentile(lat, 50))
    p99s.append(np.percentile(lat, 99))
floor = np.log(100) / 150 * 1000  # P99 of the service time itself

fig, ax = plt.subplots(figsize=(8.5, 4.5))
ax.plot(replicas, p99s, "s-", color=COLOR_RED, lw=2, markersize=6, label="P99")
ax.plot(replicas, p50s, "o-", color=COLOR_BLUE, lw=2, markersize=6, label="P50")
ax.axhline(floor, color=COLOR_GRAY, ls="--", lw=1.5,
           label=f"P99 of inference itself = {floor:.1f}ms")
ax.set_xticks(replicas)
ax.set_xticklabels([f"{c}\n({500 / (150 * c):.0%})" for c in replicas])
ax.set_xlabel("number of replicas (utilization)")
ax.set_ylabel("latency (ms)")
ax.set_ylim(0, 60)
ax.set_title("500 req/s to replicas of 150 req/s each: the tail flattens after 5-6 replicas")
ax.legend()
ax.grid(True, alpha=0.25)
plt.tight_layout()
save("serving_replica_scaling.svg")


# ============================================================
# Fig 4: Caching effect (same code as the note)
# ============================================================
rng = np.random.default_rng(1)
n = 20_000
fig, ax = plt.subplots(figsize=(8, 5))
for hit_rate, color in [(0.0, COLOR_RED), (0.3, COLOR_ORANGE), (0.7, COLOR_GREEN)]:
    hit = rng.random(n) < hit_rate
    latency = np.where(hit,
                       rng.uniform(1, 5, n),
                       rng.gamma(shape=2, scale=20, size=n) + 5)
    p50 = np.percentile(latency, 50)
    p99 = np.percentile(latency, 99)
    cdf = np.arange(1, n + 1) / n
    ax.plot(np.sort(latency), cdf, color=color, lw=2,
            label=f"hit {hit_rate:.0%} (P50 = {p50:.0f}ms, P99 = {p99:.0f}ms)")
ax.axhline(0.99, color=COLOR_GRAY, ls=":", lw=1)
ax.set_xscale("log")
ax.set_xlabel("latency (ms, log scale)")
ax.set_ylabel("cumulative fraction of requests")
ax.set_title("Caching moves the median a lot, the P99 only a little")
ax.legend(loc="lower right")
ax.grid(True, alpha=0.25)
plt.tight_layout()
save("serving_cache_effect.svg")


print("done:", sorted(p.name for p in NOTE_DIR.iterdir()))
