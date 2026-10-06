import pytest

from evren_mcp import budget
from evren_mcp.errors import EvrenError
from evren_mcp.journal import Journal
from evren_mcp.quotes import QuoteBook, fingerprint

BODY = {"architecture": "yolov8n", "hyperparams": {"epochs": 5}}


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_fingerprint_ignores_key_order():
    assert fingerprint({"a": 1, "b": 2}) == fingerprint({"b": 2, "a": 1})


def test_quote_single_use():
    qb = QuoteBook()
    q = qb.add("p1", BODY, 0.54)
    assert q.id.startswith("T-") and qb.take(q.id).estimated_cr == 0.54
    with pytest.raises(EvrenError, match="bulunamadı"):
        qb.take(q.id)


def test_quote_expires():
    clock = Clock()
    qb = QuoteBook(ttl_s=600, clock=clock)
    q = qb.add("p1", BODY, 0.54)
    clock.t += 601
    with pytest.raises(EvrenError, match="süresi"):
        qb.take(q.id)


def test_quote_body_cannot_be_mutated_after_add():
    qb = QuoteBook()
    body = {"architecture": "yolov8n", "hyperparams": {"epochs": 5}}
    q = qb.add("p1", body, 0.54)
    body["hyperparams"]["epochs"] = 500
    assert qb.take(q.id).body["hyperparams"]["epochs"] == 5


def test_pending_total_skips_expired():
    clock = Clock()
    qb = QuoteBook(ttl_s=600, clock=clock)
    qb.add("p1", BODY, 1.0)
    clock.t += 700
    qb.add("p1", BODY, 2.0)
    assert qb.pending_total() == 2.0


def test_budget_job_cap():
    with pytest.raises(EvrenError, match="tek iş tavanı"):
        budget.check(6.0, max_job=5, max_daily=20, spent_today=0, pending=0)


def test_budget_daily_cap_counts_pending():
    with pytest.raises(EvrenError, match="Günlük tavan"):
        budget.check(3.0, max_job=5, max_daily=20, spent_today=18, pending=0)
    with pytest.raises(EvrenError, match="Günlük tavan"):
        budget.check(1.0, max_job=5, max_daily=20, spent_today=10, pending=9.5)
    budget.check(1.0, max_job=5, max_daily=20, spent_today=10, pending=9.0)


def test_journal_append_read_find(tmp_path):
    j = Journal(tmp_path / "alt" / "g.jsonl")
    j.append("egitim_basladi", is_id="J1", tahmini_cr=0.54)
    j.append("egitim_bitti", is_id="J1", puan_farki=30)
    with (tmp_path / "alt" / "g.jsonl").open("a", encoding="utf-8") as f:
        f.write("bozuk satır\n")
    assert [r["olay"] for r in j.read()] == ["egitim_basladi", "egitim_bitti"]
    assert j.find("egitim_basladi", "J1")["tahmini_cr"] == 0.54
    assert j.find("egitim_basladi", "J2") is None
