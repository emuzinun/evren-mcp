# Canlı doğrulama

Gerçek platformda ölçülen davranışlar. Kodda `[ölçüldü tarih]` etiketiyle
anılan bilgilerin kaynağı burası. Hesaba özgü değerler (bakiye, puan, kimlikler)
yazılmaz.

## 06.10.2026 — Adım 1 (okuma araçları)

**Kayıt:** `claude mcp add evren --scope user -e EVREN_ENV_FILE=<tam-yol>/.env -- uv run --directory <tam-yol> evren-mcp`
→ `claude mcp list`: `evren … ✔ Connected` `[ölçüldü]`.

**stdio üzerinden gerçek platforma** (`mcp.client.Client` + `StdioServerParameters`) `[ölçüldü]`:
- Araçlar: `diagnostics`, `list_datasets`, `search_universe`, `get_credits`, `get_standing`.
- `diagnostics`: anahtar maskeli (`…` + son 4), tavanlar 5 / 20 CR.
  `istemci_elicitation: false` — bu, test istemcisinin yeteneği; Claude Code'unki
  Claude Code içinden çağrılınca görülür (aşağıda, bekliyor).
- `get_credits`: bakiye ve son hareketler okunuyor.
- `get_standing`: aylık ve tüm zamanlar ilk 10 sınırı ve fark okunuyor.
  **Bulgu:** haftalık sınır profil puanının altında ama listede değiliz → sıralama
  dönem puanını kullanıyor, dönem puanı API'de yok. Araç artık `fark: null`
  döndürüyor (test: `test_standing_not_inside_but_points_above_limit_is_unknown`).

**Claude Code içinden** `[ölçüldü 09.10.2026, Claude Code 2.1.295]`: araçlar
`mcp__evren__<araç>` adıyla yükleniyor; `diagnostics` → `istemci_elicitation: true`.
Sunucunun kullanıcıya doğrudan onay sorması (elicitation) bu sürümde mümkün;
onay kapısı hâlâ ona dayanmıyor.

**Bekliyor:** araç izin sorusunun görünüşü ve `/` menüsünde akışların tam adı
(etkileşimli oturumda bakılacak).

## 06.10.2026 — İnceleme düzeltmelerinden sonra

`today_spend` gerçek defterde salt okuma ile `[ölçüldü]`: ilk sayfa 50 satır,
47'sinde `reference_id`, 50'sinde `id` dolu; türler HOLD, RELEASE, REWARD,
SETTLE, SYSTEM_GRANT. UTC gününün 3 satırı dünkü işlerin `SYSTEM_GRANT`
iadeleri → bugünkü harcama 0 (iadeler bugünkü harcama sayılmıyor, doğru).
İkinci çağrı önbellekten (0,2 sn).

## 06.10.2026 — İlk gerçek eğitim (Adım 2)

Kullanıcı onayıyla, `evren_mcp.training` doğrudan çağrılarak (Claude Code
araçları bu oturumda yüklü değildi; akış aynı) `[ölçüldü]`:
- `estimate`: teklif `T-51B553`, tahmin 0,54 CR, en kötü 1,82, bugünkü harcama 0.
- `start`: iş `EXPORTING` → 1 dk içinde `TRAINING` → `COMPLETED`.
- Gerçek maliyet 0,14 CR. Fine-tune 1. epoch mAP50 0,356 (ağırlık yükleniyor).
- `status` bitişi günlüğe yazdı: `puan_farki: 15`.

## 23.10.2026 — `recipe` artık reddediliyor

`POST /training/jobs/dry-run` `[ölçüldü]`:
- Gövdede `recipe` varken 422 `VALIDATION_ERROR`. Genel mesaj "istek gövdesi
  eksik veya JSON olarak ayrıştırılamadı" diyor (yanıltıcı); asıl gerekçe
  `error.details[].message` içinde: "recipe/preset API'de desteklenmiyor;
  tarifin değerlerini hyperparams içinde açıkça gönderin". Önceden alan yok
  sayılıyordu.
- `recipe` olmadan aynı gövde `valid: true`.
- `gpu_count` uyarıyla yok sayılıyor ("Tanınmayan alan yok sayıldı");
  seçilen GPU sayısı 1. `POST /training/jobs`'taki davranışı ölçülmedi.
