"""Kullanıcıya gösterilen hatalar.

`EvrenError`, kütüphanenin `ToolError`'ından türer: araç içinden fırlatılınca
mesaj istemciye olduğu gibi gider. Başka her istisnanın metni sunucuda kalır
[ölçüldü 06.10.2026, mcp 2.3.0] — anahtarın kaza ile sızmaması da buna dayanır.
"""

from __future__ import annotations

from mcp.server.mcpserver.exceptions import ToolError


class EvrenError(ToolError):
    """Türkçe, kullanıcıya olduğu gibi gösterilecek hata."""


class PlatformError(EvrenError):
    """Platformun döndürdüğü hata. `code="ambiguous"`: işlem gerçekleşmiş olabilir."""

    def __init__(self, message: str, status: int | None = None, code: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


class TermsNotAccepted(PlatformError):
    """Şartların yeni sürümü yayınlanmış; onay kullanıcının kararı."""


def redact(text: str, secret: str) -> str:
    return text.replace(secret, "***") if secret else text
