"""Harcama tavanları. Bugünkü harcama platform defterinden gelir (account.today_spend)."""

from __future__ import annotations

from .errors import EvrenError


def check(
    amount: float,
    *,
    max_job: float,
    max_daily: float,
    spent_today: float,
    pending: float,
    worst: float | None = None,
) -> None:
    """Tek iş tavanı en kötü duruma (`p95_worst_cr`) göre, günlük tavan tahmine göre.

    Platform tahmini (HOLD) ayırıyor; gerçek tutar tahmini aşabilir — 0,54
    tahminli işin en kötüsü 1,86 CR [ölçüldü 05.10.2026].
    """
    if worst is not None and worst > max_job:
        raise EvrenError(
            f"Bu işin en kötü durum tutarı {worst:.2f} CR (tahmin {amount:.2f}); "
            f"tek iş tavanı {max_job:.2f} CR. Gerekirse EVREN_MAX_JOB_CR ayarını yükselt."
        )
    if amount > max_job:
        raise EvrenError(
            f"Bu iş {amount:.2f} CR; tek iş tavanı {max_job:.2f} CR. "
            "Gerekirse EVREN_MAX_JOB_CR ayarını yükselt."
        )
    total = spent_today + pending + amount
    if total > max_daily + 1e-9:
        raise EvrenError(
            f"Günlük tavan aşılır: bugün {spent_today:.2f} CR harcandı, bekleyen teklifler "
            f"{pending:.2f} CR, bu iş {amount:.2f} CR; tavan {max_daily:.2f} CR (UTC günü, "
            "TR saatiyle 03:00'te sıfırlanır)."
        )
