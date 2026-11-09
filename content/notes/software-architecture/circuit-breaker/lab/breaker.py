"""A minimal count-based circuit breaker driven by an explicit clock."""

from collections import deque


class CircuitBreaker:
    def __init__(self, window=20, min_calls=10, failure_rate=0.5,
                 open_seconds=5.0, half_open_calls=3):
        self.window = deque(maxlen=window)  # True = failure, last N results
        self.min_calls = min_calls
        self.failure_rate = failure_rate
        self.open_seconds = open_seconds
        self.half_open_calls = half_open_calls
        self.state, self.generation = "CLOSED", 0
        self.opened_at = 0.0
        self.trials = 0     # calls admitted in HALF_OPEN
        self.successes = 0  # successful trials in HALF_OPEN

    def allow(self, now):
        """Return a generation number if the call may go downstream, else None."""
        if self.state == "OPEN":
            if now - self.opened_at < self.open_seconds:
                return None
            self._move("HALF_OPEN")
            self.trials = self.successes = 0
        if self.state == "HALF_OPEN":
            if self.trials >= self.half_open_calls:
                return None
            self.trials += 1
        return self.generation

    def record(self, now, ok, generation):
        """Report the result of a call that allow() admitted."""
        if generation != self.generation:
            return  # admitted in an earlier state: not counted
        if self.state == "HALF_OPEN":
            self.successes += ok
            if not ok:
                self._move("OPEN", now)
            elif self.successes == self.half_open_calls:
                self._move("CLOSED")
                self.window.clear()
            return
        self.window.append(not ok)
        if len(self.window) >= self.min_calls:
            if sum(self.window) / len(self.window) >= self.failure_rate:
                self._move("OPEN", now)

    def _move(self, state, now=None):
        self.state, self.generation = state, self.generation + 1
        if now is not None:
            self.opened_at = now
