"""Veri setleri, sürümler, açık arama, proje."""

from __future__ import annotations

from .config import Settings
from .errors import EvrenError
from .platform import Platform, as_list, validate_id

_KINDS = ("dataset", "model")


def list_datasets(p: Platform) -> list[dict]:
    out = []
    for s in as_list(p.get("/datasets", params={"limit": 100})):
        sid = validate_id(s["id"], "veri seti kimliği")
        versions = as_list(p.get(f"/datasets/{sid}/versions"))
        out.append({
            "id": sid, "ad": s.get("name"), "gorunurluk": s.get("visibility"),
            "oge": s.get("item_count"), "etiket": s.get("annotation_count"),
            "surumler": [{"id": v.get("id"), "etiket": v.get("version_tag"),
                          "donmus": v.get("is_frozen"), "oge": v.get("item_count"),
                          "bolme": v.get("split_config")} for v in versions],
        })
    return out


def search_universe(p: Platform, query: str, kind: str = "dataset", limit: int = 10) -> list[dict]:
    if kind not in _KINDS:
        raise EvrenError(f"Tür {_KINDS} içinden olmalı, '{kind}' verildi.")
    rows = as_list(p.get("/universe/search", params={"type": kind, "q": query}))[:limit]
    return [{"ad": r.get("name"), "slug": r.get("slug"), "sahip": r.get("owner_username"),
             "oge": r.get("item_count"), "yildiz": r.get("stars_count")} for r in rows]


def default_project_id(p: Platform, settings: Settings) -> str:
    if settings.project_id:
        return validate_id(settings.project_id, "EVREN_PROJECT_ID")
    projects = as_list(p.get("/projects"))
    if not projects:
        raise EvrenError("Platformda proje yok. Panelden bir proje oluştur ya da "
                         "EVREN_PROJECT_ID ayarla.")
    return validate_id(projects[0]["id"], "proje kimliği")
