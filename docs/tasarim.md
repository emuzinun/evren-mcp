# evren-mcp — Tasarım

Tarih: 06.10.2026 · Durum: uygulandı (0.1.0); 09.10.2026'da yayın öncesi
güncellendi.

Kaynak etiketleri: `[ölçüldü tarih]` gerçek platformda ölçüldü
(`docs/canli-dogrulama.md`); `[yazarın ölçümleri]` yazarın platform ölçümlerini
tuttuğu gizli çalışma deposundaki kayıt; `[belge]` resmî belgeden.

## 1. Amaç

Claude Code'dan EVREN platformunda model eğitmek, ölçmek ve hesabı izlemek:
"bu veri setinde küçük bir model eğit, kaça mal olur?" denince ajan maliyeti
gösterir, onay alır, eğitimi başlatır, sonucu ve puan farkını getirir.

**Kimin için:** kendi Platform anahtarıyla çalışan EVREN kullanıcıları (açık
kaynak, MIT).

**Başarı ölçütü:**
- Okuma araçları Claude Code'da çalışıyor (setler, kredi, puan, eğitim durumu).
- Bir eğitim yalnız geçerli teklif + tavan + Claude Code izniyle başlıyor;
  teklifsiz ya da tavan üstü başlatma testte ve canlıda reddediliyor.
- Platform hatası (500, disk dolu, şartlar) kullanıcıya Türkçe ve doğru
  açıklanıyor; aynı eğitim iki kez başlatılmıyor.

**Neden ayrı bir şey:** resmî `evren-sdk` 0.9.2 eğitim, ölçüm, sürüm, kredi
defteri ve sıralama içermiyor `[ölçüldü 05.10]`.
Roboflow ve Hugging Face MCP sunucularında eğitimden önce maliyet gösterip onay
isteyen mekanizma yok `[belge, 06.10]` — fark bu.

## 2. Kapsam

**İlk sürümde:** setler ve sürümler, açık veri arama, kredi, puan ve sıralama,
eğitim tahmini/başlatma/izleme/durdurma, model ölçümü, gizli sete zip yükleme,
model ağırlığı indirme, hazır akışlar (`/` komutları), kaynaklar, yerel eğitim
günlüğü, Türkçe hata açıklamaları.

**Bilerek dışarıda:** silme, herkese açık yapma, etiketleme (kırmızı çizgi —
`[yazarın ölçümleri]` kurallar §1.3), API anahtarı yönetimi, şartları onaylama.
Bunlar kullanıcının panelde eliyle yaptığı işler olarak kalır.

## 3. Yaklaşım

Python, resmî `mcp` kütüphanesi (2.x, Python ≥ 3.10; kurulu 3.13), stdio.
Yazarın ölçüm betiklerindeki denenmiş kod (eğitim gövdesi, throttle, kredi, ölçüm) yeni
pakete taşınıp düzenlenir; o betiklere çalışma zamanında bağımlılık yok.
Elenenler: TypeScript (her şeyi yeniden yazmak, aynı hataları yeniden yaşamak),
ölçüm betiklerini çağıran ince sarmalayıcı (yayınlanamaz).

Kurulum: `uvx --from git+https://github.com/emuzinun/evren-mcp evren-mcp`;
geliştirmede `uv run --directory <repo> evren-mcp`.

## 4. Yapı

| Modül | Sorumluluk |
|---|---|
| `server.py` | Araç, akış ve kaynak kayıtları; iş mantığı yok |
| `platform.py` | Tek HTTP kapısı: anahtar, throttle (20 istek/dk), GET'te 5xx yeniden deneme, `{success, data}` zarfını açma, kimlik biçim denetimi |
| `training.py` | Gövde kurma, tahmin, başlatma, izleme, durdurma |
| `quotes.py` | Teklif defteri (bellekte): numara, ayar parmak izi, tutar, son geçerlilik |
| `budget.py` | Tek iş ve günlük tavan; günlük harcama platform defterinden |
| `journal.py` | Yerel eğitim günlüğü (JSONL) |
| `explain.py` | Platform hata kodu → Türkçe açıklama ve önerilen adım |
| `datasets.py` | Setler, sürümler, açık arama |
| `account.py` | Bakiye, defter, puan, sıralama |
| `upload.py` | Zip ön kontrolü ve içe aktarma |

