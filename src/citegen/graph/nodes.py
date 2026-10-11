from typing import Any, Dict

from langgraph.types import interrupt

from citegen.config import settings
from citegen.graph.state import CitationState
from citegen.latex.bibitem import format_bibitem as render_bibitem
from citegen.metadata.matching import select_best_candidate
from citegen.metadata.merge import merge_metadata
from citegen.metadata.models import ArticleMetadata
from citegen.metadata.validate import validate_metadata as run_validate
from citegen.pdf.input_validation import PdfValidationError, validate_pdf_input
from citegen.pdf.ocr import ocr_pdf_pages
from citegen.pdf.text_extractor import extract_pdf_text
from citegen.pdf.title_detector import detect_title_candidates
from citegen.providers.crossref import fetch_crossref_candidates
from citegen.providers.openalex import fetch_openalex_candidates

# =========================================================================
# Part 2: PDF Front-Half Nodes
# =========================================================================


def validate_input_node(state: CitationState) -> Dict[str, Any]:
    """Validate input: either an input title or a PDF file."""
    if state.get("input_title"):
        clean_title = state["input_title"].strip()
        if not clean_title:
            return {
                "status": "failed",
                "validation_errors": ["Input title cannot be empty"],
                "errors": [{"type": "input_validation", "message": "Input title cannot be empty"}],
            }
        return {
            "status": "validating",
            "input_title": clean_title,
            "title_confirmed": True,
        }

    pdf_path = state.get("input_pdf_path")
    if not pdf_path:
        return {
            "status": "failed",
            "validation_errors": ["No input title or PDF path provided"],
            "errors": [{"type": "input_validation", "message": "No input title or PDF path provided"}],
        }

    try:
        validate_pdf_input(pdf_path)
        return {
            "status": "validating",
        }
    except PdfValidationError as exc:
        return {
            "status": "failed",
            "validation_errors": [str(exc)],
            "errors": [{"type": "pdf_validation", "message": str(exc)}],
        }
    except Exception as exc:
        return {
            "status": "failed",
            "validation_errors": [f"Unexpected PDF error: {exc}"],
            "errors": [{"type": "pdf_validation", "message": str(exc)}],
        }


def extract_pdf_text_node(state: CitationState) -> Dict[str, Any]:
    """Extract text page by page from PDF and check if OCR is needed."""
    pdf_path = state.get("input_pdf_path")
    assert pdf_path is not None

    res = extract_pdf_text(pdf_path)
    return {
        "page_texts": res.get("page_texts", []),
        "extracted_text": res.get("extracted_text", ""),
        "needs_ocr": res.get("needs_ocr", False),
        "used_ocr": False,
    }


def ocr_fallback_node(state: CitationState) -> Dict[str, Any]:
    """Run OCR on PDF if enabled when text extraction is inadequate."""
    pdf_path = state.get("input_pdf_path")
    assert pdf_path is not None

    if not settings.ocr_enabled:
        return {
            "used_ocr": True,
            "needs_ocr": False,
            "errors": [{"type": "ocr_disabled", "message": "OCR is disabled in settings"}],
        }

    ocr_res = ocr_pdf_pages(pdf_path)
    if ocr_res.get("success"):
        return {
            "page_texts": ocr_res.get("page_texts", []),
            "extracted_text": ocr_res.get("extracted_text", ""),
            "used_ocr": True,
            "needs_ocr": False,
        }
    else:
        err_msg = ocr_res.get("error", "OCR failed")
        return {
            "used_ocr": True,
            "needs_ocr": False,
            "errors": [{"type": "ocr_failure", "message": err_msg}],
        }


async def detect_title_candidates_node(state: CitationState) -> Dict[str, Any]:
    """Detect title candidates using GROBID and PyMuPDF heuristics."""
    pdf_path = state.get("input_pdf_path")
    assert pdf_path is not None

    fallback_text = state.get("extracted_text")
    candidates = await detect_title_candidates(
        pdf_path=pdf_path,
        fallback_text=fallback_text,
    )

    if not candidates:
        return {
            "title_candidates": [],
            "selected_title": None,
            "title_attempts": state.get("title_attempts", 0),
        }

    top_cand = candidates[0]
    top_title = top_cand.get("title")

    # If high confidence (>= 0.85), auto-select as input_title
    if top_cand.get("confidence", 0.0) >= 0.85:
        return {
            "title_candidates": candidates,
            "selected_title": top_title,
            "input_title": top_title,
            "title_confirmed": True,
            "title_attempts": state.get("title_attempts", 0),
        }

    return {
        "title_candidates": candidates,
        "selected_title": top_title,
        "title_attempts": state.get("title_attempts", 0),
    }


