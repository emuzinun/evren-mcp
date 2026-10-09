"""Kredi, bugünkü harcama, puan ve sıralama."""

from __future__ import annotations

from datetime import UTC, datetime

from .errors import EvrenError
from .platform import Platform, as_list, parse_ts

MAX_LEDGER_PAGES = 80
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
        "son_hareketler": [
            {
                "zaman": x.get("created_at"),
                "tur": x.get("tx_type"),
                "tutar_cr": float(x.get("amount") or 0),
                "aciklama": x.get("description"),
            }
            for x in items
        ],
    }


def _page_items(page: object, offset: int) -> list[dict]:
    """Defter sayfası `{items: [...]}` olmalı. Bozuk ya da eksik sayfa 'harcama yok'
    sayılmaz: platform `?limit=N`'e `{}` döndürmüştü [yazarın ölçümleri]."""
    if isinstance(page, list):
        return page
    if isinstance(page, dict) and isinstance(page.get("items"), list):
        items = page["items"]
        total = page.get("total")
        if not items and isinstance(total, int) and offset < total:
            raise EvrenError(
                f"Kredi defteri eksik döndü ({offset}/{total}); güvenlik için kredi harcayan işlem yapılmadı."
            )
        return items
    raise EvrenError("Kredi defteri beklenmeyen biçimde döndü; güvenlik için kredi harcayan işlem yapılmadı.")


def _new_rows_today(p: Platform, start: datetime) -> list[dict]:
    """Önbellekteki en yeni satıra ya da dünün ilk satırına kadar yeni satırları okur."""
    cache = p.ledger_cache
    if cache.get("day") != start.date():
        cache.clear()
        cache.update(day=start.date(), rows=[], newest=None)
    rows: list[dict] = []
    offset = 0
    for _ in range(MAX_LEDGER_PAGES):
        items = _page_items(p.get("/billing/ledger", params={"offset": offset}), offset)
        if not items:
            return rows
        for x in items:
            if cache["newest"] is not None and x.get("id") == cache["newest"]:
                return rows
            try:
                created = parse_ts(str(x.get("created_at")))
            except ValueError:
                raise EvrenError(
                    "Kredi defterinde tarihi okunamayan satır var; güvenlik için kredi "
                    "harcayan işlem yapılmadı."
                ) from None
            if created < start:
                return rows
            rows.append(x)
        offset += len(items)
    raise EvrenError(
        f"Bugünün kredi defteri {MAX_LEDGER_PAGES * 50}+ satır (çoğu LLM çağrısı); "
        "harcama hesaplanamadı. Güvenlik için kredi harcayan işlem yapılmadı."
    )


def today_spend(p: Platform, now: datetime | None = None) -> float:
    """Bugün (UTC) harcanan kredi.

    Yalnız bugünün borç satırları (eksi tutar) toplanır; artı tutar ancak
    bugünkü bir borçla aynı `reference_id`'yi taşıyorsa (iş iadesi, kesin
    tutar) düşülür. Önceki günlere ait iadeler bugünkü harcamayı silmez —
    06.10 00:04'te eski işler için 1,60 CR `SYSTEM_GRANT` geldi [ölçüldü].
    Şüphede fazla sayılır (güvenli yön).

    Defter yeniden eskiye sıralı [ölçüldü 05.10.2026]; LLM kullanan bir
    hesapta günde ~1.300 satır görüldü. Gün içinde okunan satırlar önbellekte tutulur,
    sonraki çağrı yalnız yeni satırları okur.
    """
    now = now or datetime.now(UTC)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    new = _new_rows_today(p, start)
    cache = p.ledger_cache
    if new:
        cache["rows"] = new + cache["rows"]
        cache["newest"] = new[0].get("id")
    debits = {
        str(x.get("reference_id"))
        for x in cache["rows"]
        if float(x.get("amount") or 0) < 0 and x.get("reference_id")
    }
    total = 0.0
    for x in cache["rows"]:
        amount = float(x.get("amount") or 0)
        if amount < 0 or (x.get("tx_type") != "REWARD" and str(x.get("reference_id")) in debits):
            total -= amount
    return max(0.0, total)


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
    out["not"] = (
        "Sıralama dönem puanını kullanıyor; dönem puanın API'de yok, fark profil "
        "puanından hesaplanır ve en az bu kadardır. fark=null: listede değilsin, "
        "kalan fark bilinmiyor [ölçüldü 06.10.2026]."
    )
    return out
