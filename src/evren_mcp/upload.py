"""Zip ön kontrolü ve gizli veri setine yükleme.

Yükleme yolu `POST /datasets` + `POST /datasets/{id}/import` (NDJSON akışı);
`presign → put → confirm` etiket taşımıyor [yazarın ölçümleri].
Hesap genelindeki %80 benzersizlik kapısı denetlenemez (uç yok); yalnız zip
içi kopyalar sayılır ve kullanıcıya hatırlatılır.
"""

from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path, PurePosixPath

from .config import Settings
from .errors import EvrenError
from .platform import Platform, validate_id

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
_DRIVE = re.compile(r"^[A-Za-z]:")


def _is_unsafe(name: str) -> bool:
    n = name.replace("\\", "/")
    return n.startswith("/") or bool(_DRIVE.match(n)) or ".." in n.split("/")


def precheck(zip_path: Path, max_mb: float) -> dict:
    if not zip_path.is_file():
        raise EvrenError(f"Zip bulunamadı: {zip_path}")
    size_mb = zip_path.stat().st_size / 1e6
    if size_mb > max_mb:
        raise EvrenError(f"Zip {size_mb:.1f} MB; sınır {max_mb} MB (EVREN_MAX_UPLOAD_MB).")
    try:
        z = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        raise EvrenError(f"{zip_path.name} geçerli bir zip değil.") from None
    with z:
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        unsafe = [n for n in names if _is_unsafe(n)]
        if unsafe:
            raise EvrenError(f"Zip'te güvensiz yol var (klasör dışına çıkıyor): {unsafe[:3]}")
        mac = [n for n in names if "__MACOSX/" in n or PurePosixPath(n).name.startswith("._")]
        if mac:
            raise EvrenError(
                f"Zip'te {len(mac)} macOS gizli dosyası var (__MACOSX, ._*). "
                "Platform bunları görsel sanıyor; zip'i bunlar olmadan yeniden oluştur."
            )
        if not any(PurePosixPath(n).name == "data.yaml" for n in names):
            raise EvrenError("Zip'te data.yaml yok (sınıf adları burada tanımlanır).")
        images = [
            n
            for n in names
            if PurePosixPath(n).parts[:1] == ("images",) and PurePosixPath(n).suffix.lower() in IMAGE_EXT
        ]
        if not images:
            raise EvrenError("images/ klasöründe görsel yok.")
        labels = [n for n in names if PurePosixPath(n).parts[:1] == ("labels",) and n.endswith(".txt")]
        seen: set[str] = set()
        dup = 0
        for n in images:
            h = hashlib.sha256(z.read(n)).hexdigest()
            dup += h in seen
            seen.add(h)
    warnings = []
    if not labels:
        warnings.append("Etiket yok: set etiketsiz yüklenecek (etiketli zip +8 CR bonus verir).")
    if dup:
        warnings.append(f"{dup} görsel zip içinde kopya; platform kopyaları atlar.")
    warnings.append(
        "Hesap genelindeki %80 benzersizlik kapısı denetlenemedi: başka bir setinde aynı "
        "görseller varsa yükleme kredisi verilmez."
    )
    return {
        "gorsel": len(images),
        "etiket": len(labels),
        "kopya": dup,
        "boyut_mb": round(size_mb, 2),
        "uyarilar": warnings,
    }


def upload(
    p: Platform, settings: Settings, *, zip_path: str, name: str, description: str = "", dry_run: bool = True
) -> dict:
    path = Path(zip_path)
    report = precheck(path, settings.max_upload_mb)
    if dry_run:
        return {
            "kontrol": report,
            "not": "Yüklemek için kullanıcı onayıyla dry_run=false ile tekrar çağır. "
            "Set gizli (private) oluşturulur.",
        }
    name = (name or "").strip()
    if not 3 <= len(name) <= 100:
        raise EvrenError("Set adı 3–100 karakter olmalı.")
    ds = p.post(
        "/datasets",
        json={
            "name": name,
            "modality": "VISION",
            "description": description or None,
            "visibility": "private",
            "contributions_enabled": False,
        },
    )
    sid = validate_id((ds or {}).get("id", ""), "veri seti kimliği")
    try:
        events = p.post_ndjson(f"/datasets/{sid}/import", file_path=path, timeout=1800.0)
    except EvrenError as e:
        raise EvrenError(
            f"Set oluşturuldu ({sid}) ama içe aktarma sırasında hata: {e} "
            "Tekrar yüklemeden önce seti panelde kontrol et; yeniden denemek "
            "yeni bir set açar."
        ) from None
    done = next((e for e in reversed(events) if e.get("t") == "d"), None)
    if done is None:
        errors = [e.get("error") for e in events if e.get("t") == "e"][:1]
        raise EvrenError(
            f"Set oluşturuldu ({sid}) ama içe aktarma tamamlanmadı: {errors or 'yanıt yok'}. "
            "Set panelde boş durabilir; silme kararı senin."
        )
    return {
        "set_id": sid,
        "ad": name,
        "sonuc": {k: v for k, v in done.items() if k != "t"},
        "kontrol": report,
        "not": "Yeni set +5 puan getirir [ölçüldü 05.10.2026].",
    }
