"""Token-bucket rate limiter shared across connectors."""
from __future__ import annotations

import threading
import time


class RateLimiter:
    """At most `per_sec` calls per second. Thread-safe."""

    def __init__(self, per_sec: float):
        self.min_interval = 1.0 / per_sec if per_sec > 0 else 0.0
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self.min_interval - (now - self._last)
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()
