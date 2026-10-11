from typing import List, Tuple

from citegen.metadata.models import ArticleMetadata


def validate_metadata(
    metadata: ArticleMetadata,
    conflicts: List[dict] | None = None,
    match_status: str = "matched",
) -> Tuple[List[str], List[str], bool]:
    """
    Validate metadata record.
    Returns:
        (missing_fields, validation_errors, review_required)
    """
    missing_fields: List[str] = []
    validation_errors: List[str] = []
    review_required: bool = False

    # Check missing fields
    if not metadata.title or metadata.title.strip() == "Untitled":
        missing_fields.append("title")
        validation_errors.append("Title is missing or empty")
        review_required = True

    if not metadata.authors:
        missing_fields.append("authors")
        validation_errors.append("Authors list is empty")
        review_required = True
    else:
        for idx, a in enumerate(metadata.authors):
            if a.is_ambiguous:
                validation_errors.append(
                    f"Author #{idx + 1} '{a.original_name}' is ambiguous: {a.warning}"
                )
                review_required = True

    if metadata.year is None:
        missing_fields.append("year")
        validation_errors.append("Publication year is missing")
        review_required = True

    if not metadata.journal:
        missing_fields.append("journal")
        validation_errors.append("Journal name is missing")
        review_required = True

    if not metadata.journal_abbreviation:
        missing_fields.append("journal_abbreviation")

    if not metadata.doi_url:
        missing_fields.append("doi_url")

    if not metadata.volume:
        missing_fields.append("volume")

    if not metadata.issue:
        missing_fields.append("issue")

    if not metadata.first_page:
        missing_fields.append("first_page")

    if not metadata.article_number:
        missing_fields.append("article_number")

    # If neither first_page nor article_number is available
    if not metadata.first_page and not metadata.article_number:
        validation_errors.append(
            "Both first_page and article_number are missing; locator unavailable"
        )

    # If conflicts exist
    if conflicts and len(conflicts) > 0:
        for c in conflicts:
            validation_errors.append(f"Conflict in field '{c.get('field')}': {c.get('reason')}")
        review_required = True

    # If match_status is not matched
    if match_status != "matched":
        validation_errors.append(f"Match status is '{match_status}'")
        review_required = True

    # If candidate is a preprint
    if metadata.is_preprint:
        validation_errors.append("Record is identified as a preprint")
        review_required = True

    return missing_fields, validation_errors, review_required
