import pytest

from citegen.latex.bibitem import format_bibitem
from citegen.metadata.models import ArticleMetadata, Author

pytestmark = pytest.mark.part1


def test_golden_string_kunz2014():
    meta = ArticleMetadata(
        title="Firehose and mirror instabilities in a collisionless plasma",
        authors=[
            Author(surname="Kunz", given_name="M", middle_name="W"),
            Author(surname="Schekochihin", given_name="A", middle_name="A"),
            Author(surname="Stone", given_name="J", middle_name="M"),
        ],
        year=2014,
        journal="Physical Review Letters",
        journal_abbreviation="Phys. Rev. Lett.",
        doi_url="https://doi.org/10.1103/PhysRevLett.112.205003",
        volume="112",
        article_number="205003",
    )

    bibitem = format_bibitem(meta, citation_key="Kunz2014")
    expected = r"\bibitem{Kunz2014} Kunz M W, Schekochihin A A and Stone J M 2014 \textit{Phys. Rev. Lett.} \href{https://doi.org/10.1103/PhysRevLett.112.205003}{\textbf{112} 205003}."
    assert bibitem == expected


def test_golden_string_masheyeva2025():
    # 8 authors
    authors = [Author(surname="Masheyeva", given_name="R")] + [
        Author(surname=f"Author{i}", given_name="A") for i in range(2, 9)
    ]
    meta = ArticleMetadata(
        title="Plasma jets investigation",
        authors=authors,
        year=2025,
        journal="Plasma Sources Science and Technology",
        journal_abbreviation="Plasma Sources Sci. Technol.",
        doi_url="https://doi.org/10.1088/1361-6595/adcb6b",
        volume="34",
        article_number="045017",
    )

    bibitem = format_bibitem(meta, citation_key="Masheyeva2025")
    expected = r"\bibitem{Masheyeva2025} Masheyeva R \textit{et al.} 2025 \textit{Plasma Sources Sci. Technol.} \href{https://doi.org/10.1088/1361-6595/adcb6b}{\textbf{34} 045017}."
    assert bibitem == expected


def test_doi_absent_no_href():
    meta = ArticleMetadata(
        title="Pre-DOI Classic Paper",
        authors=[Author(surname="Maxwell", given_name="J", middle_name="C")],
        year=1865,
        journal="Philosophical Transactions",
        journal_abbreviation="Philos. Trans.",
        volume="155",
        first_page="459",
    )
    bibitem = format_bibitem(meta, citation_key="Maxwell1865")
    assert r"\href" not in bibitem
    assert r"\textbf{155} 459." in bibitem


def test_no_volume_no_locators_fallback():
    meta = ArticleMetadata(
        title="Forthcoming Article",
        authors=[Author(surname="Smith", given_name="J")],
        year=2026,
        journal="Nature",
        doi_url="https://doi.org/10.1038/sample",
    )
    bibitem = format_bibitem(meta, citation_key="Smith2026")
    assert r"\href{https://doi.org/10.1038/sample}{\textit{in press}}." in bibitem
    assert ".." not in bibitem
