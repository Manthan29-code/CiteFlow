import pytest

from citegen.metadata.abbreviations import get_journal_abbreviation

pytestmark = pytest.mark.part1


def test_known_journal_abbreviation():
    abbrev, warn = get_journal_abbreviation("Physical Review Letters")
    assert abbrev == "Phys. Rev. Lett."
    assert warn is None

    abbrev2, warn2 = get_journal_abbreviation("Plasma Sources Science and Technology")
    assert abbrev2 == "Plasma Sources Sci. Technol."
    assert warn2 is None


def test_unknown_journal_never_truncated():
    unknown = "International Journal of Completely Novel Unindexed Physics Research"
    abbrev, warn = get_journal_abbreviation(unknown)
    # Must NOT invent or truncate abbreviation
    assert abbrev is None
    assert warn is not None
    assert "Unknown journal abbreviation" in warn
    assert unknown in warn


def test_none_or_empty_journal():
    abbrev, warn = get_journal_abbreviation(None)
    assert abbrev is None
    assert warn is not None
