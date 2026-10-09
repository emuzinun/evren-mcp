from datetime import UTC, datetime

import httpx
import pytest

from evren_mcp.errors import EvrenError
from evren_mcp.journal import Journal
from evren_mcp.quotes import QuoteBook
from evren_mcp.training import build_body, estimate, list_jobs, start, status, stop
from tests.fakes import envelope

VER = "00000000-0000-4000-8000-000000000002"
BASE = "00000000-0000-4000-8000-000000000007"
PROJ = "00000000-0000-4000-8000-000000000003"


def kw(**over):
    d = dict(dataset_version_id=VER, architecture="yolov8n", epochs=5, batch=16, imgsz=640)
    d.update(over)
    return d


def test_body_pins_version_and_puts_epochs_in_hyperparams():
    b = build_body(**kw(base_model_version_id=BASE))
    assert b["dataset_version_id"] == VER and "dataset_id" not in b
    assert b["hyperparams"] == {"epochs": 5, "batch": 16, "imgsz": 640}
    assert "epochs" not in b  # üst düzey epochs sessizce yok sayılıyor [ölçüldü 21.09]
    assert b["base_model_version_id"] == BASE


@pytest.mark.parametrize(
    "over",
    [
        {"epochs": 0},
        {"epochs": 5000},
        {"architecture": "yolo v8; rm"},
        {"dataset_version_id": "visdrone"},
        {"batch": 0},
        {"imgsz": 10},
    ],
)
def test_body_validation(over):
    with pytest.raises(EvrenError):
        build_body(**kw(**over))


def ledger_empty(fake):
    fake.on("GET", "/billing/ledger", (200, {"items": []}))
    fake.on("GET", "/projects", (200, envelope([{"id": PROJ}])))


def test_estimate_creates_quote(fake, platform, fast_settings):
    ledger_empty(fake)
    fake.on(
        "POST",
        "/training/jobs/dry-run",
        (
            200,
            envelope(
                {
                    "valid": True,
                    "estimated_cr": 0.54,
                    "p95_worst_cr": 1.86,
                    "wall_hours": 0.1,
                    "applied_hyperparams": {"epochs": 5},
                    "warnings": [],
                }
            ),
        ),
    )
    qb = QuoteBook()
    out = estimate(platform, qb, fast_settings, **kw())
    assert out["teklif"].startswith("T-") and out["tahmini_cr"] == 0.54 and out["en_kotu_cr"] == 1.86
    assert qb.pending_total() == 0.54
    assert fake.calls("POST", "/training/jobs/dry-run")[0].url.params["project_id"] == PROJ


def test_estimate_invalid_settings_explained(fake, platform, fast_settings):
    ledger_empty(fake)
    fake.on("POST", "/training/jobs/dry-run", (200, envelope({"valid": False, "errors": ["mimari yok"]})))
    with pytest.raises(EvrenError, match="mimari yok"):
        estimate(platform, QuoteBook(), fast_settings, **kw())


def test_estimate_over_job_cap_gives_no_quote(fake, platform, fast_settings):
    ledger_empty(fake)
    fake.on("POST", "/training/jobs/dry-run", (200, envelope({"valid": True, "estimated_cr": 17.3})))
    qb = QuoteBook()
    with pytest.raises(EvrenError, match="tek iş tavanı"):
        estimate(platform, qb, fast_settings, **kw())
    assert qb.pending_total() == 0


JOB = "00000000-0000-4000-8000-000000000001"


def quote_for(qb, est=0.54):
    return qb.add(PROJ, build_body(**kw()), est)


def me(points):
    return (200, envelope({"tier_points": points, "username": "biz"}))


def test_start_happy_path_journals(fake, platform, fast_settings):
    fake.on("GET", "/billing/ledger", (200, {"items": []}))
    fake.on("GET", "/auth/me", me(1263))
    fake.on("POST", "/training/jobs", (201, envelope({"id": JOB, "status": "EXPORTING"})))
    qb, j = QuoteBook(), Journal(fast_settings.journal_path)
    out = start(platform, qb, fast_settings, j, quote_for(qb).id)
    assert out["is_id"] == JOB
    rec = j.find("egitim_basladi", JOB)
    assert rec["puan_once"] == 1263 and rec["tahmini_cr"] == 0.54
    assert fake.calls("POST", "/training/jobs")[0].url.params["project_id"] == PROJ


def test_start_rechecks_budget_at_start(fake, platform, fast_settings):
    fake.on(
        "GET",
        "/billing/ledger",
        (
            200,
            {"items": [{"created_at": datetime.now(UTC).isoformat(), "tx_type": "HOLD", "amount": "-19.9"}]},
        ),
        (200, {"items": []}),
    )
    qb = QuoteBook()
    with pytest.raises(EvrenError, match="Günlük tavan"):
        start(platform, qb, fast_settings, Journal(fast_settings.journal_path), quote_for(qb).id)
    assert fake.calls("POST", "/training/jobs") == []


