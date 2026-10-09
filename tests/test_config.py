from pathlib import Path

import pytest

from evren_mcp.config import DEFAULT_BASE_URL, load_settings
from evren_mcp.errors import EvrenError, redact


def test_missing_key_raises_turkish_error():
    with pytest.raises(EvrenError, match="EVREN_PLATFORM_API_KEY"):
        load_settings({})


def test_defaults():
    s = load_settings({"EVREN_PLATFORM_API_KEY": "abcd1234efgh"})
    assert s.base_url == DEFAULT_BASE_URL
    assert s.max_job_cr == 5.0 and s.max_daily_cr == 20.0
    assert s.max_upload_mb == 2048 and s.rpm == 20
    assert s.project_id is None


def test_overrides_and_paths(tmp_path: Path):
    s = load_settings(
        {
            "EVREN_PLATFORM_API_KEY": "abcd1234efgh",
            "EVREN_MAX_JOB_CR": "2.5",
            "EVREN_MAX_DAILY_CR": "10",
            "EVREN_JOURNAL_PATH": str(tmp_path / "g.jsonl"),
            "EVREN_DOWNLOAD_DIR": str(tmp_path / "m"),
            "EVREN_MAX_UPLOAD_MB": "100",
        }
    )
    assert s.max_job_cr == 2.5 and s.max_daily_cr == 10.0
    assert s.journal_path == tmp_path / "g.jsonl"
    assert s.download_dir == tmp_path / "m"
    assert s.max_upload_mb == 100


@pytest.mark.parametrize("deger", ["abc", "0", "-1"])
def test_bad_number_rejected(deger):
    with pytest.raises(EvrenError, match="EVREN_MAX_JOB_CR"):
        load_settings({"EVREN_PLATFORM_API_KEY": "abcd1234efgh", "EVREN_MAX_JOB_CR": deger})


def test_env_file_is_read_and_process_env_wins(tmp_path: Path, monkeypatch):
    dosya = tmp_path / ".env"
    dosya.write_text("EVREN_PLATFORM_API_KEY=dosyadaki-anahtar\nEVREN_MAX_DAILY_CR=7\n", encoding="utf-8")
    monkeypatch.setenv("EVREN_ENV_FILE", str(dosya))
    monkeypatch.setenv("EVREN_MAX_DAILY_CR", "9")
    monkeypatch.delenv("EVREN_PLATFORM_API_KEY", raising=False)
    s = load_settings()
    assert s.api_key == "dosyadaki-anahtar"
    assert s.max_daily_cr == 9.0


def test_masked_key_shows_only_last_four():
    s = load_settings({"EVREN_PLATFORM_API_KEY": "gizli-anahtar-WXYZ"})
    assert s.masked_key() == "…WXYZ"
    assert "gizli" not in s.masked_key()


def test_redact():
    assert redact("hata: gizli-anahtar geçersiz", "gizli-anahtar") == "hata: *** geçersiz"
    assert redact("metin", "") == "metin"


@pytest.mark.parametrize("deger", ["nan", "inf", "-inf", "NaN"])
def test_non_finite_cap_rejected(deger):
    """Ertelenen bulgu: `nan` tavan bütün karşılaştırmaları yanlış yapıp tavanı kapatıyordu."""
    with pytest.raises(EvrenError, match="EVREN_MAX_DAILY_CR"):
        load_settings({"EVREN_PLATFORM_API_KEY": "abcd1234efgh", "EVREN_MAX_DAILY_CR": deger})


def test_http_base_url_rejected():
    """Ertelenen bulgu: anahtar şifresiz bağlantıyla gitmemeli."""
    with pytest.raises(EvrenError, match="https"):
        load_settings(
            {"EVREN_PLATFORM_API_KEY": "abcd1234efgh", "EVREN_BASE_URL": "http://api.ssyz.org.tr/api/v1"}
        )
