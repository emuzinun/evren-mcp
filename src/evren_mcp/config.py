"""Ayarlar: ortam değişkenleri, yoksa .env dosyası.

Dosya yeri `EVREN_ENV_FILE`, verilmezse çalışma klasöründeki `.env`.
Süreç ortamındaki değer dosyadakini ezer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values

from .errors import EvrenError

DEFAULT_BASE_URL = "https://api.ssyz.org.tr/api/v1"
HOME = Path.home() / ".evren-mcp"


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    project_id: str | None = None
    max_job_cr: float = 5.0
    max_daily_cr: float = 20.0
    journal_path: Path = field(default_factory=lambda: HOME / "journal.jsonl")
    download_dir: Path = field(default_factory=lambda: HOME / "models")
    max_upload_mb: int = 2048
    rpm: int = 20

    def masked_key(self) -> str:
        return f"…{self.api_key[-4:]}" if len(self.api_key) >= 8 else "…"


def _positive(env: Mapping[str, str], name: str, default: float) -> float:
    raw = (env.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise EvrenError(f"{name} sayı olmalı, '{raw}' verildi.") from None
    if value <= 0:
        raise EvrenError(f"{name} sıfırdan büyük olmalı, '{raw}' verildi.")
    return value


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    if env is None:
        merged = dict(os.environ)
        dosya = Path(merged.get("EVREN_ENV_FILE") or Path.cwd() / ".env")
        if dosya.is_file():
            for k, v in dotenv_values(dosya).items():
                if v is not None:
                    merged.setdefault(k, v)
        env = merged

    key = (env.get("EVREN_PLATFORM_API_KEY") or "").strip()
    if not key:
        raise EvrenError(
            "EVREN_PLATFORM_API_KEY tanımlı değil. Anahtarı .env dosyasına yaz "
            "(yerini EVREN_ENV_FILE ile değiştirebilirsin)."
        )
    defaults = Settings(api_key=key)
    return Settings(
        api_key=key,
        base_url=(env.get("EVREN_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
        project_id=(env.get("EVREN_PROJECT_ID") or "").strip() or None,
        max_job_cr=_positive(env, "EVREN_MAX_JOB_CR", defaults.max_job_cr),
        max_daily_cr=_positive(env, "EVREN_MAX_DAILY_CR", defaults.max_daily_cr),
        journal_path=Path(env["EVREN_JOURNAL_PATH"])
        if env.get("EVREN_JOURNAL_PATH")
        else defaults.journal_path,
        download_dir=Path(env["EVREN_DOWNLOAD_DIR"])
        if env.get("EVREN_DOWNLOAD_DIR")
        else defaults.download_dir,
        max_upload_mb=int(_positive(env, "EVREN_MAX_UPLOAD_MB", defaults.max_upload_mb)),
    )
