import json
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

_DEFAULT_DATA_PATH = (
    Path(__file__).parent.parent.parent.parent / "data" / "journal_abbreviations.json"
)

_CACHE: Optional[Dict[str, str]] = None
_CACHE_MTIME: float = 0.0

# Rule 1: Stop words omitted in ISO 4 abbreviations
_STOP_WORDS = {
    "of", "the", "in", "on", "and", "&", "for", "to", "a", "an",
    "at", "by", "with", "from", "into", "upon", "under", "over",
    "between", "through", "about"
}

# Rule 2, 5 & 6: ISO-4 / LTWA (List of Title Word Abbreviations) truncation & contraction mappings
_WORD_ABBREVIATIONS: Dict[str, str] = {
    # Physics & Mechanics
    "physical": "Phys.",
    "physics": "Phys.",
    "physically": "Phys.",
    "mechanic": "Mech.",
    "mechanics": "Mech.",
    "mechanical": "Mech.",
    "nuclear": "Nucl.",
    "quantum": "Quantum",
    "plasma": "Plasma",
    "plasmas": "Plasmas",
    "fluid": "Fluid",
    "fluids": "Fluids",
    "solid": "Solid",
    "solids": "Solids",
    "acoustic": "Acoust.",
    "acoustics": "Acoust.",
    "radiation": "Radiat.",
    "vacuum": "Vacuum",
    "fusion": "Fusion",

    # Chemistry & Materials
    "chemical": "Chem.",
    "chemistry": "Chem.",
    "chemically": "Chem.",
    "material": "Mater.",
    "materials": "Mater.",
    "materialia": "Mater.",
    "molecular": "Mol.",
    "molecule": "Mol.",
    "molecules": "Mol.",
    "atomic": "At.",
    "atom": "At.",
    "atoms": "At.",
    "catalysis": "Catal.",
    "catalytic": "Catal.",
    "polymer": "Polym.",
    "polymers": "Polym.",
    "spectroscopy": "Spectrosc.",
    "spectroscopic": "Spectrosc.",
    "thermodynamic": "Thermodyn.",
    "thermodynamics": "Thermodyn.",

    # Astronomy & Optics
    "astronomy": "Astron.",
    "astronomical": "Astron.",
    "astrophysics": "Astrophys.",
    "astrophysical": "Astrophys.",
    "optics": "Opt.",
    "optical": "Opt.",
    "photonics": "Photonics",
    "photonic": "Photonics",
    "laser": "Laser",
    "lasers": "Lasers",

    # General Academic / Publishing Terms
    "journal": "J.",
    "journals": "J.",
    "review": "Rev.",
    "reviews": "Rev.",
    "letter": "Lett.",
    "letters": "Lett.",
    "report": "Rep.",
    "reports": "Rep.",
    "annal": "Ann.",
    "annals": "Ann.",
    "bulletin": "Bull.",
    "proceeding": "Proc.",
    "proceedings": "Proc.",
    "transaction": "Trans.",
    "transactions": "Trans.",
    "advance": "Adv.",
    "advances": "Adv.",
    "communication": "Commun.",
    "communications": "Commun.",
    "express": "Express",
    "research": "Res.",
    "society": "Soc.",
    "societies": "Soc.",
    "academy": "Acad.",
    "academies": "Acad.",
    "international": "Int.",
    "national": "Natl.",
    "american": "Am.",
    "european": "Eur.",
    "applied": "Appl.",
    "application": "Appl.",
    "applications": "Appl.",
    "technology": "Technol.",
    "technologies": "Technol.",
    "technological": "Technol.",
    "science": "Sci.",
    "sciences": "Sci.",
    "scientific": "Sci.",
    "process": "Process.",
    "processes": "Process.",
    "controlled": "Control.",
    "structure": "Struct.",
    "structural": "Struct.",
    "instrument": "Instrum.",
    "instruments": "Instrum.",
    "instrumentation": "Instrum.",
    "measurement": "Meas.",
    "measurements": "Meas.",

    # Math & Computing
    "mathematics": "Math.",
    "mathematical": "Math.",
    "theory": "Theor.",
    "theoretical": "Theor.",
    "computation": "Comput.",
    "computational": "Comput.",
    "computer": "Comput.",
    "computers": "Comput.",
    "electronic": "Electron.",
    "electronics": "Electron.",
    "electrical": "Electr.",
    "engineering": "Eng.",

    # Life, Earth & Medicine
    "biology": "Biol.",
    "biological": "Biol.",
    "biophysics": "Biophys.",
    "biophysical": "Biophys.",
    "biochemistry": "Biochem.",
    "biochemical": "Biochem.",
    "medicine": "Med.",
    "medical": "Med.",
    "medicinal": "Med.",
    "geology": "Geol.",
    "geological": "Geol.",
    "geophysics": "Geophys.",
    "geophysical": "Geophys.",
    "environment": "Environ.",
    "environmental": "Environ.",
    "nature": "Nature",
}

