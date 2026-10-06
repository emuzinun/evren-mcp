import anyio
from mcp.client import Client

from evren_mcp.server import build_server
from tests.fakes import envelope

READ_TOOLS = {"diagnostics", "list_datasets", "search_universe", "get_credits", "get_standing"}


def run(coro):
    return anyio.run(coro)


def test_read_tools_listed_and_marked_read_only(fake, platform, fast_settings):
    srv = build_server(fast_settings, platform=platform)

    async def go():
        async with Client(srv) as c:
            return (await c.list_tools()).tools

    tools = {t.name: t for t in run(go)}
    assert READ_TOOLS <= set(tools)
    assert all(tools[n].annotations.read_only_hint for n in READ_TOOLS)


def test_get_credits_through_mcp(fake, platform, fast_settings):
    fake.on("GET", "/organizations", (200, {"items": [{"credit_balance": "12.5"}]}))
    fake.on("GET", "/billing/ledger", (200, {"items": []}))
    srv = build_server(fast_settings, platform=platform)

    async def go():
        async with Client(srv) as c:
            return await c.call_tool("get_credits", {})

    r = run(go)
    assert not r.is_error and '"bakiye_cr": 12.5' in r.content[0].text


def test_evren_error_message_reaches_client_in_turkish(fake, platform, fast_settings):
    fake.on("GET", "/projects", (200, envelope([])))
    fake.on("GET", "/universe/search", (500, {"success": False}))
    srv = build_server(fast_settings, platform=platform)

    async def go():
        async with Client(srv) as c:
            return await c.call_tool("search_universe", {"query": "drone"})

    r = run(go)
    assert r.is_error and "denemede yanıt vermedi" in r.content[0].text


def test_diagnostics_masks_key(fake, platform, fast_settings):
    srv = build_server(fast_settings, platform=platform)

    async def go():
        async with Client(srv) as c:
            return await c.call_tool("diagnostics", {})

    text = run(go).content[0].text
    assert fast_settings.api_key not in text and "1234" in text  # "…" JSON'da kaçışlanabilir
