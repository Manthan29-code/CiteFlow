from typing import Literal

from citegen.graph.state import CitationState


def review_gate(state: CitationState) -> Literal["format_bibitem", "mark_unresolved"]:
    """
    Plain conditional router for Part 1.
    If review is required, match is not matched, or validation failed, route to mark_unresolved.
    Otherwise route to format_bibitem.
    """
    if state.get("review_required"):
        return "mark_unresolved"

    if state.get("match_status") != "matched":
        return "mark_unresolved"

    if state.get("validation_errors"):
        return "mark_unresolved"

    return "format_bibitem"


def validate_input_router(
    state: CitationState,
) -> Literal["fan_out_search", "extract_pdf_text", "mark_unresolved"]:
    """Route after input validation."""
    if state.get("status") == "failed":
        return "mark_unresolved"
    if state.get("input_title") and not state.get("input_pdf_path"):
        return "fan_out_search"
    return "extract_pdf_text"


def route_ocr(state: CitationState) -> Literal["ocr_fallback", "detect_title_candidates"]:
    """Route to OCR if needed and not already performed."""
    if state.get("needs_ocr") and not state.get("used_ocr"):
        return "ocr_fallback"
    return "detect_title_candidates"


def title_gate_router(
    state: CitationState,
) -> Literal["fan_out_search", "confirm_title", "mark_unresolved"]:
    """
    Title gate router:
    - If status failed or skipped -> mark_unresolved
    - If already confirmed -> fan_out_search
    - If high confidence candidate -> auto-accept to fan_out_search
    - If ambiguous/low confidence/none -> confirm_title (interactive)
      or mark_unresolved (non-interactive)
    """
    if state.get("status") in ("failed", "skipped"):
        return "mark_unresolved"

    if state.get("title_confirmed") and state.get("input_title"):
        return "fan_out_search"

    cands = state.get("title_candidates", [])
    is_interactive = state.get("interactive", False)

    if not cands:
        if is_interactive:
            return "confirm_title"
        return "mark_unresolved"

    top = cands[0]
    conf = top.get("confidence", 0.0)

    # High confidence condition: >= 0.85 and clear winner
    has_clear_winner = len(cands) == 1 or (conf - cands[1].get("confidence", 0.0) >= 0.15)
    if conf >= 0.85 and has_clear_winner:
        return "fan_out_search"

    if is_interactive:
        return "confirm_title"

    return "mark_unresolved"


def after_confirm_title_router(
    state: CitationState,
) -> Literal["fan_out_search", "mark_unresolved"]:
    """Route after user responds to confirm_title interrupt."""
    if state.get("status") in ("failed", "skipped"):
        return "mark_unresolved"

    if not state.get("input_title"):
        return "mark_unresolved"

    return "fan_out_search"


def review_gate_part2(
    state: CitationState,
) -> Literal["format_bibitem", "user_review", "confirm_title", "mark_unresolved"]:
    """
    Part 2 review gate router:
    - Accepted records proceed to format_bibitem.
    - Non-interactive mode routes unresolved to mark_unresolved.
    - Interactive mode routes to user_review (or confirm_title for no-match retry).
    """
    if state.get("status") in ("failed", "skipped"):
        return "mark_unresolved"

    match_status = state.get("match_status")
    review_req = state.get("review_required")
    val_errors = state.get("validation_errors", [])
    is_interactive = state.get("interactive", False)
    review_attempts = state.get("review_attempts", 0)
    title_attempts = state.get("title_attempts", 0)
    selected_meta = state.get("selected_metadata")

    # Happy path: matched, no review required, no validation errors, metadata present
    if not review_req and match_status == "matched" and not val_errors and selected_meta:
        return "format_bibitem"

    # Non-interactive mode never interrupts
    if not is_interactive:
        return "mark_unresolved"

    # Interactive mode:
    # 1. If no candidate was found or provider error, retry title if within limit
    if not selected_meta or match_status in ("not_found", "provider_error"):
        if title_attempts < 2:
            return "confirm_title"
        return "mark_unresolved"

    # 2. Metadata exists with conflict/validation issues
    if review_attempts >= 3:
        return "mark_unresolved"

    return "user_review"


def after_user_review_router(
    state: CitationState,
) -> Literal["validate_metadata", "mark_unresolved"]:
    """Route after user responds to user_review interrupt."""
    if state.get("status") in ("failed", "skipped"):
        return "mark_unresolved"
    return "validate_metadata"
