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


def test_standard_journal_abbreviations_and_punctuation():
    # Journal with colons
    abbrev, warn = get_journal_abbreviation("Journal of Physics D: Applied Physics")
    assert abbrev == "J. Phys. D: Appl. Phys."
    assert warn is None

    # Unpunctuated input maps to canonical abbreviation
    abbrev_unpunc, _ = get_journal_abbreviation("Journal of Physics D Applied Physics")
    assert abbrev_unpunc == "J. Phys. D: Appl. Phys."

    # Other journals from standard list
    assert get_journal_abbreviation("Physics of Fluids B: Plasma Physics")[0] == "Phys. Fluids B"
    assert get_journal_abbreviation("Journal of Physics: Conference Series")[0] == "J. Phys.: Conf. Ser."
    assert get_journal_abbreviation("Surface and Coatings Technology")[0] == "Surf. Coat. Technol."
    assert get_journal_abbreviation("Review of Scientific Instruments")[0] == "Rev. Sci. Instrum."
    assert get_journal_abbreviation("Atomic Data and Nuclear Data Tables")[0] == "At. Data Nucl. Data Tables"

