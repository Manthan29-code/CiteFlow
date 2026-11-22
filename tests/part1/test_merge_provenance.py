import pytest

from citegen.metadata.merge import merge_metadata, records_describe_same_work
from citegen.metadata.models import ArticleMetadata, Author

pytestmark = pytest.mark.part1


def test_merge_complementary_fields_same_work():
    # Crossref has volume & journal; OpenAlex has issue & article_number
    cr = ArticleMetadata(
        title="Sample Work",
        authors=[Author(surname="Smith", given_name="J")],
        year=2021,
        journal="Nature",
        volume="100",
        doi_url="https://doi.org/10.1038/example",
        field_provenance={"journal": "crossref", "volume": "crossref"},
    )
    oa = ArticleMetadata(
        title="Sample Work",
        authors=[Author(surname="Smith", given_name="John")],
        year=2021,
        issue="4",
        article_number="12345",
        doi_url="https://doi.org/10.1038/example",
        field_provenance={"issue": "openalex", "article_number": "openalex"},
    )

    merged, conflicts, prov = merge_metadata(cr, oa)
    assert conflicts == []
    assert merged.volume == "100"
    assert merged.issue == "4"
    assert merged.article_number == "12345"
    assert prov["volume"] == "crossref"
    assert prov["issue"] == "openalex"
    assert prov["article_number"] == "openalex"


def test_conflicts_not_silently_overwritten():
    cr = ArticleMetadata(
        title="Sample Work",
        year=2020,
        doi_url="https://doi.org/10.1038/example",
        volume="10",
    )
    oa = ArticleMetadata(
        title="Sample Work",
        year=2022,  # Conflicting year!
        doi_url="https://doi.org/10.1038/example",
        volume="12",  # Conflicting volume!
    )

    merged, conflicts, prov = merge_metadata(cr, oa)
    assert len(conflicts) >= 2
    conflict_fields = [c["field"] for c in conflicts]
    assert "year" in conflict_fields
    assert "volume" in conflict_fields


def test_different_works_refuse_merge():
    cr = ArticleMetadata(
        title="First Work",
        doi_url="https://doi.org/10.1038/one",
    )
    oa = ArticleMetadata(
        title="Second Work",
        doi_url="https://doi.org/10.1038/two",
    )
    same, reason = records_describe_same_work(cr, oa)
    assert same is False
    assert "Conflicting DOIs" in (reason or "")


def test_journal_and_abbrev_conflict_auto_resolved_via_curated_db():
    # Crossref has colon; OpenAlex lacks colon
    cr = ArticleMetadata(
        title="Transition from single to multiple axial potential structure in expanding helicon plasma",
        authors=[Author(surname="Ghosh", given_name="S.")],
        year=2017,
        journal="Journal of Physics D: Applied Physics",
        journal_abbreviation="J Phys D Appl Phys",  # unpunctuated from Crossref
        doi_url="https://doi.org/10.1088/1361-6463/aa5068",
        field_provenance={"journal": "crossref", "journal_abbreviation": "crossref"},
    )
    oa = ArticleMetadata(
        title="Transition from single to multiple axial potential structure in expanding helicon plasma",
        authors=[Author(surname="Ghosh", given_name="S.")],
        year=2017,
        journal="Journal of Physics D Applied Physics",  # missing colon
        journal_abbreviation="J. Phys. D: Appl. Phys.",
        doi_url="https://doi.org/10.1088/1361-6463/aa5068",
        field_provenance={"journal": "openalex", "journal_abbreviation": "curated_abbreviation"},
    )

    merged, conflicts, prov = merge_metadata(cr, oa)
    # Conflict should be auto-resolved to canonical without prompting the user
    assert len(conflicts) == 0
    assert merged.journal == "Journal of Physics D: Applied Physics"
    assert merged.journal_abbreviation == "J. Phys. D: Appl. Phys."