def test_start_ambiguous_finds_created_job_without_resending(fake, platform, fast_settings):
    fake.on("GET", "/billing/ledger", (200, {"items": []}))
    fake.on("GET", "/auth/me", me(1263))
    fake.on("POST", "/training/jobs", (500, {"success": False}))
    fake.on(
        "GET",
        "/training/jobs",
        (
            200,
            {
                "items": [
                    {
                        "id": JOB,
                        "status": "EXPORTING",
                        "architecture": "yolov8n",
                        "dataset_version_id": VER,
                        "created_at": datetime.now(UTC).isoformat(),
                    }
                ]
            },
        ),
    )
    qb = QuoteBook()
    out = start(platform, qb, fast_settings, Journal(fast_settings.journal_path), quote_for(qb).id)
    assert out["is_id"] == JOB
    assert len(fake.calls("POST", "/training/jobs")) == 1


def test_start_ambiguous_non_json_checks_list(fake, platform, fast_settings):
    fake.on("GET", "/billing/ledger", (200, {"items": []}))
    fake.on("GET", "/auth/me", me(1263))
    fake.on("POST", "/training/jobs", lambda r: httpx.Response(502, text="<html>Bad Gateway</html>"))
    fake.on("GET", "/training/jobs", (200, {"items": []}))
    qb = QuoteBook()
    with pytest.raises(EvrenError, match="tekrar gönderilmedi"):
        start(platform, qb, fast_settings, Journal(fast_settings.journal_path), quote_for(qb).id)
    assert len(fake.calls("POST", "/training/jobs")) == 1


def test_status_explains_and_journals_finish_once(fake, platform, fast_settings):
    j = Journal(fast_settings.journal_path)
    j.append("egitim_basladi", is_id=JOB, puan_once=1263)
    fake.on(
        "GET",
        f"/training/jobs/{JOB}",
        (
            200,
            envelope(
                {
                    "id": JOB,
                    "status": "COMPLETED",
                    "actual_cr": "0.50",
                    "final_metrics": {"mAP50": 0.41},
                    "model_version_id": "00000000-0000-4000-8000-000000000004",
                }
            ),
        ),
    )
    fake.on("GET", "/auth/me", me(1293))
    out = status(platform, j, JOB)
    assert out["durum_tr"] == "tamamlandı" and out["puan_farki"] == 30
    status(platform, j, JOB)
    assert len([r for r in j.read() if r["olay"] == "egitim_bitti"]) == 1


def test_status_disk_failure_explained(fake, platform, fast_settings):
    fake.on(
        "GET",
        f"/training/jobs/{JOB}",
        (
            200,
            envelope(
                {
                    "id": JOB,
                    "status": "FAILED",
                    "error_category": "INFRA",
                    "error_message": "[Errno 28] No space left on device",
                }
            ),
        ),
    )
    out = status(platform, Journal(fast_settings.journal_path), JOB)
    assert "disk" in out["aciklama"].lower()


def test_stop_refuses_finished_job(fake, platform):
    fake.on("GET", f"/training/jobs/{JOB}", (200, envelope({"id": JOB, "status": "COMPLETED"})))
    with pytest.raises(EvrenError, match="zaten"):
        stop(platform, JOB)
    assert fake.calls("POST", f"/training/jobs/{JOB}/stop") == []


def test_stop_running_job(fake, platform):
    fake.on("GET", f"/training/jobs/{JOB}", (200, envelope({"id": JOB, "status": "TRAINING"})))
    fake.on("POST", f"/training/jobs/{JOB}/stop", (200, envelope({"status": "CANCELLED"})))
    assert stop(platform, JOB)["is_id"] == JOB


def test_list_jobs(fake, platform):
    fake.on(
        "GET",
        "/training/jobs",
        (
            200,
            {
                "items": [
                    {
                        "id": JOB,
                        "status": "FAILED",
                        "architecture": "yolov8n",
                        "created_at": "2026-10-05T18:48:42Z",
                    }
                ]
            },
        ),
    )
    assert list_jobs(platform)[0]["durum_tr"] == "başarısız"


def test_start_ambiguous_and_list_unreadable_is_unclear_not_retry(fake, platform, fast_settings):
    """İnceleme (önemli 3): iş listesi de okunamazsa 'tekrar dene' denmemeli; iş oluşmuş olabilir."""
    fake.on("GET", "/billing/ledger", (200, {"items": []}))
    fake.on("GET", "/auth/me", me(1263))
    fake.on("POST", "/training/jobs", (502, "x"))
    fake.on("GET", "/training/jobs", (500, {"success": False}))
    qb, j = QuoteBook(), Journal(fast_settings.journal_path)
    with pytest.raises(EvrenError, match="belirsiz"):
        start(platform, qb, fast_settings, j, quote_for(qb).id)
    assert len(fake.calls("POST", "/training/jobs")) == 1
    assert j.read()[-1]["olay"] == "egitim_belirsiz"


