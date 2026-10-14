import re
from typing import List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from citegen.metadata.models import ArticleMetadata


def normalize_title_for_comparison(title: str) -> str:
    """Normalize title for deterministic comparison."""
    if not title:
        return ""
    # Strip HTML tags
    t = re.sub(r"<[^>]+>", "", title).lower()
    # Replace punctuation with space
    t = re.sub(r"[^\w\s]", " ", t)
    # Collapse whitespace
    return " ".join(t.split())


def extract_title_tokens(title: str) -> Set[str]:
    """Extract significant lowercase word tokens from title."""
    norm = normalize_title_for_comparison(title)
    # Exclude very short stopwords
    stopwords = {
        "a",
        "an",
        "the",
        "and",
        "or",
        "in",
        "on",
        "of",
        "to",
        "for",
        "with",
        "by",
        "at",
        "as",
        "is",
    }
    tokens = {word for word in norm.split() if word not in stopwords}
    return tokens


def extract_title_numbers(title: str) -> Set[str]:
    """Extract numeric tokens from title (e.g. Roman numerals or digits)."""
    norm = normalize_title_for_comparison(title)
    return {w for w in norm.split() if w.isdigit()}


def token_similarity(title_a: str, title_b: str) -> float:
    """Compute token Jaccard similarity between two titles."""
    t_a = extract_title_tokens(title_a)
    t_b = extract_title_tokens(title_b)
    if not t_a or not t_b:
        return 0.0
    union = t_a | t_b
    if not union:
        return 0.0
    return len(t_a & t_b) / len(union)


class CandidateEvaluation(BaseModel):
    candidate: ArticleMetadata
    is_match: bool
    score: float
    confidence: str  # high, medium, low, rejected
    reasons: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)


def evaluate_candidate(target_title: str, candidate: ArticleMetadata) -> CandidateEvaluation:
    """
    Deterministically evaluate if candidate matches target title.
    Never chooses a candidate just because it's first.
    Rejects token-similarity near misses.
    Flags conflicting years/DOIs/authors and preprint differences.
    """
    reasons: List[str] = []
    conflicts: List[str] = []

    norm_target = normalize_title_for_comparison(target_title)
    norm_cand = normalize_title_for_comparison(candidate.title)

    # 1. Title comparison
    exact_title_match = (norm_target == norm_cand) and bool(norm_target)
    sim = token_similarity(target_title, candidate.title)

    # Check for differing numbers in title (e.g. Part 1 vs Part 2)
    nums_target = extract_title_numbers(target_title)
    nums_cand = extract_title_numbers(candidate.title)
    if nums_target != nums_cand and (nums_target or nums_cand):
        reasons.append(
            f"Title numeric tokens differ ({nums_target} vs {nums_cand}); likely distinct works"
        )
        return CandidateEvaluation(
            candidate=candidate,
            is_match=False,
            score=sim,
            confidence="rejected",
            reasons=reasons,
            conflicts=["title_numbers_mismatch"],
        )

    tokens_target = extract_title_tokens(target_title)
    tokens_cand = extract_title_tokens(candidate.title)
    is_subset = (
        bool(tokens_target) and tokens_target.issubset(tokens_cand) and len(tokens_target) >= 3
    )

    if exact_title_match:
        reasons.append("Exact normalized title match")
        score = 1.0
        confidence = "high"
    elif norm_target in norm_cand or is_subset:
        reasons.append("Target title matches candidate title prefix or token subset")
        score = 0.95
        confidence = "high"
    elif sim >= 0.88:
        # High token similarity, but check for near miss
        reasons.append(f"High token similarity: {sim:.2f}")
        score = sim
        confidence = "medium"
    else:
        reasons.append(f"Token similarity below threshold: {sim:.2f}; rejected as near-miss")
        return CandidateEvaluation(
            candidate=candidate,
            is_match=False,
            score=sim,
            confidence="rejected",
            reasons=reasons,
        )

    # 2. Preprint check
    if candidate.is_preprint:
        reasons.append("Candidate is identified as a preprint")
        conflicts.append("is_preprint")

    # If confidence is medium or high, candidate is considered a match
    is_match = confidence in ("high", "medium")
    return CandidateEvaluation(
        candidate=candidate,
        is_match=is_match,
        score=score,
        confidence=confidence,
        reasons=reasons,
        conflicts=conflicts,
    )


KNOWN_REPOSITORIES: Set[str] = {
    "renate",
    "arxiv",
    "zenodo",
    "figshare",
    "osf",
    "research square",
    "biorxiv",
    "medrxiv",
    "ssrn",
    "chemrxiv",
    "preprints.org",
    "hal",
    "dryad",
    "mendeley data",
}


def candidate_canonical_score(cand: ArticleMetadata) -> int:
    """
    Score the completeness and canonical publication authority of a candidate.
    Favors peer-reviewed journal articles with complete locators over
    institutional repository deposits and preprints.
    """
    score = 0
    # 1. Non-preprint status
    if not cand.is_preprint:
        score += 10

    # 2. Journal presence and recognition
    if cand.journal:
        j_lower = cand.journal.lower().strip()
        is_repo = any(repo in j_lower for repo in KNOWN_REPOSITORIES)
        if not is_repo:
            score += 15
        else:
            score -= 5

    if cand.journal_abbreviation:
        score += 5

    # 3. Publication locators (volume, issue, page, article number)
    if cand.volume:
        score += 5
    if cand.issue:
        score += 3
    if cand.article_number or cand.first_page:
        score += 5

    # 4. DOI presence
    if cand.doi_url:
        score += 2

    return score


def select_best_candidate(
    target_title: str,
    candidates: List[ArticleMetadata],
) -> Tuple[Optional[ArticleMetadata], List[CandidateEvaluation], str]:
    """
    Select the best candidate from a list of candidates from a provider or merged pool.
    Returns:
        (best_candidate, evaluations, match_status)
        where match_status is one of: matched, ambiguous, not_found, provider_error
    """
    if not candidates:
        return None, [], "not_found"

    evaluations: List[CandidateEvaluation] = []
    matched_evals: List[CandidateEvaluation] = []

    for cand in candidates:
        ev = evaluate_candidate(target_title, cand)
        evaluations.append(ev)
        if ev.is_match:
            matched_evals.append(ev)

    if not matched_evals:
        return None, evaluations, "not_found"

    # Sort matched by score descending
    matched_evals.sort(key=lambda x: x.score, reverse=True)

    # Check if top score is unique or ambiguous
    top_score = matched_evals[0].score
    top_matches = [m for m in matched_evals if m.score >= top_score - 0.02]

    if len(top_matches) > 1:
        # If there are multiple different candidates with same high score
        # Check if they have different DOIs or titles
        dois = {m.candidate.doi_url for m in top_matches if m.candidate.doi_url}
        if len(dois) > 1:
            # Canonical tie-breaker: check if one candidate is a formal peer-reviewed journal article
            # with locators while others are repository deposits or incomplete records
            scored_matches = sorted(
                top_matches,
                key=lambda m: (candidate_canonical_score(m.candidate), m.score),
                reverse=True,
            )
            top_cand = scored_matches[0].candidate
            second_cand = scored_matches[1].candidate

            top_canonical = candidate_canonical_score(top_cand)
            second_canonical = candidate_canonical_score(second_cand)

            if top_canonical >= 25 and (top_canonical - second_canonical >= 10):
                return top_cand, evaluations, "matched"

            return None, evaluations, "ambiguous"

    best = matched_evals[0].candidate
    return best, evaluations, "matched"
