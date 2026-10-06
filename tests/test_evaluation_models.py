import pytest

from evren_mcp.errors import EvrenError
from evren_mcp.evaluation import evaluate
from evren_mcp.quotes import QuoteBook
from tests.fakes import envelope

MODEL = "00000000-0000-4000-8000-000000000004"
DS = "00000000-0000-4000-8000-000000000006"
VER = "00000000-0000-4000-8000-000000000002"


def test_evaluate_extracts_metrics_and_warns_on_test(fake, platform, fast_settings):
    fake.on("GET", "/billing/ledger", (200, {"items": []}))
    fake.on("POST", "/inference/evaluate", (200, envelope({"metrics": {"mAP50": 0.9899, "precision": 0.9},
                                                           "per_class": [{"name": "arac", "mAP50": 0.99}]})))
    out = evaluate(platform, QuoteBook(), fast_settings, model_version_id=MODEL, dataset_id=DS,
                   dataset_version_id=VER, split="test", image_size=1280)
    assert out["metrikler"]["metrics.mAP50"] == 0.9899
    assert "tek seferlik" in out["uyari"]
    sent = fake.calls("POST", "/inference/evaluate")[0]
    assert b'"image_size":1280' in sent.content.replace(b" ", b"")


def test_evaluate_rejects_bad_split(platform, fast_settings):
    with pytest.raises(EvrenError, match="bölme"):
        evaluate(platform, QuoteBook(), fast_settings, model_version_id=MODEL, dataset_id=DS,
                 dataset_version_id=VER, split="dogrulama")
