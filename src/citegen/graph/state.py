import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict


class CitationState(TypedDict, total=False):
    # Part 1 inputs and outputs
    input_title: str
    crossref_candidates: List[Dict[str, Any]]
    openalex_candidates: List[Dict[str, Any]]
    normalized_candidates: List[Dict[str, Any]]
    selected_metadata: Optional[Dict[str, Any]]
    candidate_options: Optional[List[Dict[str, Any]]]
    field_provenance: Dict[str, str]
    missing_fields: List[str]
    conflicts: List[Dict[str, Any]]
    match_status: str  # matched | ambiguous | not_found | provider_error
    review_required: bool
    validation_errors: List[str]
    bibitem: Optional[str]  # draft with placeholder key; final key assigned at batch level
    status: str  # accepted | unresolved | failed | skipped
    errors: Annotated[List[Dict[str, Any]], operator.add]

    # Part 2 additions
    input_pdf_path: Optional[str]
    interactive: Optional[bool]
    extracted_text: Optional[str]
    page_texts: Optional[List[str]]
    needs_ocr: Optional[bool]
    used_ocr: Optional[bool]
    title_candidates: Optional[List[Dict[str, Any]]]
    selected_title: Optional[str]
    title_confirmed: Optional[bool]
    title_attempts: Optional[int]
    review_attempts: Optional[int]
