"""Eğitilmiş model ağırlığını indirme.

`GET /models/versions/{vid}/download` → `{download_url, filename}`; bağlantı
imzalı ve süreli [yazarın ölçümleri]. Dosya yalnız indirme klasörüne,
`<sürüm-kimliğinin-ilk-8>/<ad>` olarak yazılır; ad sunucudan gelse de
temizlenir, var olan dosyanın üstüne yazılmaz.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from .config import Settings
from .errors import EvrenError
from .platform import Platform, validate_id

_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def _safe_name(name: str) -> str:
    base = PurePosixPath(str(name).replace("\\", "/")).name
    base = _SAFE.sub("_", base).lstrip(".")
    return base or "model.pt"


def download_model(p: Platform, settings: Settings, model_version_id: str) -> dict:
    vid = validate_id(model_version_id, "model sürümü")
    d = p.get(f"/models/versions/{vid}/download")
    url = (d or {}).get("download_url")
    if not url:
        raise EvrenError("Platform indirme bağlantısı vermedi; model henüz hazır olmayabilir.")
    dest = settings.download_dir / vid[:8] / _safe_name(d.get("filename") or "best.pt")
    if dest.exists():
        raise EvrenError(f"{dest} zaten var; üstüne yazılmadı.")
    size = p.download(url, dest)
    return {"dosya": str(dest), "boyut_mb": round(size / 1e6, 2)}
