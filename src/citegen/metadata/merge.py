from typing import Any, Dict, List, Optional, Tuple

from citegen.metadata.matching import normalize_title_for_comparison
from citegen.metadata.models import ArticleMetadata, Author


def records_describe_same_work(
    rec_a: ArticleMetadata, rec_b: ArticleMetadata
) -> Tuple[bool, Optional[str]]:
    """
    Check if two records have sufficient evidence to describe the same work.
    """
    # 1. DOI check
    if rec_a.doi_url and rec_b.doi_url:
        if rec_a.doi_url.lower() != rec_b.doi_url.lower():
            return False, f"Conflicting DOIs: {rec_a.doi_url} vs {rec_b.doi_url}"
        return True, None

    # 2. Exact title comparison
    norm_a = normalize_title_for_comparison(rec_a.title)
    norm_b = normalize_title_for_comparison(rec_b.title)
    if norm_a and norm_b and norm_a == norm_b:
        # Check years if both present
        if rec_a.year and rec_b.year and abs(rec_a.year - rec_b.year) > 1:
            return False, f"Titles match but years conflict ({rec_a.year} vs {rec_b.year})"
        return True, None

    return False, "Insufficient evidence that records describe the same work"


def merge_authors(
    authors_a: List[Author],
    authors_b: List[Author],
    prov_a: str,
    prov_b: str,
) -> Tuple[List[Author], str, Optional[Dict[str, Any]]]:
    """Merge author lists if compatible, preferring richer given names."""
    if not authors_a and not authors_b:
        return [], "", None
    if not authors_a:
        return authors_b, prov_b, None
    if not authors_b:
        return authors_a, prov_a, None

    if len(authors_a) != len(authors_b):
        conflict = {
            "field": "authors",
            "reason": f"Author counts differ ({len(authors_a)} from {prov_a} vs {len(authors_b)} from {prov_b})",
            prov_a: [a.model_dump_for_display() for a in authors_a],
            prov_b: [b.model_dump_for_display() for b in authors_b],
        }
        return authors_a, prov_a, conflict

    # Compare surnames
    merged: List[Author] = []
    has_conflict = False
    for a, b in zip(authors_a, authors_b):
        s_a = (a.surname or "").lower()
        s_b = (b.surname or "").lower()
        if s_a != s_b and s_a and s_b:
            has_conflict = True
            break
        # Pick the one with longer given name
        len_g_a = len(a.given_name or "")
        len_g_b = len(b.given_name or "")
        if len_g_b > len_g_a:
            merged.append(b)
        else:
            merged.append(a)

    if has_conflict:
        conflict = {
            "field": "authors",
            "reason": "Author surnames mismatch",
            prov_a: [a.model_dump_for_display() for a in authors_a],
            prov_b: [b.model_dump_for_display() for b in authors_b],
        }
        return authors_a, prov_a, conflict

    return merged, f"{prov_a}+{prov_b}", None


