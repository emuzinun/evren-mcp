## Yönlendirme
Yığın: Python ≥ 3.11 (geliştirmede 3.13) · `mcp` 2.3 (`MCPServer`, stdio) · httpx · uv
Komutlar: `uv run pytest -q` · `uv run ruff check src tests` · `uv run ruff format src tests` ·
`uv run mypy` · `uv run evren-mcp` (stdio sunucusu)
Belgeler: README.md (EN) · README.tr.md · CONTRIBUTING.md · `docs/tasarim.md` (tasarım) ·
`docs/canli-dogrulama.md` (gerçek platformda ölçülenler) · `docs/yayina-hazirlik.md` (yayın adımları)

---

# evren-mcp — Kurallar

Bu sunucu e-Devlet ile girilen, TCKN'ye bağlı resmî bir platformda kredi
harcar. Yazarın gizli ölçüm deposunun kuralları burada da geçerli;
özeti CONTRIBUTING.md'de.

- Kullanıcıya dönen metin ve hata açıklamaları Türkçe; kod adları İngilizce;
  yorumlar ve commit mesajları Türkçe (`tür: kısa açıklama`).
- Tek iş tavanı varsayılan 5 CR, günlük tavan 20 CR, gün UTC.
- Teklif 10 dakika geçerli, tek kullanımlık.
- Throttle 20 istek/dk; GET 5xx'te 5 deneme (bekleme ≤ 15 sn); POST/PATCH
  5xx'te tekrar yok (yalnız yan etkisiz `dry-run` hariç).
- Anahtar hiçbir çıktıya, günlüğe, hata mesajına maskesiz girmez; yalnız
  `https://` ile API alan adına giden isteğe eklenir.
- stdout'a `print` yok — stdio sunucusunda stdout protokole ait.
- Kullanıcıya gösterilen hata `EvrenError`; başka istisnanın metni istemciye gitmez.
- Silme, herkese açık yapma, etiketleme, şart onayı, anahtar yönetimi eklenmez.
- Platform davranışı ölçülmeden koda girmez; kaynak etiketi `[ölçüldü tarih]`.
- Belgelere hesaba özgü değer (bakiye, puan, gerçek kimlik, yerel yol) yazılmaz;
  testlerde uydurma UUID kullanılır. Uydurma anahtar yalnız `tests/` altında
  (`.gitleaks.toml` izni yalnız orayı kapsar).
- Commit/push ve GitHub'da açma kararı kullanıcının.
