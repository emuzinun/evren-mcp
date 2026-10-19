# evren-mcp

[![CI](https://github.com/emuzinun/evren-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/emuzinun/evren-mcp/actions/workflows/ci.yml)
[![Lisans: MIT](https://img.shields.io/badge/lisans-MIT-blue.svg)](LICENSE)
![Python 3.11–3.14](https://img.shields.io/badge/python-3.11%E2%80%933.14-blue.svg)

**Türkçe** · [English](README.en.md)

**EVREN Yapay Zeka Platformu**'nu Claude Code'a bağlayan bir
[MCP](https://modelcontextprotocol.io) sunucusu. *"Bu veri setinde küçük bir
model eğit, kaça mal olur?"* dediğinde Claude maliyeti gösterir, onayını
bekler, eğitimi başlatır, sonucu ve puan farkını getirir.

**Farkı:** kredi harcayan hiçbir iş, sana gösterilmiş ve senin onayladığın bir
teklif olmadan başlamaz. Sunucu ayrıca kendi tek iş ve günlük kredi tavanını
uygular.

> [!IMPORTANT]
> **Resmî değildir.** Bu bağımsız bir topluluk projesidir; Savunma Sanayii
> Başkanlığı (SSB) ya da EVREN Yapay Zeka Platformu tarafından geliştirilmemiş,
> onaylanmamış ve desteklenmemektedir. "EVREN" adı yalnız uyumluluğu belirtmek
> için kullanılır. Sunucu yalnız **senin kendi** API anahtarınla çalışır; yaptığı
> her işlem hesabına bağlı EVREN Platformu Kullanıcı Sözleşmesi'ne tabidir.
> Sözleşmenin 4.9–4.11. maddeleri gereği yüklediğin veri setleri ve modeller
> platform tarafından model eğitiminde kullanılabilir.

## Örnek

```text
Sen:    Drone setimde küçük bir modeli ince ayarla. Kaça mal olur?
Claude: (list_datasets → estimate_training)
        Teklif T-51B553 — tahmini 0,54 CR, en kötü 1,82 CR.
        Bugün harcanan: 0 / 20 CR. Teklif 10 dk geçerli. Başlatayım mı?
Sen:    Evet.
Claude: (start_training T-51B553) Eğitim başladı: veri hazırlanıyor → eğitiliyor.
        …
Claude: (get_training) Tamamlandı. Gerçek maliyet 0,14 CR, mAP50 0,356,
        +15 puan.
```

Maliyet, metrik ve puan 06.10.2026'daki gerçek bir eğitimden; konuşma
kısaltılmıştır.

## Gerekenler

- [uv](https://docs.astral.sh/uv/) (uygun Python'u kendisi kurar; Python 3.11+)
- [Claude Code](https://docs.claude.com/en/docs/claude-code) ya da başka bir MCP istemcisi
- EVREN hesabı ve **Platform** API anahtarı (panel → API anahtarları → Platform)

## Kurulum

1. Anahtarını yalnız senin okuyabileceğin bir dosyaya yaz, ör. `~/.evren-mcp/.env`:

   ```dotenv
   EVREN_PLATFORM_API_KEY=platform-anahtarin
   ```

2. Sunucuyu Claude Code'a kaydet (dosyanın tam yolunu ver):

   ```bash
   claude mcp add evren --scope user -e EVREN_ENV_FILE=/tam/yol/.env \
     -- uvx --from git+https://github.com/emuzinun/evren-mcp evren-mcp
   claude mcp list   # evren … ✔ Connected
   ```

   Windows'ta `C:/Users/sen/.evren-mcp/.env` gibi bir yol kullan.

<details>
<summary>Yerel kopyadan (geliştirme için)</summary>

```bash
git clone https://github.com/emuzinun/evren-mcp.git && cd evren-mcp
uv sync
cp .env.example .env   # EVREN_PLATFORM_API_KEY'i doldur
claude mcp add evren --scope user -e EVREN_ENV_FILE=<tam-yol>/.env \
  -- uv run --directory <tam-yol> evren-mcp
```

</details>

Kurulumu denemek için Claude'a *"evren diagnostics çağır"* de: ayarlarını
anahtar maskeli gösterir.

## Araçlar

| Araç | Ne yapar | Maliyet |
|---|---|---|
| `list_datasets` | Setler ve sürümleri | bedava |
| `search_universe` | Herkese açık set/model arama | bedava |
| `get_credits` | Bakiye ve son hareketler | bedava |
| `get_standing` | Puan, seviye, ilk 10 sınırına fark | bedava |
| `estimate_training` | Maliyet tahmini + 10 dk geçerli teklif | bedava |
| `start_training` | Teklifle eğitimi başlatır | **kredi** |
| `get_training` / `list_trainings` | Durum, metrik, Türkçe hata açıklaması, puan farkı | bedava |
| `stop_training` | Süren eğitimi durdurur (geri alınamaz) | iade |
| `evaluate_model` | Modelin bir bölmedeki notunu ölçer | ~0,04 CR |
| `download_model` | Ağırlığı (`best.pt`) indirir | bedava |
| `check_dataset_zip` | Zip'i yerelde kontrol eder; hiçbir şey gönderilmez | bedava |
| `upload_dataset` | Zip'i yeni **gizli** sete yükler | bedava |
| `diagnostics` | Ayarlar (anahtar maskeli), istemci yetenekleri | bedava |

**Hazır akışlar** (Claude Code'da `/` menüsünde): `egit` — rehberli eğitim,
`durum` — bakiye, puan ve süren eğitimler.
**Kaynaklar:** `evren://kurallar` (kredi kazanç kuralları),
`evren://gunluk` (yerel eğitim günlüğü).

## Onay kapısı

```text
estimate_training ──► teklif (ayar parmak izi, tahmini/en kötü tutar, 10 dk)
        │
   sen onaylarsın
        │
start_training(teklif) ──► teklif geçerli, kullanılmamış? ──► tek iş tavanı ──► günlük tavan ──► POST
                                  hayır → ret                  (en kötü durum)   (platform defteri, UTC günü)
```

1. Teklif tek kullanımlıktır ve 10 dakikada düşer; sunucu yeniden başlayınca
   teklifler silinir, eski bir fiyatla iş başlamaz.
2. Tek iş tavanı platformun en kötü durum tahminine göre denetlenir.
3. Günlük tavan, bugünkü harcamayı platformun kendi kredi defterinden okur;
   açık teklifler ve yeni başlamış işler de 10 dk boyunca sayılır. Böylece
   eşzamanlı iki çağrı tavanın altından birlikte geçemez.
4. Platform başlatma isteğine net yanıt vermezse istek **tekrar gönderilmez**
   (çift ücret riski); sunucu işi iş listesinde arar.
5. Claude Code ayrıca her araç çağrısında izin sorar.

## Ayarlar

Ortam değişkenleri ya da `EVREN_ENV_FILE`'ın gösterdiği dosya (varsayılan:
çalışma klasöründeki `.env`). Süreç ortamındaki değer dosyadakini ezer.

| Değişken | Varsayılan |
|---|---|
| `EVREN_PLATFORM_API_KEY` | (zorunlu) |
| `EVREN_ENV_FILE` | `./.env` |
| `EVREN_PROJECT_ID` | ilk proje |
| `EVREN_MAX_JOB_CR` | 5 |
| `EVREN_MAX_DAILY_CR` | 20 |
| `EVREN_JOURNAL_PATH` | `~/.evren-mcp/journal.jsonl` |
| `EVREN_DOWNLOAD_DIR` | `~/.evren-mcp/models` |
| `EVREN_MAX_UPLOAD_MB` | 2048 |

## Güvenlik ve gizlilik

- Anahtar yalnız HTTPS ile API alan adına gider; başka alan adındaki indirme
  bağlantılarına gitmez. Her çıktıda ve hata mesajında maskelenir.
- İstekler dakikada 20 ile ve patlama yumuşatmayla sınırlanır; platformun hız
  sınırı zorlanmaz (şartlar sınırı atlatmayı yasaklıyor).
- Eğitim günlüğü ve indirilen modeller senin makinende kalır.
- Açık bildirmek için [SECURITY.md](SECURITY.md).

## Bilerek olmayanlar

Silme, herkese açık yapma, etiketleme, kullanım şartlarını onaylama, anahtar
yönetimi. Bunlar panelde kullanıcının elinde kalır.

## Geliştirme

[CONTRIBUTING.md](CONTRIBUTING.md). Tasarım: [docs/tasarim.md](docs/tasarim.md),
platformda ölçülen davranış: [docs/canli-dogrulama.md](docs/canli-dogrulama.md).

## Lisans

[MIT](LICENSE)
