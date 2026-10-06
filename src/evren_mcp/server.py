"""MCP kayıtları. İş mantığı modüllerde; burada yalnız tanıtım."""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations

from . import account, datasets
from .config import Settings, load_settings
from .errors import EvrenError
from .platform import Platform

INSTRUCTIONS = (
    "EVREN platformu araçları. Kredi harcayan araçlardan önce kullanıcıya tutarı "
    "göster ve açık onay al. Eğitim: estimate_training → kullanıcı onayı → "
    "start_training(teklif). Eğitimi get_training ile izle; uzun bekleme döngüsü kurma. "
    "Test bölmesi tek seferlik ölçülür. Silme, herkese açık yapma ve etiketleme bu "
    "sunucuda yok; kullanıcı panelde yapar."
)
RO = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


def _version() -> str:
    try:
        return version("evren-mcp")
    except PackageNotFoundError:
        return "geliştirme"


def build_server(settings: Settings, platform: Platform | None = None,
                 quotes=None, journal=None) -> MCPServer:
    p = platform or Platform(settings)
    srv = MCPServer("evren", instructions=INSTRUCTIONS, version=_version())

    @srv.tool(name="diagnostics", annotations=RO,
              description="Sunucu ayarları ve istemci yetenekleri (anahtar maskeli).")
    def diagnostics(ctx: Context) -> dict:
        caps = ctx.client_capabilities
        return {"surum": _version(), "taban": settings.base_url, "anahtar": settings.masked_key(),
                "tek_is_tavani_cr": settings.max_job_cr, "gunluk_tavan_cr": settings.max_daily_cr,
                "gunluk_dosyasi": str(settings.journal_path),
                "indirme_klasoru": str(settings.download_dir),
                "istemci_elicitation": bool(caps and caps.elicitation)}

    @srv.tool(name="list_datasets", annotations=RO,
              description="Veri setlerin ve sürümleri (eğitimde sürüm kimliği kullanılır).")
    def list_datasets_tool() -> list[dict]:
        return datasets.list_datasets(p)

    @srv.tool(name="search_universe", annotations=RO,
              description="Platformdaki herkese açık veri setlerini ya da modelleri arar. kind: dataset|model")
    def search_universe_tool(query: str, kind: str = "dataset", limit: int = 10) -> list[dict]:
        return datasets.search_universe(p, query, kind, limit)

    @srv.tool(name="get_credits", annotations=RO, description="Kredi bakiyesi ve son hareketler.")
    def get_credits_tool(limit: int = 10) -> dict:
        return account.get_credits(p, limit)

    @srv.tool(name="get_standing", annotations=RO,
              description="Puan, seviye ve aylık/haftalık/tüm zamanlar ilk 10 sınırına kalan fark.")
    def get_standing_tool() -> dict:
        return account.get_standing(p)

    return srv


def main() -> None:
    try:
        settings = load_settings()
    except EvrenError as e:
        print(f"evren-mcp başlatılamadı: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    build_server(settings).run()
