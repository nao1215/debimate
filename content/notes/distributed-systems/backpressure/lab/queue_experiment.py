"""到着率 200 件/秒、処理率 100 件/秒で 3 種類のキューを 4 秒間動かす実験。"""
import asyncio
import json
import sys
import time
import tracemalloc

ARRIVAL_INTERVAL = 0.005  # 5 ms ごとに 1 件到着する（200 件/秒）
SERVICE_TIME = 0.010      # 1 件の処理に 10 ms かかる（100 件/秒）
DURATION = 4.0            # 4 秒間だけ要求を作る
MAXSIZE = 50              # 上限ありキューの長さ
PAYLOAD = 10_000          # 1 件あたり 10 KB のデータを持たせる


async def run(mode):
    queue = asyncio.Queue(maxsize=0 if mode == "unbounded" else MAXSIZE)
    stats = {"sent": 0, "rejected": 0, "done": 0,
             "samples": [], "waits": []}
    start = time.monotonic()

    async def producer():
        n = 0
        while True:
            now = time.monotonic() - start
            if now >= DURATION:
                return
            item = (time.monotonic(), bytes(PAYLOAD))
            if mode == "reject":
                try:
                    queue.put_nowait(item)
                except asyncio.QueueFull:
                    stats["rejected"] += 1
            else:
                await queue.put(item)  # unbounded は即座に返る。block は空くまで待つ
            stats["sent"] += 1
            n += 1
            if mode == "block":
                await asyncio.sleep(ARRIVAL_INTERVAL)  # 待たされた分だけ後ろへずれる
            else:
                # 到着は外から決まった時刻に来る（遅れても取り戻す）
                await asyncio.sleep(max(0, n * ARRIVAL_INTERVAL - now))

    async def consumer():
        while True:
            enqueued, _ = await queue.get()
            stats["waits"].append((time.monotonic() - start,
                                   time.monotonic() - enqueued))
            await asyncio.sleep(SERVICE_TIME)
            stats["done"] += 1

    async def sampler():
        while True:
            stats["samples"].append((time.monotonic() - start, queue.qsize()))
            await asyncio.sleep(0.1)

    tracemalloc.start()
    tasks = [asyncio.create_task(consumer()), asyncio.create_task(sampler())]
    await producer()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    for t in tasks:
        t.cancel()
    stats["peak_mb"] = peak / 1_000_000
    stats["left"] = queue.qsize()  # 4 秒の時点でまだ並んでいる件数
    return stats


def main():
    results = {}
    print(f"{'mode':<10}{'sent':>6}{'rejected':>9}{'done':>6}"
          f"{'left':>6}{'max_wait_s':>11}{'last_wait_s':>12}{'peak_MB':>9}")
    for mode in ["unbounded", "block", "reject"]:
        s = asyncio.run(run(mode))
        results[mode] = s
        print(f"{mode:<10}{s['sent']:>6}{s['rejected']:>9}{s['done']:>6}"
              f"{s['left']:>6}{max(w for _, w in s['waits']):>11.2f}"
              f"{s['left'] * SERVICE_TIME:>12.2f}{s['peak_mb']:>9.1f}")
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w") as f:
            json.dump(results, f)


main()
