from typing import Any, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from citegen.graph.nodes import (
    confirm_title_node,
    crossref_search,
    detect_title_candidates_node,
    extract_pdf_text_node,
    fan_out_search,
    format_bibitem_node,
    mark_unresolved,
    match_and_merge_records,
    normalize_provider_results,
    ocr_fallback_node,
    openalex_search,
    user_review_node,
    validate_input_node,
    validate_metadata_node,
)
from citegen.graph.routing import (
    after_confirm_title_router,
    after_user_review_router,
    review_gate,
    review_gate_part2,
    route_ocr,
    title_gate_router,
    validate_input_router,
)
from citegen.graph.state import CitationState


def build_part1_graph() -> StateGraph:
    """Build the Part 1 StateGraph workflow with parallel provider lookup."""
    builder = StateGraph(CitationState)

    # Add nodes
    builder.add_node("fan_out_search", fan_out_search)
    builder.add_node("crossref_search", crossref_search)
    builder.add_node("openalex_search", openalex_search)
    builder.add_node("normalize_provider_results", normalize_provider_results)
    builder.add_node("match_and_merge_records", match_and_merge_records)
    builder.add_node("validate_metadata", validate_metadata_node)
    builder.add_node("format_bibitem", format_bibitem_node)
    builder.add_node("mark_unresolved", mark_unresolved)

    # Static fan-out edges from START to fan_out_search, then parallel to providers
    builder.add_edge(START, "fan_out_search")
    builder.add_edge("fan_out_search", "crossref_search")
    builder.add_edge("fan_out_search", "openalex_search")

    # Static fan-in join edge to normalize_provider_results
    builder.add_edge(["crossref_search", "openalex_search"], "normalize_provider_results")

    # Linear processing pipeline
    builder.add_edge("normalize_provider_results", "match_and_merge_records")
    builder.add_edge("match_and_merge_records", "validate_metadata")

    # Review gate router
    builder.add_conditional_edges(
        "validate_metadata",
        review_gate,
        {
            "format_bibitem": "format_bibitem",
            "mark_unresolved": "mark_unresolved",
        },
    )

    builder.add_edge("format_bibitem", END)
    builder.add_edge("mark_unresolved", END)

    return builder


def get_compiled_part1_graph():
    """Compile and return the Part 1 graph."""
    builder = build_part1_graph()
    return builder.compile()


def build_part2_graph() -> StateGraph:
    """
    Build the Part 2 StateGraph workflow extending Part 1 with PDF
    and human-in-the-loop gates.
    """
    builder = StateGraph(CitationState)

    # PDF front-half nodes
    builder.add_node("validate_input", validate_input_node)
    builder.add_node("extract_pdf_text", extract_pdf_text_node)
    builder.add_node("ocr_fallback", ocr_fallback_node)
    builder.add_node("detect_title_candidates", detect_title_candidates_node)
    builder.add_node("confirm_title", confirm_title_node)

    # Part 1 nodes
    builder.add_node("fan_out_search", fan_out_search)
    builder.add_node("crossref_search", crossref_search)
    builder.add_node("openalex_search", openalex_search)
    builder.add_node("normalize_provider_results", normalize_provider_results)
    builder.add_node("match_and_merge_records", match_and_merge_records)
    builder.add_node("validate_metadata", validate_metadata_node)
    builder.add_node("format_bibitem", format_bibitem_node)
    builder.add_node("mark_unresolved", mark_unresolved)

    # Part 2 human review node
    builder.add_node("user_review", user_review_node)

    # PDF input validation edge
    builder.add_edge(START, "validate_input")
    builder.add_conditional_edges(
        "validate_input",
        validate_input_router,
        {
            "extract_pdf_text": "extract_pdf_text",
            "mark_unresolved": "mark_unresolved",
        },
    )

    # Text extraction -> OCR if needed -> title detection
    builder.add_conditional_edges(
        "extract_pdf_text",
        route_ocr,
        {
            "ocr_fallback": "ocr_fallback",
            "detect_title_candidates": "detect_title_candidates",
        },
    )
    builder.add_edge("ocr_fallback", "detect_title_candidates")

    # Title gate
    builder.add_conditional_edges(
        "detect_title_candidates",
        title_gate_router,
        {
            "fan_out_search": "fan_out_search",
            "confirm_title": "confirm_title",
            "mark_unresolved": "mark_unresolved",
        },
    )

    # Confirm title interrupt resumption
    builder.add_conditional_edges(
        "confirm_title",
        after_confirm_title_router,
        {
            "fan_out_search": "fan_out_search",
            "mark_unresolved": "mark_unresolved",
        },
    )

    # Part 1 parallel search edges
    builder.add_edge("fan_out_search", "crossref_search")
    builder.add_edge("fan_out_search", "openalex_search")
    builder.add_edge(["crossref_search", "openalex_search"], "normalize_provider_results")
    builder.add_edge("normalize_provider_results", "match_and_merge_records")
    builder.add_edge("match_and_merge_records", "validate_metadata")

    # Part 2 review gate
    builder.add_conditional_edges(
        "validate_metadata",
        review_gate_part2,
        {
            "format_bibitem": "format_bibitem",
            "user_review": "user_review",
            "confirm_title": "confirm_title",
            "mark_unresolved": "mark_unresolved",
        },
    )

    # User review loop back to validation or unresolved
    builder.add_conditional_edges(
        "user_review",
        after_user_review_router,
        {
            "validate_metadata": "validate_metadata",
            "mark_unresolved": "mark_unresolved",
        },
    )

    builder.add_edge("format_bibitem", END)
    builder.add_edge("mark_unresolved", END)

    return builder


def get_compiled_part2_graph(checkpointer: Optional[Any] = None):
    """Compile and return the Part 2 graph with checkpointer."""
    if checkpointer is None:
        checkpointer = MemorySaver()
    builder = build_part2_graph()
    return builder.compile(checkpointer=checkpointer)