def confirm_title_node(state: CitationState) -> Dict[str, Any]:
    """
    Interrupt node for user title confirmation.
    Side-effect free; re-executed from top on resume.
    """
    payload = {
        "kind": "confirm_title",
        "pdf_path": state.get("input_pdf_path"),
        "candidates": state.get("title_candidates", []),
        "selected_title": state.get("selected_title"),
        "attempts": state.get("title_attempts", 0),
    }

    user_response = interrupt(payload)

    # Process response
    if isinstance(user_response, dict):
        action = user_response.get("action")
        if action == "skip":
            return {
                "status": "skipped",
                "validation_errors": ["User skipped title confirmation"],
            }
        chosen = user_response.get("title", "")
    elif isinstance(user_response, str):
        if user_response.strip().lower() == "skip":
            return {
                "status": "skipped",
                "validation_errors": ["User skipped title confirmation"],
            }
        chosen = user_response.strip()
    else:
        chosen = str(user_response or "")

    return {
        "input_title": chosen,
        "selected_title": chosen,
        "title_confirmed": True,
        "title_attempts": state.get("title_attempts", 0) + 1,
    }


def user_review_node(state: CitationState) -> Dict[str, Any]:
    """
    Interrupt node for user metadata review and corrections.
    Side-effect free; re-executed from top on resume.
    """
    payload = {
        "kind": "user_review",
        "pdf_path": state.get("input_pdf_path"),
        "title": state.get("input_title"),
        "selected_metadata": state.get("selected_metadata"),
        "field_provenance": state.get("field_provenance", {}),
        "conflicts": state.get("conflicts", []),
        "missing_fields": state.get("missing_fields", []),
        "validation_errors": state.get("validation_errors", []),
        "match_status": state.get("match_status"),
        "attempts": state.get("review_attempts", 0),
    }

    user_response = interrupt(payload)

    curr_attempts = state.get("review_attempts", 0) + 1

    if isinstance(user_response, dict):
        action = user_response.get("action")
        if action == "skip":
            return {
                "status": "skipped",
                "validation_errors": ["User skipped metadata review"],
            }
        if action == "accept":
            return {
                "review_required": False,
                "validation_errors": [],
                "conflicts": [],
                "match_status": "matched",
                "status": "accepted",
                "review_attempts": curr_attempts,
            }

        # User submitted field edits
        edits = user_response.get("edits") or {
            k: v for k, v in user_response.items() if k not in ("action",)
        }
        current_meta = dict(state.get("selected_metadata") or {})
        current_meta.update(edits)

        prov = dict(state.get("field_provenance") or {})
        for field in edits:
            prov[field] = "user_correction"

        return {
            "selected_metadata": current_meta,
            "field_provenance": prov,
            "review_attempts": curr_attempts,
            "review_required": False,
        }

    if isinstance(user_response, str):
        cleaned = user_response.strip().lower()
        if cleaned in ("s", "skip"):
            return {
                "status": "skipped",
                "validation_errors": ["User skipped metadata review"],
            }
        if cleaned in ("a", "accept"):
            return {
                "review_required": False,
                "validation_errors": [],
                "conflicts": [],
                "match_status": "matched",
                "status": "accepted",
                "review_attempts": curr_attempts,
            }

    return {
        "review_attempts": curr_attempts,
    }


# =========================================================================
# Part 1: Provider Search, Match, Merge, Validate, Format Nodes
# =========================================================================


async def fan_out_search(state: CitationState) -> Dict[str, Any]:
    """Passthrough fan-out node."""
    return {}


async def crossref_search(state: CitationState) -> Dict[str, Any]:
    """Search Crossref asynchronously and failure-isolated."""
    title = state.get("input_title", "")
    res = await fetch_crossref_candidates(title)
    updates: Dict[str, Any] = {
        "crossref_candidates": res.get("candidates", []),
    }
    if res.get("error"):
        updates["errors"] = [res["error"]]
    return updates


async def openalex_search(state: CitationState) -> Dict[str, Any]:
    """Search OpenAlex asynchronously and failure-isolated."""
    title = state.get("input_title", "")
    res = await fetch_openalex_candidates(title)
    updates: Dict[str, Any] = {
        "openalex_candidates": res.get("candidates", []),
    }
    if res.get("error"):
        updates["errors"] = [res["error"]]
    return updates


