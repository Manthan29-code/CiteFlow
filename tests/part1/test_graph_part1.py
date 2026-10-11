import httpx
import pytest
import respx

from citegen.graph.workflow import get_compiled_part1_graph
from citegen.providers.crossref import CROSSREF_API_URL
from citegen.providers.openalex import OPENALEX_API_URL

pytestmark = pytest.mark.part1


@pytest.mark.asyncio
@respx.mock
async def test_graph_happy_path(crossref_kunz_json, openalex_kunz_json):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    graph = get_compiled_part1_graph()
    state = await graph.ainvoke(
        {
            "input_title": "Firehose and mirror instabilities in a collisionless plasma",
            "errors": [],
        }
    )

    assert state.get("status") == "accepted"
    assert state.get("match_status") == "matched"
    assert state.get("bibitem") is not None
    assert r"\bibitem{DRAFT}" in state["bibitem"]


@pytest.mark.asyncio
@respx.mock
async def test_graph_ambiguous_reaches_unresolved():
    # Candidates with ambiguous scores
    ambig_cr = {
        "message": {
            "items": [
                {
                    "title": ["Ambiguous Match 1"],
                    "DOI": "10.1000/1",
                    "issued": {"date-parts": [[2020]]},
                },
                {
                    "title": ["Ambiguous Match 1"],
                    "DOI": "10.1000/2",
                    "issued": {"date-parts": [[2020]]},
                },
            ]
        }
    }
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=ambig_cr)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json={"results": []})

    graph = get_compiled_part1_graph()
    state = await graph.ainvoke(
        {
            "input_title": "Ambiguous Match 1",
            "errors": [],
        }
    )

    assert state.get("status") == "unresolved"
    assert state.get("match_status") == "ambiguous"


@pytest.mark.asyncio
@respx.mock
async def test_graph_one_provider_down_still_completes(openalex_kunz_json):
    respx.get(CROSSREF_API_URL).respond(status_code=500, text="Down")
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    graph = get_compiled_part1_graph()
    state = await graph.ainvoke(
        {
            "input_title": "Firehose and mirror instabilities in a collisionless plasma",
            "errors": [],
        }
    )

    assert state.get("status") == "accepted"
    assert len(state.get("errors", [])) == 1
    assert state["errors"][0]["provider"] == "crossref"


@pytest.mark.asyncio
@respx.mock
async def test_graph_both_down_gives_provider_error():
    respx.get(CROSSREF_API_URL).respond(status_code=500, text="Down")
    respx.get(OPENALEX_API_URL).mock(side_effect=httpx.TimeoutException("Timeout"))

    graph = get_compiled_part1_graph()
    state = await graph.ainvoke(
        {
            "input_title": "Sample Title",
            "errors": [],
        }
    )

    assert state.get("status") == "unresolved"
    assert state.get("match_status") == "provider_error"
    # errors reducer collects both errors
    assert len(state.get("errors", [])) == 2
    providers_errored = {e["provider"] for e in state["errors"]}
    assert providers_errored == {"crossref", "openalex"}
