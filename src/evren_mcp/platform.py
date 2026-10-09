"""Platformla konuşan tek kapı.

- Anahtar yalnız API alan adına https ile giden isteğe eklenir (indirme
  bağlantısı başka bir alan adına ya da http'ye giderse anahtar gitmez).
- GET: 5xx, bağlantı hatası ve JSON olmayan gövde yeniden denenir. Platform
  GET'lerin ~4'te 1'ine 500 döndü [ölçüldü 05.10.2026].
- POST: 5xx tekrar edilmez, `code="ambiguous"` ile yükselir — 500 dönen
  istek sunucuda gerçekleşmiş olabilir (çift eğitim, çift ücret).
  Yan etkisiz POST (`dry-run`) `retry=True` ile GET gibi denenir.
- 429: `Retry-After` ya da gövdedeki `resets_at` kadar beklenir.
- Yanıt zarfı `{success, data}` açılır; zarfsız gövde olduğu gibi döner.
"""

from __future__ import annotations

import json as jsonlib
import os
import re
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from .config import Settings
from .errors import EvrenError, PlatformError, TermsNotAccepted, redact
from .explain import explain_http
from .ratelimit import RateLimiter

ATTEMPTS = 5
MAX_BACKOFF_S = 15
MAX_429_WAITS = 3
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class _NotJson(Exception):
    pass


def validate_id(value: str, label: str = "kimlik") -> str:
    v = (value or "").strip()
    if not _UUID.match(v):
        raise EvrenError(f"Geçersiz {label}: '{value}'. Platform kimlikleri UUID biçiminde (8-4-4-4-12).")
    return v


def as_list(data: Any) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("items", "results"):
            if isinstance(data.get(k), list):
                return data[k]
    return []


