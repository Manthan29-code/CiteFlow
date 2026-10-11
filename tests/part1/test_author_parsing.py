import pytest

from citegen.metadata.normalize import parse_author_name

pytestmark = pytest.mark.part1


def test_author_parsing_given_family():
    # Matthew W. Kunz
    author = parse_author_name(given="Matthew W.", family="Kunz")
    assert author.surname == "Kunz"
    assert author.given_name == "Matthew"
    assert author.middle_name == "W."
    assert author.original_name == "Matthew W. Kunz"


def test_author_parsing_multiple_given_names():
    # Alexander A Schekochihin
    author = parse_author_name(given="Alexander A", family="Schekochihin")
    assert author.surname == "Schekochihin"
    assert author.given_name == "Alexander"
    assert author.middle_name == "A"


def test_author_parsing_initial_only():
    author = parse_author_name(given="R", family="Masheyeva")
    assert author.surname == "Masheyeva"
    assert author.given_name == "R"
    assert author.middle_name is None


def test_author_parsing_particles_and_compound():
    # Ludwig van Beethoven
    author = parse_author_name(full_name="Ludwig van Beethoven")
    assert author.surname == "van Beethoven"
    assert author.given_name == "Ludwig"
    assert author.original_name == "Ludwig van Beethoven"

    # John von Neumann
    author2 = parse_author_name(full_name="John von Neumann")
    assert author2.surname == "von Neumann"
    assert author2.given_name == "John"


def test_author_parsing_comma_separated():
    author = parse_author_name(full_name="Kunz, Matthew W.")
    assert author.surname == "Kunz"
    assert author.given_name == "Matthew"
    assert author.middle_name == "W."


def test_author_parsing_unsplittable_flagged():
    # Single token name (e.g. Aristotle or Anonymous)
    author = parse_author_name(full_name="Aristotle")
    assert author.surname == "Aristotle"
    assert author.given_name is None
    assert author.is_ambiguous is True
    assert "Unsplittable" in (author.warning or "")
    assert author.original_name == "Aristotle"

    # Institutional author
    author_inst = parse_author_name(full_name="The CMS Collaboration")
    assert author_inst.is_ambiguous is True
    assert "institution" in (author_inst.warning or "").lower()
    assert author_inst.original_name == "The CMS Collaboration"
