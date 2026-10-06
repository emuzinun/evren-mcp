"""Sahte EVREN platformu: httpx.MockTransport üstünde yol → yanıt sırası.

Her yol için yanıtlar sırayla tüketilir, sonuncusu tekrarlanır. Yanıt ya
`(durum, gövde)` ya da `request -> httpx.Response` çağrılabilir.
"""

from __future__ import annotations

from typing import Any, Callable

import httpx

from evren_mcp.config import Settings
from evren_mcp.platform import Platform

Response = tuple[int, Any] | Callable[[httpx.Request], httpx.Response]


def envelope(data: Any) -> dict:
    return {"success": True, "data": data}


class FakeEvren:
    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], list[Response]] = {}
        self.requests: list[httpx.Request] = []
        self.sleeps: list[float] = []

    def on(self, method: str, path: str, *responses: Response) -> "FakeEvren":
        self.routes[(method, path)] = list(responses)
        return self

    def calls(self, method: str, path: str) -> list[httpx.Request]:
        return [r for r in self.requests
                if r.method == method and r.url.path.removeprefix("/api/v1") == path]

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = (request.method, request.url.path.removeprefix("/api/v1"))
        queue = self.routes.get(key)
        if not queue:
            return httpx.Response(404, json={"success": False, "error": {
                "code": "NOT_FOUND", "message": f"sahte platformda yok: {key}"}})
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if callable(item):
            return item(request)
        status, body = item
        if isinstance(body, (dict, list)):
            return httpx.Response(status, json=body)
        return httpx.Response(status, text=str(body))

    def platform(self, settings: Settings) -> Platform:
        http = httpx.Client(transport=httpx.MockTransport(self.handler))
        return Platform(settings, http=http, sleep=self.sleeps.append)
