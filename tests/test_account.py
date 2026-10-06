from datetime import datetime, timedelta, timezone

import pytest

from evren_mcp.account import get_credits, get_standing, today_spend
from evren_mcp.errors import EvrenError
from tests.fakes import envelope

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)


def tx(hours_ago: float, kind: str, amount: str) -> dict:
    return {"created_at": (NOW - timedelta(hours=hours_ago)).isoformat(), "tx_type": kind,
            "amount": amount, "description": kind}


def test_credits(fake, platform):
    fake.on("GET", "/organizations", (200, {"items": [{"credit_balance": "1234.5", "plan_type": "free"}]}))
    fake.on("GET", "/billing/ledger", (200, {"items": [tx(1, "HOLD", "-0.54")]}))
    c = get_credits(platform)
    assert c["bakiye_cr"] == 1234.5 and c["son_hareketler"][0]["tutar_cr"] == -0.54


def test_today_spend_nets_refunds_and_ignores_rewards(fake, platform):
    fake.on("GET", "/billing/ledger",
            (200, {"items": [tx(1, "RELEASE", "0.54"), tx(2, "HOLD", "-0.54"),
                             tx(3, "SETTLE", "6.68"), tx(4, "HOLD", "-16.65"),
                             tx(5, "REWARD", "10.0"), tx(30, "HOLD", "-99")]}))
    assert today_spend(platform, now=NOW) == pytest.approx(9.97)


def test_today_spend_pages_until_yesterday(fake, platform):
    sayfa1 = [tx(0.01 * i, "SETTLE", "0.0000") for i in range(50)]
    sayfa2 = [tx(2, "HOLD", "-3.0")] + [tx(1 + 0.01 * i, "SETTLE", "0") for i in range(49)]
    sayfa3 = [tx(11, "HOLD", "-1.0"), tx(13, "HOLD", "-50")]  # 01:00 bugün, 23:00 dün
    fake.on("GET", "/billing/ledger", (200, {"items": sayfa1}), (200, {"items": sayfa2}), (200, {"items": sayfa3}))
    assert today_spend(platform, now=NOW) == pytest.approx(4.0)
    offsets = [r.url.params.get("offset") for r in fake.calls("GET", "/billing/ledger")]
    assert offsets == ["0", "50", "100"]


def test_today_spend_fails_closed(fake, platform):
    fake.on("GET", "/billing/ledger", (200, {"items": [tx(0.001, "SETTLE", "0")] * 50}))
    with pytest.raises(EvrenError, match="hesaplanamadı"):
        today_spend(platform, now=NOW)


def test_standing_gap(fake, platform):
    fake.on("GET", "/auth/me", (200, envelope({"tier_points": 1263, "tier": "CONTRIBUTOR", "username": "biz"})))
    users = [{"username": f"u{i}", "score": 3000 - i * 100} for i in range(9)] + [{"username": "u9", "score": 1540}]
    fake.on("GET", "/universe/leaderboard", (200, envelope({"top_users": users})))
    s = get_standing(platform)
    assert s["puan"] == 1263
    assert s["donemler"]["aylik"] == {"ilk10_siniri": 1540, "ilk10_icinde": False, "fark": 277}