# Rule 4: Short academic words / roots that stay intact in ISO 4
_INTACT_ACADEMIC_WORDS = {
    "plasma", "plasmas", "fluid", "fluids", "solid", "solids",
    "acta", "laser", "lasers", "cell", "cells", "vacuum", "fusion",
    "wave", "waves", "nano", "matter", "energy", "chaos", "space",
    "earth", "solar", "optics", "quantum", "light"
}


def derive_journal_abbreviation_iso4(journal_name: str) -> Optional[str]:
    """
    Derives standard ISO-4 abbreviation implementing the 7 core international rules:
    1. Drop articles, conjunctions, and prepositions (of, the, in, on, and...).
    2. Truncate recognized words using LTWA mappings.
    3. Single-word titles are never abbreviated (Nature, Science, Lancet).
    4. Short words (<= 5 chars or recognized roots) stay unabbreviated (Acta, Plasmas).
    5. Contractions are applied (National -> Natl.).
    6. Shared word roots map to canonical abbreviations (Chemistry, Chemical -> Chem.).
    7. Acronyms stay uppercase without periods (IEEE, ACM).
    8. Preserves unknown words as capitalized if standard; returns None if unindexed novel title.
    """
    clean = journal_name.strip()

    # Strip leading article 'The ' (e.g. 'The Lancet' -> 'Lancet')
    if clean.lower().startswith("the "):
        clean = clean[4:].strip()

    tokens = clean.split()
    # Rule 3: Single-word titles are never abbreviated
    if len(tokens) <= 1:
        return clean

    res = []
    has_abbrev = False

    for t in tokens:
        # Preserve trailing punctuation like colons (e.g. 'D:')
        colon = ":" if t.endswith(":") else ""
        word = t.rstrip(":,")
        w_lower = word.lower()

        # Rule 1: Drop connector words
        if w_lower in _STOP_WORDS:
            continue

        # Rule 7: Acronyms stay all-caps without periods
        if word.isupper() and len(word) >= 2:
            res.append(word + colon)
            continue

        # Rule 2, 5 & 6: Standard LTWA abbreviation / contraction
        if w_lower in _WORD_ABBREVIATIONS:
            abbrev_val = _WORD_ABBREVIATIONS[w_lower]
            res.append(abbrev_val + colon)
            if abbrev_val != word:
                has_abbrev = True
        # Rule 4: Short / intact academic words (<= 4 chars or recognized roots)
        elif w_lower in _INTACT_ACADEMIC_WORDS or len(word) <= 4:
            res.append(word.capitalize() + colon)
        else:
            # Unindexed or novel non-academic word (e.g. 'completely', 'unindexed')
            # Avoid inventing false abbreviations
            return None

    if res and has_abbrev:
        return " ".join(res)

    return None


def load_journal_abbreviations(path: Optional[Path] = None) -> Dict[str, str]:
    """Load journal abbreviations from json file, reloading dynamically if file modified."""
    global _CACHE, _CACHE_MTIME
    file_path = path or _DEFAULT_DATA_PATH

    mtime = file_path.stat().st_mtime if file_path.exists() else 0.0
    if _CACHE is not None and path is None and mtime == _CACHE_MTIME:
        return _CACHE

    mapping: Dict[str, str] = {}
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Store normalized keys for robust lookup
                    mapping = {k.strip().lower(): v.strip() for k, v in data.items()}
        except Exception:
            mapping = {}

    if path is None:
        _CACHE = mapping
        _CACHE_MTIME = mtime

    return mapping


def get_journal_abbreviation(
    journal_name: Optional[str], custom_path: Optional[Path] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Look up journal abbreviation.
    Tier 1: Check curated JSON database (journal_abbreviations.json).
    Tier 2: Run ISO-4 7-rule algorithmic word-by-word derivation.
    Tier 3: Fallback with warning message if unknown.
    Returns:
        (abbreviation, warning_message)
    """
    if not journal_name:
        return None, "No journal name provided"

    clean_name = journal_name.strip()
    mapping = load_journal_abbreviations(custom_path)
    lookup_key = clean_name.lower()

    # Tier 1: Exact match in curated database
    if lookup_key in mapping:
        return mapping[lookup_key], None

    # Tier 2: Algorithmic ISO-4 word-by-word derivation
    derived = derive_journal_abbreviation_iso4(clean_name)
    if derived:
        return derived, None

    # Tier 3: Unknown journal abbreviation
    return (
        None,
        f"Unknown journal abbreviation for '{clean_name}'; full journal name will be used.",
    )
