from pathlib import Path

import pymupdf
import pytest
import respx

from citegen.graph.workflow import get_compiled_part2_graph
from citegen.providers.crossref import CROSSREF_API_URL
from citegen.providers.openalex import OPENALEX_API_URL

pytestmark = pytest.mark.part2


def create_pdf(path: Path, title: str, fontsize: int = 24) -> Path:
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 100), title, fontsize=fontsize)
    p.insert_text(pymupdf.Point(50, 150), "Body content of the paper.", fontsize=10)
    doc.save(str(path))
    doc.close()
    return path


@pytest.mark.asyncio
@respx.mock
async def test_non_interactive_never_interrupts_and_accepts_high_confidence(
    crossref_kunz_json, openalex_kunz_json, tmp_path: Path
):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    pdf = create_pdf(
        tmp_path / "high_conf.pdf", "Firehose and mirror instabilities in a collisionless plasma"
    )

    graph = get_compiled_part2_graph()
    result = await graph.ainvoke(
        {
            "input_pdf_path": str(pdf),
            "interactive": False,
            "errors": [],
        },
        {"configurable": {"thread_id": "non-int-1"}},
    )

    assert "__interrupt__" not in result
    assert result.get("status") == "accepted"
    assert result.get("match_status") == "matched"


@pytest.mark.asyncio
@respx.mock
async def test_non_interactive_ambiguous_ends_unresolved(tmp_path: Path):
    # Two competing titles of exact same font size
    pdf = tmp_path / "ambig.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 80), "Title Candidate Alpha", fontsize=14)
    p.insert_text(pymupdf.Point(50, 120), "Title Candidate Beta", fontsize=14)
    p.insert_text(pymupdf.Point(50, 180), "Body text of document", fontsize=10)
    doc.save(str(pdf))
    doc.close()

    graph = get_compiled_part2_graph()
    result = await graph.ainvoke(
        {
            "input_pdf_path": str(pdf),
            "interactive": False,
            "errors": [],
        },
        {"configurable": {"thread_id": "non-int-ambig"}},
    )

    assert "__interrupt__" not in result
    assert result.get("status") == "unresolved"
    assert result.get("selected_metadata") is None


@pytest.mark.asyncio
@respx.mock
async def test_non_interactive_no_match_ends_unresolved(tmp_path: Path):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json={"message": {"items": []}})
    respx.get(OPENALEX_API_URL).respond(status_code=200, json={"results": []})

    pdf = create_pdf(tmp_path / "no_match.pdf", "Completely Unmatched Title 9999", fontsize=24)

    graph = get_compiled_part2_graph()
    result = await graph.ainvoke(
        {
            "input_pdf_path": str(pdf),
            "interactive": False,
            "errors": [],
        },
        {"configurable": {"thread_id": "non-int-no-match"}},
    )

    assert "__interrupt__" not in result
    assert result.get("status") == "unresolved"
    assert result.get("match_status") == "not_found"
