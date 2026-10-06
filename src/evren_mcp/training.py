"""Eğitim: gövde, tahmin, başlatma, izleme, durdurma."""

from __future__ import annotations

import re

from . import budget
from .account import today_spend
from .config import Settings
from .datasets import default_project_id
from .errors import EvrenError
from .platform import Platform, validate_id
from .quotes import QuoteBook

_ARCH = re.compile(r"^[a-z0-9][a-z0-9._-]{1,40}$")


def build_body(*, dataset_version_id: str, architecture: str, epochs: int,
               batch: int | None = None, imgsz: int | None = None,
               base_model_version_id: str | None = None) -> dict:
    """`POST /training/jobs` gövdesi.

    - Veri sürümü her zaman sabitlenir: yalnız set verilirse platform en yeni
      sürümü sessizce seçiyor [yazarın ölçümleri].
    - `epochs` hyperparams içine yazılır: üst düzey `epochs` sessizce yok
      sayılıyor [ölçüldü 21.09.2026].
    - `recipe` platformca yok sayılıyor (yazarın ölçümleri); uyum için "quick".
    """
    if not _ARCH.match(architecture or ""):
        raise EvrenError(f"Geçersiz mimari adı: '{architecture}' (ör. yolov8n, yolo11s, rtdetr-l).")
    if not 1 <= int(epochs) <= 1000:
        raise EvrenError("epochs 1 ile 1000 arasında olmalı.")
    if batch is not None and not 1 <= int(batch) <= 512:
        raise EvrenError("batch 1 ile 512 arasında olmalı.")
    if imgsz is not None and not 64 <= int(imgsz) <= 2048:
        raise EvrenError("imgsz 64 ile 2048 arasında olmalı.")
    hp: dict = {"epochs": int(epochs)}
    if batch:
        hp["batch"] = int(batch)
    if imgsz:
        hp["imgsz"] = int(imgsz)
    body: dict = {"architecture": architecture, "recipe": "quick", "gpu_count": 1,
                  "dataset_version_id": validate_id(dataset_version_id, "veri sürümü kimliği"),
                  "hyperparams": hp}
    if base_model_version_id:
        body["base_model_version_id"] = validate_id(base_model_version_id, "başlangıç model sürümü")
    return body


def estimate(p: Platform, quotes: QuoteBook, settings: Settings, **build_kw) -> dict:
    body = build_body(**build_kw)
    project = default_project_id(p, settings)
    d = p.post("/training/jobs/dry-run", params={"project_id": project}, json=body, retry=True)
    if not d.get("valid", True):
        hatalar = "; ".join(str(e) for e in (d.get("errors") or [])) or "neden belirtilmedi"
        raise EvrenError(f"Platform bu ayarları geçersiz buldu: {hatalar}")
    est = float(d["estimated_cr"])
    worst = d.get("p95_worst_cr")
    spent = today_spend(p)
    budget.check(est, max_job=settings.max_job_cr, max_daily=settings.max_daily_cr,
                 spent_today=spent, pending=quotes.pending_total())
    q = quotes.add(project, body, est, float(worst) if worst is not None else None)
    return {
        "teklif": q.id, "gecerlilik_dk": int(quotes.ttl_s // 60),
        "tahmini_cr": est, "en_kotu_cr": q.worst_cr, "sure_saat": d.get("wall_hours"),
        "uygulanan_ayarlar": d.get("applied_hyperparams"), "uyarilar": d.get("warnings") or [],
        "gunluk": {"bugun_harcanan_cr": round(spent, 4), "tavan_cr": settings.max_daily_cr},
        "not": "Başlatmak için kullanıcıya tutarı göster, onay al, sonra start_training(teklif).",
    }
