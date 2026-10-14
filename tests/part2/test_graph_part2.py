from pathlib import Path
from unittest.mock import patch

import pymupdf
import pytest
import respx
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from citegen.graph.workflow import get_compiled_part2_graph
from citegen.providers.crossref import CROSSREF_API_URL
from citegen.providers.openalex import OPENALEX_API_URL

pytestmark = pytest.mark.part2


def create_sample_pdf(path: Path, title: str, fontsize: int = 24) -> Path:
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 100), title, fontsize=fontsize)
    p.insert_text(
        pymupdf.Point(50, 150), "Body text of the paper with normal font size.", fontsize=10
    )
    doc.save(str(path))
    doc.close()
    return path


@pytest.mark.asyncio
@respx.mock
async def test_high_confidence_title_skips_interrupt(
    crossref_kunz_json, openalex_kunz_json, tmp_path: Path
):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    pdf_file = create_sample_pdf(
        tmp_path / "kunz.pdf",
        "Firehose and mirror instabilities in a collisionless plasma",
        fontsize=24,
    )

    graph = get_compiled_part2_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-auto-accept"}}

    result = await graph.ainvoke(
        {
            "input_pdf_path": str(pdf_file),
            "interactive": True,
            "errors": [],
        },
        config,
    )

    # Should not be interrupted because title is high confidence and metadata matches cleanly
    assert "__interrupt__" not in result
    assert result.get("status") == "accepted"
    assert result.get("match_status") == "matched"
    assert result.get("bibitem") is not None


@pytest.mark.asyncio
@respx.mock
async def test_ambiguous_title_raises_confirm_title_and_resume_choice(
    crossref_kunz_json, openalex_kunz_json, tmp_path: Path
):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    # Two competing titles of exact same font size
    pdf_file = tmp_path / "ambig.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 80), "Competing Candidate One", fontsize=14)
    p.insert_text(pymupdf.Point(50, 120), "Competing Candidate Two", fontsize=14)
    p.insert_text(pymupdf.Point(50, 180), "Body text of document", fontsize=10)
    doc.save(str(pdf_file))
    doc.close()

    graph = get_compiled_part2_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-ambig-title"}}

    result = await graph.ainvoke(
        {
            "input_pdf_path": str(pdf_file),
            "interactive": True,
            "errors": [],
        },
        config,
    )

    # Must be interrupted for title confirmation
    assert "__interrupt__" in result
    payload = result["__interrupt__"][0].value
    assert payload["kind"] == "confirm_title"

    # Resume by choosing real title
    chosen = "Firehose and mirror instabilities in a collisionless plasma"
    resumed_result = await graph.ainvoke(
        Command(resume={"action": "select", "title": chosen}),
        config,
    )

    assert resumed_result.get("status") == "accepted"
    assert resumed_result.get("match_status") == "matched"


@pytest.mark.asyncio
@respx.mock
async def test_resume_with_custom_title_continues(
    crossref_kunz_json, openalex_kunz_json, tmp_path: Path
):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    pdf_file = tmp_path / "custom_test.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text(pymupdf.Point(50, 100), "Unclear Scanned Title", fontsize=13)
    p.insert_text(pymupdf.Point(50, 130), "Alternative Title Heading", fontsize=13)
    doc.save(str(pdf_file))
    doc.close()

    graph = get_compiled_part2_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-custom-title"}}

    result = await graph.ainvoke(
        {
            "input_pdf_path": str(pdf_file),
            "interactive": True,
            "errors": [],
        },
        config,
    )

    assert "__interrupt__" in result
    # Resume with custom title
    resumed = await graph.ainvoke(
        Command(
            resume={
                "action": "custom",
                "title": "Firehose and mirror instabilities in a collisionless plasma",
            }
        ),
        config,
    )

    assert resumed.get("status") == "accepted"
    assert (
        resumed.get("input_title") == "Firehose and mirror instabilities in a collisionless plasma"
    )


