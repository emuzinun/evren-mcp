"""MCP kayıtları. İş mantığı modüllerde; burada yalnız tanıtım."""

from __future__ import annotations

import json
import sys
from importlib.metadata import PackageNotFoundError, version

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations

from . import account, datasets, evaluation, models, training
from . import upload as upload_mod
from .config import Settings, load_settings
from .errors import EvrenError
from .journal import Journal
from .platform import Platform
from .quotes import QuoteBook

INSTRUCTIONS = (
    "EVREN platformu araçları. Kredi harcayan araçlardan önce kullanıcıya tutarı "
    "göster ve açık onay al. Eğitim: estimate_training → kullanıcı onayı → "
    "start_training(teklif). Eğitimi get_training ile izle; uzun bekleme döngüsü kurma. "
    "Test bölmesi tek seferlik ölçülür. Silme, herkese açık yapma ve etiketleme bu "
    "sunucuda yok; kullanıcı panelde yapar."
)
RO = ToolAnnotations(read_only_hint=True, open_world_hint=True)
LOCAL_RO = ToolAnnotations(read_only_hint=True, open_world_hint=False)
SPEND = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=True)
STOP = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=True)
LOCAL = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=True)


def _version() -> str:
    try:
        return version("evren-mcp")
    except PackageNotFoundError:
        return "geliştirme"


