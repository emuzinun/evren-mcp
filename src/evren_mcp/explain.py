"""Platform hatalarının ve durumlarının Türkçe açıklaması.

İş hatasında yalnız ilk satır aktarılır: platform `error_message`'a iç adres,
düğüm adı ve traceback koyuyor (yazarın ölçümleri); bunları kullanıcının
sohbetine taşımıyoruz.
"""

from __future__ import annotations

STATUS_TR = {
    "PENDING": "kuyrukta",
    "QUEUED": "kuyrukta",
    "EXPORTING": "veri eğitim makinesine hazırlanıyor (eğitim henüz başlamadı)",
    "TRAINING": "eğitiliyor",
    "COMPLETED": "tamamlandı",
    "FAILED": "başarısız",
    "ERROR": "başarısız",
    "CANCELLED": "durduruldu",
}

_DISK = ("no space left", "disk_full", "errno 28")


def explain_job(job: dict) -> str | None:
    status = job.get("status")
    if status == "CANCELLED":
        return "Eğitim durduruldu. Kullanılmayan kredi iade edilir."
    if status not in ("FAILED", "ERROR"):
        return None
    text = str(job.get("error_message") or "")
    category = str(job.get("error_category") or "")
    if category == "DISK_FULL" or any(h in text.lower() for h in _DISK):
        return ("Platformun diski dolu olduğu için eğitim düştü — platform kaynaklı, "
                "ayarlarınla ilgisi yok. Ayrılan kredi iade edilir (get_credits'te "
                "'Kredi iadesi' satırı). Biraz sonra yeni teklifle tekrar dene.")
    if category == "INFRA":
        return ("Platform altyapı hatası (platform kaynaklı). Ayrılan kredi iade edilir; "
                "biraz sonra tekrar dene.")
    first = text.strip().splitlines()[0][:200] if text.strip() else "mesaj yok"
    return f"Eğitim başarısız oldu ({category or 'kategori yok'}): {first}"


def explain_http(status: int, code: str | None, message: str) -> str:
    message = (message or "").strip()[:300]
    if status == 403 and (code == "terms_not_accepted" or "terms_not_accepted" in message):
        return ("Kullanım şartlarının yeni sürümü yayınlanmış. Onay senin kararın: panelde "
                "şartları okuyup onayla. Bu sunucu şartları kendisi onaylamaz.")
    if status == 401:
        return "Anahtar geçersiz ya da süresi dolmuş. .env'deki EVREN_PLATFORM_API_KEY'i kontrol et."
    if status == 403:
        return f"Bu işleme yetki yok (Platform anahtarı gerekiyor olabilir): {message}"
    if status == 404:
        return f"Bulunamadı: {message}"
    if status in (409, 422, 400):
        return f"Platform isteği reddetti: {message}"
    if status == 429:
        return "Platformun hız sınırına takıldı; biraz bekleyip tekrar dene."
    return f"Platform hatası (HTTP {status}): {message}"
