from datetime import datetime, timezone

import pytest

from evren_mcp.errors import EvrenError
from evren_mcp.quotes import QuoteBook
from evren_mcp.training import build_body, estimate
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


@pytest.mark.parametrize("over", [{"epochs": 0}, {"epochs": 5000}, {"architecture": "yolo v8; rm"},
                                  {"dataset_version_id": "visdrone"}, {"batch": 0}, {"imgsz": 10}])
def test_body_validation(over):
    with pytest.raises(EvrenError):
        build_body(**kw(**over))


def ledger_empty(fake):
    fake.on("GET", "/billing/ledger", (200, {"items": []}))
    fake.on("GET", "/projects", (200, envelope([{"id": PROJ}])))


def test_estimate_creates_quote(fake, platform, fast_settings):
    ledger_empty(fake)
    fake.on("POST", "/training/jobs/dry-run", (200, envelope({
        "valid": True, "estimated_cr": 0.54, "p95_worst_cr": 1.86, "wall_hours": 0.1,
        "applied_hyperparams": {"epochs": 5}, "warnings": []})))
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
