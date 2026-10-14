import pytest

from citegen.metadata.matching import (
    evaluate_candidate,
    select_best_candidate,
)
from citegen.metadata.models import ArticleMetadata

pytestmark = pytest.mark.part1


def test_exact_normalized_title_match():
    cand = ArticleMetadata(
        title="Exact Match Title: A Study",
        year=2021,
    )
    ev = evaluate_candidate("exact match title   a study", cand)
    assert ev.is_match is True
    assert ev.confidence == "high"
    assert "Exact normalized title match" in ev.reasons


def test_token_similarity_near_miss_rejected():
    cand = ArticleMetadata(
        title="A completely different topic in biology",
        year=2021,
    )
    ev = evaluate_candidate("A completely different topic in quantum physics", cand)
    assert ev.is_match is False
    assert ev.confidence == "rejected"
    assert any("near-miss" in r or "below threshold" in r for r in ev.reasons)


def test_similar_titles_for_different_works_not_merged():
    # Part 1 vs Part 2
    cand = ArticleMetadata(
        title="Astrophysical dynamo theory: Part 1 The kinematic dynamo",
        year=2020,
    )
    ev = evaluate_candidate(
        "Astrophysical dynamo theory: Part 2 The non-linear regime",
        cand,
    )
    assert ev.is_match is False
    assert "title_numbers_mismatch" in ev.conflicts


def test_first_result_only_never_chosen():
    # List of candidates where the first is unrelated and the second is the exact match
    cands = [
        ArticleMetadata(title="Unrelated Paper", year=2010),
        ArticleMetadata(title="Target Paper Title", year=2020),
    ]
    best, evals, status = select_best_candidate("Target Paper Title", cands)
    assert status == "matched"
    assert best is not None
    assert best.title == "Target Paper Title"


def test_preprint_flagged():
    cand = ArticleMetadata(
        title="Preprint Paper Title",
        year=2023,
        is_preprint=True,
    )
    ev = evaluate_candidate("Preprint Paper Title", cand)
    assert "is_preprint" in ev.conflicts
    assert any("preprint" in r for r in ev.reasons)


def test_ambiguous_matches_result():
    # Two papers with same high match score but different DOIs
    cands = [
        ArticleMetadata(title="Target Paper", year=2020, doi_url="https://doi.org/10.1000/1"),
        ArticleMetadata(title="Target Paper", year=2020, doi_url="https://doi.org/10.1000/2"),
    ]
    best, evals, status = select_best_candidate("Target Paper", cands)
    assert status == "ambiguous"
    assert best is None


def test_canonical_tiebreaker_prefers_journal_over_repository():
    # Candidates with identical title and score, but one is a formal journal article and the others are repository records
    journal_cand = ArticleMetadata(
        title="Experimental and numerical study of plasma",
        year=2025,
        journal="Plasma Sources Science and Technology",
        journal_abbreviation="Plasma Sources Sci. Technol.",
        doi_url="https://doi.org/10.1088/1361-6595/adcb6b",
        volume="34",
        issue="4",
        article_number="045017",
    )
    repo_cand_1 = ArticleMetadata(
        title="Experimental and numerical study of plasma",
        year=2025,
        journal="RENATE",
        doi_url="https://doi.org/10.34657/32095",
    )
    repo_cand_2 = ArticleMetadata(
        title="Experimental and numerical study of plasma",
        year=2025,
        journal="RENATE",
        doi_url="https://doi.org/10.34657/31221",
    )

    cands = [repo_cand_1, journal_cand, repo_cand_2]
    best, evals, status = select_best_candidate("Experimental and numerical study of plasma", cands)

    assert status == "matched"
    assert best is not None
    assert best.doi_url == "https://doi.org/10.1088/1361-6595/adcb6b"
    assert best.journal == "Plasma Sources Science and Technology"

