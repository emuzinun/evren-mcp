import httpx
import pytest

from evren_mcp.errors import EvrenError, PlatformError, TermsNotAccepted
from evren_mcp.platform import as_list, parse_ts, validate_id
from tests.fakes import envelope

KEY = "test-anahtar-ABCD1234"


def test_get_unwraps_envelope(fake, platform):
    fake.on("GET", "/auth/me", (200, envelope({"id": "u1"})))
    assert platform.get("/auth/me") == {"id": "u1"}


def test_get_plain_body_without_envelope(fake, platform):
    fake.on("GET", "/organizations", (200, {"items": [{"id": "o1"}]}))
    assert as_list(platform.get("/organizations")) == [{"id": "o1"}]


def test_get_retries_5xx_then_succeeds(fake, platform):
    fake.on(
        "GET", "/auth/me", (500, {"success": False}), (500, {"success": False}), (200, envelope({"id": "u1"}))
    )
    assert platform.get("/auth/me") == {"id": "u1"}
    assert len(fake.calls("GET", "/auth/me")) == 3
    assert all(s <= 15 for s in fake.sleeps)


def test_get_gives_up_after_five(fake, platform):
    fake.on("GET", "/auth/me", (500, {"success": False}))
    with pytest.raises(PlatformError, match="5 denemede"):
        platform.get("/auth/me")
    assert len(fake.calls("GET", "/auth/me")) == 5


def test_get_retries_non_json(fake, platform):
    fake.on("GET", "/auth/me", (200, "<html>bozuk</html>"), (200, envelope({"id": "u1"})))
    assert platform.get("/auth/me") == {"id": "u1"}


def test_get_4xx_not_retried_and_explained(fake, platform):
    fake.on(
        "GET",
        "/datasets/x",
        (404, {"success": False, "error": {"code": "NOT_FOUND", "message": "Veri seti bulunamadı"}}),
    )
    with pytest.raises(PlatformError, match="Bulunamadı"):
        platform.get("/datasets/x")
    assert len(fake.calls("GET", "/datasets/x")) == 1


def test_post_5xx_not_retried_marked_ambiguous(fake, platform):
    fake.on("POST", "/training/jobs", (500, {"success": False}))
    with pytest.raises(PlatformError) as e:
        platform.post("/training/jobs", json={})
    assert e.value.code == "ambiguous"
    assert len(fake.calls("POST", "/training/jobs")) == 1


def test_post_retry_flag_for_side_effect_free_calls(fake, platform):
    fake.on("POST", "/training/jobs/dry-run", (502, "x"), (200, envelope({"estimated_cr": 0.5})))
    assert platform.post("/training/jobs/dry-run", json={}, retry=True) == {"estimated_cr": 0.5}


def test_429_waits_then_retries(fake, platform):
    fake.on(
        "GET",
        "/auth/me",
        lambda r: httpx.Response(429, headers={"Retry-After": "7"}, json={}),
        (200, envelope({"id": "u1"})),
    )
    assert platform.get("/auth/me") == {"id": "u1"}
    assert 7 in fake.sleeps


def test_terms_not_accepted(fake, platform):
    fake.on(
        "GET",
        "/auth/me",
        (403, {"success": False, "error": {"code": "terms_not_accepted", "message": "terms"}}),
    )
    with pytest.raises(TermsNotAccepted, match="şart"):
        platform.get("/auth/me")


def test_key_never_in_error_message(fake, platform):
    fake.on(
        "GET",
        "/auth/me",
        (400, {"success": False, "error": {"code": "BAD", "message": f"anahtar {KEY} hatalı"}}),
    )
    with pytest.raises(PlatformError) as e:
        platform.get("/auth/me")
    assert KEY not in str(e.value)


def test_key_only_sent_to_api_host(fake, platform, tmp_path):
    seen = {}

    def dosya(request):
        seen[request.url.host] = request.headers.get("X-API-Key")
        return httpx.Response(200, content=b"agirlik")

    fake.on("GET", "/files/x.pt", dosya)
    platform.download("https://cdn.baska-alan.example/files/x.pt", tmp_path / "a.pt")
    platform.download("/api/v1/files/x.pt", tmp_path / "b.pt")
    assert seen["cdn.baska-alan.example"] is None
    assert seen["api.ssyz.org.tr"] == KEY
    assert (tmp_path / "b.pt").read_bytes() == b"agirlik"


def test_download_failure_leaves_no_file(fake, platform, tmp_path):
    fake.on("GET", "/files/y.pt", (500, "x"))
    with pytest.raises(PlatformError):
        platform.download("/api/v1/files/y.pt", tmp_path / "y.pt")
    assert not (tmp_path / "y.pt").exists()
    assert not list(tmp_path.glob("*.part"))


def test_post_ndjson_parses_events(fake, platform, tmp_path):
    z = tmp_path / "a.zip"
    z.write_bytes(b"PK")
    body = '{"t":"h"}\n{"t":"p","c":1,"n":2}\nbozuk\n{"t":"d","created":2}\n'
    fake.on("POST", "/datasets/d1/import", lambda r: httpx.Response(200, text=body))
    events = platform.post_ndjson("/datasets/d1/import", file_path=z, timeout=10)
    assert [e["t"] for e in events] == ["h", "p", "d"]


@pytest.mark.parametrize("bad", ["", "abc", "../../x", "00000000-0000-4000-8000-000000000001/stop"])
def test_validate_id_rejects(bad):
    with pytest.raises(EvrenError):
        validate_id(bad)


def test_validate_id_accepts_uuid():
    assert validate_id(" 00000000-0000-4000-8000-000000000001 ") == "00000000-0000-4000-8000-000000000001"


def test_parse_ts_accepts_z_and_offset():
    assert parse_ts("2026-10-05T19:53:05Z") == parse_ts("2026-10-05T19:53:05.000+00:00")


def test_download_transport_error_is_turkish_and_leaves_no_file(fake, platform, tmp_path):
    """İnceleme (önemli 7): akış sırasında bağlantı koparsa anlaşılır hata, yarım dosya yok."""

    def kopuk(request):
        raise httpx.ReadTimeout("zaman aşımı", request=request)

    fake.on("GET", "/files/z.pt", kopuk)
    with pytest.raises(PlatformError, match="bağlantı"):
        platform.download("/api/v1/files/z.pt", tmp_path / "z.pt")
    assert not list(tmp_path.iterdir())