def merge_metadata(
    rec_crossref: Optional[ArticleMetadata],
    rec_openalex: Optional[ArticleMetadata],
) -> Tuple[ArticleMetadata, List[Dict[str, Any]], Dict[str, str]]:
    """
    Merge records from Crossref and OpenAlex.
    Preserves per-field provenance and records conflicts without silent overwriting.
    """
    conflicts: List[Dict[str, Any]] = []
    field_provenance: Dict[str, str] = {}

    if rec_crossref is None and rec_openalex is None:
        raise ValueError("Cannot merge two None records")

    if rec_crossref is None and rec_openalex is not None:
        return rec_openalex, [], rec_openalex.field_provenance

    if rec_openalex is None and rec_crossref is not None:
        return rec_crossref, [], rec_crossref.field_provenance

    # Both are present; check if they describe the same work
    same_work, reason = records_describe_same_work(rec_crossref, rec_openalex)
    if not same_work:
        conflicts.append(
            {
                "field": "work_identity",
                "reason": reason or "Records do not describe the same work",
                "crossref_title": rec_crossref.title,
                "openalex_title": rec_openalex.title,
                "candidate_options": [rec_crossref.model_dump(), rec_openalex.model_dump()],
            }
        )
        # Keep Crossref as primary but flag conflict
        return rec_crossref, conflicts, rec_crossref.field_provenance

    # Preprint vs Published conflict
    if rec_crossref.is_preprint != rec_openalex.is_preprint:
        conflicts.append(
            {
                "field": "is_preprint",
                "reason": "Preprint status disagreement between Crossref and OpenAlex",
                "crossref_preprint": rec_crossref.is_preprint,
                "openalex_preprint": rec_openalex.is_preprint,
            }
        )

    # Title
    title = rec_crossref.title
    field_provenance["title"] = "crossref"
    if normalize_title_for_comparison(rec_crossref.title) != normalize_title_for_comparison(
        rec_openalex.title
    ):
        conflicts.append(
            {
                "field": "title",
                "reason": "Title string disagreement",
                "crossref": rec_crossref.title,
                "openalex": rec_openalex.title,
            }
        )

    # Authors
    authors, auth_prov, auth_conflict = merge_authors(
        rec_crossref.authors, rec_openalex.authors, "crossref", "openalex"
    )
    if auth_conflict:
        conflicts.append(auth_conflict)
    field_provenance["authors"] = auth_prov or "crossref"

    # Year
    year = rec_crossref.year or rec_openalex.year
    if rec_crossref.year and rec_openalex.year:
        if rec_crossref.year == rec_openalex.year:
            year = rec_crossref.year
            field_provenance["year"] = "crossref"
        else:
            conflicts.append(
                {
                    "field": "year",
                    "reason": f"Year disagreement ({rec_crossref.year} vs {rec_openalex.year})",
                    "crossref": rec_crossref.year,
                    "openalex": rec_openalex.year,
                }
            )
            year = rec_crossref.year
            field_provenance["year"] = "crossref"
    elif rec_crossref.year:
        year = rec_crossref.year
        field_provenance["year"] = "crossref"
    elif rec_openalex.year:
        year = rec_openalex.year
        field_provenance["year"] = "openalex"

    # Journal
    journal = rec_crossref.journal or rec_openalex.journal
    if rec_crossref.journal and rec_openalex.journal:
        j_cr = rec_crossref.journal.strip()
        j_oa = rec_openalex.journal.strip()
        if j_cr.lower() == j_oa.lower():
            journal = j_cr
            field_provenance["journal"] = "crossref"
        else:
            from citegen.metadata.abbreviations import (
                get_canonical_journal_info,
                normalize_journal_name,
            )

            canon_cr, _ = get_canonical_journal_info(j_cr)
            canon_oa, _ = get_canonical_journal_info(j_oa)
            norm_cr = normalize_journal_name(j_cr)
            norm_oa = normalize_journal_name(j_oa)

            if canon_cr and (canon_cr == canon_oa or norm_cr == norm_oa or not canon_oa):
                # Automatically resolved via curated standard journal database
                journal = canon_cr
                field_provenance["journal"] = "curated_database"
            elif canon_oa and (not canon_cr or norm_cr == norm_oa):
                # Automatically resolved via curated standard journal database
                journal = canon_oa
                field_provenance["journal"] = "curated_database"
            elif norm_cr == norm_oa:
                # Same journal differing only by punctuation or whitespace formatting
                journal = j_cr if len(j_cr) >= len(j_oa) else j_oa
                field_provenance["journal"] = "crossref"
            else:
                conflicts.append(
                    {
                        "field": "journal",
                        "reason": f"Journal disagreement ('{j_cr}' vs '{j_oa}')",
                        "crossref": j_cr,
                        "openalex": j_oa,
                    }
                )
                journal = j_cr
                field_provenance["journal"] = "crossref"
    elif rec_crossref.journal:
        journal = rec_crossref.journal
        field_provenance["journal"] = "crossref"
    elif rec_openalex.journal:
        journal = rec_openalex.journal
        field_provenance["journal"] = "openalex"

    # Journal Abbreviation
    from citegen.metadata.abbreviations import (
        get_journal_abbreviation,
        normalize_journal_name,
    )

    # 1. Authoritative standard abbreviation for the resolved journal always takes precedence
    curated_abbr, _ = get_journal_abbreviation(journal) if journal else (None, None)

    abbr_cr = (rec_crossref.journal_abbreviation or "").strip() or None
    abbr_oa = (rec_openalex.journal_abbreviation or "").strip() or None

    if curated_abbr:
        journal_abbrev = curated_abbr
        field_provenance["journal_abbreviation"] = "curated_abbreviation"
    elif abbr_cr and abbr_oa:
        if abbr_cr.lower() == abbr_oa.lower():
            journal_abbrev = abbr_cr
            field_provenance["journal_abbreviation"] = rec_crossref.field_provenance.get(
                "journal_abbreviation", "crossref"
            )
        elif normalize_journal_name(abbr_cr) == normalize_journal_name(abbr_oa):
            # Differ only by punctuation (e.g. missing periods) -> pick standard with periods
            journal_abbrev = abbr_cr if "." in abbr_cr else abbr_oa
            field_provenance["journal_abbreviation"] = "crossref"
        else:
            conflicts.append(
                {
                    "field": "journal_abbreviation",
                    "reason": f"Journal abbreviation disagreement ('{abbr_cr}' vs '{abbr_oa}')",
                    "crossref": abbr_cr,
                    "openalex": abbr_oa,
                }
            )
            journal_abbrev = abbr_cr
            field_provenance["journal_abbreviation"] = "crossref"
    elif abbr_cr:
        journal_abbrev = abbr_cr
        field_provenance["journal_abbreviation"] = rec_crossref.field_provenance.get(
            "journal_abbreviation", "crossref"
        )
    elif abbr_oa:
        journal_abbrev = abbr_oa
        field_provenance["journal_abbreviation"] = rec_openalex.field_provenance.get(
            "journal_abbreviation", "openalex"
        )
    else:
        journal_abbrev = None


    # DOI URL
    doi_url = rec_crossref.doi_url or rec_openalex.doi_url
    if rec_crossref.doi_url and rec_openalex.doi_url:
        if rec_crossref.doi_url.lower() == rec_openalex.doi_url.lower():
            doi_url = rec_crossref.doi_url
            field_provenance["doi_url"] = "crossref"
        else:
            conflicts.append(
                {
                    "field": "doi_url",
                    "reason": f"DOI disagreement ('{rec_crossref.doi_url}' vs '{rec_openalex.doi_url}')",
                    "crossref": rec_crossref.doi_url,
                    "openalex": rec_openalex.doi_url,
                }
            )
            doi_url = rec_crossref.doi_url
            field_provenance["doi_url"] = "crossref"
    elif rec_crossref.doi_url:
        field_provenance["doi_url"] = "crossref"
    elif rec_openalex.doi_url:
        field_provenance["doi_url"] = "openalex"

    # Volume
    volume = rec_crossref.volume or rec_openalex.volume
    if rec_crossref.volume and rec_openalex.volume:
        if rec_crossref.volume == rec_openalex.volume:
            field_provenance["volume"] = "crossref"
        else:
            conflicts.append(
                {
                    "field": "volume",
                    "reason": f"Volume disagreement ('{rec_crossref.volume}' vs '{rec_openalex.volume}')",
                    "crossref": rec_crossref.volume,
                    "openalex": rec_openalex.volume,
                }
            )
            field_provenance["volume"] = "crossref"
    elif rec_crossref.volume:
        field_provenance["volume"] = "crossref"
    elif rec_openalex.volume:
        field_provenance["volume"] = "openalex"

    # Issue
    issue = rec_crossref.issue or rec_openalex.issue
    if rec_crossref.issue and rec_openalex.issue:
        if rec_crossref.issue == rec_openalex.issue:
            field_provenance["issue"] = "crossref"
        else:
            conflicts.append(
                {
                    "field": "issue",
                    "reason": f"Issue disagreement ('{rec_crossref.issue}' vs '{rec_openalex.issue}')",
                    "crossref": rec_crossref.issue,
                    "openalex": rec_openalex.issue,
                }
            )
            field_provenance["issue"] = "crossref"
    elif rec_crossref.issue:
        field_provenance["issue"] = "crossref"
    elif rec_openalex.issue:
        field_provenance["issue"] = "openalex"

    # First page
    first_page = rec_crossref.first_page or rec_openalex.first_page
    if rec_crossref.first_page and rec_openalex.first_page:
        if rec_crossref.first_page == rec_openalex.first_page:
            field_provenance["first_page"] = "crossref"
        else:
            conflicts.append(
                {
                    "field": "first_page",
                    "reason": f"First page disagreement ('{rec_crossref.first_page}' vs '{rec_openalex.first_page}')",
                    "crossref": rec_crossref.first_page,
                    "openalex": rec_openalex.first_page,
                }
            )
            field_provenance["first_page"] = "crossref"
    elif rec_crossref.first_page:
        field_provenance["first_page"] = "crossref"
    elif rec_openalex.first_page:
        field_provenance["first_page"] = "openalex"

    # Article number
    article_number = rec_crossref.article_number or rec_openalex.article_number
    if rec_crossref.article_number and rec_openalex.article_number:
        if rec_crossref.article_number == rec_openalex.article_number:
            field_provenance["article_number"] = "crossref"
        else:
            conflicts.append(
                {
                    "field": "article_number",
                    "reason": f"Article number disagreement ('{rec_crossref.article_number}' vs '{rec_openalex.article_number}')",
                    "crossref": rec_crossref.article_number,
                    "openalex": rec_openalex.article_number,
                }
            )
            field_provenance["article_number"] = "crossref"
    elif rec_crossref.article_number:
        field_provenance["article_number"] = "crossref"
    elif rec_openalex.article_number:
        field_provenance["article_number"] = "openalex"

    merged = ArticleMetadata(
        title=title,
        authors=authors,
        year=year,
        journal=journal,
        journal_abbreviation=journal_abbrev,
        doi_url=doi_url,
        volume=volume,
        issue=issue,
        first_page=first_page,
        article_number=article_number,
        source_provider="merged",
        provider_id=rec_crossref.provider_id or rec_openalex.provider_id,
        source_url=rec_crossref.source_url or rec_openalex.source_url,
        field_provenance=field_provenance,
        warnings=list(set(rec_crossref.warnings + rec_openalex.warnings)),
        is_preprint=rec_crossref.is_preprint or rec_openalex.is_preprint,
    )
    return merged, conflicts, field_provenance
