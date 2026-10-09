from datetime import datetime, timedelta, timezone

import pytest

from evren_mcp.account import get_credits, get_standing, today_spend
from evren_mcp.errors import EvrenError
from tests.fakes import envelope

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)


def tx(hours_ago: float, kind: str, amount: str, ref: str | None = None, rid: str | None = None) -> dict:
    return {
        "id": rid,
        "created_at": (NOW - timedelta(hours=hours_ago)).isoformat(),
        "tx_type": kind,
        "amount": amount,
        "description": kind,
        "reference_id": ref,
    }


def test_credits(fake, platform):
    fake.on("GET", "/organizations", (200, {"items": [{"credit_balance": "1234.5", "plan_type": "free"}]}))
    fake.on("GET", "/billing/ledger", (200, {"items": [tx(1, "HOLD", "-0.54")]}))
    c = get_credits(platform)
    assert c["bakiye_cr"] == 1234.5 and c["son_hareketler"][0]["tutar_cr"] == -0.54


def test_today_spend_nets_refunds_and_ignores_rewards(fake, platform):
    fake.on(
        "GET",
        "/billing/ledger",
        (
            200,
            {
                "items": [
                    tx(1, "RELEASE", "0.54", ref="a"),
                    tx(2, "HOLD", "-0.54", ref="a"),
                    tx(3, "SETTLE", "6.68", ref="b"),
                    tx(4, "HOLD", "-16.65", ref="b"),
                    tx(5, "REWARD", "10.0"),
                    tx(30, "HOLD", "-99"),
                ]
            },
        ),
    )
    assert today_spend(platform, now=NOW) == pytest.approx(9.97)


def test_today_spend_pages_until_yesterday(fake, platform):
    sayfa1 = [tx(0.01 * i, "SETTLE", "0.0000") for i in range(50)]
    sayfa2 = [tx(2, "HOLD", "-3.0")] + [tx(1 + 0.01 * i, "SETTLE", "0") for i in range(49)]
    sayfa3 = [tx(11, "HOLD", "-1.0"), tx(13, "HOLD", "-50")]  # 01:00 bugün, 23:00 dün
    fake.on(
        "GET", "/billing/ledger", (200, {"items": sayfa1}), (200, {"items": sayfa2}), (200, {"items": sayfa3})
    )
    assert today_spend(platform, now=NOW) == pytest.approx(4.0)
    offsets = [r.url.params.get("offset") for r in fake.calls("GET", "/billing/ledger")]
    assert offsets == ["0", "50", "100"]


def test_today_spend_fails_closed(fake, platform):
    fake.on("GET", "/billing/ledger", (200, {"items": [tx(0.001, "SETTLE", "0")] * 50}))
    with pytest.raises(EvrenError, match="hesaplanamadı"):
        today_spend(platform, now=NOW)


def test_standing_gap(fake, platform):
    fake.on(
        "GET", "/auth/me", (200, envelope({"tier_points": 1263, "tier": "CONTRIBUTOR", "username": "biz"}))
    )
    users = [{"username": f"u{i}", "score": 3000 - i * 100} for i in range(9)] + [
        {"username": "u9", "score": 1540}
    ]
    fake.on("GET", "/universe/leaderboard", (200, envelope({"top_users": users})))
    s = get_standing(platform)
    assert s["puan"] == 1263
    assert s["donemler"]["aylik"] == {"ilk10_siniri": 1540, "ilk10_icinde": False, "fark": 277}


def test_standing_not_inside_but_points_above_limit_is_unknown(fake, platform):
    """Canlıda görüldü (06.10): haftalık sınır 1.096, profil puanı 1.263, listede yokuz.

    Sıralama dönem puanını kullanıyor; dönem puanımızı API vermiyor. "fark 0"
    listeye girmişiz gibi okunur — fark bilinmiyor olarak dönmeli.
    """
    fake.on("GET", "/auth/me", (200, envelope({"tier_points": 1263, "username": "biz"})))
    users = [{"username": f"u{i}", "score": 3000 - i * 100} for i in range(9)] + [
        {"username": "u9", "score": 1096}
    ]
    fake.on("GET", "/universe/leaderboard", (200, envelope({"top_users": users})))
    d = get_standing(platform)["donemler"]["haftalik"]
    assert d["ilk10_icinde"] is False and d["fark"] is None


def test_today_spend_ignores_refunds_for_earlier_days(fake, platform):
    """İnceleme (kritik 1): dünkü işin bugün gelen iadesi bugünkü harcamayı silmemeli.

    06.10 00:04'te eski işler için 1,60 CR SYSTEM_GRANT geldi [ölçüldü].
    """
    fake.on(
        "GET",
        "/billing/ledger",
        (
            200,
            {
                "items": [
                    tx(1, "SYSTEM_GRANT", "1.60", ref="eski-is"),
                    tx(2, "SETTLE", "3.0", ref="dunku-is"),
                    tx(3, "HOLD", "-4.0", ref="bugunku-is"),
                    tx(30, "HOLD", "-9", ref="dunku-is"),
                ]
            },
        ),
    )
    assert today_spend(platform, now=NOW) == pytest.approx(4.0)


@pytest.mark.parametrize("body", [{}, {"data": "x"}, {"items": "bozuk"}, {"items": [], "total": 120}])
def test_today_spend_rejects_malformed_or_truncated_page(fake, platform, body):
    """İnceleme (kritik 2): bozuk ya da eksik sayfa 'harcama yok' sayılmamalı."""
    fake.on("GET", "/billing/ledger", (200, body))
    with pytest.raises(EvrenError, match="defter"):
        today_spend(platform, now=NOW)


def test_today_spend_caches_and_reads_only_new_rows(fake, platform):
    """İnceleme (önemli 5): günde ~1.300 satır; her kontrol bütün günü baştan okumamalı."""
    fake.on(
        "GET",
        "/billing/ledger",
        (200, {"items": [tx(1, "HOLD", "-1", ref="x", rid="r2"), tx(2, "HOLD", "-2", ref="y", rid="r1")]}),
        (200, {"items": []}),
        (
            200,
            {"items": [tx(0.5, "HOLD", "-0.5", ref="z", rid="r3"), tx(1, "HOLD", "-1", ref="x", rid="r2")]},
        ),
    )
    assert today_spend(platform, now=NOW) == pytest.approx(3.0)
    assert today_spend(platform, now=NOW) == pytest.approx(3.5)
    assert len(fake.calls("GET", "/billing/ledger")) == 3
