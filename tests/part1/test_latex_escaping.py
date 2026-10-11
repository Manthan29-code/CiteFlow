import pytest

from citegen.latex.author_format import escape_latex
from citegen.latex.bibitem import format_bibitem
from citegen.metadata.models import ArticleMetadata, Author

pytestmark = pytest.mark.part1


def test_special_chars_escaping():
    raw = r"Special & % $ # _ { } ~ ^ \ Characters"
    escaped = escape_latex(raw)

    assert r"\&" in escaped
    assert r"\%" in escaped
    assert r"\$" in escaped
    assert r"\#" in escaped
    assert r"\_" in escaped
    assert r"\{" in escaped
    assert r"\}" in escaped
    assert r"\textasciitilde{}" in escaped
    assert r"\textasciicircum{}" in escaped
    assert r"\textbackslash{}" in escaped


def test_malicious_command_neutralized():
    malicious = r"\input{secret.tex}"
    escaped = escape_latex(malicious)
    # Must not contain unescaped \input
    assert not escaped.startswith(r"\input")
    assert r"\textbackslash{}input\{secret.tex\}" in escaped


def test_braces_balanced_in_bibitem():
    meta = ArticleMetadata(
        title=r"Test title with {curly braces} and & % $",
        authors=[Author(surname="O'Connor", given_name="A")],
        year=2024,
        journal=r"Science & Technology",
        journal_abbreviation=r"Sci. \& Technol.",
        doi_url="https://doi.org/10.1000/182_abc",
        volume="1",
        article_number="10",
    )
    bibitem = format_bibitem(meta, citation_key="OConnor2024")

    # Check balanced braces
    open_count = bibitem.count("{")
    close_count = bibitem.count("}")
    assert open_count == close_count
