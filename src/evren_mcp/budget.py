"""Harcama tavanları. Bugünkü harcama platform defterinden gelir (account.today_spend)."""

from __future__ import annotations

from .errors import EvrenError


def check(amount: float, *, max_job: float, max_daily: float,
          spent_today: float, pending: float) -> None:
    if amount > max_job:
        raise EvrenError(f"Bu iş {amount:.2f} CR; tek iş tavanı {max_job:.2f} CR. "
                         "Gerekirse EVREN_MAX_JOB_CR ayarını yükselt.")
    total = spent_today + pending + amount
    if total > max_daily + 1e-9:
        raise EvrenError(
            f"Günlük tavan aşılır: bugün {spent_today:.2f} CR harcandı, bekleyen teklifler "
            f"{pending:.2f} CR, bu iş {amount:.2f} CR; tavan {max_daily:.2f} CR (UTC günü, "
            "TR saatiyle 03:00'te sıfırlanır).")
