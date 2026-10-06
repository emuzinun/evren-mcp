# evren-mcp

[Türkçe](#türkçe) · [English](#english)

## Türkçe

**Ne işe yarar:** EVREN platformunu (SSB / SSYZ) Claude Code'a bağlayan bir MCP
sunucusu. "Bu veri setinde küçük bir model eğit, kaça mal olur?" dediğinde
Claude maliyeti gösterir, onayını alır, eğitimi başlatır, sonucu ve puan
farkını getirir.

**Farkı:** kredi harcayan hiçbir iş, gösterilmiş ve onaylanmış bir teklif
olmadan başlamaz. Benzer ML platformu sunucularında (Roboflow, Hugging Face)
böyle bir kapı yok.

### Kurulum

```bash
git clone <repo> evren-mcp && cd evren-mcp
uv sync
cp .env.example .env        # EVREN_PLATFORM_API_KEY'i doldur (Platform anahtarı)
claude mcp add evren --scope user -e EVREN_ENV_FILE=<tam-yol>/.env -- uv run --directory <tam-yol> evren-mcp
claude mcp list             # evren … ✔ Connected
```

### Araçlar

| Araç | Ne yapar | Maliyet |
|---|---|---|
| `list_datasets` | Setler ve sürümleri | bedava |
| `search_universe` | Herkese açık set/model arama | bedava |
| `get_credits` | Bakiye ve son hareketler | bedava |
| `get_standing` | Puan, seviye, ilk 10 sınırına fark | bedava |
| `estimate_training` | Maliyet tahmini + 10 dk geçerli teklif | bedava |
| `start_training` | Teklifle eğitimi başlatır | **kredi** |
| `get_training` / `list_trainings` | Durum, metrik, Türkçe hata açıklaması, puan farkı | bedava |
| `stop_training` | Süren eğitimi durdurur | iade |
| `evaluate_model` | Modelin notunu ölçer | ~0,04 CR |
| `download_model` | Ağırlığı (best.pt) indirir | bedava |
| `upload_dataset` | Zip'i yeni **gizli** sete yükler (önce kuru kontrol) | bedava |
| `diagnostics` | Ayarlar (anahtar maskeli), istemci yetenekleri | bedava |

Hazır akışlar: `egit` (rehberli eğitim), `durum` (bakiye + puan + süren işler).
Kaynaklar: `evren://kurallar` (kazanç kuralları), `evren://gunluk` (yerel günlük).

### Onay kapısı

1. `estimate_training` bir teklif üretir: ayarlar, tahmini ve en kötü tutar, 10 dk süre.
2. `start_training` yalnız bu teklifle çalışır; teklif tek kullanımlıktır.
3. Sunucu tek iş tavanını ve günlük tavanı (UTC günü) platformun kredi defterinden denetler.
4. Claude Code her araç çağrısında ayrıca izin sorar.

### Ayarlar (`.env`)

| Değişken | Varsayılan |
|---|---|
| `EVREN_PLATFORM_API_KEY` | (zorunlu) |
| `EVREN_PROJECT_ID` | ilk proje |
| `EVREN_MAX_JOB_CR` | 5 |
| `EVREN_MAX_DAILY_CR` | 20 |
| `EVREN_JOURNAL_PATH` | `~/.evren-mcp/journal.jsonl` |
| `EVREN_DOWNLOAD_DIR` | `~/.evren-mcp/models` |
| `EVREN_MAX_UPLOAD_MB` | 2048 |

### Bilerek olmayanlar

Silme, herkese açık yapma, etiketleme, kullanım şartlarını onaylama, anahtar
yönetimi. Bunlar panelde kullanıcının elinde kalır.

**Lisans:** henüz belirlenmedi (gizli repo).

## English

**What it does:** an MCP server that connects the EVREN platform (Türkiye's
SSB / SSYZ AI platform) to Claude Code. Ask "train a small model on this
dataset — how much will it cost?" and Claude shows the price, waits for your
approval, starts the job, and reports results and leaderboard change.

**What's different:** no credit-spending job starts without a quote that was
shown to and approved by the user. Comparable ML-platform servers (Roboflow,
Hugging Face) have no such gate.

### Install

```bash
git clone <repo> evren-mcp && cd evren-mcp
uv sync
cp .env.example .env        # fill EVREN_PLATFORM_API_KEY (Platform key)
claude mcp add evren --scope user -e EVREN_ENV_FILE=<full-path>/.env -- uv run --directory <full-path> evren-mcp
claude mcp list             # evren … ✔ Connected
```

### Tools

| Tool | What it does | Cost |
|---|---|---|
| `list_datasets` | Datasets and versions | free |
| `search_universe` | Search public datasets/models | free |
| `get_credits` | Balance and recent ledger | free |
| `get_standing` | Points, tier, gap to top 10 | free |
| `estimate_training` | Cost estimate + quote valid for 10 min | free |
| `start_training` | Starts training from a quote | **credits** |
| `get_training` / `list_trainings` | Status, metrics, explained errors, point change | free |
| `stop_training` | Stops a running job | refund |
| `evaluate_model` | Scores a model on a split | ~0.04 CR |
| `download_model` | Downloads weights (best.pt) | free |
| `upload_dataset` | Uploads a zip to a new **private** dataset (dry run first) | free |
| `diagnostics` | Settings (key masked), client capabilities | free |

Prompts: `egit` (guided training), `durum` (balance + points + running jobs).
Resources: `evren://kurallar` (earning rules), `evren://gunluk` (local journal).
User-facing messages are in Turkish.

### Approval gate

1. `estimate_training` issues a quote: settings, estimated and worst-case cost, 10-minute validity.
2. `start_training` only accepts that quote; quotes are single-use.
3. The server enforces a per-job cap and a daily cap (UTC day) read from the platform ledger.
4. Claude Code additionally asks permission for each tool call.

### Settings

Same table as above: `EVREN_PLATFORM_API_KEY` (required), `EVREN_PROJECT_ID`,
`EVREN_MAX_JOB_CR` (5), `EVREN_MAX_DAILY_CR` (20), `EVREN_JOURNAL_PATH`,
`EVREN_DOWNLOAD_DIR`, `EVREN_MAX_UPLOAD_MB` (2048).

### Deliberately missing

Deleting, making things public, labeling, accepting terms of use, key
management. These stay manual, in the platform's web panel.

**License:** not decided yet (private repository).
