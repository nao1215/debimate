"""Rate Limiting の 5 つの方式（と GCRA）を、時刻 t を受け取って通すか断るかを返す形で実装する。

時刻はすべて秒（float）。実時間の時計は使わず、呼び出し側が時刻を渡す。
数えるのは通した要求だけで、断った要求は数に入れない。
"""
import math
from collections import deque


class FixedWindow:
    """固定窓: 時刻を window 秒ごとの枠に切り、枠ごとの数が limit に達したら断る。"""

    def __init__(self, limit, window):
        self.limit, self.window = limit, window
        self.current, self.count = None, 0

    def allow(self, t):
        w = math.floor(t / self.window)        # 今の枠の番号
        if w != self.current:                  # 枠が変わったら数を 0 に戻す
            self.current, self.count = w, 0
        if self.count < self.limit:
            self.count += 1
            return True
        return False


class SlidingLog:
    """スライディングログ: 通した時刻をすべて記録し、直近 window 秒の件数で判定する。"""

    def __init__(self, limit, window):
        self.limit, self.window = limit, window
        self.log = deque()

    def allow(self, t):
        while self.log and self.log[0] <= t - self.window:   # 窓から出た記録を捨てる
            self.log.popleft()
        if len(self.log) < self.limit:
            self.log.append(t)
            return True
        return False


class SlidingWindowCounter:
    """スライディング窓カウンタ: 前の枠と今の枠の 2 つの数だけを持ち、
    前の枠の数を「今の窓に重なっている割合」で按分して足す（Cloudflare のブログの式）。"""

    def __init__(self, limit, window):
        self.limit, self.window = limit, window
        self.current, self.cur, self.prev = None, 0, 0

    def estimate(self, t):
        w = math.floor(t / self.window)
        if w != self.current:
            # 1 つ進んだなら今の数が前の数になる。2 つ以上進んだなら前の枠は空
            self.prev = self.cur if self.current is not None and w == self.current + 1 else 0
            self.current, self.cur = w, 0
        elapsed = t - w * self.window
        return self.prev * (self.window - elapsed) / self.window + self.cur

    def allow(self, t):
        if self.estimate(t) + 1 <= self.limit:   # この 1 件を足しても上限以内なら通す
            self.cur += 1
            return True
        return False


class TokenBucket:
    """トークンバケット: 1 秒に rate 個ずつトークンが溜まり（上限 capacity）、
    要求 1 件で 1 個使う。最初は満杯。"""

    def __init__(self, rate, capacity):
        self.rate, self.capacity = rate, capacity
        self.tokens, self.last = float(capacity), None

    def allow(self, t):
        if self.last is not None:
            self.tokens = min(self.capacity, self.tokens + (t - self.last) * self.rate)
        self.last = t
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class GCRA:
    """GCRA（Generic Cell Rate Algorithm）の仮想スケジューリング版。
    TAT（理論上の到着時刻）だけを持つ。increment = 1 / rate、limit は早着を許す幅。
    ATM Forum TM 4.1 の Figure 4-1 の左の流れ図を、そのまま書いたもの。"""

    def __init__(self, increment, limit):
        self.i, self.l = increment, limit
        self.tat = None

    def allow(self, t):
        if self.tat is None or self.tat < t:
            self.tat = t                        # 遅れて来たなら、今を基準にする
        if self.tat > t + self.l:
            return False                        # 早すぎる。TAT は変えない
        self.tat += self.i
        return True


class LeakyBucketQueue:
    """リーキーバケット（待ち行列として使う形）: 要求を容量 size の行列に入れ、
    1 秒に rate 件の一定の速さで取り出して処理する。満杯なら断る。
    allow は通したかどうかに加えて、処理される時刻を返す。"""

    def __init__(self, rate, size):
        self.interval, self.size = 1.0 / rate, size
        self.queue = deque()                    # 処理される予定の時刻
        self.next_free = 0.0

    def allow(self, t):
        while self.queue and self.queue[0] <= t:   # 処理し終えたものを行列から出す
            self.queue.popleft()
        if len(self.queue) >= self.size:
            return False, None
        start = max(t, self.next_free)
        self.next_free = start + self.interval
        self.queue.append(start)
        return True, start