def parse_ts(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _link_no_overwrite(src: Path, dest: Path) -> None:
    try:
        os.link(src, dest)
    except FileExistsError:
        raise EvrenError(f"{dest} zaten var; üstüne yazılmadı.") from None
    except OSError:
        # Sabit bağlantı desteklemeyen dosya sistemi: kontrol + taşıma.
        if dest.exists():
            raise EvrenError(f"{dest} zaten var; üstüne yazılmadı.") from None
        src.replace(dest)


class Platform:
    def __init__(
        self, settings: Settings, http: httpx.Client | None = None, sleep: Callable[[float], Any] = time.sleep
    ) -> None:
        self.settings = settings
        self.http = http or httpx.Client(timeout=120.0)
        self._sleep = sleep
        self._limiter = RateLimiter(settings.rpm)
        self._host = urlparse(settings.base_url).netloc
        self.ledger_cache: dict = {}  # account.today_spend: gün içinde okunan defter satırları

    # --- yardımcılar -------------------------------------------------------

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if path.startswith("/api/"):
            return urljoin(self.settings.base_url, path)
        return self.settings.base_url + path

    def _headers(self, url: str) -> dict[str, str]:
        u = urlparse(url)
        return {"X-API-Key": self.settings.api_key} if u.scheme == "https" and u.netloc == self._host else {}

    def _retry_after(self, r: httpx.Response) -> float:
        raw = r.headers.get("Retry-After")
        if raw and raw.strip().isdigit():
            return max(1.0, min(60.0, float(raw)))
        try:
            resets = r.json().get("error", {}).get("details", {}).get("resets_at")
            if resets:
                kalan = (parse_ts(resets) - datetime.now(UTC)).total_seconds()
                return max(1.0, min(60.0, kalan))
        except (ValueError, AttributeError):
            pass
        return 5.0

    def _request(self, method: str, path: str, **kw: Any) -> httpx.Response:
        url = self._url(path)
        waits = 0
        while True:
            self._limiter.acquire()
            r = self.http.request(method, url, headers=self._headers(url), **kw)
            if r.status_code != 429 or waits == MAX_429_WAITS:
                return r
            self._sleep(self._retry_after(r))
            waits += 1

    def _error(self, r: httpx.Response) -> PlatformError:
        code, message = None, r.text[:300]
        try:
            err = r.json().get("error") or {}
            code, message = err.get("code"), err.get("message") or message
        except (ValueError, AttributeError):
            pass
        text = redact(explain_http(r.status_code, code, str(message)), self.settings.api_key)
        if r.status_code == 403 and (code == "terms_not_accepted" or "terms_not_accepted" in r.text):
            return TermsNotAccepted(text, status=403, code="terms_not_accepted")
        return PlatformError(text, status=r.status_code, code=code)

    def _unwrap(self, r: httpx.Response) -> Any:
        if r.status_code >= 400:
            raise self._error(r)
        try:
            body = r.json()
        except ValueError:
            raise _NotJson() from None
        if isinstance(body, dict) and "success" in body:
            if body.get("success") is False:
                raise self._error(r)
            return body.get("data")
        return body

    # --- genel uçlar -------------------------------------------------------

    def _retrying(self, method: str, path: str, **kw: Any) -> Any:
        last = ""
        for i in range(ATTEMPTS):
            if i:
                self._sleep(min(2**i, MAX_BACKOFF_S))
            try:
                r = self._request(method, path, **kw)
            except httpx.TransportError:
                last = "bağlantı hatası"
                continue
            if r.status_code >= 500:
                last = f"HTTP {r.status_code}"
                continue
            try:
                return self._unwrap(r)
            except _NotJson:
                last = "JSON olmayan yanıt"
        raise PlatformError(
            f"Platform {path} için {ATTEMPTS} denemede yanıt vermedi ({last}). "
            "Platform kaynaklı geçici bir sorun olabilir; biraz sonra tekrar dene.",
            code="unavailable",
        )

    def get(self, path: str, params: dict | None = None) -> Any:
        return self._retrying("GET", path, params=params)

    def post(
        self,
        path: str,
        *,
        json: Any = None,
        params: dict | None = None,
        timeout: float | None = None,
        retry: bool = False,
    ) -> Any:
        kw: dict[str, Any] = {"json": json, "params": params}
        if timeout:
            kw["timeout"] = timeout
        if retry:
            return self._retrying("POST", path, **kw)
        try:
            r = self._request("POST", path, **kw)
        except httpx.TransportError:
            raise PlatformError(
                f"POST {path} sırasında bağlantı koptu; işlemin platformda gerçekleşip "
                "gerçekleşmediği belirsiz. İstek tekrar gönderilmedi.",
                code="ambiguous",
            ) from None
        if r.status_code >= 500:
            raise PlatformError(
                f"Platform POST {path} isteğine {r.status_code} döndü; istek tekrar "
                "gönderilmedi. İşlemin gerçekleşip gerçekleşmediği belirsiz.",
                status=r.status_code,
                code="ambiguous",
            )
        try:
            return self._unwrap(r)
        except _NotJson:
            raise PlatformError(
                f"Platform POST {path} isteğine JSON olmayan yanıt döndü; istek tekrar gönderilmedi.",
                status=r.status_code,
                code="ambiguous",
            ) from None

    def post_ndjson(self, path: str, *, file_path: Path, timeout: float) -> list[dict]:
        """Zip içe aktarma: yanıt satır satır JSON olaylarıdır (`t`: h/p/d/e)."""
        url = self._url(path)
        self._limiter.acquire()
        events: list[dict] = []
        try:
            with (
                file_path.open("rb") as f,
                self.http.stream(
                    "POST",
                    url,
                    headers=self._headers(url),
                    timeout=timeout,
                    files={"file": (file_path.name, f, "application/zip")},
                ) as r,
            ):
                if r.status_code != 200:
                    r.read()
                    raise self._error(r)
                for line in r.iter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(jsonlib.loads(line))
                    except ValueError:
                        continue
        except httpx.TransportError:
            raise PlatformError(
                "Yükleme sırasında bağlantı koptu; içe aktarmanın platformda "
                "tamamlanıp tamamlanmadığı belirsiz.",
                code="ambiguous",
            ) from None
        return events

    def download(self, url: str, dest: Path) -> int:
        """Dosyayı geçici `.part`'a indirir, bitince yerine bağlar; hata olursa iz bırakmaz.

        Var olan dosyanın üstüne yazılmaz: eşzamanlı iki indirme varlık kontrolünü
        birlikte geçse bile `os.link` hedef varsa reddeder.
        """
        full = self._url(url)
        part = dest.with_name(f"{dest.name}.{secrets.token_hex(4)}.part")
        dest.parent.mkdir(parents=True, exist_ok=True)
        self._limiter.acquire()
        size = 0
        try:
            with self.http.stream("GET", full, headers=self._headers(full), timeout=600.0) as r:
                if r.status_code != 200:
                    r.read()
                    raise self._error(r)
                with part.open("wb") as out:
                    for chunk in r.iter_bytes():
                        out.write(chunk)
                        size += len(chunk)
            _link_no_overwrite(part, dest)
        except httpx.TransportError:
            raise PlatformError(
                "İndirme sırasında bağlantı koptu; dosya yazılmadı. Biraz sonra tekrar dene.",
                code="unavailable",
            ) from None
        finally:
            if part.exists():
                part.unlink()
        return size
