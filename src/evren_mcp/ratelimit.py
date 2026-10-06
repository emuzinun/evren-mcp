"""İki katmanlı istek sınırlayıcı: dakikalık pencere + patlama yumuşatma.

Yalnız kayan pencere yetmiyor: platformun kısa pencereli bir patlama limiti
var ve art arda isteklere 429 dönüyor [ölçüldü 19.09.2026].
"""

from __future__ import annotations

import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self, rpm: int, min_aralik: float | None = None, burst: int = 4) -> None:
        self.rpm = rpm
        self.min_aralik = min_aralik if min_aralik is not None else 60.0 / max(rpm, 1)
        self.burst = burst
        self._hits: deque[float] = deque()
        self._son = 0.0
        self._jeton = float(burst)
        self._lock = threading.Lock()

    def acquire(self) -> float:
        waited = 0.0
        while True:
            with self._lock:
                now = time.monotonic()
                while self._hits and now - self._hits[0] >= 60.0:
                    self._hits.popleft()
                if self._son:
                    self._jeton = min(self.burst, self._jeton + (now - self._son) / self.min_aralik)
                if len(self._hits) >= self.rpm:
                    sleep_for = 60.0 - (now - self._hits[0]) + 0.01
                elif self._jeton < 1.0:
                    sleep_for = (1.0 - self._jeton) * self.min_aralik
                else:
                    self._hits.append(now)
                    self._jeton -= 1.0
                    self._son = now
                    return waited
            time.sleep(sleep_for)
            waited += sleep_for
