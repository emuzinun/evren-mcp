from pathlib import Path

import httpx
import pytest

from evren_mcp.errors import EvrenError
from evren_mcp.evaluation import evaluate
from evren_mcp.models import download_model
from evren_mcp.quotes import QuoteBook
from tests.fakes import envelope

MODEL = "00000000-0000-4000-8000-000000000004"
DS = "00000000-0000-4000-8000-000000000006"
VER = "00000000-0000-4000-8000-000000000002"


def test_evaluate_extracts_metrics_and_warns_on_test(fake, platform, fast_settings):
    fake.on("GET", "/billing/ledger", (200, {"items": []}))
    fake.on(
        "POST",
        "/inference/evaluate",
        (
            200,
            envelope(
                {
                    "metrics": {"mAP50": 0.9899, "precision": 0.9},
                    "per_class": [{"name": "arac", "mAP50": 0.99}],
                }
            ),
        ),
    )
    out = evaluate(
        platform,
        QuoteBook(),
        fast_settings,
        model_version_id=MODEL,
        dataset_id=DS,
        dataset_version_id=VER,
        split="test",
        image_size=1280,
    )
    assert out["metrikler"]["metrics.mAP50"] == 0.9899
    assert "tek seferlik" in out["uyari"]
    sent = fake.calls("POST", "/inference/evaluate")[0]
    assert b'"image_size":1280' in sent.content.replace(b" ", b"")


def test_evaluate_rejects_bad_split(platform, fast_settings):
    with pytest.raises(EvrenError, match="bölme"):
        evaluate(
            platform,
            QuoteBook(),
            fast_settings,
            model_version_id=MODEL,
            dataset_id=DS,
            dataset_version_id=VER,
            split="dogrulama",
        )


def test_download_model_writes_under_download_dir(fake, platform, fast_settings):
    fake.on(
        "GET",
        f"/models/versions/{MODEL}/download",
        (200, envelope({"download_url": "/api/v1/files/m/best.pt", "filename": "best.pt"})),
    )
    fake.on("GET", "/files/m/best.pt", lambda r: httpx.Response(200, content=b"x" * 2000))
    out = download_model(platform, fast_settings, MODEL)
    assert out["dosya"].endswith("best.pt")
    assert out["dosya"].startswith(str(fast_settings.download_dir))


def test_download_sanitizes_filename(fake, platform, fast_settings):
    fake.on(
        "GET",
        f"/models/versions/{MODEL}/download",
        (200, envelope({"download_url": "/api/v1/files/m/x", "filename": "../../evil.pt"})),
    )
    fake.on("GET", "/files/m/x", lambda r: httpx.Response(200, content=b"x"))
    out = download_model(platform, fast_settings, MODEL)
    assert Path(out["dosya"]).parent.parent == fast_settings.download_dir
    assert Path(out["dosya"]).name == "evil.pt"


def test_download_refuses_overwrite(fake, platform, fast_settings):
    fake.on(
        "GET",
        f"/models/versions/{MODEL}/download",
        (200, envelope({"download_url": "/api/v1/files/m/best.pt", "filename": "best.pt"})),
    )
    fake.on("GET", "/files/m/best.pt", lambda r: httpx.Response(200, content=b"x"))
    download_model(platform, fast_settings, MODEL)
    with pytest.raises(EvrenError, match="zaten var"):
        download_model(platform, fast_settings, MODEL)


def test_download_does_not_overwrite_file_created_during_download(fake, platform, fast_settings):
    """Ertelenen bulgu: eşzamanlı iki indirme varlık kontrolünü birlikte geçerse ikincisi
    birincinin dosyasının üstüne yazmamalı."""
    dest = fast_settings.download_dir / MODEL[:8] / "best.pt"

    def yaris(request):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"ilk")
        return httpx.Response(200, content=b"ikinci")

    fake.on(
        "GET",
        f"/models/versions/{MODEL}/download",
        (200, envelope({"download_url": "/api/v1/files/m/best.pt", "filename": "best.pt"})),
    )
    fake.on("GET", "/files/m/best.pt", yaris)
    with pytest.raises(EvrenError, match="zaten var"):
        download_model(platform, fast_settings, MODEL)
    assert dest.read_bytes() == b"ilk"
    assert list(dest.parent.iterdir()) == [dest]
