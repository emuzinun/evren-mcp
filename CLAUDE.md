## Yönlendirme
Yığın: Python 3.13 · `mcp` 2.3 (`MCPServer`, stdio) · httpx · uv
Komutlar: `uv run pytest -q` · `uv run evren-mcp` (stdio sunucusu)
Belgeler: `docs/tasarim.md` (tasarım) · `docs/plan.md` (uygulama planı) · `docs/yayina-hazirlik.md` ·
`docs/canli-dogrulama.md` (gerçek platformda ölçülenler) · README.md

---

# evren-mcp — Kurallar

Bu sunucu e-Devlet ile girilen, TCKN'ye bağlı resmî bir platformda kredi
harcar. Yazarın gizli ölçüm deposunun kuralları
burada da geçerli.

- Kullanıcıya dönen metin ve hata açıklamaları Türkçe; kod adları İngilizce;
  yorumlar ve commit mesajları Türkçe (`tür: kısa açıklama`).
- Tek iş tavanı varsayılan 5 CR, günlük tavan 20 CR, gün UTC.
- Teklif 10 dakika geçerli, tek kullanımlık.
- Throttle 20 istek/dk; GET 5xx'te 5 deneme (bekleme ≤ 15 sn); POST/PATCH
  5xx'te tekrar yok (yalnız yan etkisiz `dry-run` hariç).
- Anahtar hiçbir çıktıya, günlüğe, hata mesajına maskesiz girmez; yalnız API
  alan adına giden isteğe eklenir.
- stdout'a `print` yok — stdio sunucusunda stdout protokole ait.
- Kullanıcıya gösterilen hata `EvrenError`; başka istisnanın metni istemciye gitmez.
- Silme, herkese açık yapma, etiketleme, şart onayı, anahtar yönetimi eklenmez.
- Platform davranışı ölçülmeden koda girmez; kaynak etiketi `[ölçüldü tarih]`.
- Commit/push ve GitHub'da açma kararı kullanıcının.