**Ayarlar (`.env`):** `EVREN_PLATFORM_API_KEY` (zorunlu), `EVREN_MAX_JOB_CR`
(varsayılan 5), `EVREN_MAX_DAILY_CR` (20), `EVREN_JOURNAL_PATH`,
`EVREN_DOWNLOAD_DIR`, `EVREN_MAX_UPLOAD_MB` (2048; platformun kendi sınırı ölçülmedi). Anahtar hiçbir çıktıya, günlüğe, hata mesajına girmez.

## 5. Araçlar

Ad İngilizce, açıklama ve dönen metin Türkçe.

**Bedava, salt okuma**

| Araç | Girdi | Çıktı |
|---|---|---|
| `list_datasets` | — | set, sürüm etiketleri ve kimlikleri, öğe/etiket sayısı |
| `search_universe` | sorgu, tür (dataset/model) | açık set/model listesi |
| `get_credits` | — | bakiye, son hareketler |
| `get_standing` | — | puan, seviye, aylık/haftalık/tüm zamanlar ilk 10 sınırı, fark |
| `list_trainings` | adet | son işler: durum, mimari, tarih |
| `get_training` | iş kimliği | durum, metrikler, maliyet; hata varsa açıklama |
| `estimate_training` | sürüm kimliği, mimari, epoch, batch, imgsz, başlangıç modeli? | tahmini CR, süre, **teklif numarası** |
| `download_model` | model sürüm kimliği | indirilen dosyanın yolu |
| `check_dataset_zip` | zip yolu | yerel kontrol raporu; platforma istek gitmez |

**Kredi harcayan / kayıt oluşturan** (her biri Claude Code izin sorusundan geçer)

| Araç | Girdi | Ek kapı |
|---|---|---|
| `start_training` | teklif numarası | teklif geçerli, parmak izi aynı, tutar tavan altı |
| `stop_training` | iş kimliği | yalnız süren iş; `POST /training/jobs/{id}/stop`; istemciye geri alınamaz (`destructiveHint`) bildirilir |
| `evaluate_model` | model sürümü, set sürümü, bölme | günlük tavan; platformda bedava tahmini yok (çağrı başı ~0,03–0,04 CR `[ölçüldü 29.09]`) |
| `upload_dataset` | zip yolu, set adı | yerel ön kontrol tekrar koşar; set her zaman `private`. Kuru kontrol ayrı araçta: ona verilen kalıcı izin gerçek yüklemeyi kapsamaz |

**Veri sürümü sabitlenir:** eğitim ve tahmin yalnız `dataset_version_id` ile
kurulur. Yalnız set verilirse platform en yeni sürümü sessizce seçiyor
`[yazarın ölçümleri]`.

**Hazır akışlar (MCP prompts):** `/evren:egit` (set seç → tahmin → onay →
başlat → izle → puan farkı), `/evren:durum` (bakiye, puan, süren işler).
Claude Code'daki tam komut adı henüz ölçülmedi.

**Kaynaklar:** güncel kazanç kuralları (`/billing/earning/overview`), yerel
eğitim günlüğü.

## 6. Eğitim akışı ve onay kapısı

1. `estimate_training` → `POST /training/jobs/dry-run`. Sunucu teklifi
   kaydeder: numara, gövdenin parmak izi (sıralı JSON'un SHA-256'sı), tahmini
   CR, son geçerlilik (10 dk). Tavanı aşan tutara teklif verilmez.
2. Kullanıcı onaylar; Claude `start_training(teklif)` çağırır; Claude Code
   izin sorar.
3. Sunucu denetler: teklif var ve süresi geçmemiş; tutar ≤ tek iş tavanı;
   bugünkü harcama + bekleyen teklifler + tutar ≤ günlük tavan. Biri tutmazsa
   başlatmaz, nedenini söyler. Teklif tek kullanımlıktır.
4. `POST /training/jobs`; iş günlüğe yazılır. Bitişte gerçek maliyet, metrik
   ve öncesi/sonrası puan günlüğe eklenir.

**Bugünkü harcama:** platform kredi defterinde bugünün (UTC) borç satırları
(eksi tutar); artı tutar yalnız bugünkü bir borçla aynı `reference_id`'yi
taşıyorsa düşülür, önceki günlerin iadeleri bugünü silmez (`account.today_spend`).
Yerel tahmin kullanılmaz; şüphede fazla sayılır.