def test_recent_start_counts_until_ledger_catches_up(fake, platform, fast_settings):
    """İnceleme (önemli 4): defter HOLD'u gecikmeli gösterirse ikinci başlatma tavanı delmemeli."""
    import dataclasses

    s = dataclasses.replace(fast_settings, max_daily_cr=1.0)
    fake.on("GET", "/billing/ledger", (200, {"items": []}))
    fake.on("GET", "/auth/me", me(1263))
    fake.on("POST", "/training/jobs", (201, envelope({"id": JOB, "status": "EXPORTING"})))
    qb, j = QuoteBook(), Journal(s.journal_path)
    start(platform, qb, s, j, quote_for(qb, 0.6).id)
    with pytest.raises(EvrenError, match="Günlük tavan"):
        start(platform, qb, s, j, quote_for(qb, 0.6).id)
    assert len(fake.calls("POST", "/training/jobs")) == 1


def test_parallel_starts_cannot_both_pass(fake, platform, fast_settings, monkeypatch):
    """İnceleme (önemli 4): eşzamanlı iki başlatma aynı defter rakamıyla birlikte geçmemeli.

    Bariyer iki iş parçacığını defter okumasında buluşturmaya çalışır: kilit
    yoksa ikisi de teklifini almış, ikisi de 0 harcama görür ve ikisi de geçer.
    Kilit varsa ikincisi bariyere hiç ulaşamaz; bariyer zaman aşımıyla çözülür.
    """
    import contextlib
    import dataclasses
    import threading

    from evren_mcp import training as training_mod

    s = dataclasses.replace(fast_settings, max_daily_cr=1.0)
    fake.on("GET", "/auth/me", me(1263))
    fake.on("POST", "/training/jobs", (201, envelope({"id": JOB, "status": "EXPORTING"})))
    bariyer = threading.Barrier(2)

    def bekleyen_harcama(p, *a, **k):
        with contextlib.suppress(threading.BrokenBarrierError):
            bariyer.wait(timeout=0.5)
        return 0.0

    monkeypatch.setattr(training_mod, "today_spend", bekleyen_harcama)
    qb, j = QuoteBook(), Journal(s.journal_path)
    q1, q2 = quote_for(qb, 0.6), quote_for(qb, 0.6)
    sonuc = []

    def kos(q):
        try:
            start(platform, qb, s, j, q.id)
            sonuc.append("ok")
        except EvrenError:
            sonuc.append("red")

    ts = [threading.Thread(target=kos, args=(q,)) for q in (q1, q2)]
    for t_ in ts:
        t_.start()
    for t_ in ts:
        t_.join()
    assert sorted(sonuc) == ["ok", "red"]
    assert len(fake.calls("POST", "/training/jobs")) == 1


def test_job_cap_uses_worst_case(fake, platform, fast_settings):
    """İnceleme (önemli 6): tahmin 4,0 ama en kötü 12 CR; tek iş tavanını en kötü durum aşıyor."""
    ledger_empty(fake)
    fake.on(
        "POST",
        "/training/jobs/dry-run",
        (200, envelope({"valid": True, "estimated_cr": 4.0, "p95_worst_cr": 12.0})),
    )
    qb = QuoteBook()
    with pytest.raises(EvrenError, match="en kötü"):
        estimate(platform, qb, fast_settings, **kw())
    assert qb.pending_total() == 0


def test_start_ambiguous_skips_job_with_bad_timestamp(fake, platform, fast_settings):
    """Ertelenen bulgu: listedeki bozuk created_at belirsiz yanıt çözümünü düşürmemeli."""
    fake.on("GET", "/billing/ledger", (200, {"items": []}))
    fake.on("GET", "/auth/me", me(1263))
    fake.on("POST", "/training/jobs", (500, {"success": False}))
    fake.on(
        "GET",
        "/training/jobs",
        (
            200,
            {
                "items": [
                    {
                        "id": "eski",
                        "architecture": "yolov8n",
                        "dataset_version_id": VER,
                        "created_at": "bozuk",
                    },
                    {
                        "id": JOB,
                        "status": "EXPORTING",
                        "architecture": "yolov8n",
                        "dataset_version_id": VER,
                        "created_at": datetime.now(UTC).isoformat(),
                    },
                ]
            },
        ),
    )
    qb = QuoteBook()
    out = start(platform, qb, fast_settings, Journal(fast_settings.journal_path), quote_for(qb).id)
    assert out["is_id"] == JOB


def test_start_journal_failure_still_returns_job_id(fake, platform, fast_settings, tmp_path):
    """Ertelenen bulgu: iş başladıktan sonra günlük yazılamazsa iş kimliği kaybolmamalı."""
    fake.on("GET", "/billing/ledger", (200, {"items": []}))
    fake.on("GET", "/auth/me", me(1263))
    fake.on("POST", "/training/jobs", (201, envelope({"id": JOB, "status": "EXPORTING"})))
    engel = tmp_path / "dosya"
    engel.write_text("x", encoding="utf-8")
    qb = QuoteBook()
    out = start(platform, qb, fast_settings, Journal(engel / "journal.jsonl"), quote_for(qb).id)
    assert out["is_id"] == JOB
    assert "günlüğe yazılamadı" in out["uyari"]
