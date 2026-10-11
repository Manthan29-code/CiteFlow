import pytest

from citegen.metadata.models import ArticleMetadata
from citegen.metadata.normalize import normalize_crossref, normalize_doi, normalize_openalex

pytestmark = pytest.mark.part1


def test_crossref_normalization(crossref_kunz_json):
    item = crossref_kunz_json["message"]["items"][0]
    meta = normalize_crossref(item)

    assert isinstance(meta, ArticleMetadata)
    assert meta.title == "Firehose and mirror instabilities in a collisionless plasma"
    assert len(meta.authors) == 3
    assert meta.authors[0].surname == "Kunz"
    assert meta.authors[0].given_name == "M" or meta.authors[0].given_name == "M."
    assert meta.year == 2014
    assert meta.journal == "Physical Review Letters"
    assert meta.journal_abbreviation == "Phys. Rev. Lett."
    assert meta.doi_url == "https://doi.org/10.1103/PhysRevLett.112.205003"
    assert meta.volume == "112"
    assert meta.issue == "20"
    # first_page / article_number
    assert meta.article_number == "205003" or meta.first_page == "205003"


def test_openalex_normalization(openalex_kunz_json):
    item = openalex_kunz_json["results"][0]
    meta = normalize_openalex(item)

    assert isinstance(meta, ArticleMetadata)
    assert meta.title == "Firehose and mirror instabilities in a collisionless plasma"
    assert len(meta.authors) == 3
    assert meta.authors[0].surname == "Kunz"
    assert meta.authors[0].given_name == "Matthew"
    assert meta.authors[0].middle_name == "W."
    assert meta.year == 2014
    assert meta.journal == "Physical Review Letters"
    assert meta.journal_abbreviation == "Phys. Rev. Lett."
    assert meta.doi_url == "https://doi.org/10.1103/physrevlett.112.205003"
    assert meta.volume == "112"
    assert meta.issue == "20"


def test_doi_normalization_no_guessing():
    # Only valid DOIs produce doi_url
    clean, url = normalize_doi("10.1103/PhysRevLett.112.205003")
    assert clean == "10.1103/PhysRevLett.112.205003"
    assert url == "https://doi.org/10.1103/PhysRevLett.112.205003"

    clean, url = normalize_doi("https://doi.org/10.1088/1361-6595/adcb6b")
    assert clean == "10.1088/1361-6595/adcb6b"
    assert url == "https://doi.org/10.1088/1361-6595/adcb6b"

    # None or empty produces None
    clean, url = normalize_doi(None)
    assert clean is None
    assert url is None

    clean, url = normalize_doi("")
    assert clean is None
    assert url is None

    clean, url = normalize_doi("not-a-doi")
    assert clean is None
    assert url is None


def test_issue_never_copied_to_volume():
    item = {
        "title": ["Sample"],
        "issue": "5",
        # volume missing
    }
    meta = normalize_crossref(item)
    assert meta.volume is None
    assert meta.issue == "5"


def test_first_page_vs_article_number():
    # Normal page range
    item = {
        "title": ["Sample Page Range"],
        "page": "123-145",
    }
    meta = normalize_crossref(item)
    assert meta.first_page == "123"
    assert meta.article_number is None

    # Distinct article-number
    item_art = {
        "title": ["Sample Article"],
        "article-number": "e012345",
    }
    meta_art = normalize_crossref(item_art)
    assert meta_art.article_number == "e012345"
    assert meta_art.first_page is None


def test_missing_authors_gives_empty_list():
    item = {"title": ["No Author Paper"]}
    meta = normalize_crossref(item)
    assert meta.authors == []

    oa_item = {"title": "No Author Paper", "authorships": []}
    meta_oa = normalize_openalex(oa_item)
    assert meta_oa.authors == []


def test_whitespace_normalization_preserves_content():
    item = {
        "title": ["  Quantum   \n\t Mechanics   and <i>Gravity</i>  "],
    }
    meta = normalize_crossref(item)
    assert meta.title == "Quantum Mechanics and Gravity"
