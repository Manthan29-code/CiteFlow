import pytest

from citegen.latex.citation_keys import (
    assign_batch_citation_keys,
    disambiguate_keys,
    generate_base_citation_key,
)
from citegen.metadata.models import ArticleMetadata, Author

pytestmark = pytest.mark.part1


def test_base_key_generation():
    meta = ArticleMetadata(
        title="Sample",
        authors=[Author(surname="Kunz", given_name="M")],
        year=2014,
    )
    key = generate_base_citation_key(meta)
    assert key == "Kunz2014"


def test_accents_and_spaces_normalized():
    # Accented surname e.g. Schrödinger
    meta = ArticleMetadata(
        title="Sample",
        authors=[Author(surname="Schrödinger", given_name="E")],
        year=1926,
    )
    key = generate_base_citation_key(meta)
    assert key == "Schrodinger1926"

    # Compound surname with particle & spaces e.g. van Beethoven
    meta2 = ArticleMetadata(
        title="Sample",
        authors=[Author(surname="van Beethoven", given_name="L")],
        year=1800,
    )
    key2 = generate_base_citation_key(meta2)
    assert key2 == "vanBeethoven1800"


def test_duplicates_disambiguation_stable():
    keys = ["Kunz2014", "Stone2015", "Kunz2014", "Kunz2014"]
    resolved = disambiguate_keys(keys)
    assert resolved == ["Kunz2014a", "Stone2015", "Kunz2014b", "Kunz2014c"]


def test_batch_citation_keys_updates_bibitems():
    meta1 = ArticleMetadata(
        title="Paper 1",
        authors=[Author(surname="Kunz", given_name="M")],
        year=2014,
    )
    meta2 = ArticleMetadata(
        title="Paper 2",
        authors=[Author(surname="Kunz", given_name="M")],
        year=2014,
    )
    draft1 = r"\bibitem{DRAFT} Kunz M 2014 Paper 1."
    draft2 = r"\bibitem{DRAFT} Kunz M 2014 Paper 2."

    items = [(meta1, draft1), (meta2, draft2)]
    results = assign_batch_citation_keys(items)

    assert results[0][0] == "Kunz2014a"
    assert results[0][1].startswith(r"\bibitem{Kunz2014a}")

    assert results[1][0] == "Kunz2014b"
    assert results[1][1].startswith(r"\bibitem{Kunz2014b}")
