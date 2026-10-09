# Değişiklik günlüğü

Biçim [Keep a Changelog](https://keepachangelog.com/tr-TR/1.1.0/) esaslı;
sürümler [Anlamsal Sürümleme](https://semver.org/lang/tr/)'ye uyar.

## [Yayınlanmadı]

### Eklendi

- `check_dataset_zip`: zip'i platforma bir şey göndermeden yerelde kontrol eder.
- MIT lisansı, İngilizce ve Türkçe README, katkı rehberi, güvenlik politikası.
- CI: Linux, Windows ve macOS'ta Python 3.11–3.14 testleri; ruff ve mypy.

### Değişti

- `upload_dataset` artık yalnız gerçek yüklemeyi yapar (`dry_run` kalktı);
  kuru kontrol ayrı araçta. Kuru kontrole verilen kalıcı izin gerçek yüklemeyi
  kapsamaz.
- `stop_training` istemciye geri alınamaz işlem olarak bildirilir.
- Günlük tavan mesajı, bekleyen tekliflerin neden sayıldığını açıklar.

### Düzeltildi

- `nan` ya da `inf` verilen tavan bütün kontrolleri sessizce kapatıyordu;
  artık reddediliyor.
- `http://` taban adresine ya da aynı alan adındaki `http://` bağlantıya
  anahtar gönderilebiliyordu; anahtar artık yalnız HTTPS ile gider.
- Eğitim başladıktan sonra yerel günlük yazılamazsa iş kimliği kayboluyordu;
  artık iş kimliği uyarıyla döner.
- Aynı modeli eşzamanlı indiren iki çağrı birbirinin dosyasının üstüne
  yazabiliyordu.
- Kredi defterinde ya da iş listesinde bozuk tarih anlaşılmaz bir hataya yol
  açıyordu; defterde güvenli Türkçe hataya döner, iş listesinde atlanır.

## [0.1.0] — 06.10.2026

İlk sürüm. Claude Code'dan EVREN platformunda:

- Okuma: veri setleri ve sürümler, herkese açık arama, kredi, puan ve ilk 10
  farkı, eğitim listesi ve durumu (Türkçe hata açıklamalı).
- Eğitim: bedava maliyet tahmini teklif üretir; eğitim yalnız teklifle,
  tek iş ve günlük tavan içinde başlar. Belirsiz platform yanıtında istek
  tekrar gönderilmez, iş listesinden doğrulanır. Durdurma.
- Ölçüm, model ağırlığı indirme, zip ön kontrolü ve gizli sete yükleme.
- Hazır akışlar (`egit`, `durum`), kaynaklar (kazanç kuralları, yerel günlük).
- Platform okuma isteklerinde 500'e karşı yeniden deneme; anahtar yalnız API
  alan adına gider.

[Yayınlanmadı]: https://github.com/emuzinun/evren-mcp/commits/main
[0.1.0]: https://github.com/emuzinun/evren-mcp/commits/main
