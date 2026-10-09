# Güvenlik politikası / Security policy

## Desteklenen sürümler / Supported versions

| Sürüm | Destek |
|---|---|
| 0.1.x | ✅ |

## Açık bildirme / Reporting a vulnerability

Güvenlik açıklarını **herkese açık issue olarak açmayın.** GitHub'ın gizli
bildirim formunu kullanın:
[Security → Report a vulnerability](https://github.com/emuzinun/evren-mcp/security/advisories/new).

*Please do not open public issues for vulnerabilities; use GitHub's private
vulnerability reporting link above.*

Bildirimde API anahtarı, `.env` içeriği ya da kişisel veri paylaşmayın.
Bir hafta içinde yanıt vermeyi, doğrulanan açığı düzeltip yeni sürümle
duyurmayı hedefliyoruz.

## Kapsam / Scope

Kapsamda:

- API anahtarının bir çıktıya, günlüğe, hata mesajına ya da API dışı bir
  adrese sızması
- Teklif, tek iş tavanı ya da günlük tavanın atlatılarak kredi harcanması
- `download_model` / `upload_dataset` üzerinden indirme klasörü dışına yazma
  ya da yerel dosya okuma

Kapsam dışı: EVREN platformunun kendisindeki açıklar. Bunları platforma
bildirin (platformun sitesindeki iletişim adresi).
