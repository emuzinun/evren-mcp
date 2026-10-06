"""Model ölçümü (`POST /inference/evaluate`).

Platformda bedava tahmini yok; çağrı başı 0,033–0,044 CR ölçüldü
[ölçüldü 29.09.2026]. Tavan kontrolü 0,05 CR üst sınırıyla yapılır.
"""

from __future__ import annotations

from . import budget
from .account import today_spend
from .config import Settings
from .errors import EvrenError, PlatformError
from .platform import Platform, validate_id
from .quotes import QuoteBook

EVAL_ESTIMATE_CR = 0.05
_SPLITS = ("train", "validation", "test")
_KEYS = ("map", "precision", "recall", "f1")


def _metrics(obj: object, prefix: str = "", out: dict | None = None) -> dict:
    out = {} if out is None else out
    if len(out) >= 40:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and any(x in k.lower() for x in _KEYS):
                out[f"{prefix}{k}"] = v
            elif isinstance(v, (dict, list)):
                _metrics(v, f"{prefix}{k}.", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:12]):
            _metrics(v, f"{prefix}{i}.", out)
    return out


def evaluate(p: Platform, quotes: QuoteBook, settings: Settings, *, model_version_id: str,
             dataset_id: str, dataset_version_id: str, split: str = "validation",
             image_size: int = 640) -> dict:
    if split not in _SPLITS:
        raise EvrenError(f"Geçersiz bölme: '{split}'. Seçenekler: {_SPLITS}.")
    body = {"model_version_id": validate_id(model_version_id, "model sürümü"),
            "dataset_id": validate_id(dataset_id, "veri seti kimliği"),
            "dataset_version_id": validate_id(dataset_version_id, "veri sürümü kimliği"),
            "split": split, "confidence": 0.001, "iou": 0.6, "image_size": int(image_size),
            "include_samples": False}
    with quotes.spend_lock:
        budget.check(EVAL_ESTIMATE_CR, max_job=settings.max_job_cr, max_daily=settings.max_daily_cr,
                     spent_today=today_spend(p), pending=quotes.pending_total())
        token = quotes.record_spend(EVAL_ESTIMATE_CR)
    try:
        d = p.post("/inference/evaluate", json=body, timeout=1800.0)
    except PlatformError as e:
        if e.code != "ambiguous":
            quotes.cancel_spend(token)
        raise
    out: dict = {"bolme": split, "metrikler": _metrics(d)}
    if split == "test":
        out["uyari"] = ("Test kümesi tek seferlik ölçülür; bu sonuca bakarak ayar değiştirilirse "
                        "test tarafsızlığını yitirir.")
    return out