**Elicitation:** sunucunun kullanıcıya doğrudan onay sorması protokolde var;
Claude Code 2.1.295 bu yeteneği bildiriyor `[ölçüldü 09.10.2026]`. Tasarım
ona dayanmaz (her istemci desteklemez); ileride 2. adıma ek katman olarak
girebilir.

## 7. Hata durumları

| Durum | Davranış |
|---|---|
| GET 5xx | 5 deneme, artan bekleme (en çok 15 sn); sonra anlaşılır hata |
| POST/PATCH 5xx | Tekrar yok. `start_training`'de iş listesi okunup iş oluşmuş mu bakılır (çift ücret önlenir) |
| 429 | Gövdedeki `resets_at` ya da `Retry-After` kadar bekleme |
| 403 `terms_not_accepted` | Durur; şart onayı kullanıcıya bırakılır |
| İş `FAILED` (`DISK_FULL`, `INFRA`) | Türkçe açıklama; iadenin defterden doğrulanması henüz yok (bilinen sınır, `STATUS.md`) |
| JSON olmayan gövde | Okumada yeniden deneme, yazmada durum kontrolü |

Kaynak: `[yazarın ölçümleri]` platform sorunları #38, #39; `train_run.py`
`getir()` (21.09 bozuk yoklama dersi).

## 8. Güvenlik

- Anahtar yalnız ortam değişkeninden; maskelenmeden hiçbir yere yazılmaz.
- Kimlikler UUID biçim denetiminden geçer; adrese ham metin eklenmez.
- Anahtar yalnız `https://` ile API alan adına gider; `EVREN_BASE_URL` `https`
  değilse sunucu başlamaz. Tavanlarda `nan`/`inf` reddedilir.
- `download_model` yalnız `EVREN_DOWNLOAD_DIR` altına yazar; var olan dosyanın
  üstüne yazmaz (eşzamanlı indirmede de: `os.link` hedef varsa reddeder).
- `upload_dataset`: `../` ve mutlak yol içeren girdileri, `EVREN_MAX_UPLOAD_MB`
  aşan zip'i reddeder; yapı (`images/`, `labels/`, `data.yaml`), macOS `._`
  dosyaları ve zip içi kopyalar (SHA-256) kontrol edilir.
- **Sınır:** hesap genelindeki %80 benzersizlik kapısı denetlenemez (uç yok);
  araç bunu kullanıcıya hatırlatır.

## 9. Testler

`pytest` + `httpx.MockTransport` sahte platform (yazarın ölçüm
betiklerindeki test kalıbı). Ağ yok.

- Teklif: süresi geçmiş, parmak izi değişmiş, tavan üstü, ikinci kullanım → red.
- Tavan: sahte defterde bugün 18 CR, 3 CR'lik iş → red; iadeler düşülüyor.
- Hata: GET 500 → yeniden dener; POST 500 → tekrar yok, iş listesine bakar.
- Zip: yol kaçışı, eksik `data.yaml`, `._` dosyası, kopya → yakalanır.
- Anahtar: araç çıktılarında, günlükte, hata mesajında görünmez.
- MCP katmanı: bellek içi istemciyle araç listesi ve örnek çağrılar.

Canlı deneme: okuma araçları serbest; kredi harcayan deneme kullanıcı
onayıyla. İlk gerçek eğitim 06.10.2026'da yapıldı (`docs/canli-dogrulama.md`).

## 10. Teslim sırası

1. İskelet, `platform.py`, okuma araçları, Claude Code'a bağlama. ✅
2. Tahmin, teklif, tavan, başlat/durdur, günlük, hata açıklamaları. ✅
3. Ölçüm, yükleme, indirme. ✅
4. Hazır akışlar, kaynaklar, iki dilli README. ✅
5. Yayın hazırlığı: lisans, CI, lint/tip denetimi, ertelenen inceleme
   bulguları. ✅

## 11. Dil

Kullanıcıya dönen metin ve hata açıklamaları Türkçe; README Türkçe
(`README.md`, varsayılan) + İngilizce (`README.en.md`); kod adları İngilizce, yorumlar ve commit mesajları Türkçe.
