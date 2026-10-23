# Durum

## Son oturum · 23.10.2026 (0.2.1 düzeltme sürümü)

## Nerede kaldık

Repo **herkese açık** (19.10.2026); ilk sürüm `v0.2.0` (19.10.2026), son sürüm `v0.2.1`
(23.10.2026: platformun reddettiği `recipe` alanı gövdeden çıktı). Lisans (MIT), Türkçe README
(varsayılan) + İngilizcesi, katkı/güvenlik/davranış belgeleri, CI (Linux, Windows, macOS ×
Python 3.11–3.14, ruff, mypy, paket denetimi; action'lar SHA'ya sabit; yalnız
belge değişince de "CI sonucu" döner), commit'ler SSH ile imzalı, dependabot ve issue/PR
şablonları eklendi. Ertelenen inceleme bulgularından yedisi testle kapatıldı
(`CHANGELOG.md` → Yayınlanmadı). Geçmiş yeniden yazıldı: commit e-postası
GitHub noreply, iç plan ve gerçek kimlikler geçmişten çıkarıldı.

## Sıradaki

1. **Claude Code içi doğrulama:** araç izin sorusunun görünüşü, `/` menüsünde
   akışların tam adı.
2. **Başarısız işte iade doğrulaması:** iadenin defterde hangi `reference_id`
   ile geldiği ölçülmedi; ölçülünce `get_training` açıklamasına girer.
3. **Elicitation:** Claude Code 2.1.295 destekliyor; `start_training`'e ek
   onay katmanı olarak değerlendirilebilir.
4. **README'ye kısa ekran kaydı** (GIF) — gerçek oturumdan.
5. **`gpu_count`:** `dry-run` onu uyarıyla yok sayıyor [ölçüldü 23.10.2026];
   `POST /training/jobs`'ta ölçülünce gövdeden çıkarılır ya da kalır.
