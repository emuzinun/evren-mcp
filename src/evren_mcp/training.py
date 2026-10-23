"""Eğitim: gövde, tahmin, başlatma, izleme, durdurma."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from . import budget
from .account import get_points, today_spend
from .config import Settings
from .datasets import default_project_id
from .errors import EvrenError, PlatformError
from .explain import STATUS_TR, explain_job
from .journal import Journal
from .platform import Platform, as_list, parse_ts, validate_id
from .quotes import QuoteBook

TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "ERROR"}

_ARCH = re.compile(r"^[a-z0-9][a-z0-9._-]{1,40}$")


def build_body(
    *,
    dataset_version_id: str,
    architecture: str,
    epochs: int,
    batch: int | None = None,
    imgsz: int | None = None,
    base_model_version_id: str | None = None,
) -> dict:
    """`POST /training/jobs` gövdesi.

    - Veri sürümü her zaman sabitlenir: yalnız set verilirse platform en yeni
      sürümü sessizce seçiyor [yazarın ölçümleri].
    - `epochs` hyperparams içine yazılır: üst düzey `epochs` sessizce yok
      sayılıyor [ölçüldü 21.09.2026].
    - `recipe` gönderilmez: platform recipe'li gövdeyi 422 ile reddediyor
      [ölçüldü 23.10.2026].
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
    body: dict = {
        "architecture": architecture,
        "gpu_count": 1,
        "dataset_version_id": validate_id(dataset_version_id, "veri sürümü kimliği"),
        "hyperparams": hp,
    }
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
    worst = float(d["p95_worst_cr"]) if d.get("p95_worst_cr") is not None else None
    spent = today_spend(p)
    budget.check(
        est,
        max_job=settings.max_job_cr,
        max_daily=settings.max_daily_cr,
        spent_today=spent,
        pending=quotes.pending_total(),
        worst=worst,
    )
    q = quotes.add(project, body, est, worst)
    return {
        "teklif": q.id,
        "gecerlilik_dk": int(quotes.ttl_s // 60),
        "tahmini_cr": est,
        "en_kotu_cr": q.worst_cr,
        "sure_saat": d.get("wall_hours"),
        "uygulanan_ayarlar": d.get("applied_hyperparams"),
        "uyarilar": d.get("warnings") or [],
        "gunluk": {"bugun_harcanan_cr": round(spent, 4), "tavan_cr": settings.max_daily_cr},
        "not": "Başlatmak için kullanıcıya tutarı göster, onay al, sonra start_training(teklif).",
    }


def _find_created(p: Platform, body: dict, since: datetime) -> dict | None:
    for j in as_list(p.get("/training/jobs", params={"limit": 10})):
        try:
            created = parse_ts(str(j.get("created_at")))
        except ValueError:
            continue  # tarihi okunamayan iş bizim az önce başlattığımız iş sayılmaz
        if (
            created >= since - timedelta(seconds=60)
            and j.get("dataset_version_id") == body["dataset_version_id"]
            and j.get("architecture") == body["architecture"]
        ):
            return j
    return None


def _resolve_ambiguous(p: Platform, journal: Journal, q, sent_at: datetime) -> dict:
    """POST'a net yanıt gelmedi: istek tekrar gönderilmez, iş listesine bakılır.

    Liste de okunamazsa durum belirsizdir; kullanıcıya "tekrar dene" denmez —
    iş oluşmuş olabilir, ikinci başlatma çift ücret demek.
    """
    try:
        job = _find_created(p, q.body, sent_at)
    except EvrenError:
        journal.append("egitim_belirsiz", teklif=q.id, govde=q.body, tahmini_cr=q.estimated_cr)
        raise EvrenError(
            "Durum belirsiz: platform eğitim isteğine net yanıt vermedi ve iş listesi de "
            "okunamadı. İş oluşmuş olabilir; istek tekrar gönderilmedi. Yeni eğitim "
            "başlatmadan önce birkaç dakika sonra list_trainings ile kontrol et."
        ) from None
    if job is None:
        raise EvrenError(
            "Platform eğitim isteğine net yanıt vermedi ve listede yeni iş görünmüyor. "
            "İstek tekrar gönderilmedi (çift ücret riski). Birkaç dakika sonra "
            "list_trainings ile bak; iş yoksa yeni teklifle tekrar dene."
        )
    return job


def start(p: Platform, quotes: QuoteBook, settings: Settings, journal: Journal, quote_id: str) -> dict:
    q = quotes.take(quote_id)
    # Kontrol ve ayırma tek adım: eşzamanlı ikinci başlatma bu ayırmayı görür.
    with quotes.spend_lock:
        budget.check(
            q.estimated_cr,
            max_job=settings.max_job_cr,
            max_daily=settings.max_daily_cr,
            spent_today=today_spend(p),
            pending=quotes.pending_total(),
            worst=q.worst_cr,
        )
        token = quotes.record_spend(q.estimated_cr)
    try:
        before = get_points(p)
    except EvrenError:
        quotes.cancel_spend(token)
        raise
    sent_at = datetime.now(UTC)
    try:
        job = p.post("/training/jobs", params={"project_id": q.project_id}, json=q.body)
    except PlatformError as e:
        if e.code != "ambiguous":
            quotes.cancel_spend(token)  # kesin ret: kredi ayrılmadı
            raise
        job = _resolve_ambiguous(p, journal, q, sent_at)
    if not isinstance(job, dict) or not job.get("id"):
        raise EvrenError("Platform eğitim kaydını döndürmedi; list_trainings ile kontrol et.")
    logged = journal.append(
        "egitim_basladi",
        is_id=job["id"],
        teklif=q.id,
        govde=q.body,
        tahmini_cr=q.estimated_cr,
        puan_once=before,
    )
    out = {
        "is_id": job["id"],
        "durum": job.get("status"),
        "durum_tr": STATUS_TR.get(str(job.get("status")), job.get("status")),
        "tahmini_cr": q.estimated_cr,
        "not": "İlerlemeyi get_training ile izle; küçük bir iş birkaç dakika sürer.",
    }
    if logged is None:
        out["uyari"] = (
            f"Eğitim başladı ama yerel günlüğe yazılamadı ({journal.path}); "
            "bitişteki puan farkı hesaplanamayacak. İş kimliğini not et."
        )
    return out


def _summary(j: dict) -> dict:
    return {
        "is_id": j.get("id"),
        "durum": j.get("status"),
        "durum_tr": STATUS_TR.get(str(j.get("status")), j.get("status")),
        "mimari": j.get("architecture"),
        "olusturma": j.get("created_at"),
    }


def status(p: Platform, journal: Journal, job_id: str) -> dict:
    jid = validate_id(job_id, "iş kimliği")
    j = p.get(f"/training/jobs/{jid}")
    out = _summary(j) | {
        "baslama": j.get("started_at"),
        "bitis": j.get("completed_at"),
        "tahmini_cr": j.get("estimated_cr"),
        "gercek_cr": j.get("actual_cr"),
        "gpu_saat": j.get("actual_gpu_hours"),
        "kuyruk_sirasi": j.get("queue_position"),
        "metrikler": j.get("final_metrics"),
        "model_surum_id": j.get("model_version_id"),
    }
    explanation = explain_job(j)
    if explanation:
        out["aciklama"] = explanation
    started = journal.find("egitim_basladi", jid)
    if j.get("status") in TERMINAL and started and not journal.find("egitim_bitti", jid):
        after = get_points(p)
        before = started.get("puan_once")
        diff = after - before if isinstance(after, int) and isinstance(before, int) else None
        journal.append(
            "egitim_bitti",
            is_id=jid,
            durum=j.get("status"),
            gercek_cr=j.get("actual_cr"),
            metrikler=j.get("final_metrics"),
            puan_sonra=after,
            puan_farki=diff,
        )
        out["puan_farki"] = diff
    return out


def list_jobs(p: Platform, limit: int = 10) -> list[dict]:
    return [_summary(j) for j in as_list(p.get("/training/jobs", params={"limit": limit}))[:limit]]


def stop(p: Platform, job_id: str) -> dict:
    jid = validate_id(job_id, "iş kimliği")
    j = p.get(f"/training/jobs/{jid}")
    if j.get("status") in TERMINAL:
        durum = STATUS_TR.get(str(j.get("status")), j.get("status"))
        raise EvrenError(f"İş zaten bitmiş ({durum}); durdurulacak bir şey yok.")
    p.post(f"/training/jobs/{jid}/stop")
    return {
        "is_id": jid,
        "istek": "durdurma gönderildi",
        "not": "Kullanılmayan kredi iade edilir; get_training ile durumu kontrol et.",
    }