def build_server(
    settings: Settings, platform: Platform | None = None, quotes=None, journal=None
) -> MCPServer:
    p = platform or Platform(settings)
    qb = quotes or QuoteBook()
    jr = journal or Journal(settings.journal_path)
    srv = MCPServer("evren", instructions=INSTRUCTIONS, version=_version())

    @srv.tool(
        name="diagnostics",
        annotations=RO,
        description="Sunucu ayarları ve istemci yetenekleri (anahtar maskeli).",
    )
    def diagnostics(ctx: Context) -> dict:
        caps = ctx.client_capabilities
        return {
            "surum": _version(),
            "taban": settings.base_url,
            "anahtar": settings.masked_key(),
            "tek_is_tavani_cr": settings.max_job_cr,
            "gunluk_tavan_cr": settings.max_daily_cr,
            "gunluk_dosyasi": str(settings.journal_path),
            "indirme_klasoru": str(settings.download_dir),
            "istemci_elicitation": bool(caps and caps.elicitation),
        }

    @srv.tool(
        name="list_datasets",
        annotations=RO,
        description="Veri setlerin ve sürümleri (eğitimde sürüm kimliği kullanılır).",
    )
    def list_datasets_tool() -> list[dict]:
        return datasets.list_datasets(p)

    @srv.tool(
        name="search_universe",
        annotations=RO,
        description="Platformdaki herkese açık veri setlerini ya da modelleri arar. kind: dataset|model",
    )
    def search_universe_tool(query: str, kind: str = "dataset", limit: int = 10) -> list[dict]:
        return datasets.search_universe(p, query, kind, limit)

    @srv.tool(name="get_credits", annotations=RO, description="Kredi bakiyesi ve son hareketler.")
    def get_credits_tool(limit: int = 10) -> dict:
        return account.get_credits(p, limit)

    @srv.tool(
        name="get_standing",
        annotations=RO,
        description="Puan, seviye ve aylık/haftalık/tüm zamanlar ilk 10 sınırına kalan fark.",
    )
    def get_standing_tool() -> dict:
        return account.get_standing(p)

    @srv.tool(
        name="estimate_training",
        annotations=RO,
        description="Eğitim maliyetini bedava tahmin eder ve 10 dk geçerli bir teklif numarası "
        "üretir. Veri sürümü kimliği list_datasets'ten.",
    )
    def estimate_training(
        dataset_version_id: str,
        architecture: str,
        epochs: int,
        batch: int | None = None,
        imgsz: int | None = None,
        base_model_version_id: str | None = None,
    ) -> dict:
        return training.estimate(
            p,
            qb,
            settings,
            dataset_version_id=dataset_version_id,
            architecture=architecture,
            epochs=epochs,
            batch=batch,
            imgsz=imgsz,
            base_model_version_id=base_model_version_id,
        )

    @srv.tool(
        name="start_training",
        annotations=SPEND,
        description="KREDİ HARCAR. Yalnız kullanıcı teklifi açıkça onayladıktan sonra, "
        "teklif numarasıyla çağır.",
    )
    def start_training(quote_id: str) -> dict:
        return training.start(p, qb, settings, jr, quote_id)

    @srv.tool(
        name="get_training",
        annotations=RO,
        description="Eğitimin durumu, metrikleri, hata açıklaması; bitince puan farkı.",
    )
    def get_training(job_id: str) -> dict:
        return training.status(p, jr, job_id)

    @srv.tool(name="list_trainings", annotations=RO, description="Son eğitimler.")
    def list_trainings(limit: int = 10) -> list[dict]:
        return training.list_jobs(p, limit)

    @srv.tool(
        name="stop_training",
        annotations=STOP,
        description="Süren eğitimi durdurur (geri alınamaz; kullanılmayan kredi iade edilir).",
    )
    def stop_training(job_id: str) -> dict:
        return training.stop(p, job_id)

    @srv.tool(
        name="evaluate_model",
        annotations=SPEND,
        description="KÜÇÜK KREDİ HARCAR (~0,04 CR). Modelin bir veri bölmesindeki notunu ölçer. "
        "split: train|validation|test (test tek seferlik).",
    )
    def evaluate_model(
        model_version_id: str,
        dataset_id: str,
        dataset_version_id: str,
        split: str = "validation",
        image_size: int = 640,
    ) -> dict:
        return evaluation.evaluate(
            p,
            qb,
            settings,
            model_version_id=model_version_id,
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            split=split,
            image_size=image_size,
        )

    @srv.tool(
        name="download_model",
        annotations=LOCAL,
        description="Eğitilmiş modelin ağırlık dosyasını (best.pt) indirme klasörüne indirir.",
    )
    def download_model_tool(model_version_id: str) -> dict:
        return models.download_model(p, settings, model_version_id)

    @srv.tool(
        name="check_dataset_zip",
        annotations=LOCAL_RO,
        description="Zip'i yüklemeden yerelde kontrol eder (yapı, güvensiz yol, kopya görsel). "
        "Platforma istek gitmez.",
    )
    def check_dataset_zip(zip_path: str) -> dict:
        return upload_mod.check(settings, zip_path=zip_path)

    @srv.tool(
        name="upload_dataset",
        annotations=SPEND,
        description="Zip'i yeni bir GİZLİ veri setine yükler. Önce check_dataset_zip ile raporu "
        "kullanıcıya göster; yalnız kullanıcı onaylarsa çağır.",
    )
    def upload_dataset(zip_path: str, name: str, description: str = "") -> dict:
        return upload_mod.upload(p, settings, zip_path=zip_path, name=name, description=description)

    @srv.prompt(name="egit", description="Rehberli eğitim: set seç, maliyet gör, onayla, başlat, izle.")
    def egit_prompt(istek: str = "") -> str:
        return (
            f"EVREN'de bir model eğitmek istiyorum. İsteğim: {istek or '(belirtilmedi)'}\n"
            "1. list_datasets ile setlerimi göster; uygun set ve SÜRÜM kimliğini benimle seç.\n"
            "2. estimate_training ile maliyeti al; tahmini ve en kötü tutarı, süreyi, bugünkü "
            "harcamayı bana göster.\n"
            "3. Açık onayımı bekle. Onay vermezsem başlatma.\n"
            "4. Onaylarsam start_training(teklif) çağır.\n"
            "5. get_training ile birkaç dakikada bir durumu kontrol et; uzun döngü kurma, "
            "bana ara durum bildir. Bitince metrikleri ve puan farkını özetle; hata varsa "
            "açıklamasını aktar."
        )

    @srv.prompt(name="durum", description="Bakiye, puan ve süren eğitimler tek özet.")
    def durum_prompt() -> str:
        return (
            "get_credits, get_standing ve list_trainings araçlarını çağır; bakiyemi, "
            "puanımı, aylık ilk 10'a kalan farkı ve süren eğitimleri kısa bir özet olarak ver."
        )

    @srv.resource(
        "evren://kurallar",
        name="kurallar",
        mime_type="application/json",
        description="Platformun güncel kredi kazanç kuralları (/billing/earning/overview).",
    )
    def kurallar_resource() -> str:
        return json.dumps(p.get("/billing/earning/overview"), ensure_ascii=False)

    @srv.resource(
        "evren://gunluk",
        name="gunluk",
        mime_type="application/json",
        description="Yerel eğitim günlüğünün son 50 kaydı.",
    )
    def gunluk_resource() -> str:
        return json.dumps(jr.read(50), ensure_ascii=False)

    return srv


def main() -> None:
    try:
        settings = load_settings()
    except EvrenError as e:
        print(f"evren-mcp başlatılamadı: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    build_server(settings).run()
