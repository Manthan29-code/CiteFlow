import httpx
import pytest
import respx

from citegen.providers.crossref import (
    CROSSREF_API_URL,
    CrossrefClient,
    fetch_crossref_candidates,
)

pytestmark = pytest.mark.part1


@pytest.mark.asyncio
@respx.mock
async def test_crossref_success_and_user_agent(crossref_kunz_json):
    route = respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)

    client = CrossrefClient(mailto="test@example.com")
    cands = await client.search_title("Firehose and mirror instabilities")

    assert len(cands) == 1
    assert cands[0].title == "Firehose and mirror instabilities in a collisionless plasma"
    assert route.called
    headers = route.calls.last.request.headers
    assert "test@example.com" in headers["user-agent"]


@pytest.mark.asyncio
@respx.mock
async def test_crossref_empty_results():
    respx.get(CROSSREF_API_URL).respond(
        status_code=200,
        json={"status": "ok", "message": {"items": []}},
    )

    client = CrossrefClient()
    cands = await client.search_title("Nonexistent Paper Title")
    assert cands == []


@pytest.mark.asyncio
@respx.mock
async def test_crossref_http_429():
    respx.get(CROSSREF_API_URL).respond(status_code=429, text="Rate limit exceeded")

    res = await fetch_crossref_candidates("Any Title")
    assert res["candidates"] == []
    assert res["error"] is not None
    assert res["error"]["type"] == "http_error"
    assert res["error"]["status_code"] == 429


@pytest.mark.asyncio
@respx.mock
async def test_crossref_http_500():
    respx.get(CROSSREF_API_URL).respond(status_code=500, text="Internal Server Error")

    res = await fetch_crossref_candidates("Any Title")
    assert res["candidates"] == []
    assert res["error"] is not None
    assert res["error"]["type"] == "http_error"
    assert res["error"]["status_code"] == 500


@pytest.mark.asyncio
@respx.mock
async def test_crossref_malformed_json():
    respx.get(CROSSREF_API_URL).respond(status_code=200, text="Not valid JSON")

    res = await fetch_crossref_candidates("Any Title")
    assert res["candidates"] == []
    assert res["error"] is not None
    assert res["error"]["type"] == "general_error"


@pytest.mark.asyncio
@respx.mock
async def test_crossref_timeout():
    respx.get(CROSSREF_API_URL).mock(side_effect=httpx.TimeoutException("Mocked timeout"))

    res = await fetch_crossref_candidates("Any Title")
    assert res["candidates"] == []
    assert res["error"] is not None
    assert res["error"]["type"] == "timeout"


@pytest.mark.asyncio
@respx.mock
async def test_crossref_returns_several_candidates():
    items = [
        {"title": [f"Candidate {i}"], "DOI": f"10.1000/{i}", "issued": {"date-parts": [[2020]]}}
        for i in range(5)
    ]
    respx.get(CROSSREF_API_URL).respond(
        status_code=200,
        json={"status": "ok", "message": {"items": items}},
    )

    client = CrossrefClient()
    cands = await client.search_title("Candidate", rows=5)
    assert len(cands) == 5