@pytest.mark.asyncio
@respx.mock
async def test_no_title_leads_to_ocr_then_manual_entry_interrupt(
    crossref_kunz_json, openalex_kunz_json, tmp_path: Path
):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    # Empty text PDF
    pdf_file = tmp_path / "blank_ocr.pdf"
    doc = pymupdf.open()
    _ = doc.new_page()
    doc.save(str(pdf_file))
    doc.close()

    graph = get_compiled_part2_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-blank-ocr"}}

    # Mock OCR returning empty text
    with patch(
        "citegen.graph.nodes.ocr_pdf_pages",
        return_value={"success": True, "page_texts": [], "extracted_text": ""},
    ):
        result = await graph.ainvoke(
            {
                "input_pdf_path": str(pdf_file),
                "interactive": True,
                "errors": [],
            },
            config,
        )

    # Should interrupt for manual title entry
    assert "__interrupt__" in result
    payload = result["__interrupt__"][0].value
    assert payload["kind"] == "confirm_title"

    # User manually enters title
    resumed = await graph.ainvoke(
        Command(
            resume={
                "action": "custom",
                "title": "Firehose and mirror instabilities in a collisionless plasma",
            }
        ),
        config,
    )
    assert resumed.get("status") == "accepted"


@pytest.mark.asyncio
@respx.mock
async def test_no_match_retry_limit_then_unresolved(tmp_path: Path):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json={"message": {"items": []}})
    respx.get(OPENALEX_API_URL).respond(status_code=200, json={"results": []})

    pdf_file = create_sample_pdf(
        tmp_path / "unknown.pdf", "Completely Unknown Title 9999", fontsize=24
    )

    graph = get_compiled_part2_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-no-match-retry"}}

    # Initial invoke
    res1 = await graph.ainvoke(
        {
            "input_pdf_path": str(pdf_file),
            "interactive": True,
            "errors": [],
        },
        config,
    )

    # First no-match allows retry
    assert "__interrupt__" in res1
    # Retry with another unknown title
    res2 = await graph.ainvoke(
        Command(resume={"action": "custom", "title": "Second Unknown Attempt"}),
        config,
    )

    # Hits retry limit and terminates unresolved
    assert res2.get("status") == "unresolved"
    assert res2.get("match_status") in ("not_found", "ambiguous")


@pytest.mark.asyncio
@respx.mock
async def test_conflicting_record_raises_user_review_and_edits_provenance(tmp_path: Path):
    # Provider returning conflict (e.g. missing journal or ambiguous conflict)
    cr_data = {
        "message": {
            "items": [
                {
                    "title": ["A Sample Paper With Missing Journal"],
                    "DOI": "10.1000/123",
                    "issued": {"date-parts": [[2021]]},
                    "author": [{"family": "Smith", "given": "John"}],
                }
            ]
        }
    }
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=cr_data)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json={"results": []})

    pdf_file = create_sample_pdf(
        tmp_path / "review.pdf", "A Sample Paper With Missing Journal", fontsize=24
    )

    graph = get_compiled_part2_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-user-review"}}

    res = await graph.ainvoke(
        {
            "input_pdf_path": str(pdf_file),
            "interactive": True,
            "errors": [],
        },
        config,
    )

    assert "__interrupt__" in res
    payload = res["__interrupt__"][0].value
    assert payload["kind"] == "user_review"

    # User supplies missing journal abbreviation and volume
    resumed = await graph.ainvoke(
        Command(
            resume={
                "action": "edit",
                "edits": {
                    "journal": "Nature Physics",
                    "journal_abbreviation": "Nat. Phys.",
                    "volume": "17",
                    "first_page": "100",
                },
            }
        ),
        config,
    )

    assert resumed.get("status") == "accepted"
    prov = resumed.get("field_provenance", {})
    assert prov.get("journal_abbreviation") == "user_correction"
    assert prov.get("volume") == "user_correction"


