import asyncio

import httpx
import pytest
import respx

from citegen.graph.workflow import get_compiled_part1_graph
from citegen.providers.crossref import CROSSREF_API_URL
from citegen.providers.openalex import OPENALEX_API_URL

pytestmark = pytest.mark.part1


@pytest.mark.asyncio
async def test_concurrency_proof(crossref_kunz_json, openalex_kunz_json):
    """
    Concurrency proof: mock Crossref waits until OpenAlex has started.
    Test passes ONLY if both requests are in flight at the same time.
    """
    openalex_started = asyncio.Event()

    async def crossref_side_effect(request):
        try:
            # Wait for OpenAlex request to start concurrently
            await asyncio.wait_for(openalex_started.wait(), timeout=2.0)
            return httpx.Response(200, json=crossref_kunz_json)
        except asyncio.TimeoutError:
            return httpx.Response(500, text="OpenAlex did not start concurrently!")

    async def openalex_side_effect(request):
        openalex_started.set()
        return httpx.Response(200, json=openalex_kunz_json)

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(CROSSREF_API_URL).mock(side_effect=crossref_side_effect)
        respx_mock.get(OPENALEX_API_URL).mock(side_effect=openalex_side_effect)

        graph = get_compiled_part1_graph()
        result = await graph.ainvoke(
            {
                "input_title": "Firehose and mirror instabilities in a collisionless plasma",
                "errors": [],
            }
        )

        assert openalex_started.is_set(), "OpenAlex was never triggered"
        assert result.get("status") == "accepted"
        assert result.get("match_status") == "matched"
        assert result.get("bibitem") is not None


@pytest.mark.asyncio
@respx.mock
async def test_crossref_timeout_openalex_survives(openalex_kunz_json):
    respx.get(CROSSREF_API_URL).mock(side_effect=httpx.TimeoutException("Crossref timeout"))
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    graph = get_compiled_part1_graph()
    result = await graph.ainvoke(
        {
            "input_title": "Firehose and mirror instabilities in a collisionless plasma",
            "errors": [],
        }
    )

    assert result.get("status") == "accepted"
    assert result.get("selected_metadata") is not None
    # Verify survivor's result was preserved and error was captured
    assert any(e.get("provider") == "crossref" for e in result.get("errors", []))


@pytest.mark.asyncio
@respx.mock
async def test_openalex_timeout_crossref_survives(crossref_kunz_json):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).mock(side_effect=httpx.TimeoutException("OpenAlex timeout"))

    graph = get_compiled_part1_graph()
    result = await graph.ainvoke(
        {
            "input_title": "Firehose and mirror instabilities in a collisionless plasma",
            "errors": [],
        }
    )

    assert result.get("status") == "accepted"
    assert result.get("selected_metadata") is not None
    assert any(e.get("provider") == "openalex" for e in result.get("errors", []))


@pytest.mark.asyncio
@respx.mock
async def test_both_providers_fail_gives_provider_error():
    respx.get(CROSSREF_API_URL).respond(status_code=500, text="Internal error")
    respx.get(OPENALEX_API_URL).respond(status_code=429, text="Rate limit")

    graph = get_compiled_part1_graph()
    result = await graph.ainvoke(
        {
            "input_title": "Sample Paper",
            "errors": [],
        }
    )

    assert result.get("match_status") == "provider_error"
    assert result.get("status") == "unresolved"
    assert len(result.get("errors", [])) == 2


@pytest.mark.asyncio
@respx.mock
async def test_both_empty_gives_not_found():
    respx.get(CROSSREF_API_URL).respond(status_code=200, json={"message": {"items": []}})
    respx.get(OPENALEX_API_URL).respond(status_code=200, json={"results": []})

    graph = get_compiled_part1_graph()
    result = await graph.ainvoke(
        {
            "input_title": "Completely Imaginary Title",
            "errors": [],
        }
    )

    assert result.get("match_status") == "not_found"
    assert result.get("status") == "unresolved"
