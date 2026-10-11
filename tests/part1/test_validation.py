import pytest

from citegen.metadata.models import ArticleMetadata, Author
from citegen.metadata.validate import validate_metadata

pytestmark = pytest.mark.part1


def test_missing_fields_flags():
    meta = ArticleMetadata(
        title="Complete Title",
        authors=[Author(surname="Doe", given_name="John")],
        # Missing year, doi_url, volume, issue, first_page, article_number
    )
    missing, errors, req = validate_metadata(meta)

    assert "year" in missing
    assert "doi_url" in missing
    assert "volume" in missing
    assert "issue" in missing
    assert "first_page" in missing
    assert "article_number" in missing
    assert "journal" in missing
    assert req is True  # missing year and journal requires review


def test_unresolved_not_marked_accepted():
    meta = ArticleMetadata(
        title="Sample",
        authors=[Author(surname="Smith", given_name="A")],
        year=2020,
        journal="Nature",
    )
    # When match_status is not matched
    missing, errors, req = validate_metadata(meta, match_status="ambiguous")
    assert req is True
    assert any("ambiguous" in e for e in errors)


def test_conflict_requires_review():
    meta = ArticleMetadata(
        title="Sample",
        authors=[Author(surname="Smith", given_name="A")],
        year=2020,
        journal="Nature",
    )
    conflicts = [{"field": "year", "reason": "Year disagreement (2020 vs 2021)"}]
    missing, errors, req = validate_metadata(meta, conflicts=conflicts)
    assert req is True
    assert any("Conflict in field 'year'" in e for e in errors)
