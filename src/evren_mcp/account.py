"""Kredi, bugünkü harcama, puan ve sıralama."""

from __future__ import annotations

from datetime import datetime, timezone

from .errors import EvrenError
from .platform import Platform, as_list, parse_ts

MAX_LEDGER_PAGES = 40
_PERIODS = (("month", "aylik"), ("week", "haftalik"), ("all", "tum_zamanlar"))


def get_credits(p: Platform, limit: int = 10) -> dict:
    orgs = as_list(p.get("/organizations"))
    if not orgs:
        raise EvrenError("Organizasyon bulunamadı; kredi okunamadı.")
    org = orgs[0]
    items = as_list(p.get("/billing/ledger"))[:limit]
    return {
        "bakiye_cr": float(org.get("credit_balance") or 0),
        "plan": org.get("plan_type"),
        "son_hareketler": [{"zaman": x.get("created_at"), "tur": x.get("tx_type"),
                            "tutar_cr": float(x.get("amount") or 0),
                            "aciklama": x.get("description")} for x in items],
    }


def today_spend(p: Platform, now: datetime | None = None) -> float:
    """Bugün (UTC) harcanan net kredi: ödüller hariç bütün hareketlerin eksi toplamı.

    Defter yeniden eskiye sıralı [ölçüldü 05.10.2026]. Başka bir anahtarın
    günde yüzlerce 0 CR'lik LLM satırı bugünü birkaç sayfaya yayabiliyor;
    dünün ilk satırına kadar okunur. Okunamazsa güvenli tarafta kalınır.
    """
    now = now or datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    total, offset = 0.0, 0
    for _ in range(MAX_LEDGER_PAGES):
        items = as_list(p.get("/billing/ledger", params={"offset": offset}))
        if not items:
            return max(0.0, -total)
        for x in items:
            if parse_ts(str(x.get("created_at"))) < start:
                return max(0.0, -total)
            if x.get("tx_type") != "REWARD":
                total += float(x.get("amount") or 0)
        offset += len(items)
    raise EvrenError("Bugünkü harcama hesaplanamadı (defter çok uzun). "
                     "Güvenlik için kredi harcayan işlem yapılmadı.")


def get_points(p: Platform) -> int | None:
    return p.get("/auth/me").get("tier_points")


def get_standing(p: Platform) -> dict:
    me = p.get("/auth/me")
    points = me.get("tier_points") or 0
    out: dict = {"puan": points, "seviye": me.get("tier"), "donemler": {}}
    for period, label in _PERIODS:
        board = p.get("/universe/leaderboard", params={"period": period})
        users = board.get("top_users", []) if isinstance(board, dict) else []
        scores = [u["score"] for u in users if isinstance(u.get("score"), (int, float))]
        inside = any(u.get("username") == me.get("username") for u in users)
        limit = min(scores) if len(scores) >= 10 else None
        if inside:
            gap = 0
        elif limit is None or points >= limit:
            # Listede değiliz ama profil puanı sınırın üstünde: dönem puanımız
            # daha düşük, değerini API vermiyor [ölçüldü 06.10.2026, haftalık].
            gap = None
        else:
            gap = limit - points
        out["donemler"][label] = {"ilk10_siniri": limit, "ilk10_icinde": inside, "fark": gap}
    out["not"] = ("Sıralama dönem puanını kullanıyor; dönem puanın API'de yok, fark profil "
                  "puanından hesaplanır ve en az bu kadardır. fark=null: listede değilsin, "
                  "kalan fark bilinmiyor [ölçüldü 06.10.2026].")
    return out
