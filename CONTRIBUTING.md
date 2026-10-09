# Katkı rehberi

*English: issues and pull requests in English are welcome. The project's
user-facing messages, comments and commit messages are in Turkish; we can help
with translation.*

Bu sunucu, e-Devlet ile girilen ve TCKN'ye bağlı resmî bir platformda kullanıcının
kredisini harcar. Bu yüzden kurallar sıkıdır; aşağıdakiler her değişiklik için
geçerlidir.

## Kurulum

```bash
git clone https://github.com/emuzinun/evren-mcp.git && cd evren-mcp
uv sync                       # bağımlılıklar + geliştirme araçları
uv run pytest -q              # testler (ağ yok, sahte platform)
uv run ruff check src tests   # lint
uv run ruff format src tests  # biçim
uv run mypy                   # tip denetimi
```

İsteğe bağlı: `uvx pre-commit install` ile ruff her commit'te çalışır.

CI her push'ta bütün geçmişi gitleaks ile sır taramasından geçirir. Testteki
uydurma anahtarlar `tests/` altında kalır; `.gitleaks.toml` izin listesi yalnız
orayı ve yalnız genel kuralı kapsar.

Testler gerçek platforma hiç gitmez: `tests/fakes.py` içindeki `FakeEvren`,
`httpx.MockTransport` üstünde yol → yanıt sırası tutar. Yeni bir platform
çağrısı eklerken önce sahte yanıtla test yaz.

## Kurallar

- **Platform davranışı ölçülmeden koda girmez.** Platformun bir davranışına
  dayanan her kod ya da yorum kaynağını yazar: `[ölçüldü GG.AA.YYYY]`.
  `[yazarın ölçümleri]` etiketleri, yazarın platform ölçümlerini tuttuğu gizli
  çalışma deposuna işaret eder.
- **Kredi harcayan her yol** teklif + tek iş tavanı + günlük tavan kapısından
  geçer (`quotes.py`, `budget.py`). POST isteği 5xx'te tekrar gönderilmez.
- **Anahtar** hiçbir çıktıya, günlüğe ya da hata mesajına maskesiz girmez;
  yalnız HTTPS ile API alan adına giden isteğe eklenir.
- **stdout'a `print` yok:** stdio sunucusunda stdout protokole aittir.
- Kullanıcıya gösterilen hata `EvrenError`'dır; başka istisnanın metni istemciye
  gitmez.
- **Kapsam dışı:** silme, herkese açık yapma, etiketleme, şart onayı, anahtar
  yönetimi. Bunları ekleyen PR kabul edilmez.
- Kullanıcıya dönen metinler Türkçe; kod adları İngilizce.
- Her hata düzeltmesi, düzeltmeden önce başarısız olan bir testle gelir.

## Commit ve PR

- Commit biçimi: `tür: kısa açıklama` — tür
  `feat|fix|docs|refactor|test|chore|perf|build|ci|style`.
  Örnek: `fix: bozuk tarihli defter satırında güvenli hata`.
- Kullanıcıya görünen değişiklik `CHANGELOG.md`'ye "Yayınlanmadı" başlığı
  altına yazılır.
- PR açmadan önce test, lint ve tip denetimi yerelde geçmelidir; CI aynısını
  Linux, Windows ve macOS'ta Python 3.11–3.14 ile koşar.

## Gerçek platformda deneme

Gerçek platforma giden deneme yalnız kendi hesabında, okuma araçlarıyla başlar.
Kredi harcayan bir deneme yapacaksan önce `EVREN_MAX_JOB_CR` ve
`EVREN_MAX_DAILY_CR`'ı düşük tut. Ölçtüğün yeni davranışı
`docs/canli-dogrulama.md`'ye tarih ve kaynakla ekle; hesap bakiyesi, puan,
kimlik numarası gibi kişisel değerleri yazma.
