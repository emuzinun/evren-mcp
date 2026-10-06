# Canlı doğrulama

## 06.10.2026 — Adım 1 (okuma araçları)

**Kayıt:** `claude mcp add evren --scope user -e EVREN_ENV_FILE=<tam-yol>/.env -- uv run --directory <tam-yol> evren-mcp`
→ `claude mcp list`: `evren … ✔ Connected` `[ölçüldü]`.

**stdio üzerinden gerçek platforma** (`mcp.client.Client` + `StdioServerParameters`) `[ölçüldü]`:
- Araçlar: `diagnostics`, `list_datasets`, `search_universe`, `get_credits`, `get_standing`.
- `diagnostics`: anahtar maskeli (`…` + son 4), tavanlar 5 / 20 CR.
  `istemci_elicitation: false` — bu, test istemcisinin yeteneği; Claude Code'unki
  Claude Code içinden çağrılınca görülür (aşağıda, bekliyor).
- `get_credits`: bakiye … CR; son hareketler okunuyor.
- `get_standing`: puan 1.263; aylık sınır 1.540 (fark ≥ 277), tüm zamanlar 2.960.
  **Bulgu:** haftalık sınır 1.096 < profil puanı ama listede değiliz → sıralama
  dönem puanını kullanıyor, dönem puanı API'de yok. Araç artık `fark: null`
  döndürüyor (test: `test_standing_not_inside_but_points_above_limit_is_unknown`).

**Bekliyor (yeni Claude Code oturumunda kullanıcıyla):**
- Claude Code içinden `diagnostics` → `istemci_elicitation` değeri.
- Araç çağrısında izin sorusu çıkıyor mu.
- Görev 13'ten sonra: `/` menüsünde akışların tam adı.

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
- `start`: iş `…`, `EXPORTING` → 1 dk içinde `TRAINING` → `COMPLETED`.
- Gerçek maliyet 0,14 CR. Fine-tune 1. epoch mAP50 0,356 (ağırlık yükleniyor).
- `status` bitişi günlüğe yazdı: puan 1.263 → 1.278, `puan_farki: 15`.
