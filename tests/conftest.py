import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def crossref_kunz_json() -> dict:
    with open(FIXTURES_DIR / "crossref_kunz2014.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def openalex_kunz_json() -> dict:
    with open(FIXTURES_DIR / "openalex_kunz2014.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def crossref_masheyeva_json() -> dict:
    with open(FIXTURES_DIR / "crossref_masheyeva2025.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def crossref_similar_titles_json() -> dict:
    with open(FIXTURES_DIR / "crossref_similar_titles.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def crossref_preprint_pair_json() -> dict:
    with open(FIXTURES_DIR / "crossref_preprint_pair.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def reset_settings(monkeypatch):
    from citegen.config import settings

    monkeypatch.setattr(settings, "openalex_api_key", None)