def normalize_provider_results(state: CitationState) -> Dict[str, Any]:
    """
    Fan-in join node: collects results from both provider nodes.
    Determines if both failed with provider_error.
    """
    cr_raw = state.get("crossref_candidates", [])
    oa_raw = state.get("openalex_candidates", [])
    errors = state.get("errors", [])

    cr_cands = [ArticleMetadata(**c) for c in cr_raw]
    oa_cands = [ArticleMetadata(**c) for c in oa_raw]
    all_normalized = cr_cands + oa_cands

    # Check if both providers errored
    has_cr_error = any(e.get("provider") == "crossref" for e in errors)
    has_oa_error = any(e.get("provider") == "openalex" for e in errors)

    if has_cr_error and has_oa_error and not all_normalized:
        return {
            "normalized_candidates": [],
            "match_status": "provider_error",
            "review_required": True,
            "status": "unresolved",
            "validation_errors": ["Both providers failed (network or rate limit error)"],
        }

    return {
        "normalized_candidates": [c.model_dump() for c in all_normalized],
    }


def match_and_merge_records(state: CitationState) -> Dict[str, Any]:
    """
    Select best candidates from each provider and merge if matching the same work.
    """
    if state.get("match_status") == "provider_error":
        return {
            "selected_metadata": None,
            "status": "unresolved",
            "review_required": True,
        }

    title = state.get("input_title", "")
    cr_raw = state.get("crossref_candidates", [])
    oa_raw = state.get("openalex_candidates", [])

    cr_cands = [ArticleMetadata(**c) for c in cr_raw]
    oa_cands = [ArticleMetadata(**c) for c in oa_raw]

    best_cr, evals_cr, status_cr = select_best_candidate(title, cr_cands)
    best_oa, evals_oa, status_oa = select_best_candidate(title, oa_cands)

    if status_cr == "ambiguous" or status_oa == "ambiguous":
        return {
            "selected_metadata": (best_cr or best_oa).model_dump()
            if (best_cr or best_oa)
            else None,
            "match_status": "ambiguous",
            "review_required": True,
            "status": "unresolved",
            "conflicts": [{"reason": "Multiple ambiguous candidates found"}],
        }

    if not best_cr and not best_oa:
        return {
            "selected_metadata": None,
            "match_status": "not_found",
            "review_required": True,
            "status": "unresolved",
            "conflicts": [],
        }

    # If both found a match, merge them
    if best_cr and best_oa:
        merged, conflicts, provenance = merge_metadata(best_cr, best_oa)
        has_critical_conflict = any(
            c.get("field") in ("work_identity", "is_preprint", "doi_url", "year") for c in conflicts
        )
        return {
            "selected_metadata": merged.model_dump(),
            "field_provenance": provenance,
            "conflicts": conflicts,
            "match_status": "ambiguous" if has_critical_conflict else "matched",
            "review_required": bool(has_critical_conflict),
        }

    # Only one provider returned a match
    chosen = best_cr or best_oa
    assert chosen is not None
    return {
        "selected_metadata": chosen.model_dump(),
        "field_provenance": chosen.field_provenance,
        "conflicts": [],
        "match_status": "matched",
        "review_required": False,
    }


def validate_metadata_node(state: CitationState) -> Dict[str, Any]:
    """Validate selected metadata."""
    sel = state.get("selected_metadata")
    conflicts = state.get("conflicts", [])
    match_status = state.get("match_status", "matched")

    if not sel:
        return {
            "missing_fields": ["metadata"],
            "validation_errors": ["No metadata selected"],
            "review_required": True,
            "status": "unresolved",
        }

    meta = ArticleMetadata(**sel)
    missing, val_errors, review_req = run_validate(
        meta, conflicts=conflicts, match_status=match_status
    )

    is_unresolved = review_req or (match_status != "matched") or bool(val_errors)
    return {
        "missing_fields": missing,
        "validation_errors": val_errors,
        "review_required": is_unresolved,
        "status": "unresolved" if is_unresolved else "accepted",
    }


def mark_unresolved(state: CitationState) -> Dict[str, Any]:
    """Mark state as unresolved."""
    return {
        "status": "unresolved",
        "review_required": True,
    }


def format_bibitem_node(state: CitationState) -> Dict[str, Any]:
    """Format accepted record into draft bibitem."""
    sel = state.get("selected_metadata")
    if not sel:
        return {
            "status": "unresolved",
            "review_required": True,
        }
    meta = ArticleMetadata(**sel)
    draft_bibitem = render_bibitem(meta, citation_key="DRAFT")
    return {
        "bibitem": draft_bibitem,
        "status": "accepted",
    }
