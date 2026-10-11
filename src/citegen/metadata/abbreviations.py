import json
from pathlib import Path
from typing import Dict, Optional, Tuple

_DEFAULT_DATA_PATH = (
    Path(__file__).parent.parent.parent.parent / "data" / "journal_abbreviations.json"
)

_CACHE: Optional[Dict[str, str]] = None


def load_journal_abbreviations(path: Optional[Path] = None) -> Dict[str, str]:
    """Load journal abbreviations from json file."""
    global _CACHE
    file_path = path or _DEFAULT_DATA_PATH
    if _CACHE is not None and path is None:
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
    return mapping


def get_journal_abbreviation(
    journal_name: Optional[str], custom_path: Optional[Path] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Look up journal abbreviation.
    Never invents or truncates an abbreviation.
    Returns:
        (abbreviation, warning_message)
    """
    if not journal_name:
        return None, "No journal name provided"

    clean_name = journal_name.strip()
    mapping = load_journal_abbreviations(custom_path)
    lookup_key = clean_name.lower()

    if lookup_key in mapping:
        return mapping[lookup_key], None

    # Not found in trustworthy source
    return (
        None,
        f"Unknown journal abbreviation for '{clean_name}'; full journal name will be used.",
    )
