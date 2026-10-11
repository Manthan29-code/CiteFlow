import pytest

from citegen.latex.author_format import format_author_list, format_single_author
from citegen.metadata.models import Author

pytestmark = pytest.mark.part1


def test_single_author():
    a = Author(surname="Kunz", given_name="M", middle_name="W")
    assert format_single_author(a) == "Kunz M W"
    assert format_author_list([a]) == "Kunz M W"


def test_two_authors():
    a1 = Author(surname="Kunz", given_name="Matthew", middle_name="W.")
    a2 = Author(surname="Stone", given_name="James", middle_name="M.")
    res = format_author_list([a1, a2])
    assert res == "Kunz M W and Stone J M"


def test_three_authors():
    a1 = Author(surname="Kunz", given_name="Matthew", middle_name="W")
    a2 = Author(surname="Schekochihin", given_name="Alexander", middle_name="A")
    a3 = Author(surname="Stone", given_name="James", middle_name="M")
    res = format_author_list([a1, a2, a3])
    assert res == "Kunz M W, Schekochihin A A and Stone J M"


def test_no_middle_name():
    a = Author(surname="Masheyeva", given_name="R")
    assert format_single_author(a) == "Masheyeva R"


def test_exactly_seven_authors():
    authors = [Author(surname=f"Surname{i}", given_name=f"Given{i}") for i in range(1, 8)]
    res = format_author_list(authors)
    # Lists all with and before 7th
    assert "\\textit{et al.}" not in res
    assert "Surname1 G" in res
    assert "and Surname7 G" in res


def test_exactly_eight_authors():
    authors = [Author(surname=f"Surname{i}", given_name=f"Given{i}") for i in range(1, 9)]
    res = format_author_list(authors)
    assert res == "Surname1 G \\textit{et al.}"
