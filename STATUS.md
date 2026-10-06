# Durum

## Son oturum · 06.10.2026 (ilk sürüm, 0.1.0)

## Nerede kaldık

Planın 13 görevi yazıldı; bağımsız kod incelemesinin 2 kritik + 5 önemli
bulgusu düzeltildi (günlük tavan hesabı, eşzamanlı başlatma, belirsiz yanıt,
akış hataları). 109 test geçiyor. Sunucu Claude Code'a kullanıcı kapsamında
kayıtlı (`evren`); okuma araçları ve günlük harcama hesabı gerçek platformda
denendi (`docs/canli-dogrulama.md`).
Ertelenen küçük bulgular Sıradaki 5'te.

## Sıradaki

1. **İlk gerçek eğitim yapıldı** (06.10, 0,14 CR, +15 puan) → `docs/canli-dogrulama.md`.
2. **Claude Code içi doğrulama:** `diagnostics` → `istemci_elicitation`,
   araç izin sorusu, `/` menüsünde akışların tam adı.
3. **Herkese açma hazırlığı** (ilk public repo): e-posta, iç belgeler, test
   kimlikleri, lisans, şartlar, README düzeni → `docs/yayina-hazirlik.md`.
   Repo şimdilik gizli; karar kullanıcının.
4. **Ertelenen bulgular:** nan/inf tavan, http şemasına anahtar, günlük yazımı
   patlarsa iş kimliği, stop_training işareti, upload kuru/gerçek ayrımı, açık
   tekliflerin tavana sayılması (açıklama), indirme yarışı, bozuk created_at,
   başarısız işte iade doğrulaması.
