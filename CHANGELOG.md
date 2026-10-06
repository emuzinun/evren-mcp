# Değişiklik Günlüğü

## 0.1.0 — 06.10.2026

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