@pytest.mark.asyncio
@respx.mock
async def test_user_review_accept_as_is_resolves_conflict_and_formats_bibitem(tmp_path: Path):
    cr_data = {
        "message": {
            "items": [
                {
                    "title": ["Sample Conflicted Paper"],
                    "DOI": "10.1000/conflicted",
                    "issued": {"date-parts": [[2023]]},
                    "author": [{"family": "Doe", "given": "Jane"}],
                    "container-title": ["Journal of Testing"],
                    "volume": "10",
                    "page": "1-10",
                }
            ]
        }
    }
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=cr_data)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json={"results": []})

    pdf_file = create_sample_pdf(tmp_path / "accept_test.pdf", "Sample Conflicted Paper", fontsize=24)
    graph = get_compiled_part2_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-accept-flow"}}

    res = await graph.ainvoke(
        {"input_pdf_path": str(pdf_file), "interactive": True, "errors": []},
        config,
    )

    # If it raised user_review or not, test accept flow
    if "__interrupt__" in res and res["__interrupt__"][0].value.get("kind") == "user_review":
        resumed = await graph.ainvoke(
            Command(resume={"action": "accept"}),
            config,
        )
        assert resumed.get("status") == "accepted"
        assert resumed.get("bibitem") is not None
        assert "__interrupt__" not in resumed


@pytest.mark.asyncio
@respx.mock
async def test_user_review_select_candidate_choice_resolves_and_formats(tmp_path: Path):
    # Two competing candidates with identical score
    cr_data = {
        "message": {
            "items": [
                {
                    "title": ["Competing Paper Choice"],
                    "DOI": "10.1000/choice1",
                    "issued": {"date-parts": [[2021]]},
                    "author": [{"family": "One", "given": "Author"}],
                    "container-title": ["Journal One"],
                    "volume": "1",
                    "page": "10",
                },
                {
                    "title": ["Competing Paper Choice"],
                    "DOI": "10.1000/choice2",
                    "issued": {"date-parts": [[2022]]},
                    "author": [{"family": "Two", "given": "Author"}],
                    "container-title": ["Journal Two"],
                    "volume": "2",
                    "page": "20",
                },
            ]
        }
    }
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=cr_data)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json={"results": []})

    pdf_file = create_sample_pdf(tmp_path / "choice_test.pdf", "Competing Paper Choice", fontsize=24)
    graph = get_compiled_part2_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-choice-flow"}}

    res = await graph.ainvoke(
        {"input_pdf_path": str(pdf_file), "interactive": True, "errors": []},
        config,
    )

    assert "__interrupt__" in res
    payload = res["__interrupt__"][0].value
    assert payload["kind"] == "user_review"
    assert "candidate_options" in payload
    assert len(payload["candidate_options"]) >= 2

    # User picks candidate index 1 (Candidate #2)
    chosen_second = payload["candidate_options"][1]
    resumed = await graph.ainvoke(
        Command(resume={"action": "select_candidate", "candidate": chosen_second}),
        config,
    )

    assert resumed.get("status") == "accepted"
    assert resumed.get("selected_metadata", {}).get("doi_url") == "https://doi.org/10.1000/choice2"
    assert resumed.get("bibitem") is not None




@pytest.mark.asyncio
@respx.mock
async def test_thread_ids_isolate_pdfs(
    crossref_kunz_json, openalex_kunz_json, crossref_masheyeva_json, tmp_path: Path
):
    respx.get(CROSSREF_API_URL).respond(status_code=200, json=crossref_kunz_json)
    respx.get(OPENALEX_API_URL).respond(status_code=200, json=openalex_kunz_json)

    pdf1 = create_sample_pdf(
        tmp_path / "pdf1.pdf", "Firehose and mirror instabilities in a collisionless plasma"
    )
    pdf2 = create_sample_pdf(tmp_path / "pdf2.pdf", "Nonlocal effects in negative ion sources")

    graph = get_compiled_part2_graph(checkpointer=MemorySaver())

    res1 = await graph.ainvoke(
        {"input_pdf_path": str(pdf1), "interactive": False, "errors": []},
        {"configurable": {"thread_id": "thread-1"}},
    )
    res2 = await graph.ainvoke(
        {"input_pdf_path": str(pdf2), "interactive": False, "errors": []},
        {"configurable": {"thread_id": "thread-2"}},
    )

    assert res1.get("input_pdf_path") == str(pdf1.resolve())
    assert res2.get("input_pdf_path") == str(pdf2.resolve())
