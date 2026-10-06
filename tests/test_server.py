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


def test_training_tools_registered_and_spending_ones_not_read_only(fake, platform, fast_settings):
    srv = build_server(fast_settings, platform=platform)

    async def go():
        async with Client(srv) as c:
            return {t.name: t for t in (await c.list_tools()).tools}

    tools = run(go)
    for n in ("estimate_training", "get_training", "list_trainings"):
        assert tools[n].annotations.read_only_hint
    for n in ("start_training", "stop_training"):
        assert tools[n].annotations.read_only_hint is False


def test_start_training_without_quote_is_refused(fake, platform, fast_settings):
    srv = build_server(fast_settings, platform=platform)

    async def go():
        async with Client(srv) as c:
            return await c.call_tool("start_training", {"quote_id": "T-YOK"})

    r = run(go)
    assert r.is_error and "Teklif bulunamadı" in r.content[0].text
    assert fake.calls("POST", "/training/jobs") == []


def test_prompts_and_resources(fake, platform, fast_settings):
    fake.on("GET", "/billing/earning/overview", (200, envelope({"rules": [{"slug": "daily-login", "cr_reward": 10}]})))
    srv = build_server(fast_settings, platform=platform)

    async def go():
        async with Client(srv) as c:
            prompts = {p.name for p in (await c.list_prompts()).prompts}
            egit = (await c.get_prompt("egit", {"istek": "drone seti"})).messages[0].content.text
            kurallar = (await c.read_resource("evren://kurallar")).contents[0].text
            gunluk = (await c.read_resource("evren://gunluk")).contents[0].text
            return prompts, egit, kurallar, gunluk

    prompts, egit, kurallar, gunluk = run(go)
    assert {"egit", "durum"} <= prompts
    assert "estimate_training" in egit and "drone seti" in egit and "onay" in egit
    assert "daily-login" in kurallar
    assert gunluk == "[]"
