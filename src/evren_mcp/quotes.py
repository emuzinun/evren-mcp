"""Teklif defteri: kredi harcayan eğitim yalnız geçerli bir teklifle başlar.

Teklif bellekte durur (sunucu yeniden başlarsa düşer — bilerek: eski fiyatla
iş başlamasın). Gövde kopyalanır ve parmak iziyle mühürlenir.
"""

from __future__ import annotations

import copy
import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from typing import Callable

from .errors import EvrenError


def fingerprint(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


@dataclass(frozen=True)
class Quote:
    id: str
    project_id: str
    body: dict
    fingerprint: str
    estimated_cr: float
    worst_cr: float | None
    expires_at: float


class QuoteBook:
    def __init__(self, ttl_s: float = 600.0, clock: Callable[[], float] = time.time) -> None:
        self.ttl_s = ttl_s
        self._clock = clock
        self._quotes: dict[str, Quote] = {}

    def _purge(self) -> None:
        now = self._clock()
        for k in [k for k, q in self._quotes.items() if q.expires_at <= now]:
            del self._quotes[k]

    def add(self, project_id: str, body: dict, estimated_cr: float,
            worst_cr: float | None = None) -> Quote:
        self._purge()
        frozen = copy.deepcopy(body)
        q = Quote(id=f"T-{secrets.token_hex(3).upper()}", project_id=project_id, body=frozen,
                  fingerprint=fingerprint(frozen), estimated_cr=estimated_cr, worst_cr=worst_cr,
                  expires_at=self._clock() + self.ttl_s)
        self._quotes[q.id] = q
        return q

    def take(self, quote_id: str) -> Quote:
        q = self._quotes.pop((quote_id or "").strip(), None)
        if q is None:
            raise EvrenError(f"Teklif bulunamadı: '{quote_id}'. Teklifler tek kullanımlık ve "
                             "sunucu yeniden başlayınca düşer; estimate_training ile yeni teklif al.")
        if q.expires_at <= self._clock():
            raise EvrenError(f"Teklifin süresi geçti ({int(self.ttl_s // 60)} dk). "
                             "Fiyat değişmiş olabilir; estimate_training ile yeni teklif al.")
        if fingerprint(q.body) != q.fingerprint:
            raise EvrenError("Teklif bozulmuş; güvenlik için kullanılmadı. Yeni teklif al.")
        return q

    def pending_total(self) -> float:
        self._purge()
        return sum(q.estimated_cr for q in self._quotes.values())
