import httpx
import pytest
import respx

from citegen.providers.openalex import (
    OPENALEX_API_URL,
    OpenAlexClient,
    fetch_openalex_candidates,
)

pytestmark = pytest.mark.part1


@pytest.mark.asyncio
@respx.mock
async def test_openalex_success(openalex_kunz_json):
    route = respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    client = OpenAlexClient()
    cands = await client.search_title("Firehose and mirror instabilities")

    assert len(cands) == 1
    assert cands[0].title == "Firehose and mirror instabilities in a collisionless plasma"
    assert route.called
    assert "api_key" not in route.calls.last.request.url.query.decode()


@pytest.mark.asyncio
@respx.mock
async def test_openalex_api_key_only_when_configured(openalex_kunz_json):
    route = respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    client = OpenAlexClient(api_key="my_secret_key")
    await client.search_title("Sample Title")

    assert route.called
    query_str = route.calls.last.request.url.query.decode()
    assert "api_key=my_secret_key" in query_str


@pytest.mark.asyncio
@respx.mock
async def test_openalex_empty_results():
    respx.get(OPENALEX_API_URL).respond(
        status_code=200,
        json={"meta": {"count": 0}, "results": []},
    )

    client = OpenAlexClient()
    cands = await client.search_title("Unknown title")
    assert cands == []


@pytest.mark.asyncio
@respx.mock
async def test_openalex_rate_limit():
    respx.get(OPENALEX_API_URL).respond(status_code=429, text="Too Many Requests")

    res = await fetch_openalex_candidates("Title")
    assert res["candidates"] == []
    assert res["error"] is not None
    assert res["error"]["type"] == "http_error"
    assert res["error"]["status_code"] == 429


@pytest.mark.asyncio
@respx.mock
async def test_openalex_timeout():
    respx.get(OPENALEX_API_URL).mock(side_effect=httpx.TimeoutException("Timeout"))

    res = await fetch_openalex_candidates("Title")
    assert res["candidates"] == []
    assert res["error"] is not None
    assert res["error"]["type"] == "timeout"


@pytest.mark.asyncio
@respx.mock
async def test_openalex_schema_drift():
    # Response missing common keys like authorships, biblio, primary_location
    sparse_result = {
        "results": [
            {
                "id": "https://openalex.org/W99999",
                "display_name": "Paper with missing fields",
                # no publication_year, no authorships, no biblio
            }
        ]
    }
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=sparse_result)

    client = OpenAlexClient()
    cands = await client.search_title("Paper")
    assert len(cands) == 1
    assert cands[0].title == "Paper with missing fields"
    assert cands[0].year is None
    assert cands[0].authors == []
    assert cands[0].volume is None
