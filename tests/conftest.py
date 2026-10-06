import pytest

from evren_mcp.config import load_settings


@pytest.fixture
def settings(tmp_path):
    return load_settings({
        "EVREN_PLATFORM_API_KEY": "test-anahtar-ABCD1234",
        "EVREN_JOURNAL_PATH": str(tmp_path / "journal.jsonl"),
        "EVREN_DOWNLOAD_DIR": str(tmp_path / "modeller"),
    })
